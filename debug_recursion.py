#!/usr/bin/env python3
"""
Debug script to catch and analyze recursion errors in real-time.
"""

import sys
import traceback
import threading
import time
from pathlib import Path

# Set recursion limit to catch errors earlier
sys.setrecursionlimit(500)

def trace_calls(frame, event, arg):
    """Trace function calls to detect recursion patterns."""
    if event == 'call':
        filename = frame.f_code.co_filename
        function_name = frame.f_code.co_name
        
        # Only trace our batch_processor modules
        if 'batch_processor' in filename:
            print(f"CALL: {Path(filename).name}:{function_name}:{frame.f_lineno}")
    
    return trace_calls

def test_file_upload_with_tracing():
    """Test file upload with call tracing enabled."""
    print("🔍 Testing file upload with recursion tracing...")
    
    try:
        # Enable call tracing
        sys.settrace(trace_calls)
        
        import requests
        import json
        
        # Test file upload
        url = "http://localhost:8000/upload/validate"
        
        with open("GUOO-Manifest--777Bags.xlsx", "rb") as f:
            files = {"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            
            print("📤 Uploading file...")
            response = requests.post(url, files=files, auth=("admin", "admin123"))
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Upload successful!")
                print(f"Response: {response.json()}")
            else:
                print(f"❌ Upload failed: {response.text}")
                
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR DETECTED!")
        print(f"Error: {e}")
        print("\n📋 Full traceback:")
        traceback.print_exc()
        
        # Print call stack
        print("\n📊 Call stack analysis:")
        tb = traceback.extract_tb(e.__traceback__)
        call_counts = {}
        
        for frame in tb:
            key = f"{Path(frame.filename).name}:{frame.name}"
            call_counts[key] = call_counts.get(key, 0) + 1
        
        print("Most frequent calls:")
        for call, count in sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            if count > 1:
                print(f"  {call}: {count} times")
                
    except Exception as e:
        print(f"❌ Other error: {e}")
        traceback.print_exc()
    finally:
        # Disable tracing
        sys.settrace(None)

def test_processing_with_monitoring():
    """Test file processing with detailed monitoring."""
    print("🔍 Testing file processing with monitoring...")
    
    try:
        import requests
        import json
        import time
        
        # First upload and validate
        url_validate = "http://localhost:8000/upload/validate"
        
        with open("GUOO-Manifest--777Bags.xlsx", "rb") as f:
            files = {"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            
            print("📤 Validating file...")
            response = requests.post(url_validate, files=files, auth=("admin", "admin123"))
            
            if response.status_code != 200:
                print(f"❌ Validation failed: {response.text}")
                return
            
            print("✅ Validation successful!")
        
        # Now try processing
        url_process = "http://localhost:8000/upload/process"
        
        with open("GUOO-Manifest--777Bags.xlsx", "rb") as f:
            files = {"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {
                "process_mode": "empty_only",
                "algorithm": "similarity_top1"
            }
            
            print("🔄 Starting processing...")
            response = requests.post(url_process, files=files, data=data, auth=("admin", "admin123"))
            
            print(f"Process Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Processing started: {result}")
                
                # Monitor task status
                if "task_id" in result:
                    task_id = result["task_id"]
                    print(f"📊 Monitoring task: {task_id}")
                    
                    for i in range(10):  # Check status 10 times
                        time.sleep(2)
                        status_url = f"http://localhost:8000/task/{task_id}/status"
                        status_response = requests.get(status_url, auth=("admin", "admin123"))
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"Status {i+1}: {status_data.get('status', 'unknown')} - {status_data.get('progress', 0):.1%}")
                            
                            if status_data.get('status') in ['completed', 'failed']:
                                break
                        else:
                            print(f"❌ Status check failed: {status_response.text}")
                            break
            else:
                print(f"❌ Processing failed: {response.text}")
                
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR DURING PROCESSING!")
        print(f"Error: {e}")
        traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        traceback.print_exc()

def main():
    """Main debug function."""
    print("🐛 Recursion Debug Tool")
    print("=" * 50)
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server returned error")
            return 1
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        print("Please start the server with: python start_batch_web.py")
        return 1
    
    print("\n1️⃣ Testing file upload with tracing...")
    test_file_upload_with_tracing()
    
    print("\n2️⃣ Testing file processing with monitoring...")
    test_processing_with_monitoring()
    
    print("\n✅ Debug complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())