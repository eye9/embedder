#!/usr/bin/env python3
"""
URL Data Quality Validation Command-Line Tool

This script provides a simple command-line interface for validating
URL data files and generating quality reports.
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.url_data_quality_checker import URLDataQualityChecker, validate_url_data_file


def main():
    """Main command-line interface"""
    parser = argparse.ArgumentParser(
        description="URL Data Quality Validation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate URL data file
  python validate_url_quality.py data.xlsx
  
  # Validate and export detailed report to Excel
  python validate_url_quality.py data.xlsx -o report.xlsx
  
  # Validate and export detailed report to JSON
  python validate_url_quality.py data.xlsx -o report.json
  
  # Show verbose output
  python validate_url_quality.py data.xlsx -v
        """
    )
    
    parser.add_argument('file', help='Path to Excel file with URL data (URL, Code, Description columns)')
    parser.add_argument('-o', '--output', help='Output file for detailed report (.xlsx or .json)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed validation issues')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return 1
    
    print(f"Validating URL data file: {args.file}")
    
    # Validate the file
    result = validate_url_data_file(args.file)
    
    if not result["success"]:
        print(f"Validation failed: {result['error']}")
        return 1
    
    # Display summary
    analysis = result["analysis"]
    print(f"\n=== Validation Summary ===")
    print(f"Total records: {analysis['total_records']}")
    print(f"Valid URLs: {analysis['valid_urls']} ({analysis['url_quality_score']:.1f}%)")
    print(f"Invalid URLs: {analysis['invalid_urls']}")
    print(f"Valid TNVED codes: {analysis['valid_tnved_codes']} ({analysis['tnved_quality_score']:.1f}%)")
    print(f"Invalid TNVED codes: {analysis['invalid_tnved_codes']}")
    print(f"Duplicate URLs: {analysis['duplicate_urls']}")
    print(f"Missing descriptions: {analysis['missing_descriptions']}")
    print(f"Overall quality score: {analysis['overall_quality_score']:.1f}%")
    
    # Show shop type distribution
    if analysis['shop_type_distribution']:
        print(f"\n=== Shop Type Distribution ===")
        for shop_type, count in sorted(analysis['shop_type_distribution'].items()):
            print(f"  {shop_type}: {count}")
    
    # Show top domains
    if analysis['domain_distribution']:
        print(f"\n=== Top Domains ===")
        sorted_domains = sorted(analysis['domain_distribution'].items(), 
                              key=lambda x: x[1], reverse=True)
        for domain, count in sorted_domains[:10]:  # Show top 10
            print(f"  {domain}: {count}")
    
    # Show recommendations
    if analysis['recommendations']:
        print(f"\n=== Recommendations ===")
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"{i}. {rec}")
    
    # Show detailed issues if verbose
    if args.verbose:
        if analysis['url_issues']:
            print(f"\n=== URL Issues (showing first 20) ===")
            for issue in analysis['url_issues'][:20]:
                print(f"Row {issue['row']}: {issue['url']}")
                print(f"  Error: {issue['error']}")
                if issue['warnings']:
                    print(f"  Warnings: {', '.join(issue['warnings'])}")
        
        if analysis['tnved_issues']:
            print(f"\n=== TNVED Code Issues (showing first 20) ===")
            for issue in analysis['tnved_issues'][:20]:
                print(f"Row {issue['row']}: {issue['code']}")
                print(f"  Error: {issue['error']}")
                if issue['warnings']:
                    print(f"  Warnings: {', '.join(issue['warnings'])}")
    
    # Export detailed report if requested
    if args.output:
        checker = URLDataQualityChecker()
        
        if args.output.endswith('.xlsx'):
            success = checker.export_report_to_excel(result, args.output)
            if success:
                print(f"\nDetailed report exported to: {args.output}")
            else:
                print(f"\nError exporting report to: {args.output}")
                return 1
        elif args.output.endswith('.json'):
            success = checker.export_report_to_json(result, args.output)
            if success:
                print(f"\nDetailed report exported to: {args.output}")
            else:
                print(f"\nError exporting report to: {args.output}")
                return 1
        else:
            print(f"\nError: Unsupported output format. Use .xlsx or .json extension.")
            return 1
    
    # Determine exit code based on quality
    if analysis['overall_quality_score'] < 80:
        print(f"\nWarning: Overall quality score is below 80%. Consider reviewing and fixing issues.")
        return 2  # Warning exit code
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)