"""
Cleanup task for expired files and progress data.

This module implements periodic cleanup tasks for removing expired files
and progress tracking data.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any

from batch_processor.workers.celery_app import celery_app
from batch_processor.services.file_manager import FileManager
from batch_processor.services.progress_tracker import get_progress_tracker
from batch_processor.config.settings import get_config


logger = logging.getLogger(__name__)


@celery_app.task(name='batch_processor.workers.cleanup_task.cleanup_expired_files')
def cleanup_expired_files() -> Dict[str, Any]:
    """
    Periodic task to clean up expired files and progress data.
    
    This task runs periodically (configured in Celery beat schedule) to:
    1. Remove expired session files
    2. Clean up expired progress tracking data
    3. Log cleanup statistics
    
    Returns:
        Dictionary with cleanup statistics
    """
    logger.info("Starting periodic cleanup task")
    start_time = time.time()
    
    try:
        config = get_config()
        
        # Initialize services
        file_manager = FileManager(base_path=config.files.temp_dir)
        progress_tracker = get_progress_tracker()
        
        # Clean up expired files
        files_cleaned = 0
        if config.files.auto_cleanup_enabled:
            files_cleaned = file_manager.cleanup_expired_sessions(
                max_age_hours=config.security.session_timeout_hours
            )
        
        # Clean up expired progress data
        progress_cleaned = progress_tracker.cleanup_expired_progress()
        
        # Calculate cleanup time
        cleanup_time = time.time() - start_time
        
        result = {
            "status": "completed",
            "files_cleaned": files_cleaned,
            "progress_entries_cleaned": progress_cleaned,
            "cleanup_time_seconds": round(cleanup_time, 2),
            "timestamp": time.time()
        }
        
        logger.info(
            f"Cleanup completed: {files_cleaned} files, "
            f"{progress_cleaned} progress entries in {cleanup_time:.2f}s"
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Cleanup task failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            "status": "failed",
            "error": error_msg,
            "cleanup_time_seconds": time.time() - start_time,
            "timestamp": time.time()
        }


@celery_app.task(name='batch_processor.workers.cleanup_task.cleanup_session_files')
def cleanup_session_files(session_id: str) -> Dict[str, Any]:
    """
    Clean up files for a specific session.
    
    Args:
        session_id: Session identifier to clean up
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Cleaning up session files: {session_id}")
    start_time = time.time()
    
    try:
        config = get_config()
        file_manager = FileManager(base_path=config.files.temp_dir)
        progress_tracker = get_progress_tracker()
        
        # Clean up session files
        file_manager.cleanup_session(session_id)
        files_removed = 1  # Session directory removed
        
        # Clean up progress data for the session
        # Note: We need to find tasks associated with this session
        # This is a simplified approach - in production you might want
        # to maintain a session-to-task mapping
        progress_tracker.cleanup_expired_progress()
        
        cleanup_time = time.time() - start_time
        
        result = {
            "status": "completed",
            "session_id": session_id,
            "files_removed": files_removed,
            "cleanup_time_seconds": round(cleanup_time, 2)
        }
        
        logger.info(f"Session cleanup completed: {files_removed} files removed")
        return result
        
    except Exception as e:
        error_msg = f"Session cleanup failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            "status": "failed",
            "session_id": session_id,
            "error": error_msg,
            "cleanup_time_seconds": time.time() - start_time
        }