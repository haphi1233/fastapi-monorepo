"""
API Gateway Configuration
========================

Configuration classes for API Gateway setup including routes, load balancing,
authentication, rate limiting, and other gateway features.
"""

from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass


class LoadBalancingAlgorithm(str, Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    RANDOM = "random"


class HealthCheckMethod(str, Enum):
    """Health check methods"""
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    TCP_CONNECT = "tcp_connect"
    CUSTOM = "custom"


@dataclass
class ServiceInstance:
    """Service instance configuration"""
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    last_health_check: Optional[float] = None
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class RouteConfig(BaseModel):
    """Route configuration for API Gateway"""
    
    path: str = Field(..., description="Route path pattern (supports wildcards)")
    service_name: str = Field(..., description="Target service name")
    upstream_instances: List[ServiceInstance] = Field(default_factory=list, description="Service instances")
    
    # Load balancing
    load_balancing_algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN
    
    # Authentication
    require_auth: bool = True
    allowed_roles: Optional[List[str]] = None
    
    # Rate limiting
    rate_limit_rpm: Optional[int] = None  # Requests per minute
    rate_limit_burst: Optional[int] = None  # Burst capacity
    
    # Timeouts
    connect_timeout: float = 30.0
    read_timeout: float = 60.0
    
    # Retry policy
    max_retries: int = 3
    retry_backoff: float = 1.0
    
    # Health checking
    health_check_enabled: bool = True
    health_check_path: str = "/health"
    health_check_interval: int = 30  # seconds
    health_check_timeout: int = 10   # seconds
    
    # Request transformation
    strip_path_prefix: bool = True
    add_headers: Dict[str, str] = Field(default_factory=dict)
    remove_headers: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration"""
    
    algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN
    health_check_enabled: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 10
    health_check_method: HealthCheckMethod = HealthCheckMethod.HTTP_GET
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: int = 60
    
    # Sticky sessions
    sticky_sessions: bool = False
    session_cookie_name: str = "gateway_session"


class AuthConfig(BaseModel):
    """Authentication configuration"""
    
    enabled: bool = True
    jwt_secret: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600  # seconds
    
    # Auth service
    auth_service_url: str = "http://localhost:8001/api/v1"
    auth_cache_ttl: int = 300  # seconds
    
    # Public paths (no auth required)
    public_paths: List[str] = Field(default_factory=lambda: [
        "/health",
        "/metrics",
        "/api/v1/auth/login",
        "/api/v1/auth/register"
    ])


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    
    enabled: bool = True
    default_rpm: int = 1000  # Requests per minute
    default_burst: int = 100  # Burst capacity
    
    # Storage backend
    storage_type: str = "redis"  # redis, memory
    redis_url: str = "redis://localhost:6379"
    
    # Rate limit by
    by_ip: bool = True
    by_user: bool = True
    by_service: bool = True
    
    # Custom rate limits
    custom_limits: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class CORSConfig(BaseModel):
    """CORS configuration"""
    
    enabled: bool = True
    allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    allow_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    max_age: int = 86400  # seconds


class TracingConfig(BaseModel):
    """Distributed tracing configuration"""
    
    enabled: bool = True
    service_name: str = "api-gateway"
    
    # Jaeger configuration
    jaeger_enabled: bool = True
    jaeger_host: str = "localhost"
    jaeger_port: int = 14268
    jaeger_endpoint: str = "/api/traces"
    
    # Sampling
    sampling_rate: float = 0.1  # 10% sampling
    
    # Headers
    trace_header: str = "X-Trace-ID"
    span_header: str = "X-Span-ID"


class MetricsConfig(BaseModel):
    """Metrics configuration"""
    
    enabled: bool = True
    endpoint: str = "/metrics"
    
    # Prometheus configuration
    prometheus_enabled: bool = True
    
    # Custom metrics
    collect_request_duration: bool = True
    collect_request_count: bool = True
    collect_error_count: bool = True
    collect_active_connections: bool = True


class GatewayConfig(BaseModel):
    """Main API Gateway configuration"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Service discovery
    service_discovery_enabled: bool = True
    service_registry_url: str = "http://localhost:8500"  # Consul
    
    # Feature configurations
    auth: AuthConfig
    rate_limiting: RateLimitConfig
    cors: CORSConfig
    tracing: TracingConfig
    metrics: MetricsConfig
    load_balancer: LoadBalancerConfig
    
    # Routes
    routes: List[RouteConfig] = Field(default_factory=list)
    
    # Logging
    log_level: str = "INFO"
    access_log_enabled: bool = True
    access_log_format: str = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    
    # Performance
    max_connections: int = 1000
    keepalive_timeout: int = 65
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def create_default(cls) -> "GatewayConfig":
        """Create default gateway configuration"""
        return cls(
            auth=AuthConfig(
                jwt_secret="your-secret-key-change-in-production"
            ),
            rate_limiting=RateLimitConfig(),
            cors=CORSConfig(),
            tracing=TracingConfig(),
            metrics=MetricsConfig(),
            load_balancer=LoadBalancerConfig()
        )
