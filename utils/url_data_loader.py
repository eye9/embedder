"""
URL Data Loader Utility for TNVED Code Matching System

Command-line utility for loading URL-to-TNVED code mappings from Excel files
and managing the URL database.
"""

import argparse
import logging
import sys
from pathlib import Path

from services.url_processor_factory import URLProcessorFactory
from services.url_config import URLProcessingConfig, load_url_config_from_env, validate_url_config
from utils.logger import setup_logging


def setup_url_data_loader_logging():
    """Set up logging for URL data loader"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_url_data_from_excel(
    file_path: str,
    source_name: str,
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None
) -> bool:
    """
    Load URL data from Excel file into database
    
    Args:
        file_path: Path to Excel file
        source_name: Name to assign as source
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        True if loading successful
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    try:
        # Validate configuration
        validate_url_config(config)
        
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        
        # Validate setup
        if not URLProcessorFactory.validate_url_processing_setup(components):
            logger.error("URL processing setup validation failed")
            return False
        
        db_manager = components["db_manager"]
        
        # Load data from Excel
        logger.info(f"Loading URL data from: {file_path}")
        logger.info(f"Source name: {source_name}")
        
        stats = db_manager.batch_load_from_excel(file_path, source_name)
        
        # Report results
        logger.info("Loading completed with statistics:")
        logger.info(f"  Total rows processed: {stats['total']}")
        logger.info(f"  Successfully loaded: {stats['success']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info(f"  Skipped (missing data): {stats['skipped']}")
        logger.info(f"  Invalid URLs: {stats.get('invalid_urls', 0)}")
        logger.info(f"  Invalid codes: {stats.get('invalid_codes', 0)}")
        
        if stats['success'] > 0:
            logger.info("URL data loading completed successfully")
            return True
        else:
            logger.error("No data was successfully loaded")
            return False
            
    except Exception as e:
        logger.error(f"Error during URL data loading: {e}")
        return False


def get_database_statistics(db_path: str = "./chroma_db", config: URLProcessingConfig = None) -> dict:
    """
    Get URL database statistics
    
    Args:
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        Dictionary with statistics
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    try:
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        db_manager = components["db_manager"]
        
        # Get statistics
        stats = db_manager.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        return {"error": str(e)}


def delete_records_by_source(
    source_name: str,
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None
) -> int:
    """
    Delete records by source name
    
    Args:
        source_name: Source name to delete
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        Number of records deleted
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    try:
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        db_manager = components["db_manager"]
        
        # Delete records
        deleted_count = db_manager.delete_by_source(source_name)
        
        logger.info(f"Deleted {deleted_count} records from source: {source_name}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting records by source: {e}")
        return 0


def export_database_to_excel(
    output_path: str,
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None
) -> bool:
    """
    Export URL database to Excel file
    
    Args:
        output_path: Path for output Excel file
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        True if export successful
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    try:
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        db_manager = components["db_manager"]
        
        # Export data
        success = db_manager.export_to_excel(output_path)
        
        if success:
            logger.info(f"Database exported to: {output_path}")
        else:
            logger.error("Export failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Error exporting database: {e}")
        return False


def main():
    """Main CLI entry point"""
    setup_url_data_loader_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(
        description="URL Data Loader for TNVED Code Matching System"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Load URL data from Excel file")
    load_parser.add_argument("file_path", help="Path to Excel file")
    load_parser.add_argument("source_name", help="Source name for the data")
    load_parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB path")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    stats_parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB path")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete records by source")
    delete_parser.add_argument("source_name", help="Source name to delete")
    delete_parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB path")
    delete_parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export database to Excel")
    export_parser.add_argument("output_path", help="Output Excel file path")
    export_parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "load":
            # Validate file exists
            if not Path(args.file_path).exists():
                logger.error(f"File not found: {args.file_path}")
                return 1
            
            success = load_url_data_from_excel(
                args.file_path,
                args.source_name,
                args.db_path
            )
            return 0 if success else 1
        
        elif args.command == "stats":
            stats = get_database_statistics(args.db_path)
            
            if "error" in stats:
                logger.error(f"Error getting statistics: {stats['error']}")
                return 1
            
            print("\nURL Database Statistics:")
            print(f"Total records: {stats['total_records']}")
            
            if stats['by_source']:
                print("\nBy source:")
                for source, count in stats['by_source'].items():
                    print(f"  {source}: {count}")
            
            if stats['by_domain']:
                print("\nBy domain:")
                for domain, count in stats['by_domain'].items():
                    print(f"  {domain}: {count}")
            
            if stats['by_shop_type']:
                print("\nBy shop type:")
                for shop, count in stats['by_shop_type'].items():
                    print(f"  {shop}: {count}")
            
            return 0
        
        elif args.command == "delete":
            if not args.confirm:
                print(f"This will delete all records from source: {args.source_name}")
                confirm = input("Are you sure? (yes/no): ")
                if confirm.lower() != "yes":
                    print("Deletion cancelled")
                    return 0
            
            deleted_count = delete_records_by_source(args.source_name, args.db_path)
            print(f"Deleted {deleted_count} records")
            return 0
        
        elif args.command == "export":
            success = export_database_to_excel(args.output_path, args.db_path)
            return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())