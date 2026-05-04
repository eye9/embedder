#!/usr/bin/env python3
"""
Complete test to verify all fixes:
1. Empty_only mode processes only rows with missing HTS codes
2. Progress tracking works correctly
3. Successful/failed assignments are counted correctly
"""

import os
import sys
import time
import threading
import uuid
from pathlib import Path

def test_complete_solution():
    """Test all fixes together."""
    
    print("🔧 Testing complete solution for all reported issues...")
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        from batch_processor.services.progress_tracker import get_progress_tracker
        
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
        
        # Expected results based on our analysis
        expected_rows_to_process = [4, 5, 8]
        expected_count = len(expected_rows_to_process)
        
        print(f"  Expected rows to process: {expected_rows_to_process}")
        print(f"  Expected count: {expected_count}")
        
        # Track progress updates
        progress_updates = []
        progress_tracker = get_progress_tracker()
        
        def monitor_progress():
            """Monitor and collect progress updates."""
            start_time = time.time()
            while time.time() - start_time < 60:  # Monitor for up to 60 seconds
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
        
        # Start progress monitoring
        monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        monitor_thread.start()
        
        # Run processing
        print(f"\n🚀 Starting processing...")
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
        
        # Test results
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
        
        # Test 3: Progress tracking works (progress fix)
        if progress_updates:
            initial_updates = [u for u in progress_updates if u['progress'] == 0.0]
            final_updates = [u for u in progress_updates if u['progress'] == 1.0 and u['status'] == 'completed']
            
            if initial_updates and final_updates:
                print(f"✅ Test 3 PASSED: Progress tracking works ({len(progress_updates)} updates)")
                tests_passed.append(True)
            else:
                print(f"❌ Test 3 FAILED: Progress tracking incomplete")
                tests_passed.append(False)
        else:
            print(f"❌ Test 3 FAILED: No progress updates captured")
            tests_passed.append(False)
        
        # Test 4: Assignment counts are correct (assignment counting fix)
        successful_assignments = result.get('successful_assignments', 0)
        failed_assignments = result.get('failed_assignments', 0)
        
        if successful_assignments == expected_count and failed_assignments == 0:
            print(f"✅ Test 4 PASSED: Assignment counts are correct ({successful_assignments} successful, {failed_assignments} failed)")
            tests_passed.append(True)
        else:
            print(f"❌ Test 4 FAILED: Assignment counts are wrong ({successful_assignments} successful, {failed_assignments} failed)")
            tests_passed.append(False)
        
        # Test 5: Assignment counts match processed rows
        total_assignments = successful_assignments + failed_assignments
        if total_assignments == processed_rows:
            print(f"✅ Test 5 PASSED: Assignment counts match processed rows ({total_assignments} = {processed_rows})")
            tests_passed.append(True)
        else:
            print(f"❌ Test 5 FAILED: Assignment counts don't match processed rows ({total_assignments} ≠ {processed_rows})")
            tests_passed.append(False)
        
        # Overall result
        all_tests_passed = all(tests_passed)
        
        print(f"\n🏁 Final Test Summary:")
        print(f"  Test 1 (Row count - empty_only fix): {'✅ PASSED' if tests_passed[0] else '❌ FAILED'}")
        print(f"  Test 2 (Correct rows - empty_only fix): {'✅ PASSED' if tests_passed[1] else '❌ FAILED'}")
        print(f"  Test 3 (Progress tracking fix): {'✅ PASSED' if tests_passed[2] else '❌ FAILED'}")
        print(f"  Test 4 (Assignment counts fix): {'✅ PASSED' if tests_passed[3] else '❌ FAILED'}")
        print(f"  Test 5 (Counts consistency): {'✅ PASSED' if tests_passed[4] else '❌ FAILED'}")
        print(f"  Overall: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_complete_solution():
        print("\n🎉 ALL FIXES ARE WORKING PERFECTLY!")
        print("\n📝 Summary of all fixes:")
        print("  1. ✅ Empty_only mode now processes only rows with missing HTS codes")
        print("     - Before: Processed all 14,086 rows")
        print("     - After: Processes only 3 rows with missing HTS codes")
        print()
        print("  2. ✅ Progress tracking works correctly with real-time updates")
        print("     - Before: No progress updates shown")
        print("     - After: Real-time progress from 0% to 100% with time estimates")
        print()
        print("  3. ✅ Assignment counts are displayed correctly")
        print("     - Before: Showed 0 successful and 0 failed assignments")
        print("     - After: Shows 3 successful and 0 failed assignments")
        print()
        print("🚀 The program is now working as expected!")
    else:
        print("\n❌ Some fixes are not working correctly!")
        sys.exit(1)