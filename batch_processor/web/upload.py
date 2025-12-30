"""
File upload endpoints and validation for the batch Excel processor.

This module provides file upload functionality with validation,
task creation, and session management.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..config.settings import get_config, ProcessingMode, AlgorithmType
from ..services.excel_processor import ExcelProcessor
from ..services.file_manager import FileManager
from ..workers.celery_app import celery_app
from .auth import require_auth
from .models import ProcessingRequest, UploadResponse, ValidationResult, ErrorResponse


logger = logging.getLogger(__name__)

# Create router for upload endpoints
router = APIRouter(prefix="/upload", tags=["upload"])

# Initialize services
excel_processor = ExcelProcessor()
file_manager = FileManager()


def validate_uploaded_file(file: UploadFile) -> Tuple[bool, str, dict]:
    """
    Validate uploaded file format and basic properties.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (is_valid, error_message, file_info)
    """
    config = get_config()
    
    # Check file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in config.processing.supported_extensions:
        return False, f"Unsupported file format. Supported formats: {', '.join(config.processing.supported_extensions)}", {}
    
    # Check file size (approximate, since we can't get exact size without reading)
    if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
        # Try to get file size
        current_pos = file.file.tell()
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(current_pos)  # Restore position
        
        max_size_bytes = config.processing.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File too large. Maximum size: {config.processing.max_file_size_mb}MB", {}
    
    file_info = {
        "filename": file.filename,
        "content_type": file.content_type,
        "extension": file_extension
    }
    
    return True, "", file_info


async def validate_excel_content(file_path: Path) -> ValidationResult:
    """
    Validate Excel file content and structure.
    
    Args:
        file_path: Path to the uploaded Excel file
        
    Returns:
        ValidationResult with validation details
    """
    try:
        is_valid, error_message, total_rows = excel_processor.validate_file(file_path)
        
        if not is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=error_message,
                total_rows=0,
                rows_with_descriptions=0,
                rows_with_existing_codes=0,
                missing_columns=[],
                file_info={}
            )
        
        # Get detailed file information
        file_info = excel_processor.get_file_info(file_path)
        
        return ValidationResult(
            is_valid=True,
            total_rows=file_info["total_rows"],
            rows_with_descriptions=file_info["rows_with_descriptions"],
            rows_with_existing_codes=file_info["rows_with_existing_codes"],
            missing_columns=[],
            file_info=file_info
        )
        
    except Exception as e:
        logger.error(f"Error validating Excel content: {e}")
        return ValidationResult(
            is_valid=False,
            error_message=f"Failed to validate Excel file: {str(e)}",
            total_rows=0,
            rows_with_descriptions=0,
            rows_with_existing_codes=0,
            missing_columns=[],
            file_info={}
        )


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="Excel file to process"),
    process_mode: ProcessingMode = Form(default=ProcessingMode.ALL, description="Processing mode"),
    algorithm: AlgorithmType = Form(default=AlgorithmType.SIMILARITY_TOP1, description="Algorithm to use"),
    user: str = Depends(require_auth)
):
    """
    Upload Excel file and create processing task.
    
    This endpoint accepts an Excel file upload, validates it, and creates
    a background processing task. Returns task information for tracking.
    """
    try:
        # Validate file format and basic properties
        is_valid, error_msg, file_info = validate_uploaded_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Create session and save file
        session_id = str(uuid.uuid4())
        session_dir = file_manager.create_session_directory(session_id)
        
        # Save uploaded file
        file_path = await file_manager.save_uploaded_file(session_id, file)
        logger.info(f"File uploaded: {file_path} for user: {user}")
        
        # Validate Excel content
        validation_result = await validate_excel_content(file_path)
        if not validation_result.is_valid:
            # Clean up file on validation failure
            file_manager.cleanup_session(session_id)
            raise HTTPException(status_code=400, detail=validation_result.error_message)
        
        # Calculate rows to process based on mode
        if process_mode == ProcessingMode.EMPTY_ONLY:
            rows_to_process = validation_result.rows_with_descriptions - validation_result.rows_with_existing_codes
        else:
            rows_to_process = validation_result.rows_with_descriptions
        
        # Create processing task
        task_result = celery_app.send_task(
            'batch_processor.workers.processing_task.process_file',
            args=[
                session_id,
                str(file_path),
                process_mode.value,
                algorithm.value,
                user
            ]
        )
        
        task_id = task_result.id
        logger.info(f"Created processing task {task_id} for session {session_id}")
        
        # Schedule file cleanup
        file_manager.schedule_cleanup(session_id)
        
        return UploadResponse(
            task_id=task_id,
            session_id=session_id,
            filename=file.filename,
            file_size=file_info.get("file_size", 0),
            total_rows=validation_result.total_rows,
            rows_to_process=rows_to_process,
            processing_mode=process_mode,
            algorithm=algorithm,
            message=f"File uploaded successfully. Processing {rows_to_process} rows with {algorithm.value} algorithm."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResult)
async def validate_file_only(
    file: UploadFile = File(..., description="Excel file to validate"),
    user: str = Depends(require_auth)
):
    """
    Validate Excel file without processing.
    
    This endpoint validates an uploaded Excel file and returns
    detailed information about its structure and content.
    """
    try:
        # Validate file format
        is_valid, error_msg, file_info = validate_uploaded_file(file)
        if not is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                total_rows=0,
                rows_with_descriptions=0,
                rows_with_existing_codes=0,
                missing_columns=[],
                file_info=file_info
            )
        
        # Create temporary session for validation
        temp_session_id = str(uuid.uuid4())
        
        try:
            # Save file temporarily
            file_path = await file_manager.save_uploaded_file(temp_session_id, file)
            
            # Validate Excel content
            validation_result = await validate_excel_content(file_path)
            validation_result.file_info.update(file_info)
            
            return validation_result
            
        finally:
            # Always clean up temporary file
            file_manager.cleanup_session(temp_session_id)
        
    except Exception as e:
        logger.error(f"Error validating file: {e}", exc_info=True)
        return ValidationResult(
            is_valid=False,
            error_message=f"Failed to validate file: {str(e)}",
            total_rows=0,
            rows_with_descriptions=0,
            rows_with_existing_codes=0,
            missing_columns=[],
            file_info={}
        )