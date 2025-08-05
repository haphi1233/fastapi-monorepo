#!/usr/bin/env python3
"""
API Gateway Test Script
======================

Test API Gateway và các service endpoints
"""
import requests
import time
import sys
from typing import Dict, List

def test_endpoint(url: str, name: str, timeout: int = 5) -> Dict:
    """Test một endpoint"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        response_time = time.time() - start_time
        
        return {
            'name': name,
            'url': url,
            'status': 'success',
            'status_code': response.status_code,
            'response_time': round(response_time, 3),
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }
    except requests.exceptions.ConnectionError:
        return {
            'name': name,
            'url': url,
            'status': 'connection_error',
            'error': 'Service not running or not accessible'
        }
    except requests.exceptions.Timeout:
        return {
            'name': name,
            'url': url,
            'status': 'timeout',
            'error': f'Request timeout after {timeout} seconds'
        }
    except Exception as e:
        return {
            'name': name,
            'url': url,
            'status': 'error',
            'error': str(e)
        }

def main():
    """Main test function"""
    print("🧪 API Gateway & Services Test")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        # Direct services
        ("Auth Service Direct", "http://localhost:8001/health"),
        ("Articles Service Direct", "http://localhost:8002/health"),
        ("Products Service Direct", "http://localhost:8003/health"),
        
        # API Gateway
        ("API Gateway Health", "http://localhost:8000/health"),
        ("API Gateway Metrics", "http://localhost:8000/metrics"),
        
        # Gateway routing to services
        ("Gateway -> Auth", "http://localhost:8000/auth/health"),
        ("Gateway -> Articles", "http://localhost:8000/articles/health"),
        ("Gateway -> Products", "http://localhost:8000/products/health"),
        
        # API v1 routes
        ("Gateway -> Auth API", "http://localhost:8000/api/v1/auth/health"),
        ("Gateway -> Articles API", "http://localhost:8000/api/v1/articles/health"),
        ("Gateway -> Products API", "http://localhost:8000/api/v1/products/health"),
        
        # Documentation endpoints
        ("Gateway Docs", "http://localhost:8000/docs"),
        ("Auth Docs", "http://localhost:8001/docs"),
        ("Products Docs", "http://localhost:8003/docs"),
    ]
    
    results = []
    success_count = 0
    
    for name, url in endpoints:
        print(f"\n🔍 Testing {name}...")
        result = test_endpoint(url, name, timeout=10)
        results.append(result)
        
        if result['status'] == 'success':
            success_count += 1
            print(f"   ✅ {result['status_code']} - {result['response_time']}s")
        else:
            print(f"   ❌ {result['status'].upper()}: {result.get('error', 'Unknown error')}")
    
    # Summary
    total_tests = len(endpoints)
    print("\n" + "=" * 50)
    print(f"📊 Test Summary: {success_count}/{total_tests} endpoints working")
    
    # Group results by category
    categories = {
        'Direct Services': [],
        'API Gateway': [],
        'Gateway Routing': [],
        'API v1 Routes': [],
        'Documentation': []
    }
    
    for result in results:
        name = result['name']
        if 'Direct' in name:
            categories['Direct Services'].append(result)
        elif 'Gateway Health' in name or 'Gateway Metrics' in name:
            categories['API Gateway'].append(result)
        elif 'Gateway ->' in name and 'API' not in name:
            categories['Gateway Routing'].append(result)
        elif 'API' in name and 'Gateway ->' in name:
            categories['API v1 Routes'].append(result)
        elif 'Docs' in name:
            categories['Documentation'].append(result)
    
    for category, category_results in categories.items():
        if not category_results:
            continue
            
        working = sum(1 for r in category_results if r['status'] == 'success')
        total = len(category_results)
        
        print(f"\n🔧 {category}: {working}/{total} working")
        for result in category_results:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"   {status_icon} {result['name']}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if success_count == total_tests:
        print("   🎉 All systems are working perfectly!")
        print("   🚀 Your FastAPI Monorepo with API Gateway is ready to use!")
    elif success_count >= total_tests * 0.7:
        print("   ⚠️  Most systems are working. Check failed endpoints above.")
    else:
        print("   🚨 Multiple system failures detected. Check service status.")
    
    return 0 if success_count >= total_tests * 0.5 else 1

if __name__ == "__main__":
    sys.exit(main())
