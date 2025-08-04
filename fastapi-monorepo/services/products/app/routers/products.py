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

# Add path to monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.db.session import get_db
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate, 
    ProductUpdate, 
    ProductResponse, 
    ProductListResponse,
    ProductSearchParams
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={404: {"description": "Not found"}}
)

def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    """Dependency để inject ProductService"""
    return ProductService(db)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    """
    Tạo sản phẩm mới
    
    - **name**: Tên sản phẩm (required, unique)
    - **description**: Mô tả sản phẩm (optional)
    - **price**: Giá sản phẩm (required, > 0)
    - **category**: Danh mục sản phẩm (required)
    - **is_active**: Trạng thái hoạt động (default: true)
    - **stock_quantity**: Số lượng tồn kho (default: 0)
    """
    logger.info(f"Creating new product: {product_data.name}")
    return service.create_product(product_data)

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
    service: ProductService = Depends(get_product_service)
):
    """
    Cập nhật thông tin sản phẩm
    
    - **product_id**: ID của sản phẩm cần cập nhật
    - Các trường trong body là optional, chỉ cập nhật các trường được gửi lên
    """
    logger.info(f"Updating product: {product_id}")
    return service.update_product(product_id, product_data)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
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
    product_id: int,
    quantity_change: int = Query(..., description="Số lượng thay đổi (có thể âm)"),
    service: ProductService = Depends(get_product_service)
):
    """
    Cập nhật số lượng tồn kho
    
    - **product_id**: ID của sản phẩm
    - **quantity_change**: Số lượng thay đổi (dương = tăng, âm = giảm)
    
    Ví dụ:
    - quantity_change = 10: Tăng tồn kho 10 units
    - quantity_change = -5: Giảm tồn kho 5 units
    """
    logger.info(f"Updating stock for product {product_id}: {quantity_change}")
    return service.update_stock(product_id, quantity_change)

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
