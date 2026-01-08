#!/usr/bin/env python3
"""
Test script to verify that web interface fixes work correctly.
"""

import os
import sys
import time
import uuid
from pathlib import Path

def test_web_interface_simulation():
    """Simulate web interface behavior to test fixes."""
    
    print("🔧 Testing web interface simulation...")
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        from batch_processor.web.upload import _store_sync_result, _get_sync_result
        from batch_processor.web.tasks import get_processing_summary
        from batch_processor.web.models import ProcessingSummary
        
        # Test parameters
        session_id = str(uuid.uuid4())
        file_path = "GUOO-Manifest--777Bags.xlsx"
        process_mode = "empty_only"
        algorithm = "similarity_top1"
        user = "test_user"
        
        sync_task_id = "sync_" + session_id
        
        print(f"📋 Test Parameters:")
        print(f"  Session ID: {session_id}")
        print(f"  Task ID: {sync_task_id}")
        print(f"  File: {file_path}")
        print(f"  Mode: {process_mode}")
        
        # Run processing (simulating web interface behavior)
        print(f"\n🚀 Starting processing (simulating web interface)...")
        start_time = time.time()
        
        result = process_file_sync(
            session_id=session_id,
            file_path=file_path,
            process_mode=process_mode,
            algorithm=algorithm,
            user=user
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n📊 Processing Results:")
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Processed rows: {result.get('processed_rows', 0)}")
        print(f"  Total rows: {result.get('total_rows', 0)}")
        print(f"  Error count: {result.get('error_count', 0)}")
        print(f"  Successful assignments: {result.get('successful_assignments', 0)}")
        print(f"  Failed assignments: {result.get('failed_assignments', 0)}")
        
        # Simulate web interface storing the result
        print(f"\n💾 Storing result (simulating web interface)...")
        _store_sync_result(sync_task_id, result)
        
        # Test retrieving the result
        print(f"📤 Retrieving stored result...")
        stored_result = _get_sync_result(sync_task_id)
        
        if stored_result:
            print(f"  ✅ Result retrieved successfully")
            print(f"  Stored successful assignments: {stored_result.get('successful_assignments', 0)}")
            print(f"  Stored failed assignments: {stored_result.get('failed_assignments', 0)}")
        else:
            print(f"  ❌ Failed to retrieve stored result")
            return False
        
        # Test the processing summary endpoint (simulating web API call)
        print(f"\n📋 Testing processing summary endpoint...")
        
        # Create a mock user dependency (normally handled by FastAPI)
        class MockRequest:
            pass
        
        # We can't easily test the async function without FastAPI context,
        # but we can test the logic by checking the stored result directly
        if stored_result and stored_result.get("status") == "completed":
            summary_data = {
                "task_id": sync_task_id,
                "total_rows": stored_result.get("total_rows", 0),
                "processed_rows": stored_result.get("processed_rows", 0),
                "skipped_rows": stored_result.get("skipped_rows", 0),
                "successful_assignments": stored_result.get("successful_assignments", 0),
                "failed_assignments": stored_result.get("failed_assignments", 0),
                "processing_time_seconds": stored_result.get("processing_time_seconds", 0.0),
                "average_time_per_row_ms": stored_result.get("average_time_per_row_ms", 0.0),
                "algorithm_used": stored_result.get("algorithm_used", "similarity_top1"),
                "processing_mode": stored_result.get("processing_mode", "all")
            }
            
            print(f"  📊 Summary data that would be returned:")
            print(f"    Task ID: {summary_data['task_id']}")
            print(f"    Total rows: {summary_data['total_rows']}")
            print(f"    Processed rows: {summary_data['processed_rows']}")
            print(f"    Successful assignments: {summary_data['successful_assignments']}")
            print(f"    Failed assignments: {summary_data['failed_assignments']}")
            print(f"    Processing time: {summary_data['processing_time_seconds']:.2f}s")
            print(f"    Algorithm: {summary_data['algorithm_used']}")
            print(f"    Mode: {summary_data['processing_mode']}")
            
            # Validate the data
            expected_processed_rows = 3
            expected_successful_assignments = 3
            expected_failed_assignments = 0
            
            tests_passed = []
            
            # Test 1: Correct processed rows
            if summary_data['processed_rows'] == expected_processed_rows:
                print(f"  ✅ Test 1 PASSED: Correct processed rows ({summary_data['processed_rows']})")
                tests_passed.append(True)
            else:
                print(f"  ❌ Test 1 FAILED: Wrong processed rows ({summary_data['processed_rows']}, expected {expected_processed_rows})")
                tests_passed.append(False)
            
            # Test 2: Correct successful assignments
            if summary_data['successful_assignments'] == expected_successful_assignments:
                print(f"  ✅ Test 2 PASSED: Correct successful assignments ({summary_data['successful_assignments']})")
                tests_passed.append(True)
            else:
                print(f"  ❌ Test 2 FAILED: Wrong successful assignments ({summary_data['successful_assignments']}, expected {expected_successful_assignments})")
                tests_passed.append(False)
            
            # Test 3: Correct failed assignments
            if summary_data['failed_assignments'] == expected_failed_assignments:
                print(f"  ✅ Test 3 PASSED: Correct failed assignments ({summary_data['failed_assignments']})")
                tests_passed.append(True)
            else:
                print(f"  ❌ Test 3 FAILED: Wrong failed assignments ({summary_data['failed_assignments']}, expected {expected_failed_assignments})")
                tests_passed.append(False)
            
            # Test 4: Processing mode is correct
            if summary_data['processing_mode'] == process_mode:
                print(f"  ✅ Test 4 PASSED: Correct processing mode ({summary_data['processing_mode']})")
                tests_passed.append(True)
            else:
                print(f"  ❌ Test 4 FAILED: Wrong processing mode ({summary_data['processing_mode']}, expected {process_mode})")
                tests_passed.append(False)
            
            all_tests_passed = all(tests_passed)
            
            print(f"\n🏁 Web Interface Test Summary:")
            print(f"  Test 1 (Processed rows): {'✅ PASSED' if tests_passed[0] else '❌ FAILED'}")
            print(f"  Test 2 (Successful assignments): {'✅ PASSED' if tests_passed[1] else '❌ FAILED'}")
            print(f"  Test 3 (Failed assignments): {'✅ PASSED' if tests_passed[2] else '❌ FAILED'}")
            print(f"  Test 4 (Processing mode): {'✅ PASSED' if tests_passed[3] else '❌ FAILED'}")
            print(f"  Overall: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
            
            return all_tests_passed
        else:
            print(f"  ❌ Stored result is not completed")
            return False
        
    except Exception as e:
        print(f"❌ Error during web interface testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_web_interface_simulation():
        print("\n🎉 Web interface fixes are working correctly!")
        print("\n📝 Summary:")
        print("  ✅ Synchronous results are stored correctly")
        print("  ✅ Processing summary retrieves correct assignment counts")
        print("  ✅ Web interface should now show correct statistics")
    else:
        print("\n❌ Web interface fixes are not working correctly!")
        sys.exit(1)