"""
SIRA GPU Service - API Endpoints
FastAPI routes and endpoints
"""

from .health import health_router
from .inference import inference_router
from .models import models_router
from .metrics import metrics_router

__all__ = [
    "health_router",
    "inference_router", 
    "models_router",
    "metrics_router"
]
