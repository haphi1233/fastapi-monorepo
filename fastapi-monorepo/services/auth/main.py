"""
Authentication Service - Main Application
Sử dụng App Factory từ libs/common và Authentication routes
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import common libraries
from libs.common.app_factory import create_app, setup_logging
from .app.routers import auth

# Setup logging
setup_logging("auth-service")

# Create FastAPI app using factory
app = create_app(
    title=os.getenv("PROJECT_NAME", "Authentication Service"),
    description="Microservice xác thực và quản lý người dùng trong FastAPI Monorepo",
    version="1.0.0",
    cors_origins=["*"],  # Trong production nên specify origins cụ thể
    include_health_check=True,
    include_root_endpoint=True
)

# Include API routes
api_v1_prefix = os.getenv("API_V1_STR", "/api/v1")
app.include_router(auth.router, prefix=api_v1_prefix)

# Run server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
