"""
Configuration loader for workflows and agents.
Supports YAML-based configuration with validation and environment overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class WorkflowType(str, Enum):
    RAG_CHAIN = "rag_chain"
    TOOL_CALLING = "tool_calling"
    CONVERSATIONAL = "conversational"
    SEQUENTIAL = "sequential"


class AgentType(str, Enum):
    TOOL_CALLING = "tool_calling"
    CONVERSATIONAL = "conversational"
    REACT = "react"


class MemoryType(str, Enum):
    CONVERSATION_BUFFER = "conversation_buffer"
    SUMMARY = "summary"
    ENTITY = "entity"


class StepConfig(BaseModel):
    name: str
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    condition: Optional[str] = None
    retry_count: int = 3
    timeout_seconds: int = 30


class WorkflowConfig(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    workflow_type: WorkflowType
    steps: List[StepConfig]
    prompts: Dict[str, str] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)
    memory: Optional[Dict[str, Any]] = None
    token_budget: Optional[int] = None
    max_retries: int = 3
    timeout_seconds: int = 300

    @validator('steps')
    def validate_steps(cls, v):
        if not v:
            raise ValueError("Workflow must have at least one step")
        return v


class AgentConfig(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    agent_type: AgentType
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    tools: List[str] = Field(default_factory=list)
    prompts: Dict[str, str] = Field(default_factory=dict)
    memory: Optional[Dict[str, Any]] = None
    token_budget: Optional[int] = None


class ConfigLoader:
    """Loads and validates workflow and agent configurations from YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.workflows_dir = self.config_dir / "workflows"
        self.agents_dir = self.config_dir / "agents"
        
        # Ensure directories exist
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)
    
    def load_workflow(self, workflow_id: str) -> WorkflowConfig:
        """Load a workflow configuration from YAML file."""
        workflow_file = self.workflows_dir / f"{workflow_id}.yaml"
        
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow config not found: {workflow_file}")
        
        with open(workflow_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Apply environment variable substitution
        config_data = self._substitute_env_vars(config_data)
        
        return WorkflowConfig(**config_data)
    
    def load_agent(self, agent_id: str) -> AgentConfig:
        """Load an agent configuration from YAML file."""
        agent_file = self.agents_dir / f"{agent_id}.yaml"
        
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent config not found: {agent_file}")
        
        with open(agent_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Apply environment variable substitution
        config_data = self._substitute_env_vars(config_data)
        
        return AgentConfig(**config_data)
    
    def list_workflows(self) -> List[str]:
        """List all available workflow IDs."""
        return [f.stem for f in self.workflows_dir.glob("*.yaml")]
    
    def list_agents(self) -> List[str]:
        """List all available agent IDs."""
        return [f.stem for f in self.agents_dir.glob("*.yaml")]
    
    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute environment variables in configuration data."""
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        else:
            return data
    
    def validate_config(self, config: Dict[str, Any], config_type: str) -> bool:
        """Validate configuration data against schema."""
        try:
            if config_type == "workflow":
                WorkflowConfig(**config)
            elif config_type == "agent":
                AgentConfig(**config)
            else:
                raise ValueError(f"Unknown config type: {config_type}")
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False


# Global config loader instance
config_loader = ConfigLoader()
