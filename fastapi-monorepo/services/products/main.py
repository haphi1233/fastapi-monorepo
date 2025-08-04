"""
Products Service - Main Application
Entry point cho Products microservice
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add path to monorepo root
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import routers
from app.routers import products

# Import database
from libs.db.session import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=os.getenv("PROJECT_NAME", "Products Service"),
    description="Microservice quản lý sản phẩm trong FastAPI Monorepo",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên specify origins cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
api_v1_prefix = os.getenv("API_V1_STR", "/api/v1")
app.include_router(products.router, prefix=api_v1_prefix)

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Dữ liệu không hợp lệ",
            "errors": exc.errors()
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database errors"""
    logger.error(f"Database error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Lỗi cơ sở dữ liệu",
            "error": "Database connection error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Lỗi hệ thống",
            "error": "Internal server error"
        }
    )

# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint
    Kiểm tra trạng thái service và database connection
    """
    try:
        # Check database connection
        db_healthy = db_manager.health_check()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "service": "products-service",
            "version": "1.0.0",
            "database": "connected" if db_healthy else "disconnected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "products-service",
                "error": str(e)
            }
        )

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint
    Thông tin cơ bản về service
    """
    return {
        "message": "Products Service API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """
    Startup event
    Khởi tạo các resources cần thiết khi start service
    """
    logger.info("🚀 Starting Products Service...")
    logger.info(f"📊 Database URL: {db_manager._mask_password(db_manager.database_url)}")
    logger.info(f"🔧 Service Port: {os.getenv('SERVICE_PORT', '8003')}")
    logger.info("✅ Products Service started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event  
    Cleanup resources khi shutdown service
    """
    logger.info("🛑 Shutting down Products Service...")
    
    # Close database connections
    db_manager.close()
    
    logger.info("✅ Products Service shutdown completed!")

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SERVICE_PORT", 8003))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Chỉ dùng trong development
        log_level="info"
    )
