"""
Product Data Loader Service

This module provides functionality to load product data with pre-assigned ТНВЭД codes
from Excel files into ChromaDB vector database with text normalization and embedding generation.
"""

import logging
from pathlib import Path
from typing import Optional, Dict

import pandas as pd

from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from services.chroma_manager import ChromaDBManager
from utils.tnved_validator import validate_tnved_code, TNVEDValidationError


logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when data loading fails"""
    pass


class SourceAlreadyExistsError(DataLoadError):
    """Raised when loading would replace an existing product source without confirmation"""

    def __init__(self, source_name: str, existing_count: int):
        self.source_name = source_name
        self.existing_count = existing_count
        super().__init__(
            f"Product source '{source_name}' already has {existing_count} records. "
            "Pass replace_existing=True to replace it."
        )


class ProductLoader:
    """
    Loads product data with pre-assigned ТНВЭД codes from Excel files into ChromaDB.
    
    This class extends TNVEDLoader functionality to handle product records:
    1. Reading Excel file with ТНВЭД codes and product descriptions
    2. Normalizing text descriptions
    3. Generating unique IDs for products with same codes
    4. Generating embeddings
    5. Storing in ChromaDB with source information and metadata
    
    Features:
    - Batch processing for memory efficiency
    - Unique ID generation for duplicate codes
    - Source information preservation
    - Progress logging
    - Error handling for file operations
    - Excel format compatibility with existing TNVEDLoader
    
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
        Initialize Product loader.
        
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
            f"ProductLoader initialized with batch_size={batch_size}, "
            f"db_path={db_path}, collection={collection_name}"
        )
    
    def load_from_excel(
        self,
        file_path: str,
        source_name: str,
        source_type: str = "product",
        replace_existing: bool = False
    ) -> int:
        """
        Load product data from Excel file into ChromaDB.
        
        Reads the Excel file, extracts Code and TextEx columns (same format as TNVEDLoader),
        normalizes text, generates unique IDs for duplicates, generates embeddings,
        and stores in ChromaDB with source information.
        
        Args:
            file_path: Path to Excel file containing product data
            source_name: Name of the source (e.g., "customs_2024_q1")
            source_type: Type of source (default: "product")
            replace_existing: Replace existing product records with the same source_name
            
        Returns:
            Total number of records successfully loaded
            
        Raises:
            DataLoadError: If file cannot be read or required columns are missing
            SourceAlreadyExistsError: If source_name already exists and replace_existing is False
            FileNotFoundError: If file doesn't exist
            ValueError: If source_name is empty
            
        Examples:
            >>> loader = ProductLoader("./chroma_db", normalizer, embedder)
            >>> count = loader.load_from_excel("products.xlsx", "customs_2024_q1")
            >>> print(f"Loaded {count} product records")
        """
        # Validate inputs
        if not source_name or not source_name.strip():
            raise ValueError("source_name cannot be empty")
        source_name = source_name.strip()
        
        # Validate file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        logger.info(f"Starting to load product data from {file_path} with source_name: {source_name}")
        
        try:
            # Read Excel file
            logger.debug(f"Reading Excel file: {file_path}")
            df = pd.read_excel(file_path)
            logger.info(f"Excel file loaded with {len(df)} rows")
            
        except Exception as e:
            error_msg = f"Failed to read Excel file {file_path}: {e}"
            logger.error(error_msg)
            raise DataLoadError(error_msg) from e
        
        # Validate required columns (same as TNVEDLoader for compatibility)
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
        df = df.dropna(subset=["Code", "TextEx"]).copy()
        df["_excel_row_number"] = df.index + 2
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
        
        for row_idx, code in zip(df["_excel_row_number"], df["Code"]):
            try:
                normalized_code = validate_tnved_code(code, strict=False)
                normalized_codes.append(normalized_code)
            except (TNVEDValidationError, ValueError) as e:
                logger.warning(f"Invalid ТНВЭД code at row {row_idx}: '{code}' - {e}")
                invalid_codes.append((row_idx, code, str(e)))
                # Use the original code padded to 10 digits as fallback
                normalized_codes.append(str(code).zfill(10))
        
        df["Code"] = normalized_codes
        
        if invalid_codes:
            logger.warning(f"Found {len(invalid_codes)} invalid ТНВЭД codes (using fallback normalization)")
            # Log first few invalid codes for debugging
            for row_idx, code, error in invalid_codes[:5]:
                logger.debug(f"Row {row_idx}: '{code}' - {error}")
        
        logger.info(f"Normalized {len(df)} codes to 10-digit format")

        existing_source_count = self.count_product_records_by_source(source_name)
        if existing_source_count > 0:
            if not replace_existing:
                raise SourceAlreadyExistsError(source_name, existing_source_count)

            deleted_count = self.db_manager.delete_product_records_by_source(source_name)
            logger.info(
                f"Replacing product source {source_name}: deleted {deleted_count} existing records"
            )
        
        # Process data in batches
        total_processed = 0
        total_batches = (len(df) + self.batch_size - 1) // self.batch_size
        failed_batches = 0
        
        logger.info(f"Processing {len(df)} product records in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(df))
            
            batch_df = df.iloc[start_idx:end_idx]
            
            try:
                processed = self._process_batch(batch_df, source_name, batch_num + 1, total_batches)
                total_processed += processed
                
            except Exception as e:
                failed_batches += 1
                logger.error(
                    f"Error processing batch {batch_num + 1}/{total_batches}: {e}",
                    exc_info=True
                )
                # Continue with next batch instead of failing completely
                continue
        
        if failed_batches:
            logger.warning(
                f"Partially loaded {total_processed}/{len(df)} product records from {file_path} "
                f"with source_name: {source_name}; failed_batches={failed_batches}/{total_batches}"
            )
        else:
            logger.info(
                f"Successfully loaded {total_processed} product records from {file_path} "
                f"with source_name: {source_name}"
            )
        
        return total_processed

    @staticmethod
    def _generate_product_id(code: str, source_name: str, excel_row_number: int) -> str:
        """
        Generate a stable technical ID for a product row.

        Args:
            code: Normalized ТНВЭД code
            source_name: Product data source name
            excel_row_number: Original row number in Excel

        Returns:
            ChromaDB record ID
        """
        return f"product:{code}:{source_name.strip()}:{int(excel_row_number)}"
    
    def _process_batch(
        self,
        batch_df: pd.DataFrame,
        source_name: str,
        batch_num: int,
        total_batches: int
    ) -> int:
        """
        Process a single batch of product records.
        
        Args:
            batch_df: DataFrame containing batch records
            source_name: Name of the source
            batch_num: Current batch number (1-indexed)
            total_batches: Total number of batches
            
        Returns:
            Number of records processed in this batch
            
        Raises:
            Exception: If batch processing fails
        """
        logger.info(
            f"Processing product batch {batch_num}/{total_batches} "
            f"({len(batch_df)} records)"
        )
        
        # Extract codes and descriptions
        codes = batch_df["Code"].tolist()
        descriptions = batch_df["TextEx"].tolist()
        excel_row_numbers = batch_df["_excel_row_number"].tolist()
        
        unique_ids = [
            self._generate_product_id(code, source_name, row_number)
            for code, row_number in zip(codes, excel_row_numbers)
        ]
        
        logger.debug(f"Generated {len(unique_ids)} unique IDs for product records")
        
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
        
        # Prepare data for ChromaDB with source information
        ids = unique_ids
        embeddings_list = embeddings.tolist()
        documents = normalized_texts
        
        # Create metadata with source information
        metadatas = []
        source_id_columns = ["SourceID", "source_id", "ID", "DeclarationID", "declaration_id"]

        for _, row in batch_df.iterrows():
            code = row["Code"]
            desc = row["TextEx"]
            metadata = {
                "description": desc,
                "code": code,
                "source_name": source_name,
                "excel_row_number": int(row["_excel_row_number"])
            }
            
            for col in source_id_columns:
                if col in batch_df.columns:
                    source_id_value = row[col]
                    if pd.notna(source_id_value) and str(source_id_value).strip():
                        metadata["source_id"] = str(source_id_value).strip()
                    break
            
            metadatas.append(metadata)
        
        # Store in ChromaDB with source_type "product"
        logger.debug(f"Storing {len(ids)} product records in ChromaDB")
        try:
            self.db_manager.add_batch(
                ids=ids,
                embeddings=embeddings_list,
                metadatas=metadatas,
                documents=documents,
                source_type="product"
            )
        except Exception as e:
            error_msg = f"Failed to store product batch {batch_num} in ChromaDB: {e}"
            logger.error(error_msg)
            raise
        
        logger.info(
            f"Product batch {batch_num}/{total_batches} completed successfully "
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

    def count_product_records_by_source(self, source_name: str) -> int:
        """
        Count product records for a specific source_name.

        Args:
            source_name: Product data source name

        Returns:
            Number of matching product records
        """
        return self.db_manager.count_product_records_by_source(source_name)

    def reset_database(self) -> None:
        """
        Reset the database by deleting all records.

        Warning: This operation cannot be undone!
        """
        logger.warning("Resetting database - all records will be deleted")
        self.db_manager.reset()
        logger.info("Database reset complete")
    
    def validate_source_information(self, source_name: str, source_id: Optional[str] = None) -> bool:
        """
        Validate source information completeness.
        
        Args:
            source_name: Name of the source
            source_id: Optional ID in source system
            
        Returns:
            True if source information is valid, False otherwise
        """
        if not source_name or not source_name.strip():
            logger.error("Source name cannot be empty")
            return False
        
        # Source ID is optional, but if provided should not be empty
        if source_id is not None and not str(source_id).strip():
            logger.warning("Source ID provided but is empty")
            return False
        
        return True
