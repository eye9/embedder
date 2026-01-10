"""
Configuration management for the batch Excel processor.

This module provides centralized configuration management with support for
environment variables, YAML files, and default values.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ProcessingMode(str, Enum):
    """Processing modes for Excel files."""
    ALL = "all"
    EMPTY_ONLY = "empty_only"


class AlgorithmType(str, Enum):
    """Available TNVED selection algorithms."""
    SIMILARITY_TOP1 = "similarity_top1"
    LLM_REASONING = "llm_reasoning"


class URLPriority(str, Enum):
    """URL search priority modes."""
    FIRST = "first"      # URL search first, then semantic fallback
    ONLY = "only"        # URL search only, no semantic fallback
    DISABLED = "disabled" # Semantic search only, no URL processing


@dataclass
class RedisConfig:
    """Redis configuration settings."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Get Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class CeleryConfig:
    """Celery configuration settings."""
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    task_serializer: str = "json"
    accept_content: List[str] = field(default_factory=lambda: ["json"])
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True
    worker_prefetch_multiplier: int = 1
    task_acks_late: bool = True
    worker_max_tasks_per_child: int = 1000


@dataclass
class ProcessingConfig:
    """Processing configuration settings."""
    chunk_size: int = 1000
    default_algorithm: AlgorithmType = AlgorithmType.SIMILARITY_TOP1
    confidence_threshold: float = 0.7
    llm_top_k: int = 5
    max_file_size_mb: int = 100
    supported_extensions: List[str] = field(default_factory=lambda: [".xlsx", ".xls"])
    required_columns: List[str] = field(default_factory=lambda: ["Product Detailed Description"])
    output_columns: List[str] = field(default_factory=lambda: ["TNVED_Code", "Selection_Reason"])


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = False
    requests_per_minute: int = 60
    burst_size: int = 10


@dataclass
class PasswordPolicyConfig:
    """Password policy configuration."""
    min_length: int = 8
    require_uppercase: bool = False
    require_lowercase: bool = False
    require_numbers: bool = False
    require_special_chars: bool = False


@dataclass
class SessionSecurityConfig:
    """Session security configuration."""
    secure_cookies: bool = False
    httponly_cookies: bool = True
    samesite: str = "lax"
    regenerate_on_login: bool = True


@dataclass
class FailedLoginProtectionConfig:
    """Failed login protection configuration."""
    max_attempts: int = 5
    lockout_duration_minutes: int = 15
    track_by_ip: bool = True


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    session_timeout_hours: int = 24
    max_concurrent_uploads: int = 10
    allowed_hosts: List[str] = field(default_factory=lambda: ["*"])
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    csrf_protection: bool = False
    secure_cookies: bool = False
    https_only: bool = False


@dataclass
class FileConfig:
    """File management configuration."""
    temp_dir: str = "./temp_files"
    cleanup_interval_hours: int = 1
    max_storage_gb: float = 10.0
    auto_cleanup_enabled: bool = True
    max_files_per_user: int = 10
    quarantine_suspicious_files: bool = False


