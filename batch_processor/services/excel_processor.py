"""Excel file processing utilities for batch processor."""

import pandas as pd
import logging
from pathlib import Path
from typing import Iterator, Tuple, Optional, List, Dict, Any
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of Excel file validation."""
    is_valid: bool
    error_message: str
    total_rows: int
    has_description_column: bool = False
    has_hts_code_column: bool = False
    empty_descriptions: int = 0
    existing_hts_codes: int = 0


class ExcelProcessor:
    """Handles Excel file processing with memory-efficient chunked reading."""
    
    def __init__(self, chunk_size: int = 1000):
        """
        Initialize ExcelProcessor.
        
        Args:
            chunk_size: Number of rows to process in each chunk for memory efficiency
        """
        self.chunk_size = chunk_size
        self.required_columns = ["Product Detailed Description"]
        self.optional_columns = ["HTS Code"]
        
        logger.info(f"ExcelProcessor initialized with chunk_size={chunk_size}")
    
    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate Excel file format and required columns.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            ValidationResult with validation status and metadata
        """
        logger.info(f"Validating Excel file: {file_path}")
        
        try:
            # Check if file exists
            if not file_path.exists():
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File not found: {file_path}",
                    total_rows=0
                )
            
            # Check file extension
            if file_path.suffix.lower() not in ['.xlsx', '.xls']:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid file format. Expected .xlsx or .xls, got {file_path.suffix}",
                    total_rows=0
                )
            
            # Try to read the file header to check structure
            try:
                # Read just the first few rows to check columns
                df_sample = pd.read_excel(file_path, nrows=5, engine='openpyxl')
                
                if df_sample.empty:
                    return ValidationResult(
                        is_valid=False,
                        error_message="File is empty or contains no data",
                        total_rows=0
                    )
                
                # Check for required columns
                columns = df_sample.columns.tolist()
                has_description = any(
                    col for col in columns 
                    if "Product Detailed Description" in str(col)
                )
                
                if not has_description:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Required column 'Product Detailed Description' not found. Available columns: {columns}",
                        total_rows=len(df_sample),
                        has_description_column=False
                    )
                
                # Check for optional HTS Code column
                has_hts_code = any(
                    col for col in columns 
                    if "HTS Code" in str(col) or "HTS_Code" in str(col)
                )
                
                # Get total row count efficiently
                df_full = pd.read_excel(file_path, engine='openpyxl')
                total_rows = len(df_full)
                
                # Count empty descriptions and existing HTS codes
                description_col = next(
                    col for col in df_full.columns 
                    if "Product Detailed Description" in str(col)
                )
                
                empty_descriptions = df_full[description_col].isna().sum() + \
                                   (df_full[description_col].astype(str).str.strip() == '').sum()
                
                existing_hts_codes = 0
                if has_hts_code:
                    hts_col = next(
                        (col for col in df_full.columns 
                         if "HTS Code" in str(col) or "HTS_Code" in str(col)), 
                        None
                    )
                    if hts_col:
                        existing_hts_codes = (~df_full[hts_col].isna()).sum() - \
                                           (df_full[hts_col].astype(str).str.strip() == '').sum()
                
                logger.info(f"File validation successful: {total_rows} rows, "
                           f"{empty_descriptions} empty descriptions, "
                           f"{existing_hts_codes} existing HTS codes")
                
                return ValidationResult(
                    is_valid=True,
                    error_message="",
                    total_rows=total_rows,
                    has_description_column=True,
                    has_hts_code_column=has_hts_code,
                    empty_descriptions=empty_descriptions,
                    existing_hts_codes=existing_hts_codes
                )
                
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Failed to read Excel file: {str(e)}",
                    total_rows=0
                )
                
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
                total_rows=0
            )
    
    def read_file_chunked(
        self, 
        file_path: Path, 
        process_mode: str = "all"
    ) -> Iterator[Tuple[pd.DataFrame, int, int]]:
        """
        Read Excel file in chunks for memory-efficient processing.
        
        Args:
            file_path: Path to the Excel file
            process_mode: "all" to process all rows, "empty_only" to process only rows without HTS codes
            
        Yields:
            Tuple of (chunk_dataframe, chunk_start_row, total_rows)
        """
        logger.info(f"Reading file in chunks: {file_path}, mode: {process_mode}")
        
        try:
            # First, get the total row count
            df_full = pd.read_excel(file_path, engine='openpyxl')
            total_rows = len(df_full)
            
            # Find the description column
            description_col = next(
                col for col in df_full.columns 
                if "Product Detailed Description" in str(col)
            )
            
            # Find HTS Code column if it exists
            hts_col = None
            for col in df_full.columns:
                if "HTS Code" in str(col) or "HTS_Code" in str(col):
                    hts_col = col
                    break
            
            # Process in chunks
            for start_row in range(0, total_rows, self.chunk_size):
                end_row = min(start_row + self.chunk_size, total_rows)
                chunk = df_full.iloc[start_row:end_row].copy()
                
                # Filter chunk based on process_mode
                filtered_chunk = self.filter_rows_for_processing(chunk, process_mode)
                
                if not filtered_chunk.empty:
                    logger.debug(f"Yielding chunk: rows {start_row}-{end_row-1}, "
                               f"{len(filtered_chunk)} rows to process")
                    yield filtered_chunk, start_row, total_rows
                else:
                    logger.debug(f"Skipping empty chunk: rows {start_row}-{end_row-1}")
                    
        except Exception as e:
            logger.error(f"Failed to read file in chunks: {e}")
            raise
    
    def filter_rows_for_processing(
        self, 
        df: pd.DataFrame, 
        process_mode: str
    ) -> pd.DataFrame:
        """
        Filter rows based on processing mode.
        
        Args:
            df: DataFrame chunk to filter
            process_mode: "all" or "empty_only"
            
        Returns:
            Filtered DataFrame
        """
        if process_mode not in ["all", "empty_only"]:
            raise ValueError(f"Invalid process_mode: {process_mode}. Must be 'all' or 'empty_only'")
        
        # Find the description column
        description_col = next(
            (col for col in df.columns if "Product Detailed Description" in str(col)), 
            None
        )
        
        if not description_col:
            logger.warning("No 'Product Detailed Description' column found")
            return pd.DataFrame()
        
        # Always filter out rows with empty descriptions
        mask = df[description_col].notna() & (df[description_col].astype(str).str.strip() != '')
        
        if process_mode == "empty_only":
            # Additionally filter out rows that already have HTS codes
            hts_col = None
            for col in df.columns:
                if "HTS Code" in str(col) or "HTS_Code" in str(col):
                    hts_col = col
                    break
            
            if hts_col:
                # Only process rows where HTS code is empty/null
                hts_mask = df[hts_col].isna() | (df[hts_col].astype(str).str.strip() == '')
                mask = mask & hts_mask
                
                logger.debug(f"Empty-only mode: filtering {len(df)} rows to {mask.sum()} rows")
            else:
                logger.info("No HTS Code column found, processing all rows with descriptions")
        
        filtered_df = df[mask].copy()
        logger.debug(f"Filtered {len(df)} rows to {len(filtered_df)} rows for processing")
        
        return filtered_df
    
    def write_results(
        self, 
        original_file: Path, 
        results: List[Dict[str, Any]], 
        output_file: Path,
        preserve_existing_hts: bool = True
    ) -> None:
        """
        Write processing results to a new Excel file.
        
        Args:
            original_file: Path to the original Excel file
            results: List of processing results as dictionaries
            output_file: Path where to save the processed file
            preserve_existing_hts: Whether to preserve existing HTS codes (for selective mode)
        """
        logger.info(f"Writing results to: {output_file}")
        
        try:
            # Read the original file
            df_original = pd.read_excel(original_file, engine='openpyxl')
            
            # Create a copy for the output
            df_output = df_original.copy()
            
            # Find existing HTS column if it exists
            existing_hts_col = None
            for col in df_output.columns:
                if "HTS Code" in str(col) or "HTS_Code" in str(col):
                    existing_hts_col = col
                    break
            
            # Add new columns if they don't exist
            if 'TNVED_Code' not in df_output.columns:
                df_output['TNVED_Code'] = ''
            if 'Selection_Reason' not in df_output.columns:
                df_output['Selection_Reason'] = ''
            
            # If preserving existing HTS codes and there's an existing column, copy values
            if preserve_existing_hts and existing_hts_col:
                # Copy existing HTS codes to TNVED_Code column where they exist
                mask = df_output[existing_hts_col].notna() & \
                       (df_output[existing_hts_col].astype(str).str.strip() != '')
                df_output.loc[mask, 'TNVED_Code'] = df_output.loc[mask, existing_hts_col]
                df_output.loc[mask, 'Selection_Reason'] = 'Preserved existing HTS code'
            
            # Apply results to the output DataFrame
            for result in results:
                row_idx = result.get('row_index', -1)
                if 0 <= row_idx < len(df_output):
                    # Only overwrite if we don't have an existing value or not preserving
                    if not preserve_existing_hts or pd.isna(df_output.loc[row_idx, 'TNVED_Code']) or \
                       str(df_output.loc[row_idx, 'TNVED_Code']).strip() == '':
                        df_output.loc[row_idx, 'TNVED_Code'] = result.get('tnved_code', '')
                        df_output.loc[row_idx, 'Selection_Reason'] = result.get('selection_reason', '')
            
            # Write to Excel file
            df_output.to_excel(output_file, index=False, engine='openpyxl')
            
            logger.info(f"Successfully wrote {len(results)} results to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to write results: {e}")
            raise
    
    def get_processing_statistics(
        self, 
        file_path: Path, 
        process_mode: str = "all"
    ) -> Dict[str, int]:
        """
        Get statistics about what will be processed without actually processing.
        
        Args:
            file_path: Path to the Excel file
            process_mode: "all" or "empty_only"
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Getting processing statistics for: {file_path}")
        
        try:
            validation = self.validate_file(file_path)
            if not validation.is_valid:
                return {
                    'total_rows': 0,
                    'rows_to_process': 0,
                    'rows_to_skip': 0,
                    'empty_descriptions': 0,
                    'existing_hts_codes': 0,
                    'skipped_with_existing_codes': 0
                }
            
            df = pd.read_excel(file_path, engine='openpyxl')
            total_rows = len(df)
            
            # Find columns
            description_col = next(
                col for col in df.columns 
                if "Product Detailed Description" in str(col)
            )
            
            hts_col = None
            for col in df.columns:
                if "HTS Code" in str(col) or "HTS_Code" in str(col):
                    hts_col = col
                    break
            
            # Count empty descriptions
            empty_descriptions = df[description_col].isna().sum() + \
                               (df[description_col].astype(str).str.strip() == '').sum()
            
            # Count existing HTS codes
            existing_hts_codes = 0
            if hts_col:
                existing_hts_codes = (~df[hts_col].isna()).sum() - \
                                   (df[hts_col].astype(str).str.strip() == '').sum()
            
            # Calculate rows to process based on mode
            skipped_with_existing_codes = 0
            if process_mode == "all":
                rows_to_process = total_rows - empty_descriptions
                rows_to_skip = empty_descriptions
            else:  # empty_only
                if hts_col:
                    # Only process rows with descriptions but no HTS codes
                    has_description = ~(df[description_col].isna() | 
                                      (df[description_col].astype(str).str.strip() == ''))
                    has_no_hts = df[hts_col].isna() | (df[hts_col].astype(str).str.strip() == '')
                    has_existing_hts = ~has_no_hts
                    
                    rows_to_process = (has_description & has_no_hts).sum()
                    skipped_with_existing_codes = (has_description & has_existing_hts).sum()
                    rows_to_skip = total_rows - rows_to_process
                else:
                    # No HTS column, same as "all" mode
                    rows_to_process = total_rows - empty_descriptions
                    rows_to_skip = empty_descriptions
            
            stats = {
                'total_rows': total_rows,
                'rows_to_process': rows_to_process,
                'rows_to_skip': rows_to_skip,
                'empty_descriptions': empty_descriptions,
                'existing_hts_codes': existing_hts_codes,
                'skipped_with_existing_codes': skipped_with_existing_codes
            }
            
            logger.info(f"Processing statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get processing statistics: {e}")
            return {
                'total_rows': 0,
                'rows_to_process': 0,
                'rows_to_skip': 0,
                'empty_descriptions': 0,
                'existing_hts_codes': 0,
                'skipped_with_existing_codes': 0
            }
    
    def generate_completion_summary(
        self, 
        file_path: Path, 
        process_mode: str,
        processed_count: int,
        error_count: int
    ) -> Dict[str, Any]:
        """
        Generate a completion summary for selective processing mode reporting.
        
        Args:
            file_path: Path to the original Excel file
            process_mode: "all" or "empty_only"
            processed_count: Number of rows actually processed
            error_count: Number of processing errors
            
        Returns:
            Dictionary with completion summary
        """
        logger.info(f"Generating completion summary for: {file_path}")
        
        try:
            stats = self.get_processing_statistics(file_path, process_mode)
            
            summary = {
                'process_mode': process_mode,
                'total_rows': stats['total_rows'],
                'rows_processed': processed_count,
                'rows_skipped': stats['rows_to_skip'],
                'successful_processing': processed_count - error_count,
                'processing_errors': error_count,
                'empty_descriptions': stats['empty_descriptions'],
                'existing_hts_codes': stats['existing_hts_codes']
            }
            
            if process_mode == "empty_only":
                summary['skipped_with_existing_codes'] = stats['skipped_with_existing_codes']
                summary['reason_for_skipping'] = "Rows with existing HTS codes were preserved"
            else:
                summary['reason_for_skipping'] = "Only rows with empty descriptions were skipped"
            
            # Generate human-readable summary message
            if process_mode == "empty_only":
                summary['message'] = (
                    f"Processed {processed_count} rows out of {stats['total_rows']} total rows. "
                    f"Skipped {stats['skipped_with_existing_codes']} rows with existing HTS codes "
                    f"and {stats['empty_descriptions']} rows with empty descriptions. "
                    f"Successfully processed {processed_count - error_count} rows, "
                    f"with {error_count} errors."
                )
            else:
                summary['message'] = (
                    f"Processed {processed_count} rows out of {stats['total_rows']} total rows. "
                    f"Skipped {stats['empty_descriptions']} rows with empty descriptions. "
                    f"Successfully processed {processed_count - error_count} rows, "
                    f"with {error_count} errors."
                )
            
            logger.info(f"Completion summary: {summary['message']}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate completion summary: {e}")
            return {
                'process_mode': process_mode,
                'total_rows': 0,
                'rows_processed': processed_count,
                'rows_skipped': 0,
                'successful_processing': processed_count - error_count,
                'processing_errors': error_count,
                'message': f"Processing completed with {processed_count} rows processed and {error_count} errors."
            }