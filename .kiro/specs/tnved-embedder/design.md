# Design Document: ТНВЭД Embedder System

## Overview

Система ТНВЭД Embedder представляет собой Python-приложение для семантического поиска кодов ТНВЭД по текстовым описаниям товаров. Система состоит из двух основных компонентов:

1. **Загрузчик (Loader)**: Читает справочник ТНВЭД из Excel, нормализует тексты и загружает их в ChromaDB
2. **Поисковик (Searcher)**: Принимает текстовые запросы и возвращает наиболее релевантные коды ТНВЭД

Архитектура основана на векторном поиске с использованием эмбеддингов, что позволяет находить семантически близкие описания даже при различных формулировках.

## Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│  External Systems (HTTP Clients, Web Apps, etc.)         │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  REST API Layer (FastAPI)                                │
│  - /api/v1/search                                        │
│  - /api/v1/load                                          │
│  - /api/v1/code/{code}                                   │
│  - Authentication, Rate Limiting, CORS                   │
└────────────────────────┬─────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────────┐
│  Excel File     │            │  Search Requests    │
│  (ТНВЭД)        │            │  from API           │
└────────┬────────┘            └──────────┬──────────┘
         │                                │
         ▼                                │
┌─────────────────────────────────────┐   │
│  Text Normalization Pipeline        │◄──┘
│  - Lowercase conversion             │
│  - Natasha lemmatization            │
│  - Whitespace cleanup               │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Embedding Generation               │
│  (ai-forever/FRIDA via HuggingFace) │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  ChromaDB Vector Store              │
│  - Persistent storage               │
│  - Similarity search                │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Integration Layer (Optional)       │
│  - LangChain VectorStore wrapper    │
│  - LLM Provider abstraction         │
│  - Agent Tools                      │
└─────────────────────────────────────┘
```

### Component Layers

1. **Data Layer**: ChromaDB для хранения векторов и метаданных
2. **Processing Layer**: Нормализация текстов и генерация эмбеддингов
3. **Application Layer**: API для загрузки и поиска
4. **Configuration Layer**: Управление параметрами системы
5. **Integration Layer** (extensible): Интерфейсы для LLM и LangChain интеграции

### Extensibility Points

Система спроектирована с учетом будущих расширений:

- **LLM Integration**: Абстрактный интерфейс для подключения локальных или удаленных LLM (OpenAI, Anthropic, локальные модели)
- **LangChain Compatibility**: Wrapper классы для использования в качестве LangChain VectorStore и Retriever
- **Agentic RAG**: Инструменты (tools) для использования в LangChain агентах
- **Custom Embeddings**: Возможность замены модели эмбеддингов через конфигурацию
- **Plugin Architecture**: Расширение функциональности через наследование базовых классов

## Components and Interfaces

### 0. REST API Service

**Responsibility**: Предоставление HTTP API для внешних систем

**Interface**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query_time_ms: float

class LoadRequest(BaseModel):
    file_path: str
    batch_size: int = 100

class LoadResponse(BaseModel):
    records_loaded: int
    load_time_ms: float

class TNVEDAPIService:
    def __init__(self, searcher: TNVEDSearcher, loader: TNVEDLoader):
        self.app = FastAPI(title="ТНВЭД API")
        self.searcher = searcher
        self.loader = loader
        self._setup_routes()
    
    def _setup_routes(self):
        """Настройка API endpoints"""
        pass
```

**API Endpoints**:

1. **POST /api/v1/search** - Поиск кодов ТНВЭД
   ```json
   Request:
   {
     "query": "кофейные зерна арабика",
     "top_k": 5
   }
   
   Response:
   {
     "results": [
       {
         "code": "0901110000",
         "description": "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
         "normalized_text": "кофе нежареный неосвобожденный от кофеин",
         "similarity_score": 0.89
       }
     ],
     "query_time_ms": 45.2
   }
   ```

2. **POST /api/v1/load** - Загрузка данных из Excel
   ```json
   Request:
   {
     "file_path": "/path/to/tnved.xlsx",
     "batch_size": 100
   }
   
   Response:
   {
     "records_loaded": 13265,
     "load_time_ms": 125000.5
   }
   ```

