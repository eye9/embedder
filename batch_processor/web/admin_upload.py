"""
Admin data upload router for batch processor web application.

This module provides FastAPI router endpoints for admin data uploads,
including TNVED code uploads and URL mapping uploads with authentication.
"""

import logging
import uuid
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from .auth import require_auth, session_manager
from .models.admin_models import (
    AdminUploadResponse, 
    UploadSummary, 
    AdminProgressUpdate, 
    AdminValidationResult,
    AdminErrorResponse,
    AdminConflictResponse
)
from .exceptions import (
    AdminUploadException,
    AdminValidationError,
    AdminAuthenticationError,
    AdminFileSizeError,
    AdminFormatError,
    AdminConcurrentUploadError,
    AdminProcessingError,
    AdminSourceNameError
)
from .validators.upload_validator import AdminUploadValidator
from .processors.tnved_processor import TNVEDUploadProcessor
from .processors.url_processor import URLUploadProcessor
from ..config.settings import get_config
from ..services.logging_service import get_structured_logger

# Configure logging
logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/admin/upload",
    tags=["admin", "upload"],
    dependencies=[Depends(require_auth)]
)

# Initialize templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Initialize validator
validator = AdminUploadValidator()

# Global progress tracking
upload_progress: Dict[str, AdminProgressUpdate] = {}


# Error handlers for admin upload operations
@router.exception_handler(AdminValidationError)
async def admin_validation_error_handler(request: Request, exc: AdminValidationError):
    """Handle validation errors with detailed context."""
    # Use admin-specific error logging
    structured_logger.log_admin_validation_failure(
        user=getattr(request.state, 'user', None),
        upload_id=exc.upload_id,
        upload_type="unknown",  # Will be determined from context
        filename=exc.context.get("filename", "unknown"),
        error_type=exc.error_code or "validation_error",
        error_details={
            "message": exc.message,
            "missing_columns": exc.missing_columns,
            "file_info": exc.file_info
        }
    )
    
    error_response = AdminErrorResponse(
        error="ValidationError",
        detail=exc.message,
        upload_id=exc.upload_id,
        error_code=exc.error_code,
        missing_columns=exc.missing_columns,
        file_info=exc.file_info
    )
    
    return JSONResponse(
        status_code=400,
        content=error_response.dict(exclude_none=True)
    )


@router.exception_handler(AdminAuthenticationError)
async def admin_authentication_error_handler(request: Request, exc: AdminAuthenticationError):
    """Handle authentication errors."""
    structured_logger.log_security_event(
        event_type="authentication_failure",
        user=getattr(request.state, 'user', None),
        ip_address=request.client.host if request.client else None,
        description=f"Admin authentication failed: {exc.message}",
        severity=structured_logger.LogLevel.WARNING
    )
    
    error_response = AdminErrorResponse(
        error="AuthenticationError",
        detail=exc.message,
        error_code=exc.error_code
    )
    
    return JSONResponse(
        status_code=401,
        content=error_response.dict(exclude_none=True),
        headers={"WWW-Authenticate": "Basic"}
    )


@router.exception_handler(AdminFileSizeError)
async def admin_file_size_error_handler(request: Request, exc: AdminFileSizeError):
    """Handle file size limit errors."""
    structured_logger.log_error(
        exc,
        context={
            "error_type": "file_size",
            "error_code": exc.error_code,
            "upload_id": exc.upload_id,
            "file_size_bytes": exc.file_size_bytes,
            "max_size_bytes": exc.max_size_bytes,
            "endpoint": str(request.url.path)
        },
        user=getattr(request.state, 'user', None)
    )
    
    error_response = AdminErrorResponse(
        error="FileSizeError",
        detail=exc.message,
        upload_id=exc.upload_id,
        error_code=exc.error_code,
        max_file_size_mb=round(exc.max_size_bytes / (1024 * 1024))
    )
    
    return JSONResponse(
        status_code=413,
        content=error_response.dict(exclude_none=True)
    )


