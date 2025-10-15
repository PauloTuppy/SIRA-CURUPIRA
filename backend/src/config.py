"""
Configuration settings for the SIRA Backend Service
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "SIRA Backend Service"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server
    host: str = Field(default="0.0.0.0", env="FASTAPI_HOST")
    port: int = Field(default=8000, env="FASTAPI_PORT")
    workers: int = Field(default=4, env="WORKERS")
    reload: bool = Field(default=True, env="HOT_RELOAD")
    
    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "https://*.web.app",
            "https://*.firebaseapp.com"
        ],
        env="CORS_ORIGINS"
    )
    
    # Google Cloud
    google_cloud_project: str = Field(env="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(
        default=None, 
        env="GOOGLE_APPLICATION_CREDENTIALS"
    )
    vertex_ai_location: str = Field(default="us-central1", env="VERTEX_AI_LOCATION")
    
    # API Keys
    gemini_api_key: str = Field(env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Firebase/Firestore
    firestore_database: str = Field(default="(default)", env="FIRESTORE_DATABASE")
    firebase_storage_bucket: str = Field(env="FIREBASE_STORAGE_BUCKET")
    
    # Collections
    analyses_collection: str = Field(
        default="analyses", 
        env="FIRESTORE_COLLECTION_ANALYSES"
    )
    knowledge_base_collection: str = Field(
        default="knowledge_base", 
        env="FIRESTORE_COLLECTION_KNOWLEDGE_BASE"
    )
    embeddings_collection: str = Field(
        default="embeddings", 
        env="FIRESTORE_COLLECTION_EMBEDDINGS"
    )
    
    # Service URLs
    rag_service_url: str = Field(env="RAG_SERVICE_URL")
    gpu_service_url: str = Field(env="GPU_SERVICE_URL")
    
    # Redis (for caching and session management)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_minutes: int = Field(default=15, env="RATE_LIMIT_WINDOW_MINUTES")
    
    # File Upload
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(
        default=[
            "image/jpeg",
            "image/png", 
            "image/webp",
            "video/mp4",
            "video/webm"
        ],
        env="ALLOWED_FILE_TYPES"
    )
    upload_timeout_seconds: int = Field(default=300, env="UPLOAD_TIMEOUT_SECONDS")
    
    # Logging
    log_level: str = Field(default="info", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Monitoring
    enable_monitoring: bool = Field(default=True, env="ENABLE_MONITORING")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Security
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Agent Configuration
    coordinator_model: str = Field(default="gemini-pro", env="COORDINATOR_MODEL")
    image_analysis_model: str = Field(default="gemini-pro-vision", env="IMAGE_ANALYSIS_MODEL")
    ecosystem_balance_model: str = Field(default="gemma2:9b", env="ECOSYSTEM_BALANCE_MODEL")
    recovery_plan_model: str = Field(default="gemini-pro", env="RECOVERY_PLAN_MODEL")
    
    # Analysis Configuration
    max_concurrent_analyses: int = Field(default=10, env="MAX_CONCURRENT_ANALYSES")
    analysis_timeout_seconds: int = Field(default=300, env="ANALYSIS_TIMEOUT_SECONDS")
    
    # RAG Configuration
    embedding_model: str = Field(default="text-embedding-004", env="EMBEDDING_MODEL")
    vector_dimension: int = Field(default=768, env="VECTOR_DIMENSION")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    max_retrieval_results: int = Field(default=10, env="MAX_RETRIEVAL_RESULTS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }
        
    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from string if needed"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types from string if needed"""
        if isinstance(self.allowed_file_types, str):
            return [file_type.strip() for file_type in self.allowed_file_types.split(",")]
        return self.allowed_file_types


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()


# Environment-specific configurations
class DevelopmentConfig(Settings):
    """Development environment configuration"""
    debug: bool = True
    log_level: str = "debug"
    reload: bool = True
    enable_cache: bool = False


class ProductionConfig(Settings):
    """Production environment configuration"""
    debug: bool = False
    log_level: str = "info"
    reload: bool = False
    enable_cache: bool = True
    workers: int = 8


class TestingConfig(Settings):
    """Testing environment configuration"""
    debug: bool = True
    log_level: str = "debug"
    enable_cache: bool = False
    firestore_database: str = "test"
    redis_url: str = "redis://localhost:6379/1"


def get_config_by_environment(env: str) -> Settings:
    """Get configuration based on environment"""
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = configs.get(env.lower(), Settings)
    return config_class()
