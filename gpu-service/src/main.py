"""
SIRA GPU Service - Main Application
FastAPI application with OLLAMA integration for Gemma 3 inference
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings, is_development
from .api import health_router, inference_router, models_router, metrics_router
from .services.inference_service import inference_service
from .services.metrics_service import metrics_service
from .utils.logger import logger, setup_logging
from .utils.cache_utils import cache_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting SIRA GPU Service v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Model: {settings.model_name}")
    logger.info(f"OLLAMA Host: {settings.ollama_host}")
    
    try:
        # Initialize services
        await cache_manager.initialize()
        await inference_service.initialize()
        
        logger.info("SIRA GPU Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start SIRA GPU Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down SIRA GPU Service")
    
    try:
        await inference_service.shutdown()
        logger.info("SIRA GPU Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="SIRA GPU Service",
    description="Sistema Inteligente de Recuperação Ambiental - GPU Inference Service",
    version=settings.app_version,
    docs_url="/docs" if is_development() else None,
    redoc_url="/redoc" if is_development() else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = asyncio.get_event_loop().time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = asyncio.get_event_loop().time() - start_time
    
    # Log request
    logger.info(
        "HTTP request",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        processing_time=process_time,
        user_agent=request.headers.get("user-agent", ""),
        client_ip=request.client.host if request.client else "unknown"
    )
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        f"Unhandled exception: {exc}",
        path=str(request.url.path),
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An internal server error occurred",
            "path": str(request.url.path)
        }
    )


# Include routers
app.include_router(health_router)
app.include_router(inference_router)
app.include_router(models_router)
app.include_router(metrics_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "SIRA GPU Service",
        "version": settings.app_version,
        "description": "Sistema Inteligente de Recuperação Ambiental - GPU Inference Service",
        "model": settings.model_name,
        "environment": settings.environment,
        "docs_url": "/docs" if is_development() else None,
        "health_url": "/health",
        "inference_url": "/api/v1/inference",
        "models_url": "/api/v1/models",
        "metrics_url": "/api/v1/metrics"
    }


# Service info endpoint
@app.get("/info")
async def service_info():
    """Get detailed service information"""
    return {
        "service": {
            "name": "SIRA GPU Service",
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug
        },
        "configuration": {
            "model_name": settings.model_name,
            "ollama_host": settings.ollama_host,
            "cache_enabled": settings.enable_cache,
            "gpu_monitoring": settings.enable_gpu_monitoring,
            "max_concurrent_requests": 10,
            "timeout": settings.ollama_timeout
        },
        "endpoints": {
            "health": "/health",
            "inference": "/api/v1/inference",
            "models": "/api/v1/models", 
            "metrics": "/api/v1/metrics",
            "docs": "/docs" if is_development() else None
        },
        "features": {
            "streaming": True,
            "batch_processing": True,
            "caching": settings.enable_cache,
            "gpu_acceleration": True,
            "prometheus_metrics": True
        }
    }


# Development endpoints
if is_development():
    @app.get("/dev/config")
    async def dev_config():
        """Get current configuration (development only)"""
        return {
            "app": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug,
                "host": settings.host,
                "port": settings.port
            },
            "ollama": {
                "host": settings.ollama_host,
                "timeout": settings.ollama_timeout,
                "max_retries": settings.ollama_max_retries
            },
            "model": {
                "name": settings.model_name,
                "temperature": settings.model_temperature,
                "max_tokens": settings.model_max_tokens,
                "top_p": settings.model_top_p,
                "top_k": settings.model_top_k
            },
            "cache": {
                "enabled": settings.enable_cache,
                "ttl": settings.cache_ttl,
                "max_size": settings.cache_max_size,
                "redis_url": settings.redis_url
            },
            "cors": {
                "origins": settings.cors_origins
            }
        }
    
    @app.post("/dev/reset")
    async def dev_reset():
        """Reset service state (development only)"""
        try:
            # Reset metrics
            metrics_service.reset_metrics()
            
            # Clear cache
            await cache_manager.clear()
            
            return {
                "status": "success",
                "message": "Service state reset successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to reset service state: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reset service state: {e}"
            )


def create_app() -> FastAPI:
    """Factory function to create FastAPI app"""
    return app


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    # Run server
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers if not is_development() else 1,
        reload=settings.reload and is_development(),
        log_level=settings.log_level.lower(),
        access_log=True,
        server_header=False,
        date_header=False
    )


if __name__ == "__main__":
    main()
