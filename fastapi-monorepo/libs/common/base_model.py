"""
Base SQLAlchemy Model với các trường chung
Cung cấp base class cho tất cả models trong monorepo
"""
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from libs.db.session import Base


class BaseModel(Base):
    """
    Base model với các trường chung cho tất cả tables
    
    Attributes:
        id: Primary key tự động tăng
        created_at: Timestamp tạo record
        updated_at: Timestamp cập nhật record (tự động update)
        is_active: Soft delete flag (True = active, False = deleted)
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    def soft_delete(self):
        """Soft delete - đánh dấu record là không active"""
        self.is_active = False
    
    def restore(self):
        """Khôi phục record đã bị soft delete"""
        self.is_active = True
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, is_active={self.is_active})>"
