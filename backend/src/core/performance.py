"""
Performance optimization utilities for SIRA Backend
"""

import asyncio
import time
import functools
from typing import Dict, Any, Optional, Callable, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    request_count: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    recent_response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_response_time(self, response_time: float):
        """Add a response time measurement"""
        self.request_count += 1
        self.total_response_time += response_time
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        self.recent_response_times.append(response_time)
    
    def add_error(self):
        """Record an error"""
        self.error_count += 1
    
    def add_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits += 1
    
    def add_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses += 1
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time"""
        if self.request_count == 0:
            return 0.0
        return self.total_response_time / self.request_count
    
    @property
    def recent_average_response_time(self) -> float:
        """Calculate recent average response time"""
        if not self.recent_response_times:
            return 0.0
        return sum(self.recent_response_times) / len(self.recent_response_times)
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return self.cache_hits / total_cache_requests


class PerformanceMonitor:
    """Global performance monitoring"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self._lock = asyncio.Lock()
    
    async def record_request(self, endpoint: str, response_time: float, success: bool = True):
        """Record a request performance metric"""
        async with self._lock:
            metric = self.metrics[endpoint]
            metric.add_response_time(response_time)
            
            if not success:
                metric.add_error()
    
    async def record_cache_event(self, operation: str, hit: bool):
        """Record a cache event"""
        async with self._lock:
            metric = self.metrics[operation]
            if hit:
                metric.add_cache_hit()
            else:
                metric.add_cache_miss()
    
    async def get_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        async with self._lock:
            if endpoint:
                if endpoint in self.metrics:
                    metric = self.metrics[endpoint]
                    return {
                        "endpoint": endpoint,
                        "request_count": metric.request_count,
                        "average_response_time": metric.average_response_time,
                        "recent_average_response_time": metric.recent_average_response_time,
                        "min_response_time": metric.min_response_time,
                        "max_response_time": metric.max_response_time,
                        "error_rate": metric.error_rate,
                        "cache_hit_rate": metric.cache_hit_rate
                    }
                return {}
            
            # Return all metrics
            return {
                endpoint: {
                    "request_count": metric.request_count,
                    "average_response_time": metric.average_response_time,
                    "recent_average_response_time": metric.recent_average_response_time,
                    "error_rate": metric.error_rate,
                    "cache_hit_rate": metric.cache_hit_rate
                }
                for endpoint, metric in self.metrics.items()
            }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def performance_tracking(endpoint_name: Optional[str] = None):
    """Decorator for tracking endpoint performance"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            endpoint = endpoint_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                response_time = end_time - start_time
                await performance_monitor.record_request(endpoint, response_time, success)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            endpoint = endpoint_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                response_time = end_time - start_time
                # For sync functions, we can't await, so we schedule the coroutine
                asyncio.create_task(
                    performance_monitor.record_request(endpoint, response_time, success)
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ConnectionPool:
    """HTTP connection pool for external services"""
    
    def __init__(self, max_connections: int = 100, max_keepalive: int = 20):
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._pools: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def get_client(self, base_url: str) -> Any:
        """Get or create HTTP client for base URL"""
        async with self._lock:
            if base_url not in self._pools:
                import httpx
                
                limits = httpx.Limits(
                    max_connections=self.max_connections,
                    max_keepalive_connections=self.max_keepalive
                )
                
                self._pools[base_url] = httpx.AsyncClient(
                    base_url=base_url,
                    limits=limits,
                    timeout=httpx.Timeout(30.0)
                )
            
            return self._pools[base_url]
    
    async def close_all(self):
        """Close all connection pools"""
        async with self._lock:
            for client in self._pools.values():
                await client.aclose()
            self._pools.clear()


# Global connection pool
connection_pool = ConnectionPool()


class BatchProcessor:
    """Batch processing for improved throughput"""
    
    def __init__(self, batch_size: int = 10, max_wait_time: float = 1.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self._batches: Dict[str, List] = defaultdict(list)
        self._batch_futures: Dict[str, List] = defaultdict(list)
        self._batch_timers: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def add_to_batch(self, batch_key: str, item: Any) -> Any:
        """Add item to batch and return future result"""
        async with self._lock:
            # Create future for this item
            future = asyncio.Future()
            
            # Add to batch
            self._batches[batch_key].append(item)
            self._batch_futures[batch_key].append(future)
            
            # Set timer if this is the first item
            if len(self._batches[batch_key]) == 1:
                self._batch_timers[batch_key] = time.time()
            
            # Process batch if it's full or timer expired
            should_process = (
                len(self._batches[batch_key]) >= self.batch_size or
                time.time() - self._batch_timers[batch_key] >= self.max_wait_time
            )
            
            if should_process:
                # Process the batch
                batch_items = self._batches[batch_key].copy()
                batch_futures = self._batch_futures[batch_key].copy()
                
                # Clear the batch
                self._batches[batch_key].clear()
                self._batch_futures[batch_key].clear()
                del self._batch_timers[batch_key]
                
                # Process in background
                asyncio.create_task(
                    self._process_batch(batch_key, batch_items, batch_futures)
                )
        
        return await future
    
    async def _process_batch(self, batch_key: str, items: List[Any], futures: List[asyncio.Future]):
        """Process a batch of items"""
        try:
            # This is a placeholder - implement actual batch processing logic
            results = await self._execute_batch(batch_key, items)
            
            # Set results for all futures
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
                    
        except Exception as e:
            # Set exception for all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)
    
    async def _execute_batch(self, batch_key: str, items: List[Any]) -> List[Any]:
        """Execute batch processing - override in subclasses"""
        # Default implementation processes items individually
        results = []
        for item in items:
            # Placeholder processing
            results.append({"processed": item, "batch_key": batch_key})
        return results


# Global batch processor
batch_processor = BatchProcessor()


@asynccontextmanager
async def performance_context(operation_name: str):
    """Context manager for tracking operation performance"""
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        response_time = end_time - start_time
        await performance_monitor.record_request(operation_name, response_time)


class CacheManager:
    """Advanced caching with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: deque = deque()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key not in self._cache:
                await performance_monitor.record_cache_event("cache_get", False)
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                self._access_order.remove(key)
                await performance_monitor.record_cache_event("cache_get", False)
                return None
            
            # Update access order
            self._access_order.remove(key)
            self._access_order.append(key)
            
            await performance_monitor.record_cache_event("cache_get", True)
            return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            ttl = ttl or self.default_ttl
            expires_at = time.time() + ttl
            
            # Remove if already exists
            if key in self._cache:
                self._access_order.remove(key)
            
            # Evict if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = self._access_order.popleft()
                del self._cache[oldest_key]
            
            # Add new entry
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at
            }
            self._access_order.append(key)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": await self._calculate_hit_rate()
            }
    
    async def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate from performance monitor"""
        metrics = await performance_monitor.get_metrics("cache_get")
        if not metrics:
            return 0.0
        return metrics.get("cache_hit_rate", 0.0)


# Global cache manager
cache_manager = CacheManager(
    max_size=getattr(settings, 'cache_max_size', 1000),
    default_ttl=getattr(settings, 'cache_ttl', 3600.0)
)


async def optimize_database_queries():
    """Optimize database query performance"""
    # Placeholder for database optimization
    pass


async def preload_common_data():
    """Preload commonly accessed data into cache"""
    # Placeholder for data preloading
    pass


class RequestThrottler:
    """Request throttling to prevent overload"""

    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests: deque = deque()
        self._lock = asyncio.Lock()

    async def can_proceed(self) -> bool:
        """Check if request can proceed"""
        async with self._lock:
            now = time.time()

            # Remove old requests (older than 1 minute)
            while self.requests and now - self.requests[0] > 60:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False


# Global request throttler
request_throttler = RequestThrottler()
