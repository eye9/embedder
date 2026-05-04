#!/usr/bin/env python3
"""
Test script to verify that Celery task progress updates work correctly.
"""

import os
import sys
import time
import uuid
from pathlib import Path

def test_celery_task_progress():
    """Test Celery task progress updates."""
    
    print("🔧 Testing Celery task progress updates...")
    
    try:
        from batch_processor.workers.processing_task import process_excel_file
        from batch_processor.workers.celery_app import celery_app
        
        # Test parameters
        session_id = str(uuid.uuid4())
        file_path = "GUOO-Manifest--777Bags.xlsx"
        process_mode = "empty_only"
        algorithm = "similarity_top1"
        user = "test_user"
        
        print(f"📋 Test Parameters:")
        print(f"  Session ID: {session_id}")
        print(f"  File: {file_path}")
        print(f"  Mode: {process_mode}")
        print(f"  Algorithm: {algorithm}")
        
        # Create a mock Celery task context
        class MockCeleryTask:
            def __init__(self):
                self.id = f"celery_task_{int(time.time())}"
                self.state_updates = []
            
            def update_state(self, state, meta):
                """Mock update_state method to capture progress updates."""
                self.state_updates.append({
                    'timestamp': time.time(),
                    'state': state,
                    'meta': meta.copy()
                })
                print(f"  📊 Celery State Update: {state} - {meta.get('progress', 0):.1%} "
                      f"({meta.get('processed_rows', 0)}/{meta.get('total_rows', 0)}) - {meta.get('message', '')}")
        
        # Create mock task
        mock_task = MockCeleryTask()
        
        # Test the process_file_sync function with Celery task context
        print(f"\n🚀 Starting processing with Celery task context...")
        start_time = time.time()
        
        from batch_processor.workers.processing_task import process_file_sync
        
        result = process_file_sync(
            session_id=session_id,
            file_path=file_path,
            process_mode=process_mode,
            algorithm=algorithm,
            user=user,
            celery_task=mock_task
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
        
        # Analyze Celery state updates
        print(f"\n📈 Celery State Updates Analysis:")
        print(f"  Total state updates: {len(mock_task.state_updates)}")
        
        if mock_task.state_updates:
            # Check for different types of updates
            initial_updates = [u for u in mock_task.state_updates if u['meta'].get('progress', 0) == 0.0]
            validation_updates = [u for u in mock_task.state_updates if u['meta'].get('progress', 0) == 0.05]
            processing_updates = [u for u in mock_task.state_updates if 0.05 < u['meta'].get('progress', 0) < 1.0]
            
            print(f"  Initial updates (0%): {len(initial_updates)}")
            print(f"  Validation updates (5%): {len(validation_updates)}")
            print(f"  Processing updates (5%-100%): {len(processing_updates)}")
            
            # Show sample updates
            print(f"  📊 Sample state updates:")
            for i, update in enumerate(mock_task.state_updates[:5]):  # Show first 5
                meta = update['meta']
                print(f"    {i+1}. {update['state']} - {meta.get('progress', 0):.1%} "
                      f"({meta.get('processed_rows', 0)}/{meta.get('total_rows', 0)}) - {meta.get('message', '')[:50]}...")
            
            if len(mock_task.state_updates) > 5:
                print(f"    ... and {len(mock_task.state_updates) - 5} more updates")
        
        # Test results
        tests_passed = []
        
        # Test 1: Processing completed successfully
        if result.get('status') == 'completed':
            print(f"\n✅ Test 1 PASSED: Processing completed successfully")
            tests_passed.append(True)
        else:
            print(f"\n❌ Test 1 FAILED: Processing did not complete successfully")
            tests_passed.append(False)
        
        # Test 2: Celery state updates were generated
        if len(mock_task.state_updates) > 0:
            print(f"✅ Test 2 PASSED: Celery state updates were generated ({len(mock_task.state_updates)} updates)")
            tests_passed.append(True)
        else:
            print(f"❌ Test 2 FAILED: No Celery state updates were generated")
            tests_passed.append(False)
        
        # Test 3: Progress updates show progression
        if mock_task.state_updates:
            progress_values = [u['meta'].get('progress', 0) for u in mock_task.state_updates]
            min_progress = min(progress_values)
            max_progress = max(progress_values)
            
            if min_progress == 0.0 and max_progress > 0.0:
                print(f"✅ Test 3 PASSED: Progress shows progression (0% to {max_progress:.1%})")
                tests_passed.append(True)
            else:
                print(f"❌ Test 3 FAILED: Progress doesn't show proper progression ({min_progress:.1%} to {max_progress:.1%})")
                tests_passed.append(False)
        else:
            print(f"❌ Test 3 FAILED: No progress data to analyze")
            tests_passed.append(False)
        
        # Test 4: Assignment counts are correct
        expected_successful = 3
        expected_failed = 0
        actual_successful = result.get('successful_assignments', 0)
        actual_failed = result.get('failed_assignments', 0)
        
        if actual_successful == expected_successful and actual_failed == expected_failed:
            print(f"✅ Test 4 PASSED: Assignment counts are correct ({actual_successful} successful, {actual_failed} failed)")
            tests_passed.append(True)
        else:
            print(f"❌ Test 4 FAILED: Assignment counts are wrong ({actual_successful} successful, {actual_failed} failed)")
            tests_passed.append(False)
        
        # Overall result
        all_tests_passed = all(tests_passed)
        
        print(f"\n🏁 Celery Progress Test Summary:")
        print(f"  Test 1 (Processing completed): {'✅ PASSED' if tests_passed[0] else '❌ FAILED'}")
        print(f"  Test 2 (State updates generated): {'✅ PASSED' if tests_passed[1] else '❌ FAILED'}")
        print(f"  Test 3 (Progress progression): {'✅ PASSED' if tests_passed[2] else '❌ FAILED'}")
        print(f"  Test 4 (Assignment counts): {'✅ PASSED' if tests_passed[3] else '❌ FAILED'}")
        print(f"  Overall: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Error during Celery progress testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_celery_task_progress():
        print("\n🎉 Celery progress fixes are working correctly!")
        print("\n📝 Summary:")
        print("  ✅ Celery task state updates are generated")
        print("  ✅ Progress shows proper progression from 0% to completion")
        print("  ✅ Assignment counts are included in results")
        print("  ✅ Web interface should now show real-time progress")
    else:
        print("\n❌ Celery progress fixes are not working correctly!")
        sys.exit(1)