3. **GET /api/v1/code/{code}** - Получение информации о конкретном коде
   ```json
   Response:
   {
     "code": "0901110000",
     "description": "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
     "normalized_text": "кофе нежареный неосвобожденный от кофеин"
   }
   ```

4. **GET /api/v1/health** - Проверка состояния сервиса
   ```json
   Response:
   {
     "status": "healthy",
     "database_records": 13265,
     "model_loaded": true
   }
   ```

5. **GET /api/v1/stats** - Статистика использования
   ```json
   Response:
   {
     "total_searches": 1523,
     "total_records": 13265,
     "avg_search_time_ms": 42.3,
     "uptime_seconds": 86400
   }
   ```

**API Features**:
- **Authentication**: Поддержка API ключей для безопасности
- **Rate Limiting**: Ограничение количества запросов
- **CORS**: Настройка для веб-приложений
- **OpenAPI/Swagger**: Автоматическая документация
- **Async Support**: Асинхронная обработка запросов
- **Error Handling**: Стандартизированные коды ошибок

### 1. TextNormalizer

**Responsibility**: Нормализация русских текстов для обеспечения консистентности

**Interface**:
```python
class TextNormalizer:
    def normalize(self, text: str) -> str:
        """
        Нормализует текст: lowercase, лемматизация, очистка
        
        Args:
            text: Исходный текст
            
        Returns:
            Нормализованный текст
        """
        pass
```

**Implementation Details**:
- Использует Natasha для морфологического анализа и лемматизации
- Применяет lowercase преобразование
- Удаляет избыточные пробелы и специальные символы
- Сохраняет семантическое значение текста

### 2. EmbeddingGenerator

**Responsibility**: Генерация векторных представлений текстов

**Interface**:
```python
class EmbeddingGenerator:
    def __init__(self, model_name: str = "ai-forever/FRIDA"):
        """Инициализирует модель эмбеддингов"""
        pass
    
    def generate(self, texts: List[str]) -> np.ndarray:
        """
        Генерирует эмбеддинги для списка текстов
        
        Args:
            texts: Список нормализованных текстов
            
        Returns:
            Массив векторов размерности (n, embedding_dim)
        """
        pass
```

**Implementation Details**:
- Загружает модель ai-forever/FRIDA из HuggingFace
- Поддерживает батч-обработку для эффективности
- Кэширует модель в памяти для повторного использования

### 3. TNVEDLoader

**Responsibility**: Загрузка справочника ТНВЭД в векторную БД

**Interface**:
```python
class TNVEDLoader:
    def __init__(
        self,
        db_path: str,
        normalizer: TextNormalizer,
        embedder: EmbeddingGenerator,
        batch_size: int = 100
    ):
        """Инициализирует загрузчик"""
        pass
    
    def load_from_excel(self, file_path: str) -> int:
        """
        Загружает данные из Excel в ChromaDB
        
        Args:
            file_path: Путь к файлу Excel
            
        Returns:
            Количество загруженных записей
        """
        pass
```

**Implementation Details**:
- Читает Excel с помощью pandas
- Обрабатывает данные батчами для управления памятью
- Обновляет существующие записи при дубликатах кодов
- Логирует прогресс загрузки

### 4. TNVEDSearcher

**Responsibility**: Поиск кодов ТНВЭД по текстовому описанию

**Interface**:
```python
class TNVEDSearcher:
    def __init__(
        self,
        db_path: str,
        normalizer: TextNormalizer,
        embedder: EmbeddingGenerator
    ):
        """Инициализирует поисковик"""
        pass
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Ищет наиболее релевантные коды ТНВЭД
        
        Args:
            query: Текстовое описание товара
            top_k: Количество результатов
            
        Returns:
            Список результатов с кодами и similarity scores
        """
        pass
```

**Implementation Details**:
- Нормализует запрос тем же способом, что и при загрузке
- Генерирует эмбеддинг запроса
- Выполняет similarity search в ChromaDB
- Возвращает результаты с метаданными

