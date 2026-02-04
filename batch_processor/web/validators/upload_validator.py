"""
Admin upload file validator.

This module provides validation functionality for admin data uploads,
including file format validation, source name validation, and content validation.
"""

import re
import pandas as pd
from pathlib import Path
from typing import Tuple, List
from fastapi import UploadFile

from ..models import ValidationResult


class AdminUploadValidator:
    """Validates admin upload files for TNVED codes and URL mappings."""
    
    # Required columns for different upload types
    TNVED_REQUIRED_COLUMNS = ["Code", "Description"]
    URL_REQUIRED_COLUMNS = ["URL", "Code"]
    URL_OPTIONAL_COLUMNS = ["Description"]
    
    # Supported file formats
    SUPPORTED_FORMATS = [".xlsx", ".xls", ".parquet"]
    
    # File size limits
    MAX_FILE_SIZE_MB = 100
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Source name validation pattern (alphanumeric, hyphens, underscores)
    SOURCE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    def validate_file_format(self, file: UploadFile) -> Tuple[bool, str]:
        """
        Validate file extension and size.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        if not file.filename:
            return False, "No filename provided"
            
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported file format '{file_extension}'. Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
        
        # Check file size if available
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            try:
                # Get current position
                current_pos = file.file.tell()
                # Seek to end to get size
                file.file.seek(0, 2)
                file_size = file.file.tell()
                # Restore original position
                file.file.seek(current_pos)
                
                if file_size > self.MAX_FILE_SIZE_BYTES:
                    return False, f"File too large ({file_size / (1024*1024):.1f}MB). Maximum size: {self.MAX_FILE_SIZE_MB}MB"
            except Exception:
                # If we can't determine size, continue with validation
                pass
        
        return True, ""
    
    def validate_source_name(self, source_name: str) -> Tuple[bool, str]:
        """
        Validate source name format (alphanumeric, hyphens, underscores only).
        
        Args:
            source_name: Source name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not source_name:
            return False, "Source name is required"
        
        if not source_name.strip():
            return False, "Source name cannot be empty or whitespace only"
        
        # Check length (reasonable limits)
        if len(source_name) > 100:
            return False, "Source name too long (maximum 100 characters)"
        
        if len(source_name) < 2:
            return False, "Source name too short (minimum 2 characters)"
        
        # Check pattern (alphanumeric, hyphens, underscores only)
        if not self.SOURCE_NAME_PATTERN.match(source_name):
            return False, "Source name can only contain alphanumeric characters, hyphens, and underscores"
        
        return True, ""
    
    def validate_tnved_file(self, file_path: Path) -> ValidationResult:
        """
        Validate TNVED data file structure and content.
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            ValidationResult with validation details
        """
        try:
            # Read file based on extension
            file_extension = file_path.suffix.lower()
            
            if file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl')
            elif file_extension == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsupported file format: {file_extension}",
                    total_rows=0,
                    rows_with_descriptions=0,
                    rows_with_existing_codes=0,
                    missing_columns=[],
                    file_info={}
                )
            
            # Check if file is empty
            if df.empty:
                return ValidationResult(
                    is_valid=False,
                    error_message="File is empty (no data rows)",
                    total_rows=0,
                    rows_with_descriptions=0,
                    rows_with_existing_codes=0,
                    missing_columns=[],
                    file_info={}
                )
            
            # Check for required columns
            missing_columns = []
            for required_col in self.TNVED_REQUIRED_COLUMNS:
                if required_col not in df.columns:
                    missing_columns.append(required_col)
            
            if missing_columns:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required columns: {', '.join(missing_columns)}",
                    total_rows=len(df),
                    rows_with_descriptions=0,
                    rows_with_existing_codes=0,
                    missing_columns=missing_columns,
                    file_info={
                        "available_columns": list(df.columns),
                        "file_extension": file_extension
                    }
                )
            
            # Calculate statistics
            total_rows = len(df)
            
            # Count rows with non-empty descriptions
            rows_with_descriptions = 0
            if 'Description' in df.columns:
                rows_with_descriptions = df['Description'].notna().sum()
            
            # For TNVED files, we don't track existing codes (that's for processing files)
            rows_with_existing_codes = 0
            
            # Prepare file info
            file_info = {
                "available_columns": list(df.columns),
                "file_extension": file_extension,
                "total_rows": total_rows,
                "rows_with_descriptions": int(rows_with_descriptions)
            }
            
            return ValidationResult(
                is_valid=True,
                error_message=None,
                total_rows=total_rows,
                rows_with_descriptions=int(rows_with_descriptions),
                rows_with_existing_codes=rows_with_existing_codes,
                missing_columns=[],
                file_info=file_info
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Failed to read file: {str(e)}",
                total_rows=0,
                rows_with_descriptions=0,
                rows_with_existing_codes=0,
                missing_columns=[],
                file_info={}
            )
    
    def validate_url_file(self, file_path: Path) -> ValidationResult:
        """
        Validate URL mapping data file structure and content.
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            ValidationResult with validation details
        """
        try:
            # Read file based on extension
            file_extension = file_path.suffix.lower()
            
            if file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl')
            elif file_extension == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsupported file format: {file_extension}",
                    total_rows=0,
                    rows_with_descriptions=0,
                    rows_with_existing_codes=0,
                    missing_columns=[],
                    file_info={}
                )
            
            # Check if file is empty
            if df.empty:
                return ValidationResult(
                    is_valid=False,
                    error_message="File is empty (no data rows)",
                    total_rows=0,
                    rows_with_descriptions=0,
                    rows_with_existing_codes=0,
                    missing_columns=[],
                    file_info={}
                )
            
            # Check for required columns
            missing_columns = []
            for required_col in self.URL_REQUIRED_COLUMNS:
                if required_col not in df.columns:
                    missing_columns.append(required_col)
            
            if missing_columns:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required columns: {', '.join(missing_columns)}",
                    total_rows=len(df),
                    rows_with_descriptions=0,
                    rows_with_existing_codes=0,
                    missing_columns=missing_columns,
                    file_info={
                        "available_columns": list(df.columns),
                        "file_extension": file_extension
                    }
                )
            
            # Calculate statistics
            total_rows = len(df)
            
            # Count rows with non-empty descriptions (optional column)
            rows_with_descriptions = 0
            if 'Description' in df.columns:
                rows_with_descriptions = df['Description'].notna().sum()
            
            # For URL files, we don't track existing codes (that's for processing files)
            rows_with_existing_codes = 0
            
            # Check if optional columns are present
            optional_columns_present = []
            for optional_col in self.URL_OPTIONAL_COLUMNS:
                if optional_col in df.columns:
                    optional_columns_present.append(optional_col)
            
            # Prepare file info
            file_info = {
                "available_columns": list(df.columns),
                "file_extension": file_extension,
                "total_rows": total_rows,
                "rows_with_descriptions": int(rows_with_descriptions),
                "optional_columns_present": optional_columns_present,
                "has_description_column": 'Description' in df.columns
            }
            
            return ValidationResult(
                is_valid=True,
                error_message=None,
                total_rows=total_rows,
                rows_with_descriptions=int(rows_with_descriptions),
                rows_with_existing_codes=rows_with_existing_codes,
                missing_columns=[],
                file_info=file_info
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Failed to read file: {str(e)}",
                total_rows=0,
                rows_with_descriptions=0,
                rows_with_existing_codes=0,
                missing_columns=[],
                file_info={}
            )