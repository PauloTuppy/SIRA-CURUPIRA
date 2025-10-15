"""
Tests for health endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.models.responses import HealthStatus


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_basic_health(self, client):
        """Test basic health endpoint"""
        response = client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "uptime" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
    
    def test_liveness_check(self, client):
        """Test liveness endpoint"""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "uptime" in data
        assert "version" in data
    
    @patch('src.api.health.ollama_client')
    @patch('src.api.health.get_gpu_info')
    @patch('src.api.health.cache_manager')
    def test_readiness_check_healthy(self, mock_cache, mock_gpu, mock_ollama, client):
        """Test readiness check when all services are healthy"""
        # Mock OLLAMA as healthy
        mock_ollama.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock GPU as available
        mock_gpu_info = MagicMock()
        mock_gpu_info.available = True
        mock_gpu.return_value = mock_gpu_info
        
        # Mock cache as working
        mock_cache.set = AsyncMock()
        mock_cache.get = AsyncMock(return_value="test_value")
        mock_cache.delete = AsyncMock()
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["ollama"] == "healthy"
        assert data["services"]["gpu"] == "healthy"
        assert data["services"]["cache"] == "healthy"
    
    @patch('src.api.health.ollama_client')
    def test_readiness_check_ollama_unhealthy(self, mock_ollama, client):
        """Test readiness check when OLLAMA is unhealthy"""
        # Mock OLLAMA as unhealthy
        mock_ollama.health_check = AsyncMock(side_effect=Exception("Connection failed"))
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert "services" in data
        assert data["services"]["ollama"] == "unhealthy"
    
    @patch('src.api.health.get_gpu_info')
    def test_readiness_check_gpu_unavailable(self, mock_gpu, client):
        """Test readiness check when GPU is unavailable"""
        # Mock GPU as unavailable
        mock_gpu_info = MagicMock()
        mock_gpu_info.available = False
        mock_gpu.return_value = mock_gpu_info
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be degraded, not unhealthy
        assert data["status"] in ["degraded", "unhealthy"]
        assert "services" in data
        assert data["services"]["gpu"] == "degraded"
    
    @patch('src.api.health.ollama_client')
    @patch('src.api.health.get_gpu_info')
    @patch('src.api.health.monitor_gpu_usage')
    @patch('src.api.health.check_cuda_availability')
    @patch('src.api.health.metrics_service')
    def test_detailed_health(self, mock_metrics, mock_cuda, mock_gpu_usage, mock_gpu_info, mock_ollama, client):
        """Test detailed health endpoint"""
        # Mock OLLAMA
        mock_ollama.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock GPU info
        mock_gpu_info_obj = MagicMock()
        mock_gpu_info_obj.available = True
        mock_gpu_info_obj.device_count = 1
        mock_gpu_info_obj.driver_version = "525.60.11"
        mock_gpu_info_obj.cuda_version = "12.0"
        mock_gpu_info.return_value = mock_gpu_info_obj
        
        # Mock GPU usage
        mock_gpu_usage.return_value = {
            "utilization": 45.0,
            "memory_used": 2048,
            "temperature": 65
        }
        
        # Mock CUDA check
        mock_cuda.return_value = {"available": True, "version": "12.0"}
        
        # Mock metrics
        mock_metrics.get_system_metrics.return_value = {"cpu": 25.0, "memory": 60.0}
        mock_metrics.get_metrics.return_value = {
            "requests_total": 100,
            "success_rate": 95.0
        }
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "services" in data
        assert "system" in data
        assert "metrics" in data
        assert "configuration" in data
        
        # Check configuration section
        config = data["configuration"]
        assert "model_name" in config
        assert "ollama_host" in config
        assert "cache_enabled" in config
    
    @patch('src.api.health.get_gpu_info')
    @patch('src.api.health.monitor_gpu_usage')
    def test_gpu_status_available(self, mock_gpu_usage, mock_gpu_info, client):
        """Test GPU status when GPU is available"""
        # Mock GPU info
        mock_gpu_info_obj = MagicMock()
        mock_gpu_info_obj.available = True
        mock_gpu_info_obj.device_count = 1
        mock_gpu_info_obj.devices = [{
            "name": "NVIDIA L4",
            "memory_total": 24576,  # MB
            "memory_used": 8192,
            "memory_free": 16384
        }]
        mock_gpu_info_obj.driver_version = "525.60.11"
        mock_gpu_info_obj.cuda_version = "12.0"
        mock_gpu_info.return_value = mock_gpu_info_obj
        
        # Mock GPU usage
        mock_gpu_usage.return_value = {
            "utilization": 75.0,
            "temperature": 68.0
        }
        
        response = client.get("/health/gpu")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is True
        assert data["device_count"] == 1
        assert len(data["devices"]) == 1
        assert data["driver_version"] == "525.60.11"
        assert data["cuda_version"] == "12.0"
        assert data["total_memory"] == 24.0  # GB
        assert data["utilization"] == 75.0
        assert data["temperature"] == 68.0
    
    @patch('src.api.health.get_gpu_info')
    def test_gpu_status_unavailable(self, mock_gpu_info, client):
        """Test GPU status when GPU is unavailable"""
        # Mock GPU as unavailable
        mock_gpu_info_obj = MagicMock()
        mock_gpu_info_obj.available = False
        mock_gpu_info_obj.device_count = 0
        mock_gpu_info_obj.devices = []
        mock_gpu_info.return_value = mock_gpu_info_obj
        
        response = client.get("/health/gpu")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is False
        assert data["device_count"] == 0
        assert data["devices"] == []
    
    @patch('src.api.health.get_gpu_info')
    def test_gpu_status_error(self, mock_gpu_info, client):
        """Test GPU status when there's an error"""
        # Mock GPU info to raise exception
        mock_gpu_info.side_effect = Exception("GPU driver error")
        
        response = client.get("/health/gpu")
        
        assert response.status_code == 500
        data = response.json()
        
        assert "detail" in data
        assert "GPU driver error" in data["detail"]
    
    @patch('src.api.health.ollama_client')
    @patch('src.api.health.model_manager')
    def test_startup_check_ready(self, mock_model_manager, mock_ollama, client):
        """Test startup check when service is ready"""
        # Mock OLLAMA as healthy
        mock_ollama.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock model as loaded
        mock_model_info = MagicMock()
        mock_model_info.loaded = True
        mock_model_manager.get_model_info.return_value = mock_model_info
        
        response = client.get("/health/startup")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert "message" in data
        assert "model" in data
    
    @patch('src.api.health.ollama_client')
    @patch('src.api.health.model_manager')
    def test_startup_check_starting(self, mock_model_manager, mock_ollama, client):
        """Test startup check when service is still starting"""
        # Mock OLLAMA as healthy
        mock_ollama.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock model as not loaded
        mock_model_info = MagicMock()
        mock_model_info.loaded = False
        mock_model_manager.get_model_info.return_value = mock_model_info
        
        response = client.get("/health/startup")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "starting"
        assert "message" in data
    
    @patch('src.api.health.ollama_client')
    def test_startup_check_error(self, mock_ollama, client):
        """Test startup check when there's an error"""
        # Mock OLLAMA as failing
        mock_ollama.health_check = AsyncMock(side_effect=Exception("Connection failed"))
        
        response = client.get("/health/startup")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert "Connection failed" in data["message"]
