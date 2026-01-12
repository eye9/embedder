# URL Data Management Guide

## Overview

This guide covers all aspects of managing URL-to-TNVED code mappings in the batch Excel processor system. It includes data loading procedures, file formats, URL normalization examples, and best practices for maintaining the URL database.

## URL Data Loading Procedures

### File Format Requirements

URL data must be provided in Excel format (.xlsx) with the following required columns:

| Column Name | Description | Example |
|-------------|-------------|---------|
| URL | Product URL from e-commerce site | `https://www.ozon.ru/product/sumka-123456/` |
| Code | TNVED code (10 digits) | `4202129000` |
| Description | Product description | `Женская сумка из натуральной кожи` |

### Optional Columns

| Column Name | Description | Example |
|-------------|-------------|---------|
| Source | Data source identifier | `ozon_catalog_2024` |
| Shop | E-commerce shop name | `ozon` |
| Category | Product category | `Bags & Accessories` |
| Price | Product price (for reference) | `5990.00` |
| Date_Added | When URL was collected | `2024-01-15` |

### Sample Excel File Structure

```
| URL                                           | Code       | Description                    | Source        |
|-----------------------------------------------|------------|--------------------------------|---------------|
| https://www.ozon.ru/product/sumka-123456/     | 4202129000 | Женская сумка из кожи         | ozon_2024     |
| https://market.yandex.ru/product/789012       | 6403999100 | Кроссовки мужские             | yandex_2024   |
| https://www.wildberries.ru/catalog/345678/    | 6204620000 | Платье женское летнее         | wb_2024       |
```

## Loading Data Using CLI

### Basic Data Loading

```bash
# Load URL data from Excel file
python url_database_manager_cli.py load-data \
  --file url_data.xlsx \
  --source "ozon_catalog_2024"

# Load with progress reporting
python url_database_manager_cli.py load-data \
  --file url_data.xlsx \
  --source "ozon_catalog_2024" \
  --verbose

# Load and validate data quality
python url_database_manager_cli.py load-data \
  --file url_data.xlsx \
  --source "ozon_catalog_2024" \
  --validate
```

### Batch Loading Multiple Files

```bash
# Load multiple files with different sources
python url_database_manager_cli.py load-data \
  --file ozon_data.xlsx \
  --source "ozon_2024"

python url_database_manager_cli.py load-data \
  --file yandex_data.xlsx \
  --source "yandex_market_2024"

python url_database_manager_cli.py load-data \
  --file wildberries_data.xlsx \
  --source "wildberries_2024"
```

### Loading with Data Validation

```bash
# Validate data before loading
python validate_url_data.py --file url_data.xlsx --report validation_report.txt

# Load only if validation passes
python url_database_manager_cli.py load-data \
  --file url_data.xlsx \
  --source "validated_data_2024" \
  --validate \
  --skip-invalid
```

## URL Normalization Examples

### Ozon URLs

**Original URLs**:
```
https://www.ozon.ru/product/sumka-zhenskaya-123456/?asb=1&from=category
http://ozon.ru/product/sumka-zhenskaya-123456/
https://ozon.ru/product/sumka-zhenskaya-123456/?utm_source=google
```

**Normalized URL**:
```
https://ozon.ru/product/123456/
```

**Normalization Rules**:
- Remove `www.` subdomain
- Extract product ID from path
- Remove all query parameters
- Standardize to `https://ozon.ru/product/{id}/`

### Yandex Market URLs

**Original URLs**:
```
https://market.yandex.ru/product/789012?hid=12345&track=tabs
https://market.yandex.ru/product/789012/reviews
http://market.yandex.ru/product/789012
```

**Normalized URL**:
```
https://market.yandex.ru/product/789012
```

**Normalization Rules**:
- Extract product ID from path
- Remove query parameters and path suffixes
- Standardize to `https://market.yandex.ru/product/{id}`

### Wildberries URLs

**Original URLs**:
```
https://www.wildberries.ru/catalog/345678/detail.aspx?targetUrl=XS
https://wildberries.ru/catalog/345678/detail.aspx
http://www.wildberries.ru/catalog/345678/
```

**Normalized URL**:
```
https://wildberries.ru/catalog/345678/
```

**Normalization Rules**:
- Remove `www.` subdomain
- Extract product ID from catalog path
- Remove detail.aspx and query parameters
- Standardize to `https://wildberries.ru/catalog/{id}/`

### AliExpress URLs

**Original URLs**:
```
https://aliexpress.ru/item/4000123456789.html?spm=a2g0o.productlist
https://www.aliexpress.com/item/4000123456789.html?algo_pvid=abc123
http://aliexpress.ru/item/4000123456789.html
```

