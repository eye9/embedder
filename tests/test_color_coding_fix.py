#!/usr/bin/env python3
"""
Test script to verify color coding functionality after fix.
"""

import logging
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.services.excel_processor import ExcelProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_input():
    """Create a test Excel file with sample data."""
    test_file = Path("test_color_coding_input.xlsx")
    
    data = {
        'Product Detailed Description': [
            'Кофе арабика зерновой 1кг',
            'Шоколад молочный 100г',
            'Оливковое масло первого отжима',
            'Мед натуральный цветочный'
        ],
        'HTS_Code': ['', '', '', '']  # Empty HTS codes
    }
    
    df = pd.DataFrame(data)
    df.to_excel(test_file, index=False)
    logger.info(f"Created test input file: {test_file}")
    return test_file

def create_test_results():
    """Create test results with different confidence scores."""
    results = [
        {
            'row_index': 0,
            'tnved_code': '0901110000',
            'selection_reason': 'Similarity Score: 0.950',
            'confidence_score': 0.950  # High confidence - green
        },
        {
            'row_index': 1,
            'tnved_code': '1806320000',
            'selection_reason': 'Similarity Score: 0.250',
            'confidence_score': 0.250  # Medium confidence - green
        },
        {
            'row_index': 2,
            'tnved_code': '1509100000',
            'selection_reason': 'Similarity Score: 0.185',
            'confidence_score': 0.185  # Threshold - green
        },
        {
            'row_index': 3,
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
    input_file = create_test_input()
    
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
    
    logger.info(f"✓ Output file created: {output_file}")
    logger.info("")
    logger.info("Expected color coding:")
    logger.info("  Row 1 (Score 0.950): GREEN (high confidence)")
    logger.info("  Row 2 (Score 0.250): GREEN (medium confidence)")
    logger.info("  Row 3 (Score 0.185): GREEN (threshold)")
    logger.info("  Row 4 (Score 0.120): RED (low confidence)")
    logger.info("")
    logger.info("Please open the output file in Excel to verify colors!")

if __name__ == "__main__":
    try:
        test_color_coding()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)