"""
Unit tests for configuration loader.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from src.core.config_loader import ConfigLoader, WorkflowConfig, AgentConfig


class TestConfigLoader:
    """Test cases for ConfigLoader."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_loader = ConfigLoader(self.temp_dir)
    
    def test_load_workflow(self):
        """Test loading a workflow configuration."""
        # Create test workflow config
        workflow_config = {
            "name": "test_workflow",
            "description": "Test workflow",
            "version": "1.0.0",
            "workflow_type": "rag_chain",
            "steps": [
                {
                    "name": "retrieve",
                    "type": "retrieval",
                    "config": {"top_k": 5}
                }
            ]
        }
        
        # Write config to file
        workflow_file = Path(self.temp_dir) / "workflows" / "test_workflow.yaml"
        workflow_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_config, f)
        
        # Load and validate
        loaded_config = self.config_loader.load_workflow("test_workflow")
        
        assert loaded_config.name == "test_workflow"
        assert loaded_config.description == "Test workflow"
        assert len(loaded_config.steps) == 1
        assert loaded_config.steps[0].name == "retrieve"
    
    def test_load_agent(self):
        """Test loading an agent configuration."""
        # Create test agent config
        agent_config = {
            "name": "test_agent",
            "description": "Test agent",
            "version": "1.0.0",
            "agent_type": "tool_calling",
            "model": "gpt-4",
            "tools": ["sql_tool", "api_tool"]
        }
        
        # Write config to file
        agent_file = Path(self.temp_dir) / "agents" / "test_agent.yaml"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(agent_file, 'w') as f:
            yaml.dump(agent_config, f)
        
        # Load and validate
        loaded_config = self.config_loader.load_agent("test_agent")
        
        assert loaded_config.name == "test_agent"
        assert loaded_config.agent_type.value == "tool_calling"
        assert loaded_config.model == "gpt-4"
        assert len(loaded_config.tools) == 2
    
    def test_environment_variable_substitution(self):
        """Test environment variable substitution."""
        import os
        
        # Set environment variable
        os.environ["TEST_VAR"] = "test_value"
        
        # Create config with environment variable
        config = {
            "name": "test",
            "description": "Test with ${TEST_VAR}",
            "version": "1.0.0",
            "workflow_type": "rag_chain",
            "steps": []
        }
        
        # Test substitution
        substituted = self.config_loader._substitute_env_vars(config)
        assert substituted["description"] == "Test with test_value"
        
        # Cleanup
        del os.environ["TEST_VAR"]
    
    def test_validate_config(self):
        """Test configuration validation."""
        # Valid workflow config
        valid_config = {
            "name": "test",
            "description": "Test",
            "version": "1.0.0",
            "workflow_type": "rag_chain",
            "steps": [{"name": "test", "type": "test"}]
        }
        
        assert self.config_loader.validate_config(valid_config, "workflow")
        
        # Invalid config (missing required fields)
        invalid_config = {
            "name": "test"
        }
        
        assert not self.config_loader.validate_config(invalid_config, "workflow")
