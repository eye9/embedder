#!/usr/bin/env python3
"""
Test TNVED integration with a real Excel file.

This script demonstrates the complete integration working with the existing
GUOO-Manifest--777Bags.xlsx file.
"""

import logging
import sys
from pathlib import Path
import uuid

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.workers.processing_task import process_file_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_real_file_processing():
    """Test processing with the real GUOO manifest file."""
    print("Testing TNVED Integration with Real Excel File")
    print("=" * 50)
    
    # Check if the test file exists
    test_file = "GUOO-Manifest--777Bags.xlsx"
    if not Path(test_file).exists():
        print(f"❌ Test file '{test_file}' not found")
        return False
    
    print(f"📁 Processing file: {test_file}")
    
    try:
        # Process the file with TNVED integration
        result = process_file_sync(
            session_id=str(uuid.uuid4()),
            file_path=test_file,
            process_mode="empty_only",  # Only process rows without existing HTS codes
            algorithm="similarity_top1"
        )
        
        print(f"\n📊 Processing Results:")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'completed':
            print(f"✅ Processing completed successfully!")
            print(f"📈 Processed Rows: {result['processed_rows']}")
            print(f"📋 Total Rows: {result['total_rows']}")
            print(f"❌ Error Count: {result['error_count']}")
            print(f"⏱️  Processing Time: {result['processing_time_seconds']:.2f}s")
            print(f"🔧 Algorithm Used: {result['algorithm_used']}")
            print(f"📄 Output File: {result['output_file']}")
            
            # Check if output file was created
            output_path = Path(result['output_file'])
            if output_path.exists():
                print(f"✅ Output file created successfully")
                print(f"📁 File size: {output_path.stat().st_size / 1024:.1f} KB")
                
                # Read a few rows to show results
                try:
                    import pandas as pd
                    df = pd.read_excel(output_path)
                    
                    print(f"\n📋 Sample Results (first 3 rows with TNVED codes):")
                    tnved_rows = df[df['TNVED_Code'].notna() & (df['TNVED_Code'] != '')]
                    
                    if len(tnved_rows) > 0:
                        for i, (idx, row) in enumerate(tnved_rows.head(3).iterrows()):
                            print(f"\n{i+1}. Row {idx + 1}:")
                            print(f"   Description: {str(row.get('Product Detailed Description', ''))[:80]}...")
                            print(f"   TNVED Code: {row.get('TNVED_Code', '')}")
                            print(f"   Reason: {str(row.get('Selection_Reason', ''))[:100]}...")
                    else:
                        print("   No TNVED codes were assigned (all rows may have existing codes)")
                        
                except Exception as e:
                    print(f"⚠️  Could not read output file details: {e}")
            else:
                print(f"❌ Output file not found at {result['output_file']}")
            
            return True
        else:
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


def main():
    """Run the real file integration test."""
    success = test_real_file_processing()
    
    if success:
        print("\n🎉 Real file integration test completed successfully!")
        print("The TNVED system integration is working correctly with actual data.")
        return 0
    else:
        print("\n💥 Real file integration test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())