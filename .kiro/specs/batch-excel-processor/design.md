# Design Document: Batch Excel Processor

## Overview

Система пакетной обработки Excel файлов представляет собой веб-приложение для автоматического подбора кодов ТНВЭД по описаниям товаров. Система состоит из веб-интерфейса для загрузки файлов, фонового процессора для обработки данных, и системы отслеживания прогресса в реальном времени.

Архитектура основана на асинхронной обработке с использованием очередей задач, что позволяет обрабатывать большие файлы без блокировки веб-интерфейса и предоставлять пользователям информацию о прогрессе выполнения.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Web Browser (User Interface)                           │
│  - File Upload Form                                     │
│  - Authentication                                       │
│  - Progress Tracking                                    │
│  - Download Results                                     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/WebSocket
                     ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Web Application                                │
│  - Authentication endpoints                             │
│  - File upload handling                                 │
│  - Task status API                                      │
│  - WebSocket for real-time updates                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│  File Storage   │    │  Redis Task Queue & Cache       │
│  (Session-based)│    │  - Task queue management        │
│  - Upload files │    │  - Progress tracking            │
│  - Result files │    │  - Session data                 │
└─────────────────┘    └────────────┬────────────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────────────┐
                       │  Celery Worker Processes        │
                       │  - Excel file processing        │
                       │  - TNVED code lookup            │
                       │  - Progress reporting           │
                       └────────────┬────────────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────────────┐
                       │  Existing TNVED System         │
                       │  - TNVEDSearcher                │
                       │  - ChromaDB                     │
                       │  - FRIDA embeddings             │
                       └─────────────────────────────────┘
```

### Component Interaction Flow

1. **User Authentication**: Пользователь авторизуется через веб-форму
2. **File Upload**: Загружает Excel файл через веб-интерфейс
3. **Task Creation**: FastAPI создает задачу в Redis очереди
4. **Background Processing**: Celery worker обрабатывает файл асинхронно
5. **Progress Updates**: Worker отправляет обновления прогресса через Redis
6. **Real-time Feedback**: WebSocket передает обновления в браузер
7. **Result Delivery**: Обработанный файл становится доступен для скачивания

## Components and Interfaces

### 1. Web Application (FastAPI)

**Responsibility**: Предоставление веб-интерфейса и API для взаимодействия с пользователями

**Interface**:
```python
from fastapi import FastAPI, UploadFile, WebSocket, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

class ProcessingRequest(BaseModel):
    process_mode: str  # "all" or "empty_only"
    algorithm: str     # "similarity_top1" or "llm_reasoning"

class TaskStatus(BaseModel):
    task_id: str
    status: str        # "pending", "processing", "completed", "failed"
    progress: float    # 0.0 to 1.0
    processed_rows: int
    total_rows: int
    error_count: int
    estimated_time_remaining: Optional[int]  # seconds

