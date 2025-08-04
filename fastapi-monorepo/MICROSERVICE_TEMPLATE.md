# 🎯 FastAPI Microservice Template - Hướng dẫn hoàn chỉnh

## 📋 Tổng quan

Đây là **template hoàn chỉnh** để tạo microservice trong FastAPI monorepo. Template này đã được test và hoạt động 100% với service **Products** làm ví dụ mẫu.

## 🏗️ Kiến trúc Microservice

```
services/<service_name>/
├── .env                          # Environment configuration
├── main.py                       # FastAPI application entry point
├── alembic.ini                   # Database migration config
├── alembic/                      # Database migrations
│   ├── env.py                    # Migration environment
│   └── versions/                 # Migration files
└── app/
    ├── __init__.py
    ├── models/                   # SQLAlchemy database models
    │   ├── __init__.py
    │   └── <model_name>.py
    ├── schemas/                  # Pydantic API schemas
    │   ├── __init__.py
    │   └── <schema_name>.py
    ├── services/                 # Business logic layer
    │   ├── __init__.py
    │   └── <service_name>_service.py
    └── routers/                  # API endpoints
        ├── __init__.py
        └── <router_name>.py
```

## 🚀 Quy trình tạo Service mới (Step-by-step)

### **Bước 1: Tạo cấu trúc thư mục**

```bash
mkdir -p services/<service_name>/app/{models,schemas,routers,services}
```

### **Bước 2: Tạo Environment Configuration**

Tạo file `services/<service_name>/.env`:

```env
# Database Configuration
DB_USERNAME=postgres
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=5433
DB_NAME=<service_name>db

# Service Configuration
SERVICE_NAME=<service_name>-service
SERVICE_PORT=800X  # X = unique port number

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=<Service Name> Service
```

### **Bước 3: Tạo Database Model**

Tạo file `app/models/<model_name>.py`:

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from libs.db.session import Base

class <ModelName>(Base):
    __tablename__ = "<table_name>"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Add your fields here
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### **Bước 4: Tạo Pydantic Schemas**

Tạo file `app/schemas/<schema_name>.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class <ModelName>Base(BaseModel):
    # Define base fields with validation
    pass

class <ModelName>Create(<ModelName>Base):
    pass

class <ModelName>Update(BaseModel):
    # All fields optional for partial updates
    pass

class <ModelName>Response(<ModelName>Base):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
```

### **Bước 5: Tạo Service Layer**

Tạo file `app/services/<service_name>_service.py`:

```python
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from app.models.<model_name> import <ModelName>
from app.schemas.<schema_name> import <ModelName>Create, <ModelName>Update

logger = logging.getLogger(__name__)

class <ServiceName>Service:
    def __init__(self, db: Session):
        self.db = db
    
    def create_<item>(self, data: <ModelName>Create) -> <ModelName>:
        # Implement create logic
        pass
    
    def get_<item>(self, item_id: int) -> <ModelName>:
        # Implement get logic
        pass
    
    # Add other CRUD methods
```

### **Bước 6: Tạo API Routes**

Tạo file `app/routers/<router_name>.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.db.session import get_db
from app.services.<service_name>_service import <ServiceName>Service
from app.schemas.<schema_name> import <ModelName>Create, <ModelName>Response

router = APIRouter(prefix="/<items>", tags=["<items>"])

def get_<service_name>_service(db: Session = Depends(get_db)) -> <ServiceName>Service:
    return <ServiceName>Service(db)

@router.post("/", response_model=<ModelName>Response, status_code=201)
async def create_<item>(data: <ModelName>Create, service: <ServiceName>Service = Depends(get_<service_name>_service)):
    return service.create_<item>(data)

# Add other endpoints
```

### **Bước 7: Tạo Main Application**

Tạo file `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.routers import <router_name>
from libs.db.session import db_manager

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "<Service Name> Service"),
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

api_v1_prefix = os.getenv("API_V1_STR", "/api/v1")
app.include_router(<router_name>.router, prefix=api_v1_prefix)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": db_manager.health_check()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
```

### **Bước 8: Setup Database Migration**

```bash
# Tạo database
python libs/db/create_databases.py

# Setup Alembic
python libs/alembic/setup_alembic.py <service_name>

# Sửa import trong alembic/env.py
# from services.<service_name>.app.models.<model_name> import <ModelName>

# Tạo migration
cd services/<service_name>
alembic revision --autogenerate -m "create <table_name> table"
alembic upgrade head
```

### **Bước 9: Tạo __init__.py files**

