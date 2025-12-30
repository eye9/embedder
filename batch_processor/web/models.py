"""
Pydantic models for API requests and responses.

This module defines the data models used for API communication,
including request validation and response serialization.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..config.settings import ProcessingMode, AlgorithmType


class ProcessingRequest(BaseModel):
    """Request model for file processing."""
    
    process_mode: ProcessingMode = Field(
        default=ProcessingMode.ALL,
        description="Processing mode: 'all' to process all rows, 'empty_only' to process only rows without existing HTS codes"
    )
    algorithm: AlgorithmType = Field(
        default=AlgorithmType.SIMILARITY_TOP1,
        description="Algorithm to use for TNVED code selection"
    )
    
    class Config:
        use_enum_values = True


class TaskStatus(BaseModel):
    """Response model for task status."""
    
    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Task status: pending, processing, completed, failed")
    progress: float = Field(ge=0.0, le=1.0, description="Progress as a fraction from 0.0 to 1.0")
    processed_rows: int = Field(ge=0, description="Number of rows processed")
    total_rows: int = Field(ge=0, description="Total number of rows to process")
    error_count: int = Field(ge=0, description="Number of processing errors encountered")
    estimated_time_remaining: Optional[int] = Field(
        default=None, 
        description="Estimated time remaining in seconds"
    )
    created_at: Optional[datetime] = Field(default=None, description="Task creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion timestamp")
    error_message: Optional[str] = Field(default=None, description="Error message if task failed")


class UploadResponse(BaseModel):
    """Response model for file upload."""
    
    task_id: str = Field(description="Unique task identifier for tracking processing")
    session_id: str = Field(description="Session identifier for file management")
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    total_rows: int = Field(description="Total number of rows detected in file")
    rows_to_process: int = Field(description="Number of rows that will be processed based on mode")
    processing_mode: ProcessingMode = Field(description="Selected processing mode")
    algorithm: AlgorithmType = Field(description="Selected algorithm")
    message: str = Field(description="Success message")


class DownloadInfo(BaseModel):
    """Response model for download information."""
    
    task_id: str = Field(description="Task identifier")
    filename: str = Field(description="Generated filename for download")
    file_size: int = Field(description="File size in bytes")
    download_url: str = Field(description="URL for downloading the file")
    expires_at: datetime = Field(description="Download link expiration time")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error: str = Field(description="Error type or category")
    detail: str = Field(description="Detailed error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(description="Service health status")
    service: str = Field(description="Service name")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field(default="1.0.0", description="Service version")


class ServiceInfo(BaseModel):
    """Response model for service information."""
    
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    description: str = Field(description="Service description")
    endpoints: List[str] = Field(description="Available API endpoints")


class ProgressUpdate(BaseModel):
    """Model for WebSocket progress updates."""
    
    task_id: str = Field(description="Task identifier")
    progress: float = Field(ge=0.0, le=1.0, description="Progress as a fraction")
    processed_rows: int = Field(ge=0, description="Number of rows processed")
    total_rows: int = Field(ge=0, description="Total number of rows")
    error_count: int = Field(ge=0, description="Number of errors encountered")
    estimated_time_remaining: Optional[int] = Field(default=None, description="ETA in seconds")
    current_operation: Optional[str] = Field(default=None, description="Current operation description")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


class ValidationResult(BaseModel):
    """Model for file validation results."""
    
    is_valid: bool = Field(description="Whether the file is valid")
    error_message: Optional[str] = Field(default=None, description="Validation error message")
    total_rows: int = Field(ge=0, description="Total number of rows in file")
    rows_with_descriptions: int = Field(ge=0, description="Rows with non-empty descriptions")
    rows_with_existing_codes: int = Field(ge=0, description="Rows with existing HTS codes")
    missing_columns: List[str] = Field(default_factory=list, description="Missing required columns")
    file_info: Dict[str, Any] = Field(default_factory=dict, description="Additional file information")


class ProcessingSummary(BaseModel):
    """Model for processing completion summary."""
    
    task_id: str = Field(description="Task identifier")
    total_rows: int = Field(ge=0, description="Total rows in file")
    processed_rows: int = Field(ge=0, description="Rows actually processed")
    skipped_rows: int = Field(ge=0, description="Rows skipped (already had codes)")
    successful_assignments: int = Field(ge=0, description="Successful TNVED code assignments")
    failed_assignments: int = Field(ge=0, description="Failed TNVED code assignments")
    processing_time_seconds: float = Field(ge=0, description="Total processing time")
    average_time_per_row_ms: float = Field(ge=0, description="Average processing time per row")
    algorithm_used: AlgorithmType = Field(description="Algorithm used for processing")
    processing_mode: ProcessingMode = Field(description="Processing mode used")