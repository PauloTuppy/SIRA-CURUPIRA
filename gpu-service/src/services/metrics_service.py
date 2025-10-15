"""
Metrics Service for GPU Service
Collects and exposes metrics for monitoring
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

from ..config import settings
from ..utils.logger import logger


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    processing_time: float
    cached: bool
    error: Optional[str] = None


@dataclass
class ServiceMetrics:
    """Service-level metrics"""
    start_time: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens_generated: int = 0
    total_processing_time: float = 0.0
    
    # Error tracking
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Recent requests for calculating averages
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    @property
    def uptime(self) -> float:
        """Service uptime in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate percentage"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100
    
    @property
    def average_response_time(self) -> float:
        """Average response time in seconds"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_processing_time / self.successful_requests
    
    @property
    def tokens_per_second(self) -> float:
        """Tokens generated per second"""
        if self.total_processing_time == 0:
            return 0.0
        return self.total_tokens_generated / self.total_processing_time
    
    @property
    def requests_per_minute(self) -> float:
        """Requests per minute (last hour)"""
        if not self.recent_requests:
            return 0.0
        
        # Count requests in the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = sum(
            1 for req in self.recent_requests
            if req.timestamp > one_hour_ago
        )
        
        return recent_count


class MetricsService:
    """Service for collecting and exposing metrics"""
    
    def __init__(self):
        self.metrics = ServiceMetrics()
        self.model_metrics: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        
        # Performance tracking
        self.response_times: deque = deque(maxlen=1000)
        self.token_counts: deque = deque(maxlen=1000)
        
        # System metrics
        self.system_metrics: Dict[str, Any] = {}
        self.last_system_update: Optional[datetime] = None
    
    def record_request(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        processing_time: float,
        cached: bool = False,
        error: Optional[str] = None
    ):
        """Record a request with its metrics"""
        timestamp = datetime.utcnow()
        
        # Create request metrics
        request_metrics = RequestMetrics(
            timestamp=timestamp,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            processing_time=processing_time,
            cached=cached,
            error=error
        )
        
        # Update global metrics
        self.metrics.total_requests += 1
        self.metrics.recent_requests.append(request_metrics)
        
        if error:
            self.metrics.failed_requests += 1
            self.metrics.errors_by_type[error] += 1
        else:
            self.metrics.successful_requests += 1
            self.metrics.total_tokens_generated += completion_tokens
            self.metrics.total_processing_time += processing_time
            
            # Track performance
            self.response_times.append(processing_time)
            self.token_counts.append(completion_tokens)
        
        if cached:
            self.metrics.cache_hits += 1
        else:
            self.metrics.cache_misses += 1
        
        # Update model-specific metrics
        model_metrics = self.model_metrics[model]
        model_metrics.total_requests += 1
        model_metrics.recent_requests.append(request_metrics)
        
        if error:
            model_metrics.failed_requests += 1
            model_metrics.errors_by_type[error] += 1
        else:
            model_metrics.successful_requests += 1
            model_metrics.total_tokens_generated += completion_tokens
            model_metrics.total_processing_time += processing_time
        
        if cached:
            model_metrics.cache_hits += 1
        else:
            model_metrics.cache_misses += 1
        
        logger.debug(
            "Recorded request metrics",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            processing_time=processing_time,
            cached=cached,
            error=error
        )
    
    def record_cache_hit(self):
        """Record a cache hit"""
        self.metrics.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        self.metrics.cache_misses += 1
    
    def record_error(self, error_type: str):
        """Record an error"""
        self.metrics.failed_requests += 1
        self.metrics.errors_by_type[error_type] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "uptime": self.metrics.uptime,
            "requests_total": self.metrics.total_requests,
            "requests_successful": self.metrics.successful_requests,
            "requests_failed": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "tokens_generated": self.metrics.total_tokens_generated,
            "tokens_per_second": self.metrics.tokens_per_second,
            "requests_per_minute": self.metrics.requests_per_minute,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_model_metrics(self, model: str) -> Dict[str, Any]:
        """Get metrics for a specific model"""
        if model not in self.model_metrics:
            return {}
        
        model_metrics = self.model_metrics[model]
        return {
            "model": model,
            "requests_total": model_metrics.total_requests,
            "requests_successful": model_metrics.successful_requests,
            "requests_failed": model_metrics.failed_requests,
            "success_rate": model_metrics.success_rate,
            "average_response_time": model_metrics.average_response_time,
            "tokens_generated": model_metrics.total_tokens_generated,
            "tokens_per_second": model_metrics.tokens_per_second,
            "cache_hits": model_metrics.cache_hits,
            "cache_misses": model_metrics.cache_misses,
            "cache_hit_rate": model_metrics.cache_hit_rate,
            "errors_by_type": dict(model_metrics.errors_by_type)
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.response_times:
            return {
                "response_time_p50": 0.0,
                "response_time_p95": 0.0,
                "response_time_p99": 0.0,
                "avg_tokens_per_request": 0.0
            }
        
        # Calculate percentiles
        sorted_times = sorted(self.response_times)
        n = len(sorted_times)
        
        p50_idx = int(n * 0.5)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        avg_tokens = sum(self.token_counts) / len(self.token_counts) if self.token_counts else 0
        
        return {
            "response_time_p50": sorted_times[p50_idx],
            "response_time_p95": sorted_times[p95_idx],
            "response_time_p99": sorted_times[p99_idx],
            "avg_tokens_per_request": avg_tokens
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics (cached for performance)"""
        now = datetime.utcnow()
        
        # Update system metrics every 30 seconds
        if (self.last_system_update is None or 
            (now - self.last_system_update).total_seconds() > 30):
            
            try:
                from ..utils.gpu_utils import get_system_info, monitor_gpu_usage
                
                self.system_metrics = {
                    "system": get_system_info(),
                    "gpu": monitor_gpu_usage(),
                    "timestamp": now.isoformat()
                }
                self.last_system_update = now
                
            except Exception as e:
                logger.error(f"Failed to get system metrics: {e}")
                self.system_metrics = {
                    "error": str(e),
                    "timestamp": now.isoformat()
                }
        
        return self.system_metrics
    
    def reset_metrics(self):
        """Reset all metrics (use with caution)"""
        logger.warning("Resetting all metrics")
        
        self.metrics = ServiceMetrics()
        self.model_metrics.clear()
        self.response_times.clear()
        self.token_counts.clear()
        self.system_metrics.clear()
        self.last_system_update = None
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        metrics = self.get_metrics()
        performance = self.get_performance_metrics()
        
        lines = [
            f"# HELP sira_gpu_requests_total Total number of requests",
            f"# TYPE sira_gpu_requests_total counter",
            f"sira_gpu_requests_total {metrics['requests_total']}",
            "",
            f"# HELP sira_gpu_requests_successful Successful requests",
            f"# TYPE sira_gpu_requests_successful counter", 
            f"sira_gpu_requests_successful {metrics['requests_successful']}",
            "",
            f"# HELP sira_gpu_requests_failed Failed requests",
            f"# TYPE sira_gpu_requests_failed counter",
            f"sira_gpu_requests_failed {metrics['requests_failed']}",
            "",
            f"# HELP sira_gpu_response_time_seconds Response time in seconds",
            f"# TYPE sira_gpu_response_time_seconds histogram",
            f"sira_gpu_response_time_seconds_sum {metrics['average_response_time'] * metrics['requests_successful']}",
            f"sira_gpu_response_time_seconds_count {metrics['requests_successful']}",
            "",
            f"# HELP sira_gpu_tokens_generated_total Total tokens generated",
            f"# TYPE sira_gpu_tokens_generated_total counter",
            f"sira_gpu_tokens_generated_total {metrics['tokens_generated']}",
            "",
            f"# HELP sira_gpu_cache_hits_total Cache hits",
            f"# TYPE sira_gpu_cache_hits_total counter",
            f"sira_gpu_cache_hits_total {metrics['cache_hits']}",
            "",
            f"# HELP sira_gpu_uptime_seconds Service uptime",
            f"# TYPE sira_gpu_uptime_seconds gauge",
            f"sira_gpu_uptime_seconds {metrics['uptime']}",
        ]
        
        return "\n".join(lines)


# Global metrics service instance
metrics_service = MetricsService()
