#!/usr/bin/env python3
"""
Test script to validate the upload API endpoints.
"""

import requests
import base64
from pathlib import Path

def test_upload_api():
    """Test the upload API endpoints."""
    
    # API base URL
    base_url = "http://localhost:8000"
    
    # Authentication
    credentials = base64.b64encode(b"admin:admin123").decode('ascii')
    headers = {
        'Authorization': f'Basic {credentials}'
    }
    
    # Test file
    file_path = Path("GUOO-Manifest--777Bags.xlsx")
    
    if not file_path.exists():
        print(f"Error: Test file {file_path} not found")
        return False
    
    print(f"Testing upload API with file: {file_path}")
    print(f"File size: {file_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Test validation endpoint
    print("\n=== Testing /upload/validate endpoint ===")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            
            response = requests.post(
                f"{base_url}/upload/validate",
                headers=headers,
                files=files,
                timeout=30
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Validation successful!")
            print(f"Valid: {result.get('is_valid')}")
            print(f"Total rows: {result.get('total_rows')}")
            print(f"Rows with descriptions: {result.get('rows_with_descriptions')}")
            print(f"Rows with existing codes: {result.get('rows_with_existing_codes')}")
            return True
        else:
            print(f"❌ Validation failed!")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False

if __name__ == "__main__":
    success = test_upload_api()
    if not success:
        exit(1)