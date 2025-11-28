# Requirements Document

## Introduction

Система для автоматического подбора кодов ТНВЭД (Товарная номенклатура внешнеэкономической деятельности) на основе текстового описания товара. Система использует векторную базу данных ChromaDB и эмбеддинги на русском языке для семантического поиска наиболее подходящих кодов ТНВЭД по описанию товара.

## Glossary

- **ТНВЭД**: Товарная номенклатура внешнеэкономической деятельности - классификатор товаров для таможенного оформления
- **Справочник ТНВЭД**: Excel файл (tnved_full10_new.xlsx) содержащий коды в столбце Code и описания в столбце TextEx
- **Векторная БД**: ChromaDB - база данных для хранения и поиска векторных представлений текстов
- **Эмбеддинг-модель**: ai-forever/FRIDA - модель для преобразования русских текстов в векторные представления
- **Система**: Программная система для загрузки справочника ТНВЭД в векторную БД и поиска кодов
- **Natasha**: Библиотека для обработки и нормализации русских текстов

## Requirements

### Requirement 1

**User Story:** Как разработчик, я хочу загрузить справочник ТНВЭД в векторную базу данных, чтобы в дальнейшем использовать его для автоматического подбора кодов.

#### Acceptance Criteria

1. WHEN the system reads the Excel file THEN the system SHALL extract data from columns Code and TextEx
2. WHEN the system processes TextEx descriptions THEN the system SHALL convert all uppercase text to lowercase
3. WHEN the system processes TextEx descriptions THEN the system SHALL normalize Russian text using Natasha library
4. WHEN the system generates embeddings THEN the system SHALL use the ai-forever/FRIDA model from HuggingFace
5. WHEN the system stores data THEN the system SHALL save normalized text, original code, and embeddings to ChromaDB

### Requirement 2

**User Story:** Как пользователь системы, я хочу искать коды ТНВЭД по текстовому описанию товара, чтобы быстро найти подходящий код для таможенного оформления.

#### Acceptance Criteria

1. WHEN a user provides a text description THEN the system SHALL normalize the input text using the same normalization pipeline
2. WHEN a user provides a text description THEN the system SHALL generate embeddings using the same FRIDA model
3. WHEN the system performs search THEN the system SHALL return the top-k most similar ТНВЭД codes with similarity scores
4. WHEN the system returns results THEN the system SHALL include both the code and the original description for each result
5. WHEN the search query is empty or invalid THEN the system SHALL return an error message and maintain system state

### Requirement 3

**User Story:** Как администратор системы, я хочу управлять векторной базой данных, чтобы обновлять справочник при изменении ТНВЭД.

#### Acceptance Criteria

1. WHEN the system initializes ChromaDB THEN the system SHALL create or connect to a persistent collection
2. WHEN the system loads data THEN the system SHALL handle duplicate codes by updating existing entries
3. WHEN the system processes large datasets THEN the system SHALL load data in batches to manage memory efficiently
4. WHEN database operations fail THEN the system SHALL log errors with sufficient detail for debugging
5. WHEN the system completes loading THEN the system SHALL report the total number of records processed

### Requirement 4

**User Story:** Как разработчик, я хочу иметь конфигурируемую систему, чтобы легко изменять параметры модели и базы данных без изменения кода.

#### Acceptance Criteria

1. WHEN the system starts THEN the system SHALL load configuration from a configuration file or environment variables
2. WHERE configuration includes model name THEN the system SHALL support changing the embedding model
3. WHERE configuration includes database path THEN the system SHALL support custom ChromaDB storage locations
4. WHERE configuration includes batch size THEN the system SHALL use the specified batch size for processing
5. WHEN configuration is invalid or missing THEN the system SHALL use sensible default values and log warnings

### Requirement 5

**User Story:** Как пользователь системы, я хочу получать качественные результаты поиска, чтобы точно определять коды ТНВЭД для моих товаров.

#### Acceptance Criteria

1. WHEN the system normalizes text THEN the system SHALL preserve semantic meaning of the original description
2. WHEN the system performs text normalization THEN the system SHALL lemmatize words using Natasha
3. WHEN the system performs text normalization THEN the system SHALL remove excessive whitespace and special characters
4. WHEN embeddings are generated THEN the system SHALL produce consistent vectors for identical normalized texts
5. WHEN similarity search is performed THEN the system SHALL rank results by cosine similarity or equivalent metric
