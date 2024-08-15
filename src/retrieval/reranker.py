"""
Cross-encoder reranking for improved retrieval precision.
Uses sentence transformers for reranking retrieved documents.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
from sentence_transformers import CrossEncoder
import torch

logger = structlog.get_logger(__name__)


@dataclass
class RerankResult:
    """Result of document reranking."""
    content: str
    metadata: Dict[str, Any]
    original_score: float
    rerank_score: float
    chunk_id: str
    document_id: str
    rank_change: int  # Change in rank position


class CrossEncoderReranker:
    """Cross-encoder reranker for improving retrieval precision."""
    
    def __init__(
        self, 
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: Optional[str] = None
    ):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            self.model = CrossEncoder(model_name, device=self.device)
            logger.info(f"Loaded cross-encoder model: {model_name} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            raise
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: Optional[int] = None
    ) -> List[RerankResult]:
        """Rerank documents based on query-document relevance."""
        if not documents:
            return []
        
        try:
            # Prepare query-document pairs
            pairs = [(query, doc['content']) for doc in documents]
            
            # Get rerank scores
            rerank_scores = self.model.predict(pairs)
            
            # Create results with original and rerank scores
            results = []
            for i, (doc, score) in enumerate(zip(documents, rerank_scores)):
                result = RerankResult(
                    content=doc['content'],
                    metadata=doc.get('metadata', {}),
                    original_score=doc.get('similarity_score', 0.0),
                    rerank_score=float(score),
                    chunk_id=doc.get('chunk_id', ''),
                    document_id=doc.get('document_id', ''),
                    rank_change=0  # Will be calculated after sorting
                )
                results.append(result)
            
            # Sort by rerank score (descending)
            results.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # Calculate rank changes
            original_ranks = {doc['chunk_id']: i for i, doc in enumerate(documents)}
            for i, result in enumerate(results):
                original_rank = original_ranks.get(result.chunk_id, i)
                result.rank_change = original_rank - i
            
            # Apply top_k filter if specified
            if top_k is not None:
                results = results[:top_k]
            
            logger.info(f"Reranked {len(documents)} documents, top {len(results)} selected")
            return results
        
        except Exception as e:
            logger.error(f"Failed to rerank documents: {e}")
            raise
    
    def rerank_with_threshold(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        threshold: float = 0.5
    ) -> List[RerankResult]:
        """Rerank documents and filter by relevance threshold."""
        results = self.rerank(query, documents)
        
        # Filter by threshold
        filtered_results = [r for r in results if r.rerank_score >= threshold]
        
        logger.info(f"Filtered {len(results)} documents to {len(filtered_results)} above threshold {threshold}")
        return filtered_results
    
    def batch_rerank(
        self, 
        queries: List[str], 
        documents_list: List[List[Dict[str, Any]]]
    ) -> List[List[RerankResult]]:
        """Rerank multiple query-document sets in batch."""
        if len(queries) != len(documents_list):
            raise ValueError("Number of queries must match number of document lists")
        
        results = []
        for query, documents in zip(queries, documents_list):
            try:
                reranked = self.rerank(query, documents)
                results.append(reranked)
            except Exception as e:
                logger.error(f"Failed to rerank for query '{query}': {e}")
                results.append([])
        
        return results
    
    def get_relevance_explanation(
        self, 
        query: str, 
        document: str, 
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """Get explanation of why a document is relevant to a query."""
        try:
            # This is a simplified explanation - in practice, you might use
            # attention weights or other interpretability methods
            pairs = [(query, document)]
            score = self.model.predict(pairs)[0]
            
            # Simple explanation based on score
            if score > 0.8:
                explanation = "Highly relevant - strong semantic match"
            elif score > 0.6:
                explanation = "Moderately relevant - good semantic match"
            elif score > 0.4:
                explanation = "Somewhat relevant - partial semantic match"
            else:
                explanation = "Low relevance - weak semantic match"
            
            return [(explanation, float(score))]
        
        except Exception as e:
            logger.error(f"Failed to get relevance explanation: {e}")
            return [("Error generating explanation", 0.0)]


class HybridReranker:
    """Hybrid reranker that combines multiple reranking strategies."""
    
    def __init__(self, cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.cross_encoder = CrossEncoderReranker(cross_encoder_model)
        self.weights = {
            'original': 0.3,
            'cross_encoder': 0.7
        }
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: Optional[int] = None
    ) -> List[RerankResult]:
        """Rerank using hybrid approach."""
        if not documents:
            return []
        
        try:
            # Get cross-encoder rerank results
            cross_encoder_results = self.cross_encoder.rerank(query, documents)
            
            # Create hybrid results
            hybrid_results = []
            for i, (doc, ce_result) in enumerate(zip(documents, cross_encoder_results)):
                # Combine scores with weights
                hybrid_score = (
                    self.weights['original'] * doc.get('similarity_score', 0.0) +
                    self.weights['cross_encoder'] * ce_result.rerank_score
                )
                
                result = RerankResult(
                    content=doc['content'],
                    metadata=doc.get('metadata', {}),
                    original_score=doc.get('similarity_score', 0.0),
                    rerank_score=hybrid_score,
                    chunk_id=doc.get('chunk_id', ''),
                    document_id=doc.get('document_id', ''),
                    rank_change=0
                )
                hybrid_results.append(result)
            
            # Sort by hybrid score
            hybrid_results.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # Calculate rank changes
            original_ranks = {doc['chunk_id']: i for i, doc in enumerate(documents)}
            for i, result in enumerate(hybrid_results):
                original_rank = original_ranks.get(result.chunk_id, i)
                result.rank_change = original_rank - i
            
            # Apply top_k filter
            if top_k is not None:
                hybrid_results = hybrid_results[:top_k]
            
            logger.info(f"Hybrid reranked {len(documents)} documents")
            return hybrid_results
        
        except Exception as e:
            logger.error(f"Failed to hybrid rerank: {e}")
            raise
    
    def set_weights(self, original_weight: float, cross_encoder_weight: float):
        """Set the weights for combining scores."""
        total = original_weight + cross_encoder_weight
        self.weights['original'] = original_weight / total
        self.weights['cross_encoder'] = cross_encoder_weight / total
        logger.info(f"Updated rerank weights: original={self.weights['original']}, cross_encoder={self.weights['cross_encoder']}")
