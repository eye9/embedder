#!/usr/bin/env python3
"""
Test color coding with real-world selection_reason format.
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

def test_real_color_coding():
    """Test color coding with real-world selection_reason format."""
    logger.info("=== Testing color coding with real selection_reason ===")
    
    # Create test input
    test_file = Path("real_color_input.xlsx")
    data = {
        'Product Detailed Description': [
            'Акриловая подвеска для автомобиля',
            'Кофе арабика зерновой 1кг',
            'Шоколад молочный 100г'
        ],
        'HTS_Code': ['', '', '']
    }
    
    df = pd.DataFrame(data)
    df.to_excel(test_file, index=False)
    logger.info(f"Created test input: {test_file}")
    
    # Create test results with REAL selection_reason format
    results = [
        {
            'row_index': 0,
            'tnved_code': '8708999709',
            'selection_reason': 'Found by URL: https://market.yandex.ru/product/1333934340?offerid=LhprmuZjvM9hcWww4lOQ4g&sku=4580438678 | Code: 8708999709 | Description: Акриловая подвеска для автомобиля, брелок-подвеска с милым котом*1 | Source: import_26-01 | Shop: yandex_market | ID: 1333934340 | Confidence: 1.00 | Time: 7.8ms',
            'confidence_score': 1.0  # URL match - should be NO COLOR
        },
        {
            'row_index': 1,
            'tnved_code': '0901110000',
            'selection_reason': 'Found by semantic search | Similarity Score: 0.850',
            'confidence_score': 0.850  # High confidence - should be GREEN
        },
        {
            'row_index': 2,
            'tnved_code': '1806320000',
            'selection_reason': 'URL not found, used semantic search | Similarity Score: 0.120',
            'confidence_score': 0.120  # Low confidence - should be RED
        }
    ]
    
    logger.info("Test results:")
    for r in results:
        logger.info(f"  Row {r['row_index']}: score={r['confidence_score']}, reason={r['selection_reason'][:80]}...")
    
    # Process with Excel processor
    output_file = Path("real_color_output.xlsx")
    processor = ExcelProcessor()
    
    logger.info("Calling write_results...")
    processor.write_results(
        original_file=test_file,
        results=results,
        output_file=output_file,
        preserve_existing_hts=False
    )
    
    logger.info(f"✅ Test completed. Output file: {output_file}")
    logger.info("")
    logger.info("Expected colors:")
    logger.info("  Row 1 (URL match, score 1.0):   NO COLOR (white)")
    logger.info("  Row 2 (Semantic, score 0.850):  GREEN")
    logger.info("  Row 3 (Semantic, score 0.120):  RED")
    logger.info("")
    logger.info("Please open the output file in Excel to verify colors!")

if __name__ == "__main__":
    try:
        test_real_color_coding()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)