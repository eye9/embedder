# Requirements Document

## Introduction

Расширение алгоритма подбора кодов ТНВЭД в системе пакетной обработки Excel файлов для поддержки поиска по URL-адресам товаров. Система должна сначала искать коды по ссылкам на страницы товаров в интернет-магазинах, а затем использовать семантический поиск как резервный метод. Это позволит повысить точность подбора кодов за счет использования уже известных соответствий между URL и кодами ТНВЭД.

## Glossary

- **URL_Column**: Колонка "Link to customer's web-page with item description" в загружаемых Excel файлах
- **URL_Database**: База данных, содержащая соответствия между нормализованными URL и кодами ТНВЭД
- **URL_Matcher**: Компонент для поиска кодов по URL-адресам
- **URL_Normalizer**: Компонент для нормализации URL (удаление параметров запроса, стандартизация формата)
- **Hybrid_Selector**: Селектор, использующий сначала URL-поиск, затем семантический поиск
- **URL_Record**: Запись в базе данных, содержащая нормализованный URL, оригинальный URL, код ТНВЭД и описание товара
- **Normalized_URL**: URL после удаления параметров запроса (?...), фрагментов (#...) и стандартизации протокола
- **Match_Source**: Источник найденного соответствия ("url" или "semantic")
- **Система**: Система пакетной обработки Excel файлов с поддержкой URL-поиска

## Requirements

### Requirement 1

**User Story:** Как пользователь системы, я хочу загружать Excel файлы с колонкой URL товаров, чтобы система могла использовать эти ссылки для более точного подбора кодов ТНВЭД.

#### Acceptance Criteria

1. WHEN the system validates an Excel file THEN the system SHALL check for the presence of "Link to customer's web-page with item description" column
2. WHEN the system processes Excel files THEN the system SHALL extract URL values from the URL_Column for each row
3. WHEN a row contains both description and URL THEN the system SHALL use both for code selection
4. WHEN a row contains only description without URL THEN the system SHALL use semantic search as before
5. WHEN the URL_Column is missing THEN the system SHALL continue processing using only semantic search

### Requirement 2

**User Story:** Как администратор системы, я хочу загружать в базу данных соответствия между URL товаров и кодами ТНВЭД, чтобы система могла использовать эти данные для поиска.

#### Acceptance Criteria

1. WHEN loading URL data from Excel files THEN the system SHALL read URL, Code, and Description columns
2. WHEN storing URL records THEN the system SHALL normalize URLs before creating URL_Record entries
3. WHEN storing URL records THEN the system SHALL use normalized URL as primary identifier while preserving original URL
4. WHEN storing URL records THEN the system SHALL mark them with source_type "url" in metadata
5. WHEN loading URL data THEN the system SHALL validate URL format and ТНВЭД code format
6. WHEN URL records have duplicate normalized URLs THEN the system SHALL update existing records with new code and description

### Requirement 3

**User Story:** Как система, я хочу сначала искать коды ТНВЭД по URL, а затем использовать семантический поиск, чтобы максимизировать точность подбора кодов.

#### Acceptance Criteria

1. WHEN processing a row with URL THEN the system SHALL first normalize the URL and query the URL_Database for exact match
2. WHEN URL match is found THEN the system SHALL return the associated ТНВЭД code with "Found by URL" explanation
3. WHEN URL match is not found THEN the system SHALL fall back to semantic search using the description
4. WHEN using semantic search as fallback THEN the system SHALL indicate "Found by semantic search" in explanation
5. WHEN both URL and semantic search fail THEN the system SHALL return empty code with appropriate explanation

### Requirement 4

**User Story:** Как пользователь, я хочу видеть в результатах обработки информацию о том, как был найден код ТНВЭД, чтобы оценить надежность результата.

#### Acceptance Criteria

1. WHEN code is found by URL match THEN the Selection_Reason SHALL contain "Found by URL: [URL] | Code: [CODE] | Description: [DESC]"
2. WHEN code is found by semantic search THEN the Selection_Reason SHALL contain "Found by semantic search | [existing semantic reason]"
3. WHEN URL search fails but semantic succeeds THEN the Selection_Reason SHALL indicate "URL not found, used semantic search"
4. WHEN both methods fail THEN the Selection_Reason SHALL indicate "No match found by URL or semantic search"
5. WHEN URL is invalid or empty THEN the Selection_Reason SHALL indicate "Used semantic search (no valid URL provided)"

### Requirement 5

**User Story:** Как администратор системы, я хочу управлять базой URL-соответствий, чтобы поддерживать актуальность данных и добавлять новые соответствия.

#### Acceptance Criteria

1. WHEN loading new URL data THEN the system SHALL support batch loading from Excel files
2. WHEN updating URL records THEN the system SHALL allow updating existing URL-code mappings
3. WHEN querying URL database THEN the system SHALL provide statistics about total URL records
4. WHEN deleting URL records THEN the system SHALL support removal by URL pattern or source
5. WHEN exporting URL data THEN the system SHALL provide functionality to export current URL-code mappings

### Requirement 6

**User Story:** Как разработчик, я хочу интегрировать URL-поиск с существующими алгоритмами подбора кодов, чтобы обеспечить совместимость с текущей системой.

#### Acceptance Criteria

1. WHEN creating Hybrid_Selector THEN the system SHALL integrate with existing SimilarityTop1Selector and LLMReasoningSelector
2. WHEN URL search is enabled THEN the system SHALL maintain compatibility with existing algorithm configurations
3. WHEN URL database is unavailable THEN the system SHALL gracefully fall back to semantic search only
4. WHEN processing files without URL column THEN the system SHALL work exactly as before
5. WHEN URL search is disabled in configuration THEN the system SHALL skip URL matching and use semantic search

### Requirement 7

**User Story:** Как пользователь системы, я хочу настраивать приоритет URL-поиска относительно семантического поиска, чтобы адаптировать систему под разные сценарии использования.

#### Acceptance Criteria

1. WHERE URL_priority is set to "first" THEN the system SHALL try URL search before semantic search
2. WHERE URL_priority is set to "only" THEN the system SHALL use only URL search without semantic fallback
3. WHERE URL_priority is set to "disabled" THEN the system SHALL skip URL search and use only semantic search
4. WHEN URL_priority configuration is invalid THEN the system SHALL default to "first" mode with warning
5. WHEN URL search takes too long THEN the system SHALL timeout and fall back to semantic search

### Requirement 8

**User Story:** Как администратор системы, я хочу мониторить эффективность URL-поиска, чтобы оценить качество URL-базы данных и оптимизировать систему.

#### Acceptance Criteria

1. WHEN processing files with URLs THEN the system SHALL track URL match rate statistics
2. WHEN URL search is used THEN the system SHALL log URL search performance metrics
3. WHEN processing completes THEN the system SHALL report how many codes were found by URL vs semantic search
4. WHEN URL matches are found THEN the system SHALL track confidence scores for URL-based matches
5. WHEN generating reports THEN the system SHALL include URL search effectiveness in processing summaries

### Requirement 9

**User Story:** Как пользователь, я хочу обрабатывать файлы с частично заполненными URL, чтобы система эффективно работала с неполными данными.

#### Acceptance Criteria

1. WHEN URL field is empty THEN the system SHALL skip URL search and use semantic search
2. WHEN URL field contains invalid URL THEN the system SHALL log warning and use semantic search
3. WHEN URL field contains partial URL THEN the system SHALL attempt normalization before search
4. WHEN multiple URLs are in one field THEN the system SHALL use the first valid URL for search
5. WHEN URL contains special characters THEN the system SHALL properly encode URL for database search

### Requirement 11

**User Story:** Как система, я хочу нормализовать URL товаров для эффективного поиска и хранения, чтобы обеспечить точное сопоставление несмотря на различия в параметрах запроса и форматировании.

#### Acceptance Criteria

1. WHEN processing URLs THEN the system SHALL remove query parameters (everything after "?") to eliminate tracking and affiliate codes
2. WHEN processing URLs THEN the system SHALL remove URL fragments (everything after "#") to focus on core product path
3. WHEN processing URLs THEN the system SHALL normalize protocol to "https" for consistency
4. WHEN processing URLs THEN the system SHALL preserve domain and product path structure (e.g., "/product/1923313097/")
5. WHEN storing normalized URLs THEN the system SHALL maintain both original and normalized versions for reference

### Requirement 12

**User Story:** Как администратор системы, я хочу настраивать правила нормализации URL для разных интернет-магазинов, чтобы система корректно работала с различными форматами URL.

#### Acceptance Criteria

1. WHEN system encounters Ozon URLs THEN the system SHALL extract product ID from path pattern "/product/{id}/"
2. WHEN system encounters Yandex Market URLs THEN the system SHALL extract product ID from path pattern "/product/{id}" and ignore query parameters
3. WHEN system encounters Wildberries URLs THEN the system SHALL extract product ID from path pattern "/catalog/{id}/"
4. WHEN system encounters unknown URL patterns THEN the system SHALL use generic normalization (remove query params and fragments)
5. WHEN URL normalization rules are updated THEN the system SHALL support configuration-based pattern matching

### Requirement 10

**User Story:** Как администратор системы, я хочу обеспечить безопасность при работе с URL, чтобы предотвратить потенциальные угрозы безопасности.

#### Acceptance Criteria

1. WHEN processing URLs THEN the system SHALL validate URL format and reject malicious patterns
2. WHEN storing URLs THEN the system SHALL sanitize URL strings to prevent injection attacks
3. WHEN querying URL database THEN the system SHALL use parameterized queries to prevent SQL injection
4. WHEN logging URLs THEN the system SHALL mask sensitive parameters in log files
5. WHEN URL contains credentials THEN the system SHALL remove authentication information before storage