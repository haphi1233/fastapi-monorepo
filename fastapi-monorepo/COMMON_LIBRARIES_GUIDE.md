# 🏗️ Common Libraries Guide - Hướng dẫn sử dụng thư viện chung

## 📋 Tổng quan

Tài liệu này hướng dẫn cách sử dụng các **Common Libraries** đã được chuẩn hóa trong FastAPI monorepo để tránh code duplication và tăng tính maintainability.

## 🎯 Các Common Libraries đã được tạo

### **1. `libs/common/` - Base Components**

#### **BaseModel (`libs/common/base_model.py`)**
Base SQLAlchemy model với các trường chung cho tất cả tables:

```python
from libs.common.base_model import BaseModel

class Product(BaseModel):
    __tablename__ = "products"
    
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    # id, created_at, updated_at, is_active đã có sẵn từ BaseModel
```

**Tính năng có sẵn:**
- `id`: Primary key tự động tăng
- `created_at`: Timestamp tạo record  
- `updated_at`: Timestamp cập nhật record (tự động update)
- `is_active`: Soft delete flag
- `soft_delete()`: Method để soft delete
- `restore()`: Method để khôi phục record

#### **BaseSchema (`libs/common/base_schema.py`)**
Base Pydantic schemas với config chung:

```python
from libs.common.base_schema import BaseSchema, BaseResponse, BaseCreate, BaseUpdate

class ProductBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseUpdate):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)

class ProductResponse(BaseResponse):
    name: str
    price: float
    # id, created_at, updated_at, is_active đã có sẵn từ BaseResponse
```

**Schemas có sẵn:**
- `BaseSchema`: Base với config chung (from_attributes=True)
- `BaseResponse`: Response với id và timestamps
- `BaseCreate`: Base cho tạo mới
- `BaseUpdate`: Base cho cập nhật (tất cả fields optional)
- `PaginationParams`: Pagination parameters
- `SearchParams`: Search + pagination parameters
- `ListResponse`: List response với pagination info
- `APIResponse`: Standard API response wrapper
- `ErrorResponse`: Error response schema

#### **BaseService (`libs/common/base_service.py`)**
Base service class với CRUD operations chuẩn:

```python
from libs.common.base_service import BaseService
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductSearchParams

class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    def __init__(self, db: Session):
        super().__init__(Product, db)
    
    # Các methods có sẵn:
    # - create(data) -> Model
    # - get_by_id(id) -> Model | None
    # - get_by_id_or_404(id) -> Model
    # - update(id, data) -> Model
    # - delete(id, soft_delete=True) -> bool
    # - get_list(search_params) -> tuple[List[Model], int]
    # - restore(id) -> Model
    # - bulk_delete(ids, soft_delete=True) -> int
    
    def _apply_search_filter(self, query, search_term: str):
        # Override để implement search logic cụ thể
        return query.filter(Product.name.ilike(f"%{search_term}%"))
```

#### **App Factory (`libs/common/app_factory.py`)**
Factory function để tạo FastAPI app với cấu hình chuẩn:

```python
from libs.common.app_factory import create_app, setup_logging

# Setup logging
setup_logging("product-service")

# Create app
app = create_app(
    title="Product Service",
    description="Microservice quản lý sản phẩm",
    version="1.0.0",
    cors_origins=["*"],
    include_health_check=True,
    include_root_endpoint=True
)

# Include routes
app.include_router(product_router, prefix="/api/v1")
```

**Tính năng có sẵn:**
- CORS middleware
- Exception handlers (validation, database, general)
- Health check endpoint (`/health`)
- Root endpoint (`/`)
- Startup/shutdown events
- Logging configuration

### **2. `libs/auth/` - Authentication Components**

#### **JWT Utils (`libs/auth/jwt_utils.py`)**
JWT authentication utilities:

```python
from libs.auth.jwt_utils import JWTManager, PasswordManager, get_current_user_id

# Password hashing
password_manager = PasswordManager()
hashed = password_manager.hash_password("password123")
is_valid = password_manager.verify_password("password123", hashed)

# JWT tokens
jwt_manager = get_jwt_manager()  # Từ environment variables
access_token = jwt_manager.create_access_token({"sub": "user_id"})
refresh_token = jwt_manager.create_refresh_token({"sub": "user_id"})
payload = jwt_manager.verify_token(access_token, "access")

# FastAPI dependencies
@router.get("/protected")
async def protected_endpoint(current_user_id: int = Depends(get_current_user_id)):
    return {"user_id": current_user_id}
```

**Environment Variables cần thiết:**
```env
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### **3. `libs/db/` - Database Components**

#### **Database Manager (`libs/db/session.py`)**
Đã được tối ưu với connection pooling, health check, logging:

```python
from libs.db.session import get_db, db_manager

# FastAPI dependency
@router.post("/items/")
async def create_item(item_data: ItemCreate, db: Session = Depends(get_db)):
    # Use database session
    pass

