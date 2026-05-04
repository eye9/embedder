#!/usr/bin/env python3
"""
Test script to verify that successful and failed assignments are counted correctly.
"""

import os
import sys
import time
import uuid
from pathlib import Path

def test_assignments_count():
    """Test that successful and failed assignments are counted correctly."""
    
    print("🔧 Testing assignments count fix...")
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        
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
        
        # Expected results
        expected_processed_rows = 3
        
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
        
        print(f"\n📊 Processing Results:")
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Processed rows: {result.get('processed_rows', 0)}")
        print(f"  Total rows: {result.get('total_rows', 0)}")
        print(f"  Error count: {result.get('error_count', 0)}")
        print(f"  Successful assignments: {result.get('successful_assignments', 0)}")
        print(f"  Failed assignments: {result.get('failed_assignments', 0)}")
        
        # Test 1: Check if result contains assignment counts
        if 'successful_assignments' in result and 'failed_assignments' in result:
            print(f"  ✅ Assignment counts are present in result")
            test1_passed = True
        else:
            print(f"  ❌ Assignment counts are missing from result")
            test1_passed = False
        
        # Test 2: Check if assignment counts make sense
        successful_assignments = result.get('successful_assignments', 0)
        failed_assignments = result.get('failed_assignments', 0)
        processed_rows = result.get('processed_rows', 0)
        
        total_assignments = successful_assignments + failed_assignments
        
        if total_assignments == processed_rows:
            print(f"  ✅ Assignment counts match processed rows: {total_assignments} = {processed_rows}")
            test2_passed = True
        else:
            print(f"  ❌ Assignment counts don't match processed rows: {total_assignments} ≠ {processed_rows}")
            test2_passed = False
        
        # Test 3: Check if we have some successful assignments (we expect all to be successful)
        if successful_assignments > 0:
            print(f"  ✅ Has successful assignments: {successful_assignments}")
            test3_passed = True
        else:
            print(f"  ❌ No successful assignments: {successful_assignments}")
            test3_passed = False
        
        # Test 4: Check output file for actual assignments
        output_file = result.get('output_file')
        test4_passed = False
        
        if output_file and os.path.exists(output_file):
            import pandas as pd
            df_output = pd.read_excel(output_file)
            
            # Count actual assignments in the file
            assigned_mask = df_output['TNVED_Code'].notna() & (df_output['TNVED_Code'].astype(str).str.strip() != '')
            actual_assignments = assigned_mask.sum()
            
            print(f"  📄 Actual assignments in output file: {actual_assignments}")
            
            if actual_assignments == successful_assignments:
                print(f"  ✅ Output file assignments match successful count: {actual_assignments} = {successful_assignments}")
                test4_passed = True
            else:
                print(f"  ❌ Output file assignments don't match successful count: {actual_assignments} ≠ {successful_assignments}")
                
                # Show sample assignments
                if actual_assignments > 0:
                    print(f"  🔍 Sample assignments from output file:")
                    assigned_df = df_output[assigned_mask]
                    for i, (idx, row) in enumerate(assigned_df.iterrows()):
                        if i < 3:
                            desc = str(row['Product Detailed Description'])[:50]
                            code = row['TNVED_Code']
                            print(f"    Row {idx}: '{desc}...' -> {code}")
        else:
            print(f"  ❌ Output file not found: {output_file}")
        
        # Overall result
        all_tests_passed = test1_passed and test2_passed and test3_passed and test4_passed
        
        print(f"\n🏁 Test Summary:")
        print(f"  Test 1 (Assignment counts present): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"  Test 2 (Counts match processed rows): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        print(f"  Test 3 (Has successful assignments): {'✅ PASSED' if test3_passed else '❌ FAILED'}")
        print(f"  Test 4 (Output file matches): {'✅ PASSED' if test4_passed else '❌ FAILED'}")
        print(f"  Overall: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_assignments_count():
        print("\n🎉 Assignment counting fix is working correctly!")
        print("\n📝 Summary:")
        print("  ✅ Successful assignments are counted correctly")
        print("  ✅ Failed assignments are counted correctly")
        print("  ✅ Total assignments match processed rows")
        print("  ✅ Output file contains the expected assignments")
    else:
        print("\n❌ Assignment counting fix is not working correctly!")
        sys.exit(1)