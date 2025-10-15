"""
Tests for configuration module
"""

import pytest
import os
from unittest.mock import patch

from src.config import Settings, settings, is_development, is_production


class TestSettings:
    """Test Settings class"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = Settings()
        
        assert config.app_name == "SIRA GPU Service"
        assert config.app_version == "1.0.0"
        assert config.environment == "development"
        assert config.debug is True
        assert config.host == "0.0.0.0"
        assert config.port == 8002
        assert config.workers == 1
        
        # OLLAMA defaults
        assert config.ollama_host == "http://localhost:11434"
        assert config.ollama_timeout == 300
        assert config.ollama_max_retries == 3
        
        # Model defaults
        assert config.model_name == "gemma2:9b"
        assert config.model_temperature == 0.7
        assert config.model_max_tokens == 4096
        assert config.model_top_p == 0.9
        assert config.model_top_k == 40
        
        # GPU defaults
        assert config.gpu_memory_fraction == 0.8
        assert config.gpu_device_id == 0
        assert config.enable_gpu_monitoring is True
        
        # Cache defaults
        assert config.enable_cache is True
        assert config.cache_ttl == 3600
        assert config.cache_max_size == 1000
        assert config.redis_url == "redis://localhost:6379/0"
    
    def test_environment_override(self):
        """Test environment variable override"""
        with patch.dict(os.environ, {
            'APP_NAME': 'Test Service',
            'PORT': '9000',
            'MODEL_TEMPERATURE': '0.5',
            'ENABLE_CACHE': 'false'
        }):
            config = Settings()
            
            assert config.app_name == "Test Service"
            assert config.port == 9000
            assert config.model_temperature == 0.5
            assert config.enable_cache is False
    
    def test_get_ollama_url(self):
        """Test OLLAMA URL generation"""
        config = Settings()
        
        # Test default
        assert config.get_ollama_url() == "http://localhost:11434"
        assert config.get_ollama_url("/api/tags") == "http://localhost:11434/api/tags"
        
        # Test with custom host
        config.ollama_host = "http://ollama:11434"
        assert config.get_ollama_url("/api/generate") == "http://ollama:11434/api/generate"
    
    def test_get_model_config(self):
        """Test model configuration generation"""
        config = Settings()
        model_config = config.get_model_config()
        
        expected = {
            "model": "gemma2:9b",
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 4096,
            }
        }
        
        assert model_config == expected
    
    def test_temperature_validator(self):
        """Test temperature validation"""
        # Valid temperatures
        config = Settings(model_temperature=0.0)
        assert config.model_temperature == 0.0
        
        config = Settings(model_temperature=1.0)
        assert config.model_temperature == 1.0
        
        config = Settings(model_temperature=0.7)
        assert config.model_temperature == 0.7
        
        # Invalid temperatures should raise validation error
        with pytest.raises(ValueError):
            Settings(model_temperature=-0.1)
        
        with pytest.raises(ValueError):
            Settings(model_temperature=1.1)
    
    def test_top_p_validator(self):
        """Test top_p validation"""
        # Valid values
        config = Settings(model_top_p=0.1)
        assert config.model_top_p == 0.1
        
        config = Settings(model_top_p=1.0)
        assert config.model_top_p == 1.0
        
        # Invalid values
        with pytest.raises(ValueError):
            Settings(model_top_p=0.0)
        
        with pytest.raises(ValueError):
            Settings(model_top_p=1.1)
    
    def test_gpu_memory_fraction_validator(self):
        """Test GPU memory fraction validation"""
        # Valid values
        config = Settings(gpu_memory_fraction=0.1)
        assert config.gpu_memory_fraction == 0.1
        
        config = Settings(gpu_memory_fraction=1.0)
        assert config.gpu_memory_fraction == 1.0
        
        # Invalid values
        with pytest.raises(ValueError):
            Settings(gpu_memory_fraction=0.0)
        
        with pytest.raises(ValueError):
            Settings(gpu_memory_fraction=1.1)


class TestEnvironmentHelpers:
    """Test environment helper functions"""
    
    def test_is_development(self):
        """Test development environment detection"""
        with patch.object(settings, 'environment', 'development'):
            assert is_development() is True
        
        with patch.object(settings, 'environment', 'production'):
            assert is_development() is False
        
        with patch.object(settings, 'environment', 'staging'):
            assert is_development() is False
    
    def test_is_production(self):
        """Test production environment detection"""
        with patch.object(settings, 'environment', 'production'):
            assert is_production() is True
        
        with patch.object(settings, 'environment', 'development'):
            assert is_production() is False
        
        with patch.object(settings, 'environment', 'staging'):
            assert is_production() is False


class TestGlobalSettings:
    """Test global settings instance"""
    
    def test_settings_instance(self):
        """Test that settings is a Settings instance"""
        assert isinstance(settings, Settings)
    
    def test_settings_consistency(self):
        """Test that settings values are consistent"""
        # Test that we can access all expected attributes
        assert hasattr(settings, 'app_name')
        assert hasattr(settings, 'ollama_host')
        assert hasattr(settings, 'model_name')
        assert hasattr(settings, 'enable_cache')
        
        # Test methods work
        assert callable(settings.get_ollama_url)
        assert callable(settings.get_model_config)
        
        # Test that methods return expected types
        assert isinstance(settings.get_ollama_url(), str)
        assert isinstance(settings.get_model_config(), dict)
