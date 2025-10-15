"""
Model Management Endpoints for GPU Service
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..config import settings
from ..models.responses import ModelStatusResponse, ListModelsResponse
from ..services.model_manager import model_manager
from ..services.ollama_client import OllamaError
from ..utils.logger import logger

models_router = APIRouter(prefix="/api/v1/models", tags=["models"])


class PullModelRequest(BaseModel):
    """Request to pull a model"""
    model_name: str
    force: bool = False


@models_router.get("/", response_model=ListModelsResponse)
async def list_models():
    """List all available models"""
    try:
        models = model_manager.list_models()
        loaded_count = sum(1 for model in models if model.get("loaded", False))
        
        return ListModelsResponse(
            models=models,
            total=len(models),
            loaded=loaded_count
        )
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {e}"
        )


@models_router.get("/{model_name}", response_model=ModelStatusResponse)
async def get_model_status(model_name: str):
    """Get status of a specific model"""
    try:
        status = model_manager.get_model_status(model_name)
        return status
        
    except Exception as e:
        logger.error(f"Failed to get model status for {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model status: {e}"
        )


@models_router.post("/pull")
async def pull_model(request: PullModelRequest, background_tasks: BackgroundTasks):
    """Pull/download a model"""
    try:
        logger.info(f"Pulling model {request.model_name}")
        
        # Check if model already exists
        if not request.force:
            models = model_manager.list_models()
            existing_model = next((m for m in models if m["name"] == request.model_name), None)
            
            if existing_model:
                return {
                    "status": "already_exists",
                    "message": f"Model {request.model_name} already exists",
                    "model": request.model_name
                }
        
        # Pull model in background
        background_tasks.add_task(
            _pull_model_background,
            request.model_name
        )
        
        return {
            "status": "started",
            "message": f"Started pulling model {request.model_name}",
            "model": request.model_name
        }
        
    except Exception as e:
        logger.error(f"Failed to start model pull for {request.model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start model pull: {e}"
        )


async def _pull_model_background(model_name: str):
    """Background task to pull model"""
    try:
        success = await model_manager.pull_model(model_name)
        if success:
            logger.info(f"Successfully pulled model {model_name}")
        else:
            logger.error(f"Failed to pull model {model_name}")
    except Exception as e:
        logger.error(f"Background model pull failed for {model_name}: {e}")


@models_router.post("/{model_name}/load")
async def load_model(model_name: str):
    """Load model information"""
    try:
        model_info = await model_manager.load_model_info(model_name)
        
        return {
            "status": "success",
            "message": f"Model {model_name} loaded successfully",
            "model": model_info.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model: {e}"
        )


@models_router.get("/{model_name}/stats")
async def get_model_stats(model_name: str):
    """Get detailed statistics for a model"""
    try:
        stats = model_manager.get_model_stats(model_name)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No statistics found for model {model_name}"
            )
        
        return {
            "model": model_name,
            "requests_processed": stats.requests_processed,
            "total_tokens_generated": stats.total_tokens_generated,
            "total_processing_time": stats.total_processing_time,
            "average_processing_time": stats.average_processing_time,
            "tokens_per_second": stats.tokens_per_second,
            "last_used": stats.last_used.isoformat() if stats.last_used else None,
            "load_time": stats.load_time,
            "memory_usage": stats.memory_usage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model stats for {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model stats: {e}"
        )


@models_router.post("/refresh")
async def refresh_models():
    """Refresh the list of available models"""
    try:
        await model_manager.refresh_available_models()
        
        models = model_manager.list_models()
        
        return {
            "status": "success",
            "message": "Model list refreshed successfully",
            "total_models": len(models),
            "loaded_models": sum(1 for model in models if model.get("loaded", False))
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh models: {e}"
        )


@models_router.get("/current/info")
async def get_current_model_info():
    """Get information about the currently configured model"""
    try:
        current_model = settings.model_name
        model_info = model_manager.get_model_info(current_model)
        
        if not model_info:
            # Try to load model info
            try:
                model_info = await model_manager.load_model_info(current_model)
            except Exception as e:
                return {
                    "model": current_model,
                    "status": "not_loaded",
                    "error": str(e)
                }
        
        return {
            "model": current_model,
            "status": "loaded" if model_info.loaded else "not_loaded",
            "info": model_info.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get current model info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current model info: {e}"
        )


@models_router.get("/summary/stats")
async def get_models_summary():
    """Get summary statistics for all models"""
    try:
        summary = model_manager.get_summary_stats()
        
        return {
            "status": "success",
            "summary": summary,
            "current_model": settings.model_name
        }
        
    except Exception as e:
        logger.error(f"Failed to get models summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get models summary: {e}"
        )


@models_router.post("/cleanup")
async def cleanup_unused_models(max_idle_hours: int = 1):
    """Cleanup models that haven't been used recently"""
    try:
        max_idle_seconds = max_idle_hours * 3600
        await model_manager.cleanup_unused_models(max_idle_seconds)
        
        return {
            "status": "success",
            "message": f"Cleaned up models unused for more than {max_idle_hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup models: {e}"
        )


@models_router.get("/available/families")
async def get_model_families():
    """Get available model families"""
    try:
        models = model_manager.list_models()
        
        families = {}
        for model in models:
            name = model.get("name", "")
            if ":" in name:
                family, size = name.split(":", 1)
                if family not in families:
                    families[family] = []
                families[family].append({
                    "size": size,
                    "name": name,
                    "loaded": model.get("loaded", False)
                })
        
        return {
            "families": families,
            "total_families": len(families),
            "total_models": len(models)
        }
        
    except Exception as e:
        logger.error(f"Failed to get model families: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model families: {e}"
        )
