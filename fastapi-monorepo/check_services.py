#!/usr/bin/env python3
"""
Service Health Check Script
Kiểm tra trạng thái tất cả microservices
"""
import requests
import json
import sys
from typing import Dict, List

# Service configurations
SERVICES = {
    'auth-service': {
        'url': 'http://localhost:8001',
        'health_endpoint': '/health',
        'description': 'Authentication & User Management Service'
    },
    'product-service': {
        'url': 'http://localhost:8003', 
        'health_endpoint': '/health',
        'description': 'Product Management Service'
    },
    'articles-service': {
        'url': 'http://localhost:8002',
        'health_endpoint': '/health', 
        'description': 'Articles Management Service'
    }
}

def check_service_health(service_name: str, config: Dict) -> Dict:
    """Kiểm tra health của một service"""
    try:
        url = f"{config['url']}{config['health_endpoint']}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'service': service_name,
                'status': 'healthy',
                'response_time': response.elapsed.total_seconds(),
                'data': data
            }
        else:
            return {
                'service': service_name,
                'status': 'unhealthy',
                'error': f'HTTP {response.status_code}',
                'response_time': response.elapsed.total_seconds()
            }
            
    except requests.exceptions.ConnectionError:
        return {
            'service': service_name,
            'status': 'down',
            'error': 'Connection refused - service not running'
        }
    except requests.exceptions.Timeout:
        return {
            'service': service_name,
            'status': 'timeout',
            'error': 'Request timeout after 5 seconds'
        }
    except Exception as e:
        return {
            'service': service_name,
            'status': 'error',
            'error': str(e)
        }

def main():
    """Main function"""
    print("🏥 FastAPI Monorepo - Service Health Check")
    print("=" * 50)
    
    results = []
    healthy_count = 0
    
    for service_name, config in SERVICES.items():
        print(f"\n🔍 Checking {service_name}...")
        print(f"   📝 {config['description']}")
        print(f"   🌐 {config['url']}")
        
        result = check_service_health(service_name, config)
        results.append(result)
        
        if result['status'] == 'healthy':
            healthy_count += 1
            print(f"   ✅ Status: {result['status'].upper()}")
            print(f"   ⚡ Response time: {result['response_time']:.3f}s")
            if 'data' in result:
                print(f"   📊 Database: {result['data'].get('database_status', 'N/A')}")
        else:
            print(f"   ❌ Status: {result['status'].upper()}")
            print(f"   🚨 Error: {result.get('error', 'Unknown error')}")
    
    # Summary
    total_services = len(SERVICES)
    print("\n" + "=" * 50)
    print(f"📊 Summary: {healthy_count}/{total_services} services healthy")
    
    if healthy_count == total_services:
        print("🎉 All services are running perfectly!")
        print("\n🚀 Available endpoints:")
        for service_name, config in SERVICES.items():
            print(f"   • {service_name}: {config['url']}/docs")
        return 0
    else:
        print("⚠️  Some services need attention!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
