"""Product Model - Database Schema
Định nghĩa cấu trúc bảng products trong database
"""
from sqlalchemy import Column, String, Text, Numeric, Integer
from libs.common.base_model import BaseModel


class Product(BaseModel):
    """
    Product model đại diện cho bảng products trong database
    
    Kế thừa từ BaseModel để có sẵn:
        - id: Primary key tự động tăng
        - created_at: Timestamp tạo record
        - updated_at: Timestamp cập nhật record (tự động update)
        - is_active: Soft delete flag
        - soft_delete(): Method để soft delete
        - restore(): Method để khôi phục record
    
    Attributes:
        name: Tên sản phẩm (required)
        description: Mô tả sản phẩm (optional)
        price: Giá sản phẩm (required, decimal)
        category: Danh mục sản phẩm (required)
        stock_quantity: Số lượng tồn kho (default: 0)
    """
    __tablename__ = "products"
    
    # Product information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)  # 10 digits, 2 decimal places
    category = Column(String(100), nullable=False, index=True)
    
    # Inventory
    stock_quantity = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"
