#!/usr/bin/env python3
"""
Enhanced URL Database Management CLI for TNVED Code Matching System

Command-line utility for comprehensive URL database management including
advanced deletion patterns, health checks, and maintenance operations.
"""

import argparse
import logging
import sys
import re
from pathlib import Path
from typing import Dict, Any, List

from services.url_processor_factory import URLProcessorFactory
from services.url_config import URLProcessingConfig, load_url_config_from_env, validate_url_config
from utils.logger import setup_logging


def setup_cli_logging(verbose: bool = False):
    """Set up logging for CLI operations"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
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
    Get comprehensive URL database statistics
    
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


def perform_health_check(db_path: str = "./chroma_db", config: URLProcessingConfig = None) -> Dict[str, Any]:
    """
    Perform comprehensive health check of URL database
    
    Args:
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        Dictionary with health check results
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    health_results = {
        "overall_status": "healthy",
        "checks": {},
        "warnings": [],
        "errors": []
    }
    
    try:
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        
        # Check component initialization
        health_results["checks"]["components_initialized"] = URLProcessorFactory.validate_url_processing_setup(components)
        
        if not health_results["checks"]["components_initialized"]:
            health_results["errors"].append("URL processing components failed to initialize")
            health_results["overall_status"] = "unhealthy"
        
        db_manager = components["db_manager"]
        normalizer = components["normalizer"]
        matcher = components["matcher"]
        
        # Check database connectivity
        try:
            stats = db_manager.get_statistics()
            health_results["checks"]["database_accessible"] = True
            health_results["checks"]["total_records"] = stats.get("total_records", 0)
        except Exception as e:
            health_results["checks"]["database_accessible"] = False
            health_results["errors"].append(f"Database access failed: {e}")
            health_results["overall_status"] = "unhealthy"
        
        # Check normalizer functionality
        try:
            test_url = "https://ozon.ru/product/123456/"
            normalized = normalizer.normalize_url(test_url)
            health_results["checks"]["normalizer_functional"] = normalized is not None
            health_results["checks"]["supported_shops"] = len(normalizer.get_supported_shops())
        except Exception as e:
            health_results["checks"]["normalizer_functional"] = False
            health_results["errors"].append(f"URL normalizer failed: {e}")
            health_results["overall_status"] = "unhealthy"
        
        # Check matcher functionality
        try:
            matcher_stats = matcher.get_matcher_statistics()
            health_results["checks"]["matcher_functional"] = "error" not in matcher_stats
            health_results["checks"]["matcher_timeout"] = matcher_stats.get("timeout_seconds", 0)
        except Exception as e:
            health_results["checks"]["matcher_functional"] = False
            health_results["errors"].append(f"URL matcher failed: {e}")
            health_results["overall_status"] = "unhealthy"
        
        # Performance warnings
        if health_results["checks"].get("total_records", 0) > 100000:
            health_results["warnings"].append("Large database size may impact performance")
        
        if health_results["checks"].get("matcher_timeout", 0) > 10:
            health_results["warnings"].append("High matcher timeout may cause delays")
        
        # Set overall status based on errors
        if health_results["errors"]:
            health_results["overall_status"] = "unhealthy"
        elif health_results["warnings"]:
            health_results["overall_status"] = "warning"
        
        logger.info(f"Health check completed: {health_results['overall_status']}")
        return health_results
        
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        return {
            "overall_status": "unhealthy",
            "checks": {},
            "warnings": [],
            "errors": [f"Health check failed: {e}"]
        }


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


