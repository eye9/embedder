#!/usr/bin/env python3
"""
URL Processing Configuration Validation Utility

This script validates URL processing configuration and provides
detailed feedback about configuration issues.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.config.settings import (
    BatchProcessorConfig, 
    URLProcessingConfig,
    URLPriority,
    validate_url_processing_config
)


def validate_config_file(config_path: str) -> Dict[str, Any]:
    """
    Validates configuration file and returns validation results.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary with validation results
    """
    result = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "url_config": None
    }
    
    try:
        # Load configuration
        config = BatchProcessorConfig.from_yaml(config_path)
        
        # Validate overall configuration
        config.validate()
        
        # Specific URL processing validation
        url_errors = validate_url_processing_config(config.url_processing)
        if url_errors:
            result["errors"].extend(url_errors)
        else:
            result["valid"] = True
            result["url_config"] = config.url_processing
        
        # Generate warnings for common issues
        warnings = _generate_warnings(config.url_processing)
        result["warnings"].extend(warnings)
        
    except FileNotFoundError:
        result["errors"].append(f"Configuration file not found: {config_path}")
    except Exception as e:
        result["errors"].append(f"Configuration error: {str(e)}")
    
    return result


def validate_environment_config() -> Dict[str, Any]:
    """
    Validates URL processing configuration from environment variables.
    
    Returns:
        Dictionary with validation results
    """
    result = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "url_config": None,
        "env_vars_found": []
    }
    
    try:
        # Load configuration from environment
        config = BatchProcessorConfig.from_env()
        
        # Check which URL-related environment variables are set
        url_env_vars = [
            "TNVED_URL_ENABLED",
            "TNVED_URL_PRIORITY", 
            "TNVED_URL_TIMEOUT_SECONDS",
            "TNVED_URL_NORMALIZATION_ENABLED",
            "TNVED_URL_REMOVE_QUERY_PARAMS",
            "TNVED_URL_REMOVE_FRAGMENTS",
            "TNVED_URL_NORMALIZE_PROTOCOL",
            "TNVED_URL_SUPPORTED_SHOPS",
            "TNVED_URL_SECURITY_ENABLED",
            "TNVED_URL_VALIDATE_ON_INPUT",
            "TNVED_URL_SANITIZE_FOR_STORAGE",
            "TNVED_URL_MASK_SENSITIVE_PARAMS",
            "TNVED_URL_MAX_LENGTH",
            "TNVED_URL_BLOCK_MALICIOUS_PATTERNS",
            "TNVED_URL_COLLECTION_NAME",
            "TNVED_URL_BATCH_SIZE",
            "TNVED_URL_ENABLE_STATISTICS",
            "TNVED_URL_AUTO_CLEANUP_DUPLICATES"
        ]
        
        for var in url_env_vars:
            if os.getenv(var):
                result["env_vars_found"].append(f"{var}={os.getenv(var)}")
        
        # Validate overall configuration
        config.validate()
        
        # Specific URL processing validation
        url_errors = validate_url_processing_config(config.url_processing)
        if url_errors:
            result["errors"].extend(url_errors)
        else:
            result["valid"] = True
            result["url_config"] = config.url_processing
        
        # Generate warnings
        warnings = _generate_warnings(config.url_processing)
        result["warnings"].extend(warnings)
        
    except Exception as e:
        result["errors"].append(f"Environment configuration error: {str(e)}")
    
    return result


def _generate_warnings(config: URLProcessingConfig) -> List[str]:
    """Generate warnings for potential configuration issues."""
    warnings = []
    
    # Check for potentially problematic settings
    if config.timeout_seconds > 30:
        warnings.append(f"URL timeout is very high ({config.timeout_seconds}s). Consider reducing for better performance.")
    
    if config.timeout_seconds < 1:
        warnings.append(f"URL timeout is very low ({config.timeout_seconds}s). May cause frequent timeouts.")
    
    if config.priority == URLPriority.ONLY and not config.enabled:
        warnings.append("URL priority is set to 'only' but URL processing is disabled.")
    
    if not config.security.enabled:
        warnings.append("URL security validation is disabled. This may pose security risks.")
    
    if config.security.max_url_length > 4096:
        warnings.append(f"Max URL length is very high ({config.security.max_url_length}). Consider reducing.")
    
    if config.database.batch_size > 1000:
        warnings.append(f"URL database batch size is very high ({config.database.batch_size}). May impact performance.")
    
    if len(config.normalization.supported_shops) > 10:
        warnings.append(f"Many supported shops configured ({len(config.normalization.supported_shops)}). Ensure all are needed.")
    
    return warnings


def print_validation_results(results: Dict[str, Any], config_source: str):
    """Print validation results in a formatted way."""
    print(f"\n=== URL Processing Configuration Validation ({config_source}) ===")
    
    if results["valid"]:
        print("✅ Configuration is VALID")
    else:
        print("❌ Configuration is INVALID")
    
    if results["errors"]:
        print(f"\n🚨 Errors ({len(results['errors'])}):")
        for i, error in enumerate(results["errors"], 1):
            print(f"  {i}. {error}")
    
    if results["warnings"]:
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for i, warning in enumerate(results["warnings"], 1):
            print(f"  {i}. {warning}")
    
    if results.get("env_vars_found"):
        print(f"\n🔧 Environment Variables Found ({len(results['env_vars_found'])}):")
        for var in results["env_vars_found"]:
            print(f"  • {var}")
    
    if results["url_config"]:
        config = results["url_config"]
        print(f"\n📋 URL Processing Configuration Summary:")
        print(f"  • Enabled: {config.enabled}")
        print(f"  • Priority: {config.priority.value}")
        print(f"  • Timeout: {config.timeout_seconds}s")
        print(f"  • Security: {config.security.enabled}")
        print(f"  • Normalization: {config.normalization.enabled}")
        print(f"  • Collection: {config.database.collection_name}")
        print(f"  • Supported Shops: {', '.join(config.normalization.supported_shops)}")


def main():
    """Main validation function."""
    print("URL Processing Configuration Validator")
    print("=" * 50)
    
    # Check for configuration file argument
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        print(f"Validating configuration file: {config_path}")
        results = validate_config_file(config_path)
        print_validation_results(results, "File")
    else:
        print("No configuration file specified, checking environment variables...")
        results = validate_environment_config()
        print_validation_results(results, "Environment")
    
    # Exit with appropriate code
    sys.exit(0 if results["valid"] else 1)


if __name__ == "__main__":
    main()