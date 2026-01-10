"""
URL Data Validation Tools for TNVED Code Matching System

This module provides comprehensive validation utilities for URL data,
TNVED codes, and data quality reporting for URL databases.
"""

import logging
import re
import pandas as pd
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from services.url_normalizer import URLNormalizer
from utils.tnved_validator import validate_tnved_code, is_valid_tnved_code


logger = logging.getLogger(__name__)


@dataclass
class URLValidationResult:
    """Result of URL validation"""
    url: str
    is_valid: bool
    normalized_url: Optional[str] = None
    shop_type: Optional[str] = None
    product_id: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class TNVEDValidationResult:
    """Result of TNVED code validation"""
    code: str
    is_valid: bool
    normalized_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class DataQualityReport:
    """Comprehensive data quality report for URL database"""
    total_records: int
    valid_urls: int
    invalid_urls: int
    valid_tnved_codes: int
    invalid_tnved_codes: int
    duplicate_urls: int
    missing_descriptions: int
    url_validation_issues: List[Dict[str, Any]]
    tnved_validation_issues: List[Dict[str, Any]]
    shop_type_distribution: Dict[str, int]
    domain_distribution: Dict[str, int]
    source_distribution: Dict[str, int]
    recommendations: List[str]
    generated_at: str
    
    def get_url_quality_score(self) -> float:
        """Calculate URL quality score (0-100)"""
        if self.total_records == 0:
            return 0.0
        return (self.valid_urls / self.total_records) * 100
    
    def get_tnved_quality_score(self) -> float:
        """Calculate TNVED code quality score (0-100)"""
        if self.total_records == 0:
            return 0.0
        return (self.valid_tnved_codes / self.total_records) * 100
    
    def get_overall_quality_score(self) -> float:
        """Calculate overall data quality score (0-100)"""
        url_score = self.get_url_quality_score()
        tnved_score = self.get_tnved_quality_score()
        duplicate_penalty = (self.duplicate_urls / self.total_records) * 10 if self.total_records > 0 else 0
        missing_desc_penalty = (self.missing_descriptions / self.total_records) * 5 if self.total_records > 0 else 0
        
        return max(0, (url_score + tnved_score) / 2 - duplicate_penalty - missing_desc_penalty)


