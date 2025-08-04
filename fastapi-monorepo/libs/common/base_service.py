"""
Base Service Class với CRUD operations chung
Cung cấp base service cho tất cả business logic trong monorepo
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from typing import List, Optional, Type, TypeVar, Generic, Dict, Any
import logging
from datetime import datetime

from libs.common.base_model import BaseModel
from libs.common.base_schema import BaseCreate, BaseUpdate, SearchParams

# Type variables for generic typing
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseCreate)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseUpdate)

logger = logging.getLogger(__name__)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base service class với CRUD operations chuẩn
    
    Args:
        model: SQLAlchemy model class
        db: Database session
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
        self.model_name = model.__name__.lower()
    
    def create(self, data: CreateSchemaType) -> ModelType:
        """
        Tạo mới một record
        
        Args:
            data: Dữ liệu tạo mới
            
        Returns:
            Record đã tạo
            
        Raises:
            HTTPException: Nếu có lỗi khi tạo
        """
        try:
            # Convert Pydantic model to dict
            create_data = data.dict(exclude_unset=True)
            
            # Create new instance
            db_obj = self.model(**create_data)
            
            # Add to session and commit
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"Created {self.model_name} with id={db_obj.id}")
            return db_obj
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể tạo {self.model_name}: {str(e)}"
            )
    
    def get_by_id(self, item_id: int, include_inactive: bool = False) -> Optional[ModelType]:
        """
        Lấy record theo ID
        
        Args:
            item_id: ID của record
            include_inactive: Có bao gồm record đã bị soft delete không
            
        Returns:
            Record nếu tìm thấy, None nếu không
        """
        query = self.db.query(self.model).filter(self.model.id == item_id)
        
        if not include_inactive:
            query = query.filter(self.model.is_active == True)
        
        return query.first()
    
    def get_by_id_or_404(self, item_id: int, include_inactive: bool = False) -> ModelType:
        """
        Lấy record theo ID hoặc raise 404
        
        Args:
            item_id: ID của record
            include_inactive: Có bao gồm record đã bị soft delete không
            
        Returns:
            Record nếu tìm thấy
            
        Raises:
            HTTPException: 404 nếu không tìm thấy
        """
        item = self.get_by_id(item_id, include_inactive)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model_name.title()} với ID {item_id} không tồn tại"
            )
        return item
    
    def update(self, item_id: int, data: UpdateSchemaType) -> ModelType:
        """
        Cập nhật record
        
        Args:
            item_id: ID của record cần cập nhật
            data: Dữ liệu cập nhật
            
        Returns:
            Record đã cập nhật
            
        Raises:
            HTTPException: Nếu không tìm thấy hoặc có lỗi khi cập nhật
        """
        try:
            # Get existing record
            db_obj = self.get_by_id_or_404(item_id)
            
            # Update fields
            update_data = data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # Commit changes
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"Updated {self.model_name} with id={item_id}")
            return db_obj
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model_name} {item_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể cập nhật {self.model_name}: {str(e)}"
            )
    
    def delete(self, item_id: int, soft_delete: bool = True) -> bool:
        """
        Xóa record (soft delete hoặc hard delete)
        
        Args:
            item_id: ID của record cần xóa
            soft_delete: True = soft delete, False = hard delete
            
        Returns:
            True nếu xóa thành công
            
        Raises:
            HTTPException: Nếu không tìm thấy hoặc có lỗi khi xóa
        """
        try:
            # Get existing record
            db_obj = self.get_by_id_or_404(item_id)
            
            if soft_delete:
                # Soft delete
                db_obj.soft_delete()
                self.db.commit()
                logger.info(f"Soft deleted {self.model_name} with id={item_id}")
            else:
                # Hard delete
                self.db.delete(db_obj)
                self.db.commit()
                logger.info(f"Hard deleted {self.model_name} with id={item_id}")
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model_name} {item_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể xóa {self.model_name}: {str(e)}"
            )
    
    def get_list(self, search_params: SearchParams, include_inactive: bool = False) -> tuple[List[ModelType], int]:
        """
        Lấy danh sách records với search và pagination
        
        Args:
            search_params: Tham số tìm kiếm và phân trang
            include_inactive: Có bao gồm record đã bị soft delete không
            
        Returns:
            tuple: (danh sách records, tổng số records)
        """
        query = self.db.query(self.model)
        
        # Filter by active status
        if not include_inactive:
            query = query.filter(self.model.is_active == True)
        
        # Apply search filter if provided
        if search_params.search:
            query = self._apply_search_filter(query, search_params.search)
        
        # Apply is_active filter if specified
        if search_params.is_active is not None:
            query = query.filter(self.model.is_active == search_params.is_active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (search_params.page - 1) * search_params.per_page
        items = query.offset(offset).limit(search_params.per_page).all()
        
        logger.info(f"Retrieved {len(items)} {self.model_name}s (total: {total})")
        return items, total
    
    def _apply_search_filter(self, query, search_term: str):
        """
        Áp dụng search filter - override method này trong subclass
        để implement search logic cụ thể cho từng model
        
        Args:
            query: SQLAlchemy query
            search_term: Từ khóa tìm kiếm
            
        Returns:
            Query đã áp dụng search filter
        """
        # Default implementation - tìm kiếm trong trường 'name' nếu có
        if hasattr(self.model, 'name'):
            return query.filter(self.model.name.ilike(f"%{search_term}%"))
        return query
    
    def restore(self, item_id: int) -> ModelType:
        """
        Khôi phục record đã bị soft delete
        
        Args:
            item_id: ID của record cần khôi phục
            
        Returns:
            Record đã khôi phục
            
        Raises:
            HTTPException: Nếu không tìm thấy
        """
        try:
            # Get record including inactive ones
            db_obj = self.get_by_id_or_404(item_id, include_inactive=True)
            
            # Restore
            db_obj.restore()
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"Restored {self.model_name} with id={item_id}")
            return db_obj
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error restoring {self.model_name} {item_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể khôi phục {self.model_name}: {str(e)}"
            )
    
    def bulk_delete(self, item_ids: List[int], soft_delete: bool = True) -> int:
        """
        Xóa nhiều records cùng lúc
        
        Args:
            item_ids: Danh sách IDs cần xóa
            soft_delete: True = soft delete, False = hard delete
            
        Returns:
            Số lượng records đã xóa
        """
        try:
            query = self.db.query(self.model).filter(self.model.id.in_(item_ids))
            
            if soft_delete:
                # Soft delete
                count = query.update({self.model.is_active: False})
            else:
                # Hard delete
                count = query.delete()
            
            self.db.commit()
            logger.info(f"Bulk deleted {count} {self.model_name}s")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk deleting {self.model_name}s: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể xóa hàng loạt {self.model_name}: {str(e)}"
            )
