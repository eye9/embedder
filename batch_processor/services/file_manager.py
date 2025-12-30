"""File management utilities for batch processor."""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List
import pandas as pd
from fastapi import UploadFile
import logging
import tempfile
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file operations for batch processing sessions."""
    
    def __init__(self, base_path: str = "./temp_files"):
        """Initialize FileManager with base storage path."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self._cleanup_lock = threading.Lock()
        
        # Ensure base path is absolute to prevent path traversal
        self.base_path = self.base_path.resolve()
        
        logger.info(f"FileManager initialized with base path: {self.base_path}")
    
    def _validate_session_id(self, session_id: str) -> None:
        """Validate session ID to prevent path traversal attacks."""
        if not session_id:
            raise ValueError("Session ID cannot be empty")
        
        # Check for path traversal attempts
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValueError("Invalid session ID: contains path traversal characters")
        
        # Ensure it's a valid UUID format (additional security)
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise ValueError("Invalid session ID: must be a valid UUID")
    
    def _validate_filename(self, filename: str) -> None:
        """Validate filename to prevent path traversal attacks."""
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename: contains path traversal characters")
        
        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        if filename.upper().split('.')[0] in reserved_names:
            raise ValueError(f"Invalid filename: {filename} is a reserved name")
    
    def create_session_directory(self, session_id: str) -> Path:
        """Create a directory for a user session."""
        self._validate_session_id(session_id)
        
        session_dir = self.base_path / session_id
        session_dir.mkdir(exist_ok=True)
        
        # Ensure the created directory is within base_path (security check)
        if not str(session_dir.resolve()).startswith(str(self.base_path)):
            raise ValueError("Security violation: session directory outside base path")
        
        logger.info(f"Created session directory: {session_dir}")
        return session_dir
    
    def get_session_directory(self, session_id: str) -> Path:
        """Get the directory path for a session."""
        self._validate_session_id(session_id)
        
        session_dir = self.base_path / session_id
        
        # Security check
        if not str(session_dir.resolve()).startswith(str(self.base_path)):
            raise ValueError("Security violation: session directory outside base path")
        
        return session_dir
    
    async def save_uploaded_file(self, session_id: str, file: UploadFile) -> Path:
        """Save an uploaded file to the session directory."""
        self._validate_session_id(session_id)
        self._validate_filename(file.filename)
        
        session_dir = self.create_session_directory(session_id)
        file_path = session_dir / f"uploaded_{file.filename}"
        
        # Security check for final path
        if not str(file_path.resolve()).startswith(str(self.base_path)):
            raise ValueError("Security violation: file path outside base path")
        
        try:
            # Read file content
            content = await file.read()
            
            # Write to file
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # Reset file position for potential reuse
            await file.seek(0)
            
            logger.info(f"Saved uploaded file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink()
            raise
    
    def save_processed_file(
        self, 
        session_id: str, 
        df: pd.DataFrame, 
        original_filename: str
    ) -> Path:
        """Save a processed DataFrame as an Excel file."""
        self._validate_session_id(session_id)
        self._validate_filename(original_filename)
        
        session_dir = self.get_session_directory(session_id)
        
        # Generate processed filename
        base_name = Path(original_filename).stem
        processed_filename = f"processed_{base_name}.xlsx"
        file_path = session_dir / processed_filename
        
        # Security check
        if not str(file_path.resolve()).startswith(str(self.base_path)):
            raise ValueError("Security violation: file path outside base path")
        
        try:
            df.to_excel(file_path, index=False, engine='openpyxl')
            logger.info(f"Saved processed file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save processed file: {e}")
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink()
            raise
    
    def get_file_path(self, session_id: str, filename: str) -> Path:
        """Get the full path for a file in a session directory."""
        self._validate_session_id(session_id)
        self._validate_filename(filename)
        
        session_dir = self.get_session_directory(session_id)
        file_path = session_dir / filename
        
        # Security check
        if not str(file_path.resolve()).startswith(str(self.base_path)):
            raise ValueError("Security violation: file path outside base path")
        
        return file_path
    
    def file_exists(self, session_id: str, filename: str) -> bool:
        """Check if a file exists in the session directory."""
        try:
            file_path = self.get_file_path(session_id, filename)
            return file_path.exists()
        except (ValueError, OSError):
            return False
    
    def list_session_files(self, session_id: str) -> List[str]:
        """List all files in a session directory."""
        try:
            session_dir = self.get_session_directory(session_id)
            if not session_dir.exists():
                return []
            
            return [f.name for f in session_dir.iterdir() if f.is_file()]
            
        except (ValueError, OSError) as e:
            logger.error(f"Failed to list session files: {e}")
            return []
    
    def cleanup_session(self, session_id: str) -> None:
        """Remove all files and directory for a session."""
        try:
            self._validate_session_id(session_id)
            session_dir = self.get_session_directory(session_id)
            
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up session directory: {session_dir}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
    
    def schedule_cleanup(self, session_id: str, delay_hours: int = 24) -> None:
        """Schedule automatic cleanup of session files after delay."""
        def cleanup_after_delay():
            time.sleep(delay_hours * 3600)  # Convert hours to seconds
            with self._cleanup_lock:
                self.cleanup_session(session_id)
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(
            target=cleanup_after_delay,
            daemon=True,
            name=f"cleanup-{session_id}"
        )
        cleanup_thread.start()
        
        logger.info(f"Scheduled cleanup for session {session_id} in {delay_hours} hours")
    
    def schedule_cleanup_task(self, session_id: str, delay_hours: int = 24) -> None:
        """
        Schedule automatic cleanup using Celery task (preferred method).
        
        Args:
            session_id: Session ID to clean up
            delay_hours: Hours to wait before cleanup
        """
        try:
            from ..workers.celery_app import celery_app
            
            # Schedule cleanup task to run after delay
            celery_app.send_task(
                'batch_processor.workers.cleanup_task.cleanup_session_files',
                args=[session_id],
                countdown=delay_hours * 3600  # Convert hours to seconds
            )
            
            logger.info(f"Scheduled Celery cleanup task for session {session_id} in {delay_hours} hours")
            
        except Exception as e:
            logger.warning(f"Failed to schedule Celery cleanup task: {e}. Falling back to thread-based cleanup.")
            # Fallback to thread-based cleanup
            self.schedule_cleanup(session_id, delay_hours)
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions older than max_age_hours."""
        if not self.base_path.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._cleanup_lock:
            try:
                for session_dir in self.base_path.iterdir():
                    if not session_dir.is_dir():
                        continue
                    
                    # Check if directory is old enough
                    dir_mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
                    if dir_mtime < cutoff_time:
                        try:
                            # Validate it's a proper session directory (UUID format)
                            uuid.UUID(session_dir.name)
                            shutil.rmtree(session_dir)
                            cleaned_count += 1
                            logger.info(f"Cleaned up expired session: {session_dir.name}")
                        except (ValueError, OSError) as e:
                            logger.warning(f"Failed to cleanup session {session_dir.name}: {e}")
                            
            except Exception as e:
                logger.error(f"Error during expired sessions cleanup: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} expired sessions")
        return cleaned_count
    
    def get_session_size(self, session_id: str) -> int:
        """Get total size of all files in a session directory in bytes."""
        try:
            session_dir = self.get_session_directory(session_id)
            if not session_dir.exists():
                return 0
            
            total_size = 0
            for file_path in session_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to calculate session size: {e}")
            return 0
    
    def get_disk_usage(self) -> dict:
        """Get disk usage statistics for the base directory."""
        try:
            total_size = 0
            file_count = 0
            session_count = 0
            
            if self.base_path.exists():
                for item in self.base_path.iterdir():
                    if item.is_dir():
                        session_count += 1
                        for file_path in item.rglob('*'):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                                file_count += 1
            
            return {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'session_count': session_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            return {
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'file_count': 0,
                'session_count': 0
            }