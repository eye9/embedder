#!/usr/bin/env python3
"""
Optimized Data Loader for High-Performance Bulk Loading

This module provides optimized loaders for TNVED and URL data with:
- GPU acceleration support
- Vectorized data processing
- Large batch operations
- Minimal database queries
- Progress tracking
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager

import pandas as pd
import numpy as np
from tqdm import tqdm

from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from services.chroma_manager import ChromaDBManager
from utils.tnved_validator import validate_tnved_code


logger = logging.getLogger(__name__)


@contextmanager
def timer(name: str):
    """Context manager for timing operations"""
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.info(f"{name} took {elapsed:.2f}s ({elapsed/60:.2f}min, {elapsed/3600:.2f}h)")


class OptimizedTNVEDLoader:
    """
    High-performance TNVED data loader with optimizations:
    - GPU acceleration for embeddings
    - Vectorized pandas operations
    - Large batch processing
    - Minimal database queries
    - Progress tracking
    """
    
    def __init__(
        self,
        db_path: str,
        normalizer: TextNormalizer,
        embedder: EmbeddingGenerator,
        batch_size: int = 1000,
        collection_name: str = "tnved",
        show_progress: bool = True
    ):
        """
        Initialize optimized loader
        
        Args:
            db_path: Path to ChromaDB storage
            normalizer: Text normalizer instance
            embedder: Embedding generator (preferably with GPU)
            batch_size: Large batch size for processing (default: 1000)
            collection_name: ChromaDB collection name
            show_progress: Show progress bars
        """
        self.normalizer = normalizer
        self.embedder = embedder
        self.batch_size = batch_size
        self.show_progress = show_progress
        
        self.db_manager = ChromaDBManager(db_path, collection_name)
        
        logger.info(
            f"OptimizedTNVEDLoader initialized: batch_size={batch_size}, "
            f"device={embedder.device}, collection={collection_name}"
        )
    
    def load_from_excel(
        self,
        file_path: str,
        skip_duplicate_check: bool = True,
        use_vectorized: bool = True
    ) -> int:
        """
        Load TNVED data with optimizations
        
        Args:
            file_path: Path to Excel or Parquet file
            skip_duplicate_check: Skip checking for duplicates (faster for initial load)
            use_vectorized: Use vectorized operations (recommended)
            
        Returns:
            Number of records loaded
        """
        logger.info(f"Starting optimized load from {file_path}")
        
        # Read file (supports both Excel and Parquet)
        with timer("Reading file"):
            df = self._read_file(file_path)
            logger.info(f"Loaded {len(df)} rows from file")
        
        # Validate and prepare data
        with timer("Data preparation"):
            df = self._prepare_data(df, use_vectorized)
            logger.info(f"Prepared {len(df)} valid records")
        
        if len(df) == 0:
            logger.warning("No valid records to load")
            return 0
        
        # Process in large batches
        total_processed = 0
        batches = self._create_batches(df)
        
        logger.info(f"Processing {len(batches)} batches of size {self.batch_size}")
        
        iterator = tqdm(batches, desc="Loading batches") if self.show_progress else batches
        
        for batch_df in iterator:
            try:
                processed = self._process_batch_optimized(batch_df, skip_duplicate_check)
                total_processed += processed
            except Exception as e:
                logger.error(f"Error processing batch: {e}", exc_info=True)
                continue
        
        logger.info(f"Successfully loaded {total_processed} records")
        return total_processed
    
    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read file with automatic format detection"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.suffix == '.parquet':
            logger.info("Reading Parquet file (fast)")
            return pd.read_parquet(file_path)
        elif path.suffix in ['.xlsx', '.xls']:
            logger.info("Reading Excel file (may be slow for large files)")
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _prepare_data(self, df: pd.DataFrame, use_vectorized: bool = True) -> pd.DataFrame:
        """Prepare and validate data with vectorized operations"""
        
        # Check required columns
        required_columns = ["Code", "TextEx"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Remove rows with missing data
        initial_count = len(df)
        df = df.dropna(subset=["Code", "TextEx"]).copy()
        
        if len(df) < initial_count:
            logger.warning(f"Filtered out {initial_count - len(df)} rows with missing data")
        
        # Convert to strings
        df["Code"] = df["Code"].astype(str)
        df["TextEx"] = df["TextEx"].astype(str)
        
        if use_vectorized:
            # Vectorized code normalization (much faster)
            df["Code"] = df["Code"].str.strip().str.zfill(10)
            
            # Vectorized text normalization
            df["NormalizedText"] = self._normalize_texts_vectorized(df["TextEx"])
        else:
            # Fallback to loop-based processing
            df["Code"] = df["Code"].apply(lambda x: str(x).strip().zfill(10))
            df["NormalizedText"] = df["TextEx"].apply(self.normalizer.normalize)
        
        return df
    
    def _normalize_texts_vectorized(self, texts: pd.Series) -> pd.Series:
        """Vectorized text normalization using pandas"""
        # Apply all normalizations as vectorized operations
        normalized = texts.str.lower()
        normalized = normalized.str.replace(r'[^\w\s\u0400-\u04FF]', '', regex=True)
        normalized = normalized.str.replace(r'\s+', ' ', regex=True)
        normalized = normalized.str.strip()
        
        return normalized
    
    def _create_batches(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """Split DataFrame into batches"""
        batches = []
        for i in range(0, len(df), self.batch_size):
            batch = df.iloc[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    def _process_batch_optimized(
        self,
        batch_df: pd.DataFrame,
        skip_duplicate_check: bool = True
    ) -> int:
        """Process batch with optimizations"""
        
        # Extract data
        codes = batch_df["Code"].tolist()
        descriptions = batch_df["TextEx"].tolist()
        normalized_texts = batch_df["NormalizedText"].tolist()
        
        # Generate embeddings for entire batch at once
        with timer(f"Generating embeddings for {len(codes)} records"):
            embeddings = self.embedder.generate(
                normalized_texts,
                batch_size=self.batch_size,
                prefix="search_document: "
            )
            
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)
        
        # Prepare metadata
        metadatas = [
            {
                "description": desc,
                "code": code
            }
            for code, desc in zip(codes, descriptions)
        ]
        
        # Bulk upsert to ChromaDB
        with timer(f"Storing {len(codes)} records in ChromaDB"):
            self.db_manager.add_batch(
                ids=codes,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                documents=normalized_texts
            )
        
        return len(codes)
    
    def convert_excel_to_parquet(self, excel_path: str, parquet_path: Optional[str] = None) -> str:
        """
        Convert Excel file to Parquet for faster loading
        
        Args:
            excel_path: Path to Excel file
            parquet_path: Output path (default: same name with .parquet extension)
            
        Returns:
            Path to created Parquet file
        """
        if parquet_path is None:
            parquet_path = Path(excel_path).with_suffix('.parquet')
        
        logger.info(f"Converting {excel_path} to {parquet_path}")
        
        with timer("Excel to Parquet conversion"):
            df = pd.read_excel(excel_path)
            df.to_parquet(parquet_path, compression='snappy')
        
        # Compare file sizes
        excel_size = Path(excel_path).stat().st_size / (1024 * 1024)
        parquet_size = Path(parquet_path).stat().st_size / (1024 * 1024)
        
        logger.info(
            f"Conversion complete: {excel_size:.2f}MB (Excel) -> "
            f"{parquet_size:.2f}MB (Parquet), "
            f"compression ratio: {excel_size/parquet_size:.2f}x"
        )
        
        return str(parquet_path)


class OptimizedURLLoader:
    """
    High-performance URL data loader with same optimizations as TNVED loader
    """
    
    def __init__(
        self,
        db_manager,
        normalizer,
        batch_size: int = 1000,
        show_progress: bool = True
    ):
        """
        Initialize optimized URL loader
        
        Args:
            db_manager: URL database manager instance
            normalizer: URL normalizer instance
            batch_size: Large batch size for processing
            show_progress: Show progress bars
        """
        self.db_manager = db_manager
        self.normalizer = normalizer
        self.batch_size = batch_size
        self.show_progress = show_progress
        
        logger.info(f"OptimizedURLLoader initialized: batch_size={batch_size}")
    
    def load_from_excel(
        self,
        file_path: str,
        source_name: str,
        use_vectorized: bool = True
    ) -> Dict[str, int]:
        """
        Load URL data with optimizations
        
        Args:
            file_path: Path to Excel or Parquet file
            source_name: Source name for records
            use_vectorized: Use vectorized operations
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting optimized URL load from {file_path}")
        
        stats = {
            "total": 0,
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "invalid_urls": 0,
            "invalid_codes": 0
        }
        
        # Read file
        with timer("Reading file"):
            if file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            else:
                df = pd.read_excel(file_path)
            logger.info(f"Loaded {len(df)} rows")
        
        # Validate columns
        required = ['URL', 'Code', 'Description']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Prepare data
        with timer("Data preparation"):
            df = df.dropna(subset=required).copy()
            df["URL"] = df["URL"].astype(str).str.strip()
            df["Code"] = df["Code"].astype(str).str.strip().str.zfill(10)
            df["Description"] = df["Description"].astype(str).str.strip()
            
            stats["total"] = len(df)
            logger.info(f"Prepared {len(df)} valid records")
        
        # Process in batches
        batches = [df.iloc[i:i + self.batch_size] for i in range(0, len(df), self.batch_size)]
        
        iterator = tqdm(batches, desc="Loading URL batches") if self.show_progress else batches
        
        for batch_df in iterator:
            for _, row in batch_df.iterrows():
                if self.db_manager.add_url_record(
                    row['URL'],
                    row['Code'],
                    row['Description'],
                    source_name
                ):
                    stats["success"] += 1
                else:
                    stats["errors"] += 1
        
        logger.info(f"URL load completed: {stats}")
        return stats


