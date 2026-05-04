#!/usr/bin/env python3
"""
ТНВЭД Search CLI

Command-line interface for searching ТНВЭД codes by text description.
This script provides semantic search capabilities using the vector database
populated with ТНВЭД codes and descriptions.

Usage:
    python search_tnved.py <query> [options]

Examples:
    # Basic search
    python search_tnved.py "кофейные зерна арабика"

    # Search with custom number of results
    python search_tnved.py "зеленый чай" --top-k 10

    # Search with custom configuration
    python search_tnved.py "сахар белый" --config config.yaml

    # Get details for specific code
    python search_tnved.py --code 0901110000

    # Interactive mode
    python search_tnved.py --interactive

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import argparse
import sys
from pathlib import Path

from services import TextNormalizer, EmbeddingGenerator, TNVEDSearcher
from services.tnved_searcher import SearchError
from services.enhanced_searcher import EnhancedSearcher
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
        description="Search for ТНВЭД codes by text description using semantic similarity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "кофейные зерна арабика"
  %(prog)s "зеленый чай" --top-k 10
  %(prog)s "сахар белый" --config config.yaml
  %(prog)s "кофе" --source-filter reference
  %(prog)s "товары" --source-filter product
  %(prog)s --code 0901110000
  %(prog)s --interactive
        """
    )
    
    # Query argument (optional if using --code or --interactive)
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        default=None,
        help="Text description to search for (e.g., 'кофейные зерна арабика')"
    )
    
    # Search options
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=None,
        help="Number of top results to return (default: 5)"
    )
    
    parser.add_argument(
        "--source-filter",
        type=str,
        choices=["reference", "product"],
        default=None,
        help="Filter results by source type: reference (official ТНВЭД) or product (real products with codes)"
    )
    
    # Code lookup mode
    parser.add_argument(
        "--code",
        type=str,
        default=None,
        help="Look up details for a specific ТНВЭД code"
    )
    
    # Interactive mode
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enter interactive search mode"
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
    
    # Output options
    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "simple"],
        default="table",
        help="Output format: table, json, or simple (default: table)"
    )
    
    parser.add_argument(
        "--show-normalized",
        action="store_true",
        help="Show normalized text in results"
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
        help="Suppress all output except search results"
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
            if not args.quiet:
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
    
    if args.top_k:
        config.search.default_top_k = args.top_k
    
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


def format_results_table(results, show_normalized=False):
    """
    Format search results as a table.
    
    Args:
        results: List of SearchResult objects
        show_normalized: Whether to show normalized text
    """
    if not results:
        print("No results found.")
        return
    
    print()
    print("=" * 100)
    print(f"Found {len(results)} result(s)")
    print("=" * 100)
    print()
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Code: {result.code}")
        print(f"   Similarity: {result.similarity_score:.4f}")
        print(f"   Description: {result.description}")
        print(f"   Source: {result.source_type}")
        if result.source_name:
            print(f"   Source Name: {result.source_name}")
        if result.source_id:
            print(f"   Source ID: {result.source_id}")
        
        if show_normalized:
            print(f"   Normalized: {result.normalized_text}")
        
        print()


def format_results_json(results):
    """
    Format search results as JSON.
    
    Args:
        results: List of SearchResult objects
    """
    import json
    
    results_dict = [
        {
            "code": r.code,
            "description": r.description,
            "normalized_text": r.normalized_text,
            "similarity_score": r.similarity_score,
            "source_type": r.source_type,
            "source_name": r.source_name,
            "source_id": r.source_id
        }
        for r in results
    ]
    
    print(json.dumps(results_dict, ensure_ascii=False, indent=2))


def format_results_simple(results):
    """
    Format search results in simple format.
    
    Args:
        results: List of SearchResult objects
    """
    for result in results:
        source_info = f"[{result.source_type}]"
        if result.source_name:
            source_info += f" {result.source_name}"
        print(f"{result.code}\t{result.similarity_score:.4f}\t{source_info}\t{result.description}")


def perform_search(searcher, query, top_k, args):
    """
    Perform a search and display results.
    
    Args:
        searcher: EnhancedSearcher instance
        query: Search query text
        top_k: Number of results to return
        args: Command-line arguments
    """
    try:
        if not args.quiet and args.format == "table":
            print(f"\nSearching for: '{query}'")
            print(f"Top-k: {top_k}")
            if args.source_filter:
                print(f"Source filter: {args.source_filter}")
        
        # Perform search with source filter
        results = searcher.search(query, top_k=top_k, source_filter=args.source_filter)
        
        # Format and display results
        if args.format == "table":
            format_results_table(results, show_normalized=args.show_normalized)
        elif args.format == "json":
            format_results_json(results)
        elif args.format == "simple":
            format_results_simple(results)
        
    except SearchError as e:
        print(f"[ERROR] Search error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)


def lookup_code(searcher, code, args):
    """
    Look up details for a specific code.
    
    Args:
        searcher: EnhancedSearcher instance
        code: ТНВЭД code to look up
        args: Command-line arguments
    """
    try:
        # Validate and normalize the code
        try:
            normalized_code = validate_tnved_code(code, strict=False)
            if normalized_code != code:
                if not args.quiet and args.format == "table":
                    print(f"[INFO] Code normalized: '{code}' -> '{normalized_code}'")
            code = normalized_code
        except (TNVEDValidationError, ValueError) as e:
            print(f"[ERROR] Invalid ТНВЭД code format: {e}", file=sys.stderr)
            sys.exit(1)
        
        if not args.quiet and args.format == "table":
            print(f"\nLooking up code: {code}")
        
        # Get all records for this code
        results = searcher.get_all_records_for_code(code)
        
        if results:
            if args.format == "table":
                print()
                print("=" * 100)
                print("Code Details")
                print("=" * 100)
                print()
                for i, result in enumerate(results, 1):
                    print(f"{i}. Code: {result.code}")
                    print(f"   Description: {result.description}")
                    print(f"   Source: {result.source_type}")
                    if result.source_name:
                        print(f"   Source Name: {result.source_name}")
                    if result.source_id:
                        print(f"   Source ID: {result.source_id}")
                    
                    if args.show_normalized:
                        print(f"   Normalized: {result.normalized_text}")
                    
                    print()
            elif args.format == "json":
                format_results_json(results)
            elif args.format == "simple":
                format_results_simple(results)
        else:
            print(f"[ERROR] Code not found: {code}", file=sys.stderr)
            sys.exit(1)
        
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def interactive_mode(searcher, top_k, args):
    """
    Enter interactive search mode.
    
    Args:
        searcher: EnhancedSearcher instance
        top_k: Default number of results
        args: Command-line arguments
    """
    print()
    print("=" * 70)
    print("ТНВЭД Interactive Search")
    print("=" * 70)
    print()
    print("Enter search queries or commands:")
    print("  - Type a description to search")
    print("  - Type 'code:<code>' to look up a specific code")
    print("  - Type 'top-k:<n>' to change number of results")
    print("  - Type 'filter:<type>' to set source filter (reference/product/none)")
    print("  - Type 'quit' or 'exit' to exit")
    print()
    
    current_top_k = top_k
    current_filter = args.source_filter
    
    while True:
        try:
            # Show current settings in prompt
            filter_text = f" [filter: {current_filter}]" if current_filter else ""
            prompt = f"Search{filter_text}> "
            
            # Get user input
            query = input(prompt).strip()
            
            if not query:
                continue
            
            # Check for commands
            if query.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break
            
            elif query.lower().startswith("code:"):
                code = query[5:].strip()
                # Validate the code before lookup
                try:
                    normalized_code = validate_tnved_code(code, strict=False)
                    if normalized_code != code:
                        print(f"[INFO] Code normalized: '{code}' -> '{normalized_code}'")
                    lookup_code(searcher, normalized_code, args)
                except (TNVEDValidationError, ValueError) as e:
                    print(f"[ERROR] Invalid ТНВЭД code format: {e}", file=sys.stderr)
            
            elif query.lower().startswith("top-k:"):
                try:
                    new_top_k = int(query[6:].strip())
                    if new_top_k > 0:
                        current_top_k = new_top_k
                        print(f"[OK] Top-k set to {current_top_k}")
                    else:
                        print("[ERROR] Top-k must be positive", file=sys.stderr)
                except ValueError:
                    print("[ERROR] Invalid top-k value", file=sys.stderr)
            
            elif query.lower().startswith("filter:"):
                filter_value = query[7:].strip().lower()
                if filter_value == "none":
                    current_filter = None
                    print("[OK] Source filter cleared")
                elif filter_value in ["reference", "product"]:
                    current_filter = filter_value
                    print(f"[OK] Source filter set to {current_filter}")
                else:
                    print("[ERROR] Invalid filter. Use 'reference', 'product', or 'none'", file=sys.stderr)
            
            else:
                # Perform search with current filter
                # Temporarily update args.source_filter
                original_filter = args.source_filter
                args.source_filter = current_filter
                perform_search(searcher, query, current_top_k, args)
                args.source_filter = original_filter
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


def main():
    """Main CLI entry point"""
    # Parse arguments
    args = parse_arguments()
    
    # Validate arguments
    if not args.query and not args.code and not args.interactive:
        print("[ERROR] Must provide a query, --code, or --interactive", file=sys.stderr)
        print("Use --help for usage information", file=sys.stderr)
        sys.exit(1)
    
    # Load configuration
    config = load_configuration(args)
    
    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        log_format=config.logging.format
    )
    logger = get_logger(__name__)
    
    # Print header (unless quiet or non-table format)
    if not args.quiet and args.format == "table" and not args.interactive:
        print("=" * 70)
        print("ТНВЭД Search")
        print("=" * 70)
        print()
    
    try:
        # Initialize components
        if not args.quiet and args.format == "table":
            print("Initializing components...")
        
        logger.info("Initializing TextNormalizer")
        normalizer = TextNormalizer()
        
        logger.info(f"Initializing EmbeddingGenerator with model {config.model.name}")
        embedder = EmbeddingGenerator(
            model_name=config.model.name,
            device=config.model.device
        )
        
        logger.info("Initializing EnhancedSearcher")
        searcher = EnhancedSearcher(
            db_path=config.database.path,
            normalizer=normalizer,
            embedder=embedder,
            collection_name=config.database.collection_name
        )
        
        # Get database statistics
        stats = searcher.get_database_stats()
        logger.info(f"Database contains {stats['total_records']} records")
        
        if stats['total_records'] == 0:
            print("[ERROR] Database is empty. Please load data first using load_tnved.py", file=sys.stderr)
            sys.exit(1)
        
        if not args.quiet and args.format == "table":
            print(f"[OK] Components initialized")
            print(f"  Database: {stats['total_records']} records")
            print(f"    Reference: {stats['reference_records']}")
            print(f"    Product: {stats['product_records']}")
            if args.source_filter:
                print(f"  Source filter: {args.source_filter}")
        
        # Determine top-k
        top_k = args.top_k if args.top_k else config.search.default_top_k
        
        # Execute requested operation
        if args.interactive:
            interactive_mode(searcher, top_k, args)
        
        elif args.code:
            lookup_code(searcher, args.code, args)
        
        else:
            perform_search(searcher, args.query, top_k, args)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("Search interrupted by user")
        print("\n[WARNING] Interrupted by user", file=sys.stderr)
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
