"""
SIRA Backend Service - Main FastAPI Application
Sistema Inteligente de Recuperação Ambiental
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_client import make_asgi_app
import structlog

from .config import settings
from .api.v1 import analysis, history, health
from .api.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    AuthenticationMiddleware,
    MetricsMiddleware
)
from .utils.logging import setup_logging
from .utils.exceptions import SIRAException
from .services.coordinator import CoordinatorService


# Setup structured logging
setup_logging(settings.log_level, settings.log_format)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting SIRA Backend Service", version=settings.app_version)
    
    # Initialize services
    try:
        # Initialize coordinator service
        coordinator = CoordinatorService()
        await coordinator.initialize()
        app.state.coordinator = coordinator
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down SIRA Backend Service")
    
    # Cleanup services
    if hasattr(app.state, 'coordinator'):
        await app.state.coordinator.cleanup()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Sistema Inteligente de Recuperação Ambiental - Backend API",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.run.app", "localhost", "127.0.0.1"]
    )

# Add custom middlewares
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(MetricsMiddleware)

# Include API routers
app.include_router(
    analysis.router,
    prefix="/api/v1",
    tags=["analysis"]
)

app.include_router(
    history.router,
    prefix="/api/v1",
    tags=["history"]
)

app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["health"]
)

# Add Prometheus metrics endpoint
if settings.enable_monitoring:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Exception handlers
@app.exception_handler(SIRAException)
async def sira_exception_handler(request: Request, exc: SIRAException):
    """Handle custom SIRA exceptions"""
    logger.error(
        "SIRA exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": exc.timestamp.isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(
        "Request validation error",
        errors=exc.errors(),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dados de entrada inválidos",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        "Unexpected exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Erro interno do servidor" if not settings.debug else str(exc),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.debug else None,
        "api_version": "v1"
    }


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
        "version": settings.app_version
    }


# Ready check endpoint (for Kubernetes)
@app.get("/ready")
async def ready_check() -> Dict[str, Any]:
    """Readiness check endpoint"""
    # Check if all services are ready
    try:
        if hasattr(app.state, 'coordinator'):
            await app.state.coordinator.health_check()
        
        return {
            "status": "ready",
            "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
            "services": {
                "coordinator": "ready",
                "rag_service": "ready",
                "gpu_service": "ready"
            }
        }
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True
    )
