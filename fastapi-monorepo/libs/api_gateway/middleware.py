"""
API Gateway Middleware
=====================

Middleware components for API Gateway including authentication, rate limiting,
CORS, tracing, and request/response transformation.
"""

import asyncio
import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import hashlib

from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from starlette.responses import JSONResponse

from libs.auth.jwt_utils import JWTManager
from .config import AuthConfig, RateLimitConfig, CORSConfig, TracingConfig

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT Authentication middleware for API Gateway"""
    
    def __init__(self, app, config: AuthConfig):
        super().__init__(app)
        self.config = config
        self.jwt_manager = JWTManager(
            secret_key=config.jwt_secret,
            algorithm=config.jwt_algorithm
        )
        self._auth_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Authentication middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Process authentication for incoming requests"""
        
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Skip if authentication is disabled
        if not self.config.enabled:
            return await call_next(request)
        
        try:
            # Extract JWT token
            token = self._extract_token(request)
            if not token:
                return self._unauthorized_response("Missing authentication token")
            
            # Validate token (with caching)
            user_data = await self._validate_token(token)
            if not user_data:
                return self._unauthorized_response("Invalid authentication token")
            
            # Add user data to request state
            request.state.user = user_data
            request.state.user_id = user_data.get("user_id")
            request.state.username = user_data.get("username")
            request.state.roles = user_data.get("roles", [])
            
            # Continue to next middleware/handler
            response = await call_next(request)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._unauthorized_response("Authentication failed")
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is in public paths list"""
        for public_path in self.config.public_paths:
            if public_path.endswith("*"):
                if path.startswith(public_path[:-1]):
                    return True
            elif path == public_path:
                return True
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None
    
    async def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token with caching"""
        
        # Check cache first
        if token in self._auth_cache:
            cache_entry = self._auth_cache[token]
            if time.time() < cache_entry["expires_at"]:
                return cache_entry["user_data"]
            else:
                # Remove expired cache entry
                del self._auth_cache[token]
        
        try:
            # Validate token
            payload = self.jwt_manager.verify_token(token)
            user_data = {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", [])
            }
            
            # Cache the result
            self._auth_cache[token] = {
                "user_data": user_data,
                "expires_at": time.time() + self.config.auth_cache_ttl
            }
            
            return user_data
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Return unauthorized response"""
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with multiple strategies"""
    
    def __init__(self, app, config: RateLimitConfig):
        super().__init__(app)
        self.config = config
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        logger.info("Rate limiting middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Process rate limiting for incoming requests"""
        
        if not self.config.enabled:
            return await call_next(request)
        
        try:
            # Generate rate limit keys
            keys = self._generate_rate_limit_keys(request)
            
            # Check rate limits
            for key, limit_info in keys.items():
                if await self._is_rate_limited(key, limit_info):
                    return self._rate_limit_response(key, limit_info)
            
            # Record request
            for key, limit_info in keys.items():
                await self._record_request(key, limit_info)
            
            # Continue to next middleware/handler
            response = await call_next(request)
            
            # Add rate limit headers
            self._add_rate_limit_headers(response, keys)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return await call_next(request)
    
    def _generate_rate_limit_keys(self, request: Request) -> Dict[str, Dict[str, Any]]:
        """Generate rate limit keys for different strategies"""
        keys = {}
        
        # Rate limit by IP
        if self.config.by_ip:
            client_ip = self._get_client_ip(request)
            keys[f"ip:{client_ip}"] = {
                "rpm": self.config.default_rpm,
                "burst": self.config.default_burst,
                "type": "ip"
            }
        
        # Rate limit by user
        if self.config.by_user and hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
            keys[f"user:{user_id}"] = {
                "rpm": self.config.default_rpm,
                "burst": self.config.default_burst,
                "type": "user"
            }
        
        # Rate limit by service
        if self.config.by_service:
            service_name = self._extract_service_name(request.url.path)
            if service_name:
                keys[f"service:{service_name}"] = {
                    "rpm": self.config.default_rpm,
                    "burst": self.config.default_burst,
                    "type": "service"
                }
        
        return keys
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _extract_service_name(self, path: str) -> Optional[str]:
        """Extract service name from request path"""
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
            return parts[2]
        return None
    
    async def _is_rate_limited(self, key: str, limit_info: Dict[str, Any]) -> bool:
        """Check if request should be rate limited"""
        async with self._lock:
            current_time = time.time()
            
            if key not in self._rate_limits:
                self._rate_limits[key] = {
                    "requests": [],
                    "burst_used": 0,
                    "last_reset": current_time
                }
            
            rate_data = self._rate_limits[key]
            
            # Clean old requests (older than 1 minute)
            rate_data["requests"] = [
                req_time for req_time in rate_data["requests"]
                if current_time - req_time < 60
            ]
            
            # Check RPM limit
            if len(rate_data["requests"]) >= limit_info["rpm"]:
                return True
            
            # Check burst limit
            recent_requests = [
                req_time for req_time in rate_data["requests"]
                if current_time - req_time < 1  # Last second
            ]
            
            if len(recent_requests) >= limit_info["burst"]:
                return True
            
            return False
    
    async def _record_request(self, key: str, limit_info: Dict[str, Any]) -> None:
        """Record a request for rate limiting"""
        async with self._lock:
            current_time = time.time()
            
            if key not in self._rate_limits:
                self._rate_limits[key] = {
                    "requests": [],
                    "burst_used": 0,
                    "last_reset": current_time
                }
            
            self._rate_limits[key]["requests"].append(current_time)
    
    def _rate_limit_response(self, key: str, limit_info: Dict[str, Any]) -> JSONResponse:
        """Return rate limit exceeded response"""
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {limit_info['rpm']} per minute",
                "retry_after": 60,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(limit_info["rpm"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + 60))
            }
        )
    
    def _add_rate_limit_headers(
        self,
        response: Response,
        keys: Dict[str, Dict[str, Any]]
    ) -> None:
        """Add rate limit headers to response"""
        if not keys:
            return
        
        # Use the most restrictive limit for headers
        min_remaining = float('inf')
        max_limit = 0
        
        for key, limit_info in keys.items():
            if key in self._rate_limits:
                rate_data = self._rate_limits[key]
                remaining = limit_info["rpm"] - len(rate_data["requests"])
                min_remaining = min(min_remaining, remaining)
                max_limit = max(max_limit, limit_info["rpm"])
        
        if min_remaining != float('inf'):
            response.headers["X-RateLimit-Limit"] = str(max_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, int(min_remaining)))
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))