def benchmark_loading_performance(
    file_path: str,
    db_path: str = "./benchmark_db",
    test_sizes: List[int] = [100, 1000, 10000]
):
    """
    Benchmark loading performance with different configurations
    
    Args:
        file_path: Path to test data file
        db_path: Path for benchmark database
        test_sizes: List of record counts to test
    """
    from services import TextNormalizer, EmbeddingGenerator
    
    print("=" * 70)
    print("LOADING PERFORMANCE BENCHMARK")
    print("=" * 70)
    print()
    
    # Read full dataset
    print(f"Reading test data from {file_path}...")
    if file_path.endswith('.parquet'):
        df_full = pd.read_parquet(file_path)
    else:
        df_full = pd.read_excel(file_path)
    
    print(f"Loaded {len(df_full)} total records")
    print()
    
    # Test configurations
    configs = [
        {"name": "CPU, batch=100", "device": "cpu", "batch_size": 100},
        {"name": "CPU, batch=500", "device": "cpu", "batch_size": 500},
        {"name": "CPU, batch=1000", "device": "cpu", "batch_size": 1000},
    ]
    
    # Add GPU configs if available
    try:
        import torch
        if torch.cuda.is_available():
            configs.extend([
                {"name": "GPU, batch=500", "device": "cuda", "batch_size": 500},
                {"name": "GPU, batch=1000", "device": "cuda", "batch_size": 1000},
                {"name": "GPU, batch=2000", "device": "cuda", "batch_size": 2000},
            ])
            print("✓ GPU detected and will be tested")
        else:
            print("✗ No GPU available, testing CPU only")
    except ImportError:
        print("✗ PyTorch not available, testing CPU only")
    
    print()
    
    results = []
    
    for test_size in test_sizes:
        if test_size > len(df_full):
            print(f"Skipping test_size={test_size} (exceeds dataset size)")
            continue
        
        print(f"\n{'='*70}")
        print(f"Testing with {test_size} records")
        print(f"{'='*70}\n")
        
        # Create test subset
        df_test = df_full.head(test_size)
        test_file = f"benchmark_test_{test_size}.parquet"
        df_test.to_parquet(test_file)
        
        for config in configs:
            print(f"\nConfiguration: {config['name']}")
            print("-" * 50)
            
            try:
                # Initialize components
                normalizer = TextNormalizer()
                embedder = EmbeddingGenerator(
                    model_name="ai-forever/FRIDA",
                    device=config["device"]
                )
                
                # Create fresh database
                import shutil
                if Path(db_path).exists():
                    shutil.rmtree(db_path)
                
                loader = OptimizedTNVEDLoader(
                    db_path=db_path,
                    normalizer=normalizer,
                    embedder=embedder,
                    batch_size=config["batch_size"],
                    show_progress=False
                )
                
                # Measure loading time
                start_time = time.time()
                loaded = loader.load_from_excel(test_file)
                elapsed = time.time() - start_time
                
                records_per_sec = loaded / elapsed if elapsed > 0 else 0
                
                result = {
                    "config": config["name"],
                    "test_size": test_size,
                    "loaded": loaded,
                    "time_sec": elapsed,
                    "records_per_sec": records_per_sec
                }
                results.append(result)
                
                print(f"✓ Loaded {loaded} records in {elapsed:.2f}s")
                print(f"  Performance: {records_per_sec:.1f} records/sec")
                
                # Estimate time for larger datasets
                for estimate_size in [100000, 500000, 1000000]:
                    estimated_time = estimate_size / records_per_sec
                    print(f"  Estimated for {estimate_size:,} records: {estimated_time:.1f}s ({estimated_time/60:.1f}min)")
                
            except Exception as e:
                print(f"✗ Error: {e}")
                continue
        
        # Cleanup test file
        Path(test_file).unlink(missing_ok=True)
    
    # Print summary
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}\n")
    
    if results:
        df_results = pd.DataFrame(results)
        print(df_results.to_string(index=False))
        
        # Save results
        results_file = "benchmark_results.csv"
        df_results.to_csv(results_file, index=False)
        print(f"\nResults saved to {results_file}")
    else:
        print("No results collected")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        # Run benchmark
        if len(sys.argv) < 3:
            print("Usage: python optimized_loader.py benchmark <data_file>")
            sys.exit(1)
        
        benchmark_loading_performance(sys.argv[2])
    else:
        print("Optimized Loader Module")
        print("Usage:")
        print("  python optimized_loader.py benchmark <data_file>  - Run performance benchmark")
        print()
        print("Or import in your code:")
        print("  from services.optimized_loader import OptimizedTNVEDLoader")
