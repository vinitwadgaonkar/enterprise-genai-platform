"""
OpenTelemetry tracing configuration and instrumentation.
"""

import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
import structlog

logger = structlog.get_logger(__name__)


def setup_tracing(service_name: str = "enterprise-genai-platform"):
    """Setup OpenTelemetry tracing."""
    try:
        # Create resource
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development")
        })
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Create OTLP exporter
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        
        # Create span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Instrument libraries
        FastAPIInstrumentor.instrument()
        Psycopg2Instrumentor().instrument()
        OpenAIInstrumentor().instrument()
        
        logger.info(f"OpenTelemetry tracing configured for {service_name}")
        return tracer_provider
    
    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}")
        raise


def get_tracer(name: str):
    """Get a tracer instance."""
    return trace.get_tracer(name)


def create_span(tracer, name: str, **attributes):
    """Create a new span."""
    span = tracer.start_span(name)
    for key, value in attributes.items():
        span.set_attribute(key, value)
    return span


def add_span_event(span, name: str, **attributes):
    """Add an event to a span."""
    span.add_event(name, attributes)


def set_span_status(span, status_code: str, description: str = None):
    """Set the status of a span."""
    from opentelemetry.trace import Status, StatusCode
    
    if status_code == "OK":
        span.set_status(Status(StatusCode.OK))
    elif status_code == "ERROR":
        span.set_status(Status(StatusCode.ERROR, description))
    else:
        span.set_status(Status(StatusCode.UNSET, description))
