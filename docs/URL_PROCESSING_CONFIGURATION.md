# URL Processing Configuration Guide

## Overview

The URL-based code matching system extends the batch Excel processor with the ability to find TNVED codes by matching product URLs from e-commerce sites. This guide covers all configuration options, deployment scenarios, and troubleshooting for URL processing features.

## Environment Variables

### Core URL Processing Variables

```bash
# Enable/disable URL processing feature
URL_PROCESSING_ENABLED=true

# URL search priority: "first", "only", or "disabled"
# - first: Try URL search first, then semantic search as fallback
# - only: Use only URL search, no semantic fallback  
# - disabled: Use only semantic search, no URL processing
URL_PRIORITY=first

# Timeout for URL database queries (seconds)
URL_TIMEOUT_SECONDS=5.0

# URL database collection name in ChromaDB
URL_DATABASE_COLLECTION=url_tnved_mapping

# Batch size for URL database operations
URL_BATCH_SIZE=100
```

### URL Normalization Variables

```bash
# Enable URL normalization
URL_NORMALIZATION_ENABLED=true

# Remove query parameters (?param=value) from URLs
URL_REMOVE_QUERY_PARAMS=true

# Remove fragments (#fragment) from URLs
URL_REMOVE_FRAGMENTS=true

# Convert http to https for consistency
URL_NORMALIZE_PROTOCOL=true

# Supported e-commerce shops (comma-separated)
URL_SUPPORTED_SHOPS=ozon,yandex_market,wildberries,aliexpress

# Maximum allowed URL length
URL_MAX_LENGTH=2048
```

### URL Security Variables

```bash
# Enable URL security features
URL_SECURITY_ENABLED=true

# Validate URLs when processing input
URL_VALIDATE_ON_INPUT=true

# Sanitize URLs before database storage
URL_SANITIZE_FOR_STORAGE=true

# Mask sensitive parameters in logs
URL_MASK_SENSITIVE_PARAMS=true

# Block URLs with malicious patterns
URL_BLOCK_MALICIOUS_PATTERNS=true
```

### URL Database Management Variables

```bash
# Enable URL processing statistics tracking
URL_ENABLE_STATISTICS=true

# Automatically clean duplicate URLs
URL_AUTO_CLEANUP_DUPLICATES=false

# URL database backup directory
URL_BACKUP_DIR=./backups/url_database

# URL data validation on startup
URL_VALIDATE_ON_STARTUP=true
```

## Configuration File Examples

### Development Configuration

```yaml
# config_development.yaml
url_processing:
  enabled: true
  priority: "first"
  timeout_seconds: 10.0  # Longer timeout for development
  
  normalization:
    enabled: true
    remove_query_params: true
    remove_fragments: true
    normalize_protocol: true
    supported_shops:
      - "ozon"
      - "yandex_market"
      - "wildberries"
  
  security:
    enabled: true
    validate_on_input: true
    sanitize_for_storage: true
    mask_sensitive_params: true
    max_url_length: 2048
  
  database:
    collection_name: "dev_url_tnved_mapping"
    batch_size: 50  # Smaller batches for development
    enable_statistics: true
    auto_cleanup_duplicates: true

logging:
  level: "DEBUG"  # Verbose logging for development
  sensitive_data_masking: true
```

### Production Configuration

```yaml
# config_production.yaml
url_processing:
  enabled: true
  priority: "first"
  timeout_seconds: 5.0  # Strict timeout for production
  
  normalization:
    enabled: true
    remove_query_params: true
    remove_fragments: true
    normalize_protocol: true
    supported_shops:
      - "ozon"
      - "yandex_market"
      - "wildberries"
      - "aliexpress"
  
  security:
    enabled: true
    validate_on_input: true
    sanitize_for_storage: true
    mask_sensitive_params: true
    max_url_length: 2048
    block_malicious_patterns: true
  
  database:
    collection_name: "url_tnved_mapping"
    batch_size: 200  # Larger batches for production efficiency
    enable_statistics: true
    auto_cleanup_duplicates: false  # Manual cleanup in production

logging:
  level: "INFO"  # Standard logging for production
  sensitive_data_masking: true
  file_enabled: true
  file_path: "./logs/url_processing.log"
```

