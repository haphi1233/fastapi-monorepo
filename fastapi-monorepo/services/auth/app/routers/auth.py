"""
Authentication API Routes
Định nghĩa các endpoint cho authentication sử dụng common libraries
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
from libs.db.session import get_db
from libs.auth.jwt_utils import get_current_user_id
from libs.common.base_schema import ListResponse
from ..services.auth_service import AuthService
from ..schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserSearchParams,
    LoginRequest, TokenResponse, PasswordChange, RefreshTokenRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency để tạo AuthService instance"""
    return AuthService(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    service: AuthService = Depends(get_auth_service)
):
    """
    Đăng ký user mới
    
    **Yêu cầu:**
    - Username: 3-50 ký tự, chỉ chứa chữ cái, số và dấu gạch dưới
    - Email: Định dạng email hợp lệ và chưa được sử dụng
    - Password: Ít nhất 8 ký tự, có chữ hoa, chữ thường và số
    - Confirm password: Phải khớp với password
    
    **Response:**
    - Thông tin user đã tạo (không bao gồm password)
    """
    try:
        user = service.create_user(user_data)
        logger.info(f"New user registered: {user.username}")
        return UserResponse.model_validate(user)
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Đăng nhập và nhận JWT tokens
    
    **Yêu cầu:**
    - username_or_email: Username hoặc email của user
    - password: Mật khẩu
    
    **Response:**
    - access_token: JWT token để xác thực API calls
    - refresh_token: Token để refresh access token
    - user: Thông tin user
    - expires_in: Thời gian hết hạn access token (giây)
    
    **Lưu ý:**
    - Account sẽ bị khóa 30 phút sau 5 lần đăng nhập sai
    """
    try:
        user = service.authenticate_user(login_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username/email hoặc mật khẩu không đúng"
            )
        
        tokens = service.create_tokens(user)
        logger.info(f"User logged in: {user.username}")
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống khi đăng nhập"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token bằng refresh token
    
    **Yêu cầu:**
    - refresh_token: Refresh token hợp lệ
    
    **Response:**
    - access_token mới và thông tin user
    """
    try:
        tokens = service.refresh_access_token(refresh_data.refresh_token)
        logger.info("Access token refreshed successfully")
        return tokens
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Lấy thông tin user hiện tại từ JWT token
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Response:**
    - Thông tin user hiện tại
    """
    user = service.get_by_id_or_404(current_user_id)
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Cập nhật thông tin user hiện tại
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Body:**
    - Các trường cần cập nhật (tất cả optional)
    
    **Response:**
    - Thông tin user đã cập nhật
    """
    try:
        user = service.update(current_user_id, user_data)
        logger.info(f"User profile updated: {user.username}")
        return UserResponse.model_validate(user)
    except Exception as e:
        logger.error(f"Profile update failed: {str(e)}")
        raise


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Đổi mật khẩu cho user hiện tại
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Body:**
    - current_password: Mật khẩu hiện tại
    - new_password: Mật khẩu mới (ít nhất 8 ký tự, có chữ hoa, thường, số)
    - confirm_new_password: Xác nhận mật khẩu mới
    
    **Response:**
    - Thông báo thành công
    """
    try:
        service.change_password(current_user_id, password_data)
        logger.info(f"Password changed for user ID: {current_user_id}")
        return {"message": "Đổi mật khẩu thành công"}
    except Exception as e:
        logger.error(f"Password change failed: {str(e)}")
        raise


# Admin endpoints (cần quyền superuser)
@router.get("/users", response_model=ListResponse)
async def get_users(
    # Search parameters
    search: Optional[str] = Query(None, description="Tìm kiếm theo username, email, full_name"),
    username: Optional[str] = Query(None, description="Tìm theo username"),
    email: Optional[str] = Query(None, description="Tìm theo email"),
    is_verified: Optional[bool] = Query(None, description="Lọc theo trạng thái xác thực"),
    is_superuser: Optional[bool] = Query(None, description="Lọc theo quyền superuser"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    
    # Pagination parameters
    page: int = Query(1, ge=1, description="Số trang"),
    per_page: int = Query(10, ge=1, le=100, description="Số items per page"),
    
    # Dependencies
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Lấy danh sách users (Admin only)
    
    **Headers:**
    - Authorization: Bearer {access_token} (cần quyền superuser)
    
    **Query Parameters:**
    - Tìm kiếm và lọc theo các tiêu chí
    - Pagination với page và per_page
    
    **Response:**
    - Danh sách users với pagination info
    """
    # Kiểm tra quyền superuser
    current_user = service.get_by_id_or_404(current_user_id)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập"
        )
    
    # Tạo search parameters
    search_params = UserSearchParams(
        search=search,
        username=username,
        email=email,
        is_verified=is_verified,
        is_superuser=is_superuser,
        is_active=is_active,
        page=page,
        per_page=per_page
    )
    
    # Lấy danh sách users
    users, total = service.get_users(search_params)
    
    # Convert to response format
    user_responses = [UserResponse.model_validate(user) for user in users]
    
    return ListResponse(
        items=user_responses,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Lấy thông tin user theo ID (Admin only)
    
    **Headers:**
    - Authorization: Bearer {access_token} (cần quyền superuser)
    
    **Path Parameters:**
    - user_id: ID của user cần lấy thông tin
    
    **Response:**
    - Thông tin user
    """
    # Kiểm tra quyền superuser
    current_user = service.get_by_id_or_404(current_user_id)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập"
        )
    
    user = service.get_by_id_or_404(user_id)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/verify", response_model=UserResponse)
async def verify_user(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Xác thực email của user (Admin only)
    
    **Headers:**
    - Authorization: Bearer {access_token} (cần quyền superuser)
    
    **Path Parameters:**
    - user_id: ID của user cần xác thực
    
    **Response:**
    - Thông tin user đã được xác thực
    """
    # Kiểm tra quyền superuser
    current_user = service.get_by_id_or_404(current_user_id)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập"
        )
    
    user = service.verify_user_email(user_id)
    logger.info(f"User {user.username} verified by admin {current_user.username}")
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/make-superuser", response_model=UserResponse)
async def make_superuser(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Cấp quyền superuser cho user (Admin only)
    
    **Headers:**
    - Authorization: Bearer {access_token} (cần quyền superuser)
    
    **Path Parameters:**
    - user_id: ID của user cần cấp quyền
    
    **Response:**
    - Thông tin user đã được cấp quyền superuser
    """
    # Kiểm tra quyền superuser
    current_user = service.get_by_id_or_404(current_user_id)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập"
        )
    
    user = service.make_superuser(user_id)
    logger.info(f"User {user.username} granted superuser by admin {current_user.username}")
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """
    Xóa user (soft delete) (Admin only)
    
    **Headers:**
    - Authorization: Bearer {access_token} (cần quyền superuser)
    
    **Path Parameters:**
    - user_id: ID của user cần xóa
    
    **Response:**
    - 204 No Content
    """
    # Kiểm tra quyền superuser
    current_user = service.get_by_id_or_404(current_user_id)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập"
        )
    
    # Không cho phép xóa chính mình
    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa chính mình"
        )
    
    user = service.get_by_id_or_404(user_id)
    service.delete(user_id, soft_delete=True)
    logger.info(f"User {user.username} deleted by admin {current_user.username}")
    
    return {"message": "User đã được xóa thành công"}
