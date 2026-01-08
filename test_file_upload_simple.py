#!/usr/bin/env python3
"""
Test script to check file upload with a simple text file.
"""

import requests
import base64
import io

def test_simple_file_upload():
    """Test file upload with a simple text file."""
    
    # API base URL
    base_url = "http://localhost:8000"
    
    # Authentication
    credentials = base64.b64encode(b"admin:admin123").decode('ascii')
    headers = {
        'Authorization': f'Basic {credentials}'
    }
    
    # Create a simple text file in memory
    file_content = b"This is a test file content"
    file_obj = io.BytesIO(file_content)
    
    print("=== Testing /upload/validate with simple text file ===")
    try:
        files = {
            'file': ('test.txt', file_obj, 'text/plain')
        }
        
        response = requests.post(
            f"{base_url}/upload/validate",
            headers=headers,
            files=files,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 400:
            print("✅ Expected error for non-Excel file")
        elif response.status_code == 500:
            print("❌ Internal server error - need to check logs")
        else:
            print(f"❓ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_file_upload()