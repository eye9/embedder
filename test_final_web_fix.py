#!/usr/bin/env python3
"""
Final comprehensive test for all web interface fixes:
1. Empty_only mode processes only rows with missing HTS codes
2. Progress tracking works correctly (both Redis and Celery)
3. Successful/failed assignments are counted and displayed correctly
4. Web interface APIs return correct data
"""

import os
import sys
import time
import threading
import uuid
from pathlib import Path

def test_complete_web_solution():
    """Test all web interface fixes together."""
    
    print("🔧 Testing complete web interface solution...")
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        from batch_processor.services.progress_tracker import get_progress_tracker
        from batch_processor.web.upload import _store_sync_result, _get_sync_result
        
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
        print(f"  Algorithm: {algorithm}")
        
        # Expected results
        expected_rows_to_process = [4, 5, 8]
        expected_count = len(expected_rows_to_process)
        
        print(f"  Expected rows to process: {expected_rows_to_process}")
        print(f"  Expected count: {expected_count}")
        
        # Track progress updates (Redis)
        progress_updates = []
        progress_tracker = get_progress_tracker()
        
        def monitor_redis_progress():
            """Monitor Redis progress updates."""
            start_time = time.time()
            while time.time() - start_time < 60:
                progress_update = progress_tracker.get_progress(sync_task_id)
                if progress_update:
                    progress_updates.append({
                        'timestamp': time.time(),
                        'progress': progress_update.progress,
                        'processed_rows': progress_update.processed_rows,
                        'total_rows': progress_update.total_rows,
                        'status': progress_update.status,
                        'message': progress_update.message
                    })
                    
                    if progress_update.status in ['completed', 'failed']:
                        break
                
                time.sleep(0.5)
        
        # Create mock Celery task for state updates
        class MockCeleryTask:
            def __init__(self):
                self.id = f"celery_task_{int(time.time())}"
                self.state_updates = []
            
            def update_state(self, state, meta):
                self.state_updates.append({
                    'timestamp': time.time(),
                    'state': state,
                    'meta': meta.copy()
                })
        
        mock_celery_task = MockCeleryTask()
        
        # Start Redis progress monitoring
        monitor_thread = threading.Thread(target=monitor_redis_progress, daemon=True)
        monitor_thread.start()
        
        # Run processing with both Redis and Celery progress tracking
        print(f"\n🚀 Starting processing with full progress tracking...")
        start_time = time.time()
        
        result = process_file_sync(
            session_id=session_id,
            file_path=file_path,
            process_mode=process_mode,
            algorithm=algorithm,
            user=user,
            celery_task=mock_celery_task
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Wait for monitor thread to finish
        monitor_thread.join(timeout=5)
        
        print(f"\n📊 Processing Results:")
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Processed rows: {result.get('processed_rows', 0)}")
        print(f"  Total rows: {result.get('total_rows', 0)}")
        print(f"  Error count: {result.get('error_count', 0)}")
        print(f"  Successful assignments: {result.get('successful_assignments', 0)}")
        print(f"  Failed assignments: {result.get('failed_assignments', 0)}")
        
        # Store result for web interface
        print(f"\n💾 Storing result for web interface...")
        _store_sync_result(sync_task_id, result)
        
        # Test all components
        tests_passed = []
        
        # Test 1: Correct number of rows processed (empty_only fix)
        processed_rows = result.get('processed_rows', 0)
        if processed_rows == expected_count:
            print(f"\n✅ Test 1 PASSED: Correct number of rows processed ({processed_rows})")
            tests_passed.append(True)
        else:
            print(f"\n❌ Test 1 FAILED: Wrong number of rows processed ({processed_rows}, expected {expected_count})")
            tests_passed.append(False)
        
        # Test 2: Correct rows were processed (empty_only fix)
        output_file = result.get('output_file')
        if output_file and os.path.exists(output_file):
            import pandas as pd
            df_output = pd.read_excel(output_file)
            
            assigned_mask = df_output['TNVED_Code'].notna() & (df_output['TNVED_Code'].astype(str).str.strip() != '')
            assigned_rows = df_output[assigned_mask].index.tolist()
            
            if set(assigned_rows) == set(expected_rows_to_process):
                print(f"✅ Test 2 PASSED: Correct rows were processed ({assigned_rows})")
                tests_passed.append(True)
            else:
                print(f"❌ Test 2 FAILED: Wrong rows were processed ({assigned_rows}, expected {expected_rows_to_process})")
                tests_passed.append(False)
        else:
            print(f"❌ Test 2 FAILED: Output file not found")
            tests_passed.append(False)
        
        # Test 3: Redis progress tracking works
        if progress_updates:
            initial_updates = [u for u in progress_updates if u['progress'] == 0.0]
            final_updates = [u for u in progress_updates if u['progress'] == 1.0 and u['status'] == 'completed']
            
            if initial_updates and final_updates:
                print(f"✅ Test 3 PASSED: Redis progress tracking works ({len(progress_updates)} updates)")
                tests_passed.append(True)
            else:
                print(f"❌ Test 3 FAILED: Redis progress tracking incomplete")
                tests_passed.append(False)
        else:
            print(f"❌ Test 3 FAILED: No Redis progress updates captured")
            tests_passed.append(False)
        
        # Test 4: Celery state updates work
        if len(mock_celery_task.state_updates) > 0:
            progress_values = [u['meta'].get('progress', 0) for u in mock_celery_task.state_updates]
            min_progress = min(progress_values)
            max_progress = max(progress_values)
            
            if min_progress == 0.0 and max_progress >= 1.0:
                print(f"✅ Test 4 PASSED: Celery state updates work ({len(mock_celery_task.state_updates)} updates, 0% to {max_progress:.1%})")
                tests_passed.append(True)
            else:
                print(f"❌ Test 4 FAILED: Celery state updates incomplete ({min_progress:.1%} to {max_progress:.1%})")
                tests_passed.append(False)
        else:
            print(f"❌ Test 4 FAILED: No Celery state updates generated")
            tests_passed.append(False)
        
        # Test 5: Assignment counts are correct
        successful_assignments = result.get('successful_assignments', 0)
        failed_assignments = result.get('failed_assignments', 0)
        
        if successful_assignments == expected_count and failed_assignments == 0:
            print(f"✅ Test 5 PASSED: Assignment counts are correct ({successful_assignments} successful, {failed_assignments} failed)")
            tests_passed.append(True)
        else:
            print(f"❌ Test 5 FAILED: Assignment counts are wrong ({successful_assignments} successful, {failed_assignments} failed)")
            tests_passed.append(False)
        
        # Test 6: Web interface can retrieve correct data
        stored_result = _get_sync_result(sync_task_id)
        if stored_result and stored_result.get('successful_assignments') == expected_count:
            print(f"✅ Test 6 PASSED: Web interface retrieves correct assignment counts ({stored_result.get('successful_assignments')} successful)")
            tests_passed.append(True)
        else:
            print(f"❌ Test 6 FAILED: Web interface doesn't retrieve correct data")
            tests_passed.append(False)
        
        # Test 7: Processing mode and algorithm are preserved
        if (result.get('processing_mode') == process_mode and 
            result.get('algorithm_used') == algorithm):
            print(f"✅ Test 7 PASSED: Processing mode and algorithm preserved ({result.get('processing_mode')}, {result.get('algorithm_used')})")
            tests_passed.append(True)
        else:
            print(f"❌ Test 7 FAILED: Processing mode or algorithm not preserved")
            tests_passed.append(False)
        
        # Overall result
        all_tests_passed = all(tests_passed)
        
        print(f"\n🏁 Complete Web Solution Test Summary:")
        print(f"  Test 1 (Row count - empty_only fix): {'✅ PASSED' if tests_passed[0] else '❌ FAILED'}")
        print(f"  Test 2 (Correct rows - empty_only fix): {'✅ PASSED' if tests_passed[1] else '❌ FAILED'}")
        print(f"  Test 3 (Redis progress tracking): {'✅ PASSED' if tests_passed[2] else '❌ FAILED'}")
        print(f"  Test 4 (Celery state updates): {'✅ PASSED' if tests_passed[3] else '❌ FAILED'}")
        print(f"  Test 5 (Assignment counts): {'✅ PASSED' if tests_passed[4] else '❌ FAILED'}")
        print(f"  Test 6 (Web interface data): {'✅ PASSED' if tests_passed[5] else '❌ FAILED'}")
        print(f"  Test 7 (Metadata preservation): {'✅ PASSED' if tests_passed[6] else '❌ FAILED'}")
        print(f"  Overall: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        # Show progress statistics
        if progress_updates and mock_celery_task.state_updates:
            print(f"\n📈 Progress Statistics:")
            print(f"  Redis progress updates: {len(progress_updates)}")
            print(f"  Celery state updates: {len(mock_celery_task.state_updates)}")
            print(f"  Total processing time: {processing_time:.2f} seconds")
            print(f"  Average time per row: {processing_time / expected_count:.2f} seconds")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Error during complete web solution testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_complete_web_solution():
        print("\n🎉 ALL WEB INTERFACE FIXES ARE WORKING PERFECTLY!")
        print("\n📝 Complete Summary of Fixes:")
        print("  1. ✅ Empty_only mode processes only rows with missing HTS codes")
        print("     - Fixed filtering logic to process only 3 rows instead of 14,086")
        print()
        print("  2. ✅ Progress tracking works in web interface")
        print("     - Added Redis progress updates for real-time display")
        print("     - Added Celery task state updates for web API")
        print("     - Progress shows from 0% to 100% with time estimates")
        print()
        print("  3. ✅ Assignment counts are displayed correctly")
        print("     - Fixed counting logic to show 3 successful assignments")
        print("     - Added support for both sync and async results")
        print("     - Web interface now shows correct statistics")
        print()
        print("🚀 The web interface should now work perfectly!")
        print("   - Real-time progress updates during processing")
        print("   - Correct assignment counts in final results")
        print("   - Efficient processing of only necessary rows")
    else:
        print("\n❌ Some web interface fixes are not working correctly!")
        sys.exit(1)