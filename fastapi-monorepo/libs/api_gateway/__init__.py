"""
API Gateway Library for Microservices
=====================================

This library provides a comprehensive API Gateway implementation for FastAPI microservices
with advanced features including routing, load balancing, authentication, rate limiting,
and request/response transformation.

Features:
- Dynamic routing and service discovery
- Load balancing with multiple algorithms
- JWT authentication and authorization
- Rate limiting and throttling
- Request/response transformation
- Health checking and circuit breaker integration
- Metrics collection and monitoring
- CORS handling
- Request logging and tracing

Usage:
    from libs.api_gateway import APIGateway, GatewayConfig, RouteConfig
    
    # Create gateway configuration
    config = GatewayConfig(
        host="0.0.0.0",
        port=8000,
        enable_auth=True,
        enable_rate_limiting=True
    )
    
    # Define routes
    routes = [
        RouteConfig(
            path="/api/v1/auth/*",
            service_name="auth",
            upstream_url="http://localhost:8001"
        ),
        RouteConfig(
            path="/api/v1/products/*",
            service_name="products", 
            upstream_url="http://localhost:8003"
        )
    ]
    
    # Create and start gateway
    gateway = APIGateway(config, routes)
    await gateway.start()
"""

from .gateway import APIGateway
from .config import GatewayConfig, RouteConfig, LoadBalancerConfig
from .middleware import (
    AuthenticationMiddleware,
    RateLimitingMiddleware,
    CORSMiddleware,
    TracingMiddleware
)
from .load_balancer import LoadBalancer, LoadBalancingAlgorithm
from .health_checker import HealthChecker
from .metrics import GatewayMetrics

__all__ = [
    "APIGateway",
    "GatewayConfig", 
    "RouteConfig",
    "LoadBalancerConfig",
    "AuthenticationMiddleware",
    "RateLimitingMiddleware", 
    "CORSMiddleware",
    "TracingMiddleware",
    "LoadBalancer",
    "LoadBalancingAlgorithm",
    "HealthChecker",
    "GatewayMetrics"
]
