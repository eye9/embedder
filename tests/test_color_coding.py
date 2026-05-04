"""
Test script for TNVED code color coding based on similarity scores.

This script creates a test Excel file with various similarity scores
and verifies that the color coding is applied correctly.
"""

import pandas as pd
from pathlib import Path
import logging
from batch_processor.services.excel_processor import ExcelProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_excel():
    """Create a test Excel file with sample data."""
    test_file = Path("test_color_coding_input.xlsx")
    
    data = {
        "Product Detailed Description": [
            "Coffee beans arabica 1kg",
            "Green tea leaves organic",
            "Dark chocolate bar 100g",
            "Olive oil extra virgin",
            "Honey natural raw"
        ]
    }
    
    df = pd.DataFrame(data)
    df.to_excel(test_file, index=False, engine='openpyxl')
    
    logger.info(f"Created test file: {test_file}")
    return test_file


def create_test_results():
    """Create test results with different similarity scores."""
    results = [
        {
            'row_index': 0,
            'tnved_code': '0901110000',
            'selection_reason': 'Found by URL match',
            'confidence_score': 1.0  # URL match - no color
        },
        {
            'row_index': 1,
            'tnved_code': '0902100000',
            'selection_reason': 'Similarity Score: 0.850',
            'confidence_score': 0.850  # High confidence - green
        },
        {
            'row_index': 2,
            'tnved_code': '1806320000',
            'selection_reason': 'Similarity Score: 0.250',
            'confidence_score': 0.250  # Medium confidence - green
        },
        {
            'row_index': 3,
            'tnved_code': '1509100000',
            'selection_reason': 'Similarity Score: 0.185',
            'confidence_score': 0.185  # Threshold - green
        },
        {
            'row_index': 4,
            'tnved_code': '0409000000',
            'selection_reason': 'Similarity Score: 0.120',
            'confidence_score': 0.120  # Low confidence - red
        }
    ]
    
    return results


def test_color_coding():
    """Test the color coding functionality."""
    logger.info("Starting color coding test...")
    
    # Create test input file
    input_file = create_test_excel()
    
    # Create test results
    results = create_test_results()
    
    # Create output file path
    output_file = Path("test_color_coding_output.xlsx")
    
    # Initialize Excel processor
    processor = ExcelProcessor()
    
    # Write results with color coding
    logger.info("Writing results with color coding...")
    processor.write_results(
        original_file=input_file,
        results=results,
        output_file=output_file,
        preserve_existing_hts=False
    )
    
    logger.info(f"✓ Test completed successfully!")
    logger.info(f"✓ Output file created: {output_file}")
    logger.info("")
    logger.info("Expected color coding:")
    logger.info("  Row 1 (Score 1.0):   NO COLOR (URL match)")
    logger.info("  Row 2 (Score 0.850): GREEN (high confidence)")
    logger.info("  Row 3 (Score 0.250): GREEN (above threshold)")
    logger.info("  Row 4 (Score 0.185): GREEN (at threshold)")
    logger.info("  Row 5 (Score 0.120): RED (below threshold)")
    logger.info("")
    logger.info(f"Please open {output_file} to verify the colors!")
    
    # Cleanup test input file
    if input_file.exists():
        input_file.unlink()
        logger.info(f"Cleaned up test input file: {input_file}")


if __name__ == "__main__":
    try:
        test_color_coding()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
