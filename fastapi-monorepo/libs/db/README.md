# Database Configuration cho FastAPI Microservices

## 🏗️ Kiến trúc Database

File `session.py` đã được tối ưu hoá cho microservice architecture với các tính năng:

### ✅ Cải thiện chính:

1. **DatabaseManager Class**: Quản lý database connection một cách có tổ chức
2. **Connection Pooling**: Tối ưu performance với QueuePool
3. **Environment-based Configuration**: Linh hoạt cho từng service
4. **Health Check**: Endpoint để kiểm tra trạng thái database
5. **Logging & Monitoring**: Theo dõi và debug dễ dàng
6. **Error Handling**: Xử lý lỗi toàn diện
7. **Security**: Mask password trong logs

## 🔧 Cấu hình Environment Variables

Mỗi service cần có file `.env` với các biến sau:

```env
# Database connection
DB_USERNAME=postgres
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=5433
DB_NAME=<service_name>db  # authdb, articlesdb, userdb, etc.

# Service identification
SERVICE_NAME=<service_name>-service

# Debugging (optional)
DB_ECHO=false              # Log SQL queries
DB_ECHO_POOL=false         # Log connection pool events
DB_LOG_QUERIES=false       # Log query details
```

## 📝 Cách sử dụng trong FastAPI Service

### 1. Basic Usage (Backward Compatible)

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from libs.db.session import get_db

app = FastAPI()

@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    # Sử dụng database session
    return db.query(User).all()
```

### 2. Advanced Usage với DatabaseManager

```python
from fastapi import FastAPI
from libs.db.session import DatabaseManager

# Khởi tạo database manager riêng cho service
db_manager = DatabaseManager()

app = FastAPI()

@app.get("/health/db")
def database_health():
    """Health check endpoint cho database"""
    is_healthy = db_manager.health_check()
    return {"database": "healthy" if is_healthy else "unhealthy"}

@app.on_event("shutdown")
def shutdown_event():
    """Đóng database connections khi shutdown"""
    db_manager.close()
```

### 3. Custom Database URL

```python
from libs.db.session import DatabaseManager

# Sử dụng custom database URL
custom_db_manager = DatabaseManager(
    database_url="postgresql://user:pass@host:port/dbname"
)
```

## 🚀 Connection Pool Configuration

Các tham số connection pool đã được tối ưu:

```python
pool_size=10          # 10 connections cơ bản
max_overflow=20       # Tối đa 30 connections (10 + 20)
pool_pre_ping=True    # Kiểm tra connection trước khi dùng
pool_recycle=3600     # Recycle connection sau 1 giờ
pool_timeout=30       # Timeout 30s khi lấy connection
```

## 📊 Monitoring & Debugging

### Environment Variables cho Debug:

```env
DB_ECHO=true              # Log tất cả SQL queries
DB_ECHO_POOL=true         # Log connection pool events
DB_LOG_QUERIES=true       # Log chi tiết queries
```

### Health Check Endpoint:

```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": db_manager.health_check()
    }
```

## 🔒 Security Features

1. **Password Masking**: Passwords được mask trong logs
2. **Connection Timeout**: Tránh hanging connections
3. **Application Name**: Identify service trong PostgreSQL logs

## 📋 Best Practices

### 1. Service-specific Database

```
services/
├── auth/     → authdb
├── articles/ → articlesdb  
├── user/     → userdb
└── roles/    → rolesdb
```

### 2. Environment Configuration

Mỗi service có file `.env` riêng với `DB_NAME` khác nhau:

```env
# services/auth/.env
DB_NAME=authdb

# services/articles/.env  
DB_NAME=articlesdb
```

### 3. Graceful Shutdown

```python
@app.on_event("shutdown")
def shutdown_event():
    db_manager.close()
```

## 🐛 Troubleshooting

### Connection Pool Exhausted

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached
```

**Giải pháp**: Tăng `pool_size` hoặc `max_overflow` trong `DatabaseManager`

### Connection Timeout

```
psycopg2.OperationalError: timeout expired
```

**Giải pháp**: Tăng `connect_timeout` trong `connect_args`

### Memory Leaks

**Giải pháp**: Đảm bảo gọi `db_manager.close()` khi shutdown

## 🔄 Migration từ Code Cũ

Nếu service đang dùng code cũ:

```python
# Cũ
from libs.db.session import engine, SessionLocal, get_db

# Mới (backward compatible)
from libs.db.session import get_engine, get_session_local, get_db

engine = get_engine()
SessionLocal = get_session_local()
```

## 📈 Performance Tips

1. **Sử dụng `expire_on_commit=False`** để tránh lazy loading issues
2. **Set `pool_pre_ping=True`** để tránh stale connections  
3. **Monitor connection pool** với `DB_ECHO_POOL=true`
4. **Implement health checks** để monitoring
5. **Use connection timeouts** để tránh hanging requests
