"""
Custom exceptions for HTTP service communication
"""

from typing import Optional, Dict, Any


class ServiceCommunicationError(Exception):
    """Base exception for service communication errors"""
    
    def __init__(
        self, 
        message: str, 
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.service_name = service_name
        self.status_code = status_code
        self.response_data = response_data


class ServiceUnavailableError(ServiceCommunicationError):
    """Service is temporarily unavailable"""
    pass


class ServiceTimeoutError(ServiceCommunicationError):
    """Service request timed out"""
    pass


class ServiceAuthenticationError(ServiceCommunicationError):
    """Authentication failed when calling service"""
    pass


class ServiceNotFoundError(ServiceCommunicationError):
    """Service endpoint not found"""
    pass


class ServiceValidationError(ServiceCommunicationError):
    """Service returned validation error"""
    pass


class CircuitBreakerOpenError(ServiceCommunicationError):
    """Circuit breaker is open, preventing service calls"""
    pass
