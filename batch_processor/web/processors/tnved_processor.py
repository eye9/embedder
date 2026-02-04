"""
TNVED Upload Processor for Admin Data Upload Feature.

This module provides the TNVEDUploadProcessor class that handles processing
of TNVED code uploads using existing optimized services.
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
import pandas as pd
import re

from services.optimized_loader import OptimizedTNVEDLoader
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from ..models.admin_models import UploadSummary, AdminProgressUpdate

logger = logging.getLogger(__name__)


class TNVEDUploadProcessor:
    """
    Processes TNVED code uploads using existing OptimizedTNVEDLoader.
    
    This processor handles:
    - File reading (Excel and Parquet formats)
    - TNVED code normalization to 10-digit format
    - Deduplication of codes
    - Batch processing using OptimizedTNVEDLoader
    - Progress tracking and callbacks
    - Error handling and statistics collection
    """
    
    def __init__(self, db_path: str, batch_size: int = 5000):
        """
        Initialize TNVED upload processor.
        
        Args:
            db_path: Path to ChromaDB database
            batch_size: Number of records to process in each batch
        """
        self.db_path = db_path
        self.batch_size = batch_size
        
        # Initialize text processing services
        self.normalizer = TextNormalizer()
        self.embedder = EmbeddingGenerator(
            model_name="ai-forever/FRIDA",
            device="cuda" if self._is_cuda_available() else "cpu"
        )
        
        logger.info(
            f"TNVEDUploadProcessor initialized: db_path={db_path}, "
            f"batch_size={batch_size}, device={self.embedder.device}"
        )
    
    def _is_cuda_available(self) -> bool:
        """Check if CUDA is available for GPU acceleration."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    async def process_upload(
        self,
        file_path: Path,
        source_name: str,
        progress_callback: Optional[Callable[[AdminProgressUpdate], None]] = None
    ) -> UploadSummary:
        """
        Process TNVED code upload asynchronously.
        
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
        upload_id = f"tnved_{int(start_time)}"
        
        logger.info(f"Starting TNVED upload processing: {file_path}, source: {source_name}")
        
        try:
            # Step 1: Read file into DataFrame
            df = await self._read_file_async(file_path)
            total_records = len(df)
            
            logger.info(f"Read {total_records} records from {file_path}")
            
            # Step 2: Normalize codes
            df, normalization_stats = self._normalize_codes(df)
            
            # Step 3: Deduplicate codes
            df, deduplication_stats = self._deduplicate_codes(df)
            
            valid_records = len(df)
            invalid_records = total_records - valid_records
            
            logger.info(
                f"After normalization and deduplication: {valid_records} valid, "
                f"{invalid_records} invalid records"
            )
            
            # Step 4: Process in batches using OptimizedTNVEDLoader
            if valid_records > 0:
                processed_count = await self._process_batches(
                    df, source_name, upload_id, progress_callback
                )
            else:
                processed_count = 0
            
            # Step 5: Calculate final statistics
            processing_time = time.time() - start_time
            records_per_second = processed_count / processing_time if processing_time > 0 else 0
            
            # Get database total (this would need to be implemented based on ChromaDB)
            database_total = await self._get_database_total()
            
            # Create summary
            summary = UploadSummary(
                upload_id=upload_id,
                upload_type="tnved",
                source_name=source_name,
                total_records=total_records,
                successful_records=processed_count,
                failed_records=invalid_records,
                duplicate_records=deduplication_stats.get('duplicates_removed', 0),
                processing_time_seconds=processing_time,
                records_per_second=records_per_second,
                database_total_records=database_total,
                errors=normalization_stats.get('errors', []),
                warnings=[]
            )
            
            logger.info(f"TNVED upload completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error processing TNVED upload: {e}", exc_info=True)
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
        required_columns = ["Code", "Description"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        return df
    
    def _normalize_codes(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Normalize TNVED codes to 10-digit format.
        
        Args:
            df: DataFrame with Code and Description columns
            
        Returns:
            Tuple of (normalized_df, statistics_dict)
        """
        logger.debug("Normalizing TNVED codes")
        
        initial_count = len(df)
        errors = []
        
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # Remove rows with missing codes or descriptions
        df = df.dropna(subset=["Code", "Description"])
        
        # Convert codes to strings and strip whitespace
        df["Code"] = df["Code"].astype(str).str.strip()
        df["Description"] = df["Description"].astype(str).str.strip()
        
        # Remove non-digit characters from codes
        df["Code"] = df["Code"].str.replace(r'[^\d]', '', regex=True)
        
        # Filter out codes that are empty after cleaning
        valid_mask = df["Code"].str.len() > 0
        invalid_codes = df[~valid_mask]
        
        if len(invalid_codes) > 0:
            errors.append(f"Found {len(invalid_codes)} codes with no digits")
        
        df = df[valid_mask]
        
        # Zero-pad codes to 10 digits
        df["Code"] = df["Code"].str.zfill(10)
        
        # Filter out codes that are too long (more than 10 digits after padding)
        valid_length_mask = df["Code"].str.len() == 10
        invalid_length = df[~valid_length_mask]
        
        if len(invalid_length) > 0:
            errors.append(f"Found {len(invalid_length)} codes longer than 10 digits")
        
        df = df[valid_length_mask]
        
        final_count = len(df)
        invalid_count = initial_count - final_count
        
        stats = {
            'initial_count': initial_count,
            'final_count': final_count,
            'invalid_count': invalid_count,
            'errors': errors
        }
        
        logger.debug(f"Code normalization: {initial_count} -> {final_count} records")
        
        return df, stats
    
    def _deduplicate_codes(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Remove duplicate codes, keeping first occurrence.
        
        Args:
            df: DataFrame with normalized codes
            
        Returns:
            Tuple of (deduplicated_df, statistics_dict)
        """
        logger.debug("Deduplicating TNVED codes")
        
        initial_count = len(df)
        
        # Remove duplicates based on Code column, keeping first occurrence
        df_deduplicated = df.drop_duplicates(subset=["Code"], keep="first")
        
        final_count = len(df_deduplicated)
        duplicates_removed = initial_count - final_count
        
        stats = {
            'initial_count': initial_count,
            'final_count': final_count,
            'duplicates_removed': duplicates_removed
        }
        
        logger.debug(f"Deduplication: {initial_count} -> {final_count} records, removed {duplicates_removed} duplicates")
        
        return df_deduplicated, stats
    
    async def _process_batches(
        self,
        df: pd.DataFrame,
        source_name: str,
        upload_id: str,
        progress_callback: Optional[Callable[[AdminProgressUpdate], None]] = None
    ) -> int:
        """
        Process DataFrame in batches using OptimizedTNVEDLoader.
        
        Args:
            df: DataFrame with normalized and deduplicated codes
            source_name: Data source identifier
            upload_id: Upload identifier for progress tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            Number of successfully processed records
        """
        logger.debug(f"Processing {len(df)} records in batches of {self.batch_size}")
        
        # Create OptimizedTNVEDLoader instance
        loader = OptimizedTNVEDLoader(
            db_path=self.db_path,
            normalizer=self.normalizer,
            embedder=self.embedder,
            batch_size=self.batch_size,
            show_progress=False  # We handle progress ourselves
        )
        
        total_records = len(df)
        processed_records = 0
        start_time = time.time()
        
        # Process in batches
        for batch_start in range(0, total_records, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_records)
            batch_df = df.iloc[batch_start:batch_end]
            
            # Save batch to temporary file for OptimizedTNVEDLoader
            temp_file = Path(f"/tmp/tnved_batch_{upload_id}_{batch_start}.parquet")
            try:
                # Rename columns to match OptimizedTNVEDLoader expectations
                batch_df_renamed = batch_df.rename(columns={"Description": "TextEx"})
                batch_df_renamed.to_parquet(temp_file)
                
                # Process batch using OptimizedTNVEDLoader
                loop = asyncio.get_event_loop()
                batch_processed = await loop.run_in_executor(
                    None, 
                    loader.load_from_excel, 
                    str(temp_file)
                )
                
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
                
            finally:
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()
        
        logger.info(f"Batch processing completed: {processed_records} records processed")
        return processed_records
    
    async def _get_database_total(self) -> int:
        """
        Get total number of records in the database.
        
        Returns:
            Total record count in TNVED collection
        """
        # This is a placeholder - would need to implement based on ChromaDB API
        # For now, return 0 as we don't have direct access to collection stats
        return 0