### 5. ChromaDBManager

**Responsibility**: Управление подключением и операциями с ChromaDB

**Interface**:
```python
class ChromaDBManager:
    def __init__(self, db_path: str, collection_name: str = "tnved"):
        """Инициализирует подключение к ChromaDB"""
        pass
    
    def add_batch(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        documents: List[str]
    ) -> None:
        """Добавляет батч записей в коллекцию"""
        pass
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int
    ) -> Dict:
        """Выполняет поиск по векторному представлению"""
        pass
```

**Implementation Details**:
- Использует persistent client для сохранения данных на диск
- Создает коллекцию при первом запуске
- Поддерживает upsert для обновления существующих записей

### 6. Config

**Responsibility**: Управление конфигурацией системы

**Interface**:
```python
@dataclass
class Config:
    model_name: str = "ai-forever/FRIDA"
    db_path: str = "./chroma_db"
    collection_name: str = "tnved"
    batch_size: int = 100
    top_k_results: int = 5
    
    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Загружает конфигурацию из файла"""
        pass
    
    @classmethod
    def from_env(cls) -> "Config":
        """Загружает конфигурацию из переменных окружения"""
        pass
```

## Data Models

### SearchResult

```python
@dataclass
class SearchResult:
    code: str              # Код ТНВЭД
    description: str       # Оригинальное описание
    normalized_text: str   # Нормализованный текст
    similarity_score: float  # Оценка схожести (0-1)
```

### TNVEDRecord

```python
@dataclass
class TNVEDRecord:
    code: str              # Код ТНВЭД (уникальный идентификатор)
    text_ex: str           # Оригинальное описание из столбца TextEx
    normalized_text: str   # Нормализованный текст для поиска
```

## Co
rrectness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Excel Data Extraction Completeness

*For any* Excel file with Code and TextEx columns, reading the file should extract all rows and both columns should be present in the output with matching values.
**Validates: Requirements 1.1**

### Property 2: Text Normalization Consistency

*For any* text string, applying the normalization pipeline should: (1) convert all characters to lowercase, (2) remove excessive whitespace, (3) apply Natasha lemmatization, and (4) produce the same output when applied multiple times (idempotence).
**Validates: Requirements 1.2, 1.3, 5.2, 5.3**

### Property 3: Embedding Determinism

*For any* normalized text, generating embeddings multiple times should produce identical vector representations, ensuring reproducibility of search results.
**Validates: Requirements 1.4, 2.2, 5.4**

### Property 4: Storage Round-Trip Integrity

*For any* ТНВЭД record (code, description, normalized text), after storing it in ChromaDB and retrieving it, all fields should match the original values.
**Validates: Requirements 1.5**

### Property 5: Search Normalization Consistency

*For any* search query text, the normalization applied during search should produce the same result as the normalization applied during data loading for identical input texts.
**Validates: Requirements 2.1**

### Property 6: Search Result Structure and Ranking

*For any* search query with top_k parameter, the system should return exactly top_k results (or fewer if database has fewer records), each result should contain code and description fields, and results should be ordered by similarity score in descending order.
**Validates: Requirements 2.3, 2.4, 5.5**

### Property 7: Invalid Query Handling

*For any* empty or whitespace-only query string, the search operation should raise an appropriate error without modifying the database state.
**Validates: Requirements 2.5**

### Property 8: Duplicate Code Idempotence

*For any* ТНВЭД code, loading records with the same code multiple times should result in only one record in the database with the most recent data, and the total count should not increase beyond the number of unique codes.
**Validates: Requirements 3.2**

### Property 9: Load Operation Count Accuracy

*For any* dataset loaded into the system, the reported count of processed records should equal the actual number of records stored in ChromaDB.
**Validates: Requirements 3.5**

### Property 10: Configuration Parameter Respect

*For any* valid configuration with custom model_name, db_path, or batch_size, the system should use those exact values rather than defaults, verifiable through system behavior.
**Validates: Requirements 4.2, 4.3, 4.4**

### Property 11: Configuration Fallback Behavior

