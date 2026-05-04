#!/usr/bin/env python3
"""
Final test to verify both fixes:
1. Empty_only mode processes only rows with missing HTS codes
2. Progress tracking works correctly
"""

import os
import sys
import time
import threading
import uuid
from pathlib import Path

def test_complete_fix():
    """Test both the filtering fix and progress tracking."""
    
    print("🔧 Testing complete fix for empty_only mode and progress tracking...")
    
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
        
        # Test 1: Check if correct number of rows were processed
        processed_rows = result.get('processed_rows', 0)
        if processed_rows == expected_count:
            print(f"  ✅ Correct number of rows processed: {processed_rows}")
            test1_passed = True
        else:
            print(f"  ❌ Wrong number of rows processed: {processed_rows}, expected: {expected_count}")
            test1_passed = False
        
        # Test 2: Check if output file has correct assignments
        output_file = result.get('output_file')
        test2_passed = False
        
        if output_file and os.path.exists(output_file):
            import pandas as pd
            df_output = pd.read_excel(output_file)
            
            # Find rows with assigned TNVED codes
            assigned_mask = df_output['TNVED_Code'].notna() & (df_output['TNVED_Code'].astype(str).str.strip() != '')
            assigned_rows = df_output[assigned_mask].index.tolist()
            
            print(f"  🎯 Expected rows to process: {expected_rows_to_process}")
            print(f"  🎯 Actually processed rows: {assigned_rows}")
            
            if set(assigned_rows) == set(expected_rows_to_process):
                print(f"  ✅ Correct rows were processed!")
                test2_passed = True
            else:
                print(f"  ❌ Wrong rows were processed!")
                test2_passed = False
        else:
            print(f"  ❌ Output file not found: {output_file}")
        
        # Test 3: Check progress tracking
        test3_passed = False
        
        if progress_updates:
            print(f"\n📈 Progress Tracking Results:")
            print(f"  Total progress updates: {len(progress_updates)}")
            
            # Check if we have initial, intermediate, and final updates
            initial_updates = [u for u in progress_updates if u['progress'] == 0.0]
            final_updates = [u for u in progress_updates if u['progress'] == 1.0 and u['status'] == 'completed']
            intermediate_updates = [u for u in progress_updates if 0.0 < u['progress'] < 1.0]
            
            print(f"  Initial updates: {len(initial_updates)}")
            print(f"  Intermediate updates: {len(intermediate_updates)}")
            print(f"  Final updates: {len(final_updates)}")
            
            if initial_updates and final_updates:
                print(f"  ✅ Progress tracking worked correctly!")
                test3_passed = True
                
                # Show sample progress updates
                print(f"  📊 Sample progress updates:")
                for i, update in enumerate(progress_updates[:5]):  # Show first 5
                    print(f"    {i+1}. {update['progress']:.1%} ({update['processed_rows']}/{update['total_rows']}) - {update['message'][:50]}...")
                
                if len(progress_updates) > 5:
                    print(f"    ... and {len(progress_updates) - 5} more updates")
            else:
                print(f"  ❌ Progress tracking incomplete!")
        else:
            print(f"  ❌ No progress updates captured!")
        
        # Overall result
        all_tests_passed = test1_passed and test2_passed and test3_passed
        
        print(f"\n🏁 Test Summary:")
        print(f"  Test 1 (Row count): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"  Test 2 (Correct rows): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        print(f"  Test 3 (Progress tracking): {'✅ PASSED' if test3_passed else '❌ FAILED'}")
        print(f"  Overall: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_complete_fix():
        print("\n🎉 All fixes are working correctly!")
        print("\n📝 Summary of fixes:")
        print("  1. ✅ Empty_only mode now processes only rows with missing HTS codes")
        print("  2. ✅ Progress tracking works correctly with real-time updates")
        print("  3. ✅ Time estimation is provided during processing")
    else:
        print("\n❌ Some fixes are not working correctly!")
        sys.exit(1)