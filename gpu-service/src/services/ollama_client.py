"""
OLLAMA Client for GPU Service
HTTP client for communicating with OLLAMA API
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
import httpx
from datetime import datetime

from ..config import settings, get_ollama_url, get_model_config
from ..models.inference import InferenceRequest, InferenceResponse, StreamChunk
from ..utils.logger import logger, RequestLogger
from ..utils.model_utils import generate_response_id, calculate_tokens


class OllamaError(Exception):
    """OLLAMA API error"""
    pass


class OllamaClient:
    """HTTP client for OLLAMA API"""
    
    def __init__(self):
        self.base_url = settings.ollama_host
        self.timeout = settings.ollama_timeout
        self.max_retries = settings.ollama_max_retries
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Initialize HTTP client"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
            logger.info(f"Connected to OLLAMA at {self.base_url}")
    
    async def disconnect(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Disconnected from OLLAMA")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OLLAMA health"""
        try:
            if not self.client:
                await self.connect()
            
            start_time = datetime.utcnow()
            response = await self.client.get("/api/tags", timeout=10.0)
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "url": self.base_url
                }
            else:
                return {
                    "status": "unhealthy",
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}",
                    "url": self.base_url
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": self.base_url
            }
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        try:
            if not self.client:
                await self.connect()
            
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            logger.info(f"Retrieved {len(models)} models from OLLAMA")
            return models
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to list models: {e}")
            raise OllamaError(f"Failed to list models: {e}")
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull/download a model"""
        try:
            if not self.client:
                await self.connect()
            
            request_data = {"name": model_name}
            
            with RequestLogger(f"pull_{model_name}", "model_pull") as req_logger:
                response = await self.client.post(
                    "/api/pull",
                    json=request_data,
                    timeout=1800.0  # 30 minutes for model download
                )
                response.raise_for_status()
                
                req_logger.info(f"Successfully pulled model {model_name}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            raise OllamaError(f"Failed to pull model {model_name}: {e}")
    
    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        """Generate text completion"""
        try:
            if not self.client:
                await self.connect()
            
            # Prepare request data
            request_data = {
                "model": settings.model_name,
                "prompt": request.prompt,
                "stream": False,
                "options": get_model_config()["options"]
            }
            
            # Add system prompt if provided
            if request.system_prompt:
                request_data["system"] = request.system_prompt
            
            # Override with custom options
            if request.options:
                custom_options = {}
                if request.options.temperature is not None:
                    custom_options["temperature"] = request.options.temperature
                if request.options.top_p is not None:
                    custom_options["top_p"] = request.options.top_p
                if request.options.top_k is not None:
                    custom_options["top_k"] = request.options.top_k
                if request.options.max_tokens is not None:
                    custom_options["num_predict"] = request.options.max_tokens
                if request.options.stop_sequences:
                    custom_options["stop"] = request.options.stop_sequences
                if request.options.seed is not None:
                    custom_options["seed"] = request.options.seed
                
                request_data["options"].update(custom_options)
            
            # Make request
            start_time = datetime.utcnow()
            response = await self.client.post("/api/generate", json=request_data)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate tokens (approximation)
            prompt_tokens = calculate_tokens(request.prompt)
            completion_tokens = calculate_tokens(data.get("response", ""))
            
            # Create response
            inference_response = InferenceResponse(
                id=generate_response_id(),
                text=data.get("response", ""),
                model=settings.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                processing_time=processing_time,
                context_id=request.context_id,
                metadata={
                    "ollama_stats": {
                        "eval_count": data.get("eval_count", 0),
                        "eval_duration": data.get("eval_duration", 0),
                        "load_duration": data.get("load_duration", 0),
                        "prompt_eval_count": data.get("prompt_eval_count", 0),
                        "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                        "total_duration": data.get("total_duration", 0)
                    }
                }
            )
            
            logger.info(
                f"Generated response",
                model=settings.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                processing_time=processing_time
            )
            
            return inference_response
            
        except httpx.HTTPError as e:
            logger.error(f"OLLAMA generation failed: {e}")
            raise OllamaError(f"Generation failed: {e}")
    
    async def generate_stream(self, request: InferenceRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming text completion"""
        try:
            if not self.client:
                await self.connect()
            
            # Prepare request data
            request_data = {
                "model": settings.model_name,
                "prompt": request.prompt,
                "stream": True,
                "options": get_model_config()["options"]
            }
            
            # Add system prompt if provided
            if request.system_prompt:
                request_data["system"] = request.system_prompt
            
            # Override with custom options
            if request.options:
                custom_options = {}
                if request.options.temperature is not None:
                    custom_options["temperature"] = request.options.temperature
                if request.options.top_p is not None:
                    custom_options["top_p"] = request.options.top_p
                if request.options.top_k is not None:
                    custom_options["top_k"] = request.options.top_k
                if request.options.max_tokens is not None:
                    custom_options["num_predict"] = request.options.max_tokens
                if request.options.stop_sequences:
                    custom_options["stop"] = request.options.stop_sequences
                if request.options.seed is not None:
                    custom_options["seed"] = request.options.seed
                
                request_data["options"].update(custom_options)
            
            response_id = generate_response_id()
            
            # Make streaming request
            async with self.client.stream("POST", "/api/generate", json=request_data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            
                            chunk = StreamChunk(
                                id=response_id,
                                text=data.get("response", ""),
                                done=data.get("done", False),
                                context_id=request.context_id
                            )
                            
                            yield chunk
                            
                            if data.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse streaming response: {line}")
                            continue
            
        except httpx.HTTPError as e:
            logger.error(f"OLLAMA streaming failed: {e}")
            raise OllamaError(f"Streaming failed: {e}")
    
    async def show_model(self, model_name: str) -> Dict[str, Any]:
        """Get model information"""
        try:
            if not self.client:
                await self.connect()
            
            request_data = {"name": model_name}
            response = await self.client.post("/api/show", json=request_data)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            raise OllamaError(f"Failed to get model info: {e}")


# Global OLLAMA client instance
ollama_client = OllamaClient()
