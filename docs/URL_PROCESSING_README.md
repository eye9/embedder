# URL Processing Infrastructure for TNVED Code Matching

This document describes the URL processing infrastructure that has been implemented as part of Task 1 for the URL-based code matching system.

## Overview

The URL processing infrastructure provides the foundation for matching TNVED codes based on product URLs from e-commerce sites. It includes URL normalization, security validation, database management, and matching capabilities.

## Components Implemented

### 1. URL Normalizer (`services/url_normalizer.py`)

**Purpose**: Normalizes URLs for consistent storage and matching

**Features**:
- Removes query parameters and URL fragments
- Standardizes protocol to HTTPS
- Extracts product IDs from known shop patterns
- Supports shop-specific normalization rules

**Supported Shops**:
- Ozon (`ozon.ru`)
- Yandex Market (`market.yandex.ru`)
- Wildberries (`wildberries.ru`)
- AliExpress (`aliexpress.ru`, `aliexpress.com`)

**Example Usage**:
```python
from services.url_normalizer import URLNormalizer

normalizer = URLNormalizer()
result = normalizer.normalize_url("https://ozon.ru/product/123456/?ref=abc")
print(result.normalized_url)  # https://ozon.ru/product/123456/
print(result.shop_type)       # ozon
print(result.product_id)      # 123456
```

### 2. URL Database Manager (`services/url_database_manager.py`)

**Purpose**: Manages URL-to-TNVED code mappings in ChromaDB

**Features**:
- Stores URL records with normalized URLs as keys
- Supports batch loading from Excel files
- Handles duplicate URL updates
- Provides statistics and management operations
- Integrates with existing ChromaDB infrastructure

**Example Usage**:
```python
from services.url_database_manager import URLDatabaseManager
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
db_manager = URLDatabaseManager(client)

# Add a URL record
success = db_manager.add_url_record(
    url="https://ozon.ru/product/123456/",
    tnved_code="1234567890",
    description="Test Product",
    source_name="manual_entry"
)

# Find by URL
record = db_manager.find_by_url("https://ozon.ru/product/123456/")
if record:
    print(f"Found code: {record.tnved_code}")
```

### 3. URL Matcher (`services/url_matcher.py`)

**Purpose**: Performs URL-based TNVED code matching

**Features**:
- Exact URL lookup with normalization
- URL validation and suggestion
- Timeout handling for database queries
- Security sanitization for logging

**Example Usage**:
```python
from services.url_matcher import URLMatcher

matcher = URLMatcher(db_manager, timeout_seconds=5.0)
result = matcher.find_code_by_url("https://ozon.ru/product/123456/")

if result.found:
    print(f"Found TNVED code: {result.tnved_code}")
    print(f"Description: {result.description}")
```

### 4. URL Security (`services/url_security.py`)

**Purpose**: Provides security validation and sanitization for URLs

**Features**:
- Input validation against malicious patterns
- URL sanitization for safe storage and logging
- Parameter masking for sensitive data
- SQL injection prevention

**Example Usage**:
```python
from services.url_security import URLSecurity

security = URLSecurity()
validation = security.validate_url_security("https://example.com/product/123")

if validation["is_safe"]:
    sanitized = security.sanitize_url_for_storage(url)
    print(f"Safe to store: {sanitized}")
```

### 5. URL Configuration (`services/url_config.py`)

**Purpose**: Configuration management for URL processing

**Features**:
- Environment variable support
- YAML configuration integration
- Validation of configuration values
- Priority mode settings

**Configuration Options**:
- `enabled`: Enable/disable URL processing
- `priority`: URL search priority ("first", "only", "disabled")
- `timeout_seconds`: Timeout for URL database queries
- `normalization`: URL normalization settings
- `security`: Security validation settings
- `database`: URL database settings

### 6. URL Processor Factory (`services/url_processor_factory.py`)

**Purpose**: Factory for creating and configuring URL processing components

