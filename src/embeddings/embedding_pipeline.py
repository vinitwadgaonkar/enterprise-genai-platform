"""
Embedding pipeline using OpenAI text-embedding-3-large model.
Handles document chunking, embedding generation, and batch processing.
"""

import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI, AsyncOpenAI
import tiktoken
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    content: str
    chunk_id: str
    document_id: str
    chunk_index: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    chunk: DocumentChunk
    embedding: List[float]
    token_count: int
    model: str


class DocumentChunker:
    """Handles document chunking with various strategies."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_document(self, content: str, document_id: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Split a document into chunks."""
        if metadata is None:
            metadata = {}
        
        # Tokenize the content
        tokens = self.encoding.encode(content)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            # Calculate end position
            end = min(start + self.chunk_size, len(tokens))
            
            # Extract chunk tokens and decode
            chunk_tokens = tokens[start:end]
            chunk_content = self.encoding.decode(chunk_tokens)
            
            # Create chunk ID
            chunk_id = self._generate_chunk_id(document_id, chunk_index, chunk_content)
            
            # Create chunk metadata
            chunk_metadata = {
                **metadata,
                'chunk_size': len(chunk_tokens),
                'chunk_overlap': self.chunk_overlap if chunk_index > 0 else 0,
                'total_chunks': len(tokens) // self.chunk_size + (1 if len(tokens) % self.chunk_size > 0 else 0)
            }
            
            chunk = DocumentChunk(
                content=chunk_content,
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=chunk_index,
                metadata=chunk_metadata
            )
            
            chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            chunk_index += 1
            
            # Prevent infinite loop
            if start >= len(tokens):
                break
        
        logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int, content: str) -> str:
        """Generate a unique chunk ID."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{document_id}_chunk_{chunk_index}_{content_hash}"


class EmbeddingGenerator:
    """Generates embeddings using OpenAI text-embedding-3-large model."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-large", batch_size: int = 100):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.batch_size = batch_size
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generate embedding for a single text."""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            token_count = response.usage.total_tokens
            
            return embedding, token_count
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Tuple[List[float], int]]:
        """Generate embeddings for a batch of texts."""
        results = []
        
        # Process in batches to avoid rate limits
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                for data in response.data:
                    embedding = data.embedding
                    token_count = len(self.encoding.encode(batch[data.index]))
                    results.append((embedding, token_count))
                
                logger.info(f"Generated embeddings for batch {i//self.batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch: {e}")
                # Fallback to individual requests
                for text in batch:
                    try:
                        embedding, token_count = await self.generate_embedding(text)
                        results.append((embedding, token_count))
                    except Exception as individual_error:
                        logger.error(f"Failed to generate embedding for individual text: {individual_error}")
                        results.append(([], 0))
        
        return results
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))


class EmbeddingPipeline:
    """Main pipeline for document processing and embedding generation."""
    
    def __init__(self, api_key: str, chunk_size: int = 1000, chunk_overlap: int = 200, batch_size: int = 100):
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)
        self.generator = EmbeddingGenerator(api_key, batch_size=batch_size)
    
    async def process_document(self, content: str, document_id: str, metadata: Dict[str, Any] = None) -> List[EmbeddingResult]:
        """Process a document: chunk, embed, and return results."""
        # Chunk the document
        chunks = self.chunker.chunk_document(content, document_id, metadata)
        
        if not chunks:
            logger.warning(f"No chunks created for document {document_id}")
            return []
        
        # Extract texts for embedding
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        embedding_results = await self.generator.generate_embeddings_batch(texts)
        
        # Combine chunks with embeddings
        results = []
        for chunk, (embedding, token_count) in zip(chunks, embedding_results):
            result = EmbeddingResult(
                chunk=chunk,
                embedding=embedding,
                token_count=token_count,
                model=self.generator.model
            )
            results.append(result)
        
        logger.info(f"Processed document {document_id}: {len(results)} chunks, {sum(r.token_count for r in results)} tokens")
        return results
    
    async def process_documents_batch(self, documents: List[Dict[str, Any]]) -> List[List[EmbeddingResult]]:
        """Process multiple documents in parallel."""
        tasks = []
        
        for doc in documents:
            task = self.process_document(
                content=doc['content'],
                document_id=doc['document_id'],
                metadata=doc.get('metadata', {})
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process document {i}: {result}")
                valid_results.append([])
            else:
                valid_results.append(result)
        
        return valid_results
    
    def estimate_cost(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate the cost of processing documents."""
        total_tokens = 0
        total_chunks = 0
        
        for doc in documents:
            # Estimate chunks
            content_tokens = self.generator.count_tokens(doc['content'])
            estimated_chunks = (content_tokens + self.chunker.chunk_size - 1) // self.chunker.chunk_size
            total_chunks += estimated_chunks
            total_tokens += content_tokens
        
        # OpenAI pricing for text-embedding-3-large (as of 2024)
        cost_per_1k_tokens = 0.00013  # $0.00013 per 1K tokens
        estimated_cost = (total_tokens / 1000) * cost_per_1k_tokens
        
        return {
            'total_documents': len(documents),
            'estimated_chunks': total_chunks,
            'estimated_tokens': total_tokens,
            'estimated_cost_usd': round(estimated_cost, 4),
            'cost_per_document': round(estimated_cost / len(documents), 4) if documents else 0
        }
