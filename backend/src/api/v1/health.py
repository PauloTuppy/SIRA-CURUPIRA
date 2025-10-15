"""
Health check API endpoints
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
import structlog

from ...services.coordinator import CoordinatorService
from ...config import settings

router = APIRouter()
logger = structlog.get_logger("api.health")


def get_coordinator_service(request: Request) -> CoordinatorService:
    """Get coordinator service from app state"""
    if not hasattr(request.app.state, 'coordinator'):
        return None
    return request.app.state.coordinator


@router.get("/health")
async def health_check(
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns:
        Health status information
    """
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment
        }
        
        # Add coordinator health if available
        if coordinator:
            coordinator_health = await coordinator.health_check()
            health_data["coordinator"] = coordinator_health
        else:
            health_data["coordinator"] = {"status": "not_initialized"}
        
        # Determine overall status
        if coordinator and coordinator_health.get("status") != "healthy":
            health_data["status"] = "degraded"
        
        return health_data
        
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/health/detailed")
async def detailed_health_check(
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> Dict[str, Any]:
    """
    Detailed health check with component status
    
    Returns:
        Detailed health information
    """
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug
            },
            "components": {}
        }
        
        # Check coordinator service
        if coordinator:
            coordinator_health = await coordinator.health_check()
            health_data["components"]["coordinator"] = coordinator_health
            
            if coordinator_health.get("status") != "healthy":
                health_data["status"] = "degraded"
        else:
            health_data["components"]["coordinator"] = {
                "status": "not_initialized",
                "error": "Coordinator service not available"
            }
            health_data["status"] = "unhealthy"
        
        # Check external services (simulated)
        health_data["components"]["external_services"] = {
            "rag_service": {
                "status": "unknown",
                "url": settings.rag_service_url
            },
            "gpu_service": {
                "status": "unknown", 
                "url": settings.gpu_service_url
            },
            "firestore": {
                "status": "unknown",
                "project": settings.google_cloud_project
            }
        }
        
        # System information
        import psutil
        import platform
        
        health_data["system"] = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
        
        return health_data
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/ready")
async def readiness_check(
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> Dict[str, Any]:
    """
    Readiness check for Kubernetes
    
    Returns:
        Readiness status
    """
    try:
        if not coordinator:
            raise HTTPException(
                status_code=503,
                detail="Coordinator service not available"
            )
        
        coordinator_health = await coordinator.health_check()
        
        if coordinator_health.get("status") != "healthy":
            raise HTTPException(
                status_code=503,
                detail="Coordinator service not healthy"
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.app_name,
            "version": settings.app_version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for Kubernetes
    
    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.app_version
    }
