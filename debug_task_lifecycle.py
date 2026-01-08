#!/usr/bin/env python3
"""
Debug script to monitor task lifecycle and detect issues
"""

import requests
import json
import time
import threading
from datetime import datetime

def monitor_logs():
    """Monitor Docker logs in real-time"""
    import subprocess
    
    print("Starting log monitor...")
    
    # Monitor worker logs
    process = subprocess.Popen(
        ['docker', 'logs', '-f', 'batch_processor_worker'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    for line in iter(process.stdout.readline, ''):
        if any(keyword in line for keyword in [
            'Selecting code', 'Processing completed', 'Task.*succeeded', 
            'Starting synchronous', 'process_mode', 'empty_only'
        ]):
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] LOG: {line.strip()}")

def test_task_lifecycle():
    """Test task lifecycle and monitor for issues"""
    
    file_path = "GUOO-Manifest--777Bags.xlsx"
    auth = ('user', 'password')
    
    print("=== Testing Task Lifecycle ===")
    
    # Start log monitoring in background
    log_thread = threading.Thread(target=monitor_logs, daemon=True)
    log_thread.start()
    
    time.sleep(2)  # Let log monitor start
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting file upload...")
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        data = {
            'process_mode': 'empty_only',
            'algorithm': 'similarity_top1'
        }
        
        response = requests.post(
            'http://localhost:8000/upload',
            files=files,
            data=data,
            auth=auth
        )
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return
    
    result = response.json()
    task_id = result.get('task_id')
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Task created: {task_id}")
    print(f"Processing mode: {result.get('processing_mode')}")
    print(f"Rows to process: {result.get('rows_to_process')}")
    
    # Monitor task progress
    start_time = time.time()
    completion_time = None
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Check task status
        status_response = requests.get(
            f'http://localhost:8000/task/{task_id}/status',
            auth=auth
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            progress = status.get('progress', 0)
            task_status = status.get('status')
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] Status: {task_status}, Progress: {progress:.1%}, Elapsed: {elapsed:.1f}s")
            
            if task_status == 'completed':
                completion_time = current_time
                print(f"[{timestamp}] ✅ Task completed after {elapsed:.1f}s")
                
                # Get final summary
                summary_response = requests.get(
                    f'http://localhost:8000/task/{task_id}/summary',
                    auth=auth
                )
                
                if summary_response.status_code == 200:
                    summary = summary_response.json()
                    print(f"Final summary:")
                    print(f"  - Processing mode: {summary.get('processing_mode')}")
                    print(f"  - Processed rows: {summary.get('processed_rows')}")
                    print(f"  - Total rows: {summary.get('total_rows')}")
                
                break
            elif task_status == 'failed':
                print(f"[{timestamp}] ❌ Task failed: {status.get('error_message')}")
                break
        
        time.sleep(2)
        
        # Timeout after 2 minutes
        if elapsed > 120:
            print(f"❌ Task timeout after {elapsed:.1f}s")
            break
    
    # Continue monitoring logs for additional activity
    if completion_time:
        print(f"\n=== Monitoring for post-completion activity ===")
        print("Watching for any processing activity after task completion...")
        print("Press Ctrl+C to stop monitoring")
        
        try:
            # Monitor for 60 seconds after completion
            monitor_start = time.time()
            while time.time() - monitor_start < 60:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    test_task_lifecycle()