@router.exception_handler(AdminFormatError)
async def admin_format_error_handler(request: Request, exc: AdminFormatError):
    """Handle unsupported file format errors."""
    structured_logger.log_error(
        exc,
        context={
            "error_type": "file_format",
            "error_code": exc.error_code,
            "upload_id": exc.upload_id,
            "file_extension": exc.file_extension,
            "supported_formats": exc.supported_formats,
            "endpoint": str(request.url.path)
        },
        user=getattr(request.state, 'user', None)
    )
    
    error_response = AdminErrorResponse(
        error="FormatError",
        detail=exc.message,
        upload_id=exc.upload_id,
        error_code=exc.error_code,
        supported_formats=exc.supported_formats
    )
    
    return JSONResponse(
        status_code=400,
        content=error_response.dict(exclude_none=True)
    )


@router.exception_handler(AdminConcurrentUploadError)
async def admin_concurrent_upload_error_handler(request: Request, exc: AdminConcurrentUploadError):
    """Handle concurrent upload conflicts."""
    structured_logger.log_error(
        exc,
        context={
            "error_type": "concurrent_upload",
            "error_code": exc.error_code,
            "active_upload_id": exc.active_upload_id,
            "endpoint": str(request.url.path)
        },
        user=getattr(request.state, 'user', None)
    )
    
    conflict_response = AdminConflictResponse(
        detail=exc.message,
        active_upload_id=exc.active_upload_id,
        retry_after_seconds=exc.retry_after_seconds
    )
    
    headers = {}
    if exc.retry_after_seconds:
        headers["Retry-After"] = str(exc.retry_after_seconds)
    
    return JSONResponse(
        status_code=409,
        content=conflict_response.dict(exclude_none=True),
        headers=headers
    )


@router.exception_handler(AdminProcessingError)
async def admin_processing_error_handler(request: Request, exc: AdminProcessingError):
    """Handle processing errors during uploads."""
    # Use admin-specific error logging
    structured_logger.log_admin_error_context(
        user=getattr(request.state, 'user', None),
        upload_id=exc.upload_id,
        upload_type="unknown",  # Will be determined from context
        error_type=exc.error_code or "processing_error",
        error_message=exc.message,
        context=exc.context,
        processed_records=exc.processed_records,
        total_records=exc.total_records
    )
    
    error_response = AdminErrorResponse(
        error="ProcessingError",
        detail=exc.message,
        upload_id=exc.upload_id,
        error_code=exc.error_code
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict(exclude_none=True)
    )


@router.exception_handler(AdminSourceNameError)
async def admin_source_name_error_handler(request: Request, exc: AdminSourceNameError):
    """Handle invalid source name errors."""
    structured_logger.log_error(
        exc,
        context={
            "error_type": "source_name",
            "error_code": exc.error_code,
            "upload_id": exc.upload_id,
            "source_name": exc.source_name,
            "endpoint": str(request.url.path)
        },
        user=getattr(request.state, 'user', None)
    )
    
    error_response = AdminErrorResponse(
        error="SourceNameError",
        detail=exc.message,
        upload_id=exc.upload_id,
        error_code=exc.error_code
    )
    
    return JSONResponse(
        status_code=400,
        content=error_response.dict(exclude_none=True)
    )


@router.exception_handler(AdminUploadException)
async def admin_upload_error_handler(request: Request, exc: AdminUploadException):
    """Handle general admin upload errors."""
    structured_logger.log_error(
        exc,
        context={
            "error_type": "admin_upload",
            "error_code": exc.error_code,
            "upload_id": exc.upload_id,
            "endpoint": str(request.url.path),
            "context": exc.context
        },
        user=getattr(request.state, 'user', None)
    )
    
    error_response = AdminErrorResponse(
        error="AdminUploadError",
        detail=exc.message,
        upload_id=exc.upload_id,
        error_code=exc.error_code
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict(exclude_none=True)
    )


