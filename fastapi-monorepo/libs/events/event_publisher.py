"""
Event Publisher utility for easy event publishing
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from .event_bus import EventBus
from .event_schemas import BaseEvent, UserEvent, ProductEvent, ArticleEvent, EventType

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    High-level event publisher with convenience methods
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return f"evt_{uuid.uuid4().hex}"
    
    async def publish_user_created(
        self,
        user_id: int,
        username: str,
        email: str,
        full_name: Optional[str] = None,
        is_superuser: bool = False,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish user.created event"""
        event = UserEvent.user_created(
            event_id=self._generate_event_id(),
            source_service=self.event_bus.service_name,
            user_id=user_id,
            username=username,
            email=email,
            full_name=full_name,
            is_superuser=is_superuser,
            correlation_id=correlation_id
        )
        
        return await self.event_bus.publish(event)
    
    async def publish_user_login(
        self,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish user.login event"""
        event = UserEvent.user_login(
            event_id=self._generate_event_id(),
            source_service=self.event_bus.service_name,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id
        )
        
        return await self.event_bus.publish(event)
    
    async def publish_product_created(
        self,
        product_id: int,
        name: str,
        price: float,
        category: str,
        created_by_user_id: int,
        stock_quantity: int = 0,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish product.created event"""
        event = ProductEvent.product_created(
            event_id=self._generate_event_id(),
            source_service=self.event_bus.service_name,
            product_id=product_id,
            name=name,
            price=price,
            category=category,
            created_by_user_id=created_by_user_id,
            stock_quantity=stock_quantity,
            correlation_id=correlation_id
        )
        
        return await self.event_bus.publish(event)
    
    async def publish_product_stock_updated(
        self,
        product_id: int,
        old_quantity: int,
        new_quantity: int,
        quantity_change: int,
        updated_by_user_id: int,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish product.stock_updated event"""
        event = ProductEvent.product_stock_updated(
            event_id=self._generate_event_id(),
            source_service=self.event_bus.service_name,
            product_id=product_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            quantity_change=quantity_change,
            updated_by_user_id=updated_by_user_id,
            correlation_id=correlation_id
        )
        
        return await self.event_bus.publish(event)
    
    async def publish_article_created(
        self,
        article_id: int,
        title: str,
        author_user_id: int,
        category: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish article.created event"""
        event = ArticleEvent.article_created(
            event_id=self._generate_event_id(),
            source_service=self.event_bus.service_name,
            article_id=article_id,
            title=title,
            author_user_id=author_user_id,
            category=category,
            correlation_id=correlation_id
        )
        
        return await self.event_bus.publish(event)
    
    async def publish_custom_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish custom event"""
        event = BaseEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            source_service=self.event_bus.service_name,
            correlation_id=correlation_id,
            data=data,
            metadata=metadata or {}
        )
        
        return await self.event_bus.publish(event)
