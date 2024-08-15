"""
Structured logging configuration with correlation IDs.
"""

import structlog
import logging
import sys
from typing import Any, Dict, Optional
import uuid
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id.get()


def set_correlation_id(corr_id: str):
    """Set the correlation ID."""
    correlation_id.set(corr_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup structured logging."""
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add correlation ID processor
    processors.append(add_correlation_id)
    
    # Choose output format
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Set log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    logger = structlog.get_logger(__name__)
    logger.info("Structured logging configured", log_level=log_level, format=log_format)


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log events."""
    corr_id = get_correlation_id()
    if corr_id:
        event_dict["correlation_id"] = corr_id
    return event_dict


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(name)


class LoggingMiddleware:
    """Middleware for adding correlation IDs to requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate correlation ID for each request
            corr_id = generate_correlation_id()
            set_correlation_id(corr_id)
            
            # Add to request headers
            headers = dict(scope.get("headers", []))
            headers[b"x-correlation-id"] = corr_id.encode()
            scope["headers"] = [(k, v) for k, v in headers.items()]
        
        await self.app(scope, receive, send)


def log_execution_start(execution_id: str, workflow_id: str, input_data: Dict[str, Any]):
    """Log the start of an execution."""
    logger = get_logger(__name__)
    logger.info(
        "Execution started",
        execution_id=execution_id,
        workflow_id=workflow_id,
        input_keys=list(input_data.keys())
    )


def log_execution_end(execution_id: str, status: str, duration_ms: int, token_usage: Dict[str, int]):
    """Log the end of an execution."""
    logger = get_logger(__name__)
    logger.info(
        "Execution completed",
        execution_id=execution_id,
        status=status,
        duration_ms=duration_ms,
        token_usage=token_usage
    )


def log_execution_error(execution_id: str, error: str, duration_ms: int):
    """Log an execution error."""
    logger = get_logger(__name__)
    logger.error(
        "Execution failed",
        execution_id=execution_id,
        error=error,
        duration_ms=duration_ms
    )


def log_llm_call(model: str, operation: str, tokens: int, cost: float):
    """Log an LLM call."""
    logger = get_logger(__name__)
    logger.info(
        "LLM call",
        model=model,
        operation=operation,
        tokens=tokens,
        cost=cost
    )


def log_vector_operation(operation: str, store_type: str, duration_ms: int, result_count: int):
    """Log a vector operation."""
    logger = get_logger(__name__)
    logger.info(
        "Vector operation",
        operation=operation,
        store_type=store_type,
        duration_ms=duration_ms,
        result_count=result_count
    )


def log_tool_execution(tool_name: str, status: str, duration_ms: int):
    """Log a tool execution."""
    logger = get_logger(__name__)
    logger.info(
        "Tool execution",
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms
    )
