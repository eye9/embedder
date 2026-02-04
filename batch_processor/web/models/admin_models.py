"""
Pydantic models for admin data upload functionality.

This module defines data models for admin upload operations including
TNVED code uploads and URL mapping uploads.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class AdminUploadResponse(BaseModel):
    """Response for admin upload initiation."""
    
    upload_id: str = Field(description="Unique upload identifier")
    filename: str = Field(description="Original filename")
    file_size: int = Field(ge=0, description="File size in bytes")
    upload_type: str = Field(description="Upload type: 'tnved' or 'urls'")
    source_name: str = Field(description="Data source identifier")
    total_records: int = Field(ge=0, description="Total number of records in file")
    message: str = Field(description="Success message")
    
    @validator('upload_type')
    def validate_upload_type(cls, v):
        """Validate upload type is either 'tnved' or 'urls'."""
        if v not in ['tnved', 'urls']:
            raise ValueError("upload_type must be 'tnved' or 'urls'")
        return v


class UploadSummary(BaseModel):
    """Summary of upload processing results."""
    
    upload_id: str = Field(description="Upload identifier")
    upload_type: str = Field(description="Upload type: 'tnved' or 'urls'")
    source_name: str = Field(description="Data source identifier")
    total_records: int = Field(ge=0, description="Total records in uploaded file")
    successful_records: int = Field(ge=0, description="Successfully loaded records")
    failed_records: int = Field(ge=0, description="Failed records")
    invalid_urls: Optional[int] = Field(default=None, ge=0, description="Number of invalid URLs (for URL uploads)")
    invalid_codes: Optional[int] = Field(default=None, ge=0, description="Number of invalid TNVED codes")
    duplicate_records: Optional[int] = Field(default=None, ge=0, description="Number of duplicate records removed")
    processing_time_seconds: float = Field(ge=0, description="Total processing time in seconds")
    records_per_second: float = Field(ge=0, description="Processing speed in records per second")
    database_total_records: int = Field(ge=0, description="Total records in database after upload")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    warnings: List[str] = Field(default_factory=list, description="List of warning messages")
    
    @validator('upload_type')
    def validate_upload_type(cls, v):
        """Validate upload type is either 'tnved' or 'urls'."""
        if v not in ['tnved', 'urls']:
            raise ValueError("upload_type must be 'tnved' or 'urls'")
        return v
    
    @validator('successful_records', 'failed_records')
    def validate_record_counts(cls, v, values):
        """Validate that record counts are consistent."""
        if 'total_records' in values and v > values['total_records']:
            raise ValueError("Record count cannot exceed total records")
        return v


class AdminProgressUpdate(BaseModel):
    """Progress update during admin upload processing."""
    
    upload_id: str = Field(description="Upload identifier")
    processed: int = Field(ge=0, description="Number of records processed")
    total: int = Field(ge=0, description="Total number of records to process")
    progress_pct: float = Field(ge=0.0, le=100.0, description="Progress percentage (0-100)")
    records_per_sec: float = Field(ge=0, description="Processing speed in records per second")
    eta_seconds: float = Field(ge=0, description="Estimated time remaining in seconds")
    current_batch: Optional[int] = Field(default=None, ge=0, description="Current batch number being processed")
    status: str = Field(default="processing", description="Current status: processing, completed, failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    @validator('processed')
    def validate_processed(cls, v, values):
        """Validate that processed count doesn't exceed total."""
        if 'total' in values and v > values['total']:
            raise ValueError("Processed count cannot exceed total")
        return v


class AdminValidationResult(BaseModel):
    """Validation result for admin uploads."""
    
    is_valid: bool = Field(description="Whether the file passed validation")
    upload_type: str = Field(description="Upload type: 'tnved' or 'urls'")
    error_message: Optional[str] = Field(default=None, description="Validation error message if invalid")
    total_records: int = Field(ge=0, description="Total number of records in file")
    missing_columns: List[str] = Field(default_factory=list, description="List of missing required columns")
    file_info: Dict[str, Any] = Field(default_factory=dict, description="Additional file information")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    
    @validator('upload_type')
    def validate_upload_type(cls, v):
        """Validate upload type is either 'tnved' or 'urls'."""
        if v not in ['tnved', 'urls']:
            raise ValueError("upload_type must be 'tnved' or 'urls'")
        return v
    
    @validator('is_valid')
    def validate_consistency(cls, v, values):
        """Validate that invalid files have error messages."""
        if not v and 'error_message' in values and not values['error_message']:
            raise ValueError("Invalid files must have an error_message")
        return v


class AdminErrorResponse(BaseModel):
    """Error response model for admin upload operations."""
    
    error: str = Field(description="Error type or category")
    detail: str = Field(description="Detailed error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    upload_id: Optional[str] = Field(default=None, description="Upload identifier if available")
    error_code: Optional[str] = Field(default=None, description="Specific error code for programmatic handling")
    
    # Additional context for specific error types
    missing_columns: Optional[List[str]] = Field(default=None, description="Missing required columns (validation errors)")
    supported_formats: Optional[List[str]] = Field(default=None, description="Supported file formats (format errors)")
    max_file_size_mb: Optional[int] = Field(default=None, description="Maximum file size in MB (size errors)")
    file_info: Optional[Dict[str, Any]] = Field(default=None, description="File information for context")
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "error": "ValidationError",
                    "detail": "Missing required columns: Code, Description",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "upload_id": "tnved_abc123_1705312200",
                    "error_code": "MISSING_COLUMNS",
                    "missing_columns": ["Code", "Description"]
                },
                {
                    "error": "AuthenticationError", 
                    "detail": "Invalid credentials provided",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "error_code": "INVALID_CREDENTIALS"
                },
                {
                    "error": "FileSizeError",
                    "detail": "File size exceeds maximum limit of 100MB",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "error_code": "FILE_TOO_LARGE",
                    "max_file_size_mb": 100
                }
            ]
        }


class AdminConflictResponse(BaseModel):
    """Conflict response for concurrent upload attempts."""
    
    error: str = Field(default="ConflictError", description="Error type")
    detail: str = Field(description="Detailed conflict message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    active_upload_id: Optional[str] = Field(default=None, description="ID of currently active upload")
    retry_after_seconds: Optional[int] = Field(default=None, description="Suggested retry delay in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ConflictError",
                "detail": "User already has an upload in progress. Please wait for completion or cancel the existing upload.",
                "timestamp": "2024-01-15T10:30:00Z",
                "active_upload_id": "tnved_def456_1705312100",
                "retry_after_seconds": 30
            }
        }
