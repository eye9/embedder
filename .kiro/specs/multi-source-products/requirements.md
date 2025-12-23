# Requirements Document

## Introduction

Расширение системы ТНВЭД Embedder для поддержки загрузки и поиска по товарам с уже подобранными кодами ТНВЭД из различных источников (таможенные декларации, каталоги поставщиков, исторические данные). Система должна хранить как официальный справочник ТНВЭД, так и реальные примеры товаров с кодами, что улучшит точность подбора кодов для новых товаров за счет использования проверенных примеров.

## Glossary

- **Справочная запись (Reference Record)**: Официальная запись из справочника ТНВЭД с кодом и описанием
- **Товарная запись (Product Record)**: Запись о реальном товаре с подобранным кодом ТНВЭД из внешнего источника
- **Источник данных (Data Source)**: Система или файл, из которого получены товарные записи (например, "customs_2024_q1", "supplier_catalog_alfa")
- **Тип записи (Record Type)**: Классификация записи - "reference" для справочника или "product" для товаров
- **Единая коллекция (Unified Collection)**: ChromaDB коллекция, содержащая как справочные, так и товарные записи
- **Система**: Программная система ТНВЭД Embedder с поддержкой множественных источников данных

## Requirements

### Requirement 1

**User Story:** Как администратор системы, я хочу загружать товары с подобранными кодами ТНВЭД из различных источников, чтобы расширить базу знаний системы реальными примерами.

#### Acceptance Criteria

1. WHEN the system loads product data from Excel THEN the system SHALL extract data from columns Code and TextEx using the same format as reference data
2. WHEN the system loads product data THEN the system SHALL accept a source_type parameter with value "product" to distinguish from reference records
3. WHEN the system loads product data THEN the system SHALL accept a source_name parameter to identify the data source
4. WHEN the system stores product records THEN the system SHALL generate unique IDs by combining the code with a sequential counter
5. WHEN the system stores product records THEN the system SHALL include source_type, source_name, and code in metadata

### Requirement 2

**User Story:** Как пользователь системы, я хочу искать коды ТНВЭД по всем доступным источникам данных, чтобы получить наиболее точные результаты на основе как справочника, так и реальных примеров.

#### Acceptance Criteria

1. WHEN a user performs search THEN the system SHALL query both reference and product records in a single operation
2. WHEN the system returns search results THEN the system SHALL include source_type and source_name in each result
3. WHEN the system returns search results THEN the system SHALL group results by ТНВЭД code while preserving individual record details
4. WHEN multiple records have the same code THEN the system SHALL show the best matching record for each unique code
5. WHEN a user provides a filter parameter THEN the system SHALL support filtering results by source_type

### Requirement 3

**User Story:** Как администратор системы, я хочу управлять записями из разных источников независимо, чтобы обновлять или удалять данные конкретного источника без влияния на другие.

#### Acceptance Criteria

1. WHEN the system loads data with source_name THEN the system SHALL track which records belong to that source
2. WHEN the system loads data from an existing source THEN the system SHALL update existing records from that source
3. WHEN the system provides statistics THEN the system SHALL report counts by source_type and source_name
4. WHEN the system deletes records by source THEN the system SHALL remove only records matching the specified source_name
5. WHEN the system lists sources THEN the system SHALL return all unique source names with record counts

### Requirement 4

**User Story:** Как разработчик, я хочу сохранить обратную совместимость с существующим кодом, чтобы текущие скрипты загрузки и поиска продолжали работать без изменений.

#### Acceptance Criteria

1. WHEN the system loads data without source_type parameter THEN the system SHALL default to "reference" type
2. WHEN the system loads data without source_name parameter THEN the system SHALL use "tnved_official" as default source name
3. WHEN the system loads reference data THEN the system SHALL use the code as the record ID for backward compatibility
4. WHEN existing code queries the database THEN the system SHALL return results in the same format as before
5. WHEN the system performs search without filters THEN the system SHALL search across all record types by default

### Requirement 5

**User Story:** Как пользователь системы, я хочу видеть информацию об источнике данных в результатах поиска, чтобы оценить надежность подобранного кода.

#### Acceptance Criteria

1. WHEN the system displays search results THEN the system SHALL show source_type for each result
2. WHEN the system displays search results THEN the system SHALL show source_name for each result
3. WHEN the system displays product records THEN the system SHALL clearly distinguish them from reference records
4. WHEN multiple sources provide the same code THEN the system SHALL indicate the diversity of sources
5. WHEN the system formats output THEN the system SHALL provide human-readable source descriptions

### Requirement 6

**User Story:** Как администратор системы, я хочу загружать большие объемы товарных данных эффективно, чтобы минимизировать время обработки.

#### Acceptance Criteria

1. WHEN the system generates IDs for product records THEN the system SHALL use an efficient counter mechanism
2. WHEN the system loads product data in batches THEN the system SHALL maintain ID uniqueness across batches
3. WHEN the system processes duplicate descriptions within a source THEN the system SHALL handle them as separate records
4. WHEN the system loads data THEN the system SHALL report progress including source information
5. WHEN the system completes loading THEN the system SHALL report statistics by source_type

### Requirement 7

**User Story:** Как пользователь CLI, я хочу использовать простые команды для загрузки товарных данных, чтобы быстро пополнять базу знаний.

#### Acceptance Criteria

1. WHEN a user runs load command with --source-type product THEN the system SHALL load data as product records
2. WHEN a user runs load command with --source-name THEN the system SHALL tag records with the specified source
3. WHEN a user runs load command without source parameters THEN the system SHALL use reference defaults
4. WHEN a user runs search command THEN the system SHALL display source information in results
5. WHEN a user runs search command with --source-filter THEN the system SHALL filter results by source_type
