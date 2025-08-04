"""
FastAPI App Factory - Tạo FastAPI app với cấu hình chung
Cung cấp factory function để tạo FastAPI app với middleware và config chuẩn
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
import os
from typing import List, Optional
from datetime import datetime

from libs.db.session import db_manager
from libs.common.base_schema import ErrorResponse

logger = logging.getLogger(__name__)


def create_app(
    title: str,
    description: str = "",
    version: str = "1.0.0",
    cors_origins: List[str] = None,
    include_health_check: bool = True,
    include_root_endpoint: bool = True
) -> FastAPI:
    """
    Factory function để tạo FastAPI app với cấu hình chuẩn
    
    Args:
        title: Tên của service
        description: Mô tả service
        version: Phiên bản service
        cors_origins: Danh sách origins cho CORS (default: ["*"])
        include_health_check: Có bao gồm health check endpoint không
        include_root_endpoint: Có bao gồm root endpoint không
        
    Returns:
        FastAPI app đã được cấu hình
    """
    
    # Create FastAPI app
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Configure CORS
    if cors_origins is None:
        cors_origins = ["*"]  # Trong production nên specify origins cụ thể
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Add common endpoints
    if include_root_endpoint:
        add_root_endpoint(app, title, version)
    
    if include_health_check:
        add_health_check_endpoint(app, title, version)
    
    # Add startup and shutdown events
    add_lifecycle_events(app, title)
    
    return app


def add_exception_handlers(app: FastAPI):
    """Thêm exception handlers chung cho app"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handler cho lỗi validation"""
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        
        error_details = []
        for error in exc.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            message = error["msg"]
            error_details.append(f"{field}: {message}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Dữ liệu đầu vào không hợp lệ",
                "error": "Validation Error",
                "errors": error_details,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handler cho lỗi database"""
        logger.error(f"Database error on {request.url}: {str(exc)}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Lỗi hệ thống database",
                "error": "Database Error",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handler cho lỗi chung"""
        logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Lỗi hệ thống",
                "error": "Internal server error",
                "timestamp": datetime.now().isoformat()
            }
        )


def add_root_endpoint(app: FastAPI, title: str, version: str):
    """Thêm root endpoint cho app"""
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint - thông tin cơ bản về service"""
        return {
            "message": f"{title} API",
            "version": version,
            "docs": "/docs",
            "health": "/health"
        }


def add_health_check_endpoint(app: FastAPI, title: str, version: str):
    """Thêm health check endpoint cho app"""
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint - kiểm tra trạng thái service và database
        
        Returns:
            Dict với thông tin health status
        """
        # Check database health
        db_status = db_manager.health_check()
        
        # Determine overall status
        overall_status = "healthy" if db_status == "connected" else "unhealthy"
        
        return {
            "status": overall_status,
            "service": title.lower().replace(" ", "-"),
            "version": version,
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }


def add_lifecycle_events(app: FastAPI, title: str):
    """Thêm startup và shutdown events cho app"""
    
    @app.on_event("startup")
    async def startup_event():
        """Event khi service khởi động"""
        logger.info(f"🚀 {title} started successfully!")
        logger.info(f"📊 Database status: {db_manager.health_check()}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Event khi service tắt"""
        logger.info(f"🛑 {title} shutting down...")
        # Cleanup resources if needed
        db_manager.close_all_connections()


def setup_logging(service_name: str, log_level: str = "INFO"):
    """
    Setup logging configuration cho service
    
    Args:
        service_name: Tên service để đặt tên logger
        log_level: Level logging (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            # Có thể thêm FileHandler nếu cần log vào file
        ]
    )
    
    # Set SQLAlchemy logging level
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