@router.get("/", response_class=HTMLResponse)
async def admin_upload_page(request: Request, user: str = Depends(require_auth)):
    """
    Serve HTML upload interface for admin data uploads.
    
    Args:
        request: FastAPI request object
        user: Authenticated user from require_auth dependency
        
    Returns:
        HTMLResponse with admin upload form
    """
    logger.info(f"Admin upload page accessed by user: {user}")
    
    structured_logger.log_api_request(
        method="GET",
        endpoint="/admin/upload/",
        user=user,
        status_code=200,
        duration_ms=0.0
    )
    
    # Get configuration for display
    config = get_config()
    admin_config = getattr(config, 'admin_upload', {})
    
    context = {
        "request": request,
        "user": user,
        "max_file_size_mb": getattr(admin_config, 'max_file_size_mb', 100),
        "supported_formats": getattr(admin_config, 'supported_formats', ['.xlsx', '.xls', '.parquet']),
        "recommend_parquet_threshold_mb": getattr(admin_config, 'recommend_parquet_threshold_mb', 10)
    }
    
    return templates.TemplateResponse("admin_upload.html", context)


@router.post("/tnved", response_model=AdminUploadResponse)
async def upload_tnved_data(
    file: UploadFile = File(...),
    source_name: str = Form(...),
    user: str = Depends(require_auth)
):
    """
    Upload TNVED codes with descriptions.
    
    Args:
        file: Uploaded file (Excel or Parquet format)
        source_name: Data source identifier
        user: Authenticated user from require_auth dependency
        
    Returns:
        AdminUploadResponse with upload details and summary
        
    Raises:
        HTTPException: For validation errors, file errors, or processing failures
    """
    upload_id = f"tnved_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    temp_file_path = None
    
    logger.info(f"TNVED upload initiated by user {user}: {file.filename}, source: {source_name}")
    
    # Log upload initiation
    structured_logger.log_admin_upload_initiation(
        user=user,
        upload_id=upload_id,
        upload_type="tnved",
        filename=file.filename,
        file_size=0,  # Will be updated after file is read
        source_name=source_name,
        total_records=0  # Will be updated after validation
    )
    
    try:
        # Step 1: Validate file format and size
        is_valid_format, format_error = validator.validate_file_format(file)
        if not is_valid_format:
            structured_logger.log_error(
                ValueError(format_error),
                context={
                    "user": user,
                    "upload_id": upload_id,
                    "error_type": "file_format",
                    "filename": file.filename
                },
                user=user
            )
            raise HTTPException(status_code=400, detail=format_error)
        
        # Step 2: Validate source name
        is_valid_source, source_error = validator.validate_source_name(source_name)
        if not is_valid_source:
            structured_logger.log_error(
                ValueError(source_error),
                context={
                    "user": user,
                    "upload_id": upload_id,
                    "error_type": "source_name",
                    "source_name": source_name
                },
                user=user
            )
            raise HTTPException(status_code=400, detail=source_error)
        
        # Step 3: Save file to temporary location
        config = get_config()
        temp_dir = Path(getattr(config.admin_upload, 'temp_dir', './temp_uploads')) / user
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file_path = temp_dir / f"{upload_id}_{file.filename}"
        
        # Save uploaded file
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        file_size = len(content)
        
        logger.info(f"File saved to temporary location: {temp_file_path} ({file_size} bytes)")
        
        # Step 4: Validate file content
        validation_result = validator.validate_tnved_file(temp_file_path)
        if not validation_result.is_valid:
            # Log validation failure
            structured_logger.log_admin_validation_failure(
                user=user,
                upload_id=upload_id,
                upload_type="tnved",
                filename=file.filename,
                error_type="validation_failed",
                error_details={
                    "message": validation_result.error_message,
                    "missing_columns": validation_result.missing_columns
                }
            )
            
            raise AdminValidationError(
                message=validation_result.error_message,
                missing_columns=validation_result.missing_columns,
                file_info=validation_result.file_info,
                upload_id=upload_id,
                error_code="MISSING_COLUMNS" if validation_result.missing_columns else "VALIDATION_FAILED"
            )
        
        # Log successful validation and final upload initiation with all details
        structured_logger.log_admin_upload_initiation(
            user=user,
            upload_id=upload_id,
            upload_type="tnved",
            filename=file.filename,
            file_size=file_size,
            source_name=source_name,
            total_records=validation_result.total_rows
        )
        
        # Step 5: Initialize progress tracking
        progress_update = AdminProgressUpdate(
            upload_id=upload_id,
            processed=0,
            total=validation_result.total_rows,
            progress_pct=0.0,
            records_per_sec=0.0,
            eta_seconds=0.0,
            status="starting"
        )
        upload_progress[upload_id] = progress_update
        
        # Step 6: Process using TNVEDUploadProcessor asynchronously
        def progress_callback(update: AdminProgressUpdate):
            """Update progress tracking."""
            upload_progress[upload_id] = update
            
            # Log batch processing progress
            if update.current_batch:
                structured_logger.log_admin_processing_batch(
                    upload_id=upload_id,
                    user=user,
                    batch_number=update.current_batch,
                    processed_records=update.processed,
                    total_records=update.total,
                    batch_size=batch_size,
                    duration_ms=time.time() * 1000,
                    error_count=0
                )
            else:
                # Fallback to general processing progress log
                structured_logger.log_processing_progress(
                    task_id=upload_id,
                    session_id=upload_id,
                    processed_rows=update.processed,
                    total_rows=update.total,
                    error_count=0,
                    duration_ms=time.time() * 1000
                )
        
        # Initialize processor
        db_path = getattr(config, 'chroma_db_path', './chroma_db')
        batch_size = getattr(config.admin_upload, 'batch_size', 5000)
        processor = TNVEDUploadProcessor(db_path=db_path, batch_size=batch_size)
        
        # Process upload in background task
        async def process_upload():
            try:
                summary = await processor.process_upload(
                    file_path=temp_file_path,
                    source_name=source_name,
                    progress_callback=progress_callback
                )
                
                # Update final progress
                final_progress = AdminProgressUpdate(
                    upload_id=upload_id,
                    processed=summary.successful_records,
                    total=summary.total_records,
                    progress_pct=100.0,
                    records_per_sec=summary.records_per_second,
                    eta_seconds=0.0,
                    status="completed"
                )
                upload_progress[upload_id] = final_progress
                
                structured_logger.log_processing_complete(
                    task_id=upload_id,
                    session_id=upload_id,
                    user=user,
                    success=True,
                    processed_rows=summary.successful_records,
                    error_count=summary.failed_records,
                    duration_ms=summary.processing_time_seconds * 1000
                )
                
            except Exception as e:
                logger.error(f"Error processing TNVED upload {upload_id}: {e}", exc_info=True)
                
                error_progress = AdminProgressUpdate(
                    upload_id=upload_id,
                    processed=0,
                    total=validation_result.total_rows,
                    progress_pct=0.0,
                    records_per_sec=0.0,
                    eta_seconds=0.0,
                    status="failed"
                )
                upload_progress[upload_id] = error_progress
                
                structured_logger.log_error(
                    e,
                    context={
                        "user": user,
                        "upload_id": upload_id,
                        "error_type": "processing",
                        "filename": file.filename
                    },
                    user=user,
                    task_id=upload_id
                )
            finally:
                # Clean up temporary file
                if temp_file_path and temp_file_path.exists():
                    temp_file_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
        
        # Start processing task
        asyncio.create_task(process_upload())
        
        # Step 7: Return immediate response
        response = AdminUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            upload_type="tnved",
            source_name=source_name,
            total_records=validation_result.total_rows,
            message=f"TNVED upload initiated successfully. Processing {validation_result.total_rows} records."
        )
        
        structured_logger.log_file_upload(
            user=user,
            session_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            success=True
        )
        
        return response
        
    except AdminUploadException:
        # Re-raise admin upload exceptions (they will be handled by exception handlers)
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in TNVED upload: {e}", exc_info=True)
        
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        
        raise AdminProcessingError(
            message=f"Internal server error during TNVED upload: {str(e)}",
            upload_id=upload_id,
            error_code="INTERNAL_ERROR"
        )

