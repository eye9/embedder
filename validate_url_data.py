#!/usr/bin/env python3
"""
URL Data Validation Command-Line Tool

This script provides command-line interface for validating URL data files
and generating data quality reports for the TNVED code matching system.
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.url_data_quality_checker import (
    URLDataQualityChecker,
    validate_url_data_file
)


def validate_file_command(args):
    """Validates a URL data file and generates quality report"""
    print(f"Validating URL data file: {args.file}")
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return 1
    
    # Validate the file
    result = validate_url_data_file(args.file)
    
    if not result["success"]:
        print(f"Validation failed: {result['error']}")
        return 1
    
    # Display summary
    analysis = result["analysis"]
    print(f"\n=== Validation Summary ===")
    print(f"Total records: {analysis['total_records']}")
    print(f"URL quality score: {analysis['url_quality_score']:.1f}%")
    print(f"TNVED quality score: {analysis['tnved_quality_score']:.1f}%")
    print(f"Overall quality score: {analysis['overall_quality_score']:.1f}%")
    print(f"Recommendations: {len(analysis['recommendations'])}")
    
    # Show recommendations if any
    if analysis["recommendations"]:
        print(f"\n=== Recommendations ===")
        for i, rec in enumerate(analysis["recommendations"], 1):
            print(f"{i}. {rec}")
    
    # Export detailed report if requested
    if args.output:
        checker = URLDataQualityChecker()
        full_result = checker.analyze_excel_file(args.file)
        
        if args.output.endswith('.xlsx'):
            success = checker.export_report_to_excel(full_result, args.output)
            if success:
                print(f"\nDetailed report exported to: {args.output}")
            else:
                print(f"\nError exporting report to: {args.output}")
        else:
            # Export as JSON
            success = checker.export_report_to_json(full_result, args.output)
            if success:
                print(f"\nDetailed report exported to: {args.output}")
            else:
                print(f"\nError exporting report to: {args.output}")
    
    return 0


def validate_database_command(args):
    """Validates URL database and generates quality report"""
    print("Validating URL database...")
    
    try:
        print("Note: Direct database validation requires URLDatabaseManager.")
        print("Please use 'validate-file' command to validate Excel files with URL data.")
        return 1
        
    except Exception as e:
        print(f"Error validating database: {e}")
        return 1


def validate_urls_command(args):
    """Validates a list of URLs"""
    print("Validating URLs...")
    
    # Read URLs from file or command line
    urls = []
    if args.urls_file:
        if not os.path.exists(args.urls_file):
            print(f"Error: URLs file not found: {args.urls_file}")
            return 1
        
        with open(args.urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = args.urls
    
    if not urls:
        print("Error: No URLs provided")
        return 1
    
    # Validate URLs
    checker = URLDataQualityChecker()
    results = {
        'total': len(urls),
        'valid': 0,
        'invalid': 0,
        'warnings': 0,
        'results': [],
        'summary': {
            'common_errors': {},
            'common_warnings': {},
            'shop_types': {},
            'domains': {}
        }
    }
    
    for url in urls:
        validation_result = checker.validate_url(url)
        results['results'].append(validation_result)
        
        if validation_result['is_valid']:
            results['valid'] += 1
            
            # Track shop types
            if validation_result.get('shop_type'):
                shop_type = validation_result['shop_type']
                results['summary']['shop_types'][shop_type] = \
                    results['summary']['shop_types'].get(shop_type, 0) + 1
            
            # Track domains
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                results['summary']['domains'][domain] = \
                    results['summary']['domains'].get(domain, 0) + 1
            except:
                pass
        else:
            results['invalid'] += 1
            
            # Track common errors
            if validation_result.get('error_message'):
                error = validation_result['error_message']
                results['summary']['common_errors'][error] = \
                    results['summary']['common_errors'].get(error, 0) + 1
        
        # Track warnings
        if validation_result.get('warnings'):
            results['warnings'] += 1
            for warning in validation_result['warnings']:
                results['summary']['common_warnings'][warning] = \
                    results['summary']['common_warnings'].get(warning, 0) + 1
    
    # Display results
    print(f"\n=== URL Validation Results ===")
    print(f"Total URLs: {results['total']}")
    print(f"Valid URLs: {results['valid']}")
    print(f"Invalid URLs: {results['invalid']}")
    print(f"URLs with warnings: {results['warnings']}")
    
    # Show shop type distribution
    if results['summary']['shop_types']:
        print(f"\n=== Detected Shop Types ===")
        for shop_type, count in results['summary']['shop_types'].items():
            print(f"  {shop_type}: {count}")
    
    # Show common errors
    if results['summary']['common_errors']:
        print(f"\n=== Common Errors ===")
        for error, count in results['summary']['common_errors'].items():
            print(f"  {error}: {count}")
    
    # Show detailed results if requested
    if args.verbose:
        print(f"\n=== Detailed Results ===")
        for i, result in enumerate(results['results'], 1):
            status = "✓" if result['is_valid'] else "✗"
            print(f"{i:3d}. {status} {result['url']}")
            
            if result.get('shop_type'):
                print(f"     Shop: {result['shop_type']}")
            if result.get('product_id'):
                print(f"     Product ID: {result['product_id']}")
            if result.get('error_message'):
                print(f"     Error: {result['error_message']}")
            if result.get('warnings'):
                for warning in result['warnings']:
                    print(f"     Warning: {warning}")
    
    # Export results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResults exported to: {args.output}")
    
    return 0


def validate_tnved_codes_command(args):
    """Validates a list of TNVED codes"""
    print("Validating TNVED codes...")
    
    # Read codes from file or command line
    codes = []
    if args.codes_file:
        if not os.path.exists(args.codes_file):
            print(f"Error: Codes file not found: {args.codes_file}")
            return 1
        
        with open(args.codes_file, 'r', encoding='utf-8') as f:
            codes = [line.strip() for line in f if line.strip()]
    else:
        codes = args.codes
    
    if not codes:
        print("Error: No TNVED codes provided")
        return 1
    
    # Validate codes
    checker = URLDataQualityChecker()
    results = {
        'total': len(codes),
        'valid': 0,
        'invalid': 0,
        'warnings': 0,
        'results': [],
        'summary': {
            'common_errors': {},
            'common_warnings': {},
            'code_lengths': {},
            'code_prefixes': {}
        }
    }
    
    for code in codes:
        validation_result = checker.validate_tnved_code(code)
        results['results'].append(validation_result)
        
        if validation_result['is_valid']:
            results['valid'] += 1
            
            # Track code prefixes (first 4 digits)
            if validation_result.get('normalized_code'):
                prefix = validation_result['normalized_code'][:4]
                results['summary']['code_prefixes'][prefix] = \
                    results['summary']['code_prefixes'].get(prefix, 0) + 1
        else:
            results['invalid'] += 1
            
            # Track common errors
            if validation_result.get('error_message'):
                error = validation_result['error_message']
                results['summary']['common_errors'][error] = \
                    results['summary']['common_errors'].get(error, 0) + 1
        
        # Track code lengths
        code_length = len(str(code).strip())
        results['summary']['code_lengths'][code_length] = \
            results['summary']['code_lengths'].get(code_length, 0) + 1
        
        # Track warnings
        if validation_result.get('warnings'):
            results['warnings'] += 1
            for warning in validation_result['warnings']:
                results['summary']['common_warnings'][warning] = \
                    results['summary']['common_warnings'].get(warning, 0) + 1
    
    # Display results
    print(f"\n=== TNVED Code Validation Results ===")
    print(f"Total codes: {results['total']}")
    print(f"Valid codes: {results['valid']}")
    print(f"Invalid codes: {results['invalid']}")
    print(f"Codes with warnings: {results['warnings']}")
    
    # Show code length distribution
    if results['summary']['code_lengths']:
        print(f"\n=== Code Length Distribution ===")
        for length, count in sorted(results['summary']['code_lengths'].items()):
            print(f"  {length} digits: {count}")
    
    # Show common prefixes
    if results['summary']['code_prefixes']:
        print(f"\n=== Top Code Prefixes ===")
        sorted_prefixes = sorted(results['summary']['code_prefixes'].items(), 
                               key=lambda x: x[1], reverse=True)
        for prefix, count in sorted_prefixes[:10]:  # Show top 10
            print(f"  {prefix}: {count}")
    
    # Show common errors
    if results['summary']['common_errors']:
        print(f"\n=== Common Errors ===")
        for error, count in results['summary']['common_errors'].items():
            print(f"  {error}: {count}")
    
    # Show detailed results if requested
    if args.verbose:
        print(f"\n=== Detailed Results ===")
        for i, result in enumerate(results['results'], 1):
            status = "✓" if result['is_valid'] else "✗"
            print(f"{i:3d}. {status} {result['code']}")
            
            if result.get('normalized_code') and result['code'] != result.get('normalized_code'):
                print(f"     Normalized: {result['normalized_code']}")
            if result.get('error_message'):
                print(f"     Error: {result['error_message']}")
            if result.get('warnings'):
                for warning in result['warnings']:
                    print(f"     Warning: {warning}")
    
    # Export results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResults exported to: {args.output}")
    
    return 0


def main():
    """Main command-line interface"""
    parser = argparse.ArgumentParser(
        description="URL Data Validation Tool for TNVED Code Matching System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate URL data file
  python validate_url_data.py validate-file data.xlsx
  
  # Validate URL data file and export detailed report
  python validate_url_data.py validate-file data.xlsx -o report.xlsx
  
  # Validate URL database
  python validate_url_data.py validate-database
  
  # Validate specific URLs
  python validate_url_data.py validate-urls "https://ozon.ru/product/123" "https://market.yandex.ru/product/456"
  
  # Validate URLs from file
  python validate_url_data.py validate-urls --urls-file urls.txt -v
  
  # Validate TNVED codes
  python validate_url_data.py validate-codes "0901110000" "1234567890"
  
  # Validate TNVED codes from file
  python validate_url_data.py validate-codes --codes-file codes.txt -v
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate file command
    file_parser = subparsers.add_parser('validate-file', help='Validate URL data file')
    file_parser.add_argument('file', help='Path to Excel file with URL data')
    file_parser.add_argument('-o', '--output', help='Output file for detailed report (.xlsx or .json)')
    file_parser.set_defaults(func=validate_file_command)
    
    # Validate database command
    db_parser = subparsers.add_parser('validate-database', help='Validate URL database')
    db_parser.add_argument('-o', '--output', help='Output file for detailed report (.xlsx or .json)')
    db_parser.set_defaults(func=validate_database_command)
    
    # Validate URLs command
    urls_parser = subparsers.add_parser('validate-urls', help='Validate list of URLs')
    urls_group = urls_parser.add_mutually_exclusive_group(required=True)
    urls_group.add_argument('urls', nargs='*', help='URLs to validate')
    urls_group.add_argument('--urls-file', help='File containing URLs (one per line)')
    urls_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed results')
    urls_parser.add_argument('-o', '--output', help='Output file for results (.json)')
    urls_parser.set_defaults(func=validate_urls_command)
    
    # Validate TNVED codes command
    codes_parser = subparsers.add_parser('validate-codes', help='Validate list of TNVED codes')
    codes_group = codes_parser.add_mutually_exclusive_group(required=True)
    codes_group.add_argument('codes', nargs='*', help='TNVED codes to validate')
    codes_group.add_argument('--codes-file', help='File containing TNVED codes (one per line)')
    codes_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed results')
    codes_parser.add_argument('-o', '--output', help='Output file for results (.json)')
    codes_parser.set_defaults(func=validate_tnved_codes_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())