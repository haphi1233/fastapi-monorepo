"""
Product Model - Database Schema
Định nghĩa cấu trúc bảng products trong database
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
import sys
import os

# Add path to monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.db.session import Base

class Product(Base):
    """
    Product model đại diện cho bảng products trong database
    
    Attributes:
        id: Primary key, auto increment
        name: Tên sản phẩm (required)
        description: Mô tả sản phẩm (optional)
        price: Giá sản phẩm (required, decimal)
        category: Danh mục sản phẩm (required)
        is_active: Trạng thái active/inactive (default: True)
        stock_quantity: Số lượng tồn kho (default: 0)
        created_at: Thời gian tạo (auto)
        updated_at: Thời gian cập nhật (auto)
    """
    __tablename__ = "products"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Product information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)  # 10 digits, 2 decimal places
    category = Column(String(100), nullable=False, index=True)
    
    # Status and inventory
    is_active = Column(Boolean, default=True, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"
