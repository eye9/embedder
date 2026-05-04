#!/usr/bin/env python3
"""
Test script to verify the full processing pipeline with empty_only mode.
"""

import os
import sys
import time
from pathlib import Path

def test_processing():
    """Test the full processing pipeline."""
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        
        print("🧪 Testing full processing pipeline...")
        
        # Test parameters
        import uuid
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
        
        if result.get('status') == 'completed':
            print(f"  Processed rows: {result.get('processed_rows', 0)}")
            print(f"  Total rows: {result.get('total_rows', 0)}")
            print(f"  Error count: {result.get('error_count', 0)}")
            print(f"  Output file: {result.get('output_file', 'N/A')}")
            
            # Check if output file exists
            output_file = result.get('output_file')
            if output_file and os.path.exists(output_file):
                print(f"  ✅ Output file created successfully")
                
                # Analyze output file
                import pandas as pd
                df_output = pd.read_excel(output_file)
                
                assigned_codes = df_output['TNVED_Code'].notna() & (df_output['TNVED_Code'].astype(str).str.strip() != '')
                assigned_count = assigned_codes.sum()
                
                print(f"  📈 TNVED codes assigned: {assigned_count}")
                
                if assigned_count > 0:
                    print(f"  🔍 Sample assignments:")
                    assigned_df = df_output[assigned_codes]
                    for i, (idx, row) in enumerate(assigned_df.iterrows()):
                        if i < 3:
                            desc = str(row['Product Detailed Description'])[:50]
                            code = row['TNVED_Code']
                            print(f"    Row {idx}: '{desc}...' -> {code}")
                        elif i == 3:
                            print(f"    ... and {assigned_count - 3} more assignments")
                            break
                
                # Verify that only the expected rows were processed
                expected_rows = [4, 5, 8]  # From our analysis
                processed_rows = df_output[assigned_codes].index.tolist()
                
                print(f"  🎯 Expected rows to process: {expected_rows}")
                print(f"  🎯 Actually processed rows: {processed_rows}")
                
                if set(processed_rows) == set(expected_rows):
                    print(f"  ✅ Correct rows were processed!")
                else:
                    print(f"  ❌ Wrong rows were processed!")
                    return False
                
            else:
                print(f"  ❌ Output file not found: {output_file}")
                return False
                
        elif result.get('status') == 'failed':
            print(f"  ❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False
        else:
            print(f"  ❓ Unexpected status: {result.get('status')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Testing full processing with empty_only mode fix...")
    
    if test_processing():
        print("\n✅ Full processing test passed!")
    else:
        print("\n❌ Full processing test failed!")
        sys.exit(1)