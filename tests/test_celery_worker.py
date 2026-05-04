#!/usr/bin/env python3
"""
Test Celery worker task execution to find recursion.
"""

import sys
import traceback
from pathlib import Path
from collections import defaultdict

call_counts = defaultdict(int)
call_stack = []
recursion_point = None

def trace_calls(frame, event, arg):
    """Trace function calls."""
    global call_stack, recursion_point
    
    if event == 'call':
        filename = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        lineno = frame.f_lineno
        
        key = f"{Path(filename).name}:{func_name}:{lineno}"
        call_counts[key] += 1
        call_stack.append(key)
        
        depth = len(call_stack)
        
        # Print every 20 calls to see progress
        if depth % 20 == 0:
            print(f"   [Depth {depth}] {key}")
        
        # Check for recursion
        if depth > 100:
            if not recursion_point:
                recursion_point = {
                    'key': key,
                    'depth': depth,
                    'stack': call_stack.copy()
                }
            print(f"\n🚨 Deep call stack at depth {depth}!")
            print(f"   Current: {key}")
            raise RecursionError(f"Detected deep recursion at {key}")
    
    elif event == 'return':
        if call_stack:
            call_stack.pop()
    
    return trace_calls

def test_celery_task_direct():
    """Test Celery task execution directly."""
    print("\n🔍 Testing Celery task execution directly...")
    
    # Import the task
    from batch_processor.workers.processing_task import process_excel_file, process_file_sync
    from batch_processor.workers.celery_app import celery_app
    
    print("   ✅ Imports successful")
    
    # Test parameters
    session_id = "test-session-123"
    file_path = "GUOO-Manifest--777Bags.xlsx"
    process_mode = "empty_only"
    algorithm = "similarity_top1"
    user = "test_user"
    
    if not Path(file_path).exists():
        print(f"   ❌ Test file not found: {file_path}")
        return False
    
    print(f"   Session: {session_id}")
    print(f"   File: {file_path}")
    print(f"   Mode: {process_mode}")
    print(f"   Algorithm: {algorithm}")
    
    # Enable tracing
    sys.setrecursionlimit(150)
    sys.settrace(trace_calls)
    
    try:
        print("\n   Calling process_file_sync directly...")
        result = process_file_sync(
            session_id=session_id,
            file_path=file_path,
            process_mode=process_mode,
            algorithm=algorithm,
            user=user
        )
        
        print(f"\n   ✅ Result: {result.get('status')}")
        if result.get('status') == 'failed':
            print(f"   Error: {result.get('error')}")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR: {e}")
        
        if recursion_point:
            print(f"\n📍 Recursion detected at:")
            print(f"   {recursion_point['key']}")
            print(f"   Depth: {recursion_point['depth']}")
            print(f"\n📋 Call stack (last 30):")
            for i, c in enumerate(recursion_point['stack'][-30:]):
                print(f"   {i}: {c}")
        
        print(f"\n📊 Most called functions:")
        for func, count in sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            if count > 3:
                print(f"   {func}: {count} times")
        
        raise
        
    finally:
        sys.settrace(None)
        sys.setrecursionlimit(1000)

def test_celery_task_apply():
    """Test Celery task with apply (synchronous execution)."""
    print("\n🔍 Testing Celery task with apply()...")
    
    from batch_processor.workers.processing_task import process_excel_file
    from batch_processor.workers.celery_app import celery_app
    
    print("   ✅ Imports successful")
    
    # Test parameters
    session_id = "test-session-apply"
    file_path = "GUOO-Manifest--777Bags.xlsx"
    process_mode = "empty_only"
    algorithm = "similarity_top1"
    user = "test_user"
    
    if not Path(file_path).exists():
        print(f"   ❌ Test file not found: {file_path}")
        return False
    
    # Enable tracing
    sys.setrecursionlimit(150)
    sys.settrace(trace_calls)
    
    try:
        print("\n   Calling task.apply()...")
        
        # Use apply() to run task synchronously in current process
        result = process_excel_file.apply(
            args=[session_id, file_path, process_mode, algorithm, user]
        )
        
        print(f"\n   Task state: {result.state}")
        print(f"   Task result: {result.result}")
        
        if result.state == 'FAILURE':
            print(f"   Error: {result.result}")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in task.apply(): {e}")
        
        if recursion_point:
            print(f"\n📍 Recursion detected at:")
            print(f"   {recursion_point['key']}")
            print(f"\n📋 Call stack (last 30):")
            for i, c in enumerate(recursion_point['stack'][-30:]):
                print(f"   {i}: {c}")
        
        raise
        
    finally:
        sys.settrace(None)
        sys.setrecursionlimit(1000)

def main():
    """Main test function."""
    print("🐛 Celery Worker Recursion Test")
    print("=" * 60)
    
    global call_counts, call_stack, recursion_point
    
    tests = [
        ("Direct process_file_sync", test_celery_task_direct),
        ("Celery task.apply()", test_celery_task_apply),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"📋 Running: {test_name}")
        print("=" * 60)
        
        # Reset tracking
        call_counts = defaultdict(int)
        call_stack = []
        recursion_point = None
        
        try:
            test_func()
            print(f"\n✅ {test_name}: COMPLETED")
        except RecursionError as e:
            print(f"\n🚨 {test_name}: RECURSION ERROR!")
            break
        except Exception as e:
            print(f"\n❌ {test_name}: ERROR - {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Celery worker test complete")

if __name__ == "__main__":
    main()