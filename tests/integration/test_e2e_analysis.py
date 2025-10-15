"""
End-to-End Integration Tests for SIRA System
Tests complete analysis workflow: Backend -> RAG Service -> GPU Service
"""

import pytest
import asyncio
import httpx
import json
import time
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock

# Test configuration
BACKEND_URL = "http://localhost:8000"
RAG_SERVICE_URL = "http://localhost:8001"
GPU_SERVICE_URL = "http://localhost:8002"

# Test timeout settings
REQUEST_TIMEOUT = 30.0
ANALYSIS_TIMEOUT = 120.0


class TestE2EAnalysis:
    """End-to-end analysis workflow tests"""
    
    @pytest.fixture
    async def http_client(self):
        """HTTP client for API calls"""
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            yield client
    
    @pytest.fixture
    def sample_analysis_request(self) -> Dict[str, Any]:
        """Sample analysis request payload"""
        return {
            "location": {
                "latitude": -23.5505,
                "longitude": -46.6333,
                "address": "São Paulo, SP, Brazil"
            },
            "analysis_type": "comprehensive",
            "include_biodiversity": True,
            "include_recovery_plan": True,
            "user_context": {
                "organization": "Test Organization",
                "project_type": "urban_restoration"
            }
        }
    
    async def test_health_checks_all_services(self, http_client):
        """Test that all services are healthy before running tests"""
        services = [
            ("Backend", f"{BACKEND_URL}/health"),
            ("RAG Service", f"{RAG_SERVICE_URL}/health"),
            ("GPU Service", f"{GPU_SERVICE_URL}/health")
        ]
        
        for service_name, health_url in services:
            try:
                response = await http_client.get(health_url)
                assert response.status_code == 200, f"{service_name} health check failed"
                
                health_data = response.json()
                assert health_data.get("status") == "healthy", f"{service_name} is not healthy"
                
                print(f"✅ {service_name} is healthy")
                
            except Exception as e:
                pytest.fail(f"❌ {service_name} health check failed: {e}")
    
    async def test_complete_analysis_workflow(self, http_client, sample_analysis_request):
        """Test complete analysis workflow from start to finish"""
        print("\n🚀 Starting complete analysis workflow test...")
        
        # Step 1: Submit analysis request
        print("📤 Step 1: Submitting analysis request...")
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/analysis/analyze",
            json=sample_analysis_request
        )
        
        assert response.status_code == 200, f"Analysis request failed: {response.text}"
        analysis_data = response.json()
        
        assert "analysis_id" in analysis_data
        assert "status" in analysis_data
        analysis_id = analysis_data["analysis_id"]
        
        print(f"✅ Analysis submitted successfully. ID: {analysis_id}")
        
        # Step 2: Wait for analysis completion
        print("⏳ Step 2: Waiting for analysis completion...")
        start_time = time.time()
        final_result = None
        
        while time.time() - start_time < ANALYSIS_TIMEOUT:
            status_response = await http_client.get(
                f"{BACKEND_URL}/api/v1/analysis/{analysis_id}/status"
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            
            current_status = status_data.get("status")
            print(f"📊 Current status: {current_status}")
            
            if current_status == "completed":
                final_result = status_data
                break
            elif current_status == "failed":
                pytest.fail(f"Analysis failed: {status_data.get('error', 'Unknown error')}")
            
            await asyncio.sleep(5)  # Wait 5 seconds before checking again
        
        assert final_result is not None, "Analysis did not complete within timeout"
        print("✅ Analysis completed successfully!")
        
        # Step 3: Validate analysis results
        print("🔍 Step 3: Validating analysis results...")
        
        # Check required fields
        required_fields = ["analysis_id", "status", "results", "metadata"]
        for field in required_fields:
            assert field in final_result, f"Missing required field: {field}"
        
        results = final_result["results"]
        
        # Validate biome identification
        if "biome_analysis" in results:
            biome_data = results["biome_analysis"]
            assert "primary_biome" in biome_data
            assert "confidence" in biome_data
            assert isinstance(biome_data["confidence"], (int, float))
            print(f"✅ Biome identified: {biome_data['primary_biome']}")
        
        # Validate biodiversity analysis
        if "biodiversity_analysis" in results:
            biodiversity_data = results["biodiversity_analysis"]
            assert "species_count" in biodiversity_data
            assert "conservation_status" in biodiversity_data
            print(f"✅ Biodiversity analysis: {biodiversity_data['species_count']} species found")
        
        # Validate recovery plan
        if "recovery_plan" in results:
            recovery_data = results["recovery_plan"]
            assert "recommendations" in recovery_data
            assert "timeline" in recovery_data
            assert isinstance(recovery_data["recommendations"], list)
            print(f"✅ Recovery plan: {len(recovery_data['recommendations'])} recommendations")
        
        print("🎉 Complete analysis workflow test passed!")
        return final_result
    
    async def test_rag_service_integration(self, http_client):
        """Test RAG service integration for scientific data retrieval"""
        print("\n🔬 Testing RAG service integration...")
        
        # Test data ingestion status
        ingestion_response = await http_client.get(f"{RAG_SERVICE_URL}/api/v1/ingestion/status")
        assert ingestion_response.status_code == 200
        
        ingestion_data = ingestion_response.json()
        print(f"📊 Ingestion status: {ingestion_data.get('status', 'unknown')}")
        
        # Test search functionality
        search_request = {
            "query": "Atlantic Forest biodiversity conservation",
            "limit": 5,
            "include_metadata": True
        }
        
        search_response = await http_client.post(
            f"{RAG_SERVICE_URL}/api/v1/search",
            json=search_request
        )
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        assert "results" in search_data
        assert isinstance(search_data["results"], list)
        
        if search_data["results"]:
            result = search_data["results"][0]
            assert "content" in result
            assert "score" in result
            assert "metadata" in result
            print(f"✅ RAG search returned {len(search_data['results'])} results")
        
        print("✅ RAG service integration test passed!")
    
    async def test_gpu_service_integration(self, http_client):
        """Test GPU service integration for AI inference"""
        print("\n🤖 Testing GPU service integration...")
        
        # Test GPU status
        gpu_response = await http_client.get(f"{GPU_SERVICE_URL}/health/gpu")
        assert gpu_response.status_code == 200
        
        gpu_data = gpu_response.json()
        print(f"🖥️ GPU available: {gpu_data.get('available', False)}")
        
        # Test inference
        inference_request = {
            "prompt": "Analyze the biodiversity of the Atlantic Forest biome in Brazil and suggest conservation strategies.",
            "max_tokens": 500,
            "temperature": 0.7,
            "system_prompt": "You are an environmental expert specializing in Brazilian ecosystems."
        }
        
        inference_response = await http_client.post(
            f"{GPU_SERVICE_URL}/api/v1/inference/generate",
            json=inference_request
        )
        
        assert inference_response.status_code == 200
        inference_data = inference_response.json()
        
        assert "response" in inference_data
        assert "tokens_used" in inference_data
        assert len(inference_data["response"]) > 0
        
        print(f"✅ GPU inference generated {inference_data['tokens_used']} tokens")
        print("✅ GPU service integration test passed!")
    
    async def test_streaming_analysis(self, http_client, sample_analysis_request):
        """Test streaming analysis with Server-Sent Events"""
        print("\n📡 Testing streaming analysis...")
        
        # Submit streaming analysis request
        stream_request = {**sample_analysis_request, "stream": True}
        
        async with http_client.stream(
            "POST",
            f"{BACKEND_URL}/api/v1/analysis/analyze/stream",
            json=stream_request
        ) as response:
            assert response.status_code == 200
            assert response.headers.get("content-type") == "text/event-stream"
            
            events_received = 0
            final_result = None
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])  # Remove "data: " prefix
                        events_received += 1
                        
                        if event_data.get("type") == "progress":
                            print(f"📊 Progress: {event_data.get('message', 'Unknown')}")
                        elif event_data.get("type") == "completed":
                            final_result = event_data
                            break
                        elif event_data.get("type") == "error":
                            pytest.fail(f"Streaming analysis failed: {event_data.get('message')}")
                            
                    except json.JSONDecodeError:
                        continue  # Skip invalid JSON lines
            
            assert events_received > 0, "No events received from streaming endpoint"
            assert final_result is not None, "Streaming analysis did not complete"
            
            print(f"✅ Streaming analysis completed with {events_received} events")
    
    async def test_error_handling_and_recovery(self, http_client):
        """Test error handling and service recovery"""
        print("\n🛡️ Testing error handling and recovery...")
        
        # Test invalid analysis request
        invalid_request = {
            "location": {
                "latitude": "invalid",  # Invalid latitude
                "longitude": -46.6333
            }
        }
        
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/analysis/analyze",
            json=invalid_request
        )
        
        assert response.status_code == 422, "Should return validation error"
        error_data = response.json()
        assert "detail" in error_data
        print("✅ Invalid request properly rejected")
        
        # Test non-existent analysis ID
        fake_id = "non-existent-analysis-id"
        response = await http_client.get(
            f"{BACKEND_URL}/api/v1/analysis/{fake_id}/status"
        )
        
        assert response.status_code == 404, "Should return not found error"
        print("✅ Non-existent analysis properly handled")
        
        print("✅ Error handling and recovery test passed!")
    
    async def test_performance_benchmarks(self, http_client, sample_analysis_request):
        """Test performance benchmarks and response times"""
        print("\n⚡ Testing performance benchmarks...")
        
        # Test concurrent requests
        concurrent_requests = 3
        tasks = []
        
        for i in range(concurrent_requests):
            task = http_client.post(
                f"{BACKEND_URL}/api/v1/analysis/analyze",
                json=sample_analysis_request
            )
            tasks.append(task)
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) >= concurrent_requests // 2, "Too many concurrent requests failed"
        
        avg_response_time = (end_time - start_time) / concurrent_requests
        print(f"⚡ Average response time for {concurrent_requests} concurrent requests: {avg_response_time:.2f}s")
        
        # Test response time for single request
        start_time = time.time()
        response = await http_client.get(f"{BACKEND_URL}/health")
        end_time = time.time()
        
        health_response_time = end_time - start_time
        assert health_response_time < 1.0, f"Health check too slow: {health_response_time:.2f}s"
        
        print(f"⚡ Health check response time: {health_response_time:.3f}s")
        print("✅ Performance benchmarks passed!")


@pytest.mark.asyncio
async def test_full_system_integration():
    """Run all integration tests in sequence"""
    print("\n🎯 Starting Full System Integration Test Suite")
    print("=" * 60)
    
    test_instance = TestE2EAnalysis()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Run all tests
        await test_instance.test_health_checks_all_services(client)
        await test_instance.test_rag_service_integration(client)
        await test_instance.test_gpu_service_integration(client)
        await test_instance.test_error_handling_and_recovery(client)
        await test_instance.test_performance_benchmarks(client, test_instance.sample_analysis_request())
        
        # Run complete workflow test last (most comprehensive)
        await test_instance.test_complete_analysis_workflow(client, test_instance.sample_analysis_request())
        await test_instance.test_streaming_analysis(client, test_instance.sample_analysis_request())
    
    print("\n🎉 Full System Integration Test Suite PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_full_system_integration())
