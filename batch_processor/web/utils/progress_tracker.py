"""
Progress tracking utility for admin data uploads.

This module provides the UploadProgressTracker class for tracking
upload progress and calculating metrics like ETA and processing speed.
"""

import time
from typing import Optional
from ..models.admin_models import AdminProgressUpdate


class UploadProgressTracker:
    """
    Tracks upload progress for real-time feedback during admin data uploads.
    
    This class manages progress tracking for long-running upload operations,
    calculating metrics like progress percentage, processing speed, and ETA.
    """
    
    def __init__(self, total_records: int):
        """
        Initialize the progress tracker.
        
        Args:
            total_records: Total number of records to be processed
            
        Raises:
            ValueError: If total_records is not positive
        """
        if total_records <= 0:
            raise ValueError("total_records must be positive")
            
        self.total_records = total_records
        self.processed_records = 0
        self.start_time = time.time()
    
    def update(self, processed: int) -> AdminProgressUpdate:
        """
        Update progress and calculate metrics.
        
        Args:
            processed: Number of records processed so far
            
        Returns:
            AdminProgressUpdate with current progress metrics
            
        Raises:
            ValueError: If processed count is invalid
        """
        if processed < 0:
            raise ValueError("processed count cannot be negative")
        if processed > self.total_records:
            raise ValueError("processed count cannot exceed total records")
            
        self.processed_records = processed
        elapsed = time.time() - self.start_time
        
        # Calculate progress percentage
        progress_pct = (processed / self.total_records) * 100.0
        
        # Calculate records per second
        records_per_sec = processed / elapsed if elapsed > 0 else 0.0
        
        # Calculate ETA in seconds
        remaining = self.total_records - processed
        eta_seconds = remaining / records_per_sec if records_per_sec > 0 else 0.0
        
        return AdminProgressUpdate(
            upload_id="",  # Will be set by caller
            processed=processed,
            total=self.total_records,
            progress_pct=progress_pct,
            records_per_sec=records_per_sec,
            eta_seconds=eta_seconds
        )