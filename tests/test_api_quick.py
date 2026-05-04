#!/usr/bin/env python3
"""
Quick API Test

Test basic API endpoints to verify functionality.
"""

import requests
import time

def test_api():
    """Test basic API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing ТНВЭД Embedder API")
    print("=" * 40)
    
    # Wait a moment for server to be ready
    time.sleep(2)
    
    try:
        # Test root endpoint
        print("📍 Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        print()
        
        # Test health endpoint
        print("🏥 Testing health endpoint...")
        response = requests.get(f"{base_url}/api/v1/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Model loaded: {data.get('model_loaded')}")
            print(f"   Database records: {data.get('database_records')}")
        print()
        
        # Test stats endpoint
        print("📊 Testing stats endpoint...")
        response = requests.get(f"{base_url}/api/v1/stats", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total searches: {data.get('total_searches')}")
            print(f"   Uptime: {data.get('uptime_seconds'):.2f}s")
        print()
        
        print("✅ Basic API tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        print("   Make sure the server is running: python start_api.py")
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out")
        print("   Server might still be initializing")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_api()