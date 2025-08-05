"""
Product Service - Business Logic Layer
Chứa các business logic và operations cho Product
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
import logging
import sys
import os

# Add path to monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.common.base_service import BaseService
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductSearchParams

logger = logging.getLogger(__name__)


class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    """Service class chứa business logic cho Product operations (kế thừa BaseService)"""
    
    def __init__(self, db: Session):
        super().__init__(Product, db)
    
    def create_product(self, product_data: ProductCreate) -> Product:
        """
        Tạo sản phẩm mới với validation đặc thù
        
        Args:
            product_data: Dữ liệu sản phẩm từ ProductCreate schema
            
        Returns:
            Product: Sản phẩm vừa tạo
            
        Raises:
            HTTPException: Nếu tên sản phẩm đã tồn tại
        """
        # Kiểm tra tên sản phẩm đã tồn tại chưa
        existing_product = self.db.query(Product).filter(
            Product.name == product_data.name
        ).first()
        
        if existing_product:
            logger.warning(f"Attempt to create duplicate product: {product_data.name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sản phẩm với tên '{product_data.name}' đã tồn tại"
            )
        
        # Sử dụng BaseService.create() method
        return self.create(product_data)
    
    def get_product(self, product_id: int) -> Product:
        """
        Lấy sản phẩm theo ID (sử dụng BaseService method)
        
        Args:
            product_id: ID của sản phẩm
            
        Returns:
            Product: Sản phẩm tìm được
            
        Raises:
            HTTPException: Nếu không tìm thấy sản phẩm
        """
        return self.get_by_id_or_404(product_id)
    
    def get_products(self, search_params: ProductSearchParams) -> Tuple[List[Product], int]:
        """
        Lấy danh sách sản phẩm với tìm kiếm và phân trang (sử dụng BaseService)
        
        Args:
            search_params: Tham số tìm kiếm và phân trang
            
        Returns:
            tuple: (danh sách sản phẩm, tổng số sản phẩm)
        """
        return self.get_list(search_params)
    
    def _apply_search_filter(self, query, search_term: str):
        """
        Override BaseService method để implement search logic cụ thể cho Product
        
        Args:
            query: SQLAlchemy query object
            search_term: Từ khóa tìm kiếm
            
        Returns:
            query: Query đã apply search filter
        """
        return query.filter(
            or_(
                Product.name.ilike(f"%{search_term}%"),
                Product.description.ilike(f"%{search_term}%"),
                Product.category.ilike(f"%{search_term}%")
            )
        )
    
    def _apply_custom_filters(self, query, search_params: ProductSearchParams):
        """
        Apply các filter đặc thù cho Product
        
        Args:
            query: SQLAlchemy query object
            search_params: Tham số tìm kiếm
            
        Returns:
            query: Query đã apply filters
        """
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
        
        return query
    
    def update_product(self, product_id: int, product_data: ProductUpdate) -> Product:
        """
        Cập nhật sản phẩm với validation đặc thù
        
        Args:
            product_id: ID của sản phẩm
            product_data: Dữ liệu cập nhật
            
        Returns:
            Product: Sản phẩm đã cập nhật
            
        Raises:
            HTTPException: Nếu không tìm thấy sản phẩm hoặc tên đã tồn tại
        """
        # Lấy sản phẩm hiện tại
        product = self.get_product(product_id)
        
        # Kiểm tra tên sản phẩm nếu có thay đổi
        if product_data.name and product_data.name != product.name:
            existing_product = self.db.query(Product).filter(
                and_(
                    Product.name == product_data.name,
                    Product.id != product_id
                )
            ).first()
            
            if existing_product:
                logger.warning(f"Attempt to update to duplicate name: {product_data.name}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sản phẩm với tên '{product_data.name}' đã tồn tại"
                )
        
        # Cập nhật các trường
        update_data = product_data.dict(exclude_unset=True)
        
        try:
            for field, value in update_data.items():
                setattr(product, field, value)
            
            self.db.commit()
            self.db.refresh(product)
            
            logger.info(f"Updated product: {product.id} - {product.name}")
            return product
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi khi cập nhật sản phẩm"
            )
    
    def delete_product(self, product_id: int) -> bool:
        """
        Xóa sản phẩm (soft delete - set is_active = False)
        
        Args:
            product_id: ID của sản phẩm
            
        Returns:
            bool: True nếu xóa thành công
            
        Raises:
            HTTPException: Nếu không tìm thấy sản phẩm
        """
        product = self.get_product(product_id)
        
        try:
            # Soft delete - chỉ set is_active = False
            product.is_active = False
            self.db.commit()
            
            logger.info(f"Soft deleted product: {product.id} - {product.name}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi khi xóa sản phẩm"
            )
    
    def update_stock(self, product_id: int, quantity_change: int) -> Product:
        """
        Cập nhật số lượng tồn kho
        
        Args:
            product_id: ID của sản phẩm
            quantity_change: Số lượng thay đổi (có thể âm)
            
        Returns:
            Product: Sản phẩm đã cập nhật
            
        Raises:
            HTTPException: Nếu không đủ tồn kho hoặc không tìm thấy sản phẩm
        """
        product = self.get_product(product_id)
        
        new_quantity = product.stock_quantity + quantity_change
        
        if new_quantity < 0:
            logger.warning(f"Insufficient stock for product {product_id}: {product.stock_quantity} + {quantity_change}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không đủ tồn kho. Hiện có: {product.stock_quantity}, cần: {abs(quantity_change)}"
            )
        
        try:
            product.stock_quantity = new_quantity
            self.db.commit()
            self.db.refresh(product)
            
            logger.info(f"Updated stock for product {product_id}: {product.stock_quantity}")
            return product
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating stock for product {product_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi khi cập nhật tồn kho"
            )


# Dependency function for FastAPI
def get_product_service(db: Session) -> ProductService:
    """
    Dependency function để inject ProductService vào FastAPI endpoints
    
    Args:
        db: Database session (sẽ được inject bởi FastAPI Depends)
        
    Returns:
        ProductService: Instance của ProductService
    """
    return ProductService(db)