*For any* missing or invalid configuration parameter, the system should use a documented default value and continue operation without crashing.
**Validates: Requirements 4.5**

## Error Handling

### Error Categories

1. **Input Validation Errors**
   - Empty or invalid Excel file paths
   - Missing required columns (Code, TextEx)
   - Empty search queries
   - Invalid configuration values

2. **Processing Errors**
   - Model loading failures (network issues, invalid model name)
   - Text normalization failures (malformed input)
   - Embedding generation failures (model errors)

3. **Database Errors**
   - ChromaDB connection failures
   - Collection creation/access errors
   - Batch insertion failures
   - Query execution errors

### Error Handling Strategy

**Fail-Fast Principle**: Validate inputs early and fail with clear error messages

**Error Recovery**:
- Retry logic for transient network errors (model download)
- Batch processing continues on individual record failures with logging
- Database operations use transactions where possible

**Logging**:
- All errors logged with context (timestamp, operation, input data)
- Warning level for recoverable errors
- Error level for operation failures
- Info level for successful operations with statistics

**User-Facing Errors**:
```python
class TNVEDError(Exception):
    """Base exception for ТНВЭД system"""
    pass

class DataLoadError(TNVEDError):
    """Raised when data loading fails"""
    pass

class SearchError(TNVEDError):
    """Raised when search operation fails"""
    pass

class ConfigurationError(TNVEDError):
    """Raised when configuration is invalid"""
    pass
```

## Testing Strategy

### Unit Testing

Unit tests will verify specific functionality of individual components:

1. **TextNormalizer Tests**
   - Test lowercase conversion with mixed case input
   - Test whitespace removal with various whitespace patterns
   - Test Natasha integration with sample Russian words
   - Test edge cases: empty strings, special characters

2. **EmbeddingGenerator Tests**
   - Test model loading succeeds
   - Test embedding dimension matches expected size
   - Test batch processing with different batch sizes

3. **ChromaDBManager Tests**
   - Test collection creation and connection
   - Test batch insertion with sample data
   - Test query execution returns expected format

4. **Config Tests**
   - Test loading from file with valid config
   - Test loading from environment variables
   - Test default values when config missing

### Property-Based Testing

Property-based tests will verify universal properties across many randomly generated inputs using the **Hypothesis** library for Python.

**Configuration**: Each property test should run a minimum of 100 iterations to ensure thorough coverage of the input space.

**Test Tagging**: Each property-based test must include a comment with this format:
```python
# Feature: tnved-embedder, Property {number}: {property_text}
```

**Property Test Implementation Requirements**:
- Each correctness property listed above must be implemented as a single property-based test
- Tests should use Hypothesis strategies to generate diverse inputs
- Tests should be deterministic (use fixed random seeds where needed)
- Tests should be fast enough to run in CI/CD pipeline

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st

# Feature: tnved-embedder, Property 2: Text Normalization Consistency
@given(st.text(min_size=1))
def test_normalization_idempotence(text):
    normalizer = TextNormalizer()
    normalized_once = normalizer.normalize(text)
    normalized_twice = normalizer.normalize(normalized_once)
    assert normalized_once == normalized_twice
    assert normalized_once.islower()
```

### Integration Testing

Integration tests will verify end-to-end workflows:

1. **Load and Search Workflow**
   - Load sample ТНВЭД data from Excel
   - Perform searches and verify results
   - Verify data persistence across restarts

2. **Configuration Integration**
   - Test system with different configurations
   - Verify configuration changes affect behavior

### Test Data

- Use subset of real ТНВЭД data (100-200 records) for integration tests
- Generate synthetic data for property tests
- Include edge cases: very long descriptions, special characters, numbers

## Performance Considerations

### Embedding Generation
- Batch processing to utilize GPU efficiently (if available)
- Model caching to avoid reloading
- Expected throughput: ~100-500 records/second depending on hardware

### Database Operations
- Batch insertions (default 100 records per batch)
- Index optimization in ChromaDB for faster similarity search
- Expected search latency: <100ms for top-5 results

### Memory Management
- Stream processing for large Excel files
- Batch size configurable based on available memory
- Expected memory usage: ~2-4GB for model + data

## Deployment Considerations

### Dependencies
```
# Core dependencies
pandas>=2.0.0
chromadb>=0.4.0
sentence-transformers>=2.2.0  # For HuggingFace models
natasha>=1.6.0
openpyxl>=3.1.0  # For Excel reading
python>=3.9