def delete_records_by_domain_pattern(
    domain_pattern: str,
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None
) -> int:
    """
    Delete records by domain pattern
    
    Args:
        domain_pattern: Regex pattern to match domains
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        Number of records deleted
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    try:
        # Validate regex pattern
        re.compile(domain_pattern)
        
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        db_manager = components["db_manager"]
        
        # Delete records
        deleted_count = db_manager.delete_by_domain_pattern(domain_pattern)
        
        logger.info(f"Deleted {deleted_count} records matching domain pattern: {domain_pattern}")
        return deleted_count
        
    except re.error as e:
        logger.error(f"Invalid regex pattern '{domain_pattern}': {e}")
        return 0
    except Exception as e:
        logger.error(f"Error deleting records by domain pattern: {e}")
        return 0


def delete_records_by_url_pattern(
    url_pattern: str,
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None
) -> int:
    """
    Delete records by URL pattern (searches in normalized URLs)
    
    Args:
        url_pattern: Regex pattern to match URLs
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        
    Returns:
        Number of records deleted
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    try:
        # Validate regex pattern
        re.compile(url_pattern)
        
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        db_manager = components["db_manager"]
        
        # Get all records to filter by URL pattern
        all_records = db_manager.collection.get(include=["metadatas"])
        
        matching_ids = []
        for i, metadata in enumerate(all_records['metadatas']):
            normalized_url = metadata.get('normalized_url', '')
            if re.search(url_pattern, normalized_url, re.IGNORECASE):
                matching_ids.append(all_records['ids'][i])
        
        if not matching_ids:
            logger.info(f"No records found matching URL pattern: {url_pattern}")
            return 0
        
        # Delete matching records
        db_manager.collection.delete(ids=matching_ids)
        
        deleted_count = len(matching_ids)
        logger.info(f"Deleted {deleted_count} records matching URL pattern: {url_pattern}")
        return deleted_count
        
    except re.error as e:
        logger.error(f"Invalid regex pattern '{url_pattern}': {e}")
        return 0
    except Exception as e:
        logger.error(f"Error deleting records by URL pattern: {e}")
        return 0


