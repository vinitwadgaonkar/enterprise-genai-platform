"""
Token counting and budgeting utilities.
"""

import tiktoken
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class TokenCounter:
    """Utility for counting tokens and managing budgets."""
    
    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)
        self.usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def count_tokens_batch(self, texts: list[str]) -> list[int]:
        """Count tokens for multiple texts."""
        return [self.count_tokens(text) for text in texts]
    
    def add_usage(self, prompt_tokens: int, completion_tokens: int):
        """Add token usage to the counter."""
        self.usage["prompt_tokens"] += prompt_tokens
        self.usage["completion_tokens"] += completion_tokens
        self.usage["total_tokens"] += prompt_tokens + completion_tokens
    
    def get_usage(self) -> Dict[str, int]:
        """Get current token usage."""
        return self.usage.copy()
    
    def reset_usage(self):
        """Reset token usage."""
        self.usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    
    def estimate_cost(self, model: Optional[str] = None) -> Dict[str, float]:
        """Estimate cost based on token usage."""
        model = model or self.model
        
        # OpenAI pricing (as of 2024)
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "text-embedding-3-large": {"input": 0.00013}
        }
        
        if model not in pricing:
            logger.warning(f"Unknown model for pricing: {model}")
            return {"estimated_cost": 0.0}
        
        input_cost = (self.usage["prompt_tokens"] / 1000) * pricing[model]["input"]
        output_cost = (self.usage["completion_tokens"] / 1000) * pricing[model]["output"]
        total_cost = input_cost + output_cost
        
        return {
            "estimated_cost": total_cost,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "model": model
        }
