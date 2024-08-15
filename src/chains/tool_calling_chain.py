"""
Tool calling chain for SQL and API interactions.
"""

from typing import List, Dict, Any, Optional, Union
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain.schema import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import structlog

logger = structlog.get_logger(__name__)


class ToolCallingChain:
    """Chain for tool calling with SQL and API tools."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: List[BaseTool],
        system_prompt: Optional[str] = None,
        memory: Optional[ConversationBufferMemory] = None
    ):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create the agent
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for tool calling."""
        return """You are a helpful assistant with access to various tools.
        
You can:
- Execute SQL queries to analyze data
- Make API calls to external services
- Provide insights and explanations

When using tools:
1. Be precise with SQL queries
2. Handle API responses appropriately
3. Explain your reasoning
4. If a tool fails, try alternative approaches

Always be helpful and accurate in your responses."""
    
    def _create_agent(self):
        """Create the OpenAI tools agent."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
    
    async def arun(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Run the tool calling chain asynchronously."""
        try:
            result = await self.agent_executor.ainvoke({
                "input": input_text,
                **kwargs
            })
            
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "input": input_text,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Tool calling chain execution failed: {e}")
            return {
                "output": "",
                "intermediate_steps": [],
                "input": input_text,
                "success": False,
                "error": str(e)
            }
    
    def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Run the tool calling chain synchronously."""
        try:
            result = self.agent_executor.invoke({
                "input": input_text,
                **kwargs
            })
            
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "input": input_text,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Tool calling chain execution failed: {e}")
            return {
                "output": "",
                "intermediate_steps": [],
                "input": input_text,
                "success": False,
                "error": str(e)
            }
    
    def get_tools(self) -> List[BaseTool]:
        """Get the tools available to this chain."""
        return self.tools
    
    def add_tool(self, tool: BaseTool):
        """Add a tool to the chain."""
        self.tools.append(tool)
        # Recreate agent with new tools
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
        logger.info(f"Added tool: {tool.name}")
    
    def remove_tool(self, tool_name: str):
        """Remove a tool from the chain."""
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        # Recreate agent with updated tools
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
        logger.info(f"Removed tool: {tool_name}")
    
    def get_memory(self) -> ConversationBufferMemory:
        """Get the memory used by this chain."""
        return self.memory
    
    def clear_memory(self):
        """Clear the conversation memory."""
        self.memory.clear()
        logger.info("Cleared conversation memory")
