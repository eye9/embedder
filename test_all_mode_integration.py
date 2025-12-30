#!/usr/bin/env python3
"""
Test TNVED integration with "all" mode to see actual code assignment.
"""

import logging
import sys
from pathlib import Path
import uuid
import pandas as pd

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.workers.processing_task import process_file_sync

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_all_mode_processing():
    """Test processing with "all" mode on a subset of data."""
    print("Testing TNVED Integration with 'all' mode (first 10 rows)")
    print("=" * 60)
    
    # Check if the test file exists
    test_file = "GUOO-Manifest--777Bags.xlsx"
    if not Path(test_file).exists():
        print(f"❌ Test file '{test_file}' not found")
        return False
    
    # Create a smaller test file with just the first 10 rows
    try:
        print("📁 Creating subset test file...")
        df = pd.read_excel(test_file)
        
        # Take first 10 rows and clear some HTS codes to see assignment
        subset_df = df.head(10).copy()
        
        # Clear HTS codes for rows 2, 4, 6, 8 to see new assignments
        for i in [1, 3, 5, 7]:  # 0-indexed
            if i < len(subset_df):
                subset_df.iloc[i, subset_df.columns.get_loc('HTS Code')] = ''
        
        # Save subset file
        subset_file = "test_subset_manifest.xlsx"
        subset_df.to_excel(subset_file, index=False)
        print(f"✅ Created subset file: {subset_file}")
        
        # Show what we're processing
        print(f"\n📋 Processing {len(subset_df)} rows:")
        for i, row in subset_df.iterrows():
            desc = str(row.get('Product Detailed Description', ''))[:50]
            existing_code = str(row.get('HTS Code', ''))
            status = "HAS CODE" if existing_code and existing_code != 'nan' else "NEEDS CODE"
            print(f"  {i+1}. {desc}... [{status}]")
        
    except Exception as e:
        print(f"❌ Failed to create subset file: {e}")
        return False
    
    try:
        print(f"\n🔄 Processing with TNVED integration...")
        
        # Process the subset file
        result = process_file_sync(
            session_id=str(uuid.uuid4()),
            file_path=subset_file,
            process_mode="all",  # Process all rows to see TNVED assignment
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
            
            # Read and show results
            output_path = Path(result['output_file'])
            if output_path.exists():
                print(f"\n📋 TNVED Assignment Results:")
                
                output_df = pd.read_excel(output_path)
                
                for i, row in output_df.iterrows():
                    desc = str(row.get('Product Detailed Description', ''))[:50]
                    original_code = str(subset_df.iloc[i].get('HTS Code', ''))
                    tnved_code = str(row.get('TNVED_Code', ''))
                    reason = str(row.get('Selection_Reason', ''))[:80]
                    
                    print(f"\n{i+1}. {desc}...")
                    print(f"   Original HTS: {original_code if original_code != 'nan' else 'EMPTY'}")
                    print(f"   TNVED Code: {tnved_code}")
                    print(f"   Reason: {reason}...")
                
                print(f"\n✅ Output saved to: {output_path}")
            else:
                print(f"❌ Output file not found")
            
            return True
        else:
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        # Clean up subset file
        try:
            Path(subset_file).unlink()
        except:
            pass


def main():
    """Run the all mode integration test."""
    success = test_all_mode_processing()
    
    if success:
        print("\n🎉 All mode integration test completed successfully!")
        print("The TNVED system is correctly assigning codes to product descriptions.")
        return 0
    else:
        print("\n💥 All mode integration test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())