"""
Prompt template manager for system, user, and critique templates.
Supports Jinja2 templating with variable interpolation and template inheritance.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
import structlog

logger = structlog.get_logger(__name__)


class PromptManager:
    """Manages prompt templates with Jinja2 templating support."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.system_dir = self.prompts_dir / "system"
        self.user_dir = self.prompts_dir / "user"
        self.critique_dir = self.prompts_dir / "critique"
        
        # Ensure directories exist
        for dir_path in [self.system_dir, self.user_dir, self.critique_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def get_system_prompt(self, template_name: str, **kwargs) -> str:
        """Get a system prompt template with variable substitution."""
        return self._get_prompt("system", template_name, **kwargs)
    
    def get_user_prompt(self, template_name: str, **kwargs) -> str:
        """Get a user prompt template with variable substitution."""
        return self._get_prompt("user", template_name, **kwargs)
    
    def get_critique_prompt(self, template_name: str, **kwargs) -> str:
        """Get a critique prompt template with variable substitution."""
        return self._get_prompt("critique", template_name, **kwargs)
    
    def _get_prompt(self, category: str, template_name: str, **kwargs) -> str:
        """Get a prompt template with variable substitution."""
        try:
            # Add .j2 extension if not present
            if not template_name.endswith('.j2'):
                template_name += '.j2'
            
            template_path = f"{category}/{template_name}"
            template = self.jinja_env.get_template(template_path)
            
            # Add default variables
            context = {
                'category': category,
                'template_name': template_name,
                **kwargs
            }
            
            return template.render(**context)
        
        except TemplateNotFound:
            logger.error(f"Template not found: {template_path}")
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {e}")
            raise
    
    def list_templates(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List all available templates, optionally filtered by category."""
        templates = {
            'system': [],
            'user': [],
            'critique': []
        }
        
        if category:
            categories = [category]
        else:
            categories = ['system', 'user', 'critique']
        
        for cat in categories:
            dir_path = getattr(self, f"{cat}_dir")
            templates[cat] = [f.stem for f in dir_path.glob("*.j2")]
        
        return templates
    
    def validate_template(self, category: str, template_name: str) -> bool:
        """Validate that a template exists and can be rendered."""
        try:
            if not template_name.endswith('.j2'):
                template_name += '.j2'
            
            template_path = f"{category}/{template_name}"
            template = self.jinja_env.get_template(template_path)
            
            # Try to render with empty context to check syntax
            template.render()
            return True
        
        except Exception as e:
            logger.error(f"Template validation failed for {template_path}: {e}")
            return False
    
    def create_template(self, category: str, template_name: str, content: str) -> bool:
        """Create a new prompt template."""
        try:
            if not template_name.endswith('.j2'):
                template_name += '.j2'
            
            template_path = getattr(self, f"{category}_dir") / template_name
            
            with open(template_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Created template: {template_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create template {template_path}: {e}")
            return False
    
    def get_template_content(self, category: str, template_name: str) -> Optional[str]:
        """Get the raw content of a template."""
        try:
            if not template_name.endswith('.j2'):
                template_name += '.j2'
            
            template_path = getattr(self, f"{category}_dir") / template_name
            
            with open(template_path, 'r') as f:
                return f.read()
        
        except FileNotFoundError:
            logger.error(f"Template not found: {template_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading template {template_path}: {e}")
            return None
    
    def update_template(self, category: str, template_name: str, content: str) -> bool:
        """Update an existing prompt template."""
        return self.create_template(category, template_name, content)
    
    def delete_template(self, category: str, template_name: str) -> bool:
        """Delete a prompt template."""
        try:
            if not template_name.endswith('.j2'):
                template_name += '.j2'
            
            template_path = getattr(self, f"{category}_dir") / template_name
            
            if template_path.exists():
                template_path.unlink()
                logger.info(f"Deleted template: {template_path}")
                return True
            else:
                logger.warning(f"Template not found for deletion: {template_path}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete template {template_path}: {e}")
            return False


# Global prompt manager instance
prompt_manager = PromptManager()
