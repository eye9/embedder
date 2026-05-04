#!/usr/bin/env python3
"""
Debug script to test process_mode parameter handling
"""

import requests
import json
import time

def test_process_mode():
    """Test if process_mode parameter is correctly handled"""
    
    # Test file path
    file_path = "GUOO-Manifest--777Bags.xlsx"
    
    # Authentication
    auth = ('user', 'password')
    
    print("Testing process_mode parameter handling...")
    
    # Test 1: Upload with empty_only mode
    print("\n=== Test 1: Upload with empty_only mode ===")
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        data = {
            'process_mode': 'empty_only',
            'algorithm': 'similarity_top1'
        }
        
        print(f"Sending request with process_mode: {data['process_mode']}")
        
        response = requests.post(
            'http://localhost:8000/upload',
            files=files,
            data=data,
            auth=auth
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Task ID: {result.get('task_id')}")
            print(f"Processing mode in response: {result.get('processing_mode')}")
            print(f"Rows to process: {result.get('rows_to_process')}")
            print(f"Total rows: {result.get('total_rows')}")
            
            # Wait for completion and check result
            task_id = result.get('task_id')
            if task_id:
                print(f"\nWaiting for task {task_id} to complete...")
                
                # Poll for completion
                for i in range(60):  # Wait up to 60 seconds
                    status_response = requests.get(
                        f'http://localhost:8000/task/{task_id}/status',
                        auth=auth
                    )
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        print(f"Status: {status.get('status')}, Progress: {status.get('progress', 0):.2%}")
                        
                        if status.get('status') == 'completed':
                            # Get summary
                            summary_response = requests.get(
                                f'http://localhost:8000/task/{task_id}/summary',
                                auth=auth
                            )
                            
                            if summary_response.status_code == 200:
                                summary = summary_response.json()
                                print(f"\n=== Final Summary ===")
                                print(f"Processing mode: {summary.get('processing_mode')}")
                                print(f"Processed rows: {summary.get('processed_rows')}")
                                print(f"Total rows: {summary.get('total_rows')}")
                                print(f"Successful assignments: {summary.get('successful_assignments')}")
                                print(f"Failed assignments: {summary.get('failed_assignments')}")
                                
                                # Check if the processing mode is correct
                                if summary.get('processing_mode') == 'empty_only':
                                    print("✅ Processing mode is correct!")
                                else:
                                    print(f"❌ Processing mode is wrong! Expected 'empty_only', got '{summary.get('processing_mode')}'")
                                
                                # Check if processed rows is reasonable for empty_only mode
                                processed = summary.get('processed_rows', 0)
                                total = summary.get('total_rows', 0)
                                if processed < total:
                                    print(f"✅ Processed fewer rows than total ({processed} < {total}), which is expected for empty_only mode")
                                else:
                                    print(f"❌ Processed all rows ({processed} = {total}), which suggests 'all' mode was used instead")
                            
                            break
                        elif status.get('status') == 'failed':
                            print(f"❌ Task failed: {status.get('error_message')}")
                            break
                    
                    time.sleep(1)
                else:
                    print("❌ Task did not complete within 60 seconds")
        else:
            print(f"❌ Upload failed: {response.text}")

if __name__ == "__main__":
    test_process_mode()