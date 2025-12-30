"""
Utilities for working with TNVED codes.

This module provides functions for extracting and validating TNVED codes
from database identifiers and other formats.
"""

import re
from typing import Optional


def extract_tnved_code(identifier: str) -> Optional[str]:
    """
    Extract clean TNVED code from database identifier.
    
    TNVED codes in the database are stored with identifiers like:
    - "9405210013" (clean 10-digit code)
    - "9405210013_003" (code with sequence number)
    - "0901210009_001" (code with sequence number)
    
    This function extracts only the 10-digit TNVED code part.
    
    Args:
        identifier: Database identifier that may contain TNVED code
        
    Returns:
        Clean 10-digit TNVED code or None if not found
        
    Examples:
        >>> extract_tnved_code("9405210013_003")
        "9405210013"
        >>> extract_tnved_code("9405210013")
        "9405210013"
        >>> extract_tnved_code("invalid")
        None
    """
    if not identifier:
        return None
    
    # Remove any sequence number suffix (everything after underscore)
    base_code = identifier.split('_')[0]
    
    # Validate that it's exactly 10 digits
    if re.match(r'^\d{10}$', base_code):
        return base_code
    
    return None


def is_valid_tnved_code(code: str) -> bool:
    """
    Check if a string is a valid TNVED code.
    
    TNVED codes must be exactly 10 digits.
    
    Args:
        code: String to validate
        
    Returns:
        True if valid TNVED code, False otherwise
        
    Examples:
        >>> is_valid_tnved_code("9405210013")
        True
        >>> is_valid_tnved_code("9405210013_003")
        False
        >>> is_valid_tnved_code("94052100")
        False
    """
    if not code:
        return False
    
    return bool(re.match(r'^\d{10}$', code))


def format_tnved_code(code: str) -> str:
    """
    Format TNVED code for display.
    
    Currently just returns the code as-is, but could be extended
    to add formatting like spaces or dashes if needed.
    
    Args:
        code: TNVED code to format
        
    Returns:
        Formatted TNVED code
    """
    return code if code else ""


def get_tnved_code_from_search_result(search_result) -> Optional[str]:
    """
    Extract clean TNVED code from a SearchResult object.
    
    Args:
        search_result: SearchResult object from TNVED search
        
    Returns:
        Clean 10-digit TNVED code or None if not extractable
    """
    if not search_result or not hasattr(search_result, 'code'):
        return None
    
    return extract_tnved_code(search_result.code)