class URLFormatValidator:
    """Validates URL formats and provides detailed validation results"""
    
    def __init__(self):
        self.normalizer = URLNormalizer()
        self.supported_schemes = {'http', 'https'}
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
    
    def validate_url(self, url: str) -> URLValidationResult:
        """
        Comprehensive URL validation
        
        Args:
            url: URL to validate
            
        Returns:
            URLValidationResult with detailed validation information
        """
        if not url or not isinstance(url, str):
            return URLValidationResult(
                url=str(url) if url else "",
                is_valid=False,
                error_message="URL is empty or not a string"
            )
        
        url = url.strip()
        if not url:
            return URLValidationResult(
                url="",
                is_valid=False,
                error_message="URL is empty after stripping whitespace"
            )
        
        result = URLValidationResult(url=url, is_valid=False)
        
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
                    result.warnings.append("URL missing scheme, assumed HTTPS")
                else:
                    result.error_message = "URL has no valid scheme or domain"
                    return result
            
            # Validate scheme
            if parsed.scheme.lower() not in self.supported_schemes:
                result.error_message = f"Unsupported URL scheme: {parsed.scheme}"
                return result
            
            # Check for domain
            if not parsed.netloc:
                result.error_message = "URL has no domain"
                return result
            
            # Check for suspicious patterns
            full_url = parsed.geturl()
            for pattern in self.suspicious_patterns:
                if re.search(pattern, full_url, re.IGNORECASE):
                    result.warnings.append(f"Suspicious URL pattern detected: {pattern}")
            
            # Try to normalize URL
            normalized = self.normalizer.normalize_url(url)
            if normalized:
                result.normalized_url = normalized.normalized_url
                result.shop_type = normalized.shop_type
                result.product_id = normalized.product_id
                result.is_valid = True
                
                # Check if normalization changed the URL significantly
                if normalized.original_url != normalized.normalized_url:
                    result.warnings.append("URL was normalized for consistency")
            else:
                result.error_message = "URL could not be normalized"
                return result
            
            # Additional validation checks
            self._validate_domain_format(parsed.netloc, result)
            self._validate_path_format(parsed.path, result)
            
            return result
            
        except Exception as e:
            result.error_message = f"URL parsing error: {str(e)}"
            return result
    
    def _validate_domain_format(self, domain: str, result: URLValidationResult):
        """Validates domain format and adds warnings if needed"""
        # Check for valid domain format
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            result.warnings.append("Domain format may be invalid")
        
        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf']
        for tld in suspicious_tlds:
            if domain.lower().endswith(tld):
                result.warnings.append(f"Suspicious TLD detected: {tld}")
    
    def _validate_path_format(self, path: str, result: URLValidationResult):
        """Validates URL path format and adds warnings if needed"""
        # Check for suspicious path patterns
        suspicious_path_patterns = [
            r'/admin',
            r'/wp-admin',
            r'/phpmyadmin',
            r'\.php$',
            r'\.asp$',
            r'\.jsp$'
        ]
        
        for pattern in suspicious_path_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                result.warnings.append(f"Suspicious path pattern: {pattern}")
    
    def validate_urls_batch(self, urls: List[str]) -> Dict[str, Any]:
        """
        Validates a batch of URLs
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            "total": len(urls),
            "valid": 0,
            "invalid": 0,
            "warnings": 0,
            "results": [],
            "summary": {
                "common_errors": {},
                "common_warnings": {},
                "shop_types": {},
                "domains": {}
            }
        }
        
        for url in urls:
            validation_result = self.validate_url(url)
            results["results"].append(validation_result)
            
            if validation_result.is_valid:
                results["valid"] += 1
                
                # Track shop types
                if validation_result.shop_type:
                    shop_type = validation_result.shop_type
                    results["summary"]["shop_types"][shop_type] = \
                        results["summary"]["shop_types"].get(shop_type, 0) + 1
                
                # Track domains
                try:
                    domain = urlparse(url).netloc
                    results["summary"]["domains"][domain] = \
                        results["summary"]["domains"].get(domain, 0) + 1
                except:
                    pass
            else:
                results["invalid"] += 1
                
                # Track common errors
                if validation_result.error_message:
                    error = validation_result.error_message
                    results["summary"]["common_errors"][error] = \
                        results["summary"]["common_errors"].get(error, 0) + 1
            
            # Track warnings
            if validation_result.warnings:
                results["warnings"] += 1
                for warning in validation_result.warnings:
                    results["summary"]["common_warnings"][warning] = \
                        results["summary"]["common_warnings"].get(warning, 0) + 1
        
        return results


class TNVEDFormatValidator:
    """Validates TNVED code formats for URL data"""
    
    def validate_tnved_code(self, code: str) -> TNVEDValidationResult:
        """
        Validates TNVED code format
        
        Args:
            code: TNVED code to validate
            
        Returns:
            TNVEDValidationResult with validation details
        """
        if not code or not isinstance(code, str):
            return TNVEDValidationResult(
                code=str(code) if code else "",
                is_valid=False,
                error_message="TNVED code is empty or not a string"
            )
        
        code = code.strip()
        result = TNVEDValidationResult(code=code, is_valid=False)
        
        try:
            # Use existing TNVED validator
            normalized_code = validate_tnved_code(code, strict=False)
            result.normalized_code = normalized_code
            result.is_valid = True
            
            # Add warnings for common issues
            if len(code) < 10:
                result.warnings.append(f"Code padded from {len(code)} to 10 digits")
            
            if code != normalized_code:
                result.warnings.append("Code was normalized")
            
            # Check for suspicious patterns
            if normalized_code.startswith('00'):
                result.warnings.append("Code starts with '00' which may be invalid")
            
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def validate_tnved_codes_batch(self, codes: List[str]) -> Dict[str, Any]:
        """
        Validates a batch of TNVED codes
        
        Args:
            codes: List of TNVED codes to validate
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            "total": len(codes),
            "valid": 0,
            "invalid": 0,
            "warnings": 0,
            "results": [],
            "summary": {
                "common_errors": {},
                "common_warnings": {},
                "code_lengths": {},
                "code_prefixes": {}
            }
        }
        
        for code in codes:
            validation_result = self.validate_tnved_code(code)
            results["results"].append(validation_result)
            
            if validation_result.is_valid:
                results["valid"] += 1
                
                # Track code prefixes (first 4 digits)
                if validation_result.normalized_code:
                    prefix = validation_result.normalized_code[:4]
                    results["summary"]["code_prefixes"][prefix] = \
                        results["summary"]["code_prefixes"].get(prefix, 0) + 1
            else:
                results["invalid"] += 1
                
                # Track common errors
                if validation_result.error_message:
                    error = validation_result.error_message
                    results["summary"]["common_errors"][error] = \
                        results["summary"]["common_errors"].get(error, 0) + 1
            
            # Track code lengths
            code_length = len(str(code).strip())
            results["summary"]["code_lengths"][code_length] = \
                results["summary"]["code_lengths"].get(code_length, 0) + 1
            
            # Track warnings
            if validation_result.warnings:
                results["warnings"] += 1
                for warning in validation_result.warnings:
                    results["summary"]["common_warnings"][warning] = \
                        results["summary"]["common_warnings"].get(warning, 0) + 1
        
        return results


