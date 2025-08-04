"""
HTTP Client Library for Microservices Communication

Provides utilities for HTTP-based service-to-service communication
with authentication, retry logic, and error handling.
"""

from .service_client import ServiceClient, ServiceRegistry, ServiceInfo
from .circuit_breaker import CircuitBreaker
from .auth_client import AuthServiceClient
from .exceptions import ServiceCommunicationError, ServiceUnavailableError

__all__ = [
    "ServiceClient",
    "ServiceRegistry",
    "ServiceInfo", 
    "CircuitBreaker",
    "AuthServiceClient",
    "ServiceCommunicationError",
    "ServiceUnavailableError"
]
