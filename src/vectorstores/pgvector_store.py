"""
PostgreSQL pgvector integration for persistent vector storage.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import asyncpg
import numpy as np
from dataclasses import dataclass
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    chunk_id: str
    document_id: str


class PgVectorStore:
    """PostgreSQL pgvector store for embeddings."""
    
    def __init__(self, connection_string: str, table_name: str = "embeddings"):
        self.connection_string = connection_string
        self.table_name = table_name
        self.pool = None
    
    async def initialize(self):
        """Initialize the connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Initialized pgvector connection pool")
        except Exception as e:
            logger.error(f"Failed to initialize pgvector pool: {e}")
            raise
    
    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Closed pgvector connection pool")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """Add embeddings to the store."""
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # Prepare data for batch insert
                values = []
                for data in embeddings_data:
                    values.append((
                        data['document_id'],
                        data['chunk_id'],
                        data['content'],
                        data['embedding'],
                        data.get('metadata', {}),
                        data.get('created_at')
                    ))
                
                # Batch insert
                await conn.executemany(
                    f"""
                    INSERT INTO {self.table_name} 
                    (document_id, chunk_id, content, embedding, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    values
                )
                
                logger.info(f"Added {len(embeddings_data)} embeddings to pgvector")
                return True
        
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar embeddings."""
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # Build the query
                query = f"""
                    SELECT 
                        content,
                        metadata,
                        chunk_id,
                        document_id,
                        1 - (embedding <=> $1::vector) as similarity_score
                    FROM {self.table_name}
                    WHERE 1 - (embedding <=> $1::vector) > $2
                """
                
                params = [query_embedding, similarity_threshold]
                param_count = 2
                
                # Add metadata filters if provided
                if filter_metadata:
                    for key, value in filter_metadata.items():
                        param_count += 1
                        query += f" AND metadata->>'{key}' = ${param_count}"
                        params.append(str(value))
                
                query += f" ORDER BY similarity_score DESC LIMIT {top_k}"
                
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    result = SearchResult(
                        content=row['content'],
                        metadata=dict(row['metadata']) if row['metadata'] else {},
                        similarity_score=float(row['similarity_score']),
                        chunk_id=row['chunk_id'],
                        document_id=row['document_id']
                    )
                    results.append(result)
                
                logger.info(f"Found {len(results)} similar embeddings")
                return results
        
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            raise
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT content, metadata, chunk_id, embedding
                    FROM {self.table_name}
                    WHERE document_id = $1
                    ORDER BY chunk_id
                    """,
                    document_id
                )
                
                chunks = []
                for row in rows:
                    chunks.append({
                        'content': row['content'],
                        'metadata': dict(row['metadata']) if row['metadata'] else {},
                        'chunk_id': row['chunk_id'],
                        'embedding': row['embedding']
                    })
                
                logger.info(f"Retrieved {len(chunks)} chunks for document {document_id}")
                return chunks
        
        except Exception as e:
            logger.error(f"Failed to get document chunks: {e}")
            raise
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a specific document."""
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE document_id = $1",
                    document_id
                )
                
                deleted_count = int(result.split()[-1])
                logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
                return True
        
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # Total embeddings
                total_embeddings = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_name}")
                
                # Unique documents
                unique_documents = await conn.fetchval(
                    f"SELECT COUNT(DISTINCT document_id) FROM {self.table_name}"
                )
                
                # Average embedding dimension
                avg_dimension = await conn.fetchval(
                    f"SELECT AVG(array_length(embedding, 1)) FROM {self.table_name}"
                )
                
                return {
                    'total_embeddings': total_embeddings,
                    'unique_documents': unique_documents,
                    'average_dimension': float(avg_dimension) if avg_dimension else 0,
                    'table_name': self.table_name
                }
        
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
