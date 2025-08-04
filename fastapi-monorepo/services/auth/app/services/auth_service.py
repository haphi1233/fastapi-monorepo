"""
Authentication Service - Business Logic Layer
Sử dụng BaseService từ libs/common và JWT utilities từ libs/auth
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from libs.common.base_service import BaseService
from libs.auth.jwt_utils import JWTManager, PasswordManager, get_jwt_manager
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserSearchParams, LoginRequest, TokenResponse, PasswordChange

logger = logging.getLogger(__name__)


class AuthService(BaseService[User, UserCreate, UserUpdate]):
    """
    Authentication Service kế thừa từ BaseService
    Cung cấp các chức năng authentication và user management
    """
    
    def __init__(self, db: Session):
        super().__init__(User, db)
        self.jwt_manager = get_jwt_manager()
        self.password_manager = PasswordManager()
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Tạo user mới với password hashing
        
        Args:
            user_data: Dữ liệu user mới
            
        Returns:
            User đã tạo
            
        Raises:
            HTTPException: Nếu username hoặc email đã tồn tại
        """
        # Kiểm tra username đã tồn tại
        existing_user = self.db.query(User).filter(
            or_(User.username == user_data.username, User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username đã tồn tại"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email đã tồn tại"
                )
        
        # Hash password
        hashed_password = self.password_manager.hash_password(user_data.password)
        
        # Tạo user mới
        user_dict = user_data.dict(exclude={"password", "confirm_password"})
        user_dict["hashed_password"] = hashed_password
        
        db_user = User(**user_dict)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Created new user: {db_user.username} ({db_user.email})")
        return db_user
    
    def authenticate_user(self, login_data: LoginRequest) -> Optional[User]:
        """
        Xác thực user với username/email và password
        
        Args:
            login_data: Dữ liệu đăng nhập
            
        Returns:
            User nếu xác thực thành công, None nếu thất bại
        """
        # Tìm user theo username hoặc email
        user = self.db.query(User).filter(
            or_(
                User.username == login_data.username_or_email,
                User.email == login_data.username_or_email
            ),
            User.is_active == True
        ).first()
        
        if not user:
            logger.warning(f"Login attempt with non-existent user: {login_data.username_or_email}")
            return None
        
        # Kiểm tra account có bị khóa không
        if user.is_locked():
            logger.warning(f"Login attempt on locked account: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Tài khoản đã bị khóa do đăng nhập sai quá nhiều lần"
            )
        
        # Verify password
        if not self.password_manager.verify_password(login_data.password, user.hashed_password):
            # Tăng số lần đăng nhập thất bại
            user.increment_failed_attempts()
            
            # Khóa account nếu thất bại quá 5 lần
            if int(user.failed_login_attempts) >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(f"Account locked due to too many failed attempts: {user.username}")
            
            self.db.commit()
            logger.warning(f"Failed login attempt for user: {user.username}")
            return None
        
        # Reset failed attempts và update last login
        user.reset_failed_attempts()
        user.update_last_login()
        self.db.commit()
        
        logger.info(f"Successful login for user: {user.username}")
        return user
    
    def create_tokens(self, user: User) -> TokenResponse:
        """
        Tạo JWT tokens cho user
        
        Args:
            user: User object
            
        Returns:
            TokenResponse với access và refresh tokens
        """
        # Payload cho JWT
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser
        }
        
        # Tạo tokens
        access_token = self.jwt_manager.create_access_token(token_data)
        refresh_token = self.jwt_manager.create_refresh_token({"sub": str(user.id)})
        
        # Convert user to response schema
        from app.schemas.user import UserResponse
        user_response = UserResponse.model_validate(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.jwt_manager.get_token_expires_in("access"),
            user=user_response
        )
    
    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token sử dụng refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            TokenResponse với access token mới
            
        Raises:
            HTTPException: Nếu refresh token không hợp lệ
        """
        # Verify refresh token
        payload = self.jwt_manager.verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ"
            )
        
        # Lấy user từ database
        user = self.get_by_id_or_404(int(user_id))
        
        # Tạo tokens mới
        return self.create_tokens(user)
    
    def change_password(self, user_id: int, password_data: PasswordChange) -> bool:
        """
        Đổi mật khẩu cho user
        
        Args:
            user_id: ID của user
            password_data: Dữ liệu đổi mật khẩu
            
        Returns:
            True nếu đổi thành công
            
        Raises:
            HTTPException: Nếu mật khẩu hiện tại không đúng
        """
        user = self.get_by_id_or_404(user_id)
        
        # Verify current password
        if not self.password_manager.verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu hiện tại không đúng"
            )
        
        # Hash new password
        new_hashed_password = self.password_manager.hash_password(password_data.new_password)
        user.hashed_password = new_hashed_password
        
        self.db.commit()
        logger.info(f"Password changed for user: {user.username}")
        return True
    
    def get_users(self, search_params: UserSearchParams) -> tuple[list[User], int]:
        """
        Lấy danh sách users với search và pagination
        Override method từ BaseService để thêm custom search logic
        
        Args:
            search_params: Tham số tìm kiếm
            
        Returns:
            tuple: (danh sách users, tổng số users)
        """
        query = self.db.query(User)
        
        # Filter by active status
        if not search_params.is_active is None:
            query = query.filter(User.is_active == search_params.is_active)
        else:
            query = query.filter(User.is_active == True)  # Default chỉ lấy active users
        
        # Apply search filters
        if search_params.search:
            search_term = f"%{search_params.search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        if search_params.username:
            query = query.filter(User.username.ilike(f"%{search_params.username}%"))
        
        if search_params.email:
            query = query.filter(User.email.ilike(f"%{search_params.email}%"))
        
        if search_params.is_verified is not None:
            query = query.filter(User.is_verified == search_params.is_verified)
        
        if search_params.is_superuser is not None:
            query = query.filter(User.is_superuser == search_params.is_superuser)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (search_params.page - 1) * search_params.per_page
        users = query.offset(offset).limit(search_params.per_page).all()
        
        logger.info(f"Retrieved {len(users)} users (total: {total})")
        return users, total
    
    def verify_user_email(self, user_id: int) -> User:
        """
        Xác thực email của user
        
        Args:
            user_id: ID của user
            
        Returns:
            User đã được xác thực
        """
        user = self.get_by_id_or_404(user_id)
        user.is_verified = True
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Email verified for user: {user.username}")
        return user
    
    def make_superuser(self, user_id: int) -> User:
        """
        Cấp quyền superuser cho user
        
        Args:
            user_id: ID của user
            
        Returns:
            User đã được cấp quyền superuser
        """
        user = self.get_by_id_or_404(user_id)
        user.is_superuser = True
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Superuser privilege granted to user: {user.username}")
        return user
