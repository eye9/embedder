"""
ТНВЭД Code Validation Utilities

This module provides validation functions for ТНВЭД codes to ensure
they follow the correct format and structure.
"""

import re
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class TNVEDValidationError(Exception):
    """Raised when ТНВЭД code validation fails"""
    pass


def validate_tnved_code(code: str, strict: bool = True) -> str:
    """
    Validate and normalize ТНВЭД code format.
    
    ТНВЭД codes should be 10 digits long, following the format:
    - First 2 digits: Group (01-99)
    - Next 2 digits: Heading (00-99)
    - Next 2 digits: Subheading (00-99)
    - Last 4 digits: Commodity code (0000-9999)
    
    Args:
        code: ТНВЭД code to validate
        strict: If True, enforce strict 10-digit format. If False, allow shorter codes with padding
        
    Returns:
        Normalized 10-digit ТНВЭД code
        
    Raises:
        TNVEDValidationError: If code format is invalid
        ValueError: If code is empty or None
        
    Examples:
        >>> validate_tnved_code("0901110000")
        "0901110000"
        >>> validate_tnved_code("901110000")  # 9 digits, will be padded
        "0901110000"
        >>> validate_tnved_code("09011100")   # 8 digits, will be padded
        "0901110000"
        >>> validate_tnved_code("abc123")     # Invalid format
        TNVEDValidationError: Invalid ТНВЭД code format
    """
    if not code:
        raise ValueError("ТНВЭД code cannot be empty or None")
    
    # Convert to string and strip whitespace
    code_str = str(code).strip()
    
    if not code_str:
        raise ValueError("ТНВЭД code cannot be empty after stripping whitespace")
    
    # Remove any non-digit characters for validation
    digits_only = re.sub(r'\D', '', code_str)
    
    if not digits_only:
        raise TNVEDValidationError(f"ТНВЭД code must contain digits: '{code}'")
    
    # Check length constraints
    if len(digits_only) > 10:
        raise TNVEDValidationError(
            f"ТНВЭД code cannot be longer than 10 digits: '{code}' ({len(digits_only)} digits)"
        )
    
    if strict and len(digits_only) != 10:
        raise TNVEDValidationError(
            f"ТНВЭД code must be exactly 10 digits in strict mode: '{code}' ({len(digits_only)} digits)"
        )
    
    if len(digits_only) < 4:
        raise TNVEDValidationError(
            f"ТНВЭД code must be at least 4 digits: '{code}' ({len(digits_only)} digits)"
        )
    
    # Pad with leading zeros to make it 10 digits
    normalized_code = digits_only.zfill(10)
    
    # Validate the structure (basic checks)
    group = normalized_code[:2]
    heading = normalized_code[2:4]
    subheading = normalized_code[4:6]
    commodity = normalized_code[6:10]
    
    # Group should be 01-99 (00 is not valid for most classifications)
    if group == "00":
        logger.warning(f"ТНВЭД code has group '00' which may be invalid: {normalized_code}")
    
    # All parts should be numeric (already ensured by digits_only check)
    # Additional validation could be added here for specific ТНВЭД rules
    
    logger.debug(f"Validated ТНВЭД code: '{code}' -> '{normalized_code}'")
    
    return normalized_code


def is_valid_tnved_code(code: str, strict: bool = True) -> bool:
    """
    Check if a ТНВЭД code is valid without raising exceptions.
    
    Args:
        code: ТНВЭД code to check
        strict: If True, enforce strict 10-digit format
        
    Returns:
        True if code is valid, False otherwise
        
    Examples:
        >>> is_valid_tnved_code("0901110000")
        True
        >>> is_valid_tnved_code("abc123")
        False
        >>> is_valid_tnved_code("901110000", strict=False)
        True
        >>> is_valid_tnved_code("901110000", strict=True)
        False
    """
    try:
        validate_tnved_code(code, strict=strict)
        return True
    except (TNVEDValidationError, ValueError):
        return False


def normalize_tnved_code(code: str) -> Optional[str]:
    """
    Normalize ТНВЭД code format without strict validation.
    
    This function is more lenient and attempts to normalize codes
    that might have minor formatting issues.
    
    Args:
        code: ТНВЭД code to normalize
        
    Returns:
        Normalized 10-digit code or None if cannot be normalized
        
    Examples:
        >>> normalize_tnved_code("0901110000")
        "0901110000"
        >>> normalize_tnved_code("901.11.00.00")
        "0901110000"
        >>> normalize_tnved_code("09 01 11 00 00")
        "0901110000"
        >>> normalize_tnved_code("invalid")
        None
    """
    try:
        return validate_tnved_code(code, strict=False)
    except (TNVEDValidationError, ValueError):
        return None


def validate_tnved_codes_batch(codes: list, strict: bool = True) -> dict:
    """
    Validate a batch of ТНВЭД codes.
    
    Args:
        codes: List of ТНВЭД codes to validate
        strict: If True, enforce strict 10-digit format
        
    Returns:
        Dictionary with validation results:
        {
            "valid": [list of valid normalized codes],
            "invalid": [list of (original_code, error_message) tuples],
            "total": total number of codes processed,
            "valid_count": number of valid codes,
            "invalid_count": number of invalid codes
        }
        
    Examples:
        >>> codes = ["0901110000", "invalid", "901110000"]
        >>> result = validate_tnved_codes_batch(codes, strict=False)
        >>> result["valid_count"]
        2
        >>> result["invalid_count"]
        1
    """
    valid_codes = []
    invalid_codes = []
    
    for code in codes:
        try:
            normalized = validate_tnved_code(code, strict=strict)
            valid_codes.append(normalized)
        except (TNVEDValidationError, ValueError) as e:
            invalid_codes.append((code, str(e)))
    
    return {
        "valid": valid_codes,
        "invalid": invalid_codes,
        "total": len(codes),
        "valid_count": len(valid_codes),
        "invalid_count": len(invalid_codes)
    }