class URLDataQualityAnalyzer:
    """Analyzes data quality for URL databases"""
    
    def __init__(self):
        self.url_validator = URLFormatValidator()
        self.tnved_validator = TNVEDFormatValidator()
    
    def analyze_excel_file(self, file_path: str) -> DataQualityReport:
        """
        Analyzes data quality of an Excel file containing URL data
        
        Args:
            file_path: Path to Excel file with URL, Code, Description columns
            
        Returns:
            DataQualityReport with comprehensive analysis
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = ['URL', 'Code', 'Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            return self._analyze_dataframe(df)
            
        except Exception as e:
            logger.error(f"Error analyzing Excel file: {e}")
            return self._create_empty_report(error=str(e))
    
    def analyze_url_database(self, url_db_manager) -> DataQualityReport:
        """
        Analyzes data quality of URL database
        
        Args:
            url_db_manager: URLDatabaseManager instance
            
        Returns:
            DataQualityReport with comprehensive analysis
        """
        try:
            # Get all records from database
            all_records = url_db_manager.collection.get(
                include=["documents", "metadatas"]
            )
            
            if not all_records['ids']:
                return self._create_empty_report()
            
            # Convert to DataFrame for analysis
            data = []
            for i, record_id in enumerate(all_records['ids']):
                metadata = all_records['metadatas'][i]
                description = all_records['documents'][i]
                
                data.append({
                    'URL': metadata.get('original_url', ''),
                    'Code': metadata.get('tnved_code', ''),
                    'Description': description,
                    'Source': metadata.get('source_name', ''),
                    'Domain': metadata.get('domain', ''),
                    'Shop_Type': metadata.get('shop_type', '')
                })
            
            df = pd.DataFrame(data)
            return self._analyze_dataframe(df)
            
        except Exception as e:
            logger.error(f"Error analyzing URL database: {e}")
            return self._create_empty_report(error=str(e))
    
    def _analyze_dataframe(self, df: pd.DataFrame) -> DataQualityReport:
        """Analyzes DataFrame and generates quality report"""
        total_records = len(df)
        
        # Initialize counters
        valid_urls = 0
        invalid_urls = 0
        valid_tnved_codes = 0
        invalid_tnved_codes = 0
        missing_descriptions = 0
        url_validation_issues = []
        tnved_validation_issues = []
        
        # Analyze URLs
        urls = df['URL'].fillna('').astype(str).tolist()
        url_results = self.url_validator.validate_urls_batch(urls)
        
        for i, result in enumerate(url_results['results']):
            if result.is_valid:
                valid_urls += 1
            else:
                invalid_urls += 1
                url_validation_issues.append({
                    'row': i + 1,
                    'url': result.url,
                    'error': result.error_message,
                    'warnings': result.warnings
                })
        
        # Analyze TNVED codes
        codes = df['Code'].fillna('').astype(str).tolist()
        tnved_results = self.tnved_validator.validate_tnved_codes_batch(codes)
        
        for i, result in enumerate(tnved_results['results']):
            if result.is_valid:
                valid_tnved_codes += 1
            else:
                invalid_tnved_codes += 1
                tnved_validation_issues.append({
                    'row': i + 1,
                    'code': result.code,
                    'error': result.error_message,
                    'warnings': result.warnings
                })
        
        # Count missing descriptions
        missing_descriptions = df['Description'].isna().sum() + \
                             (df['Description'].astype(str).str.strip() == '').sum()
        
        # Find duplicate URLs
        duplicate_urls = df['URL'].duplicated().sum()
        
        # Generate distributions
        shop_type_distribution = {}
        domain_distribution = {}
        source_distribution = {}
        
        if 'Shop_Type' in df.columns:
            shop_type_distribution = df['Shop_Type'].value_counts().to_dict()
        
        if 'Domain' in df.columns:
            domain_distribution = df['Domain'].value_counts().to_dict()
        
        if 'Source' in df.columns:
            source_distribution = df['Source'].value_counts().to_dict()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            total_records, valid_urls, invalid_urls, valid_tnved_codes, 
            invalid_tnved_codes, duplicate_urls, missing_descriptions,
            url_validation_issues, tnved_validation_issues
        )
        
        return DataQualityReport(
            total_records=total_records,
            valid_urls=valid_urls,
            invalid_urls=invalid_urls,
            valid_tnved_codes=valid_tnved_codes,
            invalid_tnved_codes=invalid_tnved_codes,
            duplicate_urls=duplicate_urls,
            missing_descriptions=missing_descriptions,
            url_validation_issues=url_validation_issues[:100],  # Limit to first 100
            tnved_validation_issues=tnved_validation_issues[:100],  # Limit to first 100
            shop_type_distribution=shop_type_distribution,
            domain_distribution=domain_distribution,
            source_distribution=source_distribution,
            recommendations=recommendations,
            generated_at=datetime.now().isoformat()
        )
    
    def _generate_recommendations(
        self, total_records: int, valid_urls: int, invalid_urls: int,
        valid_tnved_codes: int, invalid_tnved_codes: int, duplicate_urls: int,
        missing_descriptions: int, url_issues: List, tnved_issues: List
    ) -> List[str]:
        """Generates recommendations based on analysis results"""
        recommendations = []
        
        # URL quality recommendations
        url_quality = (valid_urls / total_records) * 100 if total_records > 0 else 0
        if url_quality < 90:
            recommendations.append(
                f"URL quality is {url_quality:.1f}%. Consider reviewing and fixing invalid URLs."
            )
        
        # TNVED code quality recommendations
        tnved_quality = (valid_tnved_codes / total_records) * 100 if total_records > 0 else 0
        if tnved_quality < 95:
            recommendations.append(
                f"TNVED code quality is {tnved_quality:.1f}%. Review and fix invalid codes."
            )
        
        # Duplicate URL recommendations
        if duplicate_urls > 0:
            duplicate_rate = (duplicate_urls / total_records) * 100
            recommendations.append(
                f"Found {duplicate_urls} duplicate URLs ({duplicate_rate:.1f}%). "
                "Consider deduplication to improve data quality."
            )
        
        # Missing description recommendations
        if missing_descriptions > 0:
            missing_rate = (missing_descriptions / total_records) * 100
            recommendations.append(
                f"Found {missing_descriptions} missing descriptions ({missing_rate:.1f}%). "
                "Descriptions are important for fallback semantic search."
            )
        
        # Specific issue recommendations
        if url_issues:
            common_url_errors = {}
            for issue in url_issues:
                error = issue.get('error', 'Unknown error')
                common_url_errors[error] = common_url_errors.get(error, 0) + 1
            
            most_common_error = max(common_url_errors.items(), key=lambda x: x[1])
            recommendations.append(
                f"Most common URL error: '{most_common_error[0]}' "
                f"({most_common_error[1]} occurrences)"
            )
        
        if tnved_issues:
            common_tnved_errors = {}
            for issue in tnved_issues:
                error = issue.get('error', 'Unknown error')
                common_tnved_errors[error] = common_tnved_errors.get(error, 0) + 1
            
            most_common_error = max(common_tnved_errors.items(), key=lambda x: x[1])
            recommendations.append(
                f"Most common TNVED error: '{most_common_error[0]}' "
                f"({most_common_error[1]} occurrences)"
            )
        
        return recommendations
    
    def _create_empty_report(self, error: str = None) -> DataQualityReport:
        """Creates an empty quality report"""
        return DataQualityReport(
            total_records=0,
            valid_urls=0,
            invalid_urls=0,
            valid_tnved_codes=0,
            invalid_tnved_codes=0,
            duplicate_urls=0,
            missing_descriptions=0,
            url_validation_issues=[],
            tnved_validation_issues=[],
            shop_type_distribution={},
            domain_distribution={},
            source_distribution={},
            recommendations=[f"Error: {error}"] if error else [],
            generated_at=datetime.now().isoformat()
        )
    
    def export_report_to_excel(self, report: DataQualityReport, output_path: str) -> bool:
        """
        Exports data quality report to Excel file
        
        Args:
            report: DataQualityReport to export
            output_path: Path for output Excel file
            
        Returns:
            True if export successful
        """
        try:
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
                        report.total_records,
                        report.valid_urls,
                        report.invalid_urls,
                        report.valid_tnved_codes,
                        report.invalid_tnved_codes,
                        report.duplicate_urls,
                        report.missing_descriptions,
                        round(report.get_url_quality_score(), 2),
                        round(report.get_tnved_quality_score(), 2),
                        round(report.get_overall_quality_score(), 2)
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # URL issues sheet
                if report.url_validation_issues:
                    pd.DataFrame(report.url_validation_issues).to_excel(
                        writer, sheet_name='URL Issues', index=False
                    )
                
                # TNVED issues sheet
                if report.tnved_validation_issues:
                    pd.DataFrame(report.tnved_validation_issues).to_excel(
                        writer, sheet_name='TNVED Issues', index=False
                    )
                
                # Distributions sheet
                distributions_data = []
                
                for shop_type, count in report.shop_type_distribution.items():
                    distributions_data.append({
                        'Type': 'Shop Type',
                        'Value': shop_type,
                        'Count': count
                    })
                
                for domain, count in report.domain_distribution.items():
                    distributions_data.append({
                        'Type': 'Domain',
                        'Value': domain,
                        'Count': count
                    })
                
                for source, count in report.source_distribution.items():
                    distributions_data.append({
                        'Type': 'Source',
                        'Value': source,
                        'Count': count
                    })
                
                if distributions_data:
                    pd.DataFrame(distributions_data).to_excel(
                        writer, sheet_name='Distributions', index=False
                    )
                
                # Recommendations sheet
                recommendations_data = {
                    'Recommendation': report.recommendations
                }
                pd.DataFrame(recommendations_data).to_excel(
                    writer, sheet_name='Recommendations', index=False
                )
            
            logger.info(f"Data quality report exported to {output_path}")
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
    analyzer = URLDataQualityAnalyzer()
    
    try:
        report = analyzer.analyze_excel_file(file_path)
        
        return {
            "success": True,
            "file_path": file_path,
            "quality_report": asdict(report),
            "summary": {
                "total_records": report.total_records,
                "url_quality_score": report.get_url_quality_score(),
                "tnved_quality_score": report.get_tnved_quality_score(),
                "overall_quality_score": report.get_overall_quality_score(),
                "recommendations_count": len(report.recommendations)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "file_path": file_path,
            "error": str(e)
        }


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = validate_url_data_file(file_path)
        
        if result["success"]:
            print(f"Validation completed for {file_path}")
            print(f"Total records: {result['summary']['total_records']}")
            print(f"URL quality: {result['summary']['url_quality_score']:.1f}%")
            print(f"TNVED quality: {result['summary']['tnved_quality_score']:.1f}%")
            print(f"Overall quality: {result['summary']['overall_quality_score']:.1f}%")
            print(f"Recommendations: {result['summary']['recommendations_count']}")
        else:
            print(f"Validation failed: {result['error']}")
    else:
        print("Usage: python url_data_validator.py <excel_file_path>")