"""
Metrics middleware for Prometheus monitoring
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge
import structlog

logger = structlog.get_logger("middleware.metrics")

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

ANALYSIS_COUNT = Counter(
    'analysis_requests_total',
    'Total analysis requests',
    ['status']
)

AGENT_PROCESSING_TIME = Histogram(
    'agent_processing_duration_seconds',
    'Agent processing duration in seconds',
    ['agent_name']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting Prometheus metrics
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Collect metrics and process request
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        # Skip metrics collection for metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Get endpoint pattern (remove query params and IDs)
        endpoint = self._get_endpoint_pattern(request.url.path)
        method = request.method
        
        # Increment active requests
        ACTIVE_REQUESTS.inc()
        
        # Start timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Record analysis-specific metrics
            if endpoint.startswith("/api/v1/analyze"):
                if response.status_code == 200:
                    ANALYSIS_COUNT.labels(status="started").inc()
                elif response.status_code >= 400:
                    ANALYSIS_COUNT.labels(status="failed").inc()
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record error metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            ANALYSIS_COUNT.labels(status="error").inc()
            
            raise
            
        finally:
            # Decrement active requests
            ACTIVE_REQUESTS.dec()
    
    def _get_endpoint_pattern(self, path: str) -> str:
        """
        Convert path to endpoint pattern for metrics
        
        Args:
            path: Request path
            
        Returns:
            Endpoint pattern
        """
        # Remove query parameters
        path = path.split("?")[0]
        
        # Replace UUIDs with placeholder
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        path = re.sub(uuid_pattern, '{id}', path, flags=re.IGNORECASE)
        
        # Replace other IDs (numeric)
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


def record_agent_processing_time(agent_name: str, duration: float):
    """
    Record agent processing time metric
    
    Args:
        agent_name: Name of the agent
        duration: Processing duration in seconds
    """
    AGENT_PROCESSING_TIME.labels(agent_name=agent_name).observe(duration)


def record_analysis_completion(status: str):
    """
    Record analysis completion metric
    
    Args:
        status: Analysis completion status (completed, failed, timeout)
    """
    ANALYSIS_COUNT.labels(status=status).inc()