class BatchProcessorApp:
    def __init__(self):
        self.app = FastAPI(title="Batch Excel Processor")
        self.security = HTTPBasic()
        self._setup_routes()
    
    async def authenticate_user(self, credentials: HTTPBasicCredentials) -> str:
        """Проверяет учетные данные пользователя"""
        pass
    
    async def upload_file(
        self, 
        file: UploadFile, 
        request: ProcessingRequest,
        user: str = Depends(authenticate_user)
    ) -> dict:
        """Загружает файл и создает задачу обработки"""
        pass
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Возвращает статус задачи"""
        pass
    
    async def download_result(self, task_id: str) -> FileResponse:
        """Скачивает обработанный файл"""
        pass
    
    async def websocket_endpoint(self, websocket: WebSocket, task_id: str):
        """WebSocket для real-time обновлений прогресса"""
        pass
```

**API Endpoints**:

1. **POST /auth/login** - Аутентификация пользователя
2. **POST /upload** - Загрузка файла и создание задачи
3. **GET /task/{task_id}/status** - Получение статуса задачи
4. **GET /task/{task_id}/download** - Скачивание результата
5. **WebSocket /ws/{task_id}** - Real-time обновления прогресса

### 2. File Manager

**Responsibility**: Управление загруженными и обработанными файлами

**Interface**:
```python
import os
import uuid
from pathlib import Path

class FileManager:
    def __init__(self, base_path: str = "./temp_files"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def create_session_directory(self, session_id: str) -> Path:
        """Создает директорию для сессии пользователя"""
        session_dir = self.base_path / session_id
        session_dir.mkdir(exist_ok=True)
        return session_dir
    
    def save_uploaded_file(self, session_id: str, file: UploadFile) -> Path:
        """Сохраняет загруженный файл"""
        pass
    
    def save_processed_file(self, session_id: str, df: pd.DataFrame, original_filename: str) -> Path:
        """Сохраняет обработанный файл"""
        pass
    
    def cleanup_session(self, session_id: str) -> None:
        """Удаляет файлы сессии"""
        pass
    
    def schedule_cleanup(self, session_id: str, delay_hours: int = 24) -> None:
        """Планирует автоматическую очистку файлов"""
        pass
```

### 3. Excel Processor

**Responsibility**: Обработка Excel файлов с оптимизацией памяти

**Interface**:
```python
import pandas as pd
from typing import Iterator, Tuple, Optional

class ExcelProcessor:
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str, int]:
        """
        Валидирует Excel файл
        
        Returns:
            (is_valid, error_message, total_rows)
        """
        pass
    
    def read_file_chunked(
        self, 
        file_path: Path, 
        process_mode: str = "all"
    ) -> Iterator[Tuple[pd.DataFrame, int, int]]:
        """
        Читает файл по частям для экономии памяти
        
        Args:
            file_path: Путь к Excel файлу
            process_mode: "all" или "empty_only"
            
        Yields:
            (chunk_dataframe, chunk_start_row, total_rows)
        """
        pass
    
    def filter_rows_for_processing(
        self, 
        df: pd.DataFrame, 
        process_mode: str
    ) -> pd.DataFrame:
        """Фильтрует строки согласно режиму обработки"""
        pass
    
    def write_results(
        self, 
        original_file: Path, 
        results: List[ProcessingResult], 
        output_file: Path
    ) -> None:
        """Записывает результаты в новый Excel файл"""
        pass
```

### 4. Task Queue Manager (Celery Integration)

**Responsibility**: Управление очередью задач и фоновой обработкой

**Interface**:
```python
from celery import Celery
from typing import Dict, Any

class TaskQueueManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.celery_app = Celery(
            'batch_processor',
            broker=redis_url,
            backend=redis_url
        )
        self._configure_celery()
    
    def create_processing_task(
        self,
        session_id: str,
        file_path: str,
        process_mode: str,
        algorithm: str
    ) -> str:
        """Создает задачу обработки файла"""
        pass
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Получает статус задачи"""
        pass
    
    def update_task_progress(
        self,
        task_id: str,
        progress: float,
        processed_rows: int,
        total_rows: int,
        error_count: int = 0
    ) -> None:
        """Обновляет прогресс задачи"""
        pass
```

### 5. TNVED Code Selector

**Responsibility**: Выбор кодов ТНВЭД с использованием различных алгоритмов

**Interface**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ProcessingResult:
    row_index: int
    original_description: str
    tnved_code: Optional[str]
    selection_reason: str
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None

class TNVEDSelector(ABC):
    @abstractmethod
    def select_code(self, description: str) -> ProcessingResult:
        """Выбирает код ТНВЭД для описания товара"""
        pass

class SimilarityTop1Selector(TNVEDSelector):
    def __init__(self, tnved_searcher, confidence_threshold: float = 0.7):
        self.searcher = tnved_searcher
        self.confidence_threshold = confidence_threshold
    
    def select_code(self, description: str) -> ProcessingResult:
        """Выбирает код с наивысшим similarity score"""
        pass

class LLMReasoningSelector(TNVEDSelector):
    def __init__(self, tnved_searcher, llm_provider, top_k: int = 5):
        self.searcher = tnved_searcher
        self.llm_provider = llm_provider
        self.top_k = top_k
    
    def select_code(self, description: str) -> ProcessingResult:
        """Использует LLM для анализа top-k результатов"""
        pass

class SelectorFactory:
    @staticmethod
    def create_selector(algorithm: str, **kwargs) -> TNVEDSelector:
        """Фабрика для создания селекторов"""
        if algorithm == "similarity_top1":
            return SimilarityTop1Selector(**kwargs)
        elif algorithm == "llm_reasoning":
            return LLMReasoningSelector(**kwargs)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
```