**Normalized URL**:
```
https://aliexpress.ru/item/4000123456789.html
```

**Normalization Rules**:
- Prefer `.ru` domain over `.com`
- Extract item ID from path
- Remove all query parameters
- Standardize to `https://aliexpress.ru/item/{id}.html`

### Custom Shop URLs

For shops not in the predefined list, generic normalization is applied:

**Original URL**:
```
https://example-shop.com/products/item-123?ref=homepage&utm_campaign=sale#reviews
```

**Normalized URL**:
```
https://example-shop.com/products/item-123
```

**Generic Rules**:
- Convert `http` to `https`
- Remove query parameters (`?...`)
- Remove fragments (`#...`)
- Preserve domain and path structure

## Database Management Operations

### Viewing Database Statistics

```bash
# Get overall statistics
python url_database_manager_cli.py stats

# Get detailed statistics by source
python url_database_manager_cli.py stats --by-source

# Get statistics by domain
python url_database_manager_cli.py stats --by-domain

# Export statistics to JSON
python url_database_manager_cli.py stats --format json > url_stats.json
```

### Database Health Checks

```bash
# Basic health check
python url_database_manager_cli.py health-check

# Comprehensive health check with validation
python url_database_manager_cli.py health-check --validate-data

# Check for duplicate URLs
python url_database_manager_cli.py health-check --check-duplicates

# Check for invalid TNVED codes
python url_database_manager_cli.py health-check --validate-codes
```

### Data Export and Backup

```bash
# Export all URL data to Excel
python url_database_manager_cli.py export \
  --output url_backup_$(date +%Y%m%d).xlsx

# Export data from specific source
python url_database_manager_cli.py export \
  --source "ozon_2024" \
  --output ozon_backup.xlsx

# Export data for specific domain
python url_database_manager_cli.py export \
  --domain "ozon.ru" \
  --output ozon_domain_backup.xlsx

# Export with date range
python url_database_manager_cli.py export \
  --date-from "2024-01-01" \
  --date-to "2024-12-31" \
  --output url_data_2024.xlsx
```

### Data Cleanup Operations

```bash
# Remove duplicate URLs (keep most recent)
python url_database_manager_cli.py cleanup --remove-duplicates

# Remove URLs from specific source
python url_database_manager_cli.py cleanup \
  --source "old_data_2023"

# Remove URLs matching pattern
python url_database_manager_cli.py cleanup \
  --url-pattern "*.test.com/*"

# Remove URLs with invalid TNVED codes
python url_database_manager_cli.py cleanup --invalid-codes

# Dry run (show what would be deleted without deleting)
python url_database_manager_cli.py cleanup \
  --remove-duplicates \
  --dry-run
```

## Data Quality Management

### Data Validation

```bash
# Validate URL data file before loading
python validate_url_data.py \
  --file url_data.xlsx \
  --report validation_report.txt

# Validate existing database
python validate_url_data.py \
  --database \
  --report database_validation.txt

# Validate specific source data
python validate_url_data.py \
  --database \
  --source "ozon_2024" \
  --report ozon_validation.txt
```

### Quality Checks

```bash
# Check data quality metrics
python utils/url_data_quality_checker.py \
  --file url_data.xlsx \
  --output quality_report.json

# Check for common issues
python utils/url_data_quality_checker.py \
  --database \
  --check-duplicates \
  --check-invalid-urls \
  --check-invalid-codes

## For PWSH
  $env:PYTHONPATH = "."; python utils/url_data_quality_checker.py confirmed_120K.xlsx --database --check-duplicates --check-invalid-urls --check-invalid-codes 
```

### Data Quality Reports

The quality checker generates reports with the following metrics:

- **URL Validity**: Percentage of valid URLs
- **Code Validity**: Percentage of valid TNVED codes
- **Duplicate Rate**: Percentage of duplicate URLs
- **Normalization Success**: URLs successfully normalized
- **Shop Coverage**: Distribution across e-commerce shops
- **Data Completeness**: Missing required fields

Example quality report:
```json
{
  "total_records": 10000,
  "url_validity": {
    "valid": 9850,
    "invalid": 150,
    "validity_rate": 0.985
  },
  "code_validity": {
    "valid": 9900,
    "invalid": 100,
    "validity_rate": 0.99
  },
  "duplicates": {
    "total_duplicates": 50,
    "duplicate_rate": 0.005
  },
  "shop_distribution": {
    "ozon": 4000,
    "yandex_market": 3000,
    "wildberries": 2500,
    "aliexpress": 500
  }
}
```

## Best Practices

### Data Collection Best Practices

