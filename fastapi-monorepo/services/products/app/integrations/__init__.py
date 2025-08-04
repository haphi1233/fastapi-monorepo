"""
Integration utilities for Product Service
"""

from .http_integration import ProductHTTPIntegration
from .event_integration import ProductEventIntegration

__all__ = [
    "ProductHTTPIntegration",
    "ProductEventIntegration"
]
