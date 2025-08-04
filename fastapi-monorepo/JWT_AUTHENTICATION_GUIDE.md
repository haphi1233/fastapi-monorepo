# 🔐 JWT Authentication Integration Guide

## 📋 Tổng quan

Tài liệu này hướng dẫn cách tích hợp JWT Authentication từ **Auth Service** vào các microservices khác trong FastAPI monorepo để bảo vệ APIs.

## 🎯 Architecture Overview

```
┌─────────────────┐    JWT Token    ┌─────────────────┐
│   Auth Service  │ ──────────────► │ Product Service │
│   (Port 8001)   │                 │   (Port 8003)   │
│                 │                 │                 │
│ - Registration  │                 │ - Protected     │
│ - Login         │                 │   APIs with     │
│ - JWT Creation  │                 │   JWT Auth      │
└─────────────────┘                 └─────────────────┘
```

## 🔧 Implementation Steps

### **Bước 1: Import JWT Utils vào Service**

```python
# services/<service_name>/app/routers/<router_name>.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.auth.jwt_utils import get_current_user_id, get_current_user_payload
```

### **Bước 2: Thêm JWT Protection vào Endpoints**

#### **Protected Endpoint (cần JWT token):**
```python
@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user_id: int = Depends(get_current_user_id),  # JWT Protection
    service: ItemService = Depends(get_item_service)
):
    """
    Tạo item mới (Yêu cầu authentication)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Body:**
    - Item data fields
    """
    # current_user_id sẽ được extract từ JWT token
    return service.create_item(item_data)
```

#### **Public Endpoint (không cần JWT token):**
```python
@router.get("/", response_model=List[ItemResponse])
async def get_items(
    service: ItemService = Depends(get_item_service)
):
    """
    Lấy danh sách items (Public endpoint)
    
    Không cần authentication để browse items
    """
    return service.get_items()
```

### **Bước 3: JWT Authentication Strategy**

#### **📋 Recommended Protection Strategy:**

| HTTP Method | Endpoint Type | Protection | Reason |
|-------------|---------------|------------|---------|
| GET | List/Detail | Public | Browsing/viewing data |
| POST | Create | Protected | Creating new resources |
| PUT/PATCH | Update | Protected | Modifying existing data |
| DELETE | Delete | Protected | Removing data |

#### **📋 Example for Product Service:**

```python
# Public endpoints (no JWT required)
GET /api/v1/products/              # Browse products
GET /api/v1/products/{id}          # View product details
GET /api/v1/products/category/{name} # Browse by category

# Protected endpoints (JWT required)
POST /api/v1/products/             # Create product
PUT /api/v1/products/{id}          # Update product
DELETE /api/v1/products/{id}       # Delete product
PATCH /api/v1/products/{id}/stock  # Update stock
```

### **Bước 4: Update API Documentation**

```python
@router.post("/items/", response_model=ItemResponse)
async def create_item(
    item_data: ItemCreate,
    current_user_id: int = Depends(get_current_user_id),
    service: ItemService = Depends(get_item_service)
):
    """
    Tạo item mới (Yêu cầu authentication)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Body:**
    - name: Tên item (required)
    - description: Mô tả item (optional)
    
    **Response:**
    - Item đã được tạo với thông tin đầy đủ
    
    **Errors:**
    - 401: Not authenticated (missing or invalid JWT token)
    - 422: Validation error (invalid input data)
    """
    return service.create_item(item_data)
```

## 🧪 Testing JWT Authentication

### **Bước 1: Lấy JWT Token từ Auth Service**

```bash
# Login để lấy JWT token
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "TestPass123"
  }'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {...}
}
```

### **Bước 2: Test Public Endpoints (không cần JWT)**

```bash
# ✅ Should work without JWT token
curl -X GET "http://localhost:8003/api/v1/products/"
curl -X GET "http://localhost:8003/api/v1/products/1"
```

### **Bước 3: Test Protected Endpoints (cần JWT)**

```bash
# ❌ Should fail without JWT token
curl -X POST "http://localhost:8003/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Product","price":99.99,"category":"Test"}'
# Response: {"detail":"Not authenticated"}

# ✅ Should work with valid JWT token
curl -X POST "http://localhost:8003/api/v1/products/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -d '{"name":"Test Product","price":99.99,"category":"Test"}'
# Response: {"id":1,"name":"Test Product",...}
```

### **Bước 4: Test JWT Token Expiration**

```bash
# Test với expired token
curl -X POST "http://localhost:8003/api/v1/products/" \
  -H "Authorization: Bearer <expired_token>" \
  -d '{...}'
# Response: {"detail":"Token đã hết hạn"}

# Test với invalid token
curl -X POST "http://localhost:8003/api/v1/products/" \
  -H "Authorization: Bearer invalid_token" \
  -d '{...}'
# Response: {"detail":"Token không hợp lệ"}
```

## 🔧 Advanced JWT Features

### **1. Get Full User Info from JWT**

