"""
Product Schemas - Pydantic Models
Định nghĩa các schema cho API request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class ProductBase(BaseModel):
    """Base schema chứa các trường chung cho Product"""
    name: str = Field(..., min_length=1, max_length=255, description="Tên sản phẩm")
    description: Optional[str] = Field(None, description="Mô tả sản phẩm")
    price: Decimal = Field(..., gt=0, description="Giá sản phẩm (phải > 0)")
    category: str = Field(..., min_length=1, max_length=100, description="Danh mục sản phẩm")
    is_active: bool = Field(True, description="Trạng thái hoạt động")
    stock_quantity: int = Field(0, ge=0, description="Số lượng tồn kho (>= 0)")

    @validator('price')
    def validate_price(cls, v):
        """Validate giá sản phẩm"""
        if v <= 0:
            raise ValueError('Giá sản phẩm phải lớn hơn 0')
        return round(v, 2)  # Làm tròn 2 chữ số thập phân

    @validator('name')
    def validate_name(cls, v):
        """Validate tên sản phẩm"""
        if not v or not v.strip():
            raise ValueError('Tên sản phẩm không được để trống')
        return v.strip()

    @validator('category')
    def validate_category(cls, v):
        """Validate danh mục"""
        if not v or not v.strip():
            raise ValueError('Danh mục không được để trống')
        return v.strip()

class ProductCreate(ProductBase):
    """Schema cho tạo sản phẩm mới"""
    pass

class ProductUpdate(BaseModel):
    """Schema cho cập nhật sản phẩm (tất cả fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    stock_quantity: Optional[int] = Field(None, ge=0)

    @validator('price')
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Giá sản phẩm phải lớn hơn 0')
        return round(v, 2) if v is not None else v

    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Tên sản phẩm không được để trống')
        return v.strip() if v is not None else v

    @validator('category')
    def validate_category(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Danh mục không được để trống')
        return v.strip() if v is not None else v

class ProductResponse(ProductBase):
    """Schema cho response API (bao gồm các trường từ database)"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # Cho phép convert từ SQLAlchemy model
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class ProductListResponse(BaseModel):
    """Schema cho danh sách sản phẩm với pagination"""
    items: List[ProductResponse]
    total: int
    page: int
    per_page: int
    pages: int

class ProductSearchParams(BaseModel):
    """Schema cho tham số tìm kiếm sản phẩm"""
    name: Optional[str] = Field(None, description="Tìm theo tên sản phẩm")
    category: Optional[str] = Field(None, description="Lọc theo danh mục")
    is_active: Optional[bool] = Field(None, description="Lọc theo trạng thái")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Giá tối thiểu")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Giá tối đa")
    page: int = Field(1, ge=1, description="Số trang")
    per_page: int = Field(10, ge=1, le=100, description="Số items per page")

    @validator('max_price')
    def validate_price_range(cls, v, values):
        """Validate range giá"""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('Giá tối đa phải lớn hơn giá tối thiểu')
        return v
