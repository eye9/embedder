"""
URL Upload Processor for Admin Data Upload Feature.

This module provides the URLUploadProcessor class that handles processing
of URL mapping uploads using existing optimized services.
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
import pandas as pd
import re
import chromadb

from services.url_database_manager_optimized import OptimizedURLDatabaseManager
from services.url_normalizer import URLNormalizer
from ..models.admin_models import UploadSummary, AdminProgressUpdate

logger = logging.getLogger(__name__)


class URLUploadProcessor:
    """
    Processes URL mapping uploads using existing OptimizedURLDatabaseManager.
    
    This processor handles:
    - File reading (Excel and Parquet formats)
    - URL validation and normalization
    - TNVED code validation
    - Deduplication of URLs
    - Batch processing using OptimizedURLDatabaseManager
    - Progress tracking and callbacks
    - Error handling and statistics collection
    """
    
    def __init__(self, chroma_client: chromadb.Client, batch_size: int = 5000):
        """
        Initialize URL upload processor.
        
        Args:
            chroma_client: ChromaDB client instance
            batch_size: Number of records to process in each batch
        """
        self.chroma_client = chroma_client
        self.batch_size = batch_size
        
        # Create OptimizedURLDatabaseManager instance
        self.db_manager = OptimizedURLDatabaseManager(
            chroma_client=chroma_client,
            collection_name="url_tnved_mapping"
        )
        
        # Initialize URL normalizer
        self.url_normalizer = URLNormalizer()
        
        logger.info(
            f"URLUploadProcessor initialized: batch_size={batch_size}, "
            f"collection=url_tnved_mapping"
        )
    
    def _validate_and_normalize_urls(
        self, 
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate and normalize URLs using URLNormalizer service.
        
        Args:
            df: DataFrame with URL column
            
        Returns:
            Tuple of (valid_df_with_normalized_urls, error_list)
        """
        logger.debug(f"Validating and normalizing {len(df)} URLs")
        
        errors = []
        valid_rows = []
        
        for idx, row in df.iterrows():
            url = str(row['URL']).strip()
            
            if not url or url.lower() in ['nan', 'none', '']:
                errors.append(f"Row {idx + 1}: Empty or missing URL")
                continue
            
            # Normalize URL using URLNormalizer service
            normalized_result = self.url_normalizer.normalize_url(url)
            
            if normalized_result is None:
                errors.append(f"Row {idx + 1}: Invalid URL format: {url}")
                continue
            
            # Add normalized URL data to the row
            row_dict = row.to_dict()
            row_dict['original_url'] = normalized_result.original_url
            row_dict['normalized_url'] = normalized_result.normalized_url
            row_dict['domain'] = normalized_result.domain
            row_dict['product_id'] = normalized_result.product_id or ""
            row_dict['shop_type'] = normalized_result.shop_type or ""
            
            valid_rows.append(row_dict)
        
        # Create DataFrame from valid rows
        if valid_rows:
            valid_df = pd.DataFrame(valid_rows)
        else:
            # Return empty DataFrame with expected columns
            valid_df = pd.DataFrame(columns=[
                'URL', 'Code', 'Description', 'original_url', 'normalized_url',
                'domain', 'product_id', 'shop_type'
            ])
        
        logger.debug(
            f"URL validation completed: {len(valid_df)} valid, "
            f"{len(errors)} invalid URLs"
        )
        
        return valid_df, errors
    
    def _validate_codes(
        self, 
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate TNVED codes are 10 digits or can be normalized.
        
        Args:
            df: DataFrame with Code column
            
        Returns:
            Tuple of (valid_df_with_normalized_codes, error_list)
        """
        logger.debug(f"Validating TNVED codes for {len(df)} records")
        
        errors = []
        valid_rows = []
        
        for idx, row in df.iterrows():
            code = str(row['Code']).strip()
            
            if not code or code.lower() in ['nan', 'none', '']:
                errors.append(f"Row {idx + 1}: Empty or missing TNVED code")
                continue
            
            # Remove non-digit characters
            clean_code = re.sub(r'[^\d]', '', code)
            
            if not clean_code:
                errors.append(f"Row {idx + 1}: TNVED code contains no digits: {code}")
                continue
            
            # Check if code can be normalized to 10 digits
            if len(clean_code) > 10:
                errors.append(
                    f"Row {idx + 1}: TNVED code too long (>10 digits): {code} "
                    f"(cleaned: {clean_code})"
                )
                continue
            
            # Zero-pad to 10 digits
            normalized_code = clean_code.zfill(10)
            
            # Update row with normalized code
            row_dict = row.to_dict()
            row_dict['Code'] = normalized_code
            row_dict['original_code'] = code
            
            valid_rows.append(row_dict)
        
        # Create DataFrame from valid rows
        if valid_rows:
            valid_df = pd.DataFrame(valid_rows)
        else:
            # Return empty DataFrame with expected columns
            columns = list(df.columns) + ['original_code']
            valid_df = pd.DataFrame(columns=columns)
        
        logger.debug(
            f"Code validation completed: {len(valid_df)} valid, "
            f"{len(errors)} invalid codes"
        )
        
        return valid_df, errors
    
    def _deduplicate_urls(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Remove duplicate URLs, keeping first occurrence.
        
        Args:
            df: DataFrame with normalized_url column
            
        Returns:
            Tuple of (deduplicated_df, statistics_dict)
        """
        logger.debug(f"Deduplicating URLs for {len(df)} records")
        
        initial_count = len(df)
        
        # Remove duplicates based on normalized_url column, keeping first occurrence
        df_deduplicated = df.drop_duplicates(subset=["normalized_url"], keep="first")
        
        final_count = len(df_deduplicated)
        duplicates_removed = initial_count - final_count
        
        stats = {
            'initial_count': initial_count,
            'final_count': final_count,
            'duplicates_removed': duplicates_removed
        }
        
        logger.debug(
            f"URL deduplication: {initial_count} -> {final_count} records, "
            f"removed {duplicates_removed} duplicates"
        )
        
        return df_deduplicated, stats
    
    async def process_upload(
        self,
        file_path: Path,
        source_name: str,
        progress_callback: Optional[Callable[[AdminProgressUpdate], None]] = None
    ) -> UploadSummary:
        """
        Process URL mapping upload asynchronously.
        
        Args:
            file_path: Path to uploaded file (Excel or Parquet)
            source_name: Data source identifier
            progress_callback: Optional callback for progress updates
            
        Returns:
            UploadSummary with processing statistics
            
        Raises:
            ValueError: If file format is unsupported or required columns are missing
            FileNotFoundError: If file doesn't exist
        """
        start_time = time.time()
        upload_id = f"url_{int(start_time)}"
        
        logger.info(f"Starting URL upload processing: {file_path}, source: {source_name}")
        
        try:
            # Step 1: Read file into DataFrame
            df = await self._read_file_async(file_path)
            total_records = len(df)
            
            logger.info(f"Read {total_records} records from {file_path}")
            
            # Step 2: Validate and normalize URLs
            df_valid_urls, url_errors = self._validate_and_normalize_urls(df)
            invalid_urls_count = len(url_errors)
            
            # Step 3: Validate codes
            df_valid_codes, code_errors = self._validate_codes(df_valid_urls)
            invalid_codes_count = len(code_errors)
            
            # Step 4: Deduplicate URLs
            df_final, deduplication_stats = self._deduplicate_urls(df_valid_codes)
            
            valid_records = len(df_final)
            failed_records = total_records - valid_records
            
            logger.info(
                f"After validation and deduplication: {valid_records} valid, "
                f"{failed_records} failed records "
                f"(URLs: {invalid_urls_count}, Codes: {invalid_codes_count})"
            )
            
            # Step 5: Process in batches using OptimizedURLDatabaseManager
            if valid_records > 0:
                processed_count = await self._process_batches(
                    df_final, source_name, upload_id, progress_callback
                )
            else:
                processed_count = 0
            
            # Step 6: Calculate final statistics
            processing_time = time.time() - start_time
            records_per_second = processed_count / processing_time if processing_time > 0 else 0
            
            # Get database total
            database_total = await self._get_database_total()
            
            # Combine all errors
            all_errors = url_errors + code_errors
            
            # Create summary
            summary = UploadSummary(
                upload_id=upload_id,
                upload_type="urls",
                source_name=source_name,
                total_records=total_records,
                successful_records=processed_count,
                failed_records=failed_records,
                invalid_urls=invalid_urls_count,
                invalid_codes=invalid_codes_count,
                duplicate_records=deduplication_stats.get('duplicates_removed', 0),
                processing_time_seconds=processing_time,
                records_per_second=records_per_second,
                database_total_records=database_total,
                errors=all_errors,
                warnings=[]
            )
            
            logger.info(f"URL upload completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error processing URL upload: {e}", exc_info=True)
            raise
    
    async def _read_file_async(self, file_path: Path) -> pd.DataFrame:
        """
        Read file asynchronously with format detection.
        
        Args:
            file_path: Path to file to read
            
        Returns:
            DataFrame with file contents
            
        Raises:
            ValueError: If file format is unsupported
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Run file reading in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        if file_path.suffix.lower() == '.parquet':
            logger.debug("Reading Parquet file")
            df = await loop.run_in_executor(None, pd.read_parquet, str(file_path))
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            logger.debug("Reading Excel file")
            df = await loop.run_in_executor(None, pd.read_excel, str(file_path))
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Validate required columns
        required_columns = ["URL", "Code"]
        optional_columns = ["Description"]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Add Description column if missing
        if "Description" not in df.columns:
            df["Description"] = ""
        
        return df
    
    async def _process_batches(
        self,
        df: pd.DataFrame,
        source_name: str,
        upload_id: str,
        progress_callback: Optional[Callable[[AdminProgressUpdate], None]] = None
    ) -> int:
        """
        Process DataFrame in batches using OptimizedURLDatabaseManager.
        
        Args:
            df: DataFrame with validated and deduplicated URLs
            source_name: Data source identifier
            upload_id: Upload identifier for progress tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            Number of successfully processed records
        """
        logger.debug(f"Processing {len(df)} records in batches of {self.batch_size}")
        
        total_records = len(df)
        processed_records = 0
        start_time = time.time()
        
        # Process in batches
        for batch_start in range(0, total_records, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_records)
            batch_df = df.iloc[batch_start:batch_end]
            
            # Process batch using OptimizedURLDatabaseManager
            loop = asyncio.get_event_loop()
            batch_stats = await loop.run_in_executor(
                None,
                self.db_manager.batch_load_from_dataframe,
                batch_df,
                source_name,
                "URL",  # url_column
                "Code",  # code_column
                "Description",  # description_column
                len(batch_df)  # batch_size (process all at once)
            )
            
            batch_processed = batch_stats.get('success', 0)
            processed_records += batch_processed
            
            # Send progress update
            if progress_callback:
                elapsed_time = time.time() - start_time
                records_per_sec = processed_records / elapsed_time if elapsed_time > 0 else 0
                remaining_records = total_records - processed_records
                eta_seconds = remaining_records / records_per_sec if records_per_sec > 0 else 0
                
                progress_update = AdminProgressUpdate(
                    upload_id=upload_id,
                    processed=processed_records,
                    total=total_records,
                    progress_pct=(processed_records / total_records) * 100,
                    records_per_sec=records_per_sec,
                    eta_seconds=eta_seconds,
                    current_batch=batch_start // self.batch_size + 1
                )
                
                progress_callback(progress_update)
            
            logger.debug(f"Processed batch {batch_start}-{batch_end}: {batch_processed} records")
        
        logger.info(f"Batch processing completed: {processed_records} records processed")
        return processed_records
    
    async def _get_database_total(self) -> int:
        """
        Get total number of records in the database.
        
        Returns:
            Total record count in URL mapping collection
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self.db_manager.get_statistics)
            return stats.get('total_records', 0)
        except Exception as e:
            logger.error(f"Error getting database total: {e}")
            return 0