# API dependencies
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0

# Optional: LangChain integration
langchain>=0.1.0
langchain-community>=0.0.10

# Optional: LLM providers
openai>=1.0.0  # For OpenAI integration
```

### Deployment Modes

#### 1. Standalone Script Mode
Простой Python скрипт для локального использования:
```bash
python load_tnved.py --file tnved_full10_new.xlsx
python search_tnved.py --query "кофейные зерна"
```

#### 2. API Service Mode
REST API сервис для интеграции с другими системами:
```bash
uvicorn tnved_api:app --host 0.0.0.0 --port 8000
```

#### 3. Docker Container Mode
Контейнеризованное развертывание:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "tnved_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Setup
1. Install Python dependencies via pip/conda
2. Download FRIDA model on first run (automatic via HuggingFace)
3. Create ChromaDB directory with write permissions
4. Optional: Configure GPU support for faster embeddings
5. For API mode: Configure authentication keys and CORS settings

### Configuration File Example
```yaml
# config.yaml
model:
  name: "ai-forever/FRIDA"
  device: "cuda"  # or "cpu"

database:
  path: "./chroma_db"
  collection_name: "tnved"

processing:
  batch_size: 100
  
search:
  default_top_k: 5

# API Configuration
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  auth:
    enabled: true
    api_keys:
      - "key1_for_system_a"
      - "key2_for_system_b"
  cors:
    enabled: true
    origins:
      - "https://example.com"
      - "http://localhost:3000"
  rate_limit:
    requests_per_minute: 60
```

### Production Deployment Checklist

- [ ] Configure persistent storage for ChromaDB
- [ ] Set up API authentication and rate limiting
- [ ] Configure HTTPS/TLS for API endpoints
- [ ] Set up monitoring and logging (Prometheus, Grafana)
- [ ] Configure backup strategy for vector database
- [ ] Set up health checks and auto-restart
- [ ] Document API endpoints (OpenAPI/Swagger)
- [ ] Load test API under expected traffic
- [ ] Configure firewall rules for API access

## Extensibility Architecture

### LLM Integration Support

Система спроектирована с учетом будущей интеграции с LLM (локальными или удаленными):

**Abstraction Layer for LLM**:
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: List[SearchResult]) -> str:
        """Генерирует ответ на основе контекста из ТНВЭД"""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def generate(self, prompt: str, context: List[SearchResult]) -> str:
        # Реализация для OpenAI API
        pass

class LocalLLMProvider(LLMProvider):
    def __init__(self, model_path: str):
        # Поддержка локальных моделей (llama.cpp, vLLM и т.д.)
        pass
    
    def generate(self, prompt: str, context: List[SearchResult]) -> str:
        # Реализация для локальной модели
        pass
```

**Integration Points**:
1. **Retrieval Component**: Текущая система поиска становится retrieval компонентом
2. **Context Formatting**: Результаты поиска форматируются для LLM промпта
3. **Response Generation**: LLM генерирует ответ на основе найденных кодов ТНВЭД

### LangChain Agentic RAG Support

Архитектура поддерживает интеграцию с LangChain для agentic RAG:

**LangChain Integration Components**:

