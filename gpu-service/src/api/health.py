"""
Health Check Endpoints for GPU Service
"""

from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models.responses import HealthResponse, HealthStatus, GPUStatusResponse
from ..services.ollama_client import ollama_client
from ..services.metrics_service import metrics_service
from ..utils.logger import logger, log_health_check
from ..utils.gpu_utils import get_gpu_info, monitor_gpu_usage, check_cuda_availability

health_router = APIRouter(prefix="/health", tags=["health"])

# Service start time for uptime calculation
SERVICE_START_TIME = datetime.utcnow()


@health_router.get("/", response_model=HealthResponse)
async def basic_health():
    """Basic health check"""
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        uptime=uptime,
        version=settings.app_version
    )


@health_router.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check - service is ready to accept requests"""
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    services = {}
    overall_status = HealthStatus.HEALTHY
    
    # Check OLLAMA connection
    try:
        start_time = datetime.utcnow()
        ollama_health = await ollama_client.health_check()
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        if ollama_health["status"] == "healthy":
            services["ollama"] = HealthStatus.HEALTHY
            log_health_check("ollama", "healthy", response_time)
        else:
            services["ollama"] = HealthStatus.UNHEALTHY
            overall_status = HealthStatus.UNHEALTHY
            log_health_check("ollama", "unhealthy", response_time, error=ollama_health.get("error"))
            
    except Exception as e:
        services["ollama"] = HealthStatus.UNHEALTHY
        overall_status = HealthStatus.UNHEALTHY
        log_health_check("ollama", "unhealthy", 0, error=str(e))
    
    # Check GPU availability
    try:
        gpu_info = get_gpu_info()
        if gpu_info.available:
            services["gpu"] = HealthStatus.HEALTHY
        else:
            services["gpu"] = HealthStatus.DEGRADED
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
    except Exception as e:
        services["gpu"] = HealthStatus.UNHEALTHY
        overall_status = HealthStatus.UNHEALTHY
        logger.error(f"GPU health check failed: {e}")
    
    # Check cache if enabled
    if settings.enable_cache:
        try:
            # Simple cache test
            from ..utils.cache_utils import cache_manager
            test_key = "health_check_test"
            await cache_manager.set(test_key, "test_value", ttl=60)
            cached_value = await cache_manager.get(test_key)
            
            if cached_value == "test_value":
                services["cache"] = HealthStatus.HEALTHY
                await cache_manager.delete(test_key)
            else:
                services["cache"] = HealthStatus.DEGRADED
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
        except Exception as e:
            services["cache"] = HealthStatus.UNHEALTHY
            if overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED
            logger.error(f"Cache health check failed: {e}")
    
    return HealthResponse(
        status=overall_status,
        uptime=uptime,
        version=settings.app_version,
        services=services
    )


@health_router.get("/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness check - service is alive"""
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        uptime=uptime,
        version=settings.app_version
    )


@health_router.get("/detailed")
async def detailed_health():
    """Detailed health check with system information"""
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": uptime,
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {},
        "system": {},
        "configuration": {
            "model_name": settings.model_name,
            "ollama_host": settings.ollama_host,
            "cache_enabled": settings.enable_cache,
            "gpu_monitoring": settings.enable_gpu_monitoring
        }
    }
    
    overall_healthy = True
    
    # OLLAMA health
    try:
        ollama_health = await ollama_client.health_check()
        health_data["services"]["ollama"] = ollama_health
        if ollama_health["status"] != "healthy":
            overall_healthy = False
    except Exception as e:
        health_data["services"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # GPU health
    try:
        gpu_info = get_gpu_info()
        gpu_usage = monitor_gpu_usage()
        cuda_info = check_cuda_availability()
        
        health_data["services"]["gpu"] = {
            "available": gpu_info.available,
            "device_count": gpu_info.device_count,
            "driver_version": gpu_info.driver_version,
            "cuda_version": gpu_info.cuda_version,
            "usage": gpu_usage,
            "cuda_check": cuda_info
        }
        
        if not gpu_info.available:
            overall_healthy = False
            
    except Exception as e:
        health_data["services"]["gpu"] = {
            "status": "error",
            "error": str(e)
        }
        overall_healthy = False
    
    # System metrics
    try:
        system_metrics = metrics_service.get_system_metrics()
        health_data["system"] = system_metrics
    except Exception as e:
        health_data["system"] = {
            "error": str(e)
        }
    
    # Service metrics
    try:
        service_metrics = metrics_service.get_metrics()
        health_data["metrics"] = service_metrics
    except Exception as e:
        health_data["metrics"] = {
            "error": str(e)
        }
    
    # Cache health
    if settings.enable_cache:
        try:
            from ..utils.cache_utils import cache_manager
            cache_stats = cache_manager.get_stats()
            health_data["services"]["cache"] = {
                "status": "healthy",
                "stats": cache_stats
            }
        except Exception as e:
            health_data["services"]["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
    
    health_data["status"] = "healthy" if overall_healthy else "unhealthy"
    
    return health_data


@health_router.get("/gpu", response_model=GPUStatusResponse)
async def gpu_status():
    """Get detailed GPU status"""
    try:
        gpu_info = get_gpu_info()
        
        if not gpu_info.available:
            return GPUStatusResponse(
                available=False,
                device_count=0,
                devices=[]
            )
        
        # Get current usage
        gpu_usage = monitor_gpu_usage()
        
        return GPUStatusResponse(
            available=gpu_info.available,
            device_count=gpu_info.device_count,
            devices=gpu_info.devices,
            driver_version=gpu_info.driver_version,
            cuda_version=gpu_info.cuda_version,
            total_memory=sum(device["memory_total"] for device in gpu_info.devices) / 1024.0,  # GB
            used_memory=sum(device["memory_used"] for device in gpu_info.devices) / 1024.0,    # GB
            free_memory=sum(device["memory_free"] for device in gpu_info.devices) / 1024.0,    # GB
            utilization=gpu_usage.get("utilization", 0.0),
            temperature=gpu_usage.get("temperature", 0.0)
        )
        
    except Exception as e:
        logger.error(f"Failed to get GPU status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get GPU status: {e}")


@health_router.get("/startup")
async def startup_check():
    """Check if service has completed startup"""
    try:
        # Check if OLLAMA is accessible
        await ollama_client.health_check()
        
        # Check if default model is available
        from ..services.model_manager import model_manager
        model_info = model_manager.get_model_info(settings.model_name)
        
        if model_info and model_info.loaded:
            return {
                "status": "ready",
                "message": "Service startup completed successfully",
                "model": settings.model_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "starting",
                "message": "Service is still starting up",
                "model": settings.model_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Startup check failed: {e}",
            "timestamp": datetime.utcnow().isoformat()
        }
