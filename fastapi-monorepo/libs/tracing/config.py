"""
Tracing Configuration
====================

Configuration classes for distributed tracing setup including Jaeger, Zipkin,
sampling strategies, and custom exporters.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class TracingBackend(str, Enum):
    """Supported tracing backends"""
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    CONSOLE = "console"
    CUSTOM = "custom"


class SamplingStrategy(str, Enum):
    """Sampling strategies"""
    ALWAYS = "always"
    NEVER = "never"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"
    ADAPTIVE = "adaptive"


class TracingConfig(BaseModel):
    """Distributed tracing configuration"""
    
    # Basic settings
    enabled: bool = True
    service_name: str = Field(..., description="Service name for tracing")
    service_version: str = "1.0.0"
    environment: str = "development"
    
    # Backend configuration
    backend: TracingBackend = TracingBackend.JAEGER
    
    # Jaeger settings
    jaeger_enabled: bool = True
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    jaeger_collector_endpoint: str = "http://localhost:14268/api/traces"
    jaeger_username: Optional[str] = None
    jaeger_password: Optional[str] = None
    
    # Zipkin settings
    zipkin_enabled: bool = False
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    
    # Sampling configuration
    sampling_strategy: SamplingStrategy = SamplingStrategy.PROBABILISTIC
    sampling_rate: float = Field(0.1, ge=0.0, le=1.0, description="Sampling rate (0.0 to 1.0)")
    max_traces_per_second: int = 100
    
    # Span settings
    max_span_duration: int = 300  # seconds
    max_spans_per_trace: int = 1000
    max_tag_value_length: int = 1024
    max_log_message_length: int = 2048
    
    # Headers
    trace_id_header: str = "X-Trace-ID"
    span_id_header: str = "X-Span-ID"
    parent_span_id_header: str = "X-Parent-Span-ID"
    baggage_header_prefix: str = "X-Baggage-"
    
    # Performance
    batch_size: int = 100
    flush_interval: int = 10  # seconds
    max_queue_size: int = 10000
    
    # Features
    auto_instrument_requests: bool = True
    auto_instrument_database: bool = True
    auto_instrument_cache: bool = True
    auto_instrument_external_calls: bool = True
    
    # Tags
    default_tags: Dict[str, str] = Field(default_factory=dict)
    
    # Logging
    log_spans: bool = False
    log_level: str = "INFO"
    
    class Config:
        use_enum_values = True
    
    @classmethod
    def create_jaeger_config(
        cls,
        service_name: str,
        jaeger_endpoint: str = "http://localhost:14268/api/traces",
        sampling_rate: float = 0.1
    ) -> "TracingConfig":
        """Create Jaeger configuration"""
        return cls(
            service_name=service_name,
            backend=TracingBackend.JAEGER,
            jaeger_enabled=True,
            jaeger_endpoint=jaeger_endpoint,
            sampling_rate=sampling_rate
        )
    
    @classmethod
    def create_zipkin_config(
        cls,
        service_name: str,
        zipkin_endpoint: str = "http://localhost:9411/api/v2/spans",
        sampling_rate: float = 0.1
    ) -> "TracingConfig":
        """Create Zipkin configuration"""
        return cls(
            service_name=service_name,
            backend=TracingBackend.ZIPKIN,
            zipkin_enabled=True,
            zipkin_endpoint=zipkin_endpoint,
            sampling_rate=sampling_rate
        )
    
    @classmethod
    def create_development_config(cls, service_name: str) -> "TracingConfig":
        """Create development configuration with console output"""
        return cls(
            service_name=service_name,
            backend=TracingBackend.CONSOLE,
            sampling_strategy=SamplingStrategy.ALWAYS,
            log_spans=True
        )
