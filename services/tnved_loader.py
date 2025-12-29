"""
ТНВЭД Data Loader Service

This module provides functionality to load ТНВЭД data from Excel files
into ChromaDB vector database with text normalization and embedding generation.
"""

import logging
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import numpy as np

from models.tnved_record import TNVEDRecord
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from services.chroma_manager import ChromaDBManager
from utils.tnved_validator import validate_tnved_code, TNVEDValidationError


logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when data loading fails"""
    pass


class TNVEDLoader:
    """
    Loads ТНВЭД data from Excel files into ChromaDB.
    
    This class handles the complete pipeline:
    1. Reading Excel file with ТНВЭД codes and descriptions
    2. Normalizing text descriptions
    3. Generating embeddings
    4. Storing in ChromaDB with batch processing
    
    Features:
    - Batch processing for memory efficiency
    - Progress logging
    - Error handling for file operations
    - Duplicate code handling (upsert)
    
    Attributes:
        db_manager: ChromaDB manager instance
        normalizer: Text normalizer instance
        embedder: Embedding generator instance
        batch_size: Number of records to process in each batch
    """
    
    def __init__(
        self,
        db_path: str,
        normalizer: TextNormalizer,
        embedder: EmbeddingGenerator,
        batch_size: int = 100,
        collection_name: str = "tnved"
    ):
        """
        Initialize ТНВЭД loader.
        
        Args:
            db_path: Path to ChromaDB storage directory
            normalizer: TextNormalizer instance for text processing
            embedder: EmbeddingGenerator instance for creating embeddings
            batch_size: Number of records to process per batch (default: 100)
            collection_name: Name of ChromaDB collection (default: "tnved")
            
        Raises:
            ValueError: If batch_size is not positive
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        
        self.normalizer = normalizer
        self.embedder = embedder
        self.batch_size = batch_size
        
        # Initialize ChromaDB manager
        self.db_manager = ChromaDBManager(db_path, collection_name)
        
        logger.info(
            f"TNVEDLoader initialized with batch_size={batch_size}, "
            f"db_path={db_path}, collection={collection_name}"
        )
    
    def load_from_excel(self, file_path: str) -> int:
        """
        Load ТНВЭД data from Excel file into ChromaDB.
        
        Reads the Excel file, extracts Code and TextEx columns,
        normalizes text, generates embeddings, and stores in ChromaDB.
        Processes data in batches for memory efficiency.
        
        Args:
            file_path: Path to Excel file containing ТНВЭД data
            
        Returns:
            Total number of records successfully loaded
            
        Raises:
            DataLoadError: If file cannot be read or required columns are missing
            FileNotFoundError: If file doesn't exist
            
        Examples:
            >>> loader = TNVEDLoader("./chroma_db", normalizer, embedder)
            >>> count = loader.load_from_excel("tnved_full10_new.xlsx")
            >>> print(f"Loaded {count} records")
        """
        # Validate file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        logger.info(f"Starting to load data from {file_path}")
        
        try:
            # Read Excel file
            logger.debug(f"Reading Excel file: {file_path}")
            df = pd.read_excel(file_path)
            logger.info(f"Excel file loaded with {len(df)} rows")
            
        except Exception as e:
            error_msg = f"Failed to read Excel file {file_path}: {e}"
            logger.error(error_msg)
            raise DataLoadError(error_msg) from e
        
        # Validate required columns
        required_columns = ["Code", "TextEx"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = (
                f"Required columns missing from Excel file: {missing_columns}. "
                f"Available columns: {list(df.columns)}"
            )
            logger.error(error_msg)
            raise DataLoadError(error_msg)
        
        # Filter out rows with missing Code or TextEx
        initial_count = len(df)
        df = df.dropna(subset=["Code", "TextEx"])
        filtered_count = len(df)
        
        if filtered_count < initial_count:
            logger.warning(
                f"Filtered out {initial_count - filtered_count} rows with missing Code or TextEx"
            )
        
        if filtered_count == 0:
            logger.warning("No valid records found in Excel file")
            return 0
        
        # Convert Code to string and TextEx to string
        df["Code"] = df["Code"].astype(str)
        df["TextEx"] = df["TextEx"].astype(str)
        
        # Validate and normalize ТНВЭД codes
        logger.info("Validating and normalizing ТНВЭД codes")
        invalid_codes = []
        normalized_codes = []
        
        for idx, code in enumerate(df["Code"]):
            try:
                normalized_code = validate_tnved_code(code, strict=False)
                normalized_codes.append(normalized_code)
            except (TNVEDValidationError, ValueError) as e:
                logger.warning(f"Invalid ТНВЭД code at row {idx + 1}: '{code}' - {e}")
                invalid_codes.append((idx, code, str(e)))
                # Use the original code padded to 10 digits as fallback
                normalized_codes.append(str(code).zfill(10))
        
        df["Code"] = normalized_codes
        
        if invalid_codes:
            logger.warning(f"Found {len(invalid_codes)} invalid ТНВЭД codes (using fallback normalization)")
            # Log first few invalid codes for debugging
            for idx, code, error in invalid_codes[:5]:
                logger.debug(f"Row {idx + 1}: '{code}' - {error}")
        
        logger.info(f"Normalized {len(df)} codes to 10-digit format")
        
        # Process data in batches
        total_processed = 0
        total_batches = (len(df) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Processing {len(df)} records in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(df))
            
            batch_df = df.iloc[start_idx:end_idx]
            
            try:
                processed = self._process_batch(batch_df, batch_num + 1, total_batches)
                total_processed += processed
                
            except Exception as e:
                logger.error(
                    f"Error processing batch {batch_num + 1}/{total_batches}: {e}",
                    exc_info=True
                )
                # Continue with next batch instead of failing completely
                continue
        
        logger.info(
            f"Successfully loaded {total_processed} records from {file_path}"
        )
        
        return total_processed
    
    def _process_batch(
        self,
        batch_df: pd.DataFrame,
        batch_num: int,
        total_batches: int
    ) -> int:
        """
        Process a single batch of records.
        
        Args:
            batch_df: DataFrame containing batch records
            batch_num: Current batch number (1-indexed)
            total_batches: Total number of batches
            
        Returns:
            Number of records processed in this batch
            
        Raises:
            Exception: If batch processing fails
        """
        logger.info(
            f"Processing batch {batch_num}/{total_batches} "
            f"({len(batch_df)} records)"
        )
        
        # Extract codes and descriptions
        codes = batch_df["Code"].tolist()
        descriptions = batch_df["TextEx"].tolist()
        
        # Normalize texts
        logger.debug(f"Normalizing {len(descriptions)} texts")
        normalized_texts = []
        
        for desc in descriptions:
            try:
                normalized = self.normalizer.normalize(desc)
                normalized_texts.append(normalized)
            except Exception as e:
                logger.warning(f"Failed to normalize text '{desc[:50]}...': {e}")
                # Use empty string for failed normalization
                normalized_texts.append("")
        
        # Generate embeddings with search_document prefix for FRIDA model
        logger.debug(f"Generating embeddings for {len(normalized_texts)} texts")
        try:
            embeddings = self.embedder.generate(
                normalized_texts,
                batch_size=self.batch_size,
                prefix="search_document: "
            )
            
            # Ensure embeddings is 2D array
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)
            
        except Exception as e:
            error_msg = f"Failed to generate embeddings for batch {batch_num}: {e}"
            logger.error(error_msg)
            raise
        
        # Prepare data for ChromaDB
        ids = codes
        embeddings_list = embeddings.tolist()
        documents = normalized_texts
        metadatas = [
            {
                "description": desc,
                "code": code
            }
            for code, desc in zip(codes, descriptions)
        ]
        
        # Store in ChromaDB
        logger.debug(f"Storing {len(ids)} records in ChromaDB")
        try:
            self.db_manager.add_batch(
                ids=ids,
                embeddings=embeddings_list,
                metadatas=metadatas,
                documents=documents
            )
        except Exception as e:
            error_msg = f"Failed to store batch {batch_num} in ChromaDB: {e}"
            logger.error(error_msg)
            raise
        
        logger.info(
            f"Batch {batch_num}/{total_batches} completed successfully "
            f"({len(ids)} records stored)"
        )
        
        return len(ids)
    
    def get_record_count(self) -> int:
        """
        Get the total number of records currently in the database.
        
        Returns:
            Number of records in ChromaDB collection
        """
        return self.db_manager.count()
    
    def get_statistics_by_source_type(self) -> Dict[str, int]:
        """
        Get record counts by source type.
        
        Returns:
            Dictionary with counts for each source type
        """
        return self.db_manager.get_statistics_by_source_type()
    
    def reset_database(self) -> None:
        """
        Reset the database by deleting all records.
        
        Warning: This operation cannot be undone!
        """
        logger.warning("Resetting database - all records will be deleted")
        self.db_manager.reset()
        logger.info("Database reset complete")
