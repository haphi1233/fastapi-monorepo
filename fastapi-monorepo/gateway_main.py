#!/usr/bin/env python3
"""
API Gateway Startup Script
==========================

Khởi động API Gateway để tổng hợp tất cả các microservices
"""
import asyncio
import uvicorn
from typing import Dict, Any

from libs.api_gateway.config import (
    GatewayConfig, 
    RouteConfig, 
    ServiceInstance,
    LoadBalancerConfig,
    RateLimitConfig,
    CORSConfig,
    TracingConfig,
    AuthConfig,
    MetricsConfig
)
from libs.api_gateway.gateway import APIGateway

def create_gateway_config() -> GatewayConfig:
    """Tạo cấu hình API Gateway"""
    
    # Service instances
    auth_instances = [
        ServiceInstance(
            host="localhost",
            port=8001,
            healthy=True,
            weight=1
        )
    ]
    
    articles_instances = [
        ServiceInstance(
            host="localhost",
            port=8002, 
            healthy=True,
            weight=1
        )
    ]
    
    products_instances = [
        ServiceInstance(
            host="localhost",
            port=8003,
            healthy=True,
            weight=1
        )
    ]
    
    # Route configurations
    routes = [
        # Auth Service routes
        RouteConfig(
            path="/api/v1/auth/*",
            service_name="auth-service",
            upstream_instances=auth_instances,
            strip_path_prefix=True,
            connect_timeout=30.0,
            max_retries=3
        ),
        RouteConfig(
            path="/auth/*",
            service_name="auth-service", 
            upstream_instances=auth_instances,
            strip_path_prefix=True,
            connect_timeout=30.0,
            max_retries=3
        ),
        
        # Articles Service routes
        RouteConfig(
            path="/api/v1/articles/*",
            service_name="articles-service",
            upstream_instances=articles_instances,
            strip_path_prefix=True,
            connect_timeout=30.0,
            max_retries=3
        ),
        RouteConfig(
            path="/articles/*",
            service_name="articles-service",
            upstream_instances=articles_instances, 
            strip_path_prefix=True,
            connect_timeout=30.0,
            max_retries=3
        ),
        
        # Products Service routes
        RouteConfig(
            path="/api/v1/products/*",
            service_name="products-service",
            upstream_instances=products_instances,
            strip_path_prefix=True,
            connect_timeout=30.0,
            max_retries=3
        ),
        RouteConfig(
            path="/products/*",
            service_name="products-service",
            upstream_instances=products_instances,
            strip_path_prefix=True,
            connect_timeout=30.0,
            max_retries=3
        )
    ]
    
    # Gateway configuration
    config = GatewayConfig(
        host="0.0.0.0",
        port=8080,
        routes=routes,
        
        # Load balancer config
        load_balancer=LoadBalancerConfig(
            algorithm="round_robin",
            health_check_enabled=True,
            health_check_interval=30,
            health_check_timeout=5,
            health_check_path="/health"
        ),
        
        # Rate limiting config
        rate_limiting=RateLimitConfig(
            enabled=True,
            default_rpm=1000,
            default_burst=100
        ),
        
        # CORS config
        cors=CORSConfig(
            enabled=True,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True
        ),
        
        # Tracing config
        tracing=TracingConfig(
            enabled=True,
            service_name="api-gateway",
            jaeger_endpoint="http://localhost:14268/api/traces"
        ),
        
        # Auth config
        auth=AuthConfig(
            enabled=False,  # Disable gateway-level auth, let services handle it
            jwt_secret="your-secret-key",
            jwt_algorithm="HS256"
        ),
        
        # Metrics config
        metrics=MetricsConfig(
            enabled=True,
            endpoint="/metrics",
            include_request_duration=True,
            include_request_count=True,
            include_error_rate=True
        )
    )
    
    return config

async def main():
    """Main function"""
    print("🚀 Starting API Gateway...")
    print("=" * 50)
    
    # Create gateway config
    config = create_gateway_config()
    
    # Create gateway instance
    gateway = APIGateway(config)
    
    # Start gateway
    await gateway.start()
    
    print(f"✅ API Gateway started successfully!")
    print(f"🌐 Gateway URL: http://{config.host}:{config.port}")
    print(f"📊 Health Check: http://{config.host}:{config.port}/health")
    print(f"📈 Metrics: http://{config.host}:{config.port}/metrics")
    print("\n🔗 Available Service Routes:")
    print("   • Auth Service: http://localhost:8001/auth/* or /api/v1/auth/*")
    print("   • Articles Service: http://localhost:8002/articles/* or /api/v1/articles/*") 
    print("   • Products Service: http://localhost:8003/products/* or /api/v1/products/*")
    print("\n📚 API Documentation:")
    print(f"   • Gateway Docs: http://{config.host}:{config.port}/docs")
    print("   • Auth Docs: http://localhost:8001/docs")
    print("   • Articles Docs: http://localhost:8002/docs")
    print("   • Products Docs: http://localhost:8003/docs")
    
    # Run with uvicorn
    uvicorn_config = uvicorn.Config(
        app=gateway.app,
        host=config.host,
        port=config.port,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(uvicorn_config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
