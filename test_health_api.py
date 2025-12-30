#!/usr/bin/env python3
"""
Test script for health API endpoints.

This script tests the health check API endpoints to ensure they work correctly.
"""

import asyncio
import logging
from fastapi.testclient import TestClient

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def test_health_endpoints():
    """Test health check API endpoints."""
    print("Testing health API endpoints...")
    
    try:
        from batch_processor.web.app import create_app
        
        # Create test client
        app = create_app()
        client = TestClient(app)
        
        # Test basic health check
        print("Testing basic health check...")
        response = client.get("/health/")
        print(f"Basic health status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Health response: {data}")
            assert data["status"] == "healthy"
            print("✓ Basic health check passed")
        else:
            print(f"✗ Basic health check failed with status {response.status_code}")
            return False
        
        # Test service status
        print("Testing service status...")
        response = client.get("/health/status")
        print(f"Service status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Service info: {data['service']}")
            assert data["service"] == "Batch Excel Processor"
            print("✓ Service status check passed")
        else:
            print(f"✗ Service status check failed with status {response.status_code}")
            return False
        
        # Test readiness probe
        print("Testing readiness probe...")
        response = client.get("/health/readiness")
        print(f"Readiness status: {response.status_code}")
        if response.status_code in [200, 503]:  # Either ready or not ready is acceptable
            data = response.json()
            print(f"Readiness: {data['ready']}")
            print("✓ Readiness probe responded correctly")
        else:
            print(f"✗ Readiness probe failed with status {response.status_code}")
            return False
        
        # Test liveness probe
        print("Testing liveness probe...")
        response = client.get("/health/liveness")
        print(f"Liveness status: {response.status_code}")
        if response.status_code in [200, 503]:  # Either alive or not alive is acceptable
            data = response.json()
            print(f"Liveness: {data['alive']}")
            print("✓ Liveness probe responded correctly")
        else:
            print(f"✗ Liveness probe failed with status {response.status_code}")
            return False
        
        print("✓ All health API endpoint tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Health API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run health API tests."""
    print("=" * 60)
    print("Testing Health API Endpoints")
    print("=" * 60)
    
    success = test_health_endpoints()
    
    print("=" * 60)
    if success:
        print("🎉 All health API tests passed!")
    else:
        print("❌ Some health API tests failed.")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)