"""
Event-Driven Architecture Library for Microservices Communication

Provides utilities for asynchronous event-based communication
between services using message brokers (Redis, RabbitMQ).
"""

from .event_bus import EventBus, EventHandler
from .event_schemas import BaseEvent, UserEvent, ProductEvent, ArticleEvent, EventType
from .event_publisher import EventPublisher
from .event_subscriber import EventSubscriber
from .exceptions import EventBusError, EventPublishError, EventSubscribeError

__all__ = [
    "EventBus",
    "EventHandler", 
    "EventPublisher",
    "EventSubscriber",
    "BaseEvent",
    "UserEvent",
    "ProductEvent", 
    "ArticleEvent",
    "EventType",
    "EventBusError",
    "EventPublishError",
    "EventSubscribeError"
]
