"""
HTTP Service Client with retry logic, authentication, and service discovery
"""

import asyncio
import httpx
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .exceptions import (
    ServiceCommunicationError,
    ServiceUnavailableError,
    ServiceTimeoutError,
    ServiceAuthenticationError,
    ServiceNotFoundError,
    ServiceValidationError
)

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0


@dataclass
class ServiceInfo:
    """Service information for service discovery"""
    name: str
    base_url: str
    health_endpoint: str = "/health"
    is_healthy: bool = True
    last_health_check: float = 0
    circuit_breaker: Optional[CircuitBreaker] = field(default=None)
    
    def __post_init__(self):
        if self.circuit_breaker is None:
            self.circuit_breaker = CircuitBreaker(
                name=f"{self.name}_circuit_breaker",
                config=CircuitBreakerConfig()
            )


class ServiceRegistry:
    """
    Service registry for service discovery and health monitoring
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    def register_service(self, service_info: ServiceInfo):
        """Register a service"""
        self.services[service_info.name] = service_info
        logger.info(f"Registered service: {service_info.name} at {service_info.base_url}")
    
    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Get service info by name"""
        return self.services.get(service_name)
    
    def get_healthy_services(self) -> List[ServiceInfo]:
        """Get list of healthy services"""
        return [service for service in self.services.values() if service.is_healthy]
    
    async def start_health_monitoring(self):
        """Start background health monitoring"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Started service health monitoring")
    
    async def stop_health_monitoring(self):
        """Stop background health monitoring"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped service health monitoring")
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_services_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _check_all_services_health(self):
        """Check health of all registered services"""
        for service in self.services.values():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{service.base_url}{service.health_endpoint}")
                    service.is_healthy = response.status_code == 200
                    service.last_health_check = asyncio.get_event_loop().time()
                    
                    if service.is_healthy:
                        logger.debug(f"Service {service.name} is healthy")
                    else:
                        logger.warning(f"Service {service.name} health check failed: {response.status_code}")
                        
            except Exception as e:
                service.is_healthy = False
                service.last_health_check = asyncio.get_event_loop().time()
                logger.warning(f"Service {service.name} health check failed: {e}")


class ServiceClient:
    """
    HTTP client for service-to-service communication with advanced features:
    - Circuit breaker pattern
    - Retry logic with exponential backoff
    - Authentication forwarding
    - Request/response logging
    - Service discovery integration
    """
    
    def __init__(
        self,
        service_name: str,
        service_registry: Optional[ServiceRegistry] = None,
        retry_config: Optional[RetryConfig] = None,
        default_timeout: float = 30.0
    ):
        self.service_name = service_name
        self.service_registry = service_registry
        self.retry_config = retry_config or RetryConfig()
        self.default_timeout = default_timeout
        self.client = httpx.AsyncClient(timeout=default_timeout)
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform GET request with retry and circuit breaker
        """
        return await self._make_request("GET", endpoint, params=params, headers=headers, jwt_token=jwt_token)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform POST request with retry and circuit breaker
        """
        return await self._make_request("POST", endpoint, json=data, headers=headers, jwt_token=jwt_token)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform PUT request with retry and circuit breaker
        """
        return await self._make_request("PUT", endpoint, json=data, headers=headers, jwt_token=jwt_token)
    
    async def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Perform DELETE request with retry and circuit breaker
        """
        return await self._make_request("DELETE", endpoint, headers=headers, jwt_token=jwt_token)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """
        Make HTTP request with retry logic and circuit breaker
        """
        service_info = self._get_service_info()
        if not service_info:
            raise ServiceUnavailableError(
                f"Service {self.service_name} not found in registry",
                service_name=self.service_name
            )
        
        # Prepare headers with authentication
        headers = kwargs.get("headers", {}) or {}
        jwt_token = kwargs.pop("jwt_token", None)
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        kwargs["headers"] = headers
        
        # Build full URL
        url = f"{service_info.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Execute with circuit breaker and retry
        return await service_info.circuit_breaker.call(
            self._execute_with_retry,
            method,
            url,
            **kwargs
        )
    
    async def _execute_with_retry(self, method: str, url: str, **kwargs) -> Any:
        """
        Execute HTTP request with retry logic
        """
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.retry_config.max_attempts}: {method} {url}")
                
                response = await self.client.request(method, url, **kwargs)
                
                # Log request/response
                logger.info(f"{method} {url} -> {response.status_code}")
                
                # Handle different status codes
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        return response.json() if response.content else None
                    except json.JSONDecodeError:
                        return {"message": "Success", "status_code": response.status_code}
                
                elif response.status_code == 204:
                    return None
                
                elif response.status_code == 401:
                    raise ServiceAuthenticationError(
                        "Authentication failed",
                        service_name=self.service_name,
                        status_code=response.status_code
                    )
                
                elif response.status_code == 404:
                    raise ServiceNotFoundError(
                        f"Endpoint not found: {url}",
                        service_name=self.service_name,
                        status_code=response.status_code
                    )
                
                elif response.status_code == 422:
                    try:
                        error_data = response.json()
                    except:
                        error_data = {"detail": "Validation error"}
                    
                    raise ServiceValidationError(
                        "Validation error",
                        service_name=self.service_name,
                        status_code=response.status_code,
                        response_data=error_data
                    )
                
                elif response.status_code >= 500:
                    # Server error - retry
                    raise ServiceUnavailableError(
                        f"Server error: {response.status_code}",
                        service_name=self.service_name,
                        status_code=response.status_code
                    )
                
                else:
                    # Client error - don't retry
                    try:
                        error_data = response.json()
                    except:
                        error_data = {"detail": f"HTTP {response.status_code}"}
                    
                    raise ServiceCommunicationError(
                        f"HTTP {response.status_code}",
                        service_name=self.service_name,
                        status_code=response.status_code,
                        response_data=error_data
                    )
            
            except (ServiceAuthenticationError, ServiceNotFoundError, ServiceValidationError):
                # Don't retry these errors
                raise
            
            except Exception as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                # Don't retry on last attempt
                if attempt == self.retry_config.max_attempts - 1:
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_retry_delay(attempt)
                logger.debug(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        # All attempts failed
        if isinstance(last_exception, httpx.TimeoutException):
            raise ServiceTimeoutError(
                f"Request timeout after {self.retry_config.max_attempts} attempts",
                service_name=self.service_name
            )
        else:
            raise ServiceCommunicationError(
                f"Request failed after {self.retry_config.max_attempts} attempts: {last_exception}",
                service_name=self.service_name
            )
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if self.retry_config.strategy == RetryStrategy.NO_RETRY:
            return 0
        
        elif self.retry_config.strategy == RetryStrategy.FIXED_DELAY:
            return self.retry_config.base_delay
        
        elif self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.base_delay * (self.retry_config.backoff_multiplier ** attempt)
            return min(delay, self.retry_config.max_delay)
        
        return self.retry_config.base_delay
    
    def _get_service_info(self) -> Optional[ServiceInfo]:
        """Get service info from registry"""
        if self.service_registry:
            return self.service_registry.get_service(self.service_name)
        return None
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