# Health check
health_status = db_manager.health_check()  # "connected" | "disconnected"
```

#### **Alembic Setup (`libs/alembic/`)**
Automated Alembic setup cho services:

```bash
# Tạo database
python libs/db/create_databases.py

# Setup Alembic cho service mới
python libs/alembic/setup_alembic.py <service_name>

# Sửa import trong alembic/env.py
# from services.<service_name>.app.models.<model> import <Model>

# Tạo và chạy migration
cd services/<service_name>
alembic revision --autogenerate -m "create tables"
alembic upgrade head
```

## 🚀 Quy trình tạo Service mới với Common Libraries

### **Bước 1: Tạo cấu trúc và environment**

```bash
mkdir -p services/<service_name>/app/{models,schemas,routers,services}
touch services/<service_name>/app/{__init__.py,models/__init__.py,schemas/__init__.py,services/__init__.py,routers/__init__.py}
```

Tạo `.env`:
```env
DB_USERNAME=postgres
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=5433
DB_NAME=<service_name>db
SERVICE_NAME=<service_name>-service
SERVICE_PORT=800X
API_V1_STR=/api/v1
PROJECT_NAME=<Service Name> Service
```

### **Bước 2: Tạo Model sử dụng BaseModel**

```python
# app/models/<model_name>.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.common.base_model import BaseModel
from sqlalchemy import Column, String, Numeric

class Product(BaseModel):
    __tablename__ = "products"
    
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50), nullable=True)
```

### **Bước 3: Tạo Schemas sử dụng BaseSchema**

```python
# app/schemas/<schema_name>.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.common.base_schema import BaseSchema, BaseResponse, BaseCreate, BaseUpdate, SearchParams
from pydantic import Field
from typing import Optional

class ProductBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    category: Optional[str] = Field(None, max_length=50)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseUpdate):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, max_length=50)

class ProductResponse(BaseResponse):
    name: str
    price: float
    category: Optional[str]

class ProductSearchParams(SearchParams):
    name: Optional[str] = Field(None, description="Tìm theo tên")
    category: Optional[str] = Field(None, description="Lọc theo danh mục")
    min_price: Optional[float] = Field(None, ge=0, description="Giá tối thiểu")
    max_price: Optional[float] = Field(None, ge=0, description="Giá tối đa")
```

### **Bước 4: Tạo Service sử dụng BaseService**

```python
# app/services/<service_name>_service.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.common.base_service import BaseService
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductSearchParams

class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    def __init__(self, db: Session):
        super().__init__(Product, db)
    
    def _apply_search_filter(self, query, search_term: str):
        return query.filter(Product.name.ilike(f"%{search_term}%"))
    
    def get_products(self, search_params: ProductSearchParams) -> tuple[list[Product], int]:
        query = self.db.query(Product).filter(Product.is_active == True)
        
        # Apply custom filters
        filters = []
        if search_params.name:
            filters.append(Product.name.ilike(f"%{search_params.name}%"))
        if search_params.category:
            filters.append(Product.category.ilike(f"%{search_params.category}%"))
        if search_params.min_price is not None:
            filters.append(Product.price >= search_params.min_price)
        if search_params.max_price is not None:
            filters.append(Product.price <= search_params.max_price)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total and apply pagination
        total = query.count()
        offset = (search_params.page - 1) * search_params.per_page
        products = query.offset(offset).limit(search_params.per_page).all()
        
        return products, total
```

### **Bước 5: Tạo Router**

```python
# app/routers/<router_name>.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from libs.db.session import get_db
from libs.common.base_schema import ListResponse
from app.services.product_service import ProductService
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductSearchParams

router = APIRouter(prefix="/products", tags=["Products"])

def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    product = service.create(product_data)
    return ProductResponse.model_validate(product)

@router.get("/", response_model=ListResponse)
async def get_products(
    name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    service: ProductService = Depends(get_product_service)
):
    search_params = ProductSearchParams(
        name=name, category=category, min_price=min_price, max_price=max_price,
        page=page, per_page=per_page
    )
    
    products, total = service.get_products(search_params)
    product_responses = [ProductResponse.model_validate(p) for p in products]
    
    return ListResponse(
        items=product_responses,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0
    )

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    product = service.get_by_id_or_404(product_id)
    return ProductResponse.model_validate(product)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    service: ProductService = Depends(get_product_service)
):
    product = service.update(product_id, product_data)
    return ProductResponse.model_validate(product)

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    service.delete(product_id, soft_delete=True)
    return {"message": "Product đã được xóa thành công"}
```

### **Bước 6: Tạo Main App sử dụng App Factory**

```python
# main.py
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from libs.common.app_factory import create_app, setup_logging
from app.routers import products

# Setup logging
setup_logging(os.getenv("SERVICE_NAME", "service"))

# Create app
app = create_app(
    title=os.getenv("PROJECT_NAME", "Service"),
    description="Microservice description",
    version="1.0.0"
)