@router.post("/urls", response_model=AdminUploadResponse)
async def upload_url_mappings(
    file: UploadFile = File(...),
    source_name: str = Form(...),
    user: str = Depends(require_auth)
):
    """
    Upload URL-to-TNVED code mappings.
    
    Args:
        file: Uploaded file (Excel or Parquet format)
        source_name: Data source identifier
        user: Authenticated user from require_auth dependency
        
    Returns:
        AdminUploadResponse with upload details and summary
        
    Raises:
        HTTPException: For validation errors, file errors, or processing failures
    """
    upload_id = f"urls_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    temp_file_path = None
    
    logger.info(f"URL upload initiated by user {user}: {file.filename}, source: {source_name}")
    
    # Log upload initiation
    structured_logger.log_admin_upload_initiation(
        user=user,
        upload_id=upload_id,
        upload_type="urls",
        filename=file.filename,
        file_size=0,  # Will be updated after file is read
        source_name=source_name,
        total_records=0  # Will be updated after validation
    )
    
    try:
        # Step 1: Validate file format and size
        is_valid_format, format_error = validator.validate_file_format(file)
        if not is_valid_format:
            raise AdminFormatError(
                message=format_error,
                file_extension=Path(file.filename).suffix.lower() if file.filename else "",
                supported_formats=validator.SUPPORTED_FORMATS,
                upload_id=upload_id,
                error_code="UNSUPPORTED_FORMAT"
            )
        
        # Step 2: Validate source name
        is_valid_source, source_error = validator.validate_source_name(source_name)
        if not is_valid_source:
            raise AdminSourceNameError(
                message=source_error,
                source_name=source_name,
                upload_id=upload_id,
                error_code="INVALID_SOURCE_NAME"
            )
        
        # Step 3: Save file to temporary location
        config = get_config()
        temp_dir = Path(getattr(config.admin_upload, 'temp_dir', './temp_uploads')) / user
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file_path = temp_dir / f"{upload_id}_{file.filename}"
        
        # Save uploaded file
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        file_size = len(content)
        
        logger.info(f"File saved to temporary location: {temp_file_path} ({file_size} bytes)")
        
        # Step 4: Validate file content
        validation_result = validator.validate_url_file(temp_file_path)
        if not validation_result.is_valid:
            # Log validation failure
            structured_logger.log_admin_validation_failure(
                user=user,
                upload_id=upload_id,
                upload_type="urls",
                filename=file.filename,
                error_type="validation_failed",
                error_details={
                    "message": validation_result.error_message,
                    "missing_columns": validation_result.missing_columns
                }
            )
            
            raise AdminValidationError(
                message=validation_result.error_message,
                missing_columns=validation_result.missing_columns,
                file_info=validation_result.file_info,
                upload_id=upload_id,
                error_code="MISSING_COLUMNS" if validation_result.missing_columns else "VALIDATION_FAILED"
            )
        
        # Log successful validation and final upload initiation with all details
        structured_logger.log_admin_upload_initiation(
            user=user,
            upload_id=upload_id,
            upload_type="urls",
            filename=file.filename,
            file_size=file_size,
            source_name=source_name,
            total_records=validation_result.total_rows
        )
        
        # Step 5: Initialize progress tracking
        progress_update = AdminProgressUpdate(
            upload_id=upload_id,
            processed=0,
            total=validation_result.total_rows,
            progress_pct=0.0,
            records_per_sec=0.0,
            eta_seconds=0.0,
            status="starting"
        )
        upload_progress[upload_id] = progress_update
        
        # Step 6: Process using URLUploadProcessor asynchronously
        def progress_callback(update: AdminProgressUpdate):
            """Update progress tracking."""
            upload_progress[upload_id] = update
            
            # Log batch processing progress
            if update.current_batch:
                structured_logger.log_admin_processing_batch(
                    upload_id=upload_id,
                    user=user,
                    batch_number=update.current_batch,
                    processed_records=update.processed,
                    total_records=update.total,
                    batch_size=batch_size,
                    duration_ms=time.time() * 1000,
                    error_count=0
                )
            else:
                # Fallback to general processing progress log
                structured_logger.log_processing_progress(
                    task_id=upload_id,
                    session_id=upload_id,
                    processed_rows=update.processed,
                    total_rows=update.total,
                    error_count=0,
                    duration_ms=time.time() * 1000
                )
        
        # Initialize processor with ChromaDB client
        import chromadb
        chroma_client = chromadb.PersistentClient(
            path=getattr(config, 'chroma_db_path', './chroma_db')
        )
        batch_size = getattr(config.admin_upload, 'batch_size', 5000)
        processor = URLUploadProcessor(chroma_client=chroma_client, batch_size=batch_size)
        
        # Process upload in background task
        async def process_upload():
            try:
                summary = await processor.process_upload(
                    file_path=temp_file_path,
                    source_name=source_name,
                    progress_callback=progress_callback
                )
                
                # Update final progress
                final_progress = AdminProgressUpdate(
                    upload_id=upload_id,
                    processed=summary.successful_records,
                    total=summary.total_records,
                    progress_pct=100.0,
                    records_per_sec=summary.records_per_second,
                    eta_seconds=0.0,
                    status="completed"
                )
                upload_progress[upload_id] = final_progress
                
                structured_logger.log_processing_complete(
                    task_id=upload_id,
                    session_id=upload_id,
                    user=user,
                    success=True,
                    processed_rows=summary.successful_records,
                    error_count=summary.failed_records,
                    duration_ms=summary.processing_time_seconds * 1000
                )
                
            except Exception as e:
                logger.error(f"Error processing URL upload {upload_id}: {e}", exc_info=True)
                
                error_progress = AdminProgressUpdate(
                    upload_id=upload_id,
                    processed=0,
                    total=validation_result.total_rows,
                    progress_pct=0.0,
                    records_per_sec=0.0,
                    eta_seconds=0.0,
                    status="failed"
                )
                upload_progress[upload_id] = error_progress
                
                structured_logger.log_error(
                    e,
                    context={
                        "user": user,
                        "upload_id": upload_id,
                        "error_type": "processing",
                        "filename": file.filename
                    },
                    user=user,
                    task_id=upload_id
                )
            finally:
                # Clean up temporary file
                if temp_file_path and temp_file_path.exists():
                    temp_file_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
        
        # Start processing task
        asyncio.create_task(process_upload())
        
        # Step 7: Return immediate response
        response = AdminUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            upload_type="urls",
            source_name=source_name,
            total_records=validation_result.total_rows,
            message=f"URL mapping upload initiated successfully. Processing {validation_result.total_rows} records."
        )
        
        structured_logger.log_file_upload(
            user=user,
            session_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            success=True
        )
        
        return response
        
    except AdminUploadException:
        # Re-raise admin upload exceptions (they will be handled by exception handlers)
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in URL upload: {e}", exc_info=True)
        
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        
        raise AdminProcessingError(
            message=f"Internal server error during URL upload: {str(e)}",
            upload_id=upload_id,
            error_code="INTERNAL_ERROR"
        )
