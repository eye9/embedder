# Requirements Document

## Introduction

Расширение системы ТНВЭД Embedder для поддержки загрузки и поиска по товарам с уже подобранными кодами ТНВЭД. Это позволит улучшить точность подбора кодов за счет использования реальных примеров товаров из таможенных деклараций, каталогов поставщиков и других источников.

## Glossary

- **ТНВЭД_System**: Существующая система поиска кодов ТНВЭД
- **Reference_Record**: Запись из официального справочника ТНВЭД
- **Product_Record**: Запись товара с подобранным кодом ТНВЭД
- **Source_Type**: Тип источника данных (reference или product)
- **Product_Loader**: Компонент для загрузки товарных данных
- **Combined_Searcher**: Компонент для поиска по объединенной базе
- **Source_Filter**: Фильтр для поиска по типу источника

## Requirements

### Requirement 1: Product Data Loading

**User Story:** Как администратор системы, я хочу загружать товары с подобранными кодами ТНВЭД из Excel файлов, чтобы расширить базу знаний для более точного подбора кодов.

#### Acceptance Criteria

1. WHEN loading product data from Excel file, THE Product_Loader SHALL read Code and TextEx columns in the same format as reference data
2. WHEN processing product records, THE Product_Loader SHALL generate unique IDs using code and sequential counter (e.g., "0901110000_001")
3. WHEN storing product records, THE Product_Loader SHALL mark them with source_type "product" in metadata
4. WHEN loading product data, THE Product_Loader SHALL store source information including source name and optional source ID
5. WHEN product records have duplicate descriptions, THE Product_Loader SHALL store all duplicates with unique IDs

### Requirement 2: Source Type Management

**User Story:** Как разработчик, я хочу различать справочные записи и товарные записи, чтобы система могла работать с разными типами данных корректно.

#### Acceptance Criteria

1. WHEN storing reference records, THE ТНВЭД_System SHALL mark them with source_type "reference" in metadata
2. WHEN storing product records, THE ТНВЭД_System SHALL mark them with source_type "product" in metadata
3. WHEN loading existing reference data, THE ТНВЭД_System SHALL automatically migrate records to include source_type "reference"
4. WHEN querying records, THE ТНВЭД_System SHALL provide access to source_type information in results

### Requirement 3: Enhanced Search Functionality

**User Story:** Как пользователь, я хочу искать коды ТНВЭД по всей расширенной базе данных, чтобы получать более точные результаты на основе реальных примеров товаров.

#### Acceptance Criteria

1. WHEN performing search without filters, THE Combined_Searcher SHALL search across both reference and product records
2. WHEN user specifies source type filter, THE Combined_Searcher SHALL return only records matching the specified source_type
3. WHEN displaying search results, THE Combined_Searcher SHALL group results by ТНВЭД code and show source information
4. WHEN multiple records exist for same code, THE Combined_Searcher SHALL prioritize reference records in result ranking
5. WHEN showing product records, THE Combined_Searcher SHALL display source name and type in results

### Requirement 4: Command Line Interface Enhancement

**User Story:** Как администратор, я хочу использовать командную строку для загрузки товарных данных, чтобы автоматизировать процесс обновления базы.

#### Acceptance Criteria

1. WHEN using load command with --source-type product, THE Product_Loader SHALL load data as product records
2. WHEN using load command with --source-name parameter, THE Product_Loader SHALL store the specified source name in metadata
3. WHEN loading product data, THE Product_Loader SHALL display statistics showing reference vs product record counts
4. WHEN using search command with --source-filter, THE Combined_Searcher SHALL filter results by source type
5. WHEN displaying search results, THE Combined_Searcher SHALL show source information for each result

### Requirement 5: Data Integrity and Validation

**User Story:** Как администратор системы, я хочу обеспечить целостность данных при работе с разными типами записей, чтобы система работала надежно.

#### Acceptance Criteria

1. WHEN loading product data, THE Product_Loader SHALL validate that ТНВЭД codes follow correct format
2. WHEN generating unique IDs for products, THE Product_Loader SHALL ensure no ID collisions occur
3. WHEN storing records with same code, THE ТНВЭД_System SHALL maintain referential integrity
4. WHEN migrating existing data, THE ТНВЭД_System SHALL preserve all existing functionality
5. WHEN querying by specific code, THE ТНВЭД_System SHALL return all records (reference and product) for that code

### Requirement 6: Configuration Management

**User Story:** Как администратор, я хочу настраивать поведение системы для работы с разными типами источников, чтобы адаптировать систему под различные сценарии использования.

#### Acceptance Criteria

1. WHEN configuring search behavior, THE ТНВЭД_System SHALL allow setting default source type preferences
2. WHEN loading data, THE ТНВЭД_System SHALL support configuration of default source names
3. WHEN performing searches, THE ТНВЭД_System SHALL respect configured result grouping preferences
4. WHEN displaying results, THE ТНВЭД_System SHALL allow configuration of source information display format

### Requirement 7: Backward Compatibility

**User Story:** Как пользователь существующей системы, я хочу, чтобы все текущие функции продолжали работать без изменений, чтобы не нарушить существующие процессы.

#### Acceptance Criteria

1. WHEN using existing load commands without new parameters, THE ТНВЭД_System SHALL load data as reference records
2. WHEN using existing search commands, THE Combined_Searcher SHALL return results from all sources by default
3. WHEN accessing existing API methods, THE ТНВЭД_System SHALL maintain same response format with additional optional fields
4. WHEN running existing scripts, THE ТНВЭД_System SHALL work without requiring code changes
5. WHEN querying existing data, THE ТНВЭД_System SHALL automatically assign source_type "reference" to legacy records