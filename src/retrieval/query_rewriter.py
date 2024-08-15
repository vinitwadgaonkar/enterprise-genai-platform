"""
Query rewriting for improved retrieval precision.
Implements various query expansion and rewriting strategies.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
from openai import OpenAI

logger = structlog.get_logger(__name__)


@dataclass
class QueryRewriteResult:
    """Result of query rewriting."""
    original_query: str
    rewritten_query: str
    rewrite_type: str
    confidence: float
    metadata: Dict[str, Any]


class QueryRewriter:
    """Handles query rewriting and expansion for better retrieval."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
    
    def rewrite_query(self, query: str, rewrite_type: str = "expansion") -> QueryRewriteResult:
        """Rewrite a query using the specified strategy."""
        if rewrite_type == "expansion":
            return self._expand_query(query)
        elif rewrite_type == "reformulation":
            return self._reformulate_query(query)
        elif rewrite_type == "synonym":
            return self._synonym_expansion(query)
        elif rewrite_type == "paraphrase":
            return self._paraphrase_query(query)
        else:
            raise ValueError(f"Unknown rewrite type: {rewrite_type}")
    
    def _expand_query(self, query: str) -> QueryRewriteResult:
        """Expand query with related terms and concepts."""
        try:
            prompt = f"""
            Expand the following query with related terms, synonyms, and concepts to improve search results.
            Focus on adding relevant technical terms, alternative phrasings, and related concepts.
            
            Original query: {query}
            
            Provide an expanded query that maintains the original intent while adding relevant terms.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten_query,
                rewrite_type="expansion",
                confidence=0.8,
                metadata={"method": "llm_expansion"}
            )
        
        except Exception as e:
            logger.error(f"Failed to expand query: {e}")
            # Fallback to simple expansion
            return self._simple_expansion(query)
    
    def _reformulate_query(self, query: str) -> QueryRewriteResult:
        """Reformulate query for better clarity and specificity."""
        try:
            prompt = f"""
            Reformulate the following query to be more specific and clear for document search.
            Make it more precise while maintaining the original intent.
            
            Original query: {query}
            
            Provide a reformulated query that is more specific and likely to find relevant documents.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=150
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten_query,
                rewrite_type="reformulation",
                confidence=0.9,
                metadata={"method": "llm_reformulation"}
            )
        
        except Exception as e:
            logger.error(f"Failed to reformulate query: {e}")
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=query,
                rewrite_type="reformulation",
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    def _synonym_expansion(self, query: str) -> QueryRewriteResult:
        """Expand query with synonyms."""
        try:
            prompt = f"""
            Expand the following query with synonyms and alternative terms.
            Keep the original query intact but add synonyms in parentheses.
            
            Original query: {query}
            
            Example format: "machine learning (ML, artificial intelligence, AI, deep learning)"
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten_query,
                rewrite_type="synonym",
                confidence=0.7,
                metadata={"method": "llm_synonym"}
            )
        
        except Exception as e:
            logger.error(f"Failed to expand synonyms: {e}")
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=query,
                rewrite_type="synonym",
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    def _paraphrase_query(self, query: str) -> QueryRewriteResult:
        """Paraphrase the query while maintaining meaning."""
        try:
            prompt = f"""
            Paraphrase the following query in a different way while maintaining the exact same meaning.
            
            Original query: {query}
            
            Provide a paraphrased version that expresses the same intent using different words.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=100
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten_query,
                rewrite_type="paraphrase",
                confidence=0.8,
                metadata={"method": "llm_paraphrase"}
            )
        
        except Exception as e:
            logger.error(f"Failed to paraphrase query: {e}")
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=query,
                rewrite_type="paraphrase",
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    def _simple_expansion(self, query: str) -> QueryRewriteResult:
        """Simple rule-based query expansion as fallback."""
        # Basic keyword expansion rules
        expansions = {
            r'\bML\b': 'machine learning ML',
            r'\bAI\b': 'artificial intelligence AI',
            r'\bAPI\b': 'application programming interface API',
            r'\bSQL\b': 'structured query language SQL',
            r'\bDB\b': 'database DB',
            r'\bUI\b': 'user interface UI',
            r'\bUX\b': 'user experience UX'
        }
        
        expanded_query = query
        for pattern, replacement in expansions.items():
            expanded_query = re.sub(pattern, replacement, expanded_query, flags=re.IGNORECASE)
        
        return QueryRewriteResult(
            original_query=query,
            rewritten_query=expanded_query,
            rewrite_type="expansion",
            confidence=0.5,
            metadata={"method": "rule_based"}
        )
    
    def batch_rewrite_queries(self, queries: List[str], rewrite_type: str = "expansion") -> List[QueryRewriteResult]:
        """Rewrite multiple queries in batch."""
        results = []
        
        for query in queries:
            try:
                result = self.rewrite_query(query, rewrite_type)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to rewrite query '{query}': {e}")
                # Add fallback result
                results.append(QueryRewriteResult(
                    original_query=query,
                    rewritten_query=query,
                    rewrite_type=rewrite_type,
                    confidence=0.1,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def get_rewrite_suggestions(self, query: str) -> List[str]:
        """Get multiple rewrite suggestions for a query."""
        suggestions = []
        
        # Try different rewrite types
        rewrite_types = ["expansion", "reformulation", "synonym", "paraphrase"]
        
        for rewrite_type in rewrite_types:
            try:
                result = self.rewrite_query(query, rewrite_type)
                if result.confidence > 0.5:
                    suggestions.append(result.rewritten_query)
            except Exception as e:
                logger.warning(f"Failed to generate {rewrite_type} suggestion: {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
