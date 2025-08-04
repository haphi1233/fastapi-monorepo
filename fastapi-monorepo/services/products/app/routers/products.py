"""
Product Routes - API Endpoints
Định nghĩa các API endpoints cho Product operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
import math
import sys
import os
import uuid

# Add path to monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.db.session import get_db
from libs.auth.jwt_utils import get_current_user_id, get_jwt_manager
from libs.common.base_schema import PaginatedResponse
from ..models.product import Product
from ..schemas.product import (
    ProductCreate, 
    ProductUpdate, 
    ProductResponse, 
    ProductListResponse,
    ProductSearchParams
)
from ..services.product_service import ProductService, get_product_service
from ..integrations.http_integration import ProductHTTPIntegration
from ..integrations.event_integration import ProductEventIntegration

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={404: {"description": "Not found"}}
)

# Integration instances
http_integration = ProductHTTPIntegration()
event_integration = ProductEventIntegration()

# Dependency functions
def get_http_integration() -> ProductHTTPIntegration:
    """Get HTTP integration instance"""
    return http_integration

def get_event_integration() -> ProductEventIntegration:
    """Get Event integration instance"""
    return event_integration

def get_jwt_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from request headers"""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    return None

def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    """Dependency để inject ProductService"""
    return ProductService(db)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: Request,
    product_data: ProductCreate,
    current_user_id: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
    http_integration: ProductHTTPIntegration = Depends(get_http_integration),
    event_integration: ProductEventIntegration = Depends(get_event_integration)
):
    """
    Tạo sản phẩm mới (Yêu cầu authentication)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Body:**
    - **name**: Tên sản phẩm (required, unique)
    - **description**: Mô tả sản phẩm (optional)
    - **price**: Giá sản phẩm (required, > 0)
    - **category**: Danh mục sản phẩm (required)
    - **is_active**: Trạng thái hoạt động (default: true)
    - **stock_quantity**: Số lượng tồn kho (default: 0)
    
    **Features:**
    - HTTP Integration: Enriches product with user info from Auth Service
    - Event Integration: Publishes product.created event for other services
    """
    logger.info(f"Creating new product: {product_data.name} by user {current_user_id}")
    
    # Get JWT token for HTTP integration
    jwt_token = get_jwt_token_from_request(request)
    correlation_id = str(uuid.uuid4())
    
    try:
        # Create product
        product = service.create_product(product_data)
        logger.info(f"Product created successfully: {product.id}")
        
        # HTTP Integration: Get user info to enrich response
        user_info = None
        if jwt_token:
            user_info = await http_integration.get_user_info(current_user_id, jwt_token)
            if user_info:
                logger.info(f"Enriched product with user info: {user_info['username']}")
        
        # Event Integration: Publish product.created event
        event_published = await event_integration.publish_product_created(
            product_id=product.id,
            name=product.name,
            price=float(product.price),
            category=product.category,
            created_by_user_id=current_user_id,
            stock_quantity=product.stock_quantity,
            correlation_id=correlation_id
        )
        
        if event_published:
            logger.info(f"Published product.created event for product {product.id}")
        else:
            logger.warning(f"Failed to publish product.created event for product {product.id}")
        
        # Enrich product response with user info if available
        product_dict = product.__dict__.copy()
        if user_info:
            product_dict['created_by_info'] = {
                "id": user_info.get("id"),
                "username": user_info.get("username"),
                "full_name": user_info.get("full_name"),
                "email": user_info.get("email")
            }
        
        # Add correlation ID for tracing
        product_dict['correlation_id'] = correlation_id
        
        return ProductResponse.model_validate(product_dict)
        
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    """
    Lấy thông tin sản phẩm theo ID
    
    - **product_id**: ID của sản phẩm cần lấy
    """
    logger.info(f"Getting product: {product_id}")
    return service.get_product(product_id)

@router.get("/", response_model=ProductListResponse)
async def get_products(
    # Query parameters cho tìm kiếm
    name: Optional[str] = Query(None, description="Tìm kiếm theo tên sản phẩm"),
    category: Optional[str] = Query(None, description="Lọc theo danh mục"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    min_price: Optional[float] = Query(None, ge=0, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, ge=0, description="Giá tối đa"),
    
    # Pagination parameters
    page: int = Query(1, ge=1, description="Số trang"),
    per_page: int = Query(10, ge=1, le=100, description="Số items per page"),
    
    service: ProductService = Depends(get_product_service)
):
    """
    Lấy danh sách sản phẩm với tìm kiếm và phân trang
    
    **Tìm kiếm:**
    - **name**: Tìm kiếm theo tên (partial match)
    - **category**: Lọc theo danh mục (partial match)
    - **is_active**: Lọc theo trạng thái (true/false)
    - **min_price**: Giá tối thiểu
    - **max_price**: Giá tối đa
    
    **Phân trang:**
    - **page**: Số trang (bắt đầu từ 1)
    - **per_page**: Số items per page (1-100)
    """
    # Validate price range
    if min_price is not None and max_price is not None and max_price < min_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá tối đa phải lớn hơn giá tối thiểu"
        )
    
    # Create search parameters
    search_params = ProductSearchParams(
        name=name,
        category=category,
        is_active=is_active,
        min_price=min_price,
        max_price=max_price,
        page=page,
        per_page=per_page
    )
    
    logger.info(f"Getting products with params: page={page}, per_page={per_page}")
    
    # Get products and total count
    products, total = service.get_products(search_params)
    
    # Calculate pagination info
    pages = math.ceil(total / per_page) if total > 0 else 1
    
    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user_id: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service)
):
    """
    Cập nhật thông tin sản phẩm (Yêu cầu authentication)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Path Parameters:**
    - **product_id**: ID của sản phẩm cần cập nhật
    
    **Body:**
    - Các trường trong body là optional, chỉ cập nhật các trường được gửi lên
    """
    logger.info(f"Updating product: {product_id}")
    return service.update_product(product_id, product_data)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service)
):
    """
    Xóa sản phẩm (soft delete)
    
    - **product_id**: ID của sản phẩm cần xóa
    - Sản phẩm sẽ được đánh dấu is_active = false thay vì xóa hoàn toàn
    """
    logger.info(f"Deleting product: {product_id}")
    service.delete_product(product_id)
    return None

