# 📚 HƯỚNG DẪN KHỞI ĐỘNG FASTAPI MONOREPO

## 🎯 Giới Thiệu Dự Án

Đây là một hệ thống **Microservices** sử dụng **FastAPI**, bao gồm:

1. **Auth Service** (Port 8001): Quản lý xác thực và người dùng
2. **Articles Service** (Port 8002): Quản lý bài viết
3. **Products Service** (Port 8003): Quản lý sản phẩm  
4. **API Gateway** (Port 8080): Cổng giao tiếp chính, tổng hợp tất cả services

## 📋 Yêu Cầu Hệ Thống

### 1. Cài đặt Python
- Python 3.8 trở lên
- Kiểm tra: `python --version`

### 2. Cài đặt PostgreSQL
- PostgreSQL 12 trở lên
- Mặc định chạy trên port 5432 hoặc 5433
- Tạo các database:
  ```sql
  CREATE DATABASE authdb;
  CREATE DATABASE articlesdb;
  CREATE DATABASE productsdb;
  ```

### 3. Cài đặt Redis (Tùy chọn)
- Dùng cho event bus và caching
- Mặc định port 6379

## 🚀 Cách Khởi Động Nhanh

### Bước 1: Cài đặt Dependencies
```bash
cd d:\work\source_code\fastapi-monorepo\fastapi-monorepo
pip install -r requirements.txt
```

### Bước 2: Cấu hình Environment Variables
Tạo file `.env` trong thư mục gốc:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
AUTH_DATABASE_URL=postgresql://user:password@localhost:5433/authdb
ARTICLES_DATABASE_URL=postgresql://user:password@localhost:5433/articlesdb
PRODUCTS_DATABASE_URL=postgresql://user:password@localhost:5433/productsdb

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# Service Ports
SERVICE_PORT=8001  # Auth
ARTICLES_PORT=8002
PRODUCTS_PORT=8003
GATEWAY_PORT=8080

# Redis (optional)
REDIS_URL=redis://localhost:6379
```

### Bước 3: Khởi động Services

#### Cách 1: Dùng Script Tự Động (Khuyến nghị)
```bash
# Khởi động tất cả services cùng lúc
python start_all.py
```

#### Cách 2: Khởi động Thủ công từng Service
```bash
# Terminal 1 - Auth Service
cd services/auth
python start.py

# Terminal 2 - Articles Service  
cd services/articles
python start.py

# Terminal 3 - Products Service
cd services/products
python start.py

# Terminal 4 - API Gateway
cd d:\work\source_code\fastapi-monorepo\fastapi-monorepo
python start_gateway.py
```

## 🌐 Truy cập Hệ thống

Sau khi khởi động thành công, bạn có thể truy cập:

### API Gateway (Điểm truy cập chính)
- **URL**: http://localhost:8080
- **Swagger UI**: http://localhost:8080/docs
- **Dashboard**: http://localhost:8080/dashboard
- **Health Check**: http://localhost:8080/health

### Các Service riêng lẻ (Development)
- **Auth Service**: http://localhost:8001/docs
- **Articles Service**: http://localhost:8002/docs  
- **Products Service**: http://localhost:8003/docs

## 📖 Cấu trúc Dự án

```
fastapi-monorepo/
├── libs/                   # Thư viện dùng chung
│   ├── common/            # Utilities chung
│   ├── auth/              # JWT, authentication
│   ├── db/                # Database utilities
│   ├── events/            # Event bus
│   ├── http_client/       # HTTP client
│   └── api_gateway/       # Gateway components
├── services/              # Các microservices
│   ├── auth/             # Auth service
│   ├── articles/         # Articles service
│   └── products/         # Products service
├── gateway_main.py        # API Gateway entry point
└── start_all.py          # Script khởi động tất cả

```

## 🔧 Xử lý Lỗi Thường Gặp

### 1. Lỗi "ModuleNotFoundError: No module named 'libs'"
- Nguyên nhân: Thiếu PYTHONPATH
- Giải pháp: Dùng script `start.py` đã cấu hình sẵn

### 2. Lỗi "Database connection failed"
- Nguyên nhân: PostgreSQL chưa chạy hoặc sai thông tin kết nối
- Giải pháp: 
  - Kiểm tra PostgreSQL: `pg_isready`
  - Kiểm tra file `.env`

### 3. Lỗi "Port already in use"
- Nguyên nhân: Port đã được sử dụng
- Giải pháp:
  ```bash
  # Windows
  netstat -ano | findstr :8001
  taskkill /PID <PID> /F
  
  # Linux/Mac
  lsof -i :8001
  kill -9 <PID>
  ```

## 📚 Tài liệu API

### Authentication
Tất cả API cần JWT token (trừ public endpoints):
```http
Authorization: Bearer <your-jwt-token>
```

### Lấy Token
```http
POST http://localhost:8080/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

### Ví dụ Gọi API
```http
# Tạo sản phẩm mới
POST http://localhost:8080/api/v1/products
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Product 1",
  "price": 100000,
  "description": "Description"
}
```

## 🎯 Next Steps

1. **Development**: Xem code các services trong `services/`
2. **Testing**: Chạy tests với `pytest`
3. **Monitoring**: Xem dashboard tại http://localhost:8080/dashboard
4. **API Docs**: Khám phá API tại http://localhost:8080/docs

## 📞 Hỗ trợ

Nếu gặp vấn đề, hãy:
1. Kiểm tra logs trong terminal
2. Xem file `.env` đã cấu hình đúng chưa
3. Đảm bảo PostgreSQL và Redis đang chạy
4. Thử restart lại services

---
🚀 **Happy Coding!**
