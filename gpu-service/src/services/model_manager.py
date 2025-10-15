"""
Model Manager for GPU Service
Manages model loading, unloading, and status tracking
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..config import settings
from ..models.inference import ModelInfo
from ..models.responses import ModelStatusResponse, ServiceStatus
from ..utils.logger import logger, log_model_operation
from ..utils.model_utils import get_model_info_from_name, parse_model_name
from .ollama_client import ollama_client, OllamaError


@dataclass
class ModelStats:
    """Model usage statistics"""
    requests_processed: int = 0
    total_tokens_generated: int = 0
    total_processing_time: float = 0.0
    last_used: Optional[datetime] = None
    load_time: Optional[float] = None
    memory_usage: Optional[float] = None
    
    @property
    def average_processing_time(self) -> float:
        """Calculate average processing time per request"""
        if self.requests_processed == 0:
            return 0.0
        return self.total_processing_time / self.requests_processed
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens generated per second"""
        if self.total_processing_time == 0:
            return 0.0
        return self.total_tokens_generated / self.total_processing_time


class ModelManager:
    """Manages model lifecycle and statistics"""
    
    def __init__(self):
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.model_stats: Dict[str, ModelStats] = {}
        self.available_models: List[Dict[str, Any]] = []
        self.last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize model manager"""
        logger.info("Initializing Model Manager")
        
        try:
            # Connect to OLLAMA
            await ollama_client.connect()
            
            # Refresh available models
            await self.refresh_available_models()
            
            # Check if default model is available
            await self.ensure_default_model()
            
            logger.info("Model Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Model Manager: {e}")
            raise
    
    async def refresh_available_models(self):
        """Refresh list of available models from OLLAMA"""
        try:
            models = await ollama_client.list_models()
            self.available_models = models
            self.last_refresh = datetime.utcnow()
            
            # Update loaded models status
            for model_data in models:
                model_name = model_data.get("name", "")
                if model_name in self.loaded_models:
                    self.loaded_models[model_name].loaded = True
                    self.loaded_models[model_name].last_used = datetime.utcnow()
                    
                    # Update memory usage if available
                    if "size" in model_data:
                        size_bytes = model_data["size"]
                        size_gb = size_bytes / (1024 ** 3)
                        self.loaded_models[model_name].memory_usage = size_gb
            
            logger.info(f"Refreshed {len(models)} available models")
            
        except OllamaError as e:
            logger.error(f"Failed to refresh models: {e}")
            raise
    
    async def ensure_default_model(self):
        """Ensure default model is available"""
        default_model = settings.model_name
        
        # Check if model is in available models
        model_names = [model.get("name", "") for model in self.available_models]
        
        if default_model not in model_names:
            logger.info(f"Default model {default_model} not found, attempting to pull")
            
            try:
                await self.pull_model(default_model)
                await self.refresh_available_models()
            except Exception as e:
                logger.error(f"Failed to pull default model {default_model}: {e}")
                raise
        
        # Load model info
        await self.load_model_info(default_model)
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull/download a model"""
        async with self._lock:
            try:
                start_time = datetime.utcnow()
                
                log_model_operation("pull_start", model_name)
                success = await ollama_client.pull_model(model_name)
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                log_model_operation("pull_complete", model_name, duration=duration, success=success)
                
                if success:
                    await self.refresh_available_models()
                
                return success
                
            except Exception as e:
                log_model_operation("pull_failed", model_name, success=False)
                logger.error(f"Failed to pull model {model_name}: {e}")
                return False
    
    async def load_model_info(self, model_name: str) -> ModelInfo:
        """Load detailed model information"""
        try:
            # Get model info from OLLAMA
            try:
                model_data = await ollama_client.show_model(model_name)
            except Exception:
                # Fallback to basic info if show_model fails
                model_data = {"details": {}}
            
            # Parse model name
            parsed = parse_model_name(model_name)
            
            # Create ModelInfo
            model_info = ModelInfo(
                name=model_name,
                size=parsed["size"].upper(),
                family=parsed["family"],
                parameters=model_data.get("details", {}).get("parameter_count", 0),
                quantization=model_data.get("details", {}).get("quantization_level"),
                context_length=model_data.get("details", {}).get("context_length", 4096),
                loaded=True,
                memory_usage=None,  # Will be updated when we get actual usage
                load_time=None,
                last_used=datetime.utcnow()
            )
            
            self.loaded_models[model_name] = model_info
            
            # Initialize stats if not exists
            if model_name not in self.model_stats:
                self.model_stats[model_name] = ModelStats()
            
            logger.info(f"Loaded model info for {model_name}")
            return model_info
            
        except Exception as e:
            logger.error(f"Failed to load model info for {model_name}: {e}")
            raise
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get model information"""
        return self.loaded_models.get(model_name)
    
    def get_model_stats(self, model_name: str) -> Optional[ModelStats]:
        """Get model statistics"""
        return self.model_stats.get(model_name)
    
    def update_model_stats(
        self,
        model_name: str,
        tokens_generated: int,
        processing_time: float
    ):
        """Update model usage statistics"""
        if model_name not in self.model_stats:
            self.model_stats[model_name] = ModelStats()
        
        stats = self.model_stats[model_name]
        stats.requests_processed += 1
        stats.total_tokens_generated += tokens_generated
        stats.total_processing_time += processing_time
        stats.last_used = datetime.utcnow()
        
        # Update model info last used
        if model_name in self.loaded_models:
            self.loaded_models[model_name].last_used = datetime.utcnow()
    
    def get_model_status(self, model_name: str) -> ModelStatusResponse:
        """Get model status response"""
        model_info = self.loaded_models.get(model_name)
        stats = self.model_stats.get(model_name, ModelStats())
        
        if model_info:
            status = ServiceStatus.RUNNING if model_info.loaded else ServiceStatus.STOPPED
        else:
            status = ServiceStatus.STOPPED
        
        return ModelStatusResponse(
            name=model_name,
            status=status,
            loaded=model_info.loaded if model_info else False,
            memory_usage=model_info.memory_usage if model_info else None,
            load_time=model_info.load_time if model_info else None,
            last_used=stats.last_used,
            requests_processed=stats.requests_processed,
            average_inference_time=stats.average_processing_time
        )
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with status"""
        models = []
        
        for model_data in self.available_models:
            model_name = model_data.get("name", "")
            model_info = self.loaded_models.get(model_name)
            stats = self.model_stats.get(model_name, ModelStats())
            
            models.append({
                "name": model_name,
                "size": model_data.get("size", 0),
                "modified_at": model_data.get("modified_at"),
                "loaded": model_info.loaded if model_info else False,
                "memory_usage": model_info.memory_usage if model_info else None,
                "requests_processed": stats.requests_processed,
                "last_used": stats.last_used.isoformat() if stats.last_used else None
            })
        
        return models
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for all models"""
        total_requests = sum(stats.requests_processed for stats in self.model_stats.values())
        total_tokens = sum(stats.total_tokens_generated for stats in self.model_stats.values())
        total_time = sum(stats.total_processing_time for stats in self.model_stats.values())
        
        loaded_count = sum(1 for model in self.loaded_models.values() if model.loaded)
        
        return {
            "total_models": len(self.available_models),
            "loaded_models": loaded_count,
            "total_requests": total_requests,
            "total_tokens_generated": total_tokens,
            "total_processing_time": total_time,
            "average_tokens_per_second": total_tokens / total_time if total_time > 0 else 0,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
        }
    
    async def cleanup_unused_models(self, max_idle_time: int = 3600):
        """Cleanup models that haven't been used recently"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=max_idle_time)
        
        models_to_remove = []
        for model_name, model_info in self.loaded_models.items():
            if model_info.last_used and model_info.last_used < cutoff_time:
                models_to_remove.append(model_name)
        
        for model_name in models_to_remove:
            logger.info(f"Cleaning up unused model: {model_name}")
            self.loaded_models.pop(model_name, None)
            # Note: We keep stats for historical purposes
    
    async def shutdown(self):
        """Shutdown model manager"""
        logger.info("Shutting down Model Manager")
        
        # Disconnect from OLLAMA
        await ollama_client.disconnect()
        
        # Clear loaded models
        self.loaded_models.clear()
        
        logger.info("Model Manager shutdown complete")


# Global model manager instance
model_manager = ModelManager()