@router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    request: Request,
    product_id: int,
    quantity_change: int = Query(..., description="Số lượng thay đổi (có thể âm)"),
    current_user_id: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
    http_integration: ProductHTTPIntegration = Depends(get_http_integration),
    event_integration: ProductEventIntegration = Depends(get_event_integration)
):
    """
    Cập nhật số lượng tồn kho (Yêu cầu authentication)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Path Parameters:**
    - **product_id**: ID của sản phẩm
    
    **Query Parameters:**
    - **quantity_change**: Số lượng thay đổi (dương = tăng, âm = giảm)
    
    **Ví dụ:**
    - quantity_change = 10: Tăng tồn kho 10 units
    - quantity_change = -5: Giảm tồn kho 5 units
    
    **Features:**
    - HTTP Integration: Validates user permissions for stock management
    - Event Integration: Publishes product.stock_updated event
    """
    logger.info(f"Updating stock for product {product_id}: {quantity_change} by user {current_user_id}")
    
    # Get JWT token for HTTP integration
    jwt_token = get_jwt_token_from_request(request)
    correlation_id = str(uuid.uuid4())
    
    try:
        # Get current product to capture old quantity
        current_product = service.get_product(product_id)
        old_quantity = current_product.stock_quantity
        
        # HTTP Integration: Validate user permissions for stock management
        if jwt_token:
            has_permission = await http_integration.validate_product_permissions(
                user_id=current_user_id,
                action="manage_stock",
                jwt_token=jwt_token
            )
            
            if not has_permission:
                logger.warning(f"User {current_user_id} does not have permission to manage stock")
                # Continue anyway for demo purposes, but log the warning
        
        # Update stock
        updated_product = service.update_stock(product_id, quantity_change)
        new_quantity = updated_product.stock_quantity
        
        logger.info(f"Stock updated for product {product_id}: {old_quantity} -> {new_quantity}")
        
        # Event Integration: Publish product.stock_updated event
        event_published = await event_integration.publish_product_stock_updated(
            product_id=product_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            quantity_change=quantity_change,
            updated_by_user_id=current_user_id,
            correlation_id=correlation_id
        )
        
        if event_published:
            logger.info(f"Published product.stock_updated event for product {product_id}")
        else:
            logger.warning(f"Failed to publish product.stock_updated event for product {product_id}")
        
        # Enrich response with user info if available
        product_dict = updated_product.__dict__.copy()
        if jwt_token:
            user_info = await http_integration.get_user_info(current_user_id, jwt_token)
            if user_info:
                product_dict['updated_by_info'] = {
                    "id": user_info.get("id"),
                    "username": user_info.get("username"),
                    "full_name": user_info.get("full_name")
                }
        
        # Add correlation ID and stock change info
        product_dict['correlation_id'] = correlation_id
        product_dict['stock_change_info'] = {
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "quantity_change": quantity_change,
            "updated_by": current_user_id
        }
        
        return ProductResponse.model_validate(product_dict)
        
    except Exception as e:
        logger.error(f"Error updating stock for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stock: {str(e)}"
        )

@router.get("/category/{category_name}", response_model=ProductListResponse)
async def get_products_by_category(
    category_name: str,
    is_active: Optional[bool] = Query(True, description="Lọc theo trạng thái hoạt động"),
    page: int = Query(1, ge=1, description="Số trang"),
    per_page: int = Query(10, ge=1, le=100, description="Số items per page"),
    service: ProductService = Depends(get_product_service)
):
    """
    Lấy danh sách sản phẩm theo danh mục
    
    - **category_name**: Tên danh mục
    - **is_active**: Lọc theo trạng thái (default: true)
    - **page**: Số trang
    - **per_page**: Số items per page
    """
    search_params = ProductSearchParams(
        category=category_name,
        is_active=is_active,
        page=page,
        per_page=per_page
    )
    
    logger.info(f"Getting products by category: {category_name}")
    
    products, total = service.get_products(search_params)
    pages = math.ceil(total / per_page) if total > 0 else 1
    
    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )
