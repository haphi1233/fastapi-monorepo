"""
HTTP-based integration for Product Service
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from typing import Optional, Dict, Any
import logging

from libs.http_client import AuthServiceClient
from libs.service_registry import global_service_registry

logger = logging.getLogger(__name__)


class ProductHTTPIntegration:
    """
    HTTP-based integration utilities for Product Service
    
    Provides methods to communicate with other services via HTTP calls
    """
    
    def __init__(self):
        self.service_registry = global_service_registry
        self.auth_client = AuthServiceClient(self.service_registry.get_http_registry())
    
    async def get_user_info(self, user_id: int, jwt_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Auth Service
        
        Args:
            user_id: User ID to lookup
            jwt_token: JWT token for authentication
            
        Returns:
            User information dict or None if failed
        """
        try:
            user_info = await self.auth_client.get_user_info(user_id, jwt_token)
            logger.info(f"Retrieved user info for user_id: {user_id}")
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to get user info for user_id {user_id}: {e}")
            return None
    
    async def verify_user_exists(self, user_id: int, jwt_token: str) -> bool:
        """
        Verify if user exists in Auth Service
        
        Args:
            user_id: User ID to verify
            jwt_token: JWT token for authentication
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            return await self.auth_client.verify_user_exists(user_id, jwt_token)
            
        except Exception as e:
            logger.error(f"Failed to verify user existence for user_id {user_id}: {e}")
            return False
    
    async def get_user_by_username(self, username: str, jwt_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username from Auth Service
        
        Args:
            username: Username to lookup
            jwt_token: JWT token for authentication
            
        Returns:
            User information dict or None if not found
        """
        try:
            return await self.auth_client.get_user_by_username(username, jwt_token)
            
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
            return await self.auth_client.check_user_permissions(user_id, permission, jwt_token)
            
        except Exception as e:
            logger.error(f"Failed to check permissions for user {user_id}: {e}")
            return False
    
    async def enrich_product_with_user_info(
        self, 
        product_data: Dict[str, Any], 
        jwt_token: str
    ) -> Dict[str, Any]:
        """
        Enrich product data with user information
        
        Args:
            product_data: Product data dict
            jwt_token: JWT token for authentication
            
        Returns:
            Enriched product data with user info
        """
        try:
            # Get user info if product has created_by or updated_by fields
            enriched_data = product_data.copy()
            
            # Check for user ID fields that need enrichment
            user_fields = ['created_by', 'updated_by', 'owner_id']
            
            for field in user_fields:
                if field in product_data and product_data[field]:
                    user_id = product_data[field]
                    user_info = await self.get_user_info(user_id, jwt_token)
                    
                    if user_info:
                        enriched_data[f"{field}_info"] = {
                            "id": user_info.get("id"),
                            "username": user_info.get("username"),
                            "full_name": user_info.get("full_name"),
                            "email": user_info.get("email")
                        }
                        logger.debug(f"Enriched product with {field}_info")
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to enrich product with user info: {e}")
            return product_data
    
    async def validate_product_permissions(
        self, 
        user_id: int, 
        action: str, 
        jwt_token: str
    ) -> bool:
        """
        Validate if user has permission to perform action on products
        
        Args:
            user_id: User ID to check
            action: Action to validate (create, update, delete, etc.)
            jwt_token: JWT token for authentication
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Define permission mapping
            permission_map = {
                "create": "product.create",
                "update": "product.update", 
                "delete": "product.delete",
                "manage_stock": "product.manage_stock",
                "view_all": "product.view_all"
            }
            
            permission = permission_map.get(action)
            if not permission:
                logger.warning(f"Unknown action: {action}")
                return False
            
            return await self.check_user_permissions(user_id, permission, jwt_token)
            
        except Exception as e:
            logger.error(f"Failed to validate product permissions for user {user_id}: {e}")
            return False
    
    async def close(self):
        """Close HTTP clients"""
        await self.auth_client.close()
