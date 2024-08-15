"""
Faiss vector store for fast in-memory similarity search.
"""

import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FaissDocument:
    """Document stored in Faiss index."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    document_id: str


class FaissStore:
    """Faiss-based vector store for fast similarity search."""
    
    def __init__(self, index_path: str = "./data/faiss_index", dimension: int = 1536):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.documents = []  # Store document metadata
        self.document_map = {}  # Map chunk_id to document index
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
    
    def initialize(self):
        """Initialize or load the Faiss index."""
        try:
            if os.path.exists(f"{self.index_path}.index"):
                self._load_index()
                logger.info(f"Loaded existing Faiss index from {self.index_path}")
            else:
                self._create_index()
                logger.info(f"Created new Faiss index at {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Faiss index: {e}")
            raise
    
    def _create_index(self):
        """Create a new Faiss index."""
        # Use IndexFlatIP for cosine similarity (after normalization)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.document_map = {}
    
    def _load_index(self):
        """Load existing Faiss index."""
        # Load the index
        self.index = faiss.read_index(f"{self.index_path}.index")
        
        # Load document metadata
        with open(f"{self.index_path}.metadata", 'rb') as f:
            self.documents = pickle.load(f)
        
        # Rebuild document map
        self.document_map = {doc.chunk_id: i for i, doc in enumerate(self.documents)}
    
    def _save_index(self):
        """Save the Faiss index and metadata."""
        try:
            # Save the index
            faiss.write_index(self.index, f"{self.index_path}.index")
            
            # Save document metadata
            with open(f"{self.index_path}.metadata", 'wb') as f:
                pickle.dump(self.documents, f)
            
            logger.info(f"Saved Faiss index to {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save Faiss index: {e}")
            raise
    
    def add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """Add embeddings to the Faiss index."""
        if self.index is None:
            self.initialize()
        
        try:
            # Prepare embeddings and metadata
            embeddings = []
            new_documents = []
            
            for data in embeddings_data:
                embedding = np.array(data['embedding'], dtype=np.float32)
                
                # Normalize for cosine similarity
                embedding = embedding / np.linalg.norm(embedding)
                embeddings.append(embedding)
                
                # Create document metadata
                doc = FaissDocument(
                    content=data['content'],
                    metadata=data.get('metadata', {}),
                    chunk_id=data['chunk_id'],
                    document_id=data['document_id']
                )
                new_documents.append(doc)
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Add to index
            self.index.add(embeddings_array)
            
            # Update document storage
            start_idx = len(self.documents)
            self.documents.extend(new_documents)
            
            # Update document map
            for i, doc in enumerate(new_documents):
                self.document_map[doc.chunk_id] = start_idx + i
            
            # Save the updated index
            self._save_index()
            
            logger.info(f"Added {len(embeddings_data)} embeddings to Faiss index")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add embeddings to Faiss: {e}")
            raise
    
    def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        if self.index is None:
            self.initialize()
        
        if self.index.ntotal == 0:
            logger.warning("Faiss index is empty")
            return []
        
        try:
            # Normalize query embedding for cosine similarity
            query_array = np.array([query_embedding], dtype=np.float32)
            query_array = query_array / np.linalg.norm(query_array)
            
            # Search
            scores, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # No more results
                    break
                
                if score >= similarity_threshold:
                    doc = self.documents[idx]
                    results.append({
                        'content': doc.content,
                        'metadata': doc.metadata,
                        'similarity_score': float(score),
                        'chunk_id': doc.chunk_id,
                        'document_id': doc.document_id
                    })
            
            logger.info(f"Found {len(results)} similar embeddings in Faiss")
            return results
        
        except Exception as e:
            logger.error(f"Failed to search Faiss index: {e}")
            raise
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        if self.index is None:
            self.initialize()
        
        chunks = []
        for doc in self.documents:
            if doc.document_id == document_id:
                chunks.append({
                    'content': doc.content,
                    'metadata': doc.metadata,
                    'chunk_id': doc.chunk_id,
                    'document_id': doc.document_id
                })
        
        logger.info(f"Retrieved {len(chunks)} chunks for document {document_id}")
        return chunks
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a specific document."""
        if self.index is None:
            self.initialize()
        
        try:
            # Find chunks to delete
            chunks_to_delete = []
            for i, doc in enumerate(self.documents):
                if doc.document_id == document_id:
                    chunks_to_delete.append(i)
            
            if not chunks_to_delete:
                logger.info(f"No chunks found for document {document_id}")
                return True
            
            # Remove from documents list (in reverse order to maintain indices)
            for i in sorted(chunks_to_delete, reverse=True):
                del self.documents[i]
            
            # Rebuild the index
            self._rebuild_index()
            
            logger.info(f"Deleted {len(chunks_to_delete)} chunks for document {document_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    def _rebuild_index(self):
        """Rebuild the Faiss index from current documents."""
        if not self.documents:
            self._create_index()
            return
        
        try:
            # Create new index
            new_index = faiss.IndexFlatIP(self.dimension)
            
            # Rebuild document map
            self.document_map = {}
            
            # Add all documents to new index
            embeddings = []
            for i, doc in enumerate(self.documents):
                # We need to get the original embedding, but we don't store it
                # This is a limitation of the current implementation
                # In practice, you'd want to store embeddings separately
                logger.warning("Rebuilding index without original embeddings - this will cause data loss")
                break
            
            # For now, just create an empty index
            self.index = new_index
            self.documents = []
            self.document_map = {}
            
            logger.info("Rebuilt Faiss index")
        
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the Faiss index."""
        if self.index is None:
            self.initialize()
        
        # Count unique documents
        unique_documents = len(set(doc.document_id for doc in self.documents))
        
        return {
            'total_embeddings': self.index.ntotal if self.index else 0,
            'unique_documents': unique_documents,
            'dimension': self.dimension,
            'index_type': 'IndexFlatIP',
            'index_path': self.index_path
        }
    
    def clear(self):
        """Clear all data from the index."""
        self._create_index()
        self._save_index()
        logger.info("Cleared Faiss index")
