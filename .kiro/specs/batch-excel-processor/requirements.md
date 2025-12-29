# Requirements Document

## Introduction

Система пакетной обработки Excel файлов для автоматического подбора кодов ТНВЭД по описаниям товаров. Система предоставляет веб-интерфейс для загрузки Excel файлов с описаниями товаров, выполняет поиск соответствующих кодов ТНВЭД с использованием существующей системы поиска, и возвращает обогащенный файл с добавленными кодами и обоснованиями выбора.

## Glossary

- **Система**: Веб-приложение для пакетной обработки Excel файлов с описаниями товаров
- **Пользователь**: Лицо, загружающее Excel файл для обработки через веб-интерфейс
- **Исходный_Файл**: Excel файл с колонкой "Product Detailed Description" содержащей описания товаров
- **HTS_Code**: Колонка в Excel файле, которая может содержать уже существующие коды ТНВЭД
- **Обработанный_Файл**: Excel файл с добавленными колонками кода ТНВЭД и обоснования выбора
- **ТНВЭД_Поисковик**: Существующая система поиска кодов ТНВЭД (TNVEDSearcher)
- **Алгоритм_Поиска**: Настраиваемый метод выбора кода ТНВЭД (по similarity score или LLM reasoning)
- **Веб_Интерфейс**: HTML страница с формой для загрузки файлов и авторизации
- **Сессия_Обработки**: Уникальная сессия пользователя для отслеживания статуса обработки файла

## Requirements

### Requirement 1

**User Story:** Как пользователь, я хочу авторизоваться на веб-странице и загрузить Excel файл, чтобы начать процесс пакетной обработки описаний товаров.

#### Acceptance Criteria

1. WHEN a user visits the web interface THEN the system SHALL display an authorization form with username/password fields
2. WHEN a user provides valid credentials THEN the system SHALL authenticate the user and display the file upload interface
3. WHEN a user provides invalid credentials THEN the system SHALL display an error message and maintain the login form
4. WHEN an authenticated user uploads an Excel file THEN the system SHALL validate the file format and presence of "Product Detailed Description" column
5. WHEN the uploaded file is invalid THEN the system SHALL display a descriptive error message and allow re-upload

### Requirement 2

**User Story:** Как система, я хочу обрабатывать Excel файлы пакетно, чтобы найти коды ТНВЭД для каждого описания товара в файле.

#### Acceptance Criteria

1. WHEN the system processes an Excel file THEN the system SHALL read all rows with non-empty "Product Detailed Description" values
2. WHEN the system processes each description THEN the system SHALL use the configured search algorithm to find the most appropriate ТНВЭД code
3. WHEN the system completes processing THEN the system SHALL add two new columns: "TNVED_Code" and "Selection_Reason"
4. WHEN the system encounters processing errors for individual rows THEN the system SHALL log the error and continue processing remaining rows
5. WHEN the system completes all processing THEN the system SHALL preserve all original columns and data in the output file

### Requirement 3

**User Story:** Как администратор системы, я хочу настраивать алгоритм поиска кодов ТНВЭД, чтобы оптимизировать качество результатов для разных типов товаров.

#### Acceptance Criteria

1. WHERE algorithm is set to "similarity_top1" THEN the system SHALL select the code with highest similarity score from ТНВЭД_Поисковик
2. WHERE algorithm is set to "llm_reasoning" THEN the system SHALL use LLM to analyze top-5 results and select the most appropriate code
3. WHEN using similarity_top1 algorithm THEN the Selection_Reason SHALL contain "Code|Similarity Score|Source Name|Description"
4. WHEN using llm_reasoning algorithm THEN the Selection_Reason SHALL contain the LLM's reasoning explanation for the code selection
5. WHEN the algorithm configuration is invalid THEN the system SHALL use similarity_top1 as default and log a warning

### Requirement 4

**User Story:** Как пользователь, я хочу получить обработанный Excel файл с добавленными кодами ТНВЭД, чтобы использовать результаты для таможенного оформления.

#### Acceptance Criteria