```python
from libs.auth.jwt_utils import get_current_user_payload

@router.post("/items/")
async def create_item(
    item_data: ItemCreate,
    current_user: dict = Depends(get_current_user_payload),  # Full JWT payload
    service: ItemService = Depends(get_item_service)
):
    # current_user contains: {"sub": "user_id", "username": "...", "email": "...", "is_superuser": false}
    user_id = int(current_user["sub"])
    username = current_user["username"]
    is_superuser = current_user["is_superuser"]
    
    # Use user info in business logic
    return service.create_item(item_data, created_by=user_id)
```

### **2. Role-based Access Control**

```python
def require_superuser(current_user: dict = Depends(get_current_user_payload)):
    """Dependency để yêu cầu quyền superuser"""
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập"
        )
    return current_user

@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    current_user: dict = Depends(require_superuser),  # Chỉ superuser mới được xóa
    service: ItemService = Depends(get_item_service)
):
    return service.delete_item(item_id)
```

### **3. Optional Authentication**

```python
from fastapi.security import HTTPBearer
from fastapi import Request

security = HTTPBearer(auto_error=False)  # auto_error=False để không throw exception

@router.get("/items/")
async def get_items(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: ItemService = Depends(get_item_service)
):
    """
    Endpoint với optional authentication
    - Nếu có JWT token: trả về items của user đó
    - Nếu không có JWT token: trả về public items
    """
    current_user_id = None
    
    if credentials:
        try:
            from libs.auth.jwt_utils import get_jwt_manager
            jwt_manager = get_jwt_manager()
            payload = jwt_manager.verify_token(credentials.credentials, "access")
            current_user_id = int(payload["sub"])
        except:
            pass  # Ignore invalid tokens
    
    return service.get_items(user_id=current_user_id)
```

## 🛡️ Security Best Practices

### **1. JWT Token Security**
- ✅ Use HTTPS in production
- ✅ Set appropriate token expiration times
- ✅ Implement refresh token rotation
- ✅ Store JWT secret securely (environment variables)
- ✅ Validate token signature and expiration

### **2. Error Handling**
```python
# Good: Generic error messages
{"detail": "Not authenticated"}
{"detail": "Token đã hết hạn"}

# Bad: Specific error messages that leak info
{"detail": "User with ID 123 not found"}
{"detail": "JWT signature verification failed with key ABC"}
```

### **3. Rate Limiting**
```python
# Implement rate limiting for auth endpoints
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(...):
    pass
```

## 📊 JWT Authentication Status

### **✅ Services với JWT Protection:**

| Service | Port | Status | Protected Endpoints |
|---------|------|--------|-------------------|
| Auth Service | 8001 | ✅ Complete | All admin endpoints |
| Products Service | 8003 | ✅ Integrated | POST, PUT, DELETE, PATCH |

### **🔄 Services cần tích hợp JWT:**

| Service | Port | Status | Priority |
|---------|------|--------|----------|
| Articles Service | 8002 | ⏳ Pending | High |
| User Service | 8004 | ⏳ Pending | Medium |
| Roles Service | 8005 | ⏳ Pending | Low |

## 🎯 Integration Checklist

Khi tích hợp JWT authentication vào service mới:

### **✅ Code Changes:**
- [ ] Import `get_current_user_id` từ `libs.auth.jwt_utils`
- [ ] Thêm `current_user_id: int = Depends(get_current_user_id)` vào protected endpoints
- [ ] Cập nhật API documentation với authentication requirements
- [ ] Test các endpoints với và không có JWT token

### **✅ Testing:**
- [ ] Test public endpoints (GET) hoạt động không cần JWT
- [ ] Test protected endpoints (POST/PUT/DELETE) yêu cầu JWT
- [ ] Test với JWT token hợp lệ
- [ ] Test với JWT token hết hạn
- [ ] Test với JWT token không hợp lệ
- [ ] Test error responses đúng format

### **✅ Documentation:**
- [ ] Cập nhật API docs với authentication requirements
- [ ] Thêm examples cho JWT token usage
- [ ] Document error responses
- [ ] Update service README

## 🚀 Next Steps

1. **Complete Products Service JWT Integration** - Debug và hoàn thiện JWT protection
2. **Apply to Other Services** - Tích hợp JWT vào Articles, User, Roles services
3. **Implement Advanced Features** - Role-based access control, optional auth
4. **Security Hardening** - Rate limiting, token rotation, security headers
5. **Monitoring & Logging** - JWT usage analytics, failed auth attempts

## 🎉 Benefits of JWT Authentication

### **✅ Security:**
- Stateless authentication
- Token-based authorization
- Secure API access control
- User session management

### **✅ Scalability:**
- No server-side session storage
- Microservice-friendly
- Horizontal scaling support
- Distributed authentication

### **✅ Developer Experience:**
- Consistent auth pattern across services
- Easy to test with tools like Postman
- Clear error messages
- Comprehensive documentation

JWT Authentication framework này đã được thiết kế và implement để cung cấp security layer mạnh mẽ và scalable cho toàn bộ FastAPI monorepo! 🔐
