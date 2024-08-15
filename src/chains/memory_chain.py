"""
Memory management chain for conversation history and context.
"""

from typing import List, Dict, Any, Optional, Union
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    ConversationEntityMemory,
    CombinedMemory
)
from langchain.schema import BaseLanguageModel
from langchain.prompts import PromptTemplate
import structlog

logger = structlog.get_logger(__name__)


class MemoryChain:
    """Chain for managing conversation memory and context."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_type: str = "buffer",
        max_token_limit: int = 2000,
        return_messages: bool = True
    ):
        self.llm = llm
        self.memory_type = memory_type
        self.max_token_limit = max_token_limit
        self.return_messages = return_messages
        
        # Create memory based on type
        self.memory = self._create_memory()
    
    def _create_memory(self):
        """Create memory instance based on type."""
        if self.memory_type == "buffer":
            return ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=self.return_messages
            )
        elif self.memory_type == "summary":
            return ConversationSummaryMemory(
                llm=self.llm,
                memory_key="chat_history",
                return_messages=self.return_messages
            )
        elif self.memory_type == "entity":
            return ConversationEntityMemory(
                llm=self.llm,
                memory_key="chat_history",
                return_messages=self.return_messages
            )
        elif self.memory_type == "combined":
            # Combine different memory types
            buffer_memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=self.return_messages
            )
            summary_memory = ConversationSummaryMemory(
                llm=self.llm,
                memory_key="summary",
                return_messages=self.return_messages
            )
            entity_memory = ConversationEntityMemory(
                llm=self.llm,
                memory_key="entities",
                return_messages=self.return_messages
            )
            
            return CombinedMemory(
                memories=[buffer_memory, summary_memory, entity_memory]
            )
        else:
            raise ValueError(f"Unsupported memory type: {self.memory_type}")
    
    def add_message(self, role: str, content: str, **kwargs):
        """Add a message to memory."""
        try:
            if hasattr(self.memory, 'chat_memory'):
                self.memory.chat_memory.add_message(
                    {"role": role, "content": content}
                )
            else:
                # For combined memory, add to all sub-memories
                for memory in self.memory.memories:
                    if hasattr(memory, 'chat_memory'):
                        memory.chat_memory.add_message(
                            {"role": role, "content": content}
                        )
            
            logger.info(f"Added {role} message to memory")
        
        except Exception as e:
            logger.error(f"Failed to add message to memory: {e}")
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for use in prompts."""
        try:
            if hasattr(self.memory, 'load_memory_variables'):
                return self.memory.load_memory_variables({})
            else:
                # For combined memory, get variables from all sub-memories
                variables = {}
                for memory in self.memory.memories:
                    if hasattr(memory, 'load_memory_variables'):
                        variables.update(memory.load_memory_variables({}))
                return variables
        
        except Exception as e:
            logger.error(f"Failed to get memory variables: {e}")
            return {}
    
    def clear_memory(self):
        """Clear all memory."""
        try:
            if hasattr(self.memory, 'clear'):
                self.memory.clear()
            else:
                # For combined memory, clear all sub-memories
                for memory in self.memory.memories:
                    if hasattr(memory, 'clear'):
                        memory.clear()
            
            logger.info("Cleared memory")
        
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation."""
        try:
            if self.memory_type == "summary" or self.memory_type == "combined":
                variables = self.get_memory_variables()
                return variables.get("summary", "")
            else:
                # For buffer memory, get the full conversation
                variables = self.get_memory_variables()
                return variables.get("chat_history", "")
        
        except Exception as e:
            logger.error(f"Failed to get conversation summary: {e}")
            return ""
    
    def get_entities(self) -> Dict[str, str]:
        """Get entities from conversation."""
        try:
            if self.memory_type == "entity" or self.memory_type == "combined":
                variables = self.get_memory_variables()
                return variables.get("entities", {})
            else:
                return {}
        
        except Exception as e:
            logger.error(f"Failed to get entities: {e}")
            return {}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory usage."""
        try:
            variables = self.get_memory_variables()
            
            stats = {
                "memory_type": self.memory_type,
                "variables": list(variables.keys()),
                "variable_count": len(variables)
            }
            
            # Get message count for buffer memory
            if hasattr(self.memory, 'chat_memory'):
                stats["message_count"] = len(self.memory.chat_memory.messages)
            elif hasattr(self.memory, 'memories'):
                # For combined memory
                total_messages = 0
                for memory in self.memory.memories:
                    if hasattr(memory, 'chat_memory'):
                        total_messages += len(memory.chat_memory.messages)
                stats["message_count"] = total_messages
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
    
    def save_memory(self, file_path: str):
        """Save memory to file."""
        try:
            import pickle
            
            with open(file_path, 'wb') as f:
                pickle.dump(self.memory, f)
            
            logger.info(f"Saved memory to {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def load_memory(self, file_path: str):
        """Load memory from file."""
        try:
            import pickle
            
            with open(file_path, 'rb') as f:
                self.memory = pickle.load(f)
            
            logger.info(f"Loaded memory from {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
    
    def get_memory(self):
        """Get the memory instance."""
        return self.memory
