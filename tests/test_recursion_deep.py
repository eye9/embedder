#!/usr/bin/env python3
"""
Deep recursion debugging - traces every function call to find exact recursion point.
"""

import sys
import traceback
import functools
import threading
from pathlib import Path
from collections import defaultdict

# Track call depth per function
call_stack = []
call_counts = defaultdict(int)
max_depth = 0
recursion_detected = False
recursion_location = None

def trace_calls(frame, event, arg):
    """Trace all function calls to detect recursion."""
    global max_depth, recursion_detected, recursion_location
    
    if event == 'call':
        filename = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        lineno = frame.f_lineno
        
        # Only trace our code and key libraries
        if any(x in filename for x in ['batch_processor', 'services', 'models']):
            key = f"{Path(filename).name}:{func_name}"
            call_stack.append(key)
            call_counts[key] += 1
            
            current_depth = len(call_stack)
            if current_depth > max_depth:
                max_depth = current_depth
            
            # Detect recursion (same function called more than 10 times in stack)
            stack_count = call_stack.count(key)
            if stack_count > 10 and not recursion_detected:
                recursion_detected = True
                recursion_location = {
                    'file': filename,
                    'function': func_name,
                    'line': lineno,
                    'stack_depth': current_depth,
                    'stack': call_stack.copy()
                }
                print(f"\n🚨 RECURSION DETECTED at depth {current_depth}!")
                print(f"   File: {filename}")
                print(f"   Function: {func_name}")
                print(f"   Line: {lineno}")
                print(f"   Stack count for this function: {stack_count}")
            
            if current_depth % 50 == 0:
                print(f"   [Depth: {current_depth}] {key}")
    
    elif event == 'return':
        filename = frame.f_code.co_filename
        if any(x in filename for x in ['batch_processor', 'services', 'models']):
            if call_stack:
                call_stack.pop()
    
    return trace_calls

def test_with_tracing(test_func):
    """Decorator to run test with call tracing."""
    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        global call_stack, call_counts, max_depth, recursion_detected, recursion_location
        call_stack = []
        call_counts = defaultdict(int)
        max_depth = 0
        recursion_detected = False
        recursion_location = None
        
        sys.setrecursionlimit(200)  # Lower limit to catch recursion faster
        sys.settrace(trace_calls)
        
        try:
            result = test_func(*args, **kwargs)
            return result
        finally:
            sys.settrace(None)
            sys.setrecursionlimit(1000)
            
            print(f"\n📊 Call Statistics:")
            print(f"   Max depth reached: {max_depth}")
            print(f"   Recursion detected: {recursion_detected}")
            
            if recursion_location:
                print(f"\n🔍 Recursion Location:")
                print(f"   {recursion_location['file']}:{recursion_location['function']}:{recursion_location['line']}")
                print(f"\n📋 Call Stack at recursion point:")
                for i, call in enumerate(recursion_location['stack'][-30:]):
                    print(f"   {i}: {call}")
            
            # Show most called functions
            print(f"\n📈 Most called functions:")
            for func, count in sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                if count > 1:
                    print(f"   {func}: {count} times")
    
    return wrapper

@test_with_tracing
def test_celery_task_creation():
    """Test Celery task creation which might cause recursion."""
    print("\n🔍 Testing Celery task creation...")
    
    from batch_processor.workers.celery_app import celery_app
    print("✅ Celery app imported")
    
    # Try to send a task
    try:
        result = celery_app.send_task(
            'batch_processor.workers.processing_task.process_excel_file',
            args=['test_session', 'test_file.xlsx', 'empty_only', 'similarity_top1', 'test_user']
        )
        print(f"✅ Task created: {result.id}")
    except Exception as e:
        print(f"❌ Task creation failed: {e}")