class TracingMiddleware(BaseHTTPMiddleware):
    """Distributed tracing middleware"""
    
    def __init__(self, app, config: TracingConfig):
        super().__init__(app)
        self.config = config
        
        logger.info("Tracing middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Add tracing information to requests"""
        
        if not self.config.enabled:
            return await call_next(request)
        
        # Generate or extract trace ID
        trace_id = request.headers.get(self.config.trace_header)
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Generate span ID
        span_id = str(uuid.uuid4())
        
        # Add tracing info to request state
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        
        # Record request start
        start_time = time.time()
        
        try:
            # Continue to next middleware/handler
            response = await call_next(request)
            
            # Record successful request
            duration = time.time() - start_time
            await self._record_trace(
                request, response, trace_id, span_id, duration, success=True
            )
            
            # Add tracing headers to response
            response.headers[self.config.trace_header] = trace_id
            response.headers[self.config.span_header] = span_id
            
            return response
            
        except Exception as e:
            # Record failed request
            duration = time.time() - start_time
            await self._record_trace(
                request, None, trace_id, span_id, duration, 
                success=False, error=str(e)
            )
            raise
    
    async def _record_trace(
        self,
        request: Request,
        response: Optional[Response],
        trace_id: str,
        span_id: str,
        duration: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Record trace information"""
        
        trace_data = {
            "trace_id": trace_id,
            "span_id": span_id,
            "service_name": self.config.service_name,
            "operation_name": f"{request.method} {request.url.path}",
            "start_time": time.time() - duration,
            "duration": duration,
            "success": success,
            "tags": {
                "http.method": request.method,
                "http.url": str(request.url),
                "http.user_agent": request.headers.get("User-Agent", ""),
                "client.ip": self._get_client_ip(request)
            }
        }
        
        if response:
            trace_data["tags"]["http.status_code"] = response.status_code
        
        if error:
            trace_data["tags"]["error"] = error
        
        if hasattr(request.state, 'user_id'):
            trace_data["tags"]["user.id"] = request.state.user_id
        
        # Log trace (in production, send to Jaeger/Zipkin)
        logger.info(f"Trace: {json.dumps(trace_data)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class CORSMiddleware:
    """CORS middleware wrapper"""
    
    def __init__(self, config: CORSConfig):
        self.config = config
    
    def create_middleware(self):
        """Create CORS middleware instance"""
        if not self.config.enabled:
            return None
        
        return StarletteCORSMiddleware(
            allow_origins=self.config.allow_origins,
            allow_credentials=self.config.allow_credentials,
            allow_methods=self.config.allow_methods,
            allow_headers=self.config.allow_headers,
            max_age=self.config.max_age
        )


class RequestTransformationMiddleware(BaseHTTPMiddleware):
    """Request/Response transformation middleware"""
    
    def __init__(self, app, route_configs: Dict[str, Any]):
        super().__init__(app)
        self.route_configs = route_configs
        
        logger.info("Request transformation middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Transform requests and responses"""
        
        # Find matching route config
        route_config = self._find_route_config(request.url.path)
        
        if route_config:
            # Transform request
            await self._transform_request(request, route_config)
        
        # Continue to next middleware/handler
        response = await call_next(request)
        
        if route_config:
            # Transform response
            await self._transform_response(response, route_config)
        
        return response
    
    def _find_route_config(self, path: str) -> Optional[Dict[str, Any]]:
        """Find matching route configuration"""
        for route_path, config in self.route_configs.items():
            if self._path_matches(path, route_path):
                return config
        return None
    
    def _path_matches(self, request_path: str, route_path: str) -> bool:
        """Check if request path matches route pattern"""
        if route_path.endswith("*"):
            return request_path.startswith(route_path[:-1])
        return request_path == route_path
    
    async def _transform_request(self, request: Request, config: Dict[str, Any]) -> None:
        """Transform incoming request"""
        
        # Add headers
        add_headers = config.get("add_headers", {})
        for header_name, header_value in add_headers.items():
            request.headers.__dict__["_list"].append(
                (header_name.lower().encode(), header_value.encode())
            )
        
        # Strip path prefix
        if config.get("strip_path_prefix", False):
            # This would be handled in the routing logic
            pass
    
    async def _transform_response(self, response: Response, config: Dict[str, Any]) -> None:
        """Transform outgoing response"""
        
        # Remove headers
        remove_headers = config.get("remove_headers", [])
        for header_name in remove_headers:
            if header_name in response.headers:
                del response.headers[header_name]
