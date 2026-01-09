"""
URL Processing Configuration for TNVED Code Matching System

This module extends the existing configuration system with URL processing settings.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class URLPriority(Enum):
    """URL search priority modes"""
    FIRST = "first"      # URL search first, then semantic fallback
    ONLY = "only"        # URL search only, no semantic fallback
    DISABLED = "disabled" # Semantic search only, no URL processing


@dataclass
class URLNormalizationConfig:
    """URL normalization configuration"""
    enabled: bool = True
    remove_query_params: bool = True
    remove_fragments: bool = True
    normalize_protocol: bool = True
    supported_shops: List[str] = field(default_factory=lambda: [
        'ozon', 'yandex_market', 'wildberries', 'aliexpress'
    ])


@dataclass
class URLSecurityConfig:
    """URL security configuration"""
    enabled: bool = True
    validate_on_input: bool = True
    sanitize_for_storage: bool = True
    mask_sensitive_params: bool = True
    max_url_length: int = 2048
    block_malicious_patterns: bool = True


@dataclass
class URLDatabaseConfig:
    """URL database configuration"""
    collection_name: str = "url_tnved_mapping"
    batch_size: int = 100
    enable_statistics: bool = True
    auto_cleanup_duplicates: bool = False


@dataclass
class URLProcessingConfig:
    """Main URL processing configuration"""
    enabled: bool = True
    priority: URLPriority = URLPriority.FIRST
    timeout_seconds: float = 5.0
    normalization: URLNormalizationConfig = field(default_factory=URLNormalizationConfig)
    security: URLSecurityConfig = field(default_factory=URLSecurityConfig)
    database: URLDatabaseConfig = field(default_factory=URLDatabaseConfig)


def load_url_config_from_env() -> URLProcessingConfig:
    """
    Load URL processing configuration from environment variables
    
    Environment variables should be prefixed with TNVED_URL_
    Example: TNVED_URL_ENABLED, TNVED_URL_PRIORITY
    
    Returns:
        URLProcessingConfig instance
    """
    config = URLProcessingConfig()
    
    # Main URL processing settings
    if enabled := os.getenv("TNVED_URL_ENABLED"):
        config.enabled = enabled.lower() in ("true", "1", "yes")
    
    if priority := os.getenv("TNVED_URL_PRIORITY"):
        try:
            config.priority = URLPriority(priority.lower())
        except ValueError:
            # Invalid priority, use default
            pass
    
    if timeout := os.getenv("TNVED_URL_TIMEOUT_SECONDS"):
        try:
            config.timeout_seconds = float(timeout)
        except ValueError:
            pass
    
    # Normalization settings
    if norm_enabled := os.getenv("TNVED_URL_NORMALIZATION_ENABLED"):
        config.normalization.enabled = norm_enabled.lower() in ("true", "1", "yes")
    
    if remove_query := os.getenv("TNVED_URL_REMOVE_QUERY_PARAMS"):
        config.normalization.remove_query_params = remove_query.lower() in ("true", "1", "yes")
    
    if remove_fragments := os.getenv("TNVED_URL_REMOVE_FRAGMENTS"):
        config.normalization.remove_fragments = remove_fragments.lower() in ("true", "1", "yes")
    
    if normalize_protocol := os.getenv("TNVED_URL_NORMALIZE_PROTOCOL"):
        config.normalization.normalize_protocol = normalize_protocol.lower() in ("true", "1", "yes")
    
    if supported_shops := os.getenv("TNVED_URL_SUPPORTED_SHOPS"):
        config.normalization.supported_shops = [shop.strip() for shop in supported_shops.split(",")]
    
    # Security settings
    if security_enabled := os.getenv("TNVED_URL_SECURITY_ENABLED"):
        config.security.enabled = security_enabled.lower() in ("true", "1", "yes")
    
    if validate_input := os.getenv("TNVED_URL_VALIDATE_ON_INPUT"):
        config.security.validate_on_input = validate_input.lower() in ("true", "1", "yes")
    
    if sanitize_storage := os.getenv("TNVED_URL_SANITIZE_FOR_STORAGE"):
        config.security.sanitize_for_storage = sanitize_storage.lower() in ("true", "1", "yes")
    
    if mask_params := os.getenv("TNVED_URL_MASK_SENSITIVE_PARAMS"):
        config.security.mask_sensitive_params = mask_params.lower() in ("true", "1", "yes")
    
    if max_length := os.getenv("TNVED_URL_MAX_LENGTH"):
        try:
            config.security.max_url_length = int(max_length)
        except ValueError:
            pass
    
    if block_malicious := os.getenv("TNVED_URL_BLOCK_MALICIOUS_PATTERNS"):
        config.security.block_malicious_patterns = block_malicious.lower() in ("true", "1", "yes")
    
    # Database settings
    if collection_name := os.getenv("TNVED_URL_COLLECTION_NAME"):
        config.database.collection_name = collection_name
    
    if batch_size := os.getenv("TNVED_URL_BATCH_SIZE"):
        try:
            config.database.batch_size = int(batch_size)
        except ValueError:
            pass
    
    if enable_stats := os.getenv("TNVED_URL_ENABLE_STATISTICS"):
        config.database.enable_statistics = enable_stats.lower() in ("true", "1", "yes")
    
    if auto_cleanup := os.getenv("TNVED_URL_AUTO_CLEANUP_DUPLICATES"):
        config.database.auto_cleanup_duplicates = auto_cleanup.lower() in ("true", "1", "yes")
    
    return config


def validate_url_config(config: URLProcessingConfig) -> None:
    """
    Validates URL processing configuration
    
    Args:
        config: Configuration to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate timeout
    if config.timeout_seconds <= 0:
        raise ValueError(f"Invalid timeout_seconds: {config.timeout_seconds}. Must be positive")
    
    # Validate max URL length
    if config.security.max_url_length <= 0:
        raise ValueError(f"Invalid max_url_length: {config.security.max_url_length}. Must be positive")
    
    # Validate batch size
    if config.database.batch_size <= 0:
        raise ValueError(f"Invalid batch_size: {config.database.batch_size}. Must be positive")
    
    # Validate collection name
    if not config.database.collection_name.strip():
        raise ValueError("Collection name cannot be empty")
    
    # Validate supported shops
    if not config.normalization.supported_shops:
        raise ValueError("At least one supported shop must be specified")
    
    # Validate priority enum
    if not isinstance(config.priority, URLPriority):
        raise ValueError(f"Invalid priority: {config.priority}. Must be URLPriority enum value")


