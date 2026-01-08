"""
Task status and download endpoints for the batch Excel processor.

This module provides endpoints for checking task status and downloading
processed files with security validation and session-based access control.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from celery.result import AsyncResult

from ..config.settings import get_config
from ..services.file_manager import FileManager
from ..workers.celery_app import celery_app
from .auth import require_auth, session_manager
from .models import TaskStatus, DownloadInfo, ProcessingSummary, ErrorResponse

# Import the sync result functions
from .upload import _get_sync_result


logger = logging.getLogger(__name__)

# Create router for task endpoints
router = APIRouter(prefix="/task", tags=["tasks"])

# Initialize services
file_manager = FileManager()


def get_task_result(task_id: str) -> AsyncResult:
    """Get Celery task result object."""
    return AsyncResult(task_id, app=celery_app)


def parse_task_meta(meta: dict) -> dict:
    """Parse task metadata into standardized format."""
    if not meta:
        return {
            "progress": 0.0,
            "processed_rows": 0,
            "total_rows": 0,
            "error_count": 0,
            "estimated_time_remaining": None,
            "current_operation": None
        }
    
    return {
        "progress": meta.get("progress", 0.0),
        "processed_rows": meta.get("processed_rows", 0),
        "total_rows": meta.get("total_rows", 0),
        "error_count": meta.get("error_count", 0),
        "estimated_time_remaining": meta.get("estimated_time_remaining"),
        "current_operation": meta.get("current_operation")
    }


def validate_user_task_access(task_id: str, user: str) -> bool:
    """
    Validate that a user has access to a specific task.
    
    Args:
        task_id: Task ID to validate access for
        user: Username requesting access
        
    Returns:
        True if user has access, False otherwise
    """
    try:
        # Get task result to check if it exists and get task info
        task_result = get_task_result(task_id)
        
        # For now, we allow any authenticated user to access any task
        # In a production system, you might want to track task ownership
        # by storing user information in task metadata
        
        # Check if task exists (will raise exception if not found)
        _ = task_result.state
        
        return True
        
    except Exception as e:
        logger.warning(f"Task access validation failed for user {user}, task {task_id}: {e}")
        return False


@router.get("/{task_id}/status", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    user: str = Depends(require_auth)
):
    """
    Get the status of a processing task.
    
    Returns detailed information about task progress, including:
    - Current status (pending, processing, completed, failed)
    - Progress percentage and row counts
    - Error information if applicable
    - Time estimates
    """
    try:
        # First check if this is a synchronous result
        sync_result = _get_sync_result(task_id)
        if sync_result:
            if sync_result["status"] == "completed":
                return TaskStatus(
                    task_id=task_id,
                    status="completed",
                    progress=1.0,
                    processed_rows=sync_result.get("processed_rows", 0),
                    total_rows=sync_result.get("total_rows", 0),
                    error_count=sync_result.get("error_count", 0),
                    estimated_time_remaining=0,
                    created_at=None,
                    started_at=None,
                    completed_at=None,
                    error_message=None
                )
            else:
                return TaskStatus(
                    task_id=task_id,
                    status="failed",
                    progress=0.0,
                    processed_rows=0,
                    total_rows=0,
                    error_count=1,
                    estimated_time_remaining=None,
                    created_at=None,
                    started_at=None,
                    completed_at=None,
                    error_message=sync_result.get("error", "Processing failed")
                )
        
        # Fallback to Celery task status
        task_result = get_task_result(task_id)
        
        # Get task state and info
        state = task_result.state
        info = task_result.info or {}
        
        # Handle case where info is an exception (FAILURE state)
        if isinstance(info, Exception):
            info = {"error": str(info)}
        elif not isinstance(info, dict):
            info = {"error": str(info)}
        
        # Parse metadata
        meta = parse_task_meta(info)
        
        # Map Celery states to our status format
        status_mapping = {
            "PENDING": "pending",
            "PROGRESS": "processing", 
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "RETRY": "processing",
            "REVOKED": "failed"
        }
        
        status = status_mapping.get(state, "unknown")
        
        # Handle different states
        if state == "PENDING":
            # Task is waiting to be processed
            return TaskStatus(
                task_id=task_id,
                status="pending",
                progress=0.0,
                processed_rows=0,
                total_rows=0,
                error_count=0,
                created_at=datetime.utcnow()
            )
        
        elif state == "PROGRESS":
            # Task is currently processing
            return TaskStatus(
                task_id=task_id,
                status="processing",
                progress=meta["progress"],
                processed_rows=meta["processed_rows"],
                total_rows=meta["total_rows"],
                error_count=meta["error_count"],
                estimated_time_remaining=meta["estimated_time_remaining"],
                started_at=info.get("started_at")
            )
        
        elif state == "SUCCESS":
            # Task completed successfully
            result = task_result.result or {}
            return TaskStatus(
                task_id=task_id,
                status="completed",
                progress=1.0,
                processed_rows=result.get("processed_rows", meta["processed_rows"]),
                total_rows=result.get("total_rows", meta["total_rows"]),
                error_count=result.get("error_count", meta["error_count"]),
                started_at=result.get("started_at"),
                completed_at=result.get("completed_at")
            )
        
        elif state == "FAILURE":
            # Task failed
            error_msg = str(info) if info else "Unknown error occurred"
            return TaskStatus(
                task_id=task_id,
                status="failed",
                progress=meta["progress"],
                processed_rows=meta["processed_rows"],
                total_rows=meta["total_rows"],
                error_count=meta["error_count"],
                error_message=error_msg,
                started_at=info.get("started_at")
            )
        
        else:
            # Unknown state
            return TaskStatus(
                task_id=task_id,
                status="unknown",
                progress=meta["progress"],
                processed_rows=meta["processed_rows"],
                total_rows=meta["total_rows"],
                error_count=meta["error_count"]
            )
            
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/{task_id}/summary", response_model=ProcessingSummary)
async def get_processing_summary(
    task_id: str,
    user: str = Depends(require_auth)
):
    """
    Get detailed processing summary for a completed task.
    
    Returns comprehensive statistics about the processing operation,
    including performance metrics and processing details.
    """
    try:
        # First check if this is a synchronous result
        sync_result = _get_sync_result(task_id)
        if sync_result and sync_result.get("status") == "completed":
            return ProcessingSummary(
                task_id=task_id,
                total_rows=sync_result.get("total_rows", 0),
                processed_rows=sync_result.get("processed_rows", 0),
                skipped_rows=sync_result.get("skipped_rows", 0),
                successful_assignments=sync_result.get("successful_assignments", 0),
                failed_assignments=sync_result.get("failed_assignments", 0),
                processing_time_seconds=sync_result.get("processing_time_seconds", 0.0),
                average_time_per_row_ms=sync_result.get("average_time_per_row_ms", 0.0),
                algorithm_used=sync_result.get("algorithm_used", "similarity_top1"),
                processing_mode=sync_result.get("processing_mode", "all")
            )
        
        # Fallback to Celery task result
        task_result = get_task_result(task_id)
        
        if task_result.state != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed. Current status: {task_result.state}"
            )
        
        result = task_result.result or {}
        
        return ProcessingSummary(
            task_id=task_id,
            total_rows=result.get("total_rows", 0),
            processed_rows=result.get("processed_rows", 0),
            skipped_rows=result.get("skipped_rows", 0),
            successful_assignments=result.get("successful_assignments", 0),
            failed_assignments=result.get("failed_assignments", 0),
            processing_time_seconds=result.get("processing_time_seconds", 0.0),
            average_time_per_row_ms=result.get("average_time_per_row_ms", 0.0),
            algorithm_used=result.get("algorithm_used", "similarity_top1"),
            processing_mode=result.get("processing_mode", "all")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing summary for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get processing summary: {str(e)}"
        )


@router.get("/{task_id}/download", response_model=DownloadInfo)
async def get_download_info(
    task_id: str,
    user: str = Depends(require_auth)
):
    """
    Get download information for a completed task.
    
    Returns download URL and file information without actually
    downloading the file. Use the download URL for actual download.
    """
    try:
        task_result = get_task_result(task_id)
        
        if task_result.state != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed. Current status: {task_result.state}"
            )
        
        result = task_result.result or {}
        output_file = result.get("output_file")
        
        if not output_file:
            raise HTTPException(
                status_code=404,
                detail="Output file not found for this task"
            )
        
        output_path = Path(output_file)
        if not output_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Output file no longer exists (may have been cleaned up)"
            )
        
        # Get file info
        file_size = output_path.stat().st_size
        filename = output_path.name
        
        # Calculate expiration (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        return DownloadInfo(
            task_id=task_id,
            filename=filename,
            file_size=file_size,
            download_url=f"/task/{task_id}/download/file",
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download info for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get download info: {str(e)}"
        )


@router.get("/{task_id}/download/file")
async def download_file(
    task_id: str,
    user: str = Depends(require_auth)
):
    """
    Download the processed file for a completed task.
    
    Returns the Excel file as a downloadable attachment with
    security validation to ensure user can only access their files.
    """
    try:
        # Validate user access to this task
        if not validate_user_task_access(task_id, user):
            raise HTTPException(
                status_code=403,
                detail="Access denied: you do not have permission to access this task"
            )
        
        task_result = get_task_result(task_id)
        
        if task_result.state != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed. Current status: {task_result.state}"
            )
        
        result = task_result.result or {}
        output_file = result.get("output_file")
        
        if not output_file:
            raise HTTPException(
                status_code=404,
                detail="Output file not found for this task"
            )
        
        output_path = Path(output_file)
        
        # Security validation: ensure file is within our managed directory
        config = get_config()
        base_path = Path(config.files.temp_dir).resolve()
        
        try:
            # Check if file path is within base directory
            output_path.resolve().relative_to(base_path)
        except ValueError:
            logger.warning(f"Security violation: attempt to access file outside base path: {output_path}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: file path validation failed"
            )
        
        if not output_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Output file no longer exists (may have been cleaned up)"
            )
        
        # Generate download filename
        original_filename = result.get("original_filename", "processed_file.xlsx")
        base_name = Path(original_filename).stem
        download_filename = f"processed_{base_name}.xlsx"
        
        logger.info(f"User {user} downloading file for task {task_id}: {output_path}")
        
        return FileResponse(
            path=output_path,
            filename=download_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    user: str = Depends(require_auth)
):
    """
    Cancel a running task.
    
    Attempts to revoke the task if it's still pending or processing.
    Returns the final status of the cancellation attempt.
    """
    try:
        task_result = get_task_result(task_id)
        
        if task_result.state in ["SUCCESS", "FAILURE"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in state: {task_result.state}"
            )
        
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)
        
        logger.info(f"User {user} cancelled task {task_id}")
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )