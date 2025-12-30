#!/usr/bin/env python3
"""
Test script to validate Excel files for the batch processor.
"""

import os
import sys
from pathlib import Path

def test_file_validation(file_path: str):
    """Test file validation for the batch processor."""
    
    # Set the configuration file path
    config_path = Path("batch_processor_config.yaml")
    if config_path.exists():
        os.environ["BATCH_PROCESSOR_CONFIG"] = str(config_path.absolute())
        print(f"Using configuration file: {config_path.absolute()}")
    
    try:
        from batch_processor.services.excel_processor import ExcelProcessor
        from batch_processor.config.settings import get_config
        
        # Load configuration
        config = get_config()
        print(f"Configuration loaded successfully")
        print(f"Max file size: {config.processing.max_file_size_mb}MB")
        print(f"Supported extensions: {config.processing.supported_extensions}")
        
        # Test file validation
        processor = ExcelProcessor()
        file_path_obj = Path(file_path)
        
        print(f"\nTesting file: {file_path}")
        print(f"File exists: {file_path_obj.exists()}")
        
        if not file_path_obj.exists():
            print("Error: File not found")
            return False
        
        # Validate file
        is_valid, error_msg, total_rows = processor.validate_file(file_path_obj)
        
        print(f"\nValidation Results:")
        print(f"Valid: {is_valid}")
        print(f"Error: {error_msg}")
        print(f"Total rows: {total_rows}")
        
        if is_valid:
            # Get detailed file info
            file_info = processor.get_file_info(file_path_obj)
            print(f"\nFile Information:")
            print(f"Total rows: {file_info['total_rows']}")
            print(f"Rows with descriptions: {file_info['rows_with_descriptions']}")
            print(f"Rows with existing HTS codes: {file_info['rows_with_existing_codes']}")
            print(f"Has description column: {file_info['has_description_column']}")
            print(f"Has HTS column: {file_info['has_hts_column']}")
            print(f"Description column: {file_info['description_column']}")
            print(f"HTS column: {file_info['hts_column']}")
            
            print(f"\nColumns in file ({len(file_info['columns'])}):")
            for i, col in enumerate(file_info['columns'], 1):
                print(f"  {i:2d}. {col}")
        
        return is_valid
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python test_file_validation.py <excel_file_path>")
        print("Example: python test_file_validation.py GUOO-Manifest--777Bags.xlsx")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = test_file_validation(file_path)
    
    if success:
        print("\n✅ File validation successful! The file can be processed.")
    else:
        print("\n❌ File validation failed! Please check the file format and content.")
        sys.exit(1)

if __name__ == "__main__":
    main()