@router.post("/validate", response_model=AdminValidationResult)
async def validate_admin_file(
    file: UploadFile = File(...),
    upload_type: str = Form(...),
    user: str = Depends(require_auth)
):
    """
    Validate file without processing.
    
    Args:
        file: Uploaded file to validate
        upload_type: Type of upload ('tnved' or 'urls')
        user: Authenticated user from require_auth dependency
        
    Returns:
        AdminValidationResult with validation details
        
    Raises:
        HTTPException: For validation errors or unsupported upload types
    """
    validation_id = f"validate_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    temp_file_path = None
    
    logger.info(f"File validation initiated by user {user}: {file.filename}, type: {upload_type}")
    
    try:
        # Step 1: Validate upload type
        if upload_type not in ['tnved', 'urls']:
            raise AdminValidationError(
                message=f"Invalid upload type '{upload_type}'. Must be 'tnved' or 'urls'.",
                upload_id=validation_id,
                error_code="INVALID_UPLOAD_TYPE"
            )
        
        # Step 2: Validate file format and size
        is_valid_format, format_error = validator.validate_file_format(file)
        if not is_valid_format:
            structured_logger.log_error(
                ValueError(format_error),
                context={
                    "user": user,
                    "upload_id": validation_id,
                    "error_type": "file_format",
                    "filename": file.filename
                },
                user=user
            )
            
            return AdminValidationResult(
                is_valid=False,
                upload_type=upload_type,
                error_message=format_error,
                total_records=0,
                missing_columns=[],
                file_info={},
                warnings=[]
            )
        
        # Step 3: Save file to temporary location for validation
        config = get_config()
        temp_dir = Path(getattr(config.admin_upload, 'temp_dir', './temp_uploads')) / user
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file_path = temp_dir / f"{validation_id}_{file.filename}"
        
        # Save uploaded file
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        file_size = len(content)
        
        logger.debug(f"File saved for validation: {temp_file_path} ({file_size} bytes)")
        
        # Step 4: Perform content validation based on upload type
        if upload_type == 'tnved':
            validation_result = validator.validate_tnved_file(temp_file_path)
        else:  # upload_type == 'urls'
            validation_result = validator.validate_url_file(temp_file_path)
        
        # Step 5: Convert ValidationResult to AdminValidationResult
        warnings = []
        
        # Add file size warnings
        large_file_threshold = getattr(config.admin_upload, 'large_file_threshold_mb', 50) * 1024 * 1024
        parquet_threshold = getattr(config.admin_upload, 'recommend_parquet_threshold_mb', 10) * 1024 * 1024
        
        if file_size > large_file_threshold:
            warnings.append(f"Large file detected ({file_size / (1024*1024):.1f}MB). Processing may take longer.")
        
        if file_size > parquet_threshold and temp_file_path.suffix.lower() in ['.xlsx', '.xls']:
            warnings.append(f"Consider using Parquet format for files larger than {parquet_threshold / (1024*1024):.0f}MB for better performance.")
        
        # Add file info
        file_info = validation_result.file_info.copy()
        file_info.update({
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024*1024), 2),
            "filename": file.filename
        })
        
        admin_validation_result = AdminValidationResult(
            is_valid=validation_result.is_valid,
            upload_type=upload_type,
            error_message=validation_result.error_message,
            total_records=validation_result.total_rows,
            missing_columns=validation_result.missing_columns,
            file_info=file_info,
            warnings=warnings
        )
        
        # Log validation result
        structured_logger.log_system_event(
            event_type="file_validation",
            message=f"File validation for {file.filename}: {'valid' if validation_result.is_valid else 'invalid'}",
            extra_data={
                "user": user,
                "validation_id": validation_id,
                "upload_type": upload_type,
                "filename": file.filename,
                "file_size": file_size,
                "is_valid": validation_result.is_valid,
                "total_records": validation_result.total_rows,
                "error_message": validation_result.error_message,
                "missing_columns": validation_result.missing_columns
            }
        )
        
        return admin_validation_result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error during file validation: {e}", exc_info=True)
        
        structured_logger.log_error(
            e,
            context={
                "user": user,
                "upload_id": validation_id,
                "error_type": "validation_error",
                "filename": file.filename
            },
            user=user
        )
        
        return AdminValidationResult(
            is_valid=False,
            upload_type=upload_type,
            error_message=f"Validation error: {str(e)}",
            total_records=0,
            missing_columns=[],
            file_info={},
            warnings=[]
        )
    finally:
        # Clean up temporary file
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
            logger.debug(f"Cleaned up validation temporary file: {temp_file_path}")


