"""
Logging configuration for the SIRA Backend Service
"""

import logging
import sys
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "info", log_format: str = "json") -> None:
    """
    Setup structured logging configuration
    
    Args:
        log_level: Logging level (debug, info, warning, error)
        log_format: Log format (json, text)
    """
    
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
            structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Configure specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Suppress noisy third-party loggers
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("google.cloud").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class RequestContextFilter(logging.Filter):
    """
    Logging filter to add request context to log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add request context to log record
        
        Args:
            record: Log record to filter
            
        Returns:
            True to include the record
        """
        # Add request ID if available
        if hasattr(record, 'request_id'):
            record.request_id = getattr(record, 'request_id', None)
        
        # Add user ID if available
        if hasattr(record, 'user_id'):
            record.user_id = getattr(record, 'user_id', None)
            
        return True


class StructuredFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """
        Add custom fields to log record
        
        Args:
            log_record: Log record dictionary
            record: Original log record
            message_dict: Message dictionary
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add service information
        log_record['service'] = 'sira-backend'
        log_record['version'] = '1.0.0'
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
            
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
            
        # Add analysis context if available
        if hasattr(record, 'analysis_id'):
            log_record['analysis_id'] = record.analysis_id


def log_analysis_event(
    logger: structlog.BoundLogger,
    event: str,
    analysis_id: str,
    **kwargs: Any
) -> None:
    """
    Log an analysis-related event with structured data
    
    Args:
        logger: Structured logger instance
        event: Event name
        analysis_id: Analysis ID
        **kwargs: Additional context data
    """
    logger.info(
        event,
        analysis_id=analysis_id,
        event_type="analysis",
        **kwargs
    )


def log_agent_event(
    logger: structlog.BoundLogger,
    event: str,
    agent_name: str,
    analysis_id: str,
    **kwargs: Any
) -> None:
    """
    Log an agent-related event with structured data
    
    Args:
        logger: Structured logger instance
        event: Event name
        agent_name: Name of the agent
        analysis_id: Analysis ID
        **kwargs: Additional context data
    """
    logger.info(
        event,
        agent_name=agent_name,
        analysis_id=analysis_id,
        event_type="agent",
        **kwargs
    )


def log_service_event(
    logger: structlog.BoundLogger,
    event: str,
    service_name: str,
    **kwargs: Any
) -> None:
    """
    Log a service-related event with structured data
    
    Args:
        logger: Structured logger instance
        event: Event name
        service_name: Name of the service
        **kwargs: Additional context data
    """
    logger.info(
        event,
        service_name=service_name,
        event_type="service",
        **kwargs
    )


def log_error_event(
    logger: structlog.BoundLogger,
    error: Exception,
    context: str,
    **kwargs: Any
) -> None:
    """
    Log an error event with structured data
    
    Args:
        logger: Structured logger instance
        error: Exception that occurred
        context: Context where the error occurred
        **kwargs: Additional context data
    """
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        event_type="error",
        **kwargs,
        exc_info=True
    )


def log_performance_event(
    logger: structlog.BoundLogger,
    operation: str,
    duration_seconds: float,
    **kwargs: Any
) -> None:
    """
    Log a performance event with structured data
    
    Args:
        logger: Structured logger instance
        operation: Operation name
        duration_seconds: Duration in seconds
        **kwargs: Additional context data
    """
    logger.info(
        "Performance metric",
        operation=operation,
        duration_seconds=duration_seconds,
        event_type="performance",
        **kwargs
    )