```python
from langchain.vectorstores.base import VectorStore
from langchain.embeddings.base import Embeddings

class TNVEDVectorStore(VectorStore):
    """
    LangChain-совместимый wrapper для ChromaDB
    Позволяет использовать ТНВЭД систему как retriever в LangChain
    """
    def __init__(self, chroma_manager: ChromaDBManager, embedder: EmbeddingGenerator):
        self.chroma = chroma_manager
        self.embedder = embedder
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Реализует LangChain VectorStore интерфейс"""
        pass
    
    def as_retriever(self, **kwargs) -> BaseRetriever:
        """Возвращает LangChain Retriever"""
        pass

class TNVEDEmbeddings(Embeddings):
    """
    LangChain-совместимый wrapper для FRIDA embeddings
    """
    def __init__(self, embedder: EmbeddingGenerator):
        self.embedder = embedder
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Реализует LangChain Embeddings интерфейс"""
        pass
    
    def embed_query(self, text: str) -> List[float]:
        """Реализует LangChain Embeddings интерфейс"""
        pass
```

**Agentic RAG Architecture**:

```
┌─────────────────────────────────────────┐
│  LangChain Agent                        │
│  - ReAct/Plan-and-Execute               │
│  - Tool calling                         │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  ТНВЭД Retriever Tool                   │
│  - search_tnved(query) -> codes         │
│  - get_code_details(code) -> info       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  TNVEDVectorStore (Current System)      │
│  - ChromaDB + FRIDA embeddings          │
└─────────────────────────────────────────┘
```

**Agent Tools for ТНВЭД**:
```python
from langchain.tools import BaseTool

class TNVEDSearchTool(BaseTool):
    name = "search_tnved"
    description = """
    Ищет коды ТНВЭД по описанию товара.
    Входные данные: текстовое описание товара на русском языке.
    Возвращает: список наиболее подходящих кодов ТНВЭД с описаниями.
    """
    
    def __init__(self, searcher: TNVEDSearcher):
        self.searcher = searcher
    
    def _run(self, query: str) -> str:
        results = self.searcher.search(query, top_k=5)
        return self._format_results(results)

class TNVEDCodeDetailsTool(BaseTool):
    name = "get_tnved_details"
    description = """
    Получает подробную информацию о конкретном коде ТНВЭД.
    Входные данные: код ТНВЭД (например, "101210000").
    Возвращает: полное описание и характеристики кода.
    """
    
    def _run(self, code: str) -> str:
        # Получение деталей из ChromaDB
        pass
```

**Example Agentic RAG Usage**:
```python
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI

# Инициализация компонентов
tnved_searcher = TNVEDSearcher(...)
tools = [
    TNVEDSearchTool(tnved_searcher),
    TNVEDCodeDetailsTool(...)
]

# Создание агента
llm = ChatOpenAI(temperature=0)
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Использование
response = agent.run(
    "Мне нужно найти код ТНВЭД для импорта кофейных зерен арабика из Бразилии"
)
```

### Extensibility Design Principles

1. **Interface Segregation**: Каждый компонент имеет четкий интерфейс
2. **Dependency Injection**: Компоненты получают зависимости через конструктор
3. **Plugin Architecture**: Новые провайдеры (LLM, embeddings) добавляются через наследование
4. **Configuration-Driven**: Выбор провайдеров через конфигурацию

### Additional Configuration for Extensions

```yaml
# config.yaml (extended)
model:
  name: "ai-forever/FRIDA"
  device: "cuda"

database:
  path: "./chroma_db"
  collection_name: "tnved"

processing:
  batch_size: 100

search:
  default_top_k: 5

# LLM Integration (optional)
llm:
  enabled: false
  provider: "openai"  # or "local"
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
  local:
    model_path: "./models/llama-2-7b"
    
# LangChain Integration (optional)
langchain:
  enabled: false
  agent_type: "react"  # or "plan-and-execute"
  tools:
    - "search_tnved"
    - "get_tnved_details"
```

## Future Enhancements

1. **Multi-language Support**: Extend to support descriptions in other languages
2. **Incremental Updates**: Support updating individual records without full reload
3. **Query Expansion**: Use synonyms and related terms to improve search
4. **Caching**: Cache frequent queries for faster response
5. **API Service**: Wrap functionality in REST API for remote access
6. **Monitoring**: Add metrics for search quality and system performance
7. **Advanced RAG**: Implement re-ranking, query decomposition, and multi-hop reasoning
8. **Fine-tuning**: Fine-tune embeddings model on ТНВЭД-specific data
