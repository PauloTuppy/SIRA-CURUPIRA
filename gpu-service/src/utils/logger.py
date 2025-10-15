"""
Logging Configuration for GPU Service
Structured logging with JSON format for production
"""

import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import structlog
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False
    jsonlogger = None

from ..config import settings


def setup_logging() -> None:
    """Setup structured logging configuration"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s" if settings.log_format == "json" else "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Create logger instance
logger = structlog.get_logger("sira.gpu_service")


def log_request(
    method: str,
    path: str,
    status_code: int,
    processing_time: float,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """Log HTTP request with structured data"""
    logger.info(
        "HTTP request processed",
        method=method,
        path=path,
        status_code=status_code,
        processing_time=processing_time,
        request_id=request_id,
        user_id=user_id,
        **kwargs
    )


def log_inference(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    processing_time: float,
    request_id: Optional[str] = None,
    cached: bool = False,
    **kwargs: Any
) -> None:
    """Log inference request with metrics"""
    logger.info(
        "Inference completed",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        processing_time=processing_time,
        request_id=request_id,
        cached=cached,
        **kwargs
    )


def log_error(
    error: Exception,
    context: str,
    request_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """Log error with context and structured data"""
    logger.error(
        f"Error in {context}",
        error_type=type(error).__name__,
        error_message=str(error),
        request_id=request_id,
        **kwargs,
        exc_info=True
    )


def log_gpu_metrics(
    utilization: float,
    memory_used: float,
    memory_total: float,
    temperature: Optional[float] = None,
    **kwargs: Any
) -> None:
    """Log GPU metrics"""
    logger.info(
        "GPU metrics",
        gpu_utilization=utilization,
        memory_used_gb=memory_used,
        memory_total_gb=memory_total,
        memory_usage_percent=(memory_used / memory_total * 100) if memory_total > 0 else 0,
        temperature=temperature,
        **kwargs
    )


def log_model_operation(
    operation: str,
    model: str,
    duration: Optional[float] = None,
    success: bool = True,
    **kwargs: Any
) -> None:
    """Log model operations (load, unload, etc.)"""
    logger.info(
        f"Model {operation}",
        operation=operation,
        model=model,
        duration=duration,
        success=success,
        **kwargs
    )


def log_cache_operation(
    operation: str,
    key: str,
    hit: bool = False,
    size: Optional[int] = None,
    **kwargs: Any
) -> None:
    """Log cache operations"""
    logger.debug(
        f"Cache {operation}",
        operation=operation,
        cache_key=key,
        cache_hit=hit,
        size=size,
        **kwargs
    )


def log_health_check(
    service: str,
    status: str,
    response_time: float,
    **kwargs: Any
) -> None:
    """Log health check results"""
    logger.info(
        "Health check",
        service=service,
        status=status,
        response_time=response_time,
        **kwargs
    )


class RequestLogger:
    """Context manager for request logging"""
    
    def __init__(self, request_id: str, operation: str):
        self.request_id = request_id
        self.operation = operation
        self.start_time = datetime.utcnow()
        self.logger = logger.bind(request_id=request_id)
    
    def __enter__(self):
        self.logger.info(f"Starting {self.operation}")
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                duration=duration,
                success=True
            )
        else:
            self.logger.error(
                f"Failed {self.operation}",
                duration=duration,
                success=False,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None,
                exc_info=True
            )


# Initialize logging on import
setup_logging()
