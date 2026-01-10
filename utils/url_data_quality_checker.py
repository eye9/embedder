#!/usr/bin/env python3
"""
URL Data Quality Checker for TNVED Code Matching System

This module provides simplified validation utilities for URL data,
TNVED codes, and data quality reporting for URL databases.
"""

import logging
import re
import pandas as pd
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json

from services.url_normalizer import URLNormalizer
from utils.tnved_validator import validate_tnved_code, is_valid_tnved_code


logger = logging.getLogger(__name__)


class URLDataQualityChecker:
    """
    Simplified URL data quality checker
    
    Provides validation and quality reporting for URL data files
    and databases used in the TNVED code matching system.
    """
    
    def __init__(self):
        """Initialize the quality checker"""
        self.url_normalizer = URLNormalizer()
        self.supported_schemes = {'http', 'https'}
        
        # Patterns for suspicious URLs
        self.suspicious_patterns = [
            r'localhost',
            r'127\.0\.0\.1',
            r'192\.168\.',
            r'10\.',
            r'172\.(1[6-9]|2[0-9]|3[01])\.',
            r'file://',
            r'ftp://',
            r'javascript:',
            r'data:',
        ]
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Validates a single URL
        
        Args:
            url: URL to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'url': str(url) if url else "",
            'is_valid': False,
            'normalized_url': None,
            'shop_type': None,
            'product_id': None,
            'error_message': None,
            'warnings': []
        }
        
        if not url or not isinstance(url, str):
            result['error_message'] = "URL is empty or not a string"
            return result
        
        url = url.strip()
        if not url:
            result['error_message'] = "URL is empty after stripping whitespace"
            return result
        
        result['url'] = url
        
        try:
            # Basic URL parsing
            parsed = urlparse(url)
            
            # Check for scheme
            if not parsed.scheme:
                # Try adding https and re-parse
                test_url = 'https://' + url
                test_parsed = urlparse(test_url)
                if test_parsed.netloc:
                    parsed = test_parsed
                    result['warnings'].append("URL missing scheme, assumed HTTPS")
                else:
                    result['error_message'] = "URL has no valid scheme or domain"
                    return result
            
            # Validate scheme
            if parsed.scheme.lower() not in self.supported_schemes:
                result['error_message'] = f"Unsupported URL scheme: {parsed.scheme}"
                return result
            
            # Check for domain
            if not parsed.netloc:
                result['error_message'] = "URL has no domain"
                return result
            
            # Check for suspicious patterns
            full_url = parsed.geturl()
            for pattern in self.suspicious_patterns:
                if re.search(pattern, full_url, re.IGNORECASE):
                    result['warnings'].append(f"Suspicious URL pattern detected: {pattern}")
            
            # Try to normalize URL
            normalized = self.url_normalizer.normalize_url(url)
            if normalized:
                result['normalized_url'] = normalized.normalized_url
                result['shop_type'] = normalized.shop_type
                result['product_id'] = normalized.product_id
                result['is_valid'] = True
                
                # Check if normalization changed the URL significantly
                if normalized.original_url != normalized.normalized_url:
                    result['warnings'].append("URL was normalized for consistency")
            else:
                result['error_message'] = "URL could not be normalized"
                return result
            
            return result
            
        except Exception as e:
            result['error_message'] = f"URL parsing error: {str(e)}"
            return result
    
    def validate_tnved_code(self, code: str) -> Dict[str, Any]:
        """
        Validates a single TNVED code
        
        Args:
            code: TNVED code to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'code': str(code) if code else "",
            'is_valid': False,
            'normalized_code': None,
            'error_message': None,
            'warnings': []
        }
        
        if not code or not isinstance(code, str):
            result['error_message'] = "TNVED code is empty or not a string"
            return result
        
        code = code.strip()
        result['code'] = code
        
        try:
            # Use existing TNVED validator
            normalized_code = validate_tnved_code(code, strict=False)
            result['normalized_code'] = normalized_code
            result['is_valid'] = True
            
            # Add warnings for common issues
            if len(code) < 10:
                result['warnings'].append(f"Code padded from {len(code)} to 10 digits")
            
            if code != normalized_code:
                result['warnings'].append("Code was normalized")
            
            # Check for suspicious patterns
            if normalized_code.startswith('00'):
                result['warnings'].append("Code starts with '00' which may be invalid")
            
            return result
            
        except Exception as e:
            result['error_message'] = str(e)
            return result
    
    def analyze_excel_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyzes data quality of an Excel file containing URL data
        
        Args:
            file_path: Path to Excel file with URL, Code, Description columns
            
        Returns:
            Dictionary with comprehensive analysis results
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = ['URL', 'Code', 'Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f"Missing required columns: {missing_columns}",
                    'file_path': file_path
                }
            
            return self._analyze_dataframe(df, file_path)
            
        except Exception as e:
            logger.error(f"Error analyzing Excel file: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def _analyze_dataframe(self, df: pd.DataFrame, source_path: str = None) -> Dict[str, Any]:
        """Analyzes DataFrame and generates quality report"""
        total_records = len(df)
        
        # Initialize counters
        valid_urls = 0
        invalid_urls = 0
        valid_tnved_codes = 0
        invalid_tnved_codes = 0
        missing_descriptions = 0
        duplicate_urls = 0
        
        url_issues = []
        tnved_issues = []
        shop_type_distribution = {}
        domain_distribution = {}
        
        # Analyze URLs
        print(f"Analyzing {total_records} records...")
        
        for index, row in df.iterrows():
            # Validate URL
            url = str(row['URL']).strip() if pd.notna(row['URL']) else ""
            if url:
                url_result = self.validate_url(url)
                if url_result['is_valid']:
                    valid_urls += 1
                    
                    # Track shop types
                    if url_result['shop_type']:
                        shop_type = url_result['shop_type']
                        shop_type_distribution[shop_type] = shop_type_distribution.get(shop_type, 0) + 1
                    
                    # Track domains
                    try:
                        domain = urlparse(url).netloc
                        domain_distribution[domain] = domain_distribution.get(domain, 0) + 1
                    except:
                        pass
                else:
                    invalid_urls += 1
                    if len(url_issues) < 100:  # Limit to first 100 issues
                        url_issues.append({
                            'row': index + 1,
                            'url': url,
                            'error': url_result['error_message'],
                            'warnings': url_result['warnings']
                        })
            else:
                invalid_urls += 1
                if len(url_issues) < 100:
                    url_issues.append({
                        'row': index + 1,
                        'url': url,
                        'error': 'Empty URL',
                        'warnings': []
                    })
            
            # Validate TNVED code
            code = str(row['Code']).strip() if pd.notna(row['Code']) else ""
            if code:
                tnved_result = self.validate_tnved_code(code)
                if tnved_result['is_valid']:
                    valid_tnved_codes += 1
                else:
                    invalid_tnved_codes += 1
                    if len(tnved_issues) < 100:  # Limit to first 100 issues
                        tnved_issues.append({
                            'row': index + 1,
                            'code': code,
                            'error': tnved_result['error_message'],
                            'warnings': tnved_result['warnings']
                        })
            else:
                invalid_tnved_codes += 1
                if len(tnved_issues) < 100:
                    tnved_issues.append({
                        'row': index + 1,
                        'code': code,
                        'error': 'Empty TNVED code',
                        'warnings': []
                    })
            
            # Check for missing descriptions
            description = str(row['Description']).strip() if pd.notna(row['Description']) else ""
            if not description:
                missing_descriptions += 1
        
        # Find duplicate URLs
        url_series = df['URL'].fillna('').astype(str)
        duplicate_urls = url_series.duplicated().sum()
        
        # Calculate quality scores
        url_quality_score = (valid_urls / total_records) * 100 if total_records > 0 else 0
        tnved_quality_score = (valid_tnved_codes / total_records) * 100 if total_records > 0 else 0
        
        # Calculate overall quality score with penalties
        duplicate_penalty = (duplicate_urls / total_records) * 10 if total_records > 0 else 0
        missing_desc_penalty = (missing_descriptions / total_records) * 5 if total_records > 0 else 0
        overall_quality_score = max(0, (url_quality_score + tnved_quality_score) / 2 - duplicate_penalty - missing_desc_penalty)
        
        # Generate recommendations
        recommendations = []
        
        if url_quality_score < 90:
            recommendations.append(f"URL quality is {url_quality_score:.1f}%. Consider reviewing and fixing invalid URLs.")
        
        if tnved_quality_score < 95:
            recommendations.append(f"TNVED code quality is {tnved_quality_score:.1f}%. Review and fix invalid codes.")
        
        if duplicate_urls > 0:
            duplicate_rate = (duplicate_urls / total_records) * 100
            recommendations.append(f"Found {duplicate_urls} duplicate URLs ({duplicate_rate:.1f}%). Consider deduplication.")
        
        if missing_descriptions > 0:
            missing_rate = (missing_descriptions / total_records) * 100
            recommendations.append(f"Found {missing_descriptions} missing descriptions ({missing_rate:.1f}%). Descriptions are important for fallback semantic search.")
        
        return {
            'success': True,
            'source_path': source_path,
            'analysis': {
                'total_records': total_records,
                'valid_urls': valid_urls,
                'invalid_urls': invalid_urls,
                'valid_tnved_codes': valid_tnved_codes,
                'invalid_tnved_codes': invalid_tnved_codes,
                'duplicate_urls': duplicate_urls,
                'missing_descriptions': missing_descriptions,
                'url_quality_score': round(url_quality_score, 2),
                'tnved_quality_score': round(tnved_quality_score, 2),
                'overall_quality_score': round(overall_quality_score, 2),
                'shop_type_distribution': shop_type_distribution,
                'domain_distribution': domain_distribution,
                'url_issues': url_issues,
                'tnved_issues': tnved_issues,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
        }
    
    def export_report_to_json(self, report: Dict[str, Any], output_path: str) -> bool:
        """
        Exports analysis report to JSON file
        
        Args:
            report: Analysis report dictionary
            output_path: Path for output JSON file
            
        Returns:
            True if export successful
        """
        try:
            # Convert numpy/pandas types to native Python types for JSON serialization
            def convert_types(obj):
                if hasattr(obj, 'item'):  # numpy/pandas scalar
                    return obj.item()
                elif isinstance(obj, dict):
                    return {k: convert_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_types(v) for v in obj]
                else:
                    return obj
            
            json_compatible_report = convert_types(report)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_compatible_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Analysis report exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting report to JSON: {e}")
            return False
    
    def export_report_to_excel(self, report: Dict[str, Any], output_path: str) -> bool:
        """
        Exports analysis report to Excel file
        
        Args:
            report: Analysis report dictionary
            output_path: Path for output Excel file
            
        Returns:
            True if export successful
        """
        try:
            if not report.get('success', False):
                return False
            
            analysis = report['analysis']
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Records',
                        'Valid URLs',
                        'Invalid URLs',
                        'Valid TNVED Codes',
                        'Invalid TNVED Codes',
                        'Duplicate URLs',
                        'Missing Descriptions',
                        'URL Quality Score (%)',
                        'TNVED Quality Score (%)',
                        'Overall Quality Score (%)'
                    ],
                    'Value': [
                        analysis['total_records'],
                        analysis['valid_urls'],
                        analysis['invalid_urls'],
                        analysis['valid_tnved_codes'],
                        analysis['invalid_tnved_codes'],
                        analysis['duplicate_urls'],
                        analysis['missing_descriptions'],
                        analysis['url_quality_score'],
                        analysis['tnved_quality_score'],
                        analysis['overall_quality_score']
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # URL issues sheet
                if analysis['url_issues']:
                    pd.DataFrame(analysis['url_issues']).to_excel(
                        writer, sheet_name='URL Issues', index=False
                    )
                
                # TNVED issues sheet
                if analysis['tnved_issues']:
                    pd.DataFrame(analysis['tnved_issues']).to_excel(
                        writer, sheet_name='TNVED Issues', index=False
                    )
                
                # Distributions sheet
                distributions_data = []
                
                for shop_type, count in analysis['shop_type_distribution'].items():
                    distributions_data.append({
                        'Type': 'Shop Type',
                        'Value': shop_type,
                        'Count': count
                    })
                
                for domain, count in analysis['domain_distribution'].items():
                    distributions_data.append({
                        'Type': 'Domain',
                        'Value': domain,
                        'Count': count
                    })
                
                if distributions_data:
                    pd.DataFrame(distributions_data).to_excel(
                        writer, sheet_name='Distributions', index=False
                    )
                
                # Recommendations sheet
                if analysis['recommendations']:
                    recommendations_data = {
                        'Recommendation': analysis['recommendations']
                    }
                    pd.DataFrame(recommendations_data).to_excel(
                        writer, sheet_name='Recommendations', index=False
                    )
            
            logger.info(f"Analysis report exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting report to Excel: {e}")
            return False


def validate_url_data_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to validate a URL data file
    
    Args:
        file_path: Path to Excel file with URL data
        
    Returns:
        Dictionary with validation results and quality report
    """
    checker = URLDataQualityChecker()
    return checker.analyze_excel_file(file_path)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = validate_url_data_file(file_path)
        
        if result["success"]:
            analysis = result['analysis']
            print(f"Validation completed for {file_path}")
            print(f"Total records: {analysis['total_records']}")
            print(f"URL quality: {analysis['url_quality_score']:.1f}%")
            print(f"TNVED quality: {analysis['tnved_quality_score']:.1f}%")
            print(f"Overall quality: {analysis['overall_quality_score']:.1f}%")
            
            if analysis['recommendations']:
                print("\nRecommendations:")
                for i, rec in enumerate(analysis['recommendations'], 1):
                    print(f"{i}. {rec}")
        else:
            print(f"Validation failed: {result['error']}")
    else:
        print("Usage: python url_data_quality_checker.py <excel_file_path>")