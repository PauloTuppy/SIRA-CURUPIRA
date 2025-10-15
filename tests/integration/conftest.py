"""
Pytest configuration for integration tests
"""

import pytest
import asyncio
import httpx
import time
import os
from typing import Dict, Any, AsyncGenerator

# Test configuration
TEST_TIMEOUT = 30.0
INTEGRATION_TEST_ENV = os.getenv("INTEGRATION_TEST_ENV", "development")

# Service URLs
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
GPU_SERVICE_URL = os.getenv("GPU_SERVICE_URL", "http://localhost:8002")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def services_health_check():
    """Check that all services are healthy before running tests"""
    print("\n🏥 Checking service health before running integration tests...")
    
    services = [
        ("Backend", BACKEND_URL),
        ("RAG Service", RAG_SERVICE_URL),
        ("GPU Service", GPU_SERVICE_URL)
    ]
    
    healthy_services = []
    unhealthy_services = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for service_name, base_url in services:
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get("status") == "healthy":
                        healthy_services.append(service_name)
                        print(f"✅ {service_name} is healthy")
                    else:
                        unhealthy_services.append(service_name)
                        print(f"⚠️ {service_name} is not healthy: {health_data}")
                else:
                    unhealthy_services.append(service_name)
                    print(f"❌ {service_name} health check failed: HTTP {response.status_code}")
            except Exception as e:
                unhealthy_services.append(service_name)
                print(f"❌ {service_name} is unreachable: {e}")
    
    if unhealthy_services:
        print(f"\n⚠️ Warning: {len(unhealthy_services)} services are not healthy: {unhealthy_services}")
        print("Some integration tests may fail or be skipped.")
    
    return {
        "healthy": healthy_services,
        "unhealthy": unhealthy_services,
        "all_healthy": len(unhealthy_services) == 0
    }


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client for making API requests"""
    async with httpx.AsyncClient(
        timeout=TEST_TIMEOUT,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


@pytest.fixture
def sample_location() -> Dict[str, Any]:
    """Sample location data for tests"""
    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "address": "São Paulo, SP, Brazil"
    }


@pytest.fixture
def sample_analysis_request(sample_location) -> Dict[str, Any]:
    """Sample analysis request for tests"""
    return {
        "location": sample_location,
        "analysis_type": "comprehensive",
        "include_biodiversity": True,
        "include_recovery_plan": True,
        "user_context": {
            "organization": "Test Organization",
            "project_type": "urban_restoration"
        }
    }


@pytest.fixture
def sample_search_query() -> Dict[str, Any]:
    """Sample search query for RAG service tests"""
    return {
        "query": "Atlantic Forest biodiversity conservation",
        "limit": 5,
        "include_metadata": True
    }


@pytest.fixture
def sample_inference_request() -> Dict[str, Any]:
    """Sample inference request for GPU service tests"""
    return {
        "prompt": "Analyze the biodiversity of the Atlantic Forest biome in Brazil and suggest conservation strategies.",
        "max_tokens": 500,
        "temperature": 0.7,
        "system_prompt": "You are an environmental expert specializing in Brazilian ecosystems."
    }


@pytest.fixture
async def wait_for_service_ready():
    """Wait for services to be ready for testing"""
    async def _wait_for_ready(service_url: str, endpoint: str = "/health/ready", max_wait: int = 60):
        """Wait for a specific service to be ready"""
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            while time.time() - start_time < max_wait:
                try:
                    response = await client.get(f"{service_url}{endpoint}")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            return True
                except Exception:
                    pass
                
                await asyncio.sleep(2)
        
        return False
    
    return _wait_for_ready


@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests"""
    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}
        
        def start_timer(self, operation: str):
            self.metrics[operation] = {"start": time.time()}
        
        def end_timer(self, operation: str):
            if operation in self.metrics:
                self.metrics[operation]["end"] = time.time()
                self.metrics[operation]["duration"] = (
                    self.metrics[operation]["end"] - self.metrics[operation]["start"]
                )
        
        def get_duration(self, operation: str) -> float:
            return self.metrics.get(operation, {}).get("duration", 0.0)
        
        def get_summary(self) -> Dict[str, float]:
            return {
                op: data.get("duration", 0.0) 
                for op, data in self.metrics.items()
            }
    
    return PerformanceTracker()


@pytest.fixture
def test_data_cleanup():
    """Clean up test data after tests"""
    created_resources = []
    
    def add_resource(resource_type: str, resource_id: str):
        created_resources.append((resource_type, resource_id))
    
    yield add_resource
    
    # Cleanup after test
    print(f"\n🧹 Cleaning up {len(created_resources)} test resources...")
    for resource_type, resource_id in created_resources:
        print(f"  └─ Cleaning {resource_type}: {resource_id}")
        # Add actual cleanup logic here if needed


def pytest_configure(config):
    """Configure pytest for integration tests"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_gpu: mark test as requiring GPU service"
    )
    config.addinivalue_line(
        "markers", "requires_rag: mark test as requiring RAG service"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add integration marker to all tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to tests that might take longer
        if any(keyword in item.name.lower() for keyword in ["e2e", "workflow", "complete"]):
            item.add_marker(pytest.mark.slow)
        
        # Add service-specific markers
        if any(keyword in item.name.lower() for keyword in ["gpu", "inference", "ollama"]):
            item.add_marker(pytest.mark.requires_gpu)
        
        if any(keyword in item.name.lower() for keyword in ["rag", "search", "knowledge"]):
            item.add_marker(pytest.mark.requires_rag)


@pytest.fixture(autouse=True)
def test_environment_info():
    """Print test environment information"""
    print(f"\n🌍 Test Environment: {INTEGRATION_TEST_ENV}")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print(f"🔗 RAG Service URL: {RAG_SERVICE_URL}")
    print(f"🔗 GPU Service URL: {GPU_SERVICE_URL}")


# Skip tests if services are not available
def pytest_runtest_setup(item):
    """Setup for each test run"""
    # Skip GPU tests if GPU service is not available
    if item.get_closest_marker("requires_gpu"):
        try:
            import httpx
            response = httpx.get(f"{GPU_SERVICE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("GPU service not available")
        except Exception:
            pytest.skip("GPU service not reachable")
    
    # Skip RAG tests if RAG service is not available
    if item.get_closest_marker("requires_rag"):
        try:
            import httpx
            response = httpx.get(f"{RAG_SERVICE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("RAG service not available")
        except Exception:
            pytest.skip("RAG service not reachable")
