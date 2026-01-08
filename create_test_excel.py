#!/usr/bin/env python3
"""
Create a simple test Excel file.
"""

import pandas as pd
from pathlib import Path

def create_test_excel():
    """Create a simple test Excel file."""
    
    # Create test data
    data = {
        'Product Detailed Description': [
            'Test product 1',
            'Test product 2',
            'Test product 3'
        ],
        'HTS Code': [
            '1234567890',
            '',
            '0987654321'
        ],
        'Other Column': [
            'Value 1',
            'Value 2', 
            'Value 3'
        ]
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to Excel
    output_file = Path("test_simple.xlsx")
    df.to_excel(output_file, index=False)
    
    print(f"Created test Excel file: {output_file}")
    print(f"File size: {output_file.stat().st_size} bytes")
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")

if __name__ == "__main__":
    create_test_excel()