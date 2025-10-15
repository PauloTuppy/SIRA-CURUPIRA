"""
Rate limiting middleware
"""

import time
from typing import Callable, Dict, Tuple

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ...config import settings

logger = structlog.get_logger("middleware.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware
    """
    
    def __init__(self, app):
        super().__init__(app)
        # In-memory storage for rate limiting
        # Format: {client_ip: (request_count, window_start_time)}
        self.clients: Dict[str, Tuple[int, float]] = {}
        self.max_requests = settings.rate_limit_requests
        self.window_minutes = settings.rate_limit_window_minutes
        self.window_seconds = self.window_minutes * 60
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits and process request
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                max_requests=self.max_requests,
                window_minutes=self.window_minutes,
                request_id=getattr(request.state, "request_id", None)
            )
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "max_requests": self.max_requests,
                    "window_minutes": self.window_minutes,
                    "retry_after": self._get_retry_after(client_ip, current_time)
                }
            )
        
        # Update request count
        self._update_request_count(client_ip, current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining_requests = self._get_remaining_requests(client_ip, current_time)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(int(self._get_window_reset_time(client_ip, current_time)))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers (for load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited"""
        if client_ip not in self.clients:
            return False
        
        request_count, window_start = self.clients[client_ip]
        
        # Check if window has expired
        if current_time - window_start > self.window_seconds:
            return False
        
        # Check if limit exceeded
        return request_count >= self.max_requests
    
    def _update_request_count(self, client_ip: str, current_time: float):
        """Update request count for client"""
        if client_ip not in self.clients:
            self.clients[client_ip] = (1, current_time)
            return
        
        request_count, window_start = self.clients[client_ip]
        
        # Check if window has expired
        if current_time - window_start > self.window_seconds:
            # Start new window
            self.clients[client_ip] = (1, current_time)
        else:
            # Increment count in current window
            self.clients[client_ip] = (request_count + 1, window_start)
    
    def _get_remaining_requests(self, client_ip: str, current_time: float) -> int:
        """Get remaining requests for client"""
        if client_ip not in self.clients:
            return self.max_requests
        
        request_count, window_start = self.clients[client_ip]
        
        # Check if window has expired
        if current_time - window_start > self.window_seconds:
            return self.max_requests
        
        return max(0, self.max_requests - request_count)
    
    def _get_window_reset_time(self, client_ip: str, current_time: float) -> float:
        """Get window reset time"""
        if client_ip not in self.clients:
            return current_time + self.window_seconds
        
        _, window_start = self.clients[client_ip]
        return window_start + self.window_seconds
    
    def _get_retry_after(self, client_ip: str, current_time: float) -> int:
        """Get retry after seconds"""
        reset_time = self._get_window_reset_time(client_ip, current_time)
        return max(1, int(reset_time - current_time))
    
    def cleanup_expired_entries(self, current_time: float):
        """Clean up expired rate limit entries"""
        expired_clients = [
            client_ip for client_ip, (_, window_start) in self.clients.items()
            if current_time - window_start > self.window_seconds
        ]
        
        for client_ip in expired_clients:
            del self.clients[client_ip]
        
        if expired_clients:
            logger.debug(
                "Cleaned up expired rate limit entries",
                expired_count=len(expired_clients)
            )