1. WHEN processing is complete THEN the system SHALL generate a new Excel file with all original data plus two additional columns
2. WHEN the system generates the output file THEN the "TNVED_Code" column SHALL contain the selected ТНВЭД code for each processed row
3. WHEN the system generates the output file THEN the "Selection_Reason" column SHALL contain the justification for code selection
4. WHEN the system provides the download link THEN the user SHALL be able to download the processed file immediately
5. WHEN no suitable code is found for a description THEN the system SHALL leave TNVED_Code empty and provide explanation in Selection_Reason

### Requirement 5

**User Story:** Как пользователь, я хочу отслеживать прогресс обработки файла, чтобы понимать статус выполнения и ожидаемое время завершения.

#### Acceptance Criteria

1. WHEN file processing starts THEN the system SHALL display a progress indicator showing percentage completion
2. WHEN processing is in progress THEN the system SHALL update progress information in real-time
3. WHEN processing encounters errors THEN the system SHALL display error count and continue processing
4. WHEN processing is complete THEN the system SHALL display completion status and provide download link
5. WHEN processing takes longer than expected THEN the system SHALL provide estimated time remaining

### Requirement 6

**User Story:** Как система, я хочу обеспечить безопасность и изоляцию пользовательских данных, чтобы предотвратить несанкционированный доступ к загруженным файлам.

#### Acceptance Criteria

1. WHEN a user uploads a file THEN the system SHALL store it in a session-specific temporary directory
2. WHEN processing is complete THEN the system SHALL automatically delete uploaded and processed files after 24 hours
3. WHEN multiple users use the system simultaneously THEN the system SHALL ensure complete isolation of their data
4. WHEN a user session expires THEN the system SHALL clean up all associated temporary files
5. WHEN the system handles file operations THEN the system SHALL validate file paths to prevent directory traversal attacks

### Requirement 7

**User Story:** Как администратор системы, я хочу мониторить использование системы и производительность, чтобы обеспечить стабильную работу и планировать ресурсы.

#### Acceptance Criteria

1. WHEN the system processes files THEN the system SHALL log processing statistics including file size, row count, and processing time
2. WHEN errors occur during processing THEN the system SHALL log detailed error information for debugging
3. WHEN the system reaches resource limits THEN the system SHALL queue requests and inform users about wait times
4. WHEN the system completes processing THEN the system SHALL record success metrics and performance data
5. WHEN system maintenance is required THEN the system SHALL provide graceful degradation and user notifications

### Requirement 8

**User Story:** Как пользователь, я хочу выбирать режим обработки файла, чтобы оптимизировать время обработки и расход ресурсов при работе с частично заполненными файлами.

#### Acceptance Criteria

1. WHEN a user uploads a file THEN the system SHALL provide an option to "Process only rows without existing HTS Code"
2. WHERE the user selects "Process only empty codes" option THEN the system SHALL skip rows that already have values in "HTS Code" column
3. WHERE the user selects "Process all rows" option THEN the system SHALL process all rows regardless of existing "HTS Code" values
4. WHEN the system skips rows with existing codes THEN the system SHALL preserve the original "HTS Code" values in the output file
5. WHEN the system processes in selective mode THEN the system SHALL report the count of processed vs skipped rows in the completion summary

### Requirement 9

**User Story:** Как пользователь, я хочу получать качественные результаты поиска кодов ТНВЭД, чтобы минимизировать необходимость ручной проверки и корректировки.

#### Acceptance Criteria

1. WHEN the system uses similarity_top1 algorithm THEN the system SHALL include similarity score in Selection_Reason for quality assessment
2. WHEN the system uses llm_reasoning algorithm THEN the system SHALL provide detailed reasoning that explains why the specific code was chosen
3. WHEN similarity score is below a configurable threshold THEN the system SHALL flag the result as "Low Confidence" in Selection_Reason
4. WHEN multiple codes have very similar scores THEN the system SHALL indicate this uncertainty in Selection_Reason
5. WHEN the system cannot find any relevant codes THEN the system SHALL provide suggestions for manual review in Selection_Reason