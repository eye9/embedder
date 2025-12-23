# Design Document

## Overview

This design extends the existing ТНВЭД Embedder System to support loading and searching product data with pre-assigned ТНВЭД codes. The solution maintains backward compatibility while adding new capabilities to improve code selection accuracy through real-world product examples.

The design uses a unified collection approach where both reference records (official ТНВЭД descriptions) and product records (real products with assigned codes) coexist in the same ChromaDB collection, differentiated by metadata.

## Architecture

### Current Architecture
```
Excel File → TNVEDLoader → TextNormalizer → EmbeddingGenerator → ChromaDBManager
                                                                        ↓
Query → TNVEDSearcher → TextNormalizer → EmbeddingGenerator → ChromaDBManager
```

### Enhanced Architecture
```
Excel File (Reference) → TNVEDLoader → TextNormalizer → EmbeddingGenerator → ChromaDBManager
Excel File (Product)   → ProductLoader → TextNormalizer → EmbeddingGenerator → ChromaDBManager
                                                                                      ↓
Query → EnhancedSearcher → TextNormalizer → EmbeddingGenerator → ChromaDBManager
```

## Components and Interfaces

### Enhanced Data Models

#### Extended SearchResult
```python
@dataclass
class SearchResult:
    code: str
    description: str
    normalized_text: str
    similarity_score: float
    source_type: str  # NEW: "reference" or "product"
    source_name: Optional[str] = None  # NEW: source identifier
    source_id: Optional[str] = None    # NEW: ID in source system
```

#### ProductRecord
```python
@dataclass
class ProductRecord:
    code: str
    description: str
    normalized_text: str
    source_name: str
    source_id: Optional[str] = None
```

### Enhanced ChromaDBManager

#### ID Generation Strategy
- **Reference records**: Use ТНВЭД code as ID (existing behavior)
- **Product records**: Use format `{code}_{counter}` for uniqueness

#### Metadata Structure
```python
# Reference record metadata
{
    "description": "КОФЕ НЕЖАРЕНЫЙ...",
    "code": "0901110000",
    "source_type": "reference",
    "source_name": "tnved_official"
}

# Product record metadata  
{
    "description": "Кофе арабика зерновой 1кг",
    "code": "0901110000", 
    "source_type": "product",
    "source_name": "customs_2024_q1",
    "source_id": "декларация_12345"
}
```

### ProductLoader Service

```python
class ProductLoader:
    def __init__(
        self,
        db_path: str,
        normalizer: TextNormalizer,
        embedder: EmbeddingGenerator,
        batch_size: int = 100,
        collection_name: str = "tnved"
    )
    
    def load_from_excel(
        self,
        file_path: str,
        source_name: str,
        source_type: str = "product"
    ) -> int
    
    def _generate_unique_id(self, code: str) -> str
    def _process_batch(self, batch_df: pd.DataFrame, source_name: str) -> int
```

### EnhancedSearcher Service

```python
class EnhancedSearcher:
    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[str] = None  # "reference", "product", or None
    ) -> List[SearchResult]
    
    def search_grouped_by_code(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, List[SearchResult]]
    
    def get_all_records_for_code(self, code: str) -> List[SearchResult]
```

### Migration Service

```python
class DataMigration:
    def migrate_existing_records(self) -> int
    def add_source_metadata_to_existing(self) -> int
```

## Data Models

### ChromaDB Collection Schema

#### Unified Collection Structure
- **Collection Name**: "tnved" (unchanged)
- **ID Format**: 
  - Reference: `{tnved_code}` (e.g., "0901110000")
  - Product: `{tnved_code}_{sequence}` (e.g., "0901110000_001")

#### Record Types Coexistence
```python
# Reference record (existing format, enhanced)
{
    "id": "0901110000",
    "embedding": [...],
    "document": "кофе нежареный неосвобожденный кофеина",
    "metadata": {
        "description": "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
        "code": "0901110000",
        "source_type": "reference",
        "source_name": "tnved_official"
    }
}

# Product record (new format)
{
    "id": "0901110000_001", 
    "embedding": [...],
    "document": "кофе арабика зерновой килограмм",
    "metadata": {
        "description": "Кофе арабика зерновой 1кг",
        "code": "0901110000",
        "source_type": "product", 
        "source_name": "customs_2024_q1",
        "source_id": "декларация_12345"
    }
}
```

### Configuration Extensions

```yaml
# config.yaml additions
database:
  path: "./chroma_db"
  collection_name: "tnved"
  default_source_name: "unknown"  # NEW

search:
  default_top_k: 5
  group_by_code: false  # NEW: group results by ТНВЭД code
  prioritize_reference: true  # NEW: rank reference records higher
  
sources:  # NEW section
  reference:
    name: "tnved_official"
    display_name: "Официальный справочник ТНВЭД"
  product:
    default_name: "unknown_products"
    display_name: "Товары с подобранными кодами"
```

## Correctness Properties

Let me analyze the acceptance criteria for testability:

<function_calls>
<invoke name="prework">
<parameter name="featureName">product-data-support

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

After analyzing the acceptance criteria, I identified several redundant properties that can be consolidated:

