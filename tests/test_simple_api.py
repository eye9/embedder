#!/usr/bin/env python3
"""
Test script to check basic API endpoints.
"""

import requests
import base64

def test_simple_endpoints():
    """Test simple API endpoints."""
    
    # API base URL
    base_url = "http://localhost:8000"
    
    # Authentication
    credentials = base64.b64encode(b"admin:admin123").decode('ascii')
    headers = {
        'Authorization': f'Basic {credentials}'
    }
    
    # Test health endpoint
    print("=== Testing /health endpoint ===")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Health check successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error during health check: {e}")
    
    # Test root endpoint
    print("\n=== Testing / endpoint ===")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Root endpoint successful!")
        else:
            print(f"❌ Root endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Error during root endpoint test: {e}")

if __name__ == "__main__":
    test_simple_endpoints()