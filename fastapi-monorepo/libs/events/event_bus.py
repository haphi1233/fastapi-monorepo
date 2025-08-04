"""
Event Bus implementation using Redis as message broker
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass
import redis.asyncio as redis

from .event_schemas import BaseEvent, Event, EventType
from .exceptions import (
    EventBusError,
    EventPublishError,
    EventSubscribeError,
    EventHandlerError,
    MessageBrokerConnectionError
)

logger = logging.getLogger(__name__)


@dataclass
class EventHandler:
    """Event handler configuration"""
    event_type: EventType
    handler_func: Callable[[BaseEvent], None]
    service_name: str
    handler_id: str = None
    
    def __post_init__(self):
        if self.handler_id is None:
            self.handler_id = f"{self.service_name}_{self.event_type.value}_{uuid.uuid4().hex[:8]}"


class EventBus:
    """
    Event Bus implementation using Redis pub/sub
    
    Provides asynchronous event publishing and subscribing capabilities
    with error handling, retry logic, and event persistence.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        service_name: str = "unknown",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.redis_url = redis_url
        self.service_name = service_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.handlers: Dict[EventType, List[EventHandler]] = {}
        self.is_connected = False
        self.subscriber_tasks: List[asyncio.Task] = []
    
    async def connect(self):
        """Connect to Redis message broker"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            
            logger.info(f"Connected to Redis event bus: {self.redis_url}")
            
        except Exception as e:
            raise MessageBrokerConnectionError(f"Failed to connect to Redis: {e}")
    
    async def disconnect(self):
        """Disconnect from Redis message broker"""
        try:
            # Cancel subscriber tasks
            for task in self.subscriber_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            self.subscriber_tasks.clear()
            
            # Close pubsub
            if self.pubsub:
                await self.pubsub.close()
                self.pubsub = None
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None
            
            self.is_connected = False
            logger.info("Disconnected from Redis event bus")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")
    
    async def publish(
        self,
        event: BaseEvent,
        persist: bool = True,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish event to message broker
        
        Args:
            event: Event to publish
            persist: Whether to persist event to Redis stream
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.is_connected:
            await self.connect()
        
        # Set correlation ID if provided
        if correlation_id:
            event.correlation_id = correlation_id
        
        # Set source service
        event.source_service = self.service_name
        
        try:
            # Serialize event
            event_data = event.model_dump_json()
            
            # Publish to channel
            channel = f"events:{event.event_type.value}"
            
            for attempt in range(self.max_retries):
                try:
                    # Publish to pub/sub channel
                    await self.redis_client.publish(channel, event_data)
                    
                    # Optionally persist to Redis stream for durability
                    if persist:
                        stream_key = f"events_stream:{event.event_type.value}"
                        await self.redis_client.xadd(
                            stream_key,
                            {
                                "event_id": event.event_id,
                                "event_type": event.event_type.value,
                                "timestamp": event.timestamp.isoformat(),
                                "source_service": event.source_service,
                                "data": event_data
                            }
                        )
                    
                    logger.info(
                        f"Published event: {event.event_type.value} "
                        f"(id: {event.event_id}, service: {event.source_service})"
                    )
                    return True
                    
                except Exception as e:
                    logger.warning(f"Publish attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        raise
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type.value}: {e}")
            raise EventPublishError(
                f"Failed to publish event: {e}",
                event_type=event.event_type.value,
                event_data=event.model_dump()
            )
    
    async def subscribe(self, event_handler: EventHandler):
        """
        Subscribe to event type with handler
        
        Args:
            event_handler: Event handler configuration
        """
        if not self.is_connected:
            await self.connect()
        
        # Add handler to registry
        if event_handler.event_type not in self.handlers:
            self.handlers[event_handler.event_type] = []
        
        self.handlers[event_handler.event_type].append(event_handler)
        
        # Start subscriber task if not already running
        channel = f"events:{event_handler.event_type.value}"
        task = asyncio.create_task(
            self._subscriber_loop(channel, event_handler.event_type)
        )
        self.subscriber_tasks.append(task)
        
        logger.info(
            f"Subscribed to {event_handler.event_type.value} "
            f"with handler {event_handler.handler_id}"
        )
    
    async def _subscriber_loop(self, channel: str, event_type: EventType):
        """
        Background subscriber loop for specific event type
        """
        try:
            # Create new pubsub instance for this subscription
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            logger.info(f"Started subscriber loop for channel: {channel}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse event data
                        event_data = json.loads(message['data'])
                        event = BaseEvent.model_validate(event_data)
                        
                        # Execute all handlers for this event type
                        handlers = self.handlers.get(event_type, [])
                        for handler in handlers:
                            try:
                                await self._execute_handler(handler, event)
                            except Exception as e:
                                logger.error(
                                    f"Handler {handler.handler_id} failed for event "
                                    f"{event.event_id}: {e}"
                                )
                    
                    except Exception as e:
                        logger.error(f"Error processing message from {channel}: {e}")
        
        except asyncio.CancelledError:
            logger.info(f"Subscriber loop cancelled for channel: {channel}")
        except Exception as e:
            logger.error(f"Subscriber loop error for {channel}: {e}")
            raise EventSubscribeError(f"Subscriber loop failed: {e}")
        finally:
            try:
                await pubsub.close()
            except:
                pass
    
    async def _execute_handler(self, handler: EventHandler, event: BaseEvent):
        """
        Execute event handler with error handling
        """
        try:
            logger.debug(
                f"Executing handler {handler.handler_id} for event {event.event_id}"
            )
            
            # Execute handler (sync or async)
            if asyncio.iscoroutinefunction(handler.handler_func):
                await handler.handler_func(event)
            else:
                handler.handler_func(event)
            
            logger.debug(
                f"Handler {handler.handler_id} completed for event {event.event_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Handler {handler.handler_id} failed for event {event.event_id}: {e}"
            )
            raise EventHandlerError(
                f"Handler execution failed: {e}",
                event_type=event.event_type.value,
                event_data=event.model_dump()
            )
    
    async def get_event_history(
        self,
        event_type: EventType,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[BaseEvent]:
        """
        Get event history from Redis stream
        
        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            List of events from history
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            stream_key = f"events_stream:{event_type.value}"
            
            # Build time range
            start_id = "-"
            end_id = "+"
            
            if start_time:
                start_timestamp = int(start_time.timestamp() * 1000)
                start_id = f"{start_timestamp}-0"
            
            if end_time:
                end_timestamp = int(end_time.timestamp() * 1000)
                end_id = f"{end_timestamp}-0"
            
            # Get events from stream
            events = await self.redis_client.xrange(
                stream_key,
                min=start_id,
                max=end_id,
                count=limit
            )
            
            # Parse events
            parsed_events = []
            for event_id, fields in events:
                try:
                    event_data = json.loads(fields['data'])
                    event = BaseEvent.model_validate(event_data)
                    parsed_events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse event {event_id}: {e}")
            
            logger.info(f"Retrieved {len(parsed_events)} events from history")
            return parsed_events
            
        except Exception as e:
            logger.error(f"Failed to get event history: {e}")
            raise EventBusError(f"Failed to get event history: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of event bus connection
        
        Returns:
            Health status information
        """
        try:
            if not self.redis_client:
                return {
                    "status": "unhealthy",
                    "error": "Not connected to Redis",
                    "connected": False
                }
            
            # Test Redis connection
            await self.redis_client.ping()
            
            # Get Redis info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "connected": True,
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "handlers_count": sum(len(handlers) for handlers in self.handlers.values()),
                "active_subscriptions": len(self.subscriber_tasks)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
