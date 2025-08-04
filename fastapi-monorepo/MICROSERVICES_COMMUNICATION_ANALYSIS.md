# 🔄 Microservices Communication Analysis

## 📋 Tổng quan hiện tại

Trong FastAPI monorepo này, các services hiện tại **KHÔNG giao tiếp trực tiếp** với nhau thông qua HTTP calls hay message queues. Thay vào đó, chúng sử dụng **shared authentication pattern** và **common libraries**.

## 🏗️ Architecture hiện tại

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Auth Service  │    │ Product Service │    │Articles Service │
│   (Port 8001)   │    │   (Port 8003)   │    │   (Port 8002)   │
│                 │    │                 │    │                 │
│ - User Management│    │ - Product CRUD  │    │ - Article CRUD  │
│ - JWT Creation  │    │ - JWT Validation│    │ - JWT Validation│
│ - Authentication│    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │   Shared Libraries  │
                    │                     │
                    │ - libs/auth         │
                    │ - libs/common       │
                    │ - libs/db           │
                    └─────────────────────┘
```

## 🔗 Các phương thức giao tiếp hiện tại

### **1. 🔐 JWT Authentication Pattern**

**Cách hoạt động:**
```
1. Client → Auth Service: Login request
2. Auth Service → Client: JWT token
3. Client → Product Service: API request + JWT token
4. Product Service → libs/auth: Validate JWT token
5. Product Service → Client: Response
```

**Code example:**
```python
# Auth Service tạo JWT token
jwt_manager = JWTManager()
access_token = jwt_manager.create_access_token(user_data)

# Product Service validate JWT token
from libs.auth.jwt_utils import get_current_user_id

@router.post("/products/")
async def create_product(
    current_user_id: int = Depends(get_current_user_id)  # Validate JWT
):
    # JWT được validate thông qua shared libs/auth
    pass
```

### **2. 📚 Shared Libraries Pattern**

**Các thư viện chung:**
```
libs/
├── auth/           # JWT utilities, password hashing
├── common/         # Base models, schemas, services
└── db/             # Database session, connection
```

**Code example:**
```python
# Tất cả services sử dụng chung BaseModel
from libs.common.base_model import BaseModel

class Product(BaseModel):  # Product Service
    name = Column(String)
    
class Article(BaseModel):  # Articles Service
    title = Column(String)
