"""
Cache Utilities for GPU Service
In-memory and Redis caching for inference results
"""

import json
import time
import hashlib
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..config import settings
from .logger import logger


class InMemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times: Dict[str, float] = {}
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.cache:
            return True
        
        entry = self.cache[key]
        if "expires_at" not in entry:
            return False
        
        return time.time() > entry["expires_at"]
    
    def _evict_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if "expires_at" in entry and current_time > entry["expires_at"]
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _evict_lru(self):
        """Evict least recently used entries if cache is full"""
        if len(self.cache) < self.max_size:
            return
        
        # Sort by access time and remove oldest
        sorted_keys = sorted(self.access_times.items(), key=lambda x: x[1])
        keys_to_remove = [key for key, _ in sorted_keys[:len(self.cache) - self.max_size + 1]]
        
        for key in keys_to_remove:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        self._evict_expired()
        
        if key not in self.cache or self._is_expired(key):
            return None
        
        self.access_times[key] = time.time()
        return self.cache[key]["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        self._evict_expired()
        self._evict_lru()
        
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None
        
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time()
        }
        self.access_times[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.access_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        self._evict_expired()
        return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._evict_expired()
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": getattr(self, "_hit_rate", 0.0),
            "total_requests": getattr(self, "_total_requests", 0),
            "total_hits": getattr(self, "_total_hits", 0)
        }


class RedisCache:
    """Redis-based cache"""
    
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, falling back to in-memory cache")
            return False
        
        try:
            self.client = redis.from_url(self.redis_url)
            await self.client.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self._connected or not self.client:
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if not self._connected or not self.client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            
            if ttl > 0:
                await self.client.setex(key, ttl, serialized_value)
            else:
                await self.client.set(key, serialized_value)
            
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self._connected or not self.client:
            return False
        
        try:
            result = await self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all keys (use with caution)"""
        if not self._connected or not self.client:
            return False
        
        try:
            await self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


class CacheManager:
    """Unified cache manager with fallback support"""
    
    def __init__(self):
        self.memory_cache = InMemoryCache(
            max_size=settings.cache_max_size,
            default_ttl=settings.cache_ttl
        )
        self.redis_cache: Optional[RedisCache] = None
        self.use_redis = False
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "misses": 0
        }
        
        if settings.redis_url and REDIS_AVAILABLE:
            self.redis_cache = RedisCache(settings.redis_url, settings.cache_ttl)
    
    async def initialize(self):
        """Initialize cache connections"""
        if self.redis_cache:
            self.use_redis = await self.redis_cache.connect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis first, then memory)"""
        self.stats["total_requests"] += 1
        
        # Try Redis first if available
        if self.use_redis and self.redis_cache:
            value = await self.redis_cache.get(key)
            if value is not None:
                self.stats["redis_hits"] += 1
                # Also cache in memory for faster access
                self.memory_cache.set(key, value)
                return value
        
        # Try memory cache
        value = self.memory_cache.get(key)
        if value is not None:
            self.stats["memory_hits"] += 1
            return value
        
        self.stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache (both Redis and memory)"""
        # Set in memory cache
        self.memory_cache.set(key, value, ttl)
        
        # Set in Redis if available
        if self.use_redis and self.redis_cache:
            await self.redis_cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete key from both caches"""
        memory_deleted = self.memory_cache.delete(key)
        redis_deleted = True
        
        if self.use_redis and self.redis_cache:
            redis_deleted = await self.redis_cache.delete(key)
        
        return memory_deleted or redis_deleted
    
    async def clear(self) -> None:
        """Clear both caches"""
        self.memory_cache.clear()
        
        if self.use_redis and self.redis_cache:
            await self.redis_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = self.stats["memory_hits"] + self.stats["redis_hits"]
        hit_rate = (total_hits / self.stats["total_requests"]) if self.stats["total_requests"] > 0 else 0.0
        
        return {
            **self.stats,
            "total_hits": total_hits,
            "hit_rate": hit_rate,
            "memory_cache_size": self.memory_cache.size(),
            "redis_available": self.use_redis
        }


# Global cache manager instance
cache_manager = CacheManager()


def get_cache_key(prompt: str, model: str, options: Dict[str, Any]) -> str:
    """Generate cache key for inference request"""
    # Create deterministic key from request parameters
    key_data = {
        "prompt": prompt.strip(),
        "model": model,
        "options": {k: v for k, v in sorted(options.items()) if k in [
            "temperature", "top_p", "top_k", "max_tokens", "seed"
        ]}
    }
    
    # Create hash
    key_string = json.dumps(key_data, sort_keys=True)
    hash_object = hashlib.sha256(key_string.encode())
    return f"inference:{hash_object.hexdigest()[:16]}"


def serialize_request(request_data: Dict[str, Any]) -> str:
    """Serialize request data for caching"""
    return json.dumps(request_data, sort_keys=True, default=str)


def deserialize_response(response_data: str) -> Dict[str, Any]:
    """Deserialize cached response data"""
    return json.loads(response_data)