# Include routes
api_v1_prefix = os.getenv("API_V1_STR", "/api/v1")
app.include_router(products.router, prefix=api_v1_prefix)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
```

### **Bước 7: Setup Database và Migration**

```bash
# Tạo database
python libs/db/create_databases.py

# Setup Alembic
python libs/alembic/setup_alembic.py <service_name>

# Sửa import trong alembic/env.py
# from services.<service_name>.app.models.<model> import <Model>

# Tạo và chạy migration
cd services/<service_name>
alembic revision --autogenerate -m "create tables"
alembic upgrade head
```

### **Bước 8: Test Service**

```bash
# Start service
python main.py

# Test endpoints
curl http://localhost:800X/
curl http://localhost:800X/health
curl http://localhost:800X/docs
curl -X POST http://localhost:800X/api/v1/<items>/ -H "Content-Type: application/json" -d '{...}'
```

## ✅ Services đã áp dụng Common Libraries

### **1. Products Service** ✅
- ✅ Sử dụng BaseModel, BaseSchema, BaseService
- ✅ Sử dụng App Factory
- ✅ Test thành công tất cả APIs

### **2. Authentication Service** ✅
- ✅ Sử dụng BaseModel, BaseSchema, BaseService
- ✅ Sử dụng JWT Utils từ libs/auth
- ✅ Sử dụng App Factory
- ✅ Test thành công registration và login APIs

## 🎯 Lợi ích của Common Libraries

### **✅ Code Reusability**
- Giảm 70-80% code duplication
- Consistent patterns across services
- Faster development cho services mới

### **✅ Maintainability**
- Centralized bug fixes và improvements
- Easier refactoring
- Consistent error handling và logging

### **✅ Type Safety**
- Generic typing trong BaseService
- Pydantic validation consistency
- SQLAlchemy model consistency

### **✅ Developer Experience**
- Auto-generated API documentation
- Consistent API patterns
- Built-in health checks và monitoring

### **✅ Production Ready**
- Connection pooling
- Comprehensive error handling
- Security best practices (JWT, password hashing)
- Logging và monitoring

## 🔄 Migration từ Service cũ sang Common Libraries

### **Bước 1: Update Models**
```python
# Trước
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # ...

# Sau
from libs.common.base_model import BaseModel

class Product(BaseModel):
    __tablename__ = "products"
    # id, created_at, updated_at, is_active đã có sẵn
    # ...
```

### **Bước 2: Update Schemas**
```python
# Trước
class ProductResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    
    class Config:
        orm_mode = True

# Sau
from libs.common.base_schema import BaseResponse

class ProductResponse(BaseResponse):
    name: str
    # id, created_at, updated_at, is_active đã có sẵn
```

### **Bước 3: Update Service**
```python
# Trước
class ProductService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_product(self, data):
        # Manual CRUD implementation
        pass

# Sau
from libs.common.base_service import BaseService

class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    def __init__(self, db: Session):
        super().__init__(Product, db)
    # CRUD methods đã có sẵn
```

### **Bước 4: Update Main App**
```python
# Trước
app = FastAPI(title="Service")
app.add_middleware(CORSMiddleware, ...)
# Manual exception handlers
# Manual health check

# Sau
from libs.common.app_factory import create_app

app = create_app(
    title="Service",
    description="Description"
)
# Middleware, exception handlers, health check đã có sẵn
```

## 📚 Best Practices

### **1. Import Path**
Luôn thêm monorepo root vào sys.path:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
```

### **2. Environment Variables**
Sử dụng consistent naming:
```env
DB_USERNAME=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5433
DB_NAME=<service_name>db
SERVICE_NAME=<service_name>-service
SERVICE_PORT=800X
```

### **3. Generic Typing**
Sử dụng proper typing cho BaseService:
```python
class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    pass
```

### **4. Pydantic v2 Compatibility**
Sử dụng `model_validate` thay vì `from_orm`:
```python
return ProductResponse.model_validate(product)
```

### **5. Error Handling**
Để BaseService handle common errors, override khi cần:
```python
class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    def create(self, data: ProductCreate) -> Product:
        # Custom validation
        if self.db.query(Product).filter(Product.name == data.name).first():
            raise HTTPException(400, "Product name already exists")
        
        # Use parent method
        return super().create(data)
```

## 🎉 Kết luận

Common Libraries đã được thiết kế và implement thành công với:

✅ **Complete coverage**: Base classes cho Model, Schema, Service, App  
✅ **Production ready**: Error handling, logging, security, performance  
✅ **Developer friendly**: Easy to use, consistent patterns, good documentation  
✅ **Tested**: Đã test với Products và Authentication services  
✅ **Scalable**: Generic typing, extensible design  

Sử dụng Common Libraries giúp team phát triển services nhanh hơn, ít lỗi hơn và maintainable hơn! 🚀