### 6. Background Task Worker

**Responsibility**: Выполнение фоновой обработки файлов

**Interface**:
```python
from celery import Task
import time

class ProcessingTask(Task):
    def __init__(self):
        self.excel_processor = ExcelProcessor()
        self.file_manager = FileManager()
    
    def run(
        self,
        session_id: str,
        file_path: str,
        process_mode: str,
        algorithm: str
    ) -> Dict[str, Any]:
        """
        Основная функция обработки файла
        
        Returns:
            Результат обработки с метриками
        """
        try:
            # Валидация файла
            is_valid, error_msg, total_rows = self.excel_processor.validate_file(file_path)
            if not is_valid:
                return {"status": "failed", "error": error_msg}
            
            # Создание селектора
            selector = SelectorFactory.create_selector(algorithm)
            
            # Обработка по частям
            results = []
            processed_count = 0
            error_count = 0
            
            for chunk, start_row, total in self.excel_processor.read_file_chunked(
                file_path, process_mode
            ):
                chunk_results = self._process_chunk(chunk, selector, start_row)
                results.extend(chunk_results)
                
                processed_count += len(chunk_results)
                error_count += sum(1 for r in chunk_results if r.tnved_code is None)
                
                # Обновление прогресса
                progress = processed_count / total
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': progress,
                        'processed_rows': processed_count,
                        'total_rows': total,
                        'error_count': error_count
                    }
                )
            
            # Сохранение результатов
            output_path = self.file_manager.save_processed_file(
                session_id, results, file_path
            )
            
            return {
                "status": "completed",
                "output_file": str(output_path),
                "processed_rows": processed_count,
                "error_count": error_count
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _process_chunk(
        self, 
        chunk: pd.DataFrame, 
        selector: TNVEDSelector,
        start_row: int
    ) -> List[ProcessingResult]:
        """Обрабатывает один chunk данных"""
        pass
```

### 7. Progress Tracker

**Responsibility**: Отслеживание и передача прогресса обработки

**Interface**:
```python
import redis
import json
from typing import Dict, Any

class ProgressTracker:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def update_progress(
        self,
        task_id: str,
        progress: float,
        processed_rows: int,
        total_rows: int,
        error_count: int = 0,
        estimated_time_remaining: Optional[int] = None
    ) -> None:
        """Обновляет прогресс задачи в Redis"""
        progress_data = {
            "progress": progress,
            "processed_rows": processed_rows,
            "total_rows": total_rows,
            "error_count": error_count,
            "estimated_time_remaining": estimated_time_remaining,
            "timestamp": time.time()
        }
        
        # Сохранение в Redis
        self.redis.setex(
            f"progress:{task_id}",
            3600,  # TTL 1 час
            json.dumps(progress_data)
        )
        
        # Публикация для WebSocket
        self.redis.publish(f"progress_channel:{task_id}", json.dumps(progress_data))
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получает текущий прогресс задачи"""
        data = self.redis.get(f"progress:{task_id}")
        return json.loads(data) if data else None
```

## Data Models

### ProcessingSession

```python
@dataclass
class ProcessingSession:
    session_id: str
    user_id: str
    created_at: datetime
    original_filename: str
    file_path: Path
    process_mode: str      # "all" or "empty_only"
    algorithm: str         # "similarity_top1" or "llm_reasoning"
    task_id: Optional[str] = None
    status: str = "created"  # "created", "processing", "completed", "failed"
```

### ProcessingResult

```python
@dataclass
class ProcessingResult:
    row_index: int
    original_description: str
    tnved_code: Optional[str]
    selection_reason: str
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
```

### TaskMetrics

