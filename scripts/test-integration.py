#!/usr/bin/env python3
"""
SIRA Integration Test Script
Tests basic functionality of all services
"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import Dict, Any, Optional

# Service URLs
BACKEND_URL = "http://localhost:8000"
RAG_SERVICE_URL = "http://localhost:8001"
GPU_SERVICE_URL = "http://localhost:8002"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_info(message: str):
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {message}")

def log_success(message: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {message}")

def log_warning(message: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.ENDC} {message}")

def log_error(message: str):
    print(f"{Colors.RED}[ERROR]{Colors.ENDC} {message}")

async def test_service_health(session: aiohttp.ClientSession, service_name: str, url: str) -> bool:
    """Test if a service is healthy"""
    try:
        async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "healthy":
                    log_success(f"{service_name} is healthy")
                    return True
                else:
                    log_warning(f"{service_name} responded but status is: {data.get('status', 'unknown')}")
                    return False
            else:
                log_error(f"{service_name} health check failed: HTTP {response.status}")
                return False
    except asyncio.TimeoutError:
        log_error(f"{service_name} health check timed out")
        return False
    except Exception as e:
        log_error(f"{service_name} health check failed: {e}")
        return False

async def test_backend_basic_functionality(session: aiohttp.ClientSession) -> bool:
    """Test basic backend functionality"""
    log_info("Testing Backend basic functionality...")
    
    try:
        # Test analysis endpoint (mock request)
        analysis_request = {
            "location": {
                "latitude": -23.5505,
                "longitude": -46.6333,
                "address": "São Paulo, SP, Brazil"
            },
            "analysis_type": "basic",
            "include_biodiversity": False,
            "include_recovery_plan": False
        }
        
        async with session.post(
            f"{BACKEND_URL}/api/v1/analysis/analyze",
            json=analysis_request,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status in [200, 202]:
                data = await response.json()
                if "analysis_id" in data:
                    log_success("Backend analysis endpoint working")
                    return True
                else:
                    log_warning("Backend analysis endpoint responded but no analysis_id")
                    return False
            else:
                log_error(f"Backend analysis endpoint failed: HTTP {response.status}")
                return False
                
    except Exception as e:
        log_error(f"Backend test failed: {e}")
        return False

async def test_rag_service_functionality(session: aiohttp.ClientSession) -> bool:
    """Test RAG service functionality"""
    log_info("Testing RAG Service functionality...")
    
    try:
        # Test search endpoint
        search_request = {
            "query": "Atlantic Forest biodiversity",
            "limit": 3,
            "include_metadata": True
        }
        
        async with session.post(
            f"{RAG_SERVICE_URL}/api/v1/search",
            json=search_request,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                if "results" in data:
                    log_success(f"RAG Service search working - found {len(data['results'])} results")
                    return True
                else:
                    log_warning("RAG Service search responded but no results field")
                    return False
            else:
                log_error(f"RAG Service search failed: HTTP {response.status}")
                return False
                
    except Exception as e:
        log_error(f"RAG Service test failed: {e}")
        return False

async def test_gpu_service_functionality(session: aiohttp.ClientSession) -> bool:
    """Test GPU service functionality"""
    log_info("Testing GPU Service functionality...")
    
    try:
        # Test inference endpoint
        inference_request = {
            "prompt": "What is the Atlantic Forest biome?",
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        async with session.post(
            f"{GPU_SERVICE_URL}/api/v1/inference/generate",
            json=inference_request,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status == 200:
                data = await response.json()
                if "response" in data and len(data["response"]) > 0:
                    log_success(f"GPU Service inference working - generated {data.get('tokens_used', 0)} tokens")
                    return True
                else:
                    log_warning("GPU Service inference responded but no response content")
                    return False
            else:
                log_error(f"GPU Service inference failed: HTTP {response.status}")
                return False
                
    except Exception as e:
        log_error(f"GPU Service test failed: {e}")
        return False

async def test_service_integration(session: aiohttp.ClientSession) -> bool:
    """Test integration between services"""
    log_info("Testing service integration...")
    
    try:
        # Test backend -> RAG service integration
        search_request = {
            "query": "Cerrado conservation strategies",
            "limit": 2
        }
        
        async with session.post(
            f"{BACKEND_URL}/api/v1/knowledge/search",
            json=search_request,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                if "results" in data:
                    log_success("Backend -> RAG Service integration working")
                    
                    # Test backend -> GPU service integration
                    ai_request = {
                        "prompt": "Summarize Cerrado conservation strategies",
                        "max_tokens": 150
                    }
                    
                    async with session.post(
                        f"{BACKEND_URL}/api/v1/ai/generate",
                        json=ai_request,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as ai_response:
                        if ai_response.status == 200:
                            ai_data = await ai_response.json()
                            if "response" in ai_data:
                                log_success("Backend -> GPU Service integration working")
                                return True
                            else:
                                log_warning("Backend -> GPU Service integration responded but no content")
                                return False
                        else:
                            log_error(f"Backend -> GPU Service integration failed: HTTP {ai_response.status}")
                            return False
                else:
                    log_warning("Backend -> RAG Service integration responded but no results")
                    return False
            else:
                log_error(f"Backend -> RAG Service integration failed: HTTP {response.status}")
                return False
                
    except Exception as e:
        log_error(f"Service integration test failed: {e}")
        return False

async def test_performance_basic(session: aiohttp.ClientSession) -> bool:
    """Test basic performance metrics"""
    log_info("Testing basic performance...")
    
    try:
        # Test concurrent health checks
        tasks = []
        services = [
            ("Backend", BACKEND_URL),
            ("RAG Service", RAG_SERVICE_URL),
            ("GPU Service", GPU_SERVICE_URL)
        ]
        
        start_time = time.time()
        
        for service_name, url in services:
            task = session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10))
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        success_rate = len(successful_responses) / len(responses)
        total_time = end_time - start_time
        
        log_success(f"Performance test: {success_rate:.1%} success rate in {total_time:.2f}s")
        
        return success_rate >= 0.8  # At least 80% success rate
        
    except Exception as e:
        log_error(f"Performance test failed: {e}")
        return False

async def main():
    """Main test function"""
    print(f"{Colors.BOLD}🧪 SIRA Integration Test Suite{Colors.ENDC}")
    print("=" * 50)
    
    # Test results
    results = {}
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Service Health Checks
        log_info("Phase 1: Service Health Checks")
        services = [
            ("Backend", BACKEND_URL),
            ("RAG Service", RAG_SERVICE_URL),
            ("GPU Service", GPU_SERVICE_URL)
        ]
        
        health_results = []
        for service_name, url in services:
            result = await test_service_health(session, service_name, url)
            health_results.append(result)
            results[f"{service_name.lower()}_health"] = result
        
        print()
        
        # Test 2: Individual Service Functionality
        log_info("Phase 2: Individual Service Functionality")
        
        if results.get("backend_health", False):
            results["backend_functionality"] = await test_backend_basic_functionality(session)
        else:
            log_warning("Skipping Backend functionality test (service not healthy)")
            results["backend_functionality"] = False
        
        if results.get("rag service_health", False):
            results["rag_functionality"] = await test_rag_service_functionality(session)
        else:
            log_warning("Skipping RAG Service functionality test (service not healthy)")
            results["rag_functionality"] = False
        
        if results.get("gpu service_health", False):
            results["gpu_functionality"] = await test_gpu_service_functionality(session)
        else:
            log_warning("Skipping GPU Service functionality test (service not healthy)")
            results["gpu_functionality"] = False
        
        print()
        
        # Test 3: Service Integration
        log_info("Phase 3: Service Integration")
        
        if all(health_results):
            results["integration"] = await test_service_integration(session)
        else:
            log_warning("Skipping integration test (not all services healthy)")
            results["integration"] = False
        
        print()
        
        # Test 4: Basic Performance
        log_info("Phase 4: Basic Performance")
        results["performance"] = await test_performance_basic(session)
        
        print()
    
    # Summary
    print(f"{Colors.BOLD}📊 Test Results Summary{Colors.ENDC}")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.ENDC}" if result else f"{Colors.RED}FAIL{Colors.ENDC}"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print()
    success_rate = passed_tests / total_tests
    
    if success_rate >= 0.8:
        log_success(f"Integration tests completed: {passed_tests}/{total_tests} passed ({success_rate:.1%})")
        return 0
    else:
        log_error(f"Integration tests failed: {passed_tests}/{total_tests} passed ({success_rate:.1%})")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log_warning("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Test suite failed: {e}")
        sys.exit(1)
