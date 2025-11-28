"""
Example script demonstrating TNVEDLoader usage
"""

from services import TextNormalizer, EmbeddingGenerator, TNVEDLoader
from utils.logger import setup_logging, get_logger


def main():
    """Main example function"""
    # Setup logging
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Initializing ТНВЭД Loader components...")
    
    # Initialize components
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")
    
    # Initialize loader
    loader = TNVEDLoader(
        db_path="./chroma_db",
        normalizer=normalizer,
        embedder=embedder,
        batch_size=100,
        collection_name="tnved"
    )
    
    logger.info("Components initialized successfully")
    
    # Check current record count
    current_count = loader.get_record_count()
    logger.info(f"Current database contains {current_count} records")
    
    # Load data from Excel file
    excel_file = "tnved_full10_new.xlsx"
    
    try:
        logger.info(f"Loading data from {excel_file}...")
        total_loaded = loader.load_from_excel(excel_file)
        
        logger.info(f"✓ Successfully loaded {total_loaded} records")
        
        # Check final count
        final_count = loader.get_record_count()
        logger.info(f"Database now contains {final_count} records")
        
    except FileNotFoundError:
        logger.error(f"✗ Excel file not found: {excel_file}")
        logger.info("Please ensure the Excel file exists in the current directory")
    except Exception as e:
        logger.error(f"✗ Failed to load data: {e}", exc_info=True)


if __name__ == "__main__":
    main()