@test_with_tracing  
def test_upload_endpoint_simulation():
    """Simulate what happens in upload endpoint."""
    print("\n🔍 Simulating upload endpoint...")
    
    import uuid
    from pathlib import Path
    
    # Import modules one by one
    print("   Importing config...")
    from batch_processor.config.settings import get_config, ProcessingMode, AlgorithmType
    print("   ✅ Config imported")
    
    print("   Importing excel_processor...")
    from batch_processor.services.excel_processor import ExcelProcessor
    print("   ✅ ExcelProcessor imported")
    
    print("   Importing file_manager...")
    from batch_processor.services.file_manager import FileManager
    print("   ✅ FileManager imported")
    
    print("   Importing celery_app...")
    from batch_processor.workers.celery_app import celery_app
    print("   ✅ Celery app imported")
    
    print("   Importing processing_task...")
    from batch_processor.workers.processing_task import process_file_sync
    print("   ✅ processing_task imported")
    
    # Initialize services
    print("   Initializing ExcelProcessor...")
    excel_processor = ExcelProcessor()
    print("   ✅ ExcelProcessor initialized")
    
    print("   Initializing FileManager...")
    file_manager = FileManager()
    print("   ✅ FileManager initialized")
    
    # Simulate file upload
    session_id = str(uuid.uuid4())
    file_path = "GUOO-Manifest--777Bags.xlsx"
    
    if not Path(file_path).exists():
        print(f"   ❌ Test file not found: {file_path}")
        return False
    
    print(f"   Session: {session_id}")
    print(f"   File: {file_path}")
    
    # Try to create Celery task
    print("   Creating Celery task...")
    try:
        task_result = celery_app.send_task(
            'batch_processor.workers.processing_task.process_excel_file',
            args=[session_id, file_path, 'empty_only', 'similarity_top1', 'test_user']
        )
        print(f"   ✅ Task created: {task_result.id}")
        
        # Check task state
        print(f"   Task state: {task_result.state}")
        print(f"   Task info: {task_result.info}")
        
    except Exception as e:
        print(f"   ❌ Celery task failed: {e}")
        print("   Falling back to synchronous processing...")
        
        # This is where recursion might happen
        print("   Calling process_file_sync...")
        result = process_file_sync(
            session_id=session_id,
            file_path=file_path,
            process_mode='empty_only',
            algorithm='similarity_top1',
            user='test_user'
        )
        print(f"   ✅ Sync processing result: {result.get('status')}")
    
    return True

@test_with_tracing
def test_task_status_check():
    """Test task status checking which might cause recursion."""
    print("\n🔍 Testing task status check...")
    
    from batch_processor.web.tasks import get_task_status, get_task_result, parse_task_meta
    from celery.result import AsyncResult
    
    # Create a fake task ID
    fake_task_id = "test-task-12345"
    
    print(f"   Checking status for task: {fake_task_id}")
    
    # Get task result
    task_result = get_task_result(fake_task_id)
    print(f"   Task state: {task_result.state}")
    
    # Parse metadata
    info = task_result.info or {}
    if isinstance(info, Exception):
        info = {"error": str(info)}
    elif not isinstance(info, dict):
        info = {"error": str(info)}
    
    meta = parse_task_meta(info)
    print(f"   Parsed meta: {meta}")
    
    return True

@test_with_tracing
def test_sync_result_storage():
    """Test sync result storage which might cause recursion."""
    print("\n🔍 Testing sync result storage...")
    
    from batch_processor.web.upload import _store_sync_result, _get_sync_result
    
    test_result = {
        "status": "completed",
        "output_file": "/path/to/file.xlsx",
        "processed_rows": 100,
        "total_rows": 1000,
        "error_count": 0
    }
    
    task_id = "test-sync-task"
    
    print(f"   Storing result for task: {task_id}")
    _store_sync_result(task_id, test_result)
    print("   ✅ Result stored")
    
    print(f"   Retrieving result...")
    retrieved = _get_sync_result(task_id)
    print(f"   ✅ Result retrieved: {retrieved.get('status')}")
    
    return True

def main():
    """Run all deep recursion tests."""
    print("🐛 Deep Recursion Debugging")
    print("=" * 60)
    
    tests = [
        ("Sync Result Storage", test_sync_result_storage),
        ("Task Status Check", test_task_status_check),
        ("Celery Task Creation", test_celery_task_creation),
        ("Upload Endpoint Simulation", test_upload_endpoint_simulation),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"📋 Running: {test_name}")
        print("=" * 60)
        
        try:
            test_func()
            print(f"\n✅ {test_name}: COMPLETED")
        except RecursionError as e:
            print(f"\n🚨 {test_name}: RECURSION ERROR!")
            print(f"   Error: {e}")
            traceback.print_exc()
            break
        except Exception as e:
            print(f"\n❌ {test_name}: ERROR - {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Deep recursion debugging complete")

if __name__ == "__main__":
    main()