**Features**:
- Centralized component creation
- Integration with existing ChromaDB infrastructure
- Setup validation
- Component information reporting

**Example Usage**:
```python
from services.url_processor_factory import URLProcessorFactory
from services.url_config import URLProcessingConfig

config = URLProcessingConfig()
components = URLProcessorFactory.create_complete_url_processor("./chroma_db", config)

# Access components
normalizer = components["normalizer"]
db_manager = components["db_manager"]
matcher = components["matcher"]
```

### 7. URL Data Loader Utility (`utils/url_data_loader.py`)

**Purpose**: Command-line utility for managing URL data

**Features**:
- Load URL data from Excel files
- Database statistics reporting
- Record deletion by source
- Export functionality

**Usage Examples**:
```bash
# Load URL data from Excel
python -m utils.url_data_loader load data.xlsx "source_name"

# Show database statistics
python -m utils.url_data_loader stats

# Delete records by source
python -m utils.url_data_loader delete "source_name" --confirm

# Export database to Excel
python -m utils.url_data_loader export output.xlsx
```

## Configuration

### Environment Variables

URL processing can be configured using environment variables with the `TNVED_URL_` prefix:

```bash
# Enable URL processing
export TNVED_URL_ENABLED=true

# Set priority mode
export TNVED_URL_PRIORITY=first

# Set timeout
export TNVED_URL_TIMEOUT_SECONDS=5.0

# Configure security
export TNVED_URL_SECURITY_ENABLED=true
export TNVED_URL_MAX_LENGTH=2048

# Configure database
export TNVED_URL_COLLECTION_NAME=url_tnved_mapping
export TNVED_URL_BATCH_SIZE=100
```

### YAML Configuration

See `config_url_example.yaml` for a complete configuration example.

## Security Features

The URL processing infrastructure includes several security features:

1. **Malicious Pattern Detection**: Detects and blocks URLs with suspicious patterns
2. **Credential Removal**: Automatically removes authentication credentials from URLs
3. **Parameter Masking**: Masks sensitive parameters in logs
4. **Input Validation**: Validates URL format and structure
5. **Length Limits**: Enforces maximum URL length limits
6. **Sanitization**: Sanitizes URLs for safe storage and logging

## Integration with Existing System

The URL processing infrastructure is designed to integrate seamlessly with the existing TNVED embedder system:

- **ChromaDB Integration**: Uses the same ChromaDB client and follows existing patterns
- **Configuration Extension**: Extends the existing configuration system
- **Logging Integration**: Uses the existing logging infrastructure
- **Error Handling**: Follows existing error handling patterns

## Testing

Basic functionality can be tested using the provided test scripts:

```bash
# Run basic component tests
python test_url_basic.py

# Run comprehensive tests (may have file locking issues on Windows)
python test_url_infrastructure.py
```

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **11.1-11.5**: URL normalization with shop-specific patterns
- **12.1-12.5**: Shop-specific normalization rules
- **10.1, 10.2, 10.5**: Security validation and sanitization
- **2.1-2.6**: URL database management (foundation)
- **5.1-5.5**: Database management operations (foundation)

## Next Steps

This infrastructure provides the foundation for the complete URL-based code matching system. The next tasks will build upon these components to create:

1. Hybrid selector system combining URL and semantic search
2. Excel processing enhancements for URL support
3. Integration with the existing batch processor
4. Web interface updates for URL processing

## Files Created

- `services/url_normalizer.py` - URL normalization component
- `services/url_database_manager.py` - URL database management
- `services/url_matcher.py` - URL-based code matching
- `services/url_security.py` - Security validation and sanitization
- `services/url_config.py` - Configuration management
- `services/url_processor_factory.py` - Component factory
- `utils/url_data_loader.py` - CLI utility for URL data management
- `test_url_basic.py` - Basic functionality tests
- `test_url_infrastructure.py` - Comprehensive tests
- `config_url_example.yaml` - Example configuration
- `URL_PROCESSING_README.md` - This documentation