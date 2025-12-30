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
class SecurityConfig:
    """Security configuration settings."""
    session_timeout_hours: int = 24
    max_concurrent_uploads: int = 10
    allowed_hosts: List[str] = field(default_factory=lambda: ["*"])
    cors_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class FileConfig:
    """File management configuration."""
    temp_dir: str = "./temp_files"
    cleanup_interval_hours: int = 1
    max_storage_gb: float = 10.0
    auto_cleanup_enabled: bool = True


@dataclass
class WebConfig:
    """Web application configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    log_level: str = "info"


@dataclass
class AuthConfig:
    """Authentication configuration."""
    enabled: bool = True
    users: Dict[str, str] = field(default_factory=lambda: {"admin": "admin123"})  # username: password
    session_secret: str = "change-this-secret-key"


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
            config.auth = AuthConfig(**auth_data)
        
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