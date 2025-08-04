"""
Advanced Caching Library for Microservices
==========================================

Comprehensive caching solution with support for Redis, in-memory caching,
distributed caching, cache invalidation strategies, and performance optimization.

Features:
- Redis distributed caching
- In-memory local caching
- Multi-level caching (L1/L2)
- Cache invalidation patterns
- TTL and expiration management
- Cache warming and preloading
- Performance metrics
- Async/await support
- Decorator-based caching
- Cache-aside, write-through, write-behind patterns

Usage:
    from libs.caching import CacheManager, cache_function, invalidate_cache
    
    # Initialize cache manager
    cache = CacheManager(
        redis_url="redis://localhost:6379",
        default_ttl=3600
    )
    
    # Manual caching
    await cache.set("user:123", user_data, ttl=1800)
    user_data = await cache.get("user:123")
    
    # Decorator-based caching
    @cache_function(ttl=600, key_prefix="product")
    async def get_product(product_id: int):
        # Function result automatically cached
        return await fetch_product_from_db(product_id)
    
    # Cache invalidation
    await invalidate_cache("user:*")
"""

from .cache_manager import CacheManager, CacheBackend
from .decorators import cache_function, cache_result, invalidate_cache
from .strategies import (
    CacheStrategy,
    CacheAsideStrategy,
    WriteThroughStrategy,
    WriteBehindStrategy
)
from .config import CacheConfig
from .backends import RedisBackend, MemoryBackend, MultiLevelBackend
from .metrics import CacheMetrics
from .utils import generate_cache_key, serialize_data, deserialize_data

__all__ = [
    "CacheManager",
    "CacheBackend",
    "cache_function",
    "cache_result", 
    "invalidate_cache",
    "CacheStrategy",
    "CacheAsideStrategy",
    "WriteThroughStrategy",
    "WriteBehindStrategy",
    "CacheConfig",
    "RedisBackend",
    "MemoryBackend",
    "MultiLevelBackend",
    "CacheMetrics",
    "generate_cache_key",
    "serialize_data",
    "deserialize_data"
]
