"""
Inference Service for GPU Service
Main service for handling inference requests with caching and batching
"""

import asyncio
from typing import List, Optional, AsyncGenerator
from datetime import datetime

from ..config import settings
from ..models.inference import (
    InferenceRequest,
    InferenceResponse,
    BatchInferenceRequest,
    BatchInferenceResponse,
    StreamChunk
)
from ..utils.logger import logger, log_inference, RequestLogger
from ..utils.model_utils import generate_batch_id, clean_text, truncate_text
from ..utils.cache_utils import cache_manager, get_cache_key
from .ollama_client import ollama_client, OllamaError
from .model_manager import model_manager
from .metrics_service import metrics_service


class InferenceService:
    """Main inference service with caching and batching support"""
    
    def __init__(self):
        self.processing_requests = 0
        self.max_concurrent_requests = 10
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
    
    async def initialize(self):
        """Initialize inference service"""
        logger.info("Initializing Inference Service")
        
        try:
            # Initialize cache manager
            await cache_manager.initialize()
            
            # Initialize model manager
            await model_manager.initialize()
            
            logger.info("Inference Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Inference Service: {e}")
            raise
    
    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        """Generate text completion with caching"""
        async with self._semaphore:
            self.processing_requests += 1
            
            try:
                # Clean and validate input
                request.prompt = clean_text(request.prompt)
                if request.system_prompt:
                    request.system_prompt = clean_text(request.system_prompt)
                
                # Truncate if too long
                if len(request.prompt) > 32000:
                    request.prompt = truncate_text(request.prompt, 32000)
                    logger.warning("Prompt truncated to 32000 characters")
                
                # Check cache if enabled
                cache_key = None
                if settings.enable_cache and not request.stream:
                    cache_key = get_cache_key(
                        request.prompt,
                        settings.model_name,
                        request.options.dict() if request.options else {}
                    )
                    
                    cached_response = await cache_manager.get(cache_key)
                    if cached_response:
                        logger.info("Cache hit for inference request")
                        metrics_service.record_cache_hit()
                        
                        # Update response timestamp
                        cached_response["created_at"] = datetime.utcnow().isoformat()
                        return InferenceResponse(**cached_response)
                
                # Generate response
                with RequestLogger(request.context_id or "unknown", "inference") as req_logger:
                    start_time = datetime.utcnow()
                    
                    response = await ollama_client.generate(request)
                    
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    # Update model statistics
                    model_manager.update_model_stats(
                        settings.model_name,
                        response.completion_tokens,
                        processing_time
                    )
                    
                    # Record metrics
                    metrics_service.record_request(
                        model=settings.model_name,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        processing_time=processing_time,
                        cached=False
                    )
                    
                    # Cache response if enabled
                    if settings.enable_cache and cache_key:
                        await cache_manager.set(
                            cache_key,
                            response.dict(),
                            ttl=settings.cache_ttl
                        )
                    
                    # Log inference
                    log_inference(
                        model=settings.model_name,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        processing_time=processing_time,
                        request_id=response.id,
                        cached=False
                    )
                    
                    return response
            
            except OllamaError as e:
                logger.error(f"OLLAMA error during inference: {e}")
                metrics_service.record_error("ollama_error")
                raise
            
            except Exception as e:
                logger.error(f"Unexpected error during inference: {e}")
                metrics_service.record_error("inference_error")
                raise
            
            finally:
                self.processing_requests -= 1
    
    async def generate_stream(self, request: InferenceRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming text completion"""
        async with self._semaphore:
            self.processing_requests += 1
            
            try:
                # Clean and validate input
                request.prompt = clean_text(request.prompt)
                if request.system_prompt:
                    request.system_prompt = clean_text(request.system_prompt)
                
                # Truncate if too long
                if len(request.prompt) > 32000:
                    request.prompt = truncate_text(request.prompt, 32000)
                    logger.warning("Prompt truncated to 32000 characters")
                
                start_time = datetime.utcnow()
                total_tokens = 0
                
                async for chunk in ollama_client.generate_stream(request):
                    total_tokens += len(chunk.text.split())  # Rough token count
                    yield chunk
                    
                    if chunk.done:
                        processing_time = (datetime.utcnow() - start_time).total_seconds()
                        
                        # Update model statistics (approximate)
                        prompt_tokens = len(request.prompt.split())
                        completion_tokens = total_tokens
                        
                        model_manager.update_model_stats(
                            settings.model_name,
                            completion_tokens,
                            processing_time
                        )
                        
                        # Record metrics
                        metrics_service.record_request(
                            model=settings.model_name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            processing_time=processing_time,
                            cached=False
                        )
                        
                        # Log inference
                        log_inference(
                            model=settings.model_name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            processing_time=processing_time,
                            request_id=chunk.id,
                            cached=False
                        )
                        
                        break
            
            except OllamaError as e:
                logger.error(f"OLLAMA error during streaming: {e}")
                metrics_service.record_error("ollama_stream_error")
                raise
            
            except Exception as e:
                logger.error(f"Unexpected error during streaming: {e}")
                metrics_service.record_error("stream_error")
                raise
            
            finally:
                self.processing_requests -= 1
    
    async def batch_generate(self, batch_request: BatchInferenceRequest) -> BatchInferenceResponse:
        """Generate batch completions"""
        batch_id = generate_batch_id()
        start_time = datetime.utcnow()
        
        logger.info(f"Processing batch {batch_id} with {len(batch_request.requests)} requests")
        
        responses = []
        successful = 0
        failed = 0
        
        if batch_request.parallel:
            # Process requests in parallel
            tasks = []
            for request in batch_request.requests:
                task = asyncio.create_task(self._process_batch_request(request, batch_request.fail_fast))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    responses.append({
                        "error": type(result).__name__,
                        "message": str(result)
                    })
                    
                    if batch_request.fail_fast:
                        break
                else:
                    successful += 1
                    responses.append(result)
        else:
            # Process requests sequentially
            for request in batch_request.requests:
                try:
                    response = await self._process_batch_request(request, batch_request.fail_fast)
                    responses.append(response)
                    successful += 1
                    
                except Exception as e:
                    failed += 1
                    responses.append({
                        "error": type(e).__name__,
                        "message": str(e)
                    })
                    
                    if batch_request.fail_fast:
                        break
        
        total_processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        batch_response = BatchInferenceResponse(
            id=batch_id,
            responses=responses,
            total_requests=len(batch_request.requests),
            successful_requests=successful,
            failed_requests=failed,
            total_processing_time=total_processing_time
        )
        
        logger.info(
            f"Batch {batch_id} completed",
            total_requests=len(batch_request.requests),
            successful=successful,
            failed=failed,
            processing_time=total_processing_time
        )
        
        return batch_response
    
    async def _process_batch_request(self, request: InferenceRequest, fail_fast: bool) -> InferenceResponse:
        """Process single request in batch"""
        try:
            return await self.generate(request)
        except Exception as e:
            if fail_fast:
                raise
            logger.error(f"Batch request failed: {e}")
            raise
    
    def get_status(self) -> dict:
        """Get inference service status"""
        return {
            "processing_requests": self.processing_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
            "cache_enabled": settings.enable_cache,
            "model_name": settings.model_name,
            "ollama_host": settings.ollama_host
        }
    
    async def shutdown(self):
        """Shutdown inference service"""
        logger.info("Shutting down Inference Service")
        
        # Wait for ongoing requests to complete
        while self.processing_requests > 0:
            logger.info(f"Waiting for {self.processing_requests} requests to complete")
            await asyncio.sleep(1)
        
        # Shutdown model manager
        await model_manager.shutdown()
        
        logger.info("Inference Service shutdown complete")


# Global inference service instance
inference_service = InferenceService()
