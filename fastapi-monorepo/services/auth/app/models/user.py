"""
User Model - Authentication Service
Định nghĩa model User sử dụng BaseModel từ libs/common
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.common.base_model import BaseModel


class User(BaseModel):
    """
    User model cho authentication service
    
    Kế thừa từ BaseModel để có sẵn:
    - id, created_at, updated_at, is_active
    - soft_delete(), restore() methods
    """
    __tablename__ = "users"
    
    # Basic user information
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    
    # Authentication fields
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Profile fields
    phone = Column(String(20), nullable=True)
    avatar_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Account status
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(String(10), default="0", nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def is_locked(self) -> bool:
        """Kiểm tra xem tài khoản có bị khóa không"""
        if not self.locked_until:
            return False
        return self.locked_until > func.now()
    
    def increment_failed_attempts(self):
        """Tăng số lần đăng nhập thất bại"""
        current_attempts = int(self.failed_login_attempts)
        self.failed_login_attempts = str(current_attempts + 1)
    
    def reset_failed_attempts(self):
        """Reset số lần đăng nhập thất bại"""
        self.failed_login_attempts = "0"
        self.locked_until = None
    
    def update_last_login(self):
        """Cập nhật thời gian đăng nhập cuối"""
        self.last_login = func.now()
