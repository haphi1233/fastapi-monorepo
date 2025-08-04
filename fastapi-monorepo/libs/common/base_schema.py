"""
Base Pydantic Schemas với các trường chung
Cung cấp base schemas cho tất cả API trong monorepo
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class BaseSchema(BaseModel):
    """Base schema với config chung"""
    
    class Config:
        from_attributes = True  # Pydantic v2 equivalent of orm_mode
        validate_assignment = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TimestampMixin(BaseModel):
    """Mixin cho các trường timestamp"""
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")


class BaseResponse(BaseSchema, TimestampMixin):
    """Base response schema với id và timestamps"""
    id: int = Field(..., description="ID duy nhất")
    is_active: bool = Field(True, description="Trạng thái hoạt động")


class BaseCreate(BaseSchema):
    """Base schema cho tạo mới record"""
    pass


class BaseUpdate(BaseSchema):
    """Base schema cho cập nhật record - tất cả fields optional"""
    pass


class PaginationParams(BaseModel):
    """Schema cho pagination parameters"""
    page: int = Field(1, ge=1, description="Số trang")
    per_page: int = Field(10, ge=1, le=100, description="Số items per page")
    
    @validator('per_page')
    def validate_per_page(cls, v):
        if v > 100:
            raise ValueError('per_page không được vượt quá 100')
        return v


class SearchParams(PaginationParams):
    """Base schema cho search parameters với pagination"""
    search: Optional[str] = Field(None, description="Từ khóa tìm kiếm")
    is_active: Optional[bool] = Field(None, description="Lọc theo trạng thái hoạt động")


class ListResponse(BaseSchema):
    """Base schema cho list response với pagination"""
    items: List[Any] = Field(..., description="Danh sách items")
    total: int = Field(..., description="Tổng số items")
    page: int = Field(..., description="Trang hiện tại")
    per_page: int = Field(..., description="Số items per page")
    pages: int = Field(..., description="Tổng số trang")
    
    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        """Tự động tính số trang dựa trên total và per_page"""
        total = values.get('total', 0)
        per_page = values.get('per_page', 10)
        return (total + per_page - 1) // per_page if total > 0 else 0


class APIResponse(BaseSchema):
    """Standard API response wrapper"""
    success: bool = Field(True, description="Trạng thái thành công")
    message: str = Field("", description="Thông báo")
    data: Optional[Any] = Field(None, description="Dữ liệu response")
    errors: Optional[List[str]] = Field(None, description="Danh sách lỗi")


class ErrorResponse(BaseSchema):
    """Schema cho error response"""
    detail: str = Field(..., description="Chi tiết lỗi")
    error: str = Field(..., description="Loại lỗi")
    timestamp: datetime = Field(default_factory=datetime.now, description="Thời gian lỗi")