1. **Consistent Source Naming**:
   ```bash
   # Good: Use descriptive, dated source names
   --source "ozon_catalog_2024_q1"
   --source "yandex_market_electronics_2024"
   
   # Avoid: Generic or unclear names
   --source "data"
   --source "urls"
   ```

2. **Regular Data Updates**:
   ```bash
   # Schedule regular updates
   # Daily updates for active catalogs
   0 2 * * * python url_database_manager_cli.py load-data --file daily_updates.xlsx --source "daily_$(date +%Y%m%d)"
   
   # Weekly cleanup
   0 3 * * 0 python url_database_manager_cli.py cleanup --remove-duplicates
   ```

3. **Data Validation Before Loading**:
   ```bash
   # Always validate before loading large datasets
   python validate_url_data.py --file large_dataset.xlsx --report validation.txt
   if [ $? -eq 0 ]; then
     python url_database_manager_cli.py load-data --file large_dataset.xlsx --source "validated_data"
   fi
   ```

### Database Maintenance Best Practices

1. **Regular Backups**:
   ```bash
   # Daily backup script
   #!/bin/bash
   BACKUP_DIR="./backups/url_database"
   DATE=$(date +%Y%m%d)
   
   mkdir -p $BACKUP_DIR
   python url_database_manager_cli.py export --output "$BACKUP_DIR/url_backup_$DATE.xlsx"
   
   # Keep only last 30 days of backups
   find $BACKUP_DIR -name "url_backup_*.xlsx" -mtime +30 -delete
   ```

2. **Performance Monitoring**:
   ```bash
   # Monitor database size and performance
   python url_database_manager_cli.py stats --format json | jq '.total_records'
   python url_database_manager_cli.py health-check --performance
   ```

3. **Data Quality Monitoring**:
   ```bash
   # Weekly data quality check
   python utils/url_data_quality_checker.py \
     --database \
     --output "quality_reports/weekly_$(date +%Y%m%d).json"
   ```

### URL Collection Best Practices

1. **URL Format Consistency**:
   - Always include protocol (`https://`)
   - Use canonical URLs when possible
   - Avoid URLs with session parameters
   - Prefer product-specific URLs over category URLs

2. **TNVED Code Accuracy**:
   - Verify codes against official TNVED classifier
   - Use 10-digit format consistently
   - Double-check codes for high-value products
   - Document code assignment reasoning

3. **Description Quality**:
   - Use clear, descriptive product names
   - Include key product characteristics
   - Maintain consistent language (Russian for TNVED)
   - Avoid marketing language and special characters

### Troubleshooting Data Issues

#### Issue: High Duplicate Rate

**Diagnosis**:
```bash
python url_database_manager_cli.py health-check --check-duplicates --verbose
```

**Solutions**:
1. Review data collection process for duplicate sources
2. Implement deduplication in data preparation
3. Use `--remove-duplicates` cleanup option
4. Update source naming conventions

#### Issue: Low URL Validity Rate

**Diagnosis**:
```bash
python validate_url_data.py --file data.xlsx --report validation.txt
grep -i "invalid url" validation.txt
```

**Solutions**:
1. Review URL collection methods
2. Update URL normalization patterns
3. Filter out non-product URLs
4. Validate URLs before collection

#### Issue: TNVED Code Mismatches

**Diagnosis**:
```bash
python utils/url_data_quality_checker.py --database --check-invalid-codes
```

**Solutions**:
1. Cross-reference with official TNVED classifier
2. Review code assignment process
3. Implement automated code validation
4. Train data collectors on TNVED classification

## Integration with Processing System

### Automatic Data Loading

Configure automatic loading of new URL data:

```yaml
# config.yaml
url_processing:
  auto_loading:
    enabled: true
    watch_directory: "./url_data_incoming"
    file_pattern: "*.xlsx"
    default_source_prefix: "auto_"
    validation_required: true
```

### Processing Integration

URL data automatically integrates with the batch processing system:

1. **File Upload**: System detects URL columns in uploaded Excel files
2. **URL Matching**: System attempts URL matches before semantic search
3. **Result Reporting**: Processing results indicate match source (URL vs semantic)
4. **Statistics**: System tracks URL match rates and performance

### Monitoring Integration

```bash
# Monitor URL processing effectiveness
python -c "
from batch_processor.services.monitoring import get_url_processing_stats
stats = get_url_processing_stats()
print(f'URL Match Rate: {stats.url_match_rate:.2%}')
print(f'Database Size: {stats.total_url_records:,} records')
print(f'Average Lookup Time: {stats.average_lookup_time_ms:.1f}ms')
"
```

This comprehensive guide provides all the information needed to effectively manage URL data in the batch Excel processor system. Follow these procedures and best practices to maintain a high-quality URL database that maximizes the accuracy of TNVED code matching.