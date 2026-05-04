#!/usr/bin/env python3
"""
ТНВЭД Data Loader CLI

Command-line interface for loading ТНВЭД data from Excel files into ChromaDB.
This script provides a simple way to populate the vector database with ТНВЭД codes
and descriptions for semantic search.

Usage:
    python load_tnved.py <excel_file> [options]

Examples:
    # Load with default settings
    python load_tnved.py tnved_full10_new.xlsx

    # Load with custom configuration file
    python load_tnved.py tnved_full10_new.xlsx --config config.yaml

    # Load with custom batch size
    python load_tnved.py tnved_full10_new.xlsx --batch-size 50

    # Load with custom database path
    python load_tnved.py tnved_full10_new.xlsx --db-path ./my_chroma_db

    # Reset database before loading
    python load_tnved.py tnved_full10_new.xlsx --reset

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.5
"""

import argparse
import sys
import time
from pathlib import Path

from services import TextNormalizer, EmbeddingGenerator, TNVEDLoader
from services.tnved_loader import DataLoadError as TNVEDDataLoadError
from services.product_loader import (
    ProductLoader,
    DataLoadError as ProductDataLoadError,
    SourceAlreadyExistsError,
)
from utils.config import Config
from utils.logger import setup_logging, get_logger
from utils.tnved_validator import validate_tnved_code, TNVEDValidationError


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Load ТНВЭД data from Excel file into ChromaDB vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s tnved_full10_new.xlsx
  %(prog)s tnved_full10_new.xlsx --config config.yaml
  %(prog)s tnved_full10_new.xlsx --batch-size 50 --db-path ./my_db
  %(prog)s tnved_full10_new.xlsx --reset --verbose
  %(prog)s products.xlsx --source-type product --source-name "customs_2024_q1"
  %(prog)s supplier_catalog.xlsx --source-type product --source-name "supplier_abc"
        """
    )
    
    # Required arguments
    parser.add_argument(
        "excel_file",
        type=str,
        help="Path to Excel file containing ТНВЭД data (must have Code and TextEx columns)"
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration YAML file (default: use built-in defaults)"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to ChromaDB storage directory (default: ./chroma_db)"
    )
    
    parser.add_argument(
        "--collection-name",
        type=str,
        default=None,
        help="Name of ChromaDB collection (default: tnved)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Number of records to process per batch (default: 100)"
    )
    
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Name of embedding model from HuggingFace (default: ai-forever/FRIDA)"
    )
    
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda"],
        default=None,
        help="Device to use for embeddings: cpu or cuda (default: cpu)"
    )
    
    # Product loading options
    parser.add_argument(
        "--source-type",
        type=str,
        choices=["reference", "product"],
        default="reference",
        help="Type of data being loaded: reference (official ТНВЭД) or product (real products with codes) (default: reference)"
    )
    
    parser.add_argument(
        "--source-name",
        type=str,
        default=None,
        help="Name of the data source (e.g., 'customs_2024_q1', 'supplier_catalog'). Required when --source-type is 'product'"
    )

    parser.add_argument(
        "--replace-source",
        action="store_true",
        help="Replace existing product records with the same --source-name without prompting"
    )
    
    # Action options
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before loading (WARNING: deletes all existing data)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate file and configuration without loading data"
    )
    
    # Logging options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all output except errors"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to log file (default: logs/tnved_embedder.log)"
    )
    
    return parser.parse_args()


def load_configuration(args):
    """
    Load configuration from file or command-line arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Config: Configuration object
    """
    # Load base configuration
    if args.config:
        try:
            config = Config.from_file(args.config)
            print(f"[OK] Loaded configuration from {args.config}")
        except FileNotFoundError:
            print(f"[ERROR] Configuration file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to load configuration: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Use defaults
        config = Config()
    
    # Override with command-line arguments
    if args.db_path:
        config.database.path = args.db_path
    
    if args.collection_name:
        config.database.collection_name = args.collection_name
    
    if args.batch_size:
        config.processing.batch_size = args.batch_size
    
    if args.model_name:
        config.model.name = args.model_name
    
    if args.device:
        config.model.device = args.device
    
    if args.log_file:
        config.logging.file = args.log_file
    
    # Set log level based on verbosity
    if args.verbose:
        config.logging.level = "DEBUG"
    elif args.quiet:
        config.logging.level = "ERROR"
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"[ERROR] Invalid configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    return config


def main():
    """Main CLI entry point"""
    # Parse arguments
    args = parse_arguments()
    
    # Validate source-name requirement for product loading
    if args.source_type == "product":
        if not args.source_name or not args.source_name.strip():
            print("[ERROR] --source-name is required when --source-type is 'product'", file=sys.stderr)
            sys.exit(1)
        args.source_name = args.source_name.strip()
    
    # Load configuration
    config = load_configuration(args)
    
    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        log_format=config.logging.format
    )
    logger = get_logger(__name__)
    
    # Print header
    if not args.quiet:
        print("=" * 70)
        print("ТНВЭД Data Loader")
        print("=" * 70)
        print()
    
    # Validate Excel file exists
    excel_path = Path(args.excel_file)
    if not excel_path.exists():
        logger.error(f"Excel file not found: {args.excel_file}")
        print(f"[ERROR] Excel file not found: {args.excel_file}", file=sys.stderr)
        sys.exit(1)
    
    # Validate ТНВЭД codes in file if requested (optional pre-validation)
    if not args.dry_run and not args.quiet:
        print("Validating ТНВЭД codes in Excel file...")
        try:
            import pandas as pd
            df = pd.read_excel(args.excel_file)
            
            if "Code" in df.columns:
                codes = df["Code"].dropna().astype(str).tolist()
                invalid_codes = []
                
                for code in codes[:10]:  # Check first 10 codes as sample
                    try:
                        validate_tnved_code(code, strict=False)
                    except (TNVEDValidationError, ValueError) as e:
                        invalid_codes.append((code, str(e)))
                
                if invalid_codes:
                    print(f"[WARNING] Found {len(invalid_codes)} invalid codes in sample:")
                    for code, error in invalid_codes[:3]:  # Show first 3 errors
                        print(f"  {code}: {error}")
                    if len(invalid_codes) > 3:
                        print(f"  ... and {len(invalid_codes) - 3} more")
                    print("  (Codes will be normalized during loading)")
                else:
                    print("[OK] ТНВЭД codes format validation passed")
            else:
                print("[WARNING] No 'Code' column found for validation")
        except Exception as e:
            print(f"[WARNING] Could not validate codes: {e}")
        
        print()
    
    if not args.quiet:
        print(f"Excel file:      {args.excel_file}")
        print(f"Database path:   {config.database.path}")
        print(f"Collection:      {config.database.collection_name}")
        print(f"Batch size:      {config.processing.batch_size}")
        print(f"Model:           {config.model.name}")
        print(f"Device:          {config.model.device}")
        print(f"Source type:     {args.source_type}")
        if args.source_name:
            print(f"Source name:     {args.source_name}")
        print()
    
    # Dry run mode
    if args.dry_run:
        logger.info("Dry run mode - validating configuration only")
        print("[OK] Dry run successful - configuration is valid")
        print("  (No data was loaded)")
        sys.exit(0)
    
    try:
        # Initialize components
        if not args.quiet:
            print("Initializing components...")
        
        logger.info("Initializing TextNormalizer")
        normalizer = TextNormalizer()
        
        logger.info(f"Initializing EmbeddingGenerator with model {config.model.name}")
        embedder = EmbeddingGenerator(
            model_name=config.model.name,
            device=config.model.device
        )
        
        # Initialize appropriate loader based on source type
        if args.source_type == "product":
            logger.info("Initializing ProductLoader for product data")
            loader = ProductLoader(
                db_path=config.database.path,
                normalizer=normalizer,
                embedder=embedder,
                batch_size=config.processing.batch_size,
                collection_name=config.database.collection_name
            )
        else:
            logger.info("Initializing TNVEDLoader for reference data")
            loader = TNVEDLoader(
                db_path=config.database.path,
                normalizer=normalizer,
                embedder=embedder,
                batch_size=config.processing.batch_size,
                collection_name=config.database.collection_name
            )
        
        if not args.quiet:
            print("[OK] Components initialized")
            print()
        
        # Check current database state
        current_count = loader.get_record_count()
        current_stats = loader.get_statistics_by_source_type()
        logger.info(f"Current database contains {current_count} records")
        
        if not args.quiet:
            print(f"Current database: {current_count} records")
            if current_stats["reference"] > 0 or current_stats["product"] > 0:
                print(f"  Reference records: {current_stats['reference']}")
                print(f"  Product records:   {current_stats['product']}")
                if current_stats["legacy"] > 0:
                    print(f"  Legacy records:    {current_stats['legacy']} (will be migrated)")
            else:
                print("  (Database is empty)")
        
        # Reset database if requested
        if args.reset:
            if current_count > 0:
                logger.warning("Resetting database - all existing data will be deleted")
                if not args.quiet:
                    print("[WARNING] Resetting database (deleting all existing data)...")
                
                loader.reset_database()
                
                if not args.quiet:
                    print("[OK] Database reset complete")
            else:
                if not args.quiet:
                    print("  (Database is already empty)")

        replace_existing_source = False
        if args.source_type == "product":
            existing_source_count = loader.count_product_records_by_source(args.source_name)

            if existing_source_count > 0:
                logger.warning(
                    f"Product source {args.source_name} already exists with "
                    f"{existing_source_count} records"
                )

                if args.replace_source:
                    replace_existing_source = True
                    if not args.quiet:
                        print(
                            f"[WARNING] Replacing {existing_source_count} existing "
                            f"product records for source '{args.source_name}'"
                        )
                elif args.quiet:
                    print(
                        f"[ERROR] Product source '{args.source_name}' already has "
                        f"{existing_source_count} records. Use --replace-source to replace it.",
                        file=sys.stderr
                    )
                    sys.exit(1)
                else:
                    print(
                        f"[WARNING] Product source '{args.source_name}' already has "
                        f"{existing_source_count} records."
                    )
                    response = input("Replace existing records for this source? [y/N]: ").strip().lower()
                    if response not in {"y", "yes"}:
                        logger.info(f"Load cancelled by user for existing source {args.source_name}")
                        print("Load cancelled. No data was changed.")
                        sys.exit(0)

                    replace_existing_source = True
            elif args.replace_source:
                replace_existing_source = True
        
        if not args.quiet:
            print()
            print("Loading data from Excel file...")
            print()
        
        # Load data with timing
        start_time = time.time()
        
        logger.info(f"Starting data load from {args.excel_file}")
        
        # Load data using appropriate method based on source type
        if args.source_type == "product":
            total_loaded = loader.load_from_excel(
                args.excel_file,
                args.source_name,
                replace_existing=replace_existing_source
            )
        else:
            total_loaded = loader.load_from_excel(args.excel_file)
        
        elapsed_time = time.time() - start_time
        
        # Get final count and statistics
        final_count = loader.get_record_count()
        final_stats = loader.get_statistics_by_source_type()
        
        # Print results
        if not args.quiet:
            print()
            print("=" * 70)
            print("Load Complete!")
            print("=" * 70)
            print(f"Records loaded:  {total_loaded}")
            print(f"Total records:   {final_count}")
            print(f"  Reference records: {final_stats['reference']}")
            print(f"  Product records:   {final_stats['product']}")
            if final_stats["legacy"] > 0:
                print(f"  Legacy records:    {final_stats['legacy']} (need migration)")
            print(f"Time elapsed:    {elapsed_time:.2f} seconds")
            
            if total_loaded > 0:
                records_per_sec = total_loaded / elapsed_time
                print(f"Processing rate: {records_per_sec:.1f} records/second")
            
            print()
        
        logger.info(
            f"Load completed successfully: {total_loaded} records loaded "
            f"in {elapsed_time:.2f} seconds"
        )
        
        sys.exit(0)
        
    except SourceAlreadyExistsError as e:
        logger.error(f"Product source already exists: {e}")
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    except (TNVEDDataLoadError, ProductDataLoadError) as e:
        logger.error(f"Data load error: {e}")
        print(f"\n[ERROR] Data load error: {e}", file=sys.stderr)
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.warning("Load interrupted by user")
        print("\n[WARNING] Load interrupted by user", file=sys.stderr)
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
