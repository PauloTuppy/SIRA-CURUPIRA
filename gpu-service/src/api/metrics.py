"""
Metrics Endpoints for GPU Service
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from datetime import datetime

from ..config import settings
from ..models.responses import MetricsResponse
from ..services.metrics_service import metrics_service
from ..utils.logger import logger

metrics_router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@metrics_router.get("/", response_model=MetricsResponse)
async def get_metrics():
    """Get service metrics"""
    try:
        metrics = metrics_service.get_metrics()
        
        return MetricsResponse(
            requests_total=metrics["requests_total"],
            requests_successful=metrics["requests_successful"],
            requests_failed=metrics["requests_failed"],
            average_response_time=metrics["average_response_time"],
            tokens_generated=metrics["tokens_generated"],
            cache_hits=metrics["cache_hits"],
            cache_misses=metrics["cache_misses"],
            uptime=metrics["uptime"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {e}"
        )


@metrics_router.get("/detailed")
async def get_detailed_metrics():
    """Get detailed metrics including performance data"""
    try:
        metrics = metrics_service.get_metrics()
        performance = metrics_service.get_performance_metrics()
        system = metrics_service.get_system_metrics()
        
        return {
            "service": metrics,
            "performance": performance,
            "system": system,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get detailed metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detailed metrics: {e}"
        )


@metrics_router.get("/model/{model_name}")
async def get_model_metrics(model_name: str):
    """Get metrics for a specific model"""
    try:
        model_metrics = metrics_service.get_model_metrics(model_name)
        
        if not model_metrics:
            raise HTTPException(
                status_code=404,
                detail=f"No metrics found for model {model_name}"
            )
        
        return model_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model metrics for {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model metrics: {e}"
        )


@metrics_router.get("/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format"""
    try:
        prometheus_metrics = metrics_service.export_prometheus_metrics()
        
        return Response(
            content=prometheus_metrics,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Failed to export Prometheus metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export Prometheus metrics: {e}"
        )


@metrics_router.get("/performance")
async def get_performance_metrics():
    """Get performance metrics (response times, throughput)"""
    try:
        performance = metrics_service.get_performance_metrics()
        
        return {
            "performance": performance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {e}"
        )


@metrics_router.get("/system")
async def get_system_metrics():
    """Get system metrics (CPU, memory, GPU)"""
    try:
        system = metrics_service.get_system_metrics()
        
        return system
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {e}"
        )


@metrics_router.get("/cache")
async def get_cache_metrics():
    """Get cache metrics"""
    try:
        from ..utils.cache_utils import cache_manager
        cache_stats = cache_manager.get_stats()
        
        return {
            "cache": cache_stats,
            "enabled": settings.enable_cache,
            "ttl": settings.cache_ttl,
            "max_size": settings.cache_max_size,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache metrics: {e}"
        )


@metrics_router.get("/errors")
async def get_error_metrics():
    """Get error metrics and statistics"""
    try:
        metrics = metrics_service.get_metrics()
        
        return {
            "total_errors": metrics["requests_failed"],
            "error_rate": (metrics["requests_failed"] / metrics["requests_total"] * 100) if metrics["requests_total"] > 0 else 0,
            "errors_by_type": metrics["errors_by_type"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get error metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get error metrics: {e}"
        )


@metrics_router.get("/throughput")
async def get_throughput_metrics():
    """Get throughput metrics (requests/min, tokens/sec)"""
    try:
        metrics = metrics_service.get_metrics()
        
        return {
            "requests_per_minute": metrics["requests_per_minute"],
            "tokens_per_second": metrics["tokens_per_second"],
            "average_tokens_per_request": (
                metrics["tokens_generated"] / metrics["requests_successful"]
                if metrics["requests_successful"] > 0 else 0
            ),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get throughput metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get throughput metrics: {e}"
        )


@metrics_router.post("/reset")
async def reset_metrics():
    """Reset all metrics (use with caution)"""
    try:
        if settings.environment == "production":
            raise HTTPException(
                status_code=403,
                detail="Metrics reset is not allowed in production"
            )
        
        metrics_service.reset_metrics()
        
        return {
            "status": "success",
            "message": "All metrics have been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset metrics: {e}"
        )


@metrics_router.get("/health")
async def metrics_health():
    """Check metrics service health"""
    try:
        metrics = metrics_service.get_metrics()
        
        return {
            "status": "healthy",
            "service": "metrics",
            "uptime": metrics["uptime"],
            "total_requests": metrics["requests_total"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Metrics health check failed: {e}"
        )


@metrics_router.get("/summary")
async def get_metrics_summary():
    """Get a summary of key metrics"""
    try:
        metrics = metrics_service.get_metrics()
        performance = metrics_service.get_performance_metrics()
        
        return {
            "summary": {
                "uptime_hours": metrics["uptime"] / 3600,
                "total_requests": metrics["requests_total"],
                "success_rate": (
                    metrics["requests_successful"] / metrics["requests_total"] * 100
                    if metrics["requests_total"] > 0 else 0
                ),
                "avg_response_time": metrics["average_response_time"],
                "tokens_generated": metrics["tokens_generated"],
                "cache_hit_rate": metrics["cache_hit_rate"],
                "p95_response_time": performance.get("response_time_p95", 0),
                "requests_per_minute": metrics["requests_per_minute"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics summary: {e}"
        )
