"""
Example script demonstrating configuration and logging setup
"""

from utils.config import Config
from utils.logger import setup_logging, get_logger


def main():
    """Main example function"""
    # Load configuration from file
    try:
        config = Config.from_file("config.yaml")
        print("✓ Configuration loaded from config.yaml")
    except FileNotFoundError:
        print("✗ config.yaml not found, using defaults")
        config = Config()
    
    # Validate configuration
    try:
        config.validate()
        print("✓ Configuration is valid")
    except ValueError as e:
        print(f"✗ Configuration validation failed: {e}")
        return
    
    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_format=config.logging.format,
        log_file=config.logging.file
    )
    
    logger = get_logger(__name__)
    logger.info("Configuration and logging initialized successfully")
    
    # Display configuration
    print("\n=== Current Configuration ===")
    print(f"Model: {config.model.name}")
    print(f"Device: {config.model.device}")
    print(f"Database path: {config.database.path}")
    print(f"Collection name: {config.database.collection_name}")
    print(f"Batch size: {config.processing.batch_size}")
    print(f"Default top-k: {config.search.default_top_k}")
    print(f"Log level: {config.logging.level}")
    print(f"Log file: {config.logging.file}")
    
    logger.info("Example script completed")
    print("\n✓ Check the log file for detailed output")


if __name__ == "__main__":
    main()
