"""
JWT Authentication Utilities - Shared JWT functions
Cung cấp các utility functions cho JWT authentication trong monorepo
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer()


class JWTManager:
    """
    JWT Manager class để xử lý JWT tokens
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """
        Tạo JWT access token
        
        Args:
            data: Dữ liệu để encode vào token
            
        Returns:
            JWT access token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Tạo JWT refresh token
        
        Args:
            data: Dữ liệu để encode vào token
            
        Returns:
            JWT refresh token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify và decode JWT token
        
        Args:
            token: JWT token string
            token_type: Loại token ("access" hoặc "refresh")
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: Nếu token không hợp lệ
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Kiểm tra loại token
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Token type mismatch. Expected: {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token đã hết hạn",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_token_expires_in(self, token_type: str = "access") -> int:
        """
        Lấy thời gian hết hạn của token (tính bằng giây)
        
        Args:
            token_type: Loại token ("access" hoặc "refresh")
            
        Returns:
            Thời gian hết hạn tính bằng giây
        """
        if token_type == "access":
            return self.access_token_expire_minutes * 60
        elif token_type == "refresh":
            return self.refresh_token_expire_days * 24 * 60 * 60
        else:
            return 0


class PasswordManager:
    """
    Password Manager class để xử lý password hashing và verification
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password sử dụng bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password với hashed password
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password từ database
            
        Returns:
            True nếu password đúng, False nếu sai
        """
        return pwd_context.verify(plain_password, hashed_password)


def get_jwt_manager() -> JWTManager:
    """
    Factory function để tạo JWTManager từ environment variables
    
    Returns:
        JWTManager instance đã được cấu hình
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    return JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days
    )


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Dependency để lấy current user ID từ JWT token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        User ID từ token
        
    Raises:
        HTTPException: Nếu token không hợp lệ
    """
    jwt_manager = get_jwt_manager()
    payload = jwt_manager.verify_token(credentials.credentials, "access")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return int(user_id)


def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency để lấy full payload từ JWT token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Full token payload
        
    Raises:
        HTTPException: Nếu token không hợp lệ
    """
    jwt_manager = get_jwt_manager()
    return jwt_manager.verify_token(credentials.credentials, "access")
