"""
API Gateway Main Implementation
==============================

Main API Gateway class that orchestrates all components including routing,
load balancing, middleware, health checking, and metrics collection.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

from .config import GatewayConfig, RouteConfig, ServiceInstance
from .load_balancer import LoadBalancer, StickySessionManager
from .middleware import (
    AuthenticationMiddleware,
    RateLimitingMiddleware,
    CORSMiddleware,
    TracingMiddleware,
    RequestTransformationMiddleware
)
from .health_checker import HealthChecker
from .metrics import GatewayMetrics
from .openapi_aggregator import OpenAPIAggregator

logger = logging.getLogger(__name__)


class APIGateway:
    """Main API Gateway implementation"""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.app = FastAPI(
            title="API Gateway",
            description="Advanced API Gateway for Microservices",
            version="1.0.0"
        )
        
        # Core components
        self.load_balancer = LoadBalancer(
            algorithm=config.load_balancer.algorithm,
            health_check_enabled=config.load_balancer.health_check_enabled
        )
        self.sticky_session_manager = StickySessionManager()
        self.health_checker = HealthChecker(config.load_balancer)
        self.metrics = GatewayMetrics(config.metrics)
        self.openapi_aggregator = OpenAPIAggregator()
        
        # HTTP client for upstream requests
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Route configurations
        self.routes: Dict[str, RouteConfig] = {}
        for route in config.routes:
            self.routes[route.path] = route
        
        # Initialize components
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("API Gateway initialized")
    
    def _setup_middleware(self) -> None:
        """Setup middleware stack"""
        
        # CORS middleware (first)
        if self.config.cors.enabled:
            from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
            self.app.add_middleware(
                StarletteCORSMiddleware,
                allow_origins=self.config.cors.allow_origins,
                allow_credentials=self.config.cors.allow_credentials,
                allow_methods=self.config.cors.allow_methods,
                allow_headers=self.config.cors.allow_headers,
                max_age=self.config.cors.max_age
            )
        
        # Tracing middleware
        if self.config.tracing.enabled:
            self.app.add_middleware(TracingMiddleware, config=self.config.tracing)
        
        # Authentication middleware
        if self.config.auth.enabled:
            self.app.add_middleware(AuthenticationMiddleware, config=self.config.auth)
        
        # Rate limiting middleware
        if self.config.rate_limiting.enabled:
            self.app.add_middleware(RateLimitingMiddleware, config=self.config.rate_limiting)
        
        # Request transformation middleware
        route_configs = {route.path: route.dict() for route in self.config.routes}
        self.app.add_middleware(RequestTransformationMiddleware, route_configs=route_configs)
        
        logger.info("Middleware stack configured")
    
    def _setup_routes(self) -> None:
        """Setup dynamic routing"""
        
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            """Gateway health check"""
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "version": "1.0.0",
                "services": await self._get_service_health_status()
            }
        
        # Metrics endpoint
        if self.config.metrics.enabled:
            @self.app.get(self.config.metrics.endpoint)
            async def metrics():
                """Gateway metrics"""
                return await self.metrics.get_metrics()
        
        # Dashboard endpoint
        @self.app.get("/dashboard")
        async def dashboard():
            """Service Dashboard"""
            import os
            from fastapi.responses import FileResponse
            dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dashboard.html")
            return FileResponse(dashboard_path)
        
        # Root redirect to dashboard
        @self.app.get("/")
        async def root():
            """Redirect root to dashboard"""
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/dashboard")
            
        # Unified OpenAPI endpoint
        @self.app.get("/openapi.json")
        async def unified_openapi():
            """Unified OpenAPI specification from all services"""
            # Build services map dynamically from configured routes
            services: Dict[str, str] = {}
            for route in self.config.routes:
                # Use the first upstream instance as the base URL for spec fetch
                if route.service_name not in services and route.upstream_instances:
                    instance = route.upstream_instances[0]
                    services[route.service_name] = instance.url
            return await self.openapi_aggregator.get_unified_openapi_spec(services)
        
        # Catch-all route for proxying
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        async def proxy_request(request: Request, path: str):
            """Proxy requests to upstream services"""
            return await self._handle_proxy_request(request, path)
        
        logger.info("Routes configured")
    
    async def _handle_proxy_request(self, request: Request, path: str) -> Any:
        """Handle proxying requests to upstream services"""
        
        # Find matching route
        route_config = self._find_matching_route(f"/{path}")
        if not route_config:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Record request start time
        start_time = time.time()
        
        try:
            # Select upstream instance
            instance = await self._select_upstream_instance(request, route_config)
            if not instance:
                raise HTTPException(status_code=503, detail="No healthy upstream instances")
            
            # Build upstream URL
            upstream_url = await self._build_upstream_url(instance, path, route_config)
            
            # Forward request
            response = await self._forward_request(request, upstream_url, route_config)
            
            # Record successful request
            duration = time.time() - start_time
            await self.load_balancer.record_request_end(instance, success=True, response_time=duration)
            await self.metrics.record_request(
                method=request.method,
                path=f"/{path}",
                status_code=response.status_code,
                duration=duration,
                service=route_config.service_name
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            # Record failed request
            duration = time.time() - start_time
            if 'instance' in locals():
                await self.load_balancer.record_request_end(instance, success=False)
            
            await self.metrics.record_error(
                method=request.method,
                path=f"/{path}",
                error_type=type(e).__name__,
                service=route_config.service_name if route_config else "unknown"
            )
            
            logger.error(f"Proxy request failed: {e}")
            raise HTTPException(status_code=502, detail="Bad Gateway")
    
    def _find_matching_route(self, path: str) -> Optional[RouteConfig]:
        """Find matching route configuration"""
        for route_path, route_config in self.routes.items():
            if self._path_matches(path, route_path):
                return route_config
        return None
    
    def _path_matches(self, request_path: str, route_path: str) -> bool:
        """Check if request path matches route pattern"""
        if route_path.endswith("/*"):
            return request_path.startswith(route_path[:-2])
        elif route_path.endswith("*"):
            return request_path.startswith(route_path[:-1])
        return request_path == route_path
    
    async def _select_upstream_instance(
        self,
        request: Request,
        route_config: RouteConfig
    ) -> Optional[ServiceInstance]:
        """Select upstream service instance"""
        
        # Get client IP and session ID
        client_ip = self._get_client_ip(request)
        session_id = request.cookies.get("gateway_session")
        
        # Check for sticky session
        if session_id and self.config.load_balancer.sticky_sessions:
            instance = await self.sticky_session_manager.get_session_instance(
                session_id, route_config.upstream_instances
            )
            if instance:
                return instance
        
        # Select instance using load balancer
        instance = await self.load_balancer.select_instance(
            route_config.upstream_instances,
            client_ip=client_ip,
            session_id=session_id
        )
        
        if instance:
            # Record request start
            await self.load_balancer.record_request_start(instance)
            
            # Create sticky session if enabled
            if session_id and self.config.load_balancer.sticky_sessions:
                await self.sticky_session_manager.create_session(session_id, instance)
        
        return instance
    
    async def _build_upstream_url(
        self,
        instance: ServiceInstance,
        path: str,
        route_config: RouteConfig
    ) -> str:
        """Build upstream URL"""
        
        # Strip path prefix if configured
        if route_config.strip_path_prefix:
            # Remove the service prefix from path
            path_parts = path.strip("/").split("/")
            if len(path_parts) >= 3 and path_parts[0] == "api" and path_parts[1] == "v1":
                # Remove /api/v1/service_name prefix
                path = "/" + "/".join(path_parts[3:]) if len(path_parts) > 3 else "/"
        
        return f"{instance.url}{path}"
    
    async def _forward_request(
        self,
        request: Request,
        upstream_url: str,
        route_config: RouteConfig
    ) -> JSONResponse:
        """Forward request to upstream service"""
        
        # Prepare headers
        headers = dict(request.headers)
        
        # Add configured headers
        headers.update(route_config.add_headers)
        
        # Remove configured headers
        for header_name in route_config.remove_headers:
            headers.pop(header_name, None)
        
        # Add tracing headers
        if hasattr(request.state, 'trace_id'):
            headers['X-Trace-ID'] = request.state.trace_id
            headers['X-Span-ID'] = request.state.span_id
        
        # Get request body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Get query parameters
        query_params = dict(request.query_params)
        
        try:
            # Make upstream request
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=route_config.connect_timeout,
                    read=route_config.read_timeout
                )
            ) as client:
                
                response = await client.request(
                    method=request.method,
                    url=upstream_url,
                    headers=headers,
                    content=body,
                    params=query_params
                )
                
                # Create response
                return JSONResponse(
                    content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Bad Gateway - Connection Error")
        except Exception as e:
            logger.error(f"Upstream request failed: {e}")
            raise HTTPException(status_code=502, detail="Bad Gateway")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _get_service_health_status(self) -> Dict[str, Any]:
        """Get health status of all services"""
        service_health = {}
        
        for route_path, route_config in self.routes.items():
            service_name = route_config.service_name
            healthy_instances = [
                instance for instance in route_config.upstream_instances
                if instance.healthy
            ]
            
            service_health[service_name] = {
                "total_instances": len(route_config.upstream_instances),
                "healthy_instances": len(healthy_instances),
                "status": "healthy" if healthy_instances else "unhealthy"
            }
        
        return service_health
    
    async def start(self) -> None:
        """Start the API Gateway"""
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient()
        
        # Start OpenAPI aggregator
        await self.openapi_aggregator.start()
        
        # Start health checks
        if self.config.load_balancer.health_check_enabled:
            await self._start_health_checks()
        
        # Start metrics collection
        if self.config.metrics.enabled:
            await self.metrics.start()
        
        logger.info(f"API Gateway started on {self.config.host}:{self.config.port}")
    
    async def stop(self) -> None:
        """Stop the API Gateway"""
        
        # Close HTTP client
        if self.http_client:
            await self.http_client.aclose()
        
        # Stop OpenAPI aggregator
        await self.openapi_aggregator.stop()
        
        # Stop metrics collection
        if self.config.metrics.enabled:
            await self.metrics.stop()
        
        logger.info("API Gateway stopped")
    
    async def _start_health_checks(self) -> None:
        """Start health checks for all service instances"""
        
        all_instances = []
        for route_config in self.routes.values():
            all_instances.extend(route_config.upstream_instances)
        
        if all_instances:
            await self.load_balancer.start_health_checks(
                all_instances,
                interval=self.config.load_balancer.health_check_interval
            )
    
    def add_route(self, route_config: RouteConfig) -> None:
        """Add a new route configuration"""
        self.routes[route_config.path] = route_config
        logger.info(f"Added route: {route_config.path} -> {route_config.service_name}")
    
    def remove_route(self, path: str) -> None:
        """Remove a route configuration"""
        if path in self.routes:
            del self.routes[path]
            logger.info(f"Removed route: {path}")
    
    def get_route_stats(self) -> Dict[str, Any]:
        """Get statistics for all routes"""
        stats = {}
        
        for route_path, route_config in self.routes.items():
            service_stats = {
                "service_name": route_config.service_name,
                "instances": []
            }
            
            for instance in route_config.upstream_instances:
                instance_stats = self.load_balancer.get_instance_stats(instance)
                service_stats["instances"].append({
                    "url": instance.url,
                    "healthy": instance.healthy,
                    "weight": instance.weight,
                    "active_connections": instance_stats.active_connections,
                    "total_requests": instance_stats.total_requests,
                    "failed_requests": instance_stats.failed_requests,
                    "success_rate": instance_stats.success_rate,
                    "average_response_time": instance_stats.average_response_time
                })
            
            stats[route_path] = service_stats
        
        return stats


@asynccontextmanager
async def create_gateway(config: GatewayConfig):
    """Create and manage API Gateway lifecycle"""
    gateway = APIGateway(config)
    
    try:
        await gateway.start()
        yield gateway
    finally:
        await gateway.stop()