```bash
touch app/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/routers/__init__.py
```

### **Bước 10: Test Service**

```bash
# Start service
cd services/<service_name>
python main.py

# Test endpoints
curl http://localhost:800X/health
curl http://localhost:800X/docs
curl -X POST http://localhost:800X/api/v1/<items>/ -H "Content-Type: application/json" -d '{...}'
```

## ✅ Service Products - Ví dụ hoàn chỉnh

Service **Products** đã được tạo và test thành công với tất cả các tính năng:

### **🎯 Các API đã test thành công:**

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/` | ✅ | Root endpoint |
| GET | `/health` | ✅ | Health check |
| GET | `/docs` | ✅ | Swagger documentation |
| POST | `/api/v1/products/` | ✅ | Tạo sản phẩm mới |
| GET | `/api/v1/products/{id}` | ✅ | Lấy sản phẩm theo ID |
| PUT | `/api/v1/products/{id}` | ✅ | Cập nhật sản phẩm |
| DELETE | `/api/v1/products/{id}` | ✅ | Xóa sản phẩm (soft delete) |
| PATCH | `/api/v1/products/{id}/stock` | ✅ | Cập nhật tồn kho |

### **🧪 Test Results:**

```bash
# ✅ Tạo sản phẩm thành công
curl -X POST "http://localhost:8003/api/v1/products/" \
  -d '{"name":"Test Product","price":10.99,"category":"Test"}'
# Response: {"id":1,"name":"Test Product",...}

# ✅ Lấy sản phẩm thành công  
curl "http://localhost:8003/api/v1/products/1"
# Response: {"id":1,"name":"Test Product",...}

# ✅ Cập nhật sản phẩm thành công
curl -X PUT "http://localhost:8003/api/v1/products/2" \
  -d '{"price":899.99,"stock_quantity":75}'
# Response: {"id":2,"price":899.99,"stock_quantity":75,...}

# ✅ Cập nhật tồn kho thành công
curl -X PATCH "http://localhost:8003/api/v1/products/2/stock?quantity_change=-10"
# Response: {"id":2,"stock_quantity":65,...}

# ✅ Xóa sản phẩm thành công (soft delete)
curl -X DELETE "http://localhost:8003/api/v1/products/1"
# Response: 204 No Content
```

## 🔧 Shared Libraries đã tối ưu

### **Database Layer (`libs/db/session.py`)**
- ✅ Connection pooling với QueuePool
- ✅ Health check functionality  
- ✅ Environment-based configuration
- ✅ Comprehensive error handling
- ✅ Logging và monitoring

### **Alembic Templates (`libs/alembic/`)**
- ✅ Template cho `alembic.ini`
- ✅ Template cho `env.py`
- ✅ Setup script tự động
- ✅ Environment variables support

### **Database Creation (`libs/db/create_databases.py`)**
- ✅ Tự động tạo databases cho các services
- ✅ Error handling và logging
- ✅ Duplicate detection

## 📊 Architecture Benefits

### **✅ Microservice Advantages:**
- **Isolation**: Mỗi service có database riêng
- **Scalability**: Scale từng service độc lập
- **Technology flexibility**: Mỗi service có thể dùng tech stack khác
- **Team autonomy**: Teams phát triển độc lập
- **Fault tolerance**: Lỗi ở 1 service không ảnh hưởng toàn bộ

### **✅ Code Quality:**
- **Separation of concerns**: Model/Schema/Service/Router tách biệt
- **Type safety**: Pydantic validation và SQLAlchemy typing
- **Error handling**: Comprehensive exception handling
- **Logging**: Detailed logging cho debugging
- **Documentation**: Auto-generated API docs

### **✅ Development Experience:**
- **Hot reload**: FastAPI auto-reload trong development
- **API documentation**: Swagger UI và ReDoc
- **Health checks**: Monitoring và debugging
- **Environment-based config**: Flexible deployment

## 🎉 Kết luận

Template này cung cấp một **foundation hoàn chỉnh** để phát triển microservices trong FastAPI monorepo:

✅ **Production-ready architecture**  
✅ **Comprehensive testing** (đã test với Products service)  
✅ **Scalable database design** (per-service databases)  
✅ **Modern development practices** (type hints, validation, logging)  
✅ **Complete documentation** (API docs, README, step-by-step guides)  
✅ **Automated tooling** (migration setup, database creation)  

Bạn có thể sử dụng template này để tạo bất kỳ service nào trong monorepo một cách nhanh chóng và đáng tin cậy! 🚀