### URL-Only Processing Configuration

```yaml
# config_url_only.yaml - For scenarios where only URL matching is desired
url_processing:
  enabled: true
  priority: "only"  # No semantic fallback
  timeout_seconds: 3.0  # Shorter timeout since no fallback
  
  normalization:
    enabled: true
    remove_query_params: true
    remove_fragments: true
    normalize_protocol: true
    supported_shops:
      - "ozon"
      - "yandex_market"
      - "wildberries"
      - "aliexpress"
  
  security:
    enabled: true
    validate_on_input: true
    sanitize_for_storage: true
    max_url_length: 2048
  
  database:
    collection_name: "url_tnved_mapping"
    batch_size: 100
    enable_statistics: true

# Disable semantic search components to save resources
search:
  default_top_k: 1  # Minimal semantic search config
model:
  device: "cpu"  # Can use CPU since semantic search is disabled
```

### Semantic-Only Configuration (URL Disabled)

```yaml
# config_semantic_only.yaml - Fallback configuration without URL processing
url_processing:
  enabled: false  # Completely disable URL processing
  priority: "disabled"

# Standard semantic search configuration
model:
  name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  device: "cuda"

search:
  default_top_k: 5
  group_by_code: false
  prioritize_reference: true

processing:
  batch_size: 200
  confidence_threshold: 0.7
```

## Deployment Scenarios

### Scenario 1: Full Hybrid Processing (Recommended)

**Use Case**: Maximum accuracy with URL matching and semantic fallback

**Configuration**:
```bash
URL_PROCESSING_ENABLED=true
URL_PRIORITY=first
URL_TIMEOUT_SECONDS=5.0
URL_ENABLE_STATISTICS=true
```

**Benefits**:
- Highest accuracy for products with known URLs
- Graceful fallback to semantic search
- Comprehensive processing statistics

**Resource Requirements**:
- GPU recommended for semantic search
- Additional ChromaDB collection for URLs
- ~20% increase in processing time

### Scenario 2: URL-Only Processing

**Use Case**: High-confidence URL database with no semantic fallback needed

**Configuration**:
```bash
URL_PROCESSING_ENABLED=true
URL_PRIORITY=only
URL_TIMEOUT_SECONDS=3.0
URL_ENABLE_STATISTICS=true
```

**Benefits**:
- Fastest processing for known URLs
- Minimal resource usage
- Clear success/failure results

**Limitations**:
- No fallback for unknown URLs
- Requires comprehensive URL database

### Scenario 3: Gradual Migration

**Use Case**: Testing URL processing alongside existing semantic search

**Configuration**:
```bash
URL_PROCESSING_ENABLED=true
URL_PRIORITY=first
URL_TIMEOUT_SECONDS=10.0  # Longer timeout for testing
URL_ENABLE_STATISTICS=true
URL_AUTO_CLEANUP_DUPLICATES=true  # Clean test data
```

**Benefits**:
- Safe testing environment
- Detailed statistics for evaluation
- Easy rollback to semantic-only

### Scenario 4: High-Security Environment

**Use Case**: Strict security requirements for URL processing

**Configuration**:
```bash
URL_PROCESSING_ENABLED=true
URL_PRIORITY=first
URL_SECURITY_ENABLED=true
URL_VALIDATE_ON_INPUT=true
URL_SANITIZE_FOR_STORAGE=true
URL_MASK_SENSITIVE_PARAMS=true
URL_BLOCK_MALICIOUS_PATTERNS=true
URL_MAX_LENGTH=1024  # Stricter limit
```

**Additional Security Measures**:
- Regular URL database audits
- Encrypted ChromaDB storage
- Network isolation for URL processing
- Comprehensive logging and monitoring

## Performance Tuning

