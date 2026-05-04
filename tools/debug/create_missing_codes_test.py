#!/usr/bin/env python3
"""
Extract records with missing TNVED codes from GUOO-Manifest file
"""

import pandas as pd

def main():
    # Read the original file
    df = pd.read_excel('GUOO-Manifest--777Bags.xlsx')
    
    # Find records with missing TNVED codes
    missing_codes = df[df['HTS Code'].isna() | (df['HTS Code'] == '') | (df['HTS Code'] == 0)]
    
    print(f'Found {len(missing_codes)} records with missing TNVED codes')
    
    # Create a simplified test file with just the necessary columns
    test_data = []
    for idx, row in missing_codes.iterrows():
        url_col = "Link to customer's web-page with item description"
        test_data.append({
            'Description': row['Product Description'],
            'Description_EN': row['Product Description in English'],
            'URL': row.get(url_col, ''),
            'Original_Row': idx + 1
        })
    
    # Save to Excel
    test_df = pd.DataFrame(test_data)
    test_df.to_excel('test_missing_codes.xlsx', index=False)
    print('Created test_missing_codes.xlsx with missing records')
    print('\nMissing records:')
    print(test_df.to_string())

if __name__ == "__main__":
    main()