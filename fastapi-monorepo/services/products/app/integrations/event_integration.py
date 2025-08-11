"""
Event-driven integration for Product Service
"""

from typing import Optional, Dict, Any
import logging

from libs.events import EventBus, EventPublisher, EventSubscriber, EventType, BaseEvent
from libs.service_registry import global_service_registry

logger = logging.getLogger(__name__)


class ProductEventIntegration:
    """
    Event-driven integration utilities for Product Service
    
    Provides methods to publish and subscribe to events for async communication
    """
    
    def __init__(self):
        self.service_registry = global_service_registry
        self.event_bus = self.service_registry.get_event_bus("products")
        self.publisher = EventPublisher(self.event_bus)
        self.subscriber = EventSubscriber(self.event_bus)
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for Product Service"""
        
        @self.subscriber.on_event(EventType.USER_CREATED)
        async def handle_user_created(event: BaseEvent):
            """Handle user.created event"""
            user_data = event.data
            logger.info(
                f"New user created: {user_data['username']} ({user_data['email']}) "
                f"- Product service can now track products for this user"
            )
            
            # Could implement user-specific product initialization here
            # For example: create default product categories for new users
        
        @self.subscriber.on_event(EventType.USER_LOGIN)
        async def handle_user_login(event: BaseEvent):
            """Handle user.login event"""
            user_data = event.data
            logger.info(
                f"User login detected: {user_data['username']} "
                f"- Product service could update user activity tracking"
            )
            
            # Could implement login-based product recommendations here
        
        # Add more event handlers as needed
    
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
        """
        Publish product.created event
        
        Args:
            product_id: ID of created product
            name: Product name
            price: Product price
            category: Product category
            created_by_user_id: User who created the product
            stock_quantity: Initial stock quantity
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            success = await self.publisher.publish_product_created(
                product_id=product_id,
                name=name,
                price=price,
                category=category,
                created_by_user_id=created_by_user_id,
                stock_quantity=stock_quantity,
                correlation_id=correlation_id
            )
            
            if success:
                logger.info(f"Published product.created event for product {product_id}")
            else:
                logger.error(f"Failed to publish product.created event for product {product_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing product.created event: {e}")
            return False
    
    async def publish_product_stock_updated(
        self,
        product_id: int,
        old_quantity: int,
        new_quantity: int,
        quantity_change: int,
        updated_by_user_id: int,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish product.stock_updated event
        
        Args:
            product_id: ID of product with updated stock
            old_quantity: Previous stock quantity
            new_quantity: New stock quantity
            quantity_change: Change in quantity (positive or negative)
            updated_by_user_id: User who updated the stock
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            success = await self.publisher.publish_product_stock_updated(
                product_id=product_id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                quantity_change=quantity_change,
                updated_by_user_id=updated_by_user_id,
                correlation_id=correlation_id
            )
            
            if success:
                logger.info(f"Published product.stock_updated event for product {product_id}")
            else:
                logger.error(f"Failed to publish product.stock_updated event for product {product_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing product.stock_updated event: {e}")
            return False
    
    async def start_event_subscriptions(self):
        """Start all event subscriptions"""
        try:
            await self.event_bus.connect()
            await self.subscriber.start_all_subscriptions()
            logger.info("Started all event subscriptions for Product Service")
            
        except Exception as e:
            logger.error(f"Failed to start event subscriptions: {e}")
            raise
    
    async def stop_event_subscriptions(self):
        """Stop all event subscriptions"""
        try:
            await self.event_bus.disconnect()
            logger.info("Stopped all event subscriptions for Product Service")
            
        except Exception as e:
            logger.error(f"Failed to stop event subscriptions: {e}")
    
    async def get_event_health(self) -> Dict[str, Any]:
        """Get health status of event bus"""
        try:
            return await self.event_bus.health_check()
            
        except Exception as e:
            logger.error(f"Failed to get event health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """Get information about current subscriptions"""
        return {
            "handler_count": self.subscriber.get_handler_count(),
            "subscribed_events": [event.value for event in self.subscriber.get_subscribed_events()],
            "service_name": self.event_bus.service_name
        }
