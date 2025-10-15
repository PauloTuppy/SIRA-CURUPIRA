"""
SIRA GPU Service Configuration
Environment-based configuration for GPU inference service
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = Field(default="SIRA GPU Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8002, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    reload: bool = Field(default=False, env="RELOAD")
    
    # OLLAMA Configuration
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    ollama_timeout: int = Field(default=300, env="OLLAMA_TIMEOUT")  # 5 minutes
    ollama_max_retries: int = Field(default=3, env="OLLAMA_MAX_RETRIES")
    
    # Model Configuration
    model_name: str = Field(default="gemma2:9b", env="MODEL_NAME")
    model_temperature: float = Field(default=0.7, env="MODEL_TEMPERATURE")
    model_max_tokens: int = Field(default=4096, env="MODEL_MAX_TOKENS")
    model_top_p: float = Field(default=0.9, env="MODEL_TOP_P")
    model_top_k: int = Field(default=40, env="MODEL_TOP_K")
    
    # GPU Configuration
    gpu_memory_fraction: float = Field(default=0.8, env="GPU_MEMORY_FRACTION")
    gpu_device_id: int = Field(default=0, env="GPU_DEVICE_ID")
    enable_gpu_monitoring: bool = Field(default=True, env="ENABLE_GPU_MONITORING")
    
    # Cache Configuration
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://localhost:8001"
        ],
        env="CORS_ORIGINS"
    )
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8003, env="METRICS_PORT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Health Check
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        if v.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("Invalid log level")
        return v.upper()

    @field_validator("model_temperature")
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @field_validator("model_top_p")
    @classmethod
    def validate_top_p(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Top-p must be between 0.0 and 1.0")
        return v

    @field_validator("gpu_memory_fraction")
    @classmethod
    def validate_gpu_memory_fraction(cls, v):
        if not 0.1 <= v <= 1.0:
            raise ValueError("GPU memory fraction must be between 0.1 and 1.0")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Environment-specific configurations
def is_development() -> bool:
    """Check if running in development mode"""
    return settings.environment == "development"


def is_production() -> bool:
    """Check if running in production mode"""
    return settings.environment == "production"


def get_ollama_url(endpoint: str = "") -> str:
    """Get full OLLAMA API URL"""
    base_url = settings.ollama_host.rstrip("/")
    if endpoint:
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}"
    return base_url


def get_model_config() -> dict:
    """Get model configuration for OLLAMA"""
    return {
        "model": settings.model_name,
        "options": {
            "temperature": settings.model_temperature,
            "top_p": settings.model_top_p,
            "top_k": settings.model_top_k,
            "num_predict": settings.model_max_tokens,
        }
    }