### URL Database Optimization

```yaml
url_processing:
  database:
    batch_size: 500  # Increase for better throughput
    enable_statistics: false  # Disable if not needed
    auto_cleanup_duplicates: true  # Reduce database size
  
  timeout_seconds: 2.0  # Reduce for faster fallback
```

### Memory Optimization

```yaml
processing:
  chunk_size: 500  # Reduce if memory constrained

url_processing:
  database:
    batch_size: 50  # Smaller batches for limited memory
```

### CPU vs GPU Configuration

**CPU-Optimized** (when GPU not available):
```yaml
model:
  device: "cpu"
processing:
  batch_size: 50  # Smaller batches for CPU
url_processing:
  timeout_seconds: 10.0  # Longer timeout for CPU processing
```

**GPU-Optimized**:
```yaml
model:
  device: "cuda"
processing:
  batch_size: 200  # Larger batches for GPU
url_processing:
  timeout_seconds: 5.0  # Standard timeout with GPU acceleration
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: URL Processing Not Working

**Symptoms**:
- All results show "Used semantic search (URL search disabled)"
- No URL matches found despite having URL data

**Diagnosis**:
```bash
# Check if URL processing is enabled
grep -r "URL_PROCESSING_ENABLED" .env
grep -r "enabled.*true" config*.yaml | grep url

# Check URL database collection
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db')
collections = client.list_collections()
print([c.name for c in collections])
"
```

**Solutions**:
1. Verify `URL_PROCESSING_ENABLED=true` in environment
2. Check URL database collection exists and has data
3. Verify configuration file has `url_processing.enabled: true`
4. Restart application after configuration changes

#### Issue 2: URL Normalization Failures

**Symptoms**:
- URLs not matching despite being similar
- "URL format is invalid" errors in logs

**Diagnosis**:
```bash
# Test URL normalization
python -c "
from services.url_normalizer import URLNormalizer
normalizer = URLNormalizer()
test_url = 'https://www.ozon.ru/product/example-123456/?param=value'
result = normalizer.normalize_url(test_url)
print(f'Original: {test_url}')
print(f'Normalized: {result.normalized_url if result else None}')
"
```

**Solutions**:
1. Check supported shops configuration
2. Verify URL format matches expected patterns
3. Update shop patterns for new e-commerce sites
4. Enable debug logging to see normalization details

#### Issue 3: URL Database Performance Issues

**Symptoms**:
- Slow URL lookups
- Timeout errors in URL processing
- High memory usage

**Diagnosis**:
```bash
# Check database size and performance
python url_database_manager_cli.py stats
python url_database_manager_cli.py health-check
```

**Solutions**:
1. Increase `URL_TIMEOUT_SECONDS` for slow systems
2. Reduce `URL_BATCH_SIZE` for memory constraints
3. Enable `URL_AUTO_CLEANUP_DUPLICATES` to reduce database size
4. Consider database optimization or migration

#### Issue 4: Security Validation Errors

**Symptoms**:
- URLs rejected with security errors
- "Malicious pattern detected" in logs

**Diagnosis**:
```bash
# Check security logs
grep -i "security\|malicious\|blocked" logs/batch_processor.log
grep -i "url.*error" logs/batch_processor.log
```

**Solutions**:
1. Review and update malicious pattern detection
2. Whitelist legitimate URL patterns
3. Adjust `URL_MAX_LENGTH` if needed
4. Temporarily disable `URL_BLOCK_MALICIOUS_PATTERNS` for testing

#### Issue 5: Configuration Not Loading

**Symptoms**:
- Default values used instead of configured values
- Configuration changes not taking effect

**Diagnosis**:
```bash
# Check configuration file loading
python -c "
from batch_processor.config.loader import load_config
config = load_config()
print('URL Processing Enabled:', config.get('url_processing', {}).get('enabled', 'NOT SET'))
print('URL Priority:', config.get('url_processing', {}).get('priority', 'NOT SET'))
"
```

**Solutions**:
1. Verify configuration file path and permissions
2. Check YAML syntax with online validator
3. Ensure environment variables are properly set
4. Restart application after configuration changes

### Debug Commands

#### Check URL Processing Status
```bash
# Verify URL processing configuration
python -c "
from batch_processor.config.settings import get_url_config
config = get_url_config()
print('Enabled:', config.enabled)
print('Priority:', config.priority)
print('Timeout:', config.timeout_seconds)
"
```

#### Test URL Normalization
```bash
# Test URL normalization for specific URLs
python -c "
from services.url_normalizer import URLNormalizer
normalizer = URLNormalizer()
urls = [
    'https://www.ozon.ru/product/example-123456/?param=value',
    'https://market.yandex.ru/product/789012',
    'https://www.wildberries.ru/catalog/345678/'
]
for url in urls:
    result = normalizer.normalize_url(url)
    print(f'{url} -> {result.normalized_url if result else \"INVALID\"}')"
