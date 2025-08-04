"""
Distributed Tracing Library
===========================

Comprehensive distributed tracing implementation for microservices with support
for Jaeger, Zipkin, and custom tracing backends. Provides correlation ID tracking,
span management, and performance monitoring across service boundaries.

Features:
- Jaeger and Zipkin integration
- Automatic span creation and management
- Correlation ID propagation
- Performance metrics collection
- Error tracking and debugging
- Custom instrumentation support
- Async/await support

Usage:
    from libs.tracing import TracingManager, Span, trace_function
    
    # Initialize tracing
    tracing = TracingManager(
        service_name="my-service",
        jaeger_endpoint="http://localhost:14268/api/traces"
    )
    
    # Manual span creation
    with tracing.create_span("operation_name") as span:
        span.set_tag("user_id", 123)
        # Do work
        span.log("Processing completed")
    
    # Decorator-based tracing
    @trace_function("database_query")
    async def query_database():
        # Function automatically traced
        pass
"""

from .tracer import TracingManager, Span, SpanContext
from .decorators import trace_function, trace_class
from .middleware import TracingMiddleware
from .exporters import JaegerExporter, ZipkinExporter, ConsoleExporter
from .config import TracingConfig
from .utils import generate_trace_id, generate_span_id, extract_trace_context

__all__ = [
    "TracingManager",
    "Span", 
    "SpanContext",
    "trace_function",
    "trace_class",
    "TracingMiddleware",
    "JaegerExporter",
    "ZipkinExporter", 
    "ConsoleExporter",
    "TracingConfig",
    "generate_trace_id",
    "generate_span_id",
    "extract_trace_context"
]