def export_database_to_excel(
    output_path: str,
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None,
    filter_source: str = None,
    filter_domain: str = None
) -> bool:
    """
    Export URL database to Excel file with optional filtering
    
    Args:
        output_path: Path for output Excel file
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        filter_source: Optional source name filter
        filter_domain: Optional domain filter
        
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
        
        if filter_source or filter_domain:
            # Custom filtered export
            import pandas as pd
            
            # Get all records
            all_records = db_manager.collection.get(
                include=["documents", "metadatas"]
            )
            
            if not all_records['ids']:
                logger.warning("No records to export")
                return False
            
            # Prepare filtered data
            export_data = []
            for i, record_id in enumerate(all_records['ids']):
                metadata = all_records['metadatas'][i]
                description = all_records['documents'][i]
                
                # Apply filters
                if filter_source and metadata.get('source_name', '') != filter_source:
                    continue
                
                if filter_domain and metadata.get('domain', '') != filter_domain:
                    continue
                
                export_data.append({
                    'URL': metadata.get('original_url', ''),
                    'Normalized_URL': metadata.get('normalized_url', ''),
                    'Code': metadata.get('tnved_code', ''),
                    'Description': description,
                    'Source': metadata.get('source_name', ''),
                    'Domain': metadata.get('domain', ''),
                    'Shop_Type': metadata.get('shop_type', ''),
                    'Product_ID': metadata.get('product_id', ''),
                    'Created_At': metadata.get('created_at', ''),
                    'Updated_At': metadata.get('updated_at', '')
                })
            
            if not export_data:
                logger.warning("No records match the specified filters")
                return False
            
            # Create DataFrame and export
            df = pd.DataFrame(export_data)
            df.to_excel(output_path, index=False)
            
            logger.info(f"Exported {len(export_data)} filtered records to {output_path}")
            return True
        else:
            # Use built-in export
            success = db_manager.export_to_excel(output_path)
            
            if success:
                logger.info(f"Database exported to: {output_path}")
            else:
                logger.error("Export failed")
            
            return success
        
    except Exception as e:
        logger.error(f"Error exporting database: {e}")
        return False


def cleanup_duplicate_urls(
    db_path: str = "./chroma_db",
    config: URLProcessingConfig = None,
    dry_run: bool = True
) -> Dict[str, int]:
    """
    Clean up duplicate URL records (keeps most recent)
    
    Args:
        db_path: Path to ChromaDB storage
        config: URL processing configuration
        dry_run: If True, only report what would be deleted
        
    Returns:
        Dictionary with cleanup statistics
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = load_url_config_from_env()
    
    stats = {
        "total_records": 0,
        "duplicates_found": 0,
        "records_to_delete": 0,
        "records_deleted": 0
    }
    
    try:
        # Create URL processing components
        components = URLProcessorFactory.create_complete_url_processor(db_path, config)
        db_manager = components["db_manager"]
        
        # Get all records
        all_records = db_manager.collection.get(include=["metadatas"])
        stats["total_records"] = len(all_records['ids'])
        
        if stats["total_records"] == 0:
            logger.info("No records found in database")
            return stats
        
        # Group by normalized URL
        url_groups = {}
        for i, metadata in enumerate(all_records['metadatas']):
            normalized_url = metadata.get('normalized_url', '')
            if normalized_url not in url_groups:
                url_groups[normalized_url] = []
            url_groups[normalized_url].append({
                'id': all_records['ids'][i],
                'metadata': metadata,
                'index': i
            })
        
        # Find duplicates
        records_to_delete = []
        for normalized_url, records in url_groups.items():
            if len(records) > 1:
                stats["duplicates_found"] += 1
                
                # Sort by updated_at timestamp (keep most recent)
                records.sort(key=lambda x: x['metadata'].get('updated_at', ''), reverse=True)
                
                # Mark all but the first (most recent) for deletion
                for record in records[1:]:
                    records_to_delete.append(record['id'])
                    stats["records_to_delete"] += 1
        
        logger.info(f"Found {stats['duplicates_found']} duplicate URL groups")
        logger.info(f"Would delete {stats['records_to_delete']} duplicate records")
        
        if not dry_run and records_to_delete:
            # Actually delete the duplicates
            db_manager.collection.delete(ids=records_to_delete)
            stats["records_deleted"] = len(records_to_delete)
            logger.info(f"Deleted {stats['records_deleted']} duplicate records")
        elif dry_run:
            logger.info("Dry run mode - no records were actually deleted")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error during duplicate cleanup: {e}")
        stats["error"] = str(e)
        return stats


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced URL Database Management CLI for TNVED Code Matching System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s load data.xlsx my_source --db-path ./db
  %(prog)s stats --verbose
  %(prog)s health-check
  %(prog)s delete-source old_data --confirm
  %(prog)s delete-pattern --domain ".*\\.example\\.com" --confirm
  %(prog)s export output.xlsx --filter-source my_source
  %(prog)s cleanup --dry-run
        """
    )
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB path (default: ./chroma_db)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Load URL data from Excel file")
    load_parser.add_argument("file_path", help="Path to Excel file")
    load_parser.add_argument("source_name", help="Source name for the data")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    # Health check command
    health_parser = subparsers.add_parser("health-check", help="Perform database health check")
    
    # Delete by source command
    delete_source_parser = subparsers.add_parser("delete-source", help="Delete records by source")
    delete_source_parser.add_argument("source_name", help="Source name to delete")
    delete_source_parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    
    # Delete by pattern command
    delete_pattern_parser = subparsers.add_parser("delete-pattern", help="Delete records by pattern")
    delete_pattern_group = delete_pattern_parser.add_mutually_exclusive_group(required=True)
    delete_pattern_group.add_argument("--domain", help="Domain regex pattern")
    delete_pattern_group.add_argument("--url", help="URL regex pattern")
    delete_pattern_parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export database to Excel")
    export_parser.add_argument("output_path", help="Output Excel file path")
    export_parser.add_argument("--filter-source", help="Filter by source name")
    export_parser.add_argument("--filter-domain", help="Filter by domain")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up duplicate URLs")
    cleanup_parser.add_argument("--dry-run", action="store_true", default=True, help="Show what would be deleted (default)")
    cleanup_parser.add_argument("--execute", action="store_true", help="Actually perform cleanup")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up logging
    setup_cli_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
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
            
            print("\n📊 URL Database Statistics:")
            print(f"Total records: {stats['total_records']}")
            
            if stats['by_source']:
                print("\n📁 By source:")
                for source, count in sorted(stats['by_source'].items()):
                    print(f"  {source}: {count}")
            
            if stats['by_domain']:
                print("\n🌐 By domain:")
                for domain, count in sorted(stats['by_domain'].items()):
                    print(f"  {domain}: {count}")
            
            if stats['by_shop_type']:
                print("\n🏪 By shop type:")
                for shop, count in sorted(stats['by_shop_type'].items()):
                    print(f"  {shop}: {count}")
            
            return 0
        
        elif args.command == "health-check":
            health = perform_health_check(args.db_path)
            
            status_emoji = {
                "healthy": "✅",
                "warning": "⚠️",
                "unhealthy": "❌"
            }
            
            print(f"\n{status_emoji.get(health['overall_status'], '❓')} Overall Status: {health['overall_status'].upper()}")
            
            print("\n🔍 Health Checks:")
            for check, result in health['checks'].items():
                emoji = "✅" if result else "❌"
                print(f"  {emoji} {check}: {result}")
            
            if health['warnings']:
                print("\n⚠️ Warnings:")
                for warning in health['warnings']:
                    print(f"  • {warning}")
            
            if health['errors']:
                print("\n❌ Errors:")
                for error in health['errors']:
                    print(f"  • {error}")
            
            return 0 if health['overall_status'] != "unhealthy" else 1
        
        elif args.command == "delete-source":
            if not args.confirm:
                print(f"This will delete all records from source: {args.source_name}")
                confirm = input("Are you sure? (yes/no): ")
                if confirm.lower() != "yes":
                    print("Deletion cancelled")
                    return 0
            
            deleted_count = delete_records_by_source(args.source_name, args.db_path)
            print(f"🗑️ Deleted {deleted_count} records")
            return 0
        
        elif args.command == "delete-pattern":
            pattern_type = "domain" if args.domain else "URL"
            pattern = args.domain or args.url
            
            if not args.confirm:
                print(f"This will delete all records matching {pattern_type} pattern: {pattern}")
                confirm = input("Are you sure? (yes/no): ")
                if confirm.lower() != "yes":
                    print("Deletion cancelled")
                    return 0
            
            if args.domain:
                deleted_count = delete_records_by_domain_pattern(args.domain, args.db_path)
            else:
                deleted_count = delete_records_by_url_pattern(args.url, args.db_path)
            
            print(f"🗑️ Deleted {deleted_count} records")
            return 0
        
        elif args.command == "export":
            success = export_database_to_excel(
                args.output_path, 
                args.db_path,
                filter_source=args.filter_source,
                filter_domain=args.filter_domain
            )
            return 0 if success else 1
        
        elif args.command == "cleanup":
            dry_run = not args.execute
            stats = cleanup_duplicate_urls(args.db_path, dry_run=dry_run)
            
            if "error" in stats:
                logger.error(f"Cleanup failed: {stats['error']}")
                return 1
            
            print(f"\n🧹 Duplicate Cleanup Results:")
            print(f"Total records: {stats['total_records']}")
            print(f"Duplicate groups found: {stats['duplicates_found']}")
            print(f"Records to delete: {stats['records_to_delete']}")
            
            if not dry_run:
                print(f"Records deleted: {stats['records_deleted']}")
            else:
                print("(Dry run - no records were actually deleted)")
                print("Use --execute to perform actual cleanup")
            
            return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())