```

#### Check URL Database Health
```bash
# Check URL database statistics and health
python url_database_manager_cli.py stats
python url_database_manager_cli.py health-check
python url_database_manager_cli.py validate-data
```

#### Monitor URL Processing Performance
```bash
# Monitor URL processing in real-time
tail -f logs/batch_processor.log | grep -i "url\|processing\|match"
```

### Performance Monitoring

#### Key Metrics to Monitor

1. **URL Match Rate**: Percentage of URLs that find matches
2. **Processing Time**: Average time for URL lookups
3. **Fallback Rate**: How often semantic search is used
4. **Error Rate**: URL validation and processing errors
5. **Database Size**: Growth of URL database over time

#### Monitoring Commands

```bash
# Get processing statistics
python -c "
from batch_processor.services.monitoring import get_url_processing_stats
stats = get_url_processing_stats()
print(f'URL Match Rate: {stats.url_match_rate:.2%}')
print(f'Average Lookup Time: {stats.average_url_lookup_time_ms:.2f}ms')
print(f'Fallback Rate: {stats.semantic_fallbacks / stats.total_rows:.2%}')
"

# Monitor database growth
python url_database_manager_cli.py stats --format json | jq '.total_records'
```

## Migration Guide

### Migrating from Semantic-Only to Hybrid Processing

1. **Backup Current Configuration**:
   ```bash
   cp config.yaml config_backup_$(date +%Y%m%d).yaml
   cp .env .env_backup_$(date +%Y%m%d)
   ```

2. **Update Configuration**:
   ```bash
   # Add URL processing variables to .env
   echo "URL_PROCESSING_ENABLED=true" >> .env
   echo "URL_PRIORITY=first" >> .env
   echo "URL_TIMEOUT_SECONDS=5.0" >> .env
   ```

3. **Load Initial URL Data**:
   ```bash
   python url_database_manager_cli.py load-data \
     --file url_data.xlsx \
     --source "initial_migration"
   ```

4. **Test Configuration**:
   ```bash
   python -c "from batch_processor.config.loader import load_config; print(load_config()['url_processing'])"
   ```

5. **Monitor Initial Processing**:
   ```bash
   # Process a small test file first
   python start_batch_processor.py --file test_small.xlsx --mode all
   ```

### Rolling Back URL Processing

1. **Disable URL Processing**:
   ```bash
   sed -i 's/URL_PROCESSING_ENABLED=true/URL_PROCESSING_ENABLED=false/' .env
   ```

2. **Restart Application**:
   ```bash
   # Restart web application
   pkill -f "start_batch_web.py"
   python start_batch_web.py &
   ```

3. **Verify Semantic-Only Mode**:
   ```bash
   # Check that URL processing is disabled
   curl -X POST http://localhost:8000/api/validate-file \
     -F "file=@test.xlsx" | jq '.has_url_column'
   ```

This comprehensive configuration guide covers all aspects of URL processing setup, deployment, and troubleshooting. Use it as a reference for implementing and maintaining URL-based code matching in your environment.