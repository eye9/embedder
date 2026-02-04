"""
Custom exceptions for admin upload functionality.

This module defines custom exception classes for admin upload operations
with specific error codes and context information.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


class AdminUploadException(Exception):
    """Base exception for admin upload operations."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        upload_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize admin upload exception.
        
        Args:
            message: Error message
            error_code: Specific error code for programmatic handling
            upload_id: Upload identifier if available
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.upload_id = upload_id
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class AdminValidationError(AdminUploadException):
    """Exception for validation errors during admin uploads."""
    
    def __init__(
        self,
        message: str,
        missing_columns: Optional[List[str]] = None,
        file_info: Optional[Dict[str, Any]] = None,
        upload_id: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Validation error message
            missing_columns: List of missing required columns
            file_info: File information for context
            upload_id: Upload identifier if available
            error_code: Specific error code
        """
        context = {
            "missing_columns": missing_columns or [],
            "file_info": file_info or {}
        }
        super().__init__(message, error_code, upload_id, context)
        self.missing_columns = missing_columns or []
        self.file_info = file_info or {}


class AdminAuthenticationError(AdminUploadException):
    """Exception for authentication errors in admin operations."""
    
    def __init__(
        self,
        message: str = "Authentication required for admin operations",
        error_code: str = "AUTHENTICATION_REQUIRED"
    ):
        """
        Initialize authentication error.
        
        Args:
            message: Authentication error message
            error_code: Specific error code
        """
        super().__init__(message, error_code)


class AdminFileSizeError(AdminUploadException):
    """Exception for file size limit errors."""
    
    def __init__(
        self,
        message: str,
        file_size_bytes: int,
        max_size_bytes: int,
        upload_id: Optional[str] = None,
        error_code: str = "FILE_TOO_LARGE"
    ):
        """
        Initialize file size error.
        
        Args:
            message: File size error message
            file_size_bytes: Actual file size in bytes
            max_size_bytes: Maximum allowed size in bytes
            upload_id: Upload identifier if available
            error_code: Specific error code
        """
        context = {
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
            "max_size_bytes": max_size_bytes,
            "max_size_mb": round(max_size_bytes / (1024 * 1024), 2)
        }
        super().__init__(message, error_code, upload_id, context)
        self.file_size_bytes = file_size_bytes
        self.max_size_bytes = max_size_bytes


class AdminFormatError(AdminUploadException):
    """Exception for unsupported file format errors."""
    
    def __init__(
        self,
        message: str,
        file_extension: str,
        supported_formats: List[str],
        upload_id: Optional[str] = None,
        error_code: str = "UNSUPPORTED_FORMAT"
    ):
        """
        Initialize format error.
        
        Args:
            message: Format error message
            file_extension: Actual file extension
            supported_formats: List of supported formats
            upload_id: Upload identifier if available
            error_code: Specific error code
        """
        context = {
            "file_extension": file_extension,
            "supported_formats": supported_formats
        }
        super().__init__(message, error_code, upload_id, context)
        self.file_extension = file_extension
        self.supported_formats = supported_formats


class AdminConcurrentUploadError(AdminUploadException):
    """Exception for concurrent upload conflicts."""
    
    def __init__(
        self,
        message: str,
        active_upload_id: str,
        retry_after_seconds: Optional[int] = None,
        error_code: str = "CONCURRENT_UPLOAD_CONFLICT"
    ):
        """
        Initialize concurrent upload error.
        
        Args:
            message: Conflict error message
            active_upload_id: ID of currently active upload
            retry_after_seconds: Suggested retry delay
            error_code: Specific error code
        """
        context = {
            "active_upload_id": active_upload_id,
            "retry_after_seconds": retry_after_seconds
        }
        super().__init__(message, error_code, None, context)
        self.active_upload_id = active_upload_id
        self.retry_after_seconds = retry_after_seconds


class AdminProcessingError(AdminUploadException):
    """Exception for processing errors during admin uploads."""
    
    def __init__(
        self,
        message: str,
        upload_id: Optional[str] = None,
        processed_records: Optional[int] = None,
        total_records: Optional[int] = None,
        error_code: str = "PROCESSING_ERROR"
    ):
        """
        Initialize processing error.
        
        Args:
            message: Processing error message
            upload_id: Upload identifier
            processed_records: Number of records processed before error
            total_records: Total number of records
            error_code: Specific error code
        """
        context = {
            "processed_records": processed_records,
            "total_records": total_records
        }
        super().__init__(message, error_code, upload_id, context)
        self.processed_records = processed_records
        self.total_records = total_records


class AdminSourceNameError(AdminUploadException):
    """Exception for invalid source name errors."""
    
    def __init__(
        self,
        message: str,
        source_name: str,
        upload_id: Optional[str] = None,
        error_code: str = "INVALID_SOURCE_NAME"
    ):
        """
        Initialize source name error.
        
        Args:
            message: Source name error message
            source_name: Invalid source name
            upload_id: Upload identifier if available
            error_code: Specific error code
        """
        context = {
            "source_name": source_name,
            "allowed_characters": "alphanumeric characters, hyphens, and underscores"
        }
        super().__init__(message, error_code, upload_id, context)
        self.source_name = source_name