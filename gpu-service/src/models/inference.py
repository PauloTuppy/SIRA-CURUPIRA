"""
Inference Models for GPU Service
Pydantic models for inference requests and responses
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class GenerationOptions(BaseModel):
    """Options for text generation"""
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=40, ge=1, le=100)
    max_tokens: Optional[int] = Field(default=4096, ge=1, le=8192)
    stop_sequences: Optional[List[str]] = Field(default=None)
    seed: Optional[int] = Field(default=None)
    
    @validator("stop_sequences")
    def validate_stop_sequences(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError("Maximum 10 stop sequences allowed")
        return v


class InferenceRequest(BaseModel):
    """Single inference request"""
    prompt: str = Field(..., min_length=1, max_length=32000)
    system_prompt: Optional[str] = Field(default=None, max_length=8000)
    options: Optional[GenerationOptions] = Field(default_factory=GenerationOptions)
    stream: bool = Field(default=False)
    context_id: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator("prompt")
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()
    
    @validator("system_prompt")
    def validate_system_prompt(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v


class InferenceResponse(BaseModel):
    """Single inference response"""
    id: str = Field(..., description="Unique response ID")
    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used for generation")
    prompt_tokens: int = Field(..., ge=0, description="Number of prompt tokens")
    completion_tokens: int = Field(..., ge=0, description="Number of completion tokens")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    context_id: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator("total_tokens")
    def validate_total_tokens(cls, v, values):
        prompt_tokens = values.get("prompt_tokens", 0)
        completion_tokens = values.get("completion_tokens", 0)
        expected_total = prompt_tokens + completion_tokens
        if v != expected_total:
            raise ValueError(f"Total tokens ({v}) must equal prompt_tokens + completion_tokens ({expected_total})")
        return v


class BatchInferenceRequest(BaseModel):
    """Batch inference request"""
    requests: List[InferenceRequest] = Field(..., min_items=1, max_items=50)
    parallel: bool = Field(default=True, description="Process requests in parallel")
    fail_fast: bool = Field(default=False, description="Stop on first error")
    
    @validator("requests")
    def validate_requests(cls, v):
        if len(v) > 50:
            raise ValueError("Maximum 50 requests per batch")
        return v


class BatchInferenceResponse(BaseModel):
    """Batch inference response"""
    id: str = Field(..., description="Batch ID")
    responses: List[Union[InferenceResponse, Dict[str, str]]] = Field(...)
    total_requests: int = Field(..., ge=0)
    successful_requests: int = Field(..., ge=0)
    failed_requests: int = Field(..., ge=0)
    total_processing_time: float = Field(..., ge=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator("total_requests")
    def validate_total_requests(cls, v, values):
        responses = values.get("responses", [])
        if v != len(responses):
            raise ValueError("Total requests must match number of responses")
        return v
    
    @validator("successful_requests")
    def validate_successful_requests(cls, v, values):
        failed = values.get("failed_requests", 0)
        total = values.get("total_requests", 0)
        if v + failed != total:
            raise ValueError("Successful + failed requests must equal total requests")
        return v


class ModelInfo(BaseModel):
    """Information about a loaded model"""
    name: str = Field(..., description="Model name")
    size: str = Field(..., description="Model size (e.g., '9B', '27B')")
    family: str = Field(..., description="Model family (e.g., 'gemma2')")
    parameters: int = Field(..., ge=0, description="Number of parameters")
    quantization: Optional[str] = Field(default=None, description="Quantization method")
    context_length: int = Field(..., ge=0, description="Maximum context length")
    loaded: bool = Field(..., description="Whether model is loaded")
    memory_usage: Optional[float] = Field(default=None, ge=0.0, description="Memory usage in GB")
    load_time: Optional[float] = Field(default=None, ge=0.0, description="Load time in seconds")
    last_used: Optional[datetime] = Field(default=None, description="Last usage timestamp")


class StreamChunk(BaseModel):
    """Streaming response chunk"""
    id: str = Field(..., description="Response ID")
    text: str = Field(..., description="Text chunk")
    done: bool = Field(default=False, description="Whether generation is complete")
    context_id: Optional[str] = Field(default=None)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "resp_123",
                "text": "This is a chunk of generated text",
                "done": False,
                "context_id": "ctx_456"
            }
        }
