"""
Models package for batch processor web application.

This package contains Pydantic models for API requests and responses.
"""

# Import existing models for backward compatibility
from .base_models import (
    ProcessingRequest,
    TaskStatus,
    UploadResponse,
    DownloadInfo,
    ErrorResponse,
    HealthResponse,
    ServiceInfo,
    ProgressUpdate,
    ValidationResult,
    ProcessingSummary
)

# Import admin models
from .admin_models import (
    AdminUploadResponse,
    UploadSummary,
    AdminProgressUpdate,
    AdminValidationResult
)

__all__ = [
    # Base models
    "ProcessingRequest",
    "TaskStatus",
    "UploadResponse",
    "DownloadInfo",
    "ErrorResponse",
    "HealthResponse",
    "ServiceInfo",
    "ProgressUpdate",
    "ValidationResult",
    "ProcessingSummary",
    # Admin models
    "AdminUploadResponse",
    "UploadSummary",
    "AdminProgressUpdate",
    "AdminValidationResult"
]
