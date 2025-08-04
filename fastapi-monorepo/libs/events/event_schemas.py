"""
Event schemas for type-safe event communication
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Standard event types"""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Product events
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_DELETED = "product.deleted"
    PRODUCT_STOCK_UPDATED = "product.stock_updated"
    
    # Article events
    ARTICLE_CREATED = "article.created"
    ARTICLE_UPDATED = "article.updated"
    ARTICLE_DELETED = "article.deleted"
    ARTICLE_PUBLISHED = "article.published"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"


class BaseEvent(BaseModel):
    """Base event schema with common fields"""
    
    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    source_service: str = Field(..., description="Service that published the event")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    version: str = Field(default="1.0", description="Event schema version")
    data: Dict[str, Any] = Field(..., description="Event payload data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserEvent(BaseEvent):
    """User-related events"""
    
    @classmethod
    def user_created(
        cls,
        event_id: str,
        source_service: str,
        user_id: int,
        username: str,
        email: str,
        full_name: Optional[str] = None,
        is_superuser: bool = False,
        correlation_id: Optional[str] = None
    ) -> "UserEvent":
        """Create user.created event"""
        return cls(
            event_id=event_id,
            event_type=EventType.USER_CREATED,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "user_id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name,
                "is_superuser": is_superuser
            }
        )
    
    @classmethod
    def user_updated(
        cls,
        event_id: str,
        source_service: str,
        user_id: int,
        updated_fields: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> "UserEvent":
        """Create user.updated event"""
        return cls(
            event_id=event_id,
            event_type=EventType.USER_UPDATED,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "user_id": user_id,
                "updated_fields": updated_fields
            }
        )
    
    @classmethod
    def user_login(
        cls,
        event_id: str,
        source_service: str,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "UserEvent":
        """Create user.login event"""
        return cls(
            event_id=event_id,
            event_type=EventType.USER_LOGIN,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "user_id": user_id,
                "username": username,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )


class ProductEvent(BaseEvent):
    """Product-related events"""
    
    @classmethod
    def product_created(
        cls,
        event_id: str,
        source_service: str,
        product_id: int,
        name: str,
        price: float,
        category: str,
        created_by_user_id: int,
        stock_quantity: int = 0,
        correlation_id: Optional[str] = None
    ) -> "ProductEvent":
        """Create product.created event"""
        return cls(
            event_id=event_id,
            event_type=EventType.PRODUCT_CREATED,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "product_id": product_id,
                "name": name,
                "price": price,
                "category": category,
                "created_by_user_id": created_by_user_id,
                "stock_quantity": stock_quantity
            }
        )
    
    @classmethod
    def product_stock_updated(
        cls,
        event_id: str,
        source_service: str,
        product_id: int,
        old_quantity: int,
        new_quantity: int,
        quantity_change: int,
        updated_by_user_id: int,
        correlation_id: Optional[str] = None
    ) -> "ProductEvent":
        """Create product.stock_updated event"""
        return cls(
            event_id=event_id,
            event_type=EventType.PRODUCT_STOCK_UPDATED,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "product_id": product_id,
                "old_quantity": old_quantity,
                "new_quantity": new_quantity,
                "quantity_change": quantity_change,
                "updated_by_user_id": updated_by_user_id
            }
        )


class ArticleEvent(BaseEvent):
    """Article-related events"""
    
    @classmethod
    def article_created(
        cls,
        event_id: str,
        source_service: str,
        article_id: int,
        title: str,
        author_user_id: int,
        category: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "ArticleEvent":
        """Create article.created event"""
        return cls(
            event_id=event_id,
            event_type=EventType.ARTICLE_CREATED,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "article_id": article_id,
                "title": title,
                "author_user_id": author_user_id,
                "category": category
            }
        )
    
    @classmethod
    def article_published(
        cls,
        event_id: str,
        source_service: str,
        article_id: int,
        title: str,
        author_user_id: int,
        published_at: datetime,
        correlation_id: Optional[str] = None
    ) -> "ArticleEvent":
        """Create article.published event"""
        return cls(
            event_id=event_id,
            event_type=EventType.ARTICLE_PUBLISHED,
            source_service=source_service,
            correlation_id=correlation_id,
            data={
                "article_id": article_id,
                "title": title,
                "author_user_id": author_user_id,
                "published_at": published_at.isoformat()
            }
        )


# Union type for all event types
Event = Union[BaseEvent, UserEvent, ProductEvent, ArticleEvent]
