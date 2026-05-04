#!/usr/bin/env python3
"""
Test HTTP request handling to find recursion in FastAPI/Starlette.
"""

import sys
import traceback
import asyncio
from pathlib import Path
from collections import defaultdict

# Track calls
call_counts = defaultdict(int)
call_stack = []

def trace_calls(frame, event, arg):
    """Trace function calls."""
    global call_stack
    
    if event == 'call':
        filename = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        lineno = frame.f_lineno
        
        key = f"{Path(filename).name}:{func_name}:{lineno}"
        call_counts[key] += 1
        call_stack.append(key)
        
        # Check for recursion
        if len(call_stack) > 150:
            print(f"\n🚨 Deep call stack detected at depth {len(call_stack)}!")
            print(f"   Current: {key}")
            print(f"   Last 20 calls:")
            for i, c in enumerate(call_stack[-20:]):
                print(f"   {i}: {c}")
            raise RecursionError(f"Detected deep recursion at {key}")
    
    elif event == 'return':
        if call_stack:
            call_stack.pop()
    
    return trace_calls

async def test_fastapi_app():
    """Test FastAPI app directly."""
    print("\n🔍 Testing FastAPI app directly...")
    
    from fastapi.testclient import TestClient
    from batch_processor.web.app import create_app
    
    print("   Creating app...")
    app = create_app()
    print("   ✅ App created")
    
    print("   Creating test client...")
    client = TestClient(app)
    print("   ✅ Test client created")
    
    # Test health endpoint
    print("   Testing /health endpoint...")
    response = client.get("/health")
    print(f"   ✅ Health response: {response.status_code}")
    
    # Test file upload with auth
    print("   Testing /upload/validate endpoint...")
    
    file_path = "GUOO-Manifest--777Bags.xlsx"
    if not Path(file_path).exists():
        print(f"   ❌ Test file not found: {file_path}")
        return False
    
    with open(file_path, "rb") as f:
        files = {"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post(
            "/upload/validate",
            files=files,
            auth=("admin", "admin123")
        )
    
    print(f"   ✅ Validate response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total rows: {data.get('total_rows')}")
    
    # Test file processing
    print("   Testing /upload/ endpoint (processing)...")
    
    # Enable tracing for this critical part
    sys.setrecursionlimit(200)
    sys.settrace(trace_calls)
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {
                "process_mode": "empty_only",
                "algorithm": "similarity_top1"
            }
            response = client.post(
                "/upload/",
                files=files,
                data=data,
                auth=("admin", "admin123")
            )
        
        print(f"   ✅ Upload response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Task ID: {result.get('task_id')}")
            print(f"   Message: {result.get('message')}")
            
            # Check task status
            task_id = result.get('task_id')
            if task_id:
                print(f"   Checking task status...")
                status_response = client.get(
                    f"/task/{task_id}/status",
                    auth=("admin", "admin123")
                )
                print(f"   Status response: {status_response.status_code}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Task status: {status_data.get('status')}")
                    print(f"   Error message: {status_data.get('error_message')}")
        else:
            print(f"   ❌ Upload failed: {response.text}")
            
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR: {e}")
        print(f"\n📊 Most called functions:")
        for func, count in sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            if count > 5:
                print(f"   {func}: {count} times")
        raise
    finally:
        sys.settrace(None)
        sys.setrecursionlimit(1000)
    
    return True

def main():
    """Main test function."""
    print("🐛 HTTP Recursion Test")
    print("=" * 60)
    
    try:
        asyncio.run(test_fastapi_app())
        print("\n✅ All HTTP tests passed!")
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR DETECTED!")
        print(f"Error: {e}")
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())