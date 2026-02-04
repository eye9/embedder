#!/usr/bin/env python3
"""
Debug test for color coding functionality.
"""

import logging
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.services.excel_processor import ExcelProcessor

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_color_coding_debug():
    """Test color coding with detailed logging."""
    logger.info("=== Starting debug color coding test ===")
    
    # Create test input
    test_file = Path("debug_color_input.xlsx")
    data = {
        'Product Detailed Description': [
            'Кофе арабика зерновой 1кг',
            'Шоколад молочный 100г'
        ],
        'HTS_Code': ['', '']
    }
    
    df = pd.DataFrame(data)
    df.to_excel(test_file, index=False)
    logger.info(f"Created test input: {test_file}")
    
    # Create test results with confidence scores
    results = [
        {
            'row_index': 0,
            'tnved_code': '0901110000',
            'selection_reason': 'High confidence match',
            'confidence_score': 0.95  # Should be green
        },
        {
            'row_index': 1,
            'tnved_code': '1806320000',
            'selection_reason': 'Low confidence match',
            'confidence_score': 0.12  # Should be red
        }
    ]
    
    logger.info(f"Test results: {results}")
    
    # Process with Excel processor
    output_file = Path("debug_color_output.xlsx")
    processor = ExcelProcessor()
    
    logger.info("Calling write_results...")
    processor.write_results(
        original_file=test_file,
        results=results,
        output_file=output_file,
        preserve_existing_hts=False
    )
    
    logger.info(f"✅ Test completed. Output file: {output_file}")
    logger.info("Expected colors:")
    logger.info("  Row 1: GREEN (score 0.95 >= 0.185)")
    logger.info("  Row 2: RED (score 0.12 < 0.185)")

if __name__ == "__main__":
    try:
        test_color_coding_debug()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)