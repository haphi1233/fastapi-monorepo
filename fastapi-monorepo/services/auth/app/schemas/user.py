"""
User Schemas - Authentication Service
Định nghĩa các schema cho User API sử dụng BaseSchema từ libs/common
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional
from datetime import datetime

from libs.common.base_schema import BaseSchema, BaseResponse, BaseCreate, BaseUpdate, SearchParams


class UserBase(BaseSchema):
    """Base schema cho User với các trường chung"""
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    email: EmailStr = Field(..., description="Email người dùng")
    full_name: Optional[str] = Field(None, max_length=100, description="Họ và tên")
    phone: Optional[str] = Field(None, max_length=20, description="Số điện thoại")
    bio: Optional[str] = Field(None, max_length=500, description="Giới thiệu bản thân")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username chỉ được chứa chữ cái, số và dấu gạch dưới')
        return v.lower()


class UserCreate(UserBase):
    """Schema cho tạo user mới"""
    password: str = Field(..., min_length=8, description="Mật khẩu")
    confirm_password: str = Field(..., description="Xác nhận mật khẩu")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Mật khẩu xác nhận không khớp')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Mật khẩu phải có ít nhất 8 ký tự')
        if not any(c.isupper() for c in v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ hoa')
        if not any(c.islower() for c in v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ thường')
        if not any(c.isdigit() for c in v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ số')
        return v


class UserUpdate(BaseUpdate):
    """Schema cho cập nhật user - tất cả fields optional"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = Field(None)
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None)
    
    @validator('username')
    def validate_username(cls, v):
        if v and (not v.isalnum() and '_' not in v):
            raise ValueError('Username chỉ được chứa chữ cái, số và dấu gạch dưới')
        return v.lower() if v else v


class UserResponse(BaseResponse):
    """Schema cho response User"""
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    is_superuser: bool
    last_login: Optional[datetime]


class UserSearchParams(SearchParams):
    """Schema cho tham số tìm kiếm user"""
    username: Optional[str] = Field(None, description="Tìm theo username")
    email: Optional[str] = Field(None, description="Tìm theo email")
    is_verified: Optional[bool] = Field(None, description="Lọc theo trạng thái xác thực")
    is_superuser: Optional[bool] = Field(None, description="Lọc theo quyền superuser")


class PasswordChange(BaseSchema):
    """Schema cho đổi mật khẩu"""
    current_password: str = Field(..., description="Mật khẩu hiện tại")
    new_password: str = Field(..., min_length=8, description="Mật khẩu mới")
    confirm_new_password: str = Field(..., description="Xác nhận mật khẩu mới")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Mật khẩu xác nhận không khớp')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Mật khẩu phải có ít nhất 8 ký tự')
        if not any(c.isupper() for c in v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ hoa')
        if not any(c.islower() for c in v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ thường')
        if not any(c.isdigit() for c in v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ số')
        return v


class LoginRequest(BaseSchema):
    """Schema cho đăng nhập"""
    username_or_email: str = Field(..., description="Username hoặc email")
    password: str = Field(..., description="Mật khẩu")


class TokenResponse(BaseSchema):
    """Schema cho JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Loại token")
    expires_in: int = Field(..., description="Thời gian hết hạn (giây)")
    user: UserResponse = Field(..., description="Thông tin user")


class RefreshTokenRequest(BaseSchema):
    """Schema cho refresh token"""
    refresh_token: str = Field(..., description="Refresh token")
