"""
Workflow engine that orchestrates chains based on YAML configurations.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import structlog
from .config_loader import WorkflowConfig, AgentConfig, config_loader
from .prompt_manager import prompt_manager
from ..chains.rag_chain import RAGChain
from ..chains.tool_calling_chain import ToolCallingChain
from ..chains.memory_chain import MemoryChain
from ..tools.base import tool_registry
from ..utils.token_counter import TokenCounter

logger = structlog.get_logger(__name__)


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of workflow execution."""
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    output: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    token_usage: Dict[str, int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.token_usage is None:
            self.token_usage = {}
        if self.metadata is None:
            self.metadata = {}


class WorkflowEngine:
    """Engine for executing workflows and agents."""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.token_counter = TokenCounter()
        self.executions: Dict[str, ExecutionResult] = {}
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        input_data: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> ExecutionResult:
        """Execute a workflow based on its configuration."""
        if execution_id is None:
            execution_id = str(uuid.uuid4())
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Load workflow configuration
            workflow_config = config_loader.load_workflow(workflow_id)
            
            # Create execution result
            result = ExecutionResult(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.RUNNING,
                output=None
            )
            self.executions[execution_id] = result
            
            # Execute workflow steps
            output = await self._execute_workflow_steps(workflow_config, input_data)
            
            # Calculate execution time
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Update result
            result.status = ExecutionStatus.COMPLETED
            result.output = output
            result.execution_time_ms = execution_time
            result.token_usage = self.token_counter.get_usage()
            
            logger.info(f"Workflow {workflow_id} completed in {execution_time}ms")
            return result
        
        except Exception as e:
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            result = ExecutionResult(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.FAILED,
                output=None,
                error=str(e),
                execution_time_ms=execution_time,
                token_usage=self.token_counter.get_usage()
            )
            self.executions[execution_id] = result
            
            logger.error(f"Workflow {workflow_id} failed: {e}")
            return result
    
    async def execute_agent(
        self, 
        agent_id: str, 
        input_data: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> ExecutionResult:
        """Execute an agent based on its configuration."""
        if execution_id is None:
            execution_id = str(uuid.uuid4())
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Load agent configuration
            agent_config = config_loader.load_agent(agent_id)
            
            # Create execution result
            result = ExecutionResult(
                execution_id=execution_id,
                agent_id=agent_id,
                status=ExecutionStatus.RUNNING,
                output=None
            )
            self.executions[execution_id] = result
            
            # Execute agent
            output = await self._execute_agent(agent_config, input_data)
            
            # Calculate execution time
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Update result
            result.status = ExecutionStatus.COMPLETED
            result.output = output
            result.execution_time_ms = execution_time
            result.token_usage = self.token_counter.get_usage()
            
            logger.info(f"Agent {agent_id} completed in {execution_time}ms")
            return result
        
        except Exception as e:
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            result = ExecutionResult(
                execution_id=execution_id,
                agent_id=agent_id,
                status=ExecutionStatus.FAILED,
                output=None,
                error=str(e),
                execution_time_ms=execution_time,
                token_usage=self.token_counter.get_usage()
            )
            self.executions[execution_id] = result
            
            logger.error(f"Agent {agent_id} failed: {e}")
            return result
    
    async def _execute_workflow_steps(
        self, 
        workflow_config: WorkflowConfig, 
        input_data: Dict[str, Any]
    ) -> Any:
        """Execute workflow steps in sequence."""
        context = input_data.copy()
        
        for step in workflow_config.steps:
            try:
                # Execute step
                step_result = await self._execute_step(step, context)
                
                # Update context with step result
                context[step.name] = step_result
                
                logger.info(f"Executed step: {step.name}")
            
            except Exception as e:
                logger.error(f"Step {step.name} failed: {e}")
                raise
        
        return context
    
    async def _execute_step(self, step_config, context: Dict[str, Any]) -> Any:
        """Execute a single workflow step."""
        step_type = step_config.type
        
        if step_type == "retrieval":
            return await self._execute_retrieval_step(step_config, context)
        elif step_type == "llm_call":
            return await self._execute_llm_step(step_config, context)
        elif step_type == "tool_call":
            return await self._execute_tool_step(step_config, context)
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def _execute_retrieval_step(self, step_config, context: Dict[str, Any]) -> Any:
        """Execute a retrieval step."""
        # This would integrate with the vector store and retrieval system
        # For now, return a placeholder
        return {"retrieved_documents": [], "step": "retrieval"}
    
    async def _execute_llm_step(self, step_config, context: Dict[str, Any]) -> Any:
        """Execute an LLM call step."""
        # This would integrate with the LLM and prompt system
        # For now, return a placeholder
        return {"llm_response": "Generated response", "step": "llm_call"}
    
    async def _execute_tool_step(self, step_config, context: Dict[str, Any]) -> Any:
        """Execute a tool call step."""
        tool_name = step_config.config.get("tool_name")
        tool_params = step_config.config.get("params", {})
        
        # Get tool from registry
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Execute tool
        result = await tool.execute(**tool_params)
        return result
    
    async def _execute_agent(self, agent_config: AgentConfig, input_data: Dict[str, Any]) -> Any:
        """Execute an agent."""
        # This would create and execute the appropriate agent type
        # For now, return a placeholder
        return {"agent_response": "Agent executed", "agent_type": agent_config.agent_type}
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution result by ID."""
        return self.executions.get(execution_id)
    
    def list_executions(self) -> List[ExecutionResult]:
        """List all executions."""
        return list(self.executions.values())
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        executions = self.list_executions()
        
        if not executions:
            return {"total": 0}
        
        status_counts = {}
        for execution in executions:
            status = execution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_time = sum(execution.execution_time_ms for execution in executions)
        avg_time = total_time / len(executions) if executions else 0
        
        return {
            "total": len(executions),
            "status_counts": status_counts,
            "average_execution_time_ms": avg_time,
            "total_execution_time_ms": total_time
        }
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        execution = self.get_execution(execution_id)
        if execution and execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.CANCELLED
            logger.info(f"Cancelled execution: {execution_id}")
            return True
        return False
