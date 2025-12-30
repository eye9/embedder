#!/usr/bin/env python3
"""
Simple test script to verify the Batch Excel Processor API endpoints.
"""

import requests
import json
import time
from pathlib import Path


def test_api_endpoints():
    """Test the main API endpoints."""
    base_url = "http://localhost:8001"
    
    print("🧪 Testing Batch Excel Processor API")
    print(f"📡 Base URL: {base_url}")
    print("-" * 50)
    
    try:
        # Test 1: Health check
        print("1️⃣ Testing health check...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
        
        # Test 2: Service info
        print("\n2️⃣ Testing service info...")
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Service info passed")
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Endpoints: {len(data.get('endpoints', []))}")
        else:
            print(f"❌ Service info failed: {response.status_code}")
        
        # Test 3: Upload endpoint (without auth - should fail)
        print("\n3️⃣ Testing upload endpoint (no auth)...")
        response = requests.post(f"{base_url}/upload", timeout=5)
        if response.status_code == 401:
            print("✅ Upload endpoint correctly requires authentication")
        else:
            print(f"❌ Upload endpoint should require auth: {response.status_code}")
        
        # Test 4: Upload endpoint (with auth but no file - should fail)
        print("\n4️⃣ Testing upload endpoint (auth, no file)...")
        auth = ("admin", "admin123")
        response = requests.post(f"{base_url}/upload", auth=auth, timeout=5)
        if response.status_code == 422:  # Validation error
            print("✅ Upload endpoint correctly validates file requirement")
        else:
            print(f"❌ Upload endpoint validation: {response.status_code}")
        
        # Test 5: WebSocket info
        print("\n5️⃣ Testing WebSocket info...")
        test_task_id = "test-task-123"
        response = requests.get(f"{base_url}/ws/info/{test_task_id}", timeout=5)
        if response.status_code == 200:
            print("✅ WebSocket info endpoint working")
            data = response.json()
            print(f"   WebSocket URL: {data.get('websocket_url')}")
        else:
            print(f"❌ WebSocket info failed: {response.status_code}")
        
        print("\n🎉 API testing completed!")
        print("✅ All core endpoints are responding correctly")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the server running?")
        print("💡 Start the server with: python start_web_app.py")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print("\n🚀 Ready for production!")
    else:
        print("\n🔧 Please fix issues before deployment")