"""Test backward compatibility of models import."""

# Test that old imports still work
from batch_processor.web.models import (
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

# Test that new imports work
from batch_processor.web.models import (
    AdminUploadResponse,
    UploadSummary,
    AdminProgressUpdate,
    AdminValidationResult
)

print("✓ All imports work correctly!")
print("✓ Backward compatibility maintained")
print("✓ New admin models available")
