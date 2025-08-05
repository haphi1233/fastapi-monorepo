"""
Unified OpenAPI Documentation Aggregator
========================================

Tổng hợp OpenAPI specs từ tất cả microservices thành 1 documentation duy nhất
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
import httpx
from fastapi.openapi.utils import get_openapi

logger = logging.getLogger(__name__)

class OpenAPIAggregator:
    """Aggregates OpenAPI specs from multiple microservices"""
    
    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.cached_specs: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes cache
        
    async def start(self):
        """Initialize HTTP client"""
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
    async def stop(self):
        """Cleanup HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
    
    async def fetch_service_openapi(self, service_name: str, service_url: str) -> Optional[Dict[str, Any]]:
        """Fetch OpenAPI spec from a microservice"""
        try:
            if not self.http_client:
                await self.start()
                
            response = await self.http_client.get(f"{service_url}/openapi.json")
            response.raise_for_status()
            
            openapi_spec = response.json()
            logger.info(f"Successfully fetched OpenAPI spec from {service_name}")
            return openapi_spec
            
        except Exception as e:
            logger.warning(f"Failed to fetch OpenAPI spec from {service_name} ({service_url}): {e}")
            return None
    
    def merge_openapi_specs(self, specs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple OpenAPI specs into one unified spec"""
        
        # Base unified spec
        unified_spec = {
            "openapi": "3.1.0",
            "info": {
                "title": "🚀 FastAPI Monorepo - Unified API Documentation",
                "description": """
## Tổng hợp tất cả API endpoints từ toàn bộ microservices

Đây là API documentation tập trung cho toàn bộ hệ thống FastAPI Monorepo, 
bao gồm tất cả endpoints từ các microservices:

### 🏗️ Kiến trúc hệ thống:
- **API Gateway** (port 8080): Điều phối và routing requests
- **Auth Service** (port 8001): Xác thực và quản lý người dùng  
- **Products Service** (port 8003): Quản lý sản phẩm và inventory
- **Articles Service** (port 8002): Quản lý bài viết và nội dung

### 🔗 Routing qua API Gateway:
- Tất cả requests có thể được gửi qua Gateway tại port 8080
- Paths sẽ được tự động routing tới service tương ứng
- Hỗ trợ load balancing, rate limiting, CORS

### 📚 Cách sử dụng:
1. **Thông qua Gateway** (khuyến nghị): `http://localhost:8080/service-path/endpoint`
2. **Trực tiếp service**: `http://localhost:port/endpoint`

### 🛡️ Authentication:
- Hầu hết endpoints cần JWT token trong header `Authorization: Bearer <token>`
- Lấy token từ `/auth/login` hoặc `/api/v1/auth/login`
                """,
                "version": "1.0.0",
                "contact": {
                    "name": "FastAPI Monorepo Team",
                    "email": "support@fastapi-monorepo.com"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8080",
                    "description": "API Gateway (Recommended - All services via Gateway)"
                },
                {
                    "url": "http://localhost:8001", 
                    "description": "Auth Service (Direct)"
                },
                {
                    "url": "http://localhost:8003",
                    "description": "Products Service (Direct)"
                },
                {
                    "url": "http://localhost:8002",
                    "description": "Articles Service (Direct)"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT token obtained from /auth/login"
                    }
                }
            },
            "security": [{"BearerAuth": []}],
            "tags": []
        }
        
        # Service to tag mapping
        service_tags = {
            "auth-service": {
                "name": "🔐 Authentication", 
                "description": "User authentication, registration, and profile management"
            },
            "products-service": {
                "name": "📦 Products",
                "description": "Product management, inventory, categories, and stock control"
            },
            "articles-service": {
                "name": "📝 Articles", 
                "description": "Content management, publishing, and article operations"
            },
            "gateway": {
                "name": "⚙️ Gateway",
                "description": "API Gateway management, health checks, and metrics"
            }
        }
        
        # Add service tags
        for service_name, tag_info in service_tags.items():
            unified_spec["tags"].append(tag_info)
        
        # Merge paths from all services
        for service_name, spec in specs.items():
            if not spec or "paths" not in spec:
                continue
                
            service_tag = None
            for svc, tag in service_tags.items():
                if svc in service_name or service_name in svc:
                    service_tag = tag["name"]
                    break
            
            # Add service paths with proper prefixes
            for path, path_item in spec["paths"].items():
                # Skip gateway internal paths to avoid conflicts
                if service_name == "gateway" and path in ["/", "/dashboard", "/health", "/metrics"]:
                    continue
                    
                # Determine the gateway path
                if service_name == "auth-service":
                    gateway_paths = [f"/auth{path}", f"/api/v1/auth{path}"]
                elif service_name == "products-service":
                    gateway_paths = [f"/products{path}", f"/api/v1/products{path}"]
                elif service_name == "articles-service":
                    gateway_paths = [f"/articles{path}", f"/api/v1/articles{path}"]
                else:
                    gateway_paths = [path]
                
                # Add each gateway path
                for gateway_path in gateway_paths:
                    # Copy path item
                    unified_path_item = {}
                    
                    for method, operation in path_item.items():
                        if method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                            # Copy operation
                            unified_operation = dict(operation)
                            
                            # Add service tag
                            if service_tag:
                                if "tags" not in unified_operation:
                                    unified_operation["tags"] = []
                                if service_tag not in unified_operation["tags"]:
                                    unified_operation["tags"].append(service_tag)
                            
                            # Update operation ID to avoid conflicts
                            if "operationId" in unified_operation:
                                unified_operation["operationId"] = f"{service_name}_{unified_operation['operationId']}"
                            
                            # Add service info to summary
                            if "summary" in unified_operation:
                                unified_operation["summary"] = f"[{service_name.replace('-service', '').title()}] {unified_operation['summary']}"
                            
                            unified_path_item[method] = unified_operation
                    
                    if unified_path_item:
                        unified_spec["paths"][gateway_path] = unified_path_item
        
        # Merge schemas from all services
        for service_name, spec in specs.items():
            if not spec or "components" not in spec or "schemas" not in spec["components"]:
                continue
                
            for schema_name, schema_def in spec["components"]["schemas"].items():
                # Prefix schema names to avoid conflicts
                prefixed_name = f"{service_name.replace('-service', '').title()}{schema_name}"
                unified_spec["components"]["schemas"][prefixed_name] = schema_def
        
        return unified_spec
    
    async def get_unified_openapi_spec(self, services: Dict[str, str]) -> Dict[str, Any]:
        """Get unified OpenAPI spec from all services"""
        
        specs = {}
        
        # Fetch specs from all services concurrently
        tasks = []
        for service_name, service_url in services.items():
            task = self.fetch_service_openapi(service_name, service_url)
            tasks.append((service_name, task))
        
        # Wait for all requests to complete
        for service_name, task in tasks:
            try:
                spec = await task
                if spec:
                    specs[service_name] = spec
            except Exception as e:
                logger.warning(f"Failed to fetch spec for {service_name}: {e}")
        
        # Merge all specs
        unified_spec = self.merge_openapi_specs(specs)
        
        logger.info(f"Successfully created unified OpenAPI spec with {len(unified_spec['paths'])} endpoints")
        return unified_spec