def get_default_url_config() -> URLProcessingConfig:
    """
    Returns default URL processing configuration
    
    Returns:
        URLProcessingConfig with default values
    """
    return URLProcessingConfig()


def merge_url_config_with_dict(config: URLProcessingConfig, data: dict) -> URLProcessingConfig:
    """
    Merges URL configuration with dictionary data (from YAML/JSON)
    
    Args:
        config: Base configuration
        data: Dictionary with configuration overrides
        
    Returns:
        Updated configuration
    """
    if "url_processing" not in data:
        return config
    
    url_data = data["url_processing"]
    
    # Main settings
    if "enabled" in url_data:
        config.enabled = url_data["enabled"]
    
    if "priority" in url_data:
        try:
            config.priority = URLPriority(url_data["priority"])
        except ValueError:
            pass  # Keep default
    
    if "timeout_seconds" in url_data:
        config.timeout_seconds = url_data["timeout_seconds"]
    
    # Normalization settings
    if "normalization" in url_data:
        norm_data = url_data["normalization"]
        
        if "enabled" in norm_data:
            config.normalization.enabled = norm_data["enabled"]
        if "remove_query_params" in norm_data:
            config.normalization.remove_query_params = norm_data["remove_query_params"]
        if "remove_fragments" in norm_data:
            config.normalization.remove_fragments = norm_data["remove_fragments"]
        if "normalize_protocol" in norm_data:
            config.normalization.normalize_protocol = norm_data["normalize_protocol"]
        if "supported_shops" in norm_data:
            config.normalization.supported_shops = norm_data["supported_shops"]
    
    # Security settings
    if "security" in url_data:
        sec_data = url_data["security"]
        
        if "enabled" in sec_data:
            config.security.enabled = sec_data["enabled"]
        if "validate_on_input" in sec_data:
            config.security.validate_on_input = sec_data["validate_on_input"]
        if "sanitize_for_storage" in sec_data:
            config.security.sanitize_for_storage = sec_data["sanitize_for_storage"]
        if "mask_sensitive_params" in sec_data:
            config.security.mask_sensitive_params = sec_data["mask_sensitive_params"]
        if "max_url_length" in sec_data:
            config.security.max_url_length = sec_data["max_url_length"]
        if "block_malicious_patterns" in sec_data:
            config.security.block_malicious_patterns = sec_data["block_malicious_patterns"]
    
    # Database settings
    if "database" in url_data:
        db_data = url_data["database"]
        
        if "collection_name" in db_data:
            config.database.collection_name = db_data["collection_name"]
        if "batch_size" in db_data:
            config.database.batch_size = db_data["batch_size"]
        if "enable_statistics" in db_data:
            config.database.enable_statistics = db_data["enable_statistics"]
        if "auto_cleanup_duplicates" in db_data:
            config.database.auto_cleanup_duplicates = db_data["auto_cleanup_duplicates"]
    
    return config