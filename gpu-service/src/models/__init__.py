"""
SIRA GPU Service - Pydantic Models
Data models for API requests and responses
"""

from .inference import (
    InferenceRequest,
    InferenceResponse,
    BatchInferenceRequest,
    BatchInferenceResponse,
    ModelInfo,
    GenerationOptions
)

from .responses import (
    HealthResponse,
    ErrorResponse,
    MetricsResponse,
    ModelStatusResponse,
    GPUStatusResponse
)

__all__ = [
    # Inference models
    "InferenceRequest",
    "InferenceResponse", 
    "BatchInferenceRequest",
    "BatchInferenceResponse",
    "ModelInfo",
    "GenerationOptions",
    
    # Response models
    "HealthResponse",
    "ErrorResponse",
    "MetricsResponse",
    "ModelStatusResponse",
    "GPUStatusResponse"
]
