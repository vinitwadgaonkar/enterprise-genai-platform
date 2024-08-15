"""
Base classes for tool implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(self, name: str, description: str, **kwargs):
        self.name = name
        self.description = description
        self.config = kwargs
        self.logger = structlog.get_logger(name=name)
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for tool parameters."""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters against schema."""
        try:
            schema = self.get_schema()
            # Basic validation - in practice, you'd use jsonschema
            required_params = schema.get('required', [])
            for param in required_params:
                if param not in parameters:
                    self.logger.error(f"Missing required parameter: {param}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Parameter validation failed: {e}")
            return False
    
    def get_description(self) -> str:
        """Get tool description."""
        return self.description
    
    def get_name(self) -> str:
        """Get tool name."""
        return self.name


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool."""
        self.tools[tool.get_name()] = tool
        logger.info(f"Registered tool: {tool.get_name()}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())
    
    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get schemas for all registered tools."""
        return {
            name: tool.get_schema() 
            for name, tool in self.tools.items()
        }
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{name}' not found"
            )
        
        try:
            if not tool.validate_parameters(kwargs):
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Invalid parameters for tool '{name}'"
                )
            
            return tool.execute(**kwargs)
        
        except Exception as e:
            logger.error(f"Tool execution failed for '{name}': {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


# Global tool registry
tool_registry = ToolRegistry()