@router.get("/progress/{upload_id}")
async def get_upload_progress(
    upload_id: str,
    user: str = Depends(require_auth)
):
    """
    Get progress for a specific upload.
    
    Args:
        upload_id: Upload identifier
        user: Authenticated user from require_auth dependency
        
    Returns:
        AdminProgressUpdate with current progress
        
    Raises:
        HTTPException: If upload ID not found
    """
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail=f"Upload ID '{upload_id}' not found")
    
    return upload_progress[upload_id]


@router.get("/summary/{upload_id}")
async def get_upload_summary(
    upload_id: str,
    user: str = Depends(require_auth)
):
    """
    Get summary for a completed upload.
    
    Args:
        upload_id: Upload identifier
        user: Authenticated user from require_auth dependency
        
    Returns:
        Upload summary information
        
    Raises:
        HTTPException: If upload ID not found or upload not completed
    """
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail=f"Upload ID '{upload_id}' not found")
    
    progress = upload_progress[upload_id]
    
    if progress.status not in ['completed', 'failed']:
        raise HTTPException(
            status_code=400, 
            detail=f"Upload '{upload_id}' is not completed (status: {progress.status})"
        )
    
    # For now, return the progress info as summary
    # In a full implementation, this would return a more detailed UploadSummary
    return {
        "upload_id": upload_id,
        "status": progress.status,
        "total_records": progress.total,
        "processed_records": progress.processed,
        "progress_pct": progress.progress_pct,
        "records_per_sec": progress.records_per_sec,
        "timestamp": progress.timestamp
    }