"""
Prometheus metrics collection and export.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from typing import Dict, Any, Optional
import time
import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects and exports Prometheus metrics."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        # Request metrics
        self.request_count = Counter(
            'genai_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'genai_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # LLM metrics
        self.llm_requests = Counter(
            'genai_llm_requests_total',
            'Total LLM requests',
            ['model', 'operation'],
            registry=self.registry
        )
        
        self.llm_tokens = Counter(
            'genai_llm_tokens_total',
            'Total LLM tokens',
            ['model', 'type'],
            registry=self.registry
        )
        
        self.llm_cost = Counter(
            'genai_llm_cost_total',
            'Total LLM cost in USD',
            ['model'],
            registry=self.registry
        )
        
        # Vector store metrics
        self.vector_operations = Counter(
            'genai_vector_operations_total',
            'Total vector operations',
            ['operation', 'store_type'],
            registry=self.registry
        )
        
        self.vector_search_duration = Histogram(
            'genai_vector_search_duration_seconds',
            'Vector search duration',
            ['store_type'],
            registry=self.registry
        )
        
        # Tool metrics
        self.tool_executions = Counter(
            'genai_tool_executions_total',
            'Total tool executions',
            ['tool_name', 'status'],
            registry=self.registry
        )
        
        self.tool_duration = Histogram(
            'genai_tool_duration_seconds',
            'Tool execution duration',
            ['tool_name'],
            registry=self.registry
        )
        
        # Workflow metrics
        self.workflow_executions = Counter(
            'genai_workflow_executions_total',
            'Total workflow executions',
            ['workflow_id', 'status'],
            registry=self.registry
        )
        
        self.workflow_duration = Histogram(
            'genai_workflow_duration_seconds',
            'Workflow execution duration',
            ['workflow_id'],
            registry=self.registry
        )
        
        # System metrics
        self.active_executions = Gauge(
            'genai_active_executions',
            'Number of active executions',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'genai_memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        # Info metric
        self.service_info = Info(
            'genai_service_info',
            'Service information',
            registry=self.registry
        )
        self.service_info.info({
            'version': '1.0.0',
            'service': 'enterprise-genai-platform'
        })
    
    def record_request(self, method: str, endpoint: str, status: str, duration: float):
        """Record a request metric."""
        self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_llm_request(self, model: str, operation: str, tokens: int, cost: float):
        """Record LLM metrics."""
        self.llm_requests.labels(model=model, operation=operation).inc()
        self.llm_tokens.labels(model=model, type='total').inc(tokens)
        self.llm_cost.labels(model=model).inc(cost)
    
    def record_vector_operation(self, operation: str, store_type: str, duration: float):
        """Record vector operation metrics."""
        self.vector_operations.labels(operation=operation, store_type=store_type).inc()
        if operation == 'search':
            self.vector_search_duration.labels(store_type=store_type).observe(duration)
    
    def record_tool_execution(self, tool_name: str, status: str, duration: float):
        """Record tool execution metrics."""
        self.tool_executions.labels(tool_name=tool_name, status=status).inc()
        self.tool_duration.labels(tool_name=tool_name).observe(duration)
    
    def record_workflow_execution(self, workflow_id: str, status: str, duration: float):
        """Record workflow execution metrics."""
        self.workflow_executions.labels(workflow_id=workflow_id, status=status).inc()
        self.workflow_duration.labels(workflow_id=workflow_id).observe(duration)
    
    def set_active_executions(self, count: int):
        """Set the number of active executions."""
        self.active_executions.set(count)
    
    def set_memory_usage(self, bytes_used: int):
        """Set memory usage."""
        self.memory_usage.set(bytes_used)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as a dictionary."""
        # This is a simplified version - in practice, you'd parse the Prometheus format
        return {
            'request_count': 'See /metrics endpoint for detailed metrics',
            'llm_metrics': 'See /metrics endpoint for detailed metrics',
            'vector_metrics': 'See /metrics endpoint for detailed metrics',
            'tool_metrics': 'See /metrics endpoint for detailed metrics',
            'workflow_metrics': 'See /metrics endpoint for detailed metrics'
        }


# Global metrics collector
metrics_collector = MetricsCollector()
