"""
Service Registry for microservices discovery and configuration
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

from .http_client import ServiceRegistry, ServiceInfo
from .events import EventBus


@dataclass
class ServiceConfig:
    """Configuration for a microservice"""
    name: str
    port: int
    base_url: str
    health_endpoint: str = "/health"
    api_prefix: str = "/api/v1"


class MicroserviceRegistry:
    """
    Central registry for all microservices in the monorepo
    
    Provides service discovery, configuration, and communication setup
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.services: Dict[str, ServiceConfig] = {}
        self.http_registry = ServiceRegistry()
        self.event_buses: Dict[str, EventBus] = {}
        
        # Register all services
        self._register_default_services()
    
    def _register_default_services(self):
        """Register default services from monorepo"""
        
        # Get base host from environment
        base_host = os.getenv("SERVICE_HOST", "localhost")
        
        services = [
            ServiceConfig(
                name="auth",
                port=8001,
                base_url=f"http://{base_host}:8001",
                api_prefix="/api/v1"
            ),
            ServiceConfig(
                name="articles",
                port=8002,
                base_url=f"http://{base_host}:8002",
                api_prefix="/api/v1"
            ),
            ServiceConfig(
                name="products",
                port=8003,
                base_url=f"http://{base_host}:8003",
                api_prefix="/api/v1"
            ),
            ServiceConfig(
                name="user",
                port=8004,
                base_url=f"http://{base_host}:8004",
                api_prefix="/api/v1"
            ),
            ServiceConfig(
                name="roles",
                port=8005,
                base_url=f"http://{base_host}:8005",
                api_prefix="/api/v1"
            )
        ]
        
        for service_config in services:
            self.register_service(service_config)
    
    def register_service(self, service_config: ServiceConfig):
        """Register a service in the registry"""
        self.services[service_config.name] = service_config
        
        # Register in HTTP service registry
        service_info = ServiceInfo(
            name=service_config.name,
            base_url=f"{service_config.base_url}{service_config.api_prefix}",
            health_endpoint=service_config.health_endpoint
        )
        self.http_registry.register_service(service_info)
    
    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """Get service configuration by name"""
        return self.services.get(service_name)
    
    def get_http_registry(self) -> ServiceRegistry:
        """Get HTTP service registry"""
        return self.http_registry
    
    def get_event_bus(self, service_name: str) -> EventBus:
        """Get or create event bus for service"""
        if service_name not in self.event_buses:
            self.event_buses[service_name] = EventBus(
                redis_url=self.redis_url,
                service_name=service_name
            )
        
        return self.event_buses[service_name]
    
    async def start_health_monitoring(self):
        """Start health monitoring for all services"""
        await self.http_registry.start_health_monitoring()
    
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        await self.http_registry.stop_health_monitoring()
    
    def get_all_services(self) -> Dict[str, ServiceConfig]:
        """Get all registered services"""
        return self.services.copy()
    
    def get_service_url(self, service_name: str, endpoint: str = "") -> Optional[str]:
        """Get full URL for service endpoint"""
        service_config = self.get_service_config(service_name)
        if service_config:
            base_url = f"{service_config.base_url}{service_config.api_prefix}"
            return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}" if endpoint else base_url
        return None


# Global service registry instance
global_service_registry = MicroserviceRegistry()