@dataclass
class WebConfig:
    """Web application configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    access_log: bool = True
    server_header: bool = True
    proxy_headers: bool = False


@dataclass
class AuthConfig:
    """Authentication configuration."""
    enabled: bool = True
    users: Dict[str, str] = field(default_factory=lambda: {"admin": "admin123"})  # username: password
    session_secret: str = "change-this-secret-key"
    password_policy: PasswordPolicyConfig = field(default_factory=PasswordPolicyConfig)
    session_security: SessionSecurityConfig = field(default_factory=SessionSecurityConfig)
    failed_login_protection: FailedLoginProtectionConfig = field(default_factory=FailedLoginProtectionConfig)


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "info"
    format: str = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/batch_processor.log"
    max_file_size_mb: int = 100
    backup_count: int = 5
    structured_logging: bool = False
    log_requests: bool = True
    log_errors_only: bool = False
    sensitive_data_masking: bool = True


@dataclass
class AlertConfig:
    """Alert configuration."""
    enabled: bool = False
    error_threshold: int = 10
    response_time_threshold_ms: int = 5000
    disk_usage_threshold_percent: int = 85
    memory_usage_threshold_percent: int = 90


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enabled: bool = True
    health_check_interval: int = 30
    metrics_enabled: bool = True
    performance_tracking: bool = True
    error_tracking: bool = True
    alerts: AlertConfig = field(default_factory=AlertConfig)


@dataclass
class PerformanceConfig:
    """Performance optimization configuration."""
    connection_pool_size: int = 10
    max_connections: int = 50
    request_timeout_seconds: int = 300
    worker_timeout_seconds: int = 1800
    enable_compression: bool = False
    cache_static_files: bool = False


@dataclass
class BackupConfig:
    """Backup and recovery configuration."""
    enabled: bool = False
    interval_hours: int = 24
    retention_days: int = 7
    backup_path: str = "./backups"
    include_logs: bool = True
    include_temp_files: bool = False


@dataclass
class FeatureConfig:
    """Feature flags configuration."""
    llm_integration: bool = False
    advanced_analytics: bool = False
    batch_notifications: bool = False
    api_versioning: bool = True
    swagger_ui: bool = True


@dataclass
class URLNormalizationConfig:
    """URL normalization configuration."""
    enabled: bool = True
    remove_query_params: bool = True
    remove_fragments: bool = True
    normalize_protocol: bool = True
    supported_shops: List[str] = field(default_factory=lambda: [
        'ozon', 'yandex_market', 'wildberries', 'aliexpress'
    ])


@dataclass
class URLSecurityConfig:
    """URL security configuration."""
    enabled: bool = True
    validate_on_input: bool = True
    sanitize_for_storage: bool = True
    mask_sensitive_params: bool = True
    max_url_length: int = 2048
    block_malicious_patterns: bool = True


@dataclass
class URLDatabaseConfig:
    """URL database configuration."""
    collection_name: str = "url_tnved_mapping"
    batch_size: int = 100
    enable_statistics: bool = True
    auto_cleanup_duplicates: bool = False


@dataclass
class URLProcessingConfig:
    """URL processing configuration."""
    enabled: bool = True
    priority: URLPriority = URLPriority.FIRST
    timeout_seconds: float = 5.0
    normalization: URLNormalizationConfig = field(default_factory=URLNormalizationConfig)
    security: URLSecurityConfig = field(default_factory=URLSecurityConfig)
    database: URLDatabaseConfig = field(default_factory=URLDatabaseConfig)


@dataclass
class BatchProcessorConfig:
    """Main configuration class for the batch processor."""
    redis: RedisConfig = field(default_factory=RedisConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    files: FileConfig = field(default_factory=FileConfig)
    web: WebConfig = field(default_factory=WebConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    url_processing: URLProcessingConfig = field(default_factory=URLProcessingConfig)
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "BatchProcessorConfig":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchProcessorConfig":
        """Create configuration from dictionary."""
        config = cls()
        
        # Update Redis config
        if "redis" in data:
            redis_data = data["redis"]
            config.redis = RedisConfig(**redis_data)
        
        # Update Celery config
        if "celery" in data:
            celery_data = data["celery"]
            config.celery = CeleryConfig(**celery_data)
        
        # Update processing config
        if "processing" in data:
            proc_data = data["processing"]
            config.processing = ProcessingConfig(**proc_data)
        
        # Update security config
        if "security" in data:
            sec_data = data["security"]
            # Handle nested rate_limiting config
            if "rate_limiting" in sec_data:
                rate_limit_data = sec_data.pop("rate_limiting")
                sec_data["rate_limiting"] = RateLimitConfig(**rate_limit_data)
            config.security = SecurityConfig(**sec_data)
        
        # Update file config
        if "files" in data:
            file_data = data["files"]
            config.files = FileConfig(**file_data)
        
        # Update web config
        if "web" in data:
            web_data = data["web"]
            config.web = WebConfig(**web_data)
        
        # Update auth config
        if "auth" in data:
            auth_data = data["auth"]
            # Handle nested auth configs
            if "password_policy" in auth_data:
                policy_data = auth_data.pop("password_policy")
                auth_data["password_policy"] = PasswordPolicyConfig(**policy_data)
            if "session_security" in auth_data:
                session_data = auth_data.pop("session_security")
                auth_data["session_security"] = SessionSecurityConfig(**session_data)
            if "failed_login_protection" in auth_data:
                protection_data = auth_data.pop("failed_login_protection")
                auth_data["failed_login_protection"] = FailedLoginProtectionConfig(**protection_data)
            config.auth = AuthConfig(**auth_data)
        
        # Update logging config
        if "logging" in data:
            logging_data = data["logging"]
            config.logging = LoggingConfig(**logging_data)
        
        # Update monitoring config
        if "monitoring" in data:
            monitoring_data = data["monitoring"]
            # Handle nested alerts config
            if "alerts" in monitoring_data:
                alerts_data = monitoring_data.pop("alerts")
                monitoring_data["alerts"] = AlertConfig(**alerts_data)
            config.monitoring = MonitoringConfig(**monitoring_data)
        
        # Update performance config
        if "performance" in data:
            perf_data = data["performance"]
            config.performance = PerformanceConfig(**perf_data)
        
        # Update backup config
        if "backup" in data:
            backup_data = data["backup"]
            config.backup = BackupConfig(**backup_data)
        
        # Update features config
        if "features" in data:
            features_data = data["features"]
            config.features = FeatureConfig(**features_data)
        
        # Update URL processing config
        if "url_processing" in data:
            url_data = data["url_processing"]
            
            # Handle priority enum conversion
            if "priority" in url_data:
                priority_str = url_data["priority"]
                try:
                    url_data["priority"] = URLPriority(priority_str)
                except ValueError:
                    # Keep original value, will be caught in validation
                    pass
            
            # Handle nested URL configs
            if "normalization" in url_data:
                norm_data = url_data.pop("normalization")
                url_data["normalization"] = URLNormalizationConfig(**norm_data)
            if "security" in url_data:
                sec_data = url_data.pop("security")
                url_data["security"] = URLSecurityConfig(**sec_data)
            if "database" in url_data:
                db_data = url_data.pop("database")
                url_data["database"] = URLDatabaseConfig(**db_data)
            
            config.url_processing = URLProcessingConfig(**url_data)
        
        return config
    
    @classmethod
    def from_env(cls) -> "BatchProcessorConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        # Redis configuration from environment
        config.redis.host = os.getenv("REDIS_HOST", config.redis.host)
        config.redis.port = int(os.getenv("REDIS_PORT", config.redis.port))
        config.redis.db = int(os.getenv("REDIS_DB", config.redis.db))
        config.redis.password = os.getenv("REDIS_PASSWORD", config.redis.password)
        
        # Celery configuration from environment
        config.celery.broker_url = os.getenv("CELERY_BROKER_URL", config.redis.url)
        config.celery.result_backend = os.getenv("CELERY_RESULT_BACKEND", config.redis.url)
        
        # Processing configuration from environment
        config.processing.chunk_size = int(os.getenv("PROCESSING_CHUNK_SIZE", config.processing.chunk_size))
        config.processing.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", config.processing.confidence_threshold))
        config.processing.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", config.processing.max_file_size_mb))
        
        # Web configuration from environment
        config.web.host = os.getenv("WEB_HOST", config.web.host)
        config.web.port = int(os.getenv("WEB_PORT", config.web.port))
        config.web.debug = os.getenv("DEBUG", "false").lower() == "true"
        config.web.log_level = os.getenv("LOG_LEVEL", config.web.log_level)
        
        # File configuration from environment
        config.files.temp_dir = os.getenv("TEMP_DIR", config.files.temp_dir)
        config.files.max_storage_gb = float(os.getenv("MAX_STORAGE_GB", config.files.max_storage_gb))
        
        # Auth configuration from environment
        config.auth.enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
        config.auth.session_secret = os.getenv("SESSION_SECRET", config.auth.session_secret)
        
        # URL processing configuration from environment
        config.url_processing.enabled = os.getenv("TNVED_URL_ENABLED", "true").lower() == "true"
        
        if priority := os.getenv("TNVED_URL_PRIORITY"):
            try:
                config.url_processing.priority = URLPriority(priority.lower())
            except ValueError:
                pass  # Keep default
        
        if timeout := os.getenv("TNVED_URL_TIMEOUT_SECONDS"):
            try:
                config.url_processing.timeout_seconds = float(timeout)
            except ValueError:
                pass
        
        # URL normalization settings
        config.url_processing.normalization.enabled = os.getenv("TNVED_URL_NORMALIZATION_ENABLED", "true").lower() == "true"
        config.url_processing.normalization.remove_query_params = os.getenv("TNVED_URL_REMOVE_QUERY_PARAMS", "true").lower() == "true"
        config.url_processing.normalization.remove_fragments = os.getenv("TNVED_URL_REMOVE_FRAGMENTS", "true").lower() == "true"
        config.url_processing.normalization.normalize_protocol = os.getenv("TNVED_URL_NORMALIZE_PROTOCOL", "true").lower() == "true"
        
        if supported_shops := os.getenv("TNVED_URL_SUPPORTED_SHOPS"):
            config.url_processing.normalization.supported_shops = [shop.strip() for shop in supported_shops.split(",")]
        
        # URL security settings
        config.url_processing.security.enabled = os.getenv("TNVED_URL_SECURITY_ENABLED", "true").lower() == "true"
        config.url_processing.security.validate_on_input = os.getenv("TNVED_URL_VALIDATE_ON_INPUT", "true").lower() == "true"
        config.url_processing.security.sanitize_for_storage = os.getenv("TNVED_URL_SANITIZE_FOR_STORAGE", "true").lower() == "true"
        config.url_processing.security.mask_sensitive_params = os.getenv("TNVED_URL_MASK_SENSITIVE_PARAMS", "true").lower() == "true"
        config.url_processing.security.block_malicious_patterns = os.getenv("TNVED_URL_BLOCK_MALICIOUS_PATTERNS", "true").lower() == "true"
        
        if max_length := os.getenv("TNVED_URL_MAX_LENGTH"):
            try:
                config.url_processing.security.max_url_length = int(max_length)
            except ValueError:
                pass
        
        # URL database settings
        if collection_name := os.getenv("TNVED_URL_COLLECTION_NAME"):
            config.url_processing.database.collection_name = collection_name
        
        if batch_size := os.getenv("TNVED_URL_BATCH_SIZE"):
            try:
                config.url_processing.database.batch_size = int(batch_size)
            except ValueError:
                pass
        
        config.url_processing.database.enable_statistics = os.getenv("TNVED_URL_ENABLE_STATISTICS", "true").lower() == "true"
        config.url_processing.database.auto_cleanup_duplicates = os.getenv("TNVED_URL_AUTO_CLEANUP_DUPLICATES", "false").lower() == "true"
        
        return config
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate processing settings
        if self.processing.chunk_size <= 0:
            errors.append("Processing chunk_size must be positive")
        
        if not (0.0 <= self.processing.confidence_threshold <= 1.0):
            errors.append("Confidence threshold must be between 0.0 and 1.0")
        
        if self.processing.max_file_size_mb <= 0:
            errors.append("Max file size must be positive")
        
        # Validate file settings
        if self.files.max_storage_gb <= 0:
            errors.append("Max storage must be positive")
        
        # Validate web settings
        if not (1 <= self.web.port <= 65535):
            errors.append("Web port must be between 1 and 65535")
        
        # Validate auth settings
        if self.auth.enabled and not self.auth.users:
            errors.append("Authentication is enabled but no users configured")
        
        # Validate URL processing settings
        if self.url_processing.enabled:
            if self.url_processing.timeout_seconds <= 0:
                errors.append("URL processing timeout must be positive")
            
            if self.url_processing.security.max_url_length <= 0:
                errors.append("URL max length must be positive")
            
            if self.url_processing.database.batch_size <= 0:
                errors.append("URL database batch size must be positive")
            
            if not self.url_processing.database.collection_name.strip():
                errors.append("URL database collection name cannot be empty")
            
            if not self.url_processing.normalization.supported_shops:
                errors.append("At least one supported shop must be specified for URL processing")
        
        if errors:
            raise ValueError("Configuration validation failed: " + "; ".join(errors))


# Global configuration instance
_config: Optional[BatchProcessorConfig] = None


def get_config() -> BatchProcessorConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config(config_path: Optional[str] = None) -> BatchProcessorConfig:
    """
    Load configuration from file or environment.
    
    Args:
        config_path: Path to YAML configuration file. If None, checks environment
                    variable BATCH_PROCESSOR_CONFIG, then loads from environment.
    
    Returns:
        BatchProcessorConfig instance
    """
    # Check for config path in environment if not provided
    if config_path is None:
        config_path = os.getenv("BATCH_PROCESSOR_CONFIG")
    
    if config_path and Path(config_path).exists():
        config = BatchProcessorConfig.from_yaml(config_path)
    else:
        config = BatchProcessorConfig.from_env()
    
    config.validate()
    return config


def set_config(config: BatchProcessorConfig) -> None:
    """Set the global configuration instance."""
    global _config
    config.validate()
    _config = config


def validate_url_processing_config(config: URLProcessingConfig) -> List[str]:
    """
    Validates URL processing configuration and returns list of errors.
    
    Args:
        config: URL processing configuration to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Validate timeout
    if config.timeout_seconds <= 0:
        errors.append(f"Invalid URL timeout_seconds: {config.timeout_seconds}. Must be positive")
    
    # Validate max URL length
    if config.security.max_url_length <= 0:
        errors.append(f"Invalid URL max_url_length: {config.security.max_url_length}. Must be positive")
    
    # Validate batch size
    if config.database.batch_size <= 0:
        errors.append(f"Invalid URL batch_size: {config.database.batch_size}. Must be positive")
    
    # Validate collection name
    if not config.database.collection_name.strip():
        errors.append("URL collection name cannot be empty")
    
    # Validate supported shops
    if not config.normalization.supported_shops:
        errors.append("At least one supported shop must be specified")
    
    # Validate priority enum
    if not isinstance(config.priority, URLPriority):
        errors.append(f"Invalid URL priority: {config.priority}. Must be URLPriority enum value")
    
    return errors


def get_url_processing_config() -> URLProcessingConfig:
    """
    Get URL processing configuration from global config.
    
    Returns:
        URLProcessingConfig instance
    """
    return get_config().url_processing


def is_url_processing_enabled() -> bool:
    """
    Check if URL processing is enabled in configuration.
    
    Returns:
        True if URL processing is enabled
    """
    return get_config().url_processing.enabled