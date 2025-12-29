"""
Configuration management for ТНВЭД Embedder System
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cuda"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "./chroma_db"
    collection_name: str = "tnved"
    default_source_name: str = "unknown"


@dataclass
class ProcessingConfig:
    """Processing configuration"""
    batch_size: int = 100


@dataclass
class SearchConfig:
    """Search configuration"""
    default_top_k: int = 5
    group_by_code: bool = False
    prioritize_reference: bool = True
    show_source_info: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "tnved_embedder.log"


@dataclass
class AuthConfig:
    """Authentication configuration"""
    enabled: bool = False
    api_keys: List[str] = field(default_factory=list)


@dataclass
class CORSConfig:
    """CORS configuration"""
    enabled: bool = True
    origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60


@dataclass
class APIConfig:
    """API configuration"""
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    auth: AuthConfig = field(default_factory=AuthConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)


@dataclass
class OpenAIConfig:
    """OpenAI configuration"""
    api_key: str = ""
    model: str = "gpt-4"


@dataclass
class LocalLLMConfig:
    """Local LLM configuration"""
    model_path: str = "./models/llama-2-7b"


@dataclass
class LLMConfig:
    """LLM integration configuration"""
    enabled: bool = False
    provider: str = "openai"
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    local: LocalLLMConfig = field(default_factory=LocalLLMConfig)


@dataclass
class LangChainConfig:
    """LangChain integration configuration"""
    enabled: bool = False
    agent_type: str = "react"
    tools: List[str] = field(default_factory=lambda: ["search_tnved", "get_tnved_details"])


@dataclass
class ReferenceSourceConfig:
    """Reference source configuration"""
    name: str = "tnved_official"
    display_name: str = "Официальный справочник ТНВЭД"


@dataclass
class ProductSourceConfig:
    """Product source configuration"""
    default_name: str = "unknown_products"
    display_name: str = "Товары с подобранными кодами"


@dataclass
class SourcesConfig:
    """Sources configuration"""
    reference: ReferenceSourceConfig = field(default_factory=ReferenceSourceConfig)
    product: ProductSourceConfig = field(default_factory=ProductSourceConfig)


@dataclass
class DisplayConfig:
    """Display configuration"""
    source_format: str = "detailed"  # Options: "detailed", "compact", "minimal"
    show_source_id: bool = True
    show_similarity_score: bool = True
    max_description_length: int = 100


@dataclass
class Config:
    """Main configuration class for ТНВЭД Embedder System"""
    model: ModelConfig = field(default_factory=ModelConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    langchain: LangChainConfig = field(default_factory=LangChainConfig)
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """
        Load configuration from YAML file
        
        Args:
            path: Path to configuration file
            
        Returns:
            Config instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data is None:
            data = {}
        
        return cls._from_dict(data)

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables
        
        Environment variables should be prefixed with TNVED_
        Example: TNVED_MODEL_NAME, TNVED_DATABASE_PATH
        
        Returns:
            Config instance
        """
        config = cls()
        
        # Model configuration
        if model_name := os.getenv("TNVED_MODEL_NAME"):
            config.model.name = model_name
        if device := os.getenv("TNVED_MODEL_DEVICE"):
            config.model.device = device
        
        # Database configuration
        if db_path := os.getenv("TNVED_DATABASE_PATH"):
            config.database.path = db_path
        if collection_name := os.getenv("TNVED_COLLECTION_NAME"):
            config.database.collection_name = collection_name
        if default_source_name := os.getenv("TNVED_DEFAULT_SOURCE_NAME"):
            config.database.default_source_name = default_source_name
        
        # Processing configuration
        if batch_size := os.getenv("TNVED_BATCH_SIZE"):
            try:
                config.processing.batch_size = int(batch_size)
            except ValueError:
                pass  # Use default value
        
        # Search configuration
        if top_k := os.getenv("TNVED_DEFAULT_TOP_K"):
            try:
                config.search.default_top_k = int(top_k)
            except ValueError:
                pass  # Use default value
        if group_by_code := os.getenv("TNVED_GROUP_BY_CODE"):
            config.search.group_by_code = group_by_code.lower() in ("true", "1", "yes")
        if prioritize_reference := os.getenv("TNVED_PRIORITIZE_REFERENCE"):
            config.search.prioritize_reference = prioritize_reference.lower() in ("true", "1", "yes")
        if show_source_info := os.getenv("TNVED_SHOW_SOURCE_INFO"):
            config.search.show_source_info = show_source_info.lower() in ("true", "1", "yes")
        
        # Logging configuration
        if log_level := os.getenv("TNVED_LOG_LEVEL"):
            config.logging.level = log_level
        if log_file := os.getenv("TNVED_LOG_FILE"):
            config.logging.file = log_file
        
        # API configuration
        if api_enabled := os.getenv("TNVED_API_ENABLED"):
            config.api.enabled = api_enabled.lower() in ("true", "1", "yes")
        if api_host := os.getenv("TNVED_API_HOST"):
            config.api.host = api_host
        if api_port := os.getenv("TNVED_API_PORT"):
            try:
                config.api.port = int(api_port)
            except ValueError:
                pass
        
        return config

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """
        Create Config from dictionary
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Config instance
        """
        config = cls()
        
        # Model configuration
        if "model" in data:
            model_data = data["model"]
            if "name" in model_data:
                config.model.name = model_data["name"]
            if "device" in model_data:
                config.model.device = model_data["device"]
        
        # Database configuration
        if "database" in data:
            db_data = data["database"]
            if "path" in db_data:
                config.database.path = db_data["path"]
            if "collection_name" in db_data:
                config.database.collection_name = db_data["collection_name"]
            if "default_source_name" in db_data:
                config.database.default_source_name = db_data["default_source_name"]
        
        # Processing configuration
        if "processing" in data:
            proc_data = data["processing"]
            if "batch_size" in proc_data:
                config.processing.batch_size = proc_data["batch_size"]
        
        # Search configuration
        if "search" in data:
            search_data = data["search"]
            if "default_top_k" in search_data:
                config.search.default_top_k = search_data["default_top_k"]
            if "group_by_code" in search_data:
                config.search.group_by_code = search_data["group_by_code"]
            if "prioritize_reference" in search_data:
                config.search.prioritize_reference = search_data["prioritize_reference"]
            if "show_source_info" in search_data:
                config.search.show_source_info = search_data["show_source_info"]
        
        # Logging configuration
        if "logging" in data:
            log_data = data["logging"]
            if "level" in log_data:
                config.logging.level = log_data["level"]
            if "format" in log_data:
                config.logging.format = log_data["format"]
            if "file" in log_data:
                config.logging.file = log_data["file"]
        
        # API configuration
        if "api" in data:
            api_data = data["api"]
            if "enabled" in api_data:
                config.api.enabled = api_data["enabled"]
            if "host" in api_data:
                config.api.host = api_data["host"]
            if "port" in api_data:
                config.api.port = api_data["port"]
            
            # Auth configuration
            if "auth" in api_data:
                auth_data = api_data["auth"]
                if "enabled" in auth_data:
                    config.api.auth.enabled = auth_data["enabled"]
                if "api_keys" in auth_data:
                    config.api.auth.api_keys = auth_data["api_keys"]
            
            # CORS configuration
            if "cors" in api_data:
                cors_data = api_data["cors"]
                if "enabled" in cors_data:
                    config.api.cors.enabled = cors_data["enabled"]
                if "origins" in cors_data:
                    config.api.cors.origins = cors_data["origins"]
            
            # Rate limit configuration
            if "rate_limit" in api_data:
                rate_data = api_data["rate_limit"]
                if "requests_per_minute" in rate_data:
                    config.api.rate_limit.requests_per_minute = rate_data["requests_per_minute"]
        
        # LLM configuration
        if "llm" in data:
            llm_data = data["llm"]
            if "enabled" in llm_data:
                config.llm.enabled = llm_data["enabled"]
            if "provider" in llm_data:
                config.llm.provider = llm_data["provider"]
            
            # OpenAI configuration
            if "openai" in llm_data:
                openai_data = llm_data["openai"]
                if "api_key" in openai_data:
                    config.llm.openai.api_key = openai_data["api_key"]
                if "model" in openai_data:
                    config.llm.openai.model = openai_data["model"]
            
            # Local LLM configuration
            if "local" in llm_data:
                local_data = llm_data["local"]
                if "model_path" in local_data:
                    config.llm.local.model_path = local_data["model_path"]
        
        # LangChain configuration
        if "langchain" in data:
            lc_data = data["langchain"]
            if "enabled" in lc_data:
                config.langchain.enabled = lc_data["enabled"]
            if "agent_type" in lc_data:
                config.langchain.agent_type = lc_data["agent_type"]
            if "tools" in lc_data:
                config.langchain.tools = lc_data["tools"]
        
        # Sources configuration
        if "sources" in data:
            sources_data = data["sources"]
            
            # Reference source configuration
            if "reference" in sources_data:
                ref_data = sources_data["reference"]
                if "name" in ref_data:
                    config.sources.reference.name = ref_data["name"]
                if "display_name" in ref_data:
                    config.sources.reference.display_name = ref_data["display_name"]
            
            # Product source configuration
            if "product" in sources_data:
                prod_data = sources_data["product"]
                if "default_name" in prod_data:
                    config.sources.product.default_name = prod_data["default_name"]
                if "display_name" in prod_data:
                    config.sources.product.display_name = prod_data["display_name"]
        
        # Display configuration
        if "display" in data:
            display_data = data["display"]
            if "source_format" in display_data:
                config.display.source_format = display_data["source_format"]
            if "show_source_id" in display_data:
                config.display.show_source_id = display_data["show_source_id"]
            if "show_similarity_score" in display_data:
                config.display.show_similarity_score = display_data["show_similarity_score"]
            if "max_description_length" in display_data:
                config.display.max_description_length = display_data["max_description_length"]
        
        return config

    def validate(self) -> None:
        """
        Validate configuration values
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate device
        if self.model.device not in ("cpu", "cuda"):
            raise ValueError(f"Invalid device: {self.model.device}. Must be 'cpu' or 'cuda'")
        
        # Validate batch size
        if self.processing.batch_size <= 0:
            raise ValueError(f"Invalid batch_size: {self.processing.batch_size}. Must be positive")
        
        # Validate top_k
        if self.search.default_top_k <= 0:
            raise ValueError(f"Invalid default_top_k: {self.search.default_top_k}. Must be positive")
        
        # Validate log level
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.logging.level not in valid_levels:
            raise ValueError(f"Invalid log level: {self.logging.level}. Must be one of {valid_levels}")
        
        # Validate API port
        if not (1 <= self.api.port <= 65535):
            raise ValueError(f"Invalid API port: {self.api.port}. Must be between 1 and 65535")
        
        # Validate display format
        valid_formats = ("detailed", "compact", "minimal")
        if self.display.source_format not in valid_formats:
            raise ValueError(f"Invalid source_format: {self.display.source_format}. Must be one of {valid_formats}")
        
        # Validate max description length
        if self.display.max_description_length <= 0:
            raise ValueError(f"Invalid max_description_length: {self.display.max_description_length}. Must be positive")
        
        # Validate source names are not empty
        if not self.sources.reference.name.strip():
            raise ValueError("Reference source name cannot be empty")
        if not self.sources.product.default_name.strip():
            raise ValueError("Product default source name cannot be empty")
        if not self.database.default_source_name.strip():
            raise ValueError("Database default source name cannot be empty")
