# Products Service - Hướng dẫn hoàn chỉnh

## 🎯 Tổng quan

Service Products là một **microservice hoàn chỉnh** trong FastAPI monorepo, được thiết kế để quản lý sản phẩm với đầy đủ các tính năng CRUD, validation, error handling, và database integration.

## 🏗️ Kiến trúc Service

```
services/products/
├── .env                          # Environment variables
├── main.py                       # FastAPI application entry point
├── alembic.ini                   # Alembic configuration
├── alembic/                      # Database migrations
│   ├── env.py                    # Alembic environment
│   └── versions/                 # Migration files
└── app/
    ├── __init__.py
    ├── models/                   # SQLAlchemy models
    │   ├── __init__.py
    │   └── product.py            # Product model
    ├── schemas/                  # Pydantic schemas
    │   ├── __init__.py
    │   └── product.py            # API schemas
    ├── services/                 # Business logic
    │   ├── __init__.py
    │   └── product_service.py    # Product service
    └── routers/                  # API endpoints
        ├── __init__.py
        └── products.py           # Product routes
```

## 📋 Hướng dẫn từng bước chi tiết

### **Bước 1: Environment Configuration**

File `.env` chứa cấu hình cho service:

```env
# Database Configuration
DB_USERNAME=postgres
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=5433
DB_NAME=productsdb

# Service Configuration
SERVICE_NAME=products-service
SERVICE_PORT=8003

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=Products Service
```

### **Bước 2: Database Model (SQLAlchemy)**

File `app/models/product.py` định nghĩa cấu trúc database:

```python
class Product(Base):
    __tablename__ = "products"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Product information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    
    # Status and inventory
    is_active = Column(Boolean, default=True)
    stock_quantity = Column(Integer, default=0)
    
    # Timestamps (auto-managed)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Đặc điểm quan trọng:**
- ✅ **Indexes**: Trên `name` và `category` để tối ưu query
- ✅ **Validation**: `nullable=False` cho required fields
- ✅ **Timestamps**: Auto-managed với `func.now()`
- ✅ **Decimal precision**: `Numeric(10, 2)` cho price

### **Bước 3: API Schemas (Pydantic)**

File `app/schemas/product.py` định nghĩa validation và serialization:

```python
class ProductCreate(ProductBase):
    """Schema cho tạo sản phẩm mới"""
    pass

class ProductUpdate(BaseModel):
    """Schema cho cập nhật (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    # ... other optional fields

class ProductResponse(ProductBase):
    """Schema cho API response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True  # Convert từ SQLAlchemy model
```

**Đặc điểm quan trọng:**
- ✅ **Validation**: `Field()` với constraints
- ✅ **Custom validators**: `@validator` cho business rules
- ✅ **Optional updates**: `ProductUpdate` với optional fields
- ✅ **ORM integration**: `orm_mode = True`

### **Bước 4: Business Logic (Service Layer)**

File `app/services/product_service.py` chứa business logic:

```python
class ProductService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_product(self, product_data: ProductCreate) -> Product:
        # Kiểm tra duplicate name
        # Tạo product mới
        # Handle exceptions
        
    def get_products(self, search_params: ProductSearchParams) -> tuple[List[Product], int]:
        # Build dynamic query với filters
        # Apply pagination
        # Return products + total count
```

**Đặc điểm quan trọng:**
- ✅ **Separation of concerns**: Business logic tách biệt khỏi API layer
- ✅ **Error handling**: Comprehensive exception handling
- ✅ **Logging**: Detailed logging cho debugging
- ✅ **Validation**: Business rule validation

### **Bước 5: API Endpoints (FastAPI Routes)**

File `app/routers/products.py` định nghĩa REST API:

```python
@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(product_data: ProductCreate, service: ProductService = Depends(get_product_service)):
    return service.create_product(product_data)

@router.get("/", response_model=ProductListResponse)
async def get_products(
    name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    # ... pagination params
    service: ProductService = Depends(get_product_service)
):
    # Handle search and pagination
```

**Đặc điểm quan trọng:**
- ✅ **RESTful design**: Standard HTTP methods và status codes
- ✅ **Dependency injection**: Service injection với `Depends()`
- ✅ **Query parameters**: Flexible search và pagination
- ✅ **Response models**: Consistent API responses

### **Bước 6: Main Application**

File `main.py` là entry point của service:

```python
app = FastAPI(
    title="Products Service",
    description="Microservice quản lý sản phẩm",
    version="1.0.0"
)

# Middleware
app.add_middleware(CORSMiddleware, ...)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(...):

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": db_manager.health_check()}
```

**Đặc điểm quan trọng:**
- ✅ **Global exception handling**: Consistent error responses
- ✅ **Health checks**: Database connectivity monitoring
- ✅ **CORS**: Cross-origin support
- ✅ **Startup/shutdown events**: Resource management

## 🚀 Cách chạy Service

### **1. Setup Database**

```bash
# Tạo database
python libs/db/create_databases.py

# Chạy migrations
cd services/products
alembic upgrade head
```

### **2. Start Service**

```bash
cd services/products
python main.py
```

Service sẽ chạy trên port 8003: http://localhost:8003

### **3. API Documentation**

- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **Health Check**: http://localhost:8003/health

## 📊 API Endpoints

### **Products CRUD**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/products/` | Tạo sản phẩm mới |
| GET | `/api/v1/products/{id}` | Lấy sản phẩm theo ID |
| GET | `/api/v1/products/` | Lấy danh sách sản phẩm (có search & pagination) |
| PUT | `/api/v1/products/{id}` | Cập nhật sản phẩm |
| DELETE | `/api/v1/products/{id}` | Xóa sản phẩm (soft delete) |

### **Inventory Management**

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/api/v1/products/{id}/stock?quantity_change=10` | Cập nhật tồn kho |

### **Category Filtering**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/products/category/{category_name}` | Lấy sản phẩm theo danh mục |

## 🔍 Ví dụ sử dụng API

### **1. Tạo sản phẩm mới**

```bash
curl -X POST "http://localhost:8003/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iPhone 15 Pro",
    "description": "Latest iPhone with advanced features",
    "price": 999.99,
    "category": "Electronics",
    "stock_quantity": 50
  }'
```

### **2. Tìm kiếm sản phẩm**

```bash
curl "http://localhost:8003/api/v1/products/?name=iPhone&category=Electronics&page=1&per_page=10"
```

### **3. Cập nhật tồn kho**

```bash
curl -X PATCH "http://localhost:8003/api/v1/products/1/stock?quantity_change=-5"
```

## 🛠️ Testing

### **Manual Testing với curl**

```bash
# Health check
curl http://localhost:8003/health

# Create product
curl -X POST http://localhost:8003/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Product", "price": 10.99, "category": "Test"}'

# Get products
curl http://localhost:8003/api/v1/products/
```

### **Testing với Swagger UI**

1. Mở http://localhost:8003/docs
2. Thử các endpoints trực tiếp trên UI
3. Xem request/response examples

## 🔧 Customization

### **Thêm field mới vào Product**

1. **Update Model** (`app/models/product.py`):
```python
class Product(Base):
    # ... existing fields
    brand = Column(String(100), nullable=True)  # New field
```

2. **Update Schemas** (`app/schemas/product.py`):
```python
class ProductBase(BaseModel):
    # ... existing fields
    brand: Optional[str] = Field(None, max_length=100)
```

3. **Create Migration**:
```bash
alembic revision --autogenerate -m "add brand field"
alembic upgrade head
```

### **Thêm endpoint mới**

1. **Update Service** (`app/services/product_service.py`):
```python
def get_products_by_brand(self, brand: str) -> List[Product]:
    return self.db.query(Product).filter(Product.brand == brand).all()
```

2. **Update Router** (`app/routers/products.py`):
```python
@router.get("/brand/{brand_name}")
async def get_products_by_brand(brand_name: str, service: ProductService = Depends(get_product_service)):
    return service.get_products_by_brand(brand_name)
```

## 📈 Performance Tips

1. **Database Indexing**: Thêm indexes cho các trường thường query
2. **Connection Pooling**: Đã được cấu hình trong `libs/db/session.py`
3. **Pagination**: Luôn sử dụng pagination cho large datasets
4. **Caching**: Có thể thêm Redis caching cho frequently accessed data

## 🔒 Security Considerations

1. **Input Validation**: Pydantic schemas validate tất cả inputs
2. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
3. **Error Handling**: Không expose sensitive information trong error messages
4. **CORS**: Configure properly cho production

## 📚 Tài liệu tham khảo

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

---

## 🎉 Kết luận

Service Products này là một **template hoàn chỉnh** cho việc phát triển microservices trong FastAPI monorepo. Nó bao gồm:

✅ **Complete CRUD operations**  
✅ **Database integration với Alembic**  
✅ **Comprehensive error handling**  
✅ **API documentation với Swagger**  
✅ **Health checks và monitoring**  
✅ **Scalable architecture**  
✅ **Production-ready configuration**  

Bạn có thể sử dụng service này làm template để tạo các services khác trong monorepo!
