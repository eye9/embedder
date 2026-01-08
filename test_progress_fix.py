#!/usr/bin/env python3
"""
Test script to verify that progress tracking works correctly.
"""

import os
import sys
import time
import threading
from pathlib import Path

def monitor_progress(task_id, duration=30):
    """Monitor progress updates for a task."""
    
    try:
        from batch_processor.services.progress_tracker import get_progress_tracker
        
        progress_tracker = get_progress_tracker()
        
        print(f"🔍 Monitoring progress for task: {task_id}")
        
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < duration:
            progress_update = progress_tracker.get_progress(task_id)
            
            if progress_update:
                current_progress = progress_update.progress
                
                if current_progress != last_progress:
                    print(f"  📊 Progress: {current_progress:.1%} "
                          f"({progress_update.processed_rows}/{progress_update.total_rows} rows) "
                          f"- {progress_update.message}")
                    
                    if progress_update.estimated_time_remaining:
                        print(f"      ⏱️  Estimated time remaining: {progress_update.estimated_time_remaining}s")
                    
                    last_progress = current_progress
                
                # Check if task is completed
                if progress_update.status in ['completed', 'failed']:
                    print(f"  ✅ Task {progress_update.status}: {progress_update.message}")
                    break
            
            time.sleep(1)
        
        print(f"🔍 Progress monitoring ended for task: {task_id}")
        
    except Exception as e:
        print(f"❌ Error monitoring progress: {e}")

def test_progress_tracking():
    """Test progress tracking during file processing."""
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        import uuid
        
        print("🧪 Testing progress tracking...")
        
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
        
        # Start progress monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_progress,
            args=(sync_task_id, 60),  # Monitor for up to 60 seconds
            daemon=True
        )
        monitor_thread.start()
        
        # Give monitor thread a moment to start
        time.sleep(1)
        
        # Run processing
        print(f"\n🚀 Starting processing with progress tracking...")
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
        
        print(f"\n📊 Final Results:")
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Processed rows: {result.get('processed_rows', 0)}")
        print(f"  Total rows: {result.get('total_rows', 0)}")
        print(f"  Error count: {result.get('error_count', 0)}")
        
        # Check final progress state
        from batch_processor.services.progress_tracker import get_progress_tracker
        progress_tracker = get_progress_tracker()
        final_progress = progress_tracker.get_progress(sync_task_id)
        
        if final_progress:
            print(f"\n📈 Final Progress State:")
            print(f"  Status: {final_progress.status}")
            print(f"  Progress: {final_progress.progress:.1%}")
            print(f"  Message: {final_progress.message}")
            
            if final_progress.status == 'completed' and final_progress.progress == 1.0:
                print(f"  ✅ Progress tracking worked correctly!")
                return True
            else:
                print(f"  ❌ Progress tracking incomplete!")
                return False
        else:
            print(f"  ❌ No final progress data found!")
            return False
        
    except Exception as e:
        print(f"❌ Error during progress test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Testing progress tracking fix...")
    
    if test_progress_tracking():
        print("\n✅ Progress tracking test passed!")
    else:
        print("\n❌ Progress tracking test failed!")
        sys.exit(1)