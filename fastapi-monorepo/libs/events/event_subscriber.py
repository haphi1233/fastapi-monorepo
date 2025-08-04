"""
Event Subscriber utility for easy event handling
"""

import asyncio
import logging
from typing import Callable, Dict, Any, Optional
from functools import wraps

from .event_bus import EventBus, EventHandler
from .event_schemas import BaseEvent, EventType

logger = logging.getLogger(__name__)


class EventSubscriber:
    """
    High-level event subscriber with decorator-based handler registration
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.handlers: Dict[EventType, list] = {}
    
    def on_event(self, event_type: EventType):
        """
        Decorator to register event handler
        
        Usage:
            @subscriber.on_event(EventType.USER_CREATED)
            async def handle_user_created(event: BaseEvent):
                print(f"User created: {event.data['username']}")
        """
        def decorator(func: Callable[[BaseEvent], None]):
            @wraps(func)
            async def wrapper(event: BaseEvent):
                try:
                    logger.debug(f"Handling {event_type.value} event: {event.event_id}")
                    
                    if asyncio.iscoroutinefunction(func):
                        await func(event)
                    else:
                        func(event)
                    
                    logger.debug(f"Successfully handled {event_type.value} event: {event.event_id}")
                    
                except Exception as e:
                    logger.error(f"Error handling {event_type.value} event {event.event_id}: {e}")
                    raise
            
            # Register handler
            handler = EventHandler(
                event_type=event_type,
                handler_func=wrapper,
                service_name=self.event_bus.service_name
            )
            
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            
            self.handlers[event_type].append(handler)
            
            return wrapper
        
        return decorator
    
    async def start_all_subscriptions(self):
        """Start all registered event subscriptions"""
        for event_type, handlers in self.handlers.items():
            for handler in handlers:
                await self.event_bus.subscribe(handler)
                logger.info(f"Started subscription for {event_type.value} with handler {handler.handler_id}")
    
    def get_handler_count(self) -> int:
        """Get total number of registered handlers"""
        return sum(len(handlers) for handlers in self.handlers.values())
    
    def get_subscribed_events(self) -> list:
        """Get list of subscribed event types"""
        return list(self.handlers.keys())


# Convenience functions for common event handling patterns

def create_user_event_handlers(event_bus: EventBus) -> EventSubscriber:
    """Create subscriber with common user event handlers"""
    subscriber = EventSubscriber(event_bus)
    
    @subscriber.on_event(EventType.USER_CREATED)
    async def log_user_created(event: BaseEvent):
        user_data = event.data
        logger.info(
            f"User created: {user_data['username']} ({user_data['email']}) "
            f"by service {event.source_service}"
        )
    
    @subscriber.on_event(EventType.USER_LOGIN)
    async def log_user_login(event: BaseEvent):
        user_data = event.data
        logger.info(
            f"User login: {user_data['username']} from {user_data.get('ip_address', 'unknown')} "
            f"at {event.timestamp}"
        )
    
    return subscriber


def create_product_event_handlers(event_bus: EventBus) -> EventSubscriber:
    """Create subscriber with common product event handlers"""
    subscriber = EventSubscriber(event_bus)
    
    @subscriber.on_event(EventType.PRODUCT_CREATED)
    async def log_product_created(event: BaseEvent):
        product_data = event.data
        logger.info(
            f"Product created: {product_data['name']} (${product_data['price']}) "
            f"in category {product_data['category']} by user {product_data['created_by_user_id']}"
        )
    
    @subscriber.on_event(EventType.PRODUCT_STOCK_UPDATED)
    async def log_stock_updated(event: BaseEvent):
        stock_data = event.data
        logger.info(
            f"Stock updated for product {stock_data['product_id']}: "
            f"{stock_data['old_quantity']} -> {stock_data['new_quantity']} "
            f"(change: {stock_data['quantity_change']})"
        )
    
    return subscriber


def create_article_event_handlers(event_bus: EventBus) -> EventSubscriber:
    """Create subscriber with common article event handlers"""
    subscriber = EventSubscriber(event_bus)
    
    @subscriber.on_event(EventType.ARTICLE_CREATED)
    async def log_article_created(event: BaseEvent):
        article_data = event.data
        logger.info(
            f"Article created: '{article_data['title']}' "
            f"by user {article_data['author_user_id']}"
        )
    
    @subscriber.on_event(EventType.ARTICLE_PUBLISHED)
    async def log_article_published(event: BaseEvent):
        article_data = event.data
        logger.info(
            f"Article published: '{article_data['title']}' "
            f"by user {article_data['author_user_id']} at {article_data['published_at']}"
        )
    
    return subscriber
