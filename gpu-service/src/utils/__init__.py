"""
SIRA GPU Service - Utilities
Common utilities and helper functions
"""

from .logger import logger, setup_logging
from .gpu_utils import (
    get_gpu_info,
    check_gpu_availability,
    get_gpu_memory_info,
    monitor_gpu_usage
)
from .model_utils import (
    generate_request_id,
    calculate_tokens,
    validate_model_name,
    format_model_size
)
from .cache_utils import (
    CacheManager,
    get_cache_key,
    serialize_request,
    deserialize_response
)

__all__ = [
    # Logging
    "logger",
    "setup_logging",
    
    # GPU utilities
    "get_gpu_info",
    "check_gpu_availability", 
    "get_gpu_memory_info",
    "monitor_gpu_usage",
    
    # Model utilities
    "generate_request_id",
    "calculate_tokens",
    "validate_model_name",
    "format_model_size",
    
    # Cache utilities
    "CacheManager",
    "get_cache_key",
    "serialize_request",
    "deserialize_response"
]