**Property Reflection:**
- Properties 1.3 and 2.2 both test source_type "product" assignment - can be combined
- Properties 3.2 and 4.4 both test source filtering - can be combined  
- Properties 3.5 and 4.5 both test source information display - can be combined
- Properties 7.2 and 3.1 both test unfiltered search behavior - can be combined

### Core Properties

**Property 1: Excel Format Compatibility**
*For any* Excel file with Code and TextEx columns, the Product_Loader should successfully read and process the data regardless of whether it's reference or product data
**Validates: Requirements 1.1**

**Property 2: Unique ID Generation**
*For any* ТНВЭД code and any number of product records, generated IDs should follow the pattern `{code}_{counter}` and be globally unique within the collection
**Validates: Requirements 1.2, 5.2**

**Property 3: Source Type Consistency**
*For any* loaded record, the source_type metadata should correctly reflect the loading mode ("reference" for reference data, "product" for product data)
**Validates: Requirements 1.3, 2.1, 2.2**

**Property 4: Source Information Preservation**
*For any* product record loaded with source information, the stored metadata should contain the complete source name and optional source ID
**Validates: Requirements 1.4**

**Property 5: Duplicate Handling**
*For any* set of records with identical descriptions but same ТНВЭД code, each should be stored with a unique ID while preserving all content
**Validates: Requirements 1.5**

**Property 6: Legacy Data Migration**
*For any* existing record without source_type metadata, the system should automatically assign source_type "reference" while preserving all existing functionality
**Validates: Requirements 2.3, 7.5**

**Property 7: Search Result Completeness**
*For any* search query, results should include source_type information and, for product records, source name and source ID when available
**Validates: Requirements 2.4, 3.5, 4.5**

**Property 8: Unfiltered Search Scope**
*For any* search query without source filters, results should include records from both reference and product sources
**Validates: Requirements 3.1, 7.2**

**Property 9: Source Filtering**
*For any* search query with source_type filter, results should contain only records matching the specified source_type
**Validates: Requirements 3.2, 4.4**

**Property 10: Result Grouping and Prioritization**
*For any* search results containing multiple records with the same ТНВЭД code, reference records should be ranked higher than product records in the result ordering
**Validates: Requirements 3.4**

**Property 11: CLI Parameter Propagation**
*For any* load command with --source-type and --source-name parameters, the specified values should be correctly stored in the record metadata
**Validates: Requirements 4.1, 4.2**

**Property 12: Statistics Display**
*For any* data loading operation, the system should display accurate counts of reference vs product records processed
**Validates: Requirements 4.3**

**Property 13: Code Format Validation**
*For any* input ТНВЭД code, the system should accept valid 10-digit codes and reject invalid formats
**Validates: Requirements 5.1**

**Property 14: Referential Integrity**
*For any* ТНВЭД code with multiple associated records, all records should maintain consistent code values and proper relationships
**Validates: Requirements 5.3**

**Property 15: Backward Compatibility**
*For any* existing API call or script, the system should continue to work without modification while providing enhanced functionality through optional parameters
**Validates: Requirements 5.4, 7.1, 7.3, 7.4**

**Property 16: Code Query Completeness**
*For any* specific ТНВЭД code query, the system should return all associated records (both reference and product) for that code
**Validates: Requirements 5.5**

**Property 17: Configuration Behavior**
*For any* configured search preferences (source type, grouping, display format), the system should respect these settings in search operations and result display
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

## Error Handling

### Data Loading Errors
- **Invalid Excel Format**: Graceful handling of missing columns or corrupted files
- **Duplicate ID Generation**: Automatic retry with incremented counter
- **Embedding Generation Failures**: Skip problematic records with logging
- **ChromaDB Connection Issues**: Retry logic with exponential backoff

### Search Errors  
- **Empty Query Handling**: Return appropriate error message
- **Invalid Source Filter**: Validate filter values before processing
- **Database Unavailable**: Graceful degradation with cached results if available
- **Malformed Results**: Sanitize and validate all returned data

### Migration Errors
- **Partial Migration Failures**: Rollback capability for data consistency
- **Schema Conflicts**: Automatic resolution with conflict logging
- **Performance Issues**: Batch processing with progress tracking

## Testing Strategy

### Dual Testing Approach
The system will use both unit testing and property-based testing for comprehensive coverage:

**Unit Tests** will focus on:
- Specific examples of data loading and searching
- Edge cases like empty files, malformed data
- Integration points between components
- CLI parameter parsing and validation
- Error conditions and exception handling

**Property-Based Tests** will verify:
- Universal properties across all valid inputs using randomized test data
- ID generation uniqueness across large datasets
- Search consistency across different query types
- Data integrity during migration operations
- Configuration behavior across different settings

**Property Test Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with format: **Feature: product-data-support, Property {number}: {property_text}**
- Use pytest-hypothesis for Python property-based testing
- Generate realistic test data including valid ТНВЭД codes, product descriptions, and source metadata

**Testing Framework:**
- **pytest** for unit tests and test organization
- **pytest-hypothesis** for property-based testing
- **pandas** for Excel file generation in tests
- **tempfile** for isolated test environments
- **unittest.mock** for component isolation