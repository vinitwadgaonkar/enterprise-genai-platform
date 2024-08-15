"""
RAG (Retrieval-Augmented Generation) chain implementation.
"""

from typing import List, Dict, Any, Optional, Union
from langchain.chains import RetrievalQA
from langchain.chains.base import Chain
from langchain.schema import BaseRetriever, BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.schema import Document
import structlog

logger = structlog.get_logger(__name__)


class RAGChain:
    """RAG chain for document Q&A with retrieval and generation."""
    
    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLanguageModel,
        prompt_template: Optional[PromptTemplate] = None,
        return_source_documents: bool = True
    ):
        self.retriever = retriever
        self.llm = llm
        self.prompt_template = prompt_template
        self.return_source_documents = return_source_documents
        
        # Create the RAG chain
        self.chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=self.return_source_documents
        )
    
    async def arun(self, query: str, **kwargs) -> Dict[str, Any]:
        """Run the RAG chain asynchronously."""
        try:
            result = await self.chain.ainvoke({"query": query})
            
            return {
                "answer": result.get("result", ""),
                "source_documents": result.get("source_documents", []),
                "query": query,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"RAG chain execution failed: {e}")
            return {
                "answer": "",
                "source_documents": [],
                "query": query,
                "success": False,
                "error": str(e)
            }
    
    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """Run the RAG chain synchronously."""
        try:
            result = self.chain.invoke({"query": query})
            
            return {
                "answer": result.get("result", ""),
                "source_documents": result.get("source_documents", []),
                "query": query,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"RAG chain execution failed: {e}")
            return {
                "answer": "",
                "source_documents": [],
                "query": query,
                "success": False,
                "error": str(e)
            }
    
    def get_retriever(self) -> BaseRetriever:
        """Get the retriever used by this chain."""
        return self.retriever
    
    def get_llm(self) -> BaseLanguageModel:
        """Get the LLM used by this chain."""
        return self.llm
