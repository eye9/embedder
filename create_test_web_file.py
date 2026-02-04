#!/usr/bin/env python3
"""
Create a test Excel file for web interface testing.
"""

import pandas as pd
from pathlib import Path

def create_test_file():
    """Create a test Excel file."""
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
    output_file = Path("test_web_color_coding.xlsx")
    df.to_excel(output_file, index=False)
    print(f"Created test file: {output_file}")

if __name__ == "__main__":
    create_test_file()