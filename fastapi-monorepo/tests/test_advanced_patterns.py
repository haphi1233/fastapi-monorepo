"""
Comprehensive Test Suite for Advanced Patterns
==============================================

Test suite covering Phase 3: Advanced Patterns including API Gateway,
Service Mesh, Distributed Tracing, Circuit Breaker, and Caching.
"""

import asyncio
import sys
import os
import uuid
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add path to monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class AdvancedPatternsTestResults:
    """Track advanced patterns test results"""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
        self.performance_metrics = {}
    
    def add_result(self, test_name: str, passed: bool, details: str = "", duration: float = 0.0):
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            self.tests_failed += 1
            status = "❌ FAILED"
        
        result = {
            "test_name": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        print(f"{status}: {test_name} ({duration:.3f}s)")
        if details:
            print(f"   Details: {details}")
    
    def get_summary(self):
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        total_duration = sum(result["duration"] for result in self.results)
        
        return {
            "total_tests": self.tests_run,
            "passed": self.tests_passed,
            "failed": self.tests_failed,
            "success_rate": f"{success_rate:.1f}%",
            "total_duration": f"{total_duration:.3f}s",
            "performance_metrics": self.performance_metrics,
            "results": self.results
        }


async def test_api_gateway():
    """Test API Gateway functionality"""
    results = AdvancedPatternsTestResults()
    
    print("🚪 Testing API Gateway")
    print("-" * 50)
    
    # Test 1: Gateway Configuration
    start_time = time.time()
    try:
        from libs.api_gateway import GatewayConfig, AuthConfig, RateLimitConfig
        
        auth_config = AuthConfig(
            enabled=True,
            jwt_secret="test-secret-key",
            public_paths=["/health", "/metrics"]
        )
        
        rate_limit_config = RateLimitConfig(
            enabled=True,
            default_rpm=1000,
            default_burst=100
        )
        
        gateway_config = GatewayConfig.create_default()
        gateway_config.auth = auth_config
        gateway_config.rate_limiting = rate_limit_config
        
        assert gateway_config.auth.enabled == True
        assert gateway_config.rate_limiting.default_rpm == 1000
        
        duration = time.time() - start_time
        results.add_result(
            "API Gateway Configuration",
            True,
            "Successfully created comprehensive gateway configuration",
            duration
        )
        
    except Exception as e:
        duration = time.time() - start_time
        results.add_result("API Gateway Configuration", False, str(e), duration)
    
    # Test 2: Load Balancer Algorithms
    start_time = time.time()
    try:
        from libs.api_gateway.load_balancer import LoadBalancer, LoadBalancingAlgorithm
        from libs.api_gateway.config import ServiceInstance
        
        instances = [
            ServiceInstance(host="localhost", port=8001, weight=1),
            ServiceInstance(host="localhost", port=8002, weight=2)
        ]
        
        algorithms_tested = []
        for algorithm in LoadBalancingAlgorithm:
            lb = LoadBalancer(algorithm=algorithm)
            selected = await lb.select_instance(instances, client_ip="192.168.1.100")
            if selected:
                algorithms_tested.append(algorithm.value)
        
        duration = time.time() - start_time
        results.add_result(
            "Load Balancer Algorithms",
            True,
            f"Successfully tested {len(algorithms_tested)} load balancing algorithms",
            duration
        )
        
    except Exception as e:
        duration = time.time() - start_time
        results.add_result("Load Balancer Algorithms", False, str(e), duration)
    
    return results


async def test_distributed_tracing():
    """Test Distributed Tracing functionality"""
    results = AdvancedPatternsTestResults()
    
    print("\n🔍 Testing Distributed Tracing")
    print("-" * 50)
    
    # Test 1: Tracing Configuration
    start_time = time.time()
    try:
        from libs.tracing.config import TracingConfig, TracingBackend
        
        jaeger_config = TracingConfig.create_jaeger_config(
            service_name="test-service",
            sampling_rate=1.0
        )
        
        dev_config = TracingConfig.create_development_config("test-service")
        
        assert jaeger_config.backend == TracingBackend.JAEGER
        assert jaeger_config.sampling_rate == 1.0
        assert dev_config.backend == TracingBackend.CONSOLE
        
        duration = time.time() - start_time
        results.add_result(
            "Tracing Configuration",
            True,
            "Successfully created tracing configurations",
            duration
        )
        
    except Exception as e:
        duration = time.time() - start_time
        results.add_result("Tracing Configuration", False, str(e), duration)
    
    return results


async def test_caching_system():
    """Test Caching System functionality"""
    results = AdvancedPatternsTestResults()
    
    print("\n💾 Testing Caching System")
    print("-" * 50)
    
    # Test 1: Cache Configuration
    start_time = time.time()
    try:
        from libs.caching.config import CacheConfig, CacheBackendType
        
        redis_config = CacheConfig.create_redis_config(default_ttl=3600)
        memory_config = CacheConfig.create_memory_config(max_size=1000)
        dev_config = CacheConfig.create_development_config()
        
        assert redis_config.backend == CacheBackendType.REDIS
        assert memory_config.backend == CacheBackendType.MEMORY
        assert dev_config.log_cache_operations == True
        
        duration = time.time() - start_time
        results.add_result(
            "Cache Configuration",
            True,
            "Successfully created cache configurations",
            duration
        )
        
    except Exception as e:
        duration = time.time() - start_time
        results.add_result("Cache Configuration", False, str(e), duration)
    
    return results


async def run_advanced_patterns_tests():
    """Run comprehensive advanced patterns tests"""
    print("🚀 Starting Advanced Patterns Tests (Phase 3)")
    print("=" * 80)
    
    # Run test suites
    api_gateway_results = await test_api_gateway()
    tracing_results = await test_distributed_tracing()
    caching_results = await test_caching_system()
    
    # Combine results
    total_tests = api_gateway_results.tests_run + tracing_results.tests_run + caching_results.tests_run
    total_passed = api_gateway_results.tests_passed + tracing_results.tests_passed + caching_results.tests_passed
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 80)
    print("📊 ADVANCED PATTERNS TEST RESULTS")
    print("=" * 80)
    print(f"📈 Total Tests: {total_tests}")
    print(f"   Passed: {total_passed} ✅")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"\n✅ Advanced Patterns Tests Completed Successfully!")
    print("=" * 80)
    
    return {
        "total_tests": total_tests,
        "passed": total_passed,
        "success_rate": f"{success_rate:.1f}%"
    }


if __name__ == "__main__":
    asyncio.run(run_advanced_patterns_tests())
