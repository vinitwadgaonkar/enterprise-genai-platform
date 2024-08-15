"""
FastAPI main application with REST endpoints for workflow execution.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import json
import structlog
from ..core.workflow_engine import WorkflowEngine, ExecutionResult
from ..core.config_loader import config_loader
from ..core.prompt_manager import prompt_manager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enterprise GenAI Platform",
    description="A composable GenAI platform for workflows and agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global workflow engine
workflow_engine = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global workflow_engine
    
    # Initialize workflow engine
    import os
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    workflow_engine = WorkflowEngine(openai_api_key)
    logger.info("Enterprise GenAI Platform started")


# Pydantic models
class WorkflowExecutionRequest(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any]
    execution_id: Optional[str] = None


class AgentExecutionRequest(BaseModel):
    agent_id: str
    input_data: Dict[str, Any]
    execution_id: Optional[str] = None


class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int
    token_usage: Dict[str, int]


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "enterprise-genai-platform"}


# Workflow endpoints
@app.post("/api/v1/workflows/execute", response_model=ExecutionResponse)
async def execute_workflow(request: WorkflowExecutionRequest):
    """Execute a workflow."""
    try:
        result = await workflow_engine.execute_workflow(
            workflow_id=request.workflow_id,
            input_data=request.input_data,
            execution_id=request.execution_id
        )
        
        return ExecutionResponse(
            execution_id=result.execution_id,
            status=result.status.value,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
            token_usage=result.token_usage
        )
    
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows")
async def list_workflows():
    """List all available workflows."""
    try:
        workflows = config_loader.list_workflows()
        return {"workflows": workflows}
    
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow configuration."""
    try:
        workflow_config = config_loader.load_workflow(workflow_id)
        return {
            "name": workflow_config.name,
            "description": workflow_config.description,
            "version": workflow_config.version,
            "workflow_type": workflow_config.workflow_type.value,
            "steps": [step.dict() for step in workflow_config.steps]
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent endpoints
@app.post("/api/v1/agents/execute", response_model=ExecutionResponse)
async def execute_agent(request: AgentExecutionRequest):
    """Execute an agent."""
    try:
        result = await workflow_engine.execute_agent(
            agent_id=request.agent_id,
            input_data=request.input_data,
            execution_id=request.execution_id
        )
        
        return ExecutionResponse(
            execution_id=result.execution_id,
            status=result.status.value,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
            token_usage=result.token_usage
        )
    
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents")
async def list_agents():
    """List all available agents."""
    try:
        agents = config_loader.list_agents()
        return {"agents": agents}
    
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent configuration."""
    try:
        agent_config = config_loader.load_agent(agent_id)
        return {
            "name": agent_config.name,
            "description": agent_config.description,
            "version": agent_config.version,
            "agent_type": agent_config.agent_type.value,
            "model": agent_config.model,
            "tools": agent_config.tools
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Execution management endpoints
@app.get("/api/v1/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution result by ID."""
    try:
        result = workflow_engine.get_execution(execution_id)
        if not result:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return ExecutionResponse(
            execution_id=result.execution_id,
            status=result.status.value,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
            token_usage=result.token_usage
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/executions")
async def list_executions():
    """List all executions."""
    try:
        executions = workflow_engine.list_executions()
        return {
            "executions": [
                {
                    "execution_id": exec.execution_id,
                    "workflow_id": getattr(exec, 'workflow_id', None),
                    "agent_id": getattr(exec, 'agent_id', None),
                    "status": exec.status.value,
                    "execution_time_ms": exec.execution_time_ms
                }
                for exec in executions
            ]
        }
    
    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/executions/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel a running execution."""
    try:
        success = workflow_engine.cancel_execution(execution_id)
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found or not cancellable")
        
        return {"message": "Execution cancelled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Prompt template endpoints
@app.get("/api/v1/prompts")
async def list_prompt_templates():
    """List all prompt templates."""
    try:
        templates = prompt_manager.list_templates()
        return {"templates": templates}
    
    except Exception as e:
        logger.error(f"Failed to list prompt templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/prompts/{category}/{template_name}")
async def get_prompt_template(category: str, template_name: str):
    """Get a prompt template."""
    try:
        content = prompt_manager.get_template_content(category, template_name)
        if not content:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"content": content, "category": category, "template_name": template_name}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Statistics endpoint
@app.get("/api/v1/stats")
async def get_statistics():
    """Get platform statistics."""
    try:
        execution_stats = workflow_engine.get_execution_stats()
        return {
            "executions": execution_stats,
            "workflows": len(config_loader.list_workflows()),
            "agents": len(config_loader.list_agents())
        }
    
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Streaming endpoint for real-time updates
@app.get("/api/v1/executions/{execution_id}/stream")
async def stream_execution(execution_id: str):
    """Stream execution updates."""
    async def generate():
        while True:
            result = workflow_engine.get_execution(execution_id)
            if result:
                yield f"data: {json.dumps(result.__dict__)}\n\n"
                if result.status.value in ["completed", "failed", "cancelled"]:
                    break
            await asyncio.sleep(1)
    
    return StreamingResponse(generate(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
