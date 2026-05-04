#!/usr/bin/env python3
"""
Test script to verify that empty_only mode processes only rows with missing HTS codes.
"""

import pandas as pd
import sys
import os
from pathlib import Path

def test_file_analysis():
    """Analyze the GUOO-Manifest file to understand what should be processed."""
    
    file_path = "GUOO-Manifest--777Bags.xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found")
        return False
    
    print(f"📁 Analyzing file: {file_path}")
    
    # Read the file
    df = pd.read_excel(file_path)
    
    print(f"📊 Total rows: {len(df)}")
    print(f"📊 Total columns: {len(df.columns)}")
    
    # Check for required columns
    description_col = None
    hts_col = None
    
    for col in df.columns:
        if "Product Detailed Description" in str(col):
            description_col = col
        if "HTS Code" in str(col):
            hts_col = col
    
    if not description_col:
        print("❌ No 'Product Detailed Description' column found")
        return False
    
    if not hts_col:
        print("❌ No 'HTS Code' column found")
        return False
    
    print(f"✅ Found description column: '{description_col}'")
    print(f"✅ Found HTS code column: '{hts_col}'")
    
    # Analyze data
    total_rows = len(df)
    rows_with_descriptions = df[description_col].notna().sum()
    rows_with_hts_codes = df[hts_col].notna().sum()
    rows_with_empty_hts = df[hts_col].isna().sum()
    
    print(f"\n📈 Data Analysis:")
    print(f"  Total rows: {total_rows}")
    print(f"  Rows with descriptions: {rows_with_descriptions}")
    print(f"  Rows with HTS codes: {rows_with_hts_codes}")
    print(f"  Rows with empty HTS codes: {rows_with_empty_hts}")
    
    # Find rows that should be processed in empty_only mode
    mask_has_description = df[description_col].notna() & (df[description_col].astype(str).str.strip() != '')
    mask_no_hts = df[hts_col].isna() | (df[hts_col].astype(str).str.strip() == '')
    
    should_process = mask_has_description & mask_no_hts
    rows_to_process = should_process.sum()
    
    print(f"  Rows to process in empty_only mode: {rows_to_process}")
    
    if rows_to_process > 0:
        print(f"\n🔍 Rows that should be processed:")
        to_process_df = df[should_process]
        for idx, row in to_process_df.iterrows():
            desc = str(row[description_col])[:50]
            print(f"  Row {idx}: '{desc}...'")
    
    return True

def test_excel_processor_filtering():
    """Test the ExcelProcessor filtering logic."""
    
    try:
        from batch_processor.services.excel_processor import ExcelProcessor
        
        processor = ExcelProcessor()
        file_path = Path("GUOO-Manifest--777Bags.xlsx")
        
        print(f"\n🧪 Testing ExcelProcessor filtering...")
        
        # Test empty_only mode
        chunk_count = 0
        total_filtered_rows = 0
        
        for chunk, start_row, total_rows in processor.read_file_chunked(file_path, "empty_only"):
            chunk_count += 1
            chunk_size = len(chunk)
            total_filtered_rows += chunk_size
            
            print(f"  Chunk {chunk_count}: {chunk_size} rows (original rows {start_row} to {start_row + chunk_size - 1})")
            
            # Show first few rows of each chunk
            if chunk_size > 0:
                description_col = None
                for col in chunk.columns:
                    if "Product Detailed Description" in str(col):
                        description_col = col
                        break
                
                if description_col:
                    for i, (idx, row) in enumerate(chunk.iterrows()):
                        if i < 3:  # Show first 3 rows
                            desc = str(row[description_col])[:50]
                            print(f"    Row {idx}: '{desc}...'")
                        elif i == 3 and chunk_size > 3:
                            print(f"    ... and {chunk_size - 3} more rows")
                            break
        
        print(f"\n📊 Filtering Results:")
        print(f"  Total chunks: {chunk_count}")
        print(f"  Total filtered rows: {total_filtered_rows}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing ExcelProcessor: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing empty_only mode fix...")
    
    success = True
    
    # Test 1: File analysis
    if not test_file_analysis():
        success = False
    
    # Test 2: ExcelProcessor filtering
    if not test_excel_processor_filtering():
        success = False
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)