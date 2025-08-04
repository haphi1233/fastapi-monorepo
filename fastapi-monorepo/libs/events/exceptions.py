"""
Custom exceptions for event-driven communication
"""

from typing import Optional, Dict, Any


class EventBusError(Exception):
    """Base exception for event bus errors"""
    
    def __init__(
        self, 
        message: str, 
        event_type: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.event_type = event_type
        self.event_data = event_data


class EventPublishError(EventBusError):
    """Error publishing event to message broker"""
    pass


class EventSubscribeError(EventBusError):
    """Error subscribing to event from message broker"""
    pass


class EventHandlerError(EventBusError):
    """Error in event handler execution"""
    pass


class EventSerializationError(EventBusError):
    """Error serializing/deserializing event data"""
    pass


class MessageBrokerConnectionError(EventBusError):
    """Error connecting to message broker"""
    pass
