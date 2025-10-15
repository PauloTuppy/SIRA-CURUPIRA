"""
Integration Tests for Service-to-Service Communication
Tests communication patterns between Backend, RAG Service, and GPU Service
"""

import pytest
import asyncio
import httpx
import json
import time
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock

# Service URLs
BACKEND_URL = "http://localhost:8000"
RAG_SERVICE_URL = "http://localhost:8001"
GPU_SERVICE_URL = "http://localhost:8002"


class TestServiceCommunication:
    """Test inter-service communication patterns"""
    
    @pytest.fixture
    async def http_client(self):
        """HTTP client for API calls"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client
    
    async def test_backend_to_rag_communication(self, http_client):
        """Test Backend -> RAG Service communication"""
        print("\n🔄 Testing Backend -> RAG Service communication...")
        
        # Test that backend can query RAG service
        search_request = {
            "query": "Cerrado biome conservation strategies",
            "location": {
                "latitude": -15.7801,
                "longitude": -47.9292
            },
            "limit": 3
        }
        
        # Send request through backend (which should forward to RAG service)
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/knowledge/search",
            json=search_request
        )
        
        assert response.status_code == 200, f"Backend->RAG communication failed: {response.text}"
        data = response.json()
        
        assert "results" in data
        assert isinstance(data["results"], list)
        
        print(f"✅ Backend successfully communicated with RAG service")
        print(f"📊 Retrieved {len(data['results'])} knowledge results")
    
    async def test_backend_to_gpu_communication(self, http_client):
        """Test Backend -> GPU Service communication"""
        print("\n🔄 Testing Backend -> GPU Service communication...")
        
        # Test that backend can send inference requests to GPU service
        inference_request = {
            "prompt": "Generate a recovery plan for degraded Cerrado areas",
            "context": {
                "biome": "Cerrado",
                "degradation_level": "moderate",
                "area_size": "100 hectares"
            }
        }
        
        # Send request through backend (which should forward to GPU service)
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/ai/generate",
            json=inference_request
        )
        
        assert response.status_code == 200, f"Backend->GPU communication failed: {response.text}"
        data = response.json()
        
        assert "response" in data
        assert "tokens_used" in data
        assert len(data["response"]) > 0
        
        print(f"✅ Backend successfully communicated with GPU service")
        print(f"🤖 Generated response with {data['tokens_used']} tokens")
    
    async def test_rag_to_gpu_enrichment(self, http_client):
        """Test RAG Service -> GPU Service for content enrichment"""
        print("\n🔄 Testing RAG -> GPU Service for content enrichment...")
        
        # First, get some content from RAG service
        rag_response = await http_client.post(
            f"{RAG_SERVICE_URL}/api/v1/search",
            json={
                "query": "Atlantic Forest endangered species",
                "limit": 2,
                "include_metadata": True
            }
        )
        
        assert rag_response.status_code == 200
        rag_data = rag_response.json()
        
        if not rag_data.get("results"):
            pytest.skip("No RAG results available for enrichment test")
        
        # Use RAG content to enrich with GPU service
        rag_content = rag_data["results"][0]["content"]
        
        enrichment_request = {
            "prompt": f"Summarize and provide actionable insights for this scientific data: {rag_content[:500]}...",
            "max_tokens": 300,
            "temperature": 0.6
        }
        
        gpu_response = await http_client.post(
            f"{GPU_SERVICE_URL}/api/v1/inference/generate",
            json=enrichment_request
        )
        
        assert gpu_response.status_code == 200
        gpu_data = gpu_response.json()
        
        assert "response" in gpu_data
        assert len(gpu_data["response"]) > 0
        
        print(f"✅ RAG content successfully enriched by GPU service")
        print(f"📝 Enriched content length: {len(gpu_data['response'])} characters")
    
    async def test_coordinated_analysis_workflow(self, http_client):
        """Test coordinated workflow across all services"""
        print("\n🎯 Testing coordinated analysis workflow...")
        
        # Step 1: Backend coordinates the analysis
        analysis_request = {
            "location": {
                "latitude": -23.5505,
                "longitude": -46.6333,
                "address": "São Paulo, SP, Brazil"
            },
            "analysis_type": "comprehensive",
            "include_biodiversity": True,
            "include_recovery_plan": True
        }
        
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/analysis/analyze",
            json=analysis_request
        )
        
        assert response.status_code == 200
        analysis_data = response.json()
        analysis_id = analysis_data["analysis_id"]
        
        print(f"📋 Analysis started with ID: {analysis_id}")
        
        # Step 2: Monitor the coordinated workflow
        max_wait_time = 60  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = await http_client.get(
                f"{BACKEND_URL}/api/v1/analysis/{analysis_id}/status"
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            
            current_status = status_data.get("status")
            progress = status_data.get("progress", {})
            
            print(f"📊 Status: {current_status}")
            
            # Check if services are being coordinated
            if "steps" in progress:
                for step in progress["steps"]:
                    step_name = step.get("name", "Unknown")
                    step_status = step.get("status", "Unknown")
                    print(f"  └─ {step_name}: {step_status}")
            
            if current_status in ["completed", "failed"]:
                break
            
            await asyncio.sleep(3)
        
        # Verify coordination was successful
        final_status = status_data.get("status")
        assert final_status == "completed", f"Coordinated analysis failed: {final_status}"
        
        print("✅ Coordinated analysis workflow completed successfully")
    
    async def test_service_resilience(self, http_client):
        """Test service resilience and fallback mechanisms"""
        print("\n🛡️ Testing service resilience...")
        
        # Test backend resilience when RAG service is slow
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock slow RAG service response
            async def slow_response(*args, **kwargs):
                if "rag-service" in str(args[0]):
                    await asyncio.sleep(2)  # Simulate slow response
                    return httpx.Response(200, json={"results": []})
                return await httpx.AsyncClient.post(*args, **kwargs)
            
            mock_post.side_effect = slow_response
            
            # Backend should handle slow RAG service gracefully
            search_request = {
                "query": "Test query",
                "timeout": 1  # Short timeout
            }
            
            start_time = time.time()
            response = await http_client.post(
                f"{BACKEND_URL}/api/v1/knowledge/search",
                json=search_request
            )
            end_time = time.time()
            
            # Should either succeed quickly or fail gracefully
            response_time = end_time - start_time
            assert response_time < 5.0, f"Response took too long: {response_time}s"
            
            print(f"✅ Service resilience test completed in {response_time:.2f}s")
    
    async def test_load_balancing_and_scaling(self, http_client):
        """Test load balancing and scaling capabilities"""
        print("\n⚖️ Testing load balancing and scaling...")
        
        # Send multiple concurrent requests to test load handling
        concurrent_requests = 5
        tasks = []
        
        for i in range(concurrent_requests):
            request_data = {
                "query": f"Test query {i}",
                "limit": 1
            }
            
            task = http_client.post(
                f"{BACKEND_URL}/api/v1/knowledge/search",
                json=request_data
            )
            tasks.append(task)
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        failed_responses = [r for r in responses if isinstance(r, Exception)]
        
        success_rate = len(successful_responses) / len(responses)
        avg_response_time = (end_time - start_time) / len(responses)
        
        print(f"📊 Success rate: {success_rate:.2%}")
        print(f"⚡ Average response time: {avg_response_time:.2f}s")
        
        # At least 80% should succeed under load
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2%}"
        
        print("✅ Load balancing and scaling test passed")
    
    async def test_data_consistency(self, http_client):
        """Test data consistency across services"""
        print("\n🔄 Testing data consistency...")
        
        # Test that the same query returns consistent results
        test_query = "Mata Atlântica biodiversity"
        
        # Query RAG service directly
        rag_response = await http_client.post(
            f"{RAG_SERVICE_URL}/api/v1/search",
            json={"query": test_query, "limit": 3}
        )
        
        # Query through backend
        backend_response = await http_client.post(
            f"{BACKEND_URL}/api/v1/knowledge/search",
            json={"query": test_query, "limit": 3}
        )
        
        if rag_response.status_code == 200 and backend_response.status_code == 200:
            rag_data = rag_response.json()
            backend_data = backend_response.json()
            
            # Results should be consistent (allowing for minor differences in formatting)
            rag_count = len(rag_data.get("results", []))
            backend_count = len(backend_data.get("results", []))
            
            print(f"📊 RAG direct: {rag_count} results")
            print(f"📊 Backend proxy: {backend_count} results")
            
            # Allow some variance but should be roughly consistent
            assert abs(rag_count - backend_count) <= 1, "Inconsistent result counts"
            
            print("✅ Data consistency test passed")
        else:
            print("⚠️ Data consistency test skipped (services not available)")
    
    async def test_authentication_propagation(self, http_client):
        """Test authentication token propagation between services"""
        print("\n🔐 Testing authentication propagation...")
        
        # Test with mock authentication header
        auth_headers = {
            "Authorization": "Bearer test-token-123",
            "X-User-ID": "test-user"
        }
        
        # Send authenticated request through backend
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/knowledge/search",
            json={"query": "test", "limit": 1},
            headers=auth_headers
        )
        
        # Should handle authentication gracefully (even if not fully implemented)
        assert response.status_code in [200, 401, 403], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            print("✅ Authentication propagation working")
        else:
            print("ℹ️ Authentication not yet implemented (expected)")
    
    async def test_error_propagation(self, http_client):
        """Test error propagation between services"""
        print("\n❌ Testing error propagation...")
        
        # Test invalid request that should propagate error correctly
        invalid_request = {
            "query": "",  # Empty query should cause error
            "limit": -1   # Invalid limit
        }
        
        response = await http_client.post(
            f"{BACKEND_URL}/api/v1/knowledge/search",
            json=invalid_request
        )
        
        # Should return proper error response
        assert response.status_code >= 400, "Should return error status"
        
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data, "Should include error details"
        
        print("✅ Error propagation working correctly")


@pytest.mark.asyncio
async def test_all_service_communication():
    """Run all service communication tests"""
    print("\n🌐 Starting Service Communication Test Suite")
    print("=" * 60)
    
    test_instance = TestServiceCommunication()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test basic communication patterns
        await test_instance.test_backend_to_rag_communication(client)
        await test_instance.test_backend_to_gpu_communication(client)
        await test_instance.test_rag_to_gpu_enrichment(client)
        
        # Test advanced coordination
        await test_instance.test_coordinated_analysis_workflow(client)
        await test_instance.test_service_resilience(client)
        await test_instance.test_load_balancing_and_scaling(client)
        
        # Test data and error handling
        await test_instance.test_data_consistency(client)
        await test_instance.test_authentication_propagation(client)
        await test_instance.test_error_propagation(client)
    
    print("\n🎉 Service Communication Test Suite PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_all_service_communication())