```

### **3. 🗄️ Database Isolation Pattern**

**Mỗi service có database riêng:**
```
- authdb      (Auth Service)
- productsdb  (Products Service)  
- articlesdb  (Articles Service)
- userdb      (User Service)
- rolesdb     (Roles Service)
```

## 🚫 Các phương thức giao tiếp CHƯA được implement

### **1. HTTP Service-to-Service Communication**
```python
# CHƯA CÓ: Product Service gọi Auth Service để verify user
async def verify_user_exists(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://auth-service:8001/users/{user_id}")
        return response.json()
```

### **2. Message Queue/Event-Driven Communication**
```python
# CHƯA CÓ: Event publishing khi tạo product
await event_bus.publish("product.created", {
    "product_id": product.id,
    "user_id": current_user_id
})
```

### **3. gRPC Communication**
```python
# CHƯA CÓ: gRPC calls giữa services
import grpc
from auth_service_pb2_grpc import AuthServiceStub

async def verify_user_grpc(user_id: int):
    channel = grpc.aio.insecure_channel('auth-service:50051')
    stub = AuthServiceStub(channel)
    return await stub.VerifyUser(user_id)
```

## 🎯 Recommended Communication Patterns

### **Scenario 1: Product Service cần verify User info**

**❌ Hiện tại:** Product Service chỉ có `user_id` từ JWT, không biết thêm thông tin user

**✅ Nên có:**
```python
# Option 1: HTTP call to Auth Service
async def get_user_info(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8001/api/v1/users/{user_id}")
        return response.json()

@router.post("/products/")
async def create_product(
    product_data: ProductCreate,
    current_user_id: int = Depends(get_current_user_id)
):
    # Get full user info from Auth Service
    user_info = await get_user_info(current_user_id)
    
    # Use user info in business logic
    product_data.created_by_username = user_info["username"]
    return service.create_product(product_data)
```

### **Scenario 2: Articles Service cần liên kết với User**

**❌ Hiện tại:** Articles chỉ lưu `user_id`, không có thông tin user

**✅ Nên có:**
```python
# Event-driven approach
@router.post("/articles/")
async def create_article(
    article_data: ArticleCreate,
    current_user_id: int = Depends(get_current_user_id)
):
    article = service.create_article(article_data, author_id=current_user_id)
    
    # Publish event for other services
    await event_bus.publish("article.created", {
        "article_id": article.id,
        "author_id": current_user_id,
        "title": article.title
    })
    
    return article
```

### **Scenario 3: Cross-service Data Aggregation**

**❌ Hiện tại:** Không có cách nào để aggregate data từ nhiều services

**✅ Nên có:**
```python
# API Gateway pattern hoặc BFF (Backend for Frontend)
@router.get("/dashboard/")
async def get_dashboard(current_user_id: int = Depends(get_current_user_id)):
    # Aggregate data from multiple services
    async with httpx.AsyncClient() as client:
        # Get user info
        user_response = await client.get(f"http://localhost:8001/api/v1/users/{current_user_id}")
        
        # Get user's products
        products_response = await client.get(f"http://localhost:8003/api/v1/products/?user_id={current_user_id}")
        
        # Get user's articles
        articles_response = await client.get(f"http://localhost:8002/api/v1/articles/?author_id={current_user_id}")
    
    return {
        "user": user_response.json(),
        "products": products_response.json(),
        "articles": articles_response.json()
    }
```

## 🛠️ Implementation Options

### **1. 🌐 HTTP-based Communication**

**Ưu điểm:**
- ✅ Đơn giản, dễ implement
- ✅ RESTful, human-readable
- ✅ Có thể test bằng curl/Postman
- ✅ Tương thích với existing FastAPI services

**Nhược điểm:**
- ❌ Latency cao hơn
- ❌ Network overhead
- ❌ Cần handle timeout, retry logic

**Implementation:**
```python
# libs/http_client/service_client.py
import httpx
from typing import Optional, Dict, Any

class ServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get(self, endpoint: str, headers: Optional[Dict] = None):
        response = await self.client.get(f"{self.base_url}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def post(self, endpoint: str, data: Dict[str, Any], headers: Optional[Dict] = None):
        response = await self.client.post(f"{self.base_url}{endpoint}", json=data, headers=headers)
        response.raise_for_status()
        return response.json()

# Usage in Product Service
auth_client = ServiceClient("http://localhost:8001/api/v1")

async def get_user_info(user_id: int, jwt_token: str):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    return await auth_client.get(f"/users/{user_id}", headers=headers)
```

### **2. 📨 Event-Driven Communication**

**Ưu điểm:**
- ✅ Loose coupling
- ✅ Scalable
- ✅ Asynchronous processing
- ✅ Event sourcing capabilities

**Nhược điểm:**
- ❌ Phức tạp hơn
- ❌ Eventual consistency
- ❌ Cần message broker (Redis, RabbitMQ)

**Implementation:**
```python
# libs/events/event_bus.py
import redis
import json
from typing import Dict, Any, Callable

class EventBus:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        message = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis.publish(event_type, json.dumps(message))
    
    async def subscribe(self, event_type: str, handler: Callable):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(event_type)
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await handler(data)

# Usage
event_bus = EventBus()

# Publisher (Auth Service)
await event_bus.publish("user.created", {
    "user_id": user.id,
    "username": user.username,
    "email": user.email
})

# Subscriber (Products Service)
async def handle_user_created(event_data):
    user_id = event_data["data"]["user_id"]
    # Update local cache or trigger business logic
    logger.info(f"User {user_id} created, updating product permissions")

await event_bus.subscribe("user.created", handle_user_created)
```

### **3. 🚀 gRPC Communication**

**Ưu điểm:**
- ✅ High performance
- ✅ Type-safe
- ✅ Bi-directional streaming
- ✅ Language agnostic

**Nhược điểm:**
- ❌ Phức tạp setup
- ❌ Cần protobuf definitions
- ❌ Khó debug hơn HTTP

## 📊 Current vs Recommended Architecture

### **🔄 Current Architecture:**
```
Client → Auth Service (JWT) → Client → Product Service (JWT validation)
```

### **🎯 Recommended Architecture:**
```
                    ┌─────────────────┐
                    │   API Gateway   │
                    │  (Port 8000)    │
                    └─────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │   Auth Service  │ │ Product Service │ │Articles Service │
   │   (Port 8001)   │ │   (Port 8003)   │ │   (Port 8002)   │
   └─────────────────┘ └─────────────────┘ └─────────────────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌─────────────────┐
                    │   Event Bus     │
                    │   (Redis)       │
                    └─────────────────┘
```

## 🎯 Next Steps để implement Service Communication

### **Phase 1: HTTP-based Communication**
1. Tạo `libs/http_client` với ServiceClient utility
2. Implement service discovery (service registry)
3. Add retry logic và circuit breaker pattern
4. Implement cross-service authentication forwarding

### **Phase 2: Event-Driven Architecture**
1. Setup Redis/RabbitMQ message broker
2. Tạo `libs/events` với EventBus utility
3. Define event schemas và contracts
4. Implement event handlers trong các services

### **Phase 3: Advanced Patterns**
1. API Gateway với routing và load balancing
2. Service mesh (Istio) cho advanced networking
3. Distributed tracing (Jaeger/Zipkin)
4. Circuit breaker và bulkhead patterns

## 🎉 Kết luận

**Hiện tại:** Các services giao tiếp **gián tiếp** thông qua **shared JWT authentication** và **common libraries**.

**Tương lai:** Nên implement **HTTP-based service communication** và **event-driven architecture** để tạo ra một microservices ecosystem hoàn chỉnh và scalable! 🚀