```python
@dataclass
class TaskMetrics:
    task_id: str
    total_rows: int
    processed_rows: int
    successful_rows: int
    error_count: int
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    average_time_per_row_ms: Optional[float] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Authentication Behavior Consistency

*For any* set of user credentials, the system should authenticate valid credentials and display the upload interface, while rejecting invalid credentials with error messages and maintaining the login form.
**Validates: Requirements 1.2, 1.3**

### Property 2: File Validation Completeness

*For any* uploaded Excel file, the system should validate file format and required column presence, displaying descriptive error messages for invalid files while allowing re-upload.
**Validates: Requirements 1.4, 1.5**

### Property 3: Row Processing Completeness

*For any* Excel file with mixed empty and non-empty "Product Detailed Description" values, the system should process all non-empty rows using the configured algorithm and continue processing despite individual row errors.
**Validates: Requirements 2.1, 2.2, 2.4**

### Property 4: Output File Structure Consistency

*For any* processed Excel file, the output should preserve all original columns and data while adding exactly two new columns ("TNVED_Code" and "Selection_Reason") with appropriate values for each processed row.
**Validates: Requirements 2.3, 2.5, 4.1, 4.2, 4.3**

### Property 5: Algorithm Selection Behavior

*For any* processing request with algorithm configuration, the system should use similarity_top1 for highest similarity score selection with formatted reasons, use llm_reasoning for LLM-based analysis with explanatory reasons, and default to similarity_top1 with warnings for invalid configurations.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 6: Download Availability

*For any* completed processing task, the system should immediately provide a downloadable file with proper handling of cases where no suitable codes are found.
**Validates: Requirements 4.4, 4.5**

### Property 7: Progress Tracking Accuracy

*For any* file processing operation, the system should provide real-time progress updates, display error counts during processing, show completion status with download links, and provide time estimates for long-running operations.
**Validates: Requirements 5.2, 5.3, 5.4, 5.5**

### Property 8: User Data Isolation

*For any* concurrent users of the system, each user's uploaded and processed files should be stored in session-specific directories with complete isolation from other users' data.
**Validates: Requirements 6.1, 6.3**

### Property 9: Automatic Cleanup Scheduling

*For any* file processing session, the system should schedule automatic deletion of files after 24 hours and clean up files when sessions expire.
**Validates: Requirements 6.2, 6.4**

### Property 10: Security Path Validation

*For any* file operation, the system should validate file paths to prevent directory traversal attacks and other path-based security vulnerabilities.
**Validates: Requirements 6.5**

### Property 11: Comprehensive Logging

*For any* processing operation, the system should log processing statistics, detailed error information, and success metrics, while providing appropriate resource management under high load.
**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

### Property 12: Selective Processing Mode Behavior

*For any* file with existing HTS Code values, when "Process only empty codes" mode is selected, the system should skip rows with existing codes while preserving their values, and when "Process all rows" mode is selected, the system should process all rows regardless of existing values.
**Validates: Requirements 8.2, 8.3, 8.4**

### Property 13: Processing Mode Reporting

*For any* selective processing operation, the system should accurately report the count of processed versus skipped rows in the completion summary.
**Validates: Requirements 8.5**

### Property 14: Quality Assessment Integration

*For any* processed description, the system should include appropriate quality indicators: similarity scores for similarity_top1 algorithm, detailed reasoning for llm_reasoning algorithm, low confidence flags for scores below threshold, uncertainty indicators for similar scores, and manual review suggestions when no relevant codes are found.
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

## Error Handling

### Error Categories

1. **Authentication Errors**
   - Invalid credentials
   - Session expiration
   - Authorization failures

2. **File Upload Errors**
   - Invalid file format (not Excel)
   - Missing required columns
   - File size limits exceeded
   - Corrupted files

3. **Processing Errors**
   - Individual row processing failures
   - TNVED search service unavailable
   - LLM service failures (for llm_reasoning algorithm)
   - Memory/resource exhaustion

4. **System Errors**
   - Redis connection failures
   - Celery worker failures
   - File system errors
   - Network connectivity issues

### Error Handling Strategy

**Graceful Degradation**: System continues operating with reduced functionality when non-critical components fail

**Error Recovery**:
- Retry logic for transient network errors (TNVED search, LLM calls)
- Individual row failures don't stop batch processing
- Automatic fallback to similarity_top1 when LLM fails
- Queue management for worker failures

**User Communication**:
- Clear error messages with actionable guidance
- Progress updates include error counts
- Detailed error logs for debugging (admin only)
- Graceful handling of session timeouts

**Error Logging**:
```python
class ErrorHandler:
    def log_processing_error(
        self,
        task_id: str,
        row_index: int,
        description: str,
        error: Exception
    ) -> None:
        """Logs individual row processing errors"""
        pass
    
    def log_system_error(
        self,
        component: str,
        operation: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Logs system-level errors with context"""
        pass
```

## Testing Strategy

### Unit Testing

Unit tests will verify specific functionality of individual components:

1. **Authentication Tests**
   - Test credential validation with various input formats
   - Test session management and expiration
   - Test authorization for different user roles

2. **File Processing Tests**
   - Test Excel file validation with valid/invalid files
   - Test chunked reading with different file sizes
   - Test selective processing modes (all vs empty_only)

3. **TNVED Selection Tests**
   - Test similarity_top1 algorithm with known inputs
   - Test LLM reasoning algorithm with mock LLM responses
   - Test fallback behavior when algorithms fail

4. **Progress Tracking Tests**
   - Test progress calculation accuracy
   - Test real-time update mechanisms
   - Test WebSocket communication

### Property-Based Testing

Property-based tests will verify universal properties across many randomly generated inputs using the **Hypothesis** library for Python.

**Configuration**: Each property test should run a minimum of 100 iterations to ensure thorough coverage of the input space.

**Test Tagging**: Each property-based test must include a comment with this format:
```python
# Feature: batch-excel-processor, Property {number}: {property_text}
```

**Property Test Implementation Requirements**:
- Each correctness property listed above must be implemented as a single property-based test
- Tests should use Hypothesis strategies to generate diverse Excel files, user inputs, and processing scenarios
- Tests should be deterministic (use fixed random seeds where needed)
- Tests should be fast enough to run in CI/CD pipeline

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st
import pandas as pd

# Feature: batch-excel-processor, Property 4: Output File Structure Consistency
@given(
    st.data(),
    st.lists(st.text(min_size=1), min_size=1, max_size=100)
)
def test_output_file_structure_consistency(data, descriptions):
    # Generate Excel file with descriptions
    df = pd.DataFrame({"Product Detailed Description": descriptions})
    
    # Process file
    processor = ExcelProcessor()
    results = processor.process_file(df, "similarity_top1")
    
    # Verify structure
    assert "TNVED_Code" in results.columns
    assert "Selection_Reason" in results.columns
    assert len(results) == len(descriptions)
    # Verify all original columns preserved
    for col in df.columns:
        assert col in results.columns
        assert results[col].equals(df[col])
```

### Integration Testing

Integration tests will verify end-to-end workflows:

1. **Complete Processing Workflow**
   - Upload file → Process → Download results
   - Test with various file sizes and content types
   - Verify progress tracking throughout process

2. **Concurrent User Testing**
   - Multiple users uploading files simultaneously
   - Verify data isolation and resource management
   - Test session cleanup and file management

3. **Error Recovery Testing**
   - Simulate various failure scenarios
   - Verify graceful degradation and recovery
   - Test retry mechanisms and fallback behavior

### Performance Testing

1. **Load Testing**
   - Test with large Excel files (10K+ rows)
   - Concurrent user scenarios
   - Memory usage monitoring

2. **Scalability Testing**
   - Multiple Celery workers
   - Redis performance under load
   - File system I/O optimization

### Test Data

- Use synthetic Excel files with various structures and sizes
- Include edge cases: empty files, files with special characters, very long descriptions
- Test with both valid and invalid TNVED search scenarios
- Generate realistic product descriptions for testing

## Deployment Architecture

### Production Deployment Stack

```
┌─────────────────────────────────────────────────────────┐
│  Load Balancer (Nginx)                                  │
│  - SSL termination                                      │
│  - Static file serving                                  │
│  - Request routing                                      │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│  FastAPI App    │    │  FastAPI App                    │
│  (Instance 1)   │    │  (Instance 2)                   │
│  - Web UI       │    │  - Web UI                       │
│  - API endpoints│    │  - API endpoints                │
│  - WebSocket    │    │  - WebSocket                    │
└─────────────────┘    └─────────────────────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Redis Cluster                                          │
│  - Task queue (Celery broker)                          │
│  - Progress tracking                                    │
│  - Session storage                                      │
│  - Caching                                             │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│  Celery Worker  │    │  Celery Worker                  │
│  (Instance 1)   │    │  (Instance 2)                   │
│  - File proc.   │    │  - File processing              │
│  - TNVED search │    │  - TNVED search                 │
│  - Progress upd.│    │  - Progress updates             │
└─────────────────┘    └─────────────────────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Existing TNVED System                                  │
│  - ChromaDB                                            │
│  - FRIDA embeddings                                    │
│  - TNVEDSearcher                                       │
└─────────────────────────────────────────────────────────┘
```

### Container Configuration

**Docker Compose Setup**:
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./temp_files:/app/temp_files
    depends_on:
      - redis
  
  worker:
    build: .
    command: celery -A batch_processor.celery worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./temp_files:/app/temp_files
      - ./chroma_db:/app/chroma_db
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Environment Configuration

```yaml
# config.yaml
app:
  title: "Batch Excel Processor"
  debug: false
  secret_key: "${SECRET_KEY}"
  
auth:
  users:
    - username: "admin"
      password_hash: "${ADMIN_PASSWORD_HASH}"
    - username: "user1"
      password_hash: "${USER1_PASSWORD_HASH}"

file_processing:
  max_file_size_mb: 100
  chunk_size: 1000
  temp_dir: "./temp_files"
  cleanup_hours: 24

celery:
  broker_url: "${REDIS_URL}"
  result_backend: "${REDIS_URL}"
  task_serializer: "json"
  accept_content: ["json"]
  result_serializer: "json"
  timezone: "UTC"

tnved:
  searcher_config:
    db_path: "./chroma_db"
    model_name: "ai-forever/FRIDA"
    top_k_default: 5
  
  algorithms:
    similarity_top1:
      confidence_threshold: 0.7
    llm_reasoning:
      provider: "openai"  # or "local"
      model: "gpt-4"
      top_k: 5

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/batch_processor.log"
  max_size_mb: 100
  backup_count: 5
```

### Security Considerations

1. **Authentication & Authorization**
   - HTTP Basic Auth for simplicity (can be upgraded to OAuth2/JWT)
   - Password hashing with bcrypt
   - Session-based access control

2. **File Security**
   - File type validation (Excel only)
   - File size limits
   - Path traversal prevention
   - Automatic cleanup of temporary files

3. **Network Security**
   - HTTPS in production
   - CORS configuration
   - Rate limiting on API endpoints

4. **Data Protection**
   - User data isolation
   - Secure temporary file storage
   - No persistent storage of sensitive data

### Monitoring & Observability

1. **Application Metrics**
   - Processing time per file
   - Success/failure rates
   - Queue length and worker utilization
   - Memory and CPU usage

2. **Business Metrics**
   - Files processed per day
   - Average file size
   - Algorithm usage statistics
   - Error patterns and frequencies

3. **Health Checks**
   - Web application health
   - Celery worker status
   - Redis connectivity
   - TNVED system availability

4. **Alerting**
   - High error rates
   - Queue backlog
   - Resource exhaustion
   - Service unavailability

### Scalability Considerations

1. **Horizontal Scaling**
   - Multiple FastAPI instances behind load balancer
   - Multiple Celery workers for parallel processing
   - Redis clustering for high availability

2. **Performance Optimization**
   - Chunked file processing for memory efficiency
   - Connection pooling for database access
   - Caching of frequent TNVED searches
   - Async I/O for web requests

3. **Resource Management**
   - Memory limits for workers
   - Queue size limits
   - File size restrictions
   - Processing timeouts

## Future Enhancements

1. **Advanced Features**
   - Batch processing history and analytics
   - Custom algorithm configuration per user
   - Integration with external ERP systems
   - Multi-language support for descriptions

2. **Performance Improvements**
   - Caching of TNVED search results
   - Parallel processing within single files
   - Streaming file processing for very large files
   - GPU acceleration for embeddings

3. **User Experience**
   - Drag-and-drop file upload
   - Preview of processing results before download
   - Email notifications for completed processing
   - Mobile-responsive interface

4. **Integration Capabilities**
   - REST API for programmatic access
   - Webhook notifications
   - Integration with cloud storage (S3, Google Drive)
   - Export to various formats (CSV, JSON, XML)

5. **Advanced Analytics**
   - Processing quality metrics
   - Algorithm performance comparison
   - User behavior analytics
   - Cost optimization insights