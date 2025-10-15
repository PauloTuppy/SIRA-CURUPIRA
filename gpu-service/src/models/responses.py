"""
Response Models for GPU Service
Pydantic models for API responses
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceStatus(str, Enum):
    """Service status enumeration"""
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class HealthResponse(BaseModel):
    """Health check response"""
    status: HealthStatus = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime: float = Field(..., ge=0.0, description="Uptime in seconds")
    version: str = Field(..., description="Service version")
    services: Dict[str, HealthStatus] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "uptime": 3600.5,
                "version": "1.0.0",
                "services": {
                    "ollama": "healthy",
                    "gpu": "healthy",
                    "cache": "healthy"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid prompt length",
                "details": {"field": "prompt", "constraint": "max_length"},
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_123"
            }
        }


class MetricsResponse(BaseModel):
    """Metrics response"""
    requests_total: int = Field(..., ge=0, description="Total requests processed")
    requests_successful: int = Field(..., ge=0, description="Successful requests")
    requests_failed: int = Field(..., ge=0, description="Failed requests")
    average_response_time: float = Field(..., ge=0.0, description="Average response time in seconds")
    tokens_generated: int = Field(..., ge=0, description="Total tokens generated")
    cache_hits: int = Field(..., ge=0, description="Cache hits")
    cache_misses: int = Field(..., ge=0, description="Cache misses")
    uptime: float = Field(..., ge=0.0, description="Service uptime in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "requests_total": 1000,
                "requests_successful": 950,
                "requests_failed": 50,
                "average_response_time": 2.5,
                "tokens_generated": 50000,
                "cache_hits": 200,
                "cache_misses": 800,
                "uptime": 86400.0,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ModelStatusResponse(BaseModel):
    """Model status response"""
    name: str = Field(..., description="Model name")
    status: ServiceStatus = Field(..., description="Model status")
    loaded: bool = Field(..., description="Whether model is loaded")
    memory_usage: Optional[float] = Field(default=None, ge=0.0, description="Memory usage in GB")
    load_time: Optional[float] = Field(default=None, ge=0.0, description="Load time in seconds")
    last_used: Optional[datetime] = Field(default=None, description="Last usage timestamp")
    requests_processed: int = Field(default=0, ge=0, description="Requests processed by this model")
    average_inference_time: Optional[float] = Field(default=None, ge=0.0, description="Average inference time")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "gemma2:9b",
                "status": "running",
                "loaded": True,
                "memory_usage": 18.5,
                "load_time": 45.2,
                "last_used": "2024-01-15T10:25:00Z",
                "requests_processed": 150,
                "average_inference_time": 2.3
            }
        }


class GPUStatusResponse(BaseModel):
    """GPU status response"""
    available: bool = Field(..., description="Whether GPU is available")
    device_count: int = Field(..., ge=0, description="Number of GPU devices")
    devices: List[Dict[str, Any]] = Field(default_factory=list, description="GPU device information")
    driver_version: Optional[str] = Field(default=None, description="GPU driver version")
    cuda_version: Optional[str] = Field(default=None, description="CUDA version")
    total_memory: Optional[float] = Field(default=None, ge=0.0, description="Total GPU memory in GB")
    used_memory: Optional[float] = Field(default=None, ge=0.0, description="Used GPU memory in GB")
    free_memory: Optional[float] = Field(default=None, ge=0.0, description="Free GPU memory in GB")
    utilization: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="GPU utilization percentage")
    temperature: Optional[float] = Field(default=None, ge=0.0, description="GPU temperature in Celsius")
    
    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "device_count": 1,
                "devices": [
                    {
                        "id": 0,
                        "name": "NVIDIA L4",
                        "memory_total": 24576,
                        "memory_used": 18432,
                        "memory_free": 6144,
                        "utilization": 85.5,
                        "temperature": 72.0
                    }
                ],
                "driver_version": "535.104.05",
                "cuda_version": "12.2",
                "total_memory": 24.0,
                "used_memory": 18.0,
                "free_memory": 6.0,
                "utilization": 85.5,
                "temperature": 72.0
            }
        }


class ListModelsResponse(BaseModel):
    """List models response"""
    models: List[Dict[str, Any]] = Field(..., description="Available models")
    total: int = Field(..., ge=0, description="Total number of models")
    loaded: int = Field(..., ge=0, description="Number of loaded models")
    
    class Config:
        schema_extra = {
            "example": {
                "models": [
                    {
                        "name": "gemma2:9b",
                        "size": "9B",
                        "family": "gemma2",
                        "loaded": True,
                        "memory_usage": 18.5
                    },
                    {
                        "name": "gemma2:27b",
                        "size": "27B", 
                        "family": "gemma2",
                        "loaded": False,
                        "memory_usage": None
                    }
                ],
                "total": 2,
                "loaded": 1
            }
        }
