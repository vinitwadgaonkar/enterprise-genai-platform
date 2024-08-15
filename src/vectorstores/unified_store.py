"""
Unified vector store interface supporting both pgvector and Faiss.
"""

from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import structlog
from .pgvector_store import PgVectorStore, SearchResult
from .faiss_store import FaissStore

logger = structlog.get_logger(__name__)


class VectorStoreInterface(ABC):
    """Abstract interface for vector stores."""
    
    @abstractmethod
    async def add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """Add embeddings to the store."""
        pass
    
    @abstractmethod
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        pass
    
    @abstractmethod
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a specific document."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the store."""
        pass


class UnifiedVectorStore(VectorStoreInterface):
    """Unified vector store that can use either pgvector or Faiss."""
    
    def __init__(
        self, 
        store_type: str = "pgvector",
        pgvector_connection: Optional[str] = None,
        faiss_index_path: Optional[str] = None,
        dimension: int = 1536
    ):
        self.store_type = store_type
        self.dimension = dimension
        
        if store_type == "pgvector":
            if not pgvector_connection:
                raise ValueError("pgvector_connection is required for pgvector store")
            self.store = PgVectorStore(pgvector_connection)
        elif store_type == "faiss":
            if not faiss_index_path:
                faiss_index_path = "./data/faiss_index"
            self.store = FaissStore(faiss_index_path, dimension)
        else:
            raise ValueError(f"Unsupported store type: {store_type}")
    
    async def initialize(self):
        """Initialize the vector store."""
        if self.store_type == "pgvector":
            await self.store.initialize()
        else:
            self.store.initialize()
        
        logger.info(f"Initialized {self.store_type} vector store")
    
    async def close(self):
        """Close the vector store."""
        if self.store_type == "pgvector":
            await self.store.close()
        # Faiss doesn't need explicit closing
        logger.info(f"Closed {self.store_type} vector store")
    
    async def add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """Add embeddings to the store."""
        if self.store_type == "pgvector":
            return await self.store.add_embeddings(embeddings_data)
        else:
            return self.store.add_embeddings(embeddings_data)
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        if self.store_type == "pgvector":
            results = await self.store.similarity_search(
                query_embedding, top_k, similarity_threshold, filter_metadata
            )
            # Convert SearchResult objects to dictionaries
            return [
                {
                    'content': result.content,
                    'metadata': result.metadata,
                    'similarity_score': result.similarity_score,
                    'chunk_id': result.chunk_id,
                    'document_id': result.document_id
                }
                for result in results
            ]
        else:
            return self.store.similarity_search(
                query_embedding, top_k, similarity_threshold
            )
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        if self.store_type == "pgvector":
            return await self.store.get_document_chunks(document_id)
        else:
            return self.store.get_document_chunks(document_id)
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a specific document."""
        if self.store_type == "pgvector":
            return await self.store.delete_document(document_id)
        else:
            return self.store.delete_document(document_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the store."""
        if self.store_type == "pgvector":
            return await self.store.get_stats()
        else:
            return self.store.get_stats()
    
    def switch_store(self, new_store_type: str, **kwargs):
        """Switch to a different vector store type."""
        logger.info(f"Switching from {self.store_type} to {new_store_type}")
        
        # Close current store
        if self.store_type == "pgvector":
            # Note: This would need to be awaited in practice
            pass
        
        # Initialize new store
        self.store_type = new_store_type
        
        if new_store_type == "pgvector":
            if 'pgvector_connection' not in kwargs:
                raise ValueError("pgvector_connection is required for pgvector store")
            self.store = PgVectorStore(kwargs['pgvector_connection'])
        elif new_store_type == "faiss":
            faiss_index_path = kwargs.get('faiss_index_path', "./data/faiss_index")
            self.store = FaissStore(faiss_index_path, self.dimension)
        else:
            raise ValueError(f"Unsupported store type: {new_store_type}")


class HybridVectorStore:
    """Hybrid vector store that uses both pgvector and Faiss for different purposes."""
    
    def __init__(
        self,
        pgvector_connection: str,
        faiss_index_path: str = "./data/faiss_index",
        dimension: int = 1536,
        primary_store: str = "pgvector"  # Primary store for writes
    ):
        self.primary_store = primary_store
        self.pgvector_store = PgVectorStore(pgvector_connection)
        self.faiss_store = FaissStore(faiss_index_path, dimension)
        self.dimension = dimension
    
    async def initialize(self):
        """Initialize both vector stores."""
        await self.pgvector_store.initialize()
        self.faiss_store.initialize()
        logger.info("Initialized hybrid vector store")
    
    async def close(self):
        """Close both vector stores."""
        await self.pgvector_store.close()
        # Faiss doesn't need explicit closing
        logger.info("Closed hybrid vector store")
    
    async def add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """Add embeddings to both stores."""
        try:
            # Add to primary store
            if self.primary_store == "pgvector":
                pgvector_success = await self.pgvector_store.add_embeddings(embeddings_data)
                faiss_success = self.faiss_store.add_embeddings(embeddings_data)
            else:
                faiss_success = self.faiss_store.add_embeddings(embeddings_data)
                pgvector_success = await self.pgvector_store.add_embeddings(embeddings_data)
            
            success = pgvector_success and faiss_success
            if success:
                logger.info(f"Added embeddings to both stores: {len(embeddings_data)} items")
            else:
                logger.warning("Failed to add embeddings to one or both stores")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to add embeddings to hybrid store: {e}")
            raise
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
        use_faiss: bool = True  # Use Faiss for faster search by default
    ) -> List[Dict[str, Any]]:
        """Search using the specified store."""
        try:
            if use_faiss:
                # Use Faiss for fast search
                results = self.faiss_store.similarity_search(
                    query_embedding, top_k, similarity_threshold
                )
            else:
                # Use pgvector for search with metadata filtering
                pgvector_results = await self.pgvector_store.similarity_search(
                    query_embedding, top_k, similarity_threshold, filter_metadata
                )
                results = [
                    {
                        'content': result.content,
                        'metadata': result.metadata,
                        'similarity_score': result.similarity_score,
                        'chunk_id': result.chunk_id,
                        'document_id': result.document_id
                    }
                    for result in pgvector_results
                ]
            
            logger.info(f"Found {len(results)} similar embeddings using {'Faiss' if use_faiss else 'pgvector'}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to search hybrid store: {e}")
            raise
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get document chunks from primary store."""
        if self.primary_store == "pgvector":
            return await self.pgvector_store.get_document_chunks(document_id)
        else:
            return self.faiss_store.get_document_chunks(document_id)
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document from both stores."""
        try:
            pgvector_success = await self.pgvector_store.delete_document(document_id)
            faiss_success = self.faiss_store.delete_document(document_id)
            
            success = pgvector_success and faiss_success
            if success:
                logger.info(f"Deleted document {document_id} from both stores")
            else:
                logger.warning(f"Failed to delete document {document_id} from one or both stores")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to delete document from hybrid store: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics from both stores."""
        try:
            pgvector_stats = await self.pgvector_store.get_stats()
            faiss_stats = self.faiss_store.get_stats()
            
            return {
                'pgvector': pgvector_stats,
                'faiss': faiss_stats,
                'primary_store': self.primary_store,
                'dimension': self.dimension
            }
        
        except Exception as e:
            logger.error(f"Failed to get hybrid store stats: {e}")
            raise
