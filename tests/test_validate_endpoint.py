#!/usr/bin/env python3
"""
Test script to check validate endpoint availability.
"""

import requests
import base64

def test_validate_endpoint():
    """Test validate endpoint availability."""
    
    # API base URL
    base_url = "http://localhost:8000"
    
    # Authentication
    credentials = base64.b64encode(b"admin:admin123").decode('ascii')
    headers = {
        'Authorization': f'Basic {credentials}'
    }
    
    # Test GET request to validate endpoint (should return 405 Method Not Allowed)
    print("=== Testing GET /upload/validate endpoint ===")
    try:
        response = requests.get(f"{base_url}/upload/validate", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 405:
            print("✅ Endpoint exists (Method Not Allowed is expected for GET)")
        else:
            print(f"❌ Unexpected response")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test POST without file (should return 422 Validation Error)
    print("\n=== Testing POST /upload/validate without file ===")
    try:
        response = requests.post(f"{base_url}/upload/validate", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 422:
            print("✅ Endpoint exists (Validation Error is expected without file)")
        else:
            print(f"❌ Unexpected response")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_validate_endpoint()