"""
Inference Endpoints for GPU Service
"""

from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

from ..config import settings
from ..models.inference import (
    InferenceRequest,
    InferenceResponse,
    BatchInferenceRequest,
    BatchInferenceResponse,
    StreamChunk
)
from ..models.responses import ErrorResponse
from ..services.inference_service import inference_service
from ..services.ollama_client import OllamaError
from ..utils.logger import logger, log_request
from ..utils.model_utils import generate_request_id

inference_router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


@inference_router.post("/generate", response_model=InferenceResponse)
async def generate_text(request: InferenceRequest, background_tasks: BackgroundTasks):
    """Generate text completion"""
    request_id = generate_request_id()
    
    try:
        # Set request ID if not provided
        if not request.context_id:
            request.context_id = request_id
        
        logger.info(f"Processing inference request {request_id}")
        
        # Generate response
        response = await inference_service.generate(request)
        
        # Log request in background
        background_tasks.add_task(
            log_request,
            method="POST",
            path="/api/v1/inference/generate",
            status_code=200,
            processing_time=response.processing_time,
            request_id=request_id
        )
        
        return response
        
    except OllamaError as e:
        logger.error(f"OLLAMA error for request {request_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="OllamaError",
                message=str(e),
                request_id=request_id
            ).dict()
        )
    
    except ValueError as e:
        logger.error(f"Validation error for request {request_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="ValidationError",
                message=str(e),
                request_id=request_id
            ).dict()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error for request {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="InternalError",
                message="An unexpected error occurred",
                request_id=request_id
            ).dict()
        )


@inference_router.post("/generate/stream")
async def generate_text_stream(request: InferenceRequest):
    """Generate streaming text completion"""
    request_id = generate_request_id()
    
    try:
        # Set request ID if not provided
        if not request.context_id:
            request.context_id = request_id
        
        # Force streaming mode
        request.stream = True
        
        logger.info(f"Processing streaming inference request {request_id}")
        
        async def stream_generator() -> AsyncGenerator[str, None]:
            try:
                async for chunk in inference_service.generate_stream(request):
                    # Format as Server-Sent Events
                    chunk_data = chunk.dict()
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    if chunk.done:
                        break
                        
                # Send final event
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_chunk = {
                    "error": type(e).__name__,
                    "message": str(e),
                    "request_id": request_id
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start streaming for request {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="StreamingError",
                message=str(e),
                request_id=request_id
            ).dict()
        )


@inference_router.post("/batch", response_model=BatchInferenceResponse)
async def batch_generate(batch_request: BatchInferenceRequest, background_tasks: BackgroundTasks):
    """Generate batch text completions"""
    batch_id = generate_request_id()
    
    try:
        logger.info(f"Processing batch inference request {batch_id} with {len(batch_request.requests)} requests")
        
        # Validate batch size
        if len(batch_request.requests) > 50:
            raise ValueError("Maximum 50 requests per batch")
        
        # Generate batch response
        response = await inference_service.batch_generate(batch_request)
        
        # Log request in background
        background_tasks.add_task(
            log_request,
            method="POST",
            path="/api/v1/inference/batch",
            status_code=200,
            processing_time=response.total_processing_time,
            request_id=batch_id
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error for batch {batch_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="ValidationError",
                message=str(e),
                request_id=batch_id
            ).dict()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error for batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="InternalError",
                message="An unexpected error occurred",
                request_id=batch_id
            ).dict()
        )


@inference_router.get("/status")
async def inference_status():
    """Get inference service status"""
    try:
        status = inference_service.get_status()
        
        from datetime import datetime
        return {
            "status": "healthy",
            "service": "inference",
            "details": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get inference status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get inference status: {e}"
        )


@inference_router.post("/warmup")
async def warmup_model():
    """Warm up the model with a simple request"""
    try:
        warmup_request = InferenceRequest(
            prompt="Hello, this is a warmup request.",
            options=None
        )
        
        logger.info("Warming up model")
        response = await inference_service.generate(warmup_request)
        
        return {
            "status": "success",
            "message": "Model warmed up successfully",
            "processing_time": response.processing_time,
            "model": settings.model_name
        }
        
    except Exception as e:
        logger.error(f"Model warmup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model warmup failed: {e}"
        )


@inference_router.get("/limits")
async def get_limits():
    """Get inference service limits and configuration"""
    return {
        "max_prompt_length": 32000,
        "max_completion_tokens": settings.model_max_tokens,
        "max_concurrent_requests": 10,
        "max_batch_size": 50,
        "timeout_seconds": settings.ollama_timeout,
        "cache_enabled": settings.enable_cache,
        "cache_ttl": settings.cache_ttl,
        "model_name": settings.model_name,
        "model_config": {
            "temperature": settings.model_temperature,
            "top_p": settings.model_top_p,
            "top_k": settings.model_top_k,
            "max_tokens": settings.model_max_tokens
        }
    }


@inference_router.post("/test")
async def test_inference():
    """Test inference with a simple prompt"""
    try:
        test_request = InferenceRequest(
            prompt="What is artificial intelligence?",
            options=None
        )
        
        response = await inference_service.generate(test_request)
        
        return {
            "status": "success",
            "test_prompt": test_request.prompt,
            "response_text": response.text[:200] + "..." if len(response.text) > 200 else response.text,
            "processing_time": response.processing_time,
            "tokens": {
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Inference test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Inference test failed: {e}"
        )
