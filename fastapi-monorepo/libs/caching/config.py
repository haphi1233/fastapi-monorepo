"""
Caching Configuration
====================

Configuration classes for caching system including Redis, memory caching,
TTL settings, and performance optimization parameters.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class CacheBackendType(str, Enum):
    """Cache backend types"""
    REDIS = "redis"
    MEMORY = "memory"
    MULTI_LEVEL = "multi_level"
    DUMMY = "dummy"


class CacheStrategy(str, Enum):
    """Cache strategies"""
    CACHE_ASIDE = "cache_aside"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"


class EvictionPolicy(str, Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    RANDOM = "random"


class SerializationFormat(str, Enum):
    """Serialization formats"""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"


class CacheConfig(BaseModel):
    """Cache configuration"""
    
    # Basic settings
    enabled: bool = True
    backend: CacheBackendType = CacheBackendType.REDIS
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    
    # TTL settings
    default_ttl: int = 3600  # seconds
    max_ttl: int = 86400  # 24 hours
    min_ttl: int = 60  # 1 minute
    
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    redis_pool_size: int = 10
    redis_timeout: int = 30
    
    # Memory cache settings
    memory_max_size: int = 1000  # Maximum number of items
    memory_eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    
    # Multi-level cache settings
    l1_backend: CacheBackendType = CacheBackendType.MEMORY
    l1_max_size: int = 500
    l1_ttl: int = 300  # 5 minutes
    l2_backend: CacheBackendType = CacheBackendType.REDIS
    l2_ttl: int = 3600  # 1 hour
    
    # Serialization
    serialization_format: SerializationFormat = SerializationFormat.JSON
    compress_data: bool = False
    compression_threshold: int = 1024  # bytes
    
    # Performance
    batch_size: int = 100
    pipeline_enabled: bool = True
    connection_pool_enabled: bool = True
    
    # Monitoring
    metrics_enabled: bool = True
    log_cache_operations: bool = False
    
    # Key management
    key_prefix: str = ""
    key_separator: str = ":"
    namespace: str = "default"
    
    # Cache warming
    warm_cache_on_startup: bool = False
    warm_cache_patterns: List[str] = Field(default_factory=list)
    
    # Invalidation
    invalidation_enabled: bool = True
    invalidation_patterns: List[str] = Field(default_factory=list)
    
    # Circuit breaker for cache failures
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: int = 60
    
    class Config:
        use_enum_values = True
    
    @classmethod
    def create_redis_config(
        cls,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600
    ) -> "CacheConfig":
        """Create Redis cache configuration"""
        return cls(
            backend=CacheBackendType.REDIS,
            redis_url=redis_url,
            default_ttl=default_ttl
        )
    
    @classmethod
    def create_memory_config(
        cls,
        max_size: int = 1000,
        default_ttl: int = 3600
    ) -> "CacheConfig":
        """Create memory cache configuration"""
        return cls(
            backend=CacheBackendType.MEMORY,
            memory_max_size=max_size,
            default_ttl=default_ttl
        )
    
    @classmethod
    def create_multi_level_config(
        cls,
        redis_url: str = "redis://localhost:6379",
        l1_max_size: int = 500,
        l1_ttl: int = 300,
        l2_ttl: int = 3600
    ) -> "CacheConfig":
        """Create multi-level cache configuration"""
        return cls(
            backend=CacheBackendType.MULTI_LEVEL,
            redis_url=redis_url,
            l1_max_size=l1_max_size,
            l1_ttl=l1_ttl,
            l2_ttl=l2_ttl
        )
    
    @classmethod
    def create_development_config(cls) -> "CacheConfig":
        """Create development configuration"""
        return cls(
            backend=CacheBackendType.MEMORY,
            memory_max_size=100,
            default_ttl=300,
            log_cache_operations=True,
            metrics_enabled=True
        )
