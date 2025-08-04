"""
Specialized HTTP client for Auth Service communication
"""

from typing import Optional, Dict, Any, List
import logging

from .service_client import ServiceClient, ServiceRegistry
from .exceptions import ServiceAuthenticationError, ServiceValidationError

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """
    Specialized client for Auth Service communication
    
    Provides high-level methods for common auth operations:
    - User verification
    - User information retrieval
    - Permission checks
    """
    
    def __init__(self, service_registry: Optional[ServiceRegistry] = None):
        self.client = ServiceClient("auth", service_registry)
    
    async def get_user_info(self, user_id: int, jwt_token: str) -> Dict[str, Any]:
        """
        Get user information by ID
        
        Args:
            user_id: User ID to lookup
            jwt_token: JWT token for authentication
            
        Returns:
            User information dict
            
        Raises:
            ServiceAuthenticationError: If JWT token is invalid
            ServiceNotFoundError: If user not found
        """
        try:
            response = await self.client.get(
                f"/api/v1/users/{user_id}",
                jwt_token=jwt_token
            )
            logger.info(f"Retrieved user info for user_id: {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get user info for user_id {user_id}: {e}")
            raise
    
    async def verify_user_exists(self, user_id: int, jwt_token: str) -> bool:
        """
        Verify if user exists
        
        Args:
            user_id: User ID to verify
            jwt_token: JWT token for authentication
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            await self.get_user_info(user_id, jwt_token)
            return True
        except Exception:
            return False
    
    async def get_user_by_username(self, username: str, jwt_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username
        
        Args:
            username: Username to lookup
            jwt_token: JWT token for authentication
            
        Returns:
            User information dict or None if not found
        """
        try:
            response = await self.client.get(
                "/api/v1/users/search",
                params={"username": username, "per_page": 1},
                jwt_token=jwt_token
            )
            
            users = response.get("items", [])
            if users:
                logger.info(f"Found user by username: {username}")
                return users[0]
            else:
                logger.info(f"User not found by username: {username}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    async def check_user_permissions(self, user_id: int, permission: str, jwt_token: str) -> bool:
        """
        Check if user has specific permission
        
        Args:
            user_id: User ID to check
            permission: Permission to check
            jwt_token: JWT token for authentication
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            user_info = await self.get_user_info(user_id, jwt_token)
            
            # Check if user is superuser (has all permissions)
            if user_info.get("is_superuser", False):
                logger.info(f"User {user_id} has superuser permissions")
                return True
            
            # Check specific permissions (would need to implement permissions system)
            # For now, return False for non-superusers
            logger.info(f"User {user_id} does not have permission: {permission}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check permissions for user {user_id}: {e}")
            return False
    
    async def get_users_list(
        self, 
        jwt_token: str,
        page: int = 1,
        per_page: int = 10,
        search_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get paginated list of users
        
        Args:
            jwt_token: JWT token for authentication
            page: Page number
            per_page: Items per page
            search_params: Optional search parameters
            
        Returns:
            Paginated user list response
        """
        try:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            if search_params:
                params.update(search_params)
            
            response = await self.client.get(
                "/api/v1/users/search",
                params=params,
                jwt_token=jwt_token
            )
            
            logger.info(f"Retrieved users list: page {page}, per_page {per_page}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get users list: {e}")
            raise
    
    async def validate_jwt_token(self, jwt_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and get user payload
        
        Args:
            jwt_token: JWT token to validate
            
        Returns:
            JWT payload if valid, None if invalid
        """
        try:
            # Use the token to get current user info
            response = await self.client.get(
                "/api/v1/auth/me",
                jwt_token=jwt_token
            )
            
            logger.info("JWT token validated successfully")
            return response
            
        except ServiceAuthenticationError:
            logger.warning("JWT token validation failed")
            return None
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}")
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh JWT access token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token response or None if failed
        """
        try:
            response = await self.client.post(
                "/api/v1/auth/refresh",
                data={"refresh_token": refresh_token}
            )
            
            logger.info("JWT token refreshed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Failed to refresh JWT token: {e}")
            return None
    
    async def close(self):
        """Close the underlying HTTP client"""
        await self.client.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
