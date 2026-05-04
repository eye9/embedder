#!/usr/bin/env python3
"""
Check specific task error details.
"""

import requests
import json
import sys

def check_task_details(task_id):
    """Get detailed task information."""
    try:
        # Get task status
        status_url = f"http://localhost:8000/task/{task_id}/status"
        response = requests.get(status_url, auth=("admin", "admin123"))
        
        if response.status_code == 200:
            data = response.json()
            print(f"Task Status: {json.dumps(data, indent=2)}")
            
            # Check if there's an error message
            if data.get('error_message'):
                print(f"\n🚨 Error Message: {data['error_message']}")
            
            return data
        else:
            print(f"❌ Failed to get task status: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking task: {e}")
        return None

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python check_task_error.py <task_id>")
        return 1
    
    task_id = sys.argv[1]
    print(f"🔍 Checking task: {task_id}")
    
    result = check_task_details(task_id)
    if result and result.get('status') == 'failed':
        print("\n📋 Task failed. Checking for recursion patterns...")
        error_msg = result.get('error_message', '')
        if 'recursion' in error_msg.lower() or 'maximum' in error_msg.lower():
            print("🚨 RECURSION ERROR DETECTED!")
            print(f"Error: {error_msg}")
        else:
            print(f"Other error: {error_msg}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())