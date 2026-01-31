# Рекомендации по ускорению загрузки данных

## 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Загрузка URL

**Текущая скорость**: 1-3 записи в секунду  
**Время для 100,000 записей**: 9-28 часов  
**Причина**: Построчная обработка с проверкой существования каждой записи

### ✅ РЕШЕНИЕ: Используйте оптимизированный загрузчик

```bash
# Вместо старого url_database_manager_cli.py
python load_urls_fast.py data.parquet my_source

# Результат: 500-2000 записей/сек (в 200-1000 раз быстрее!)
# 100,000 записей = 1-3 минуты вместо 9-28 часов
```

**Подробности**: См. [docs/FAST_URL_LOADING.md](./FAST_URL_LOADING.md)

---

## Текущая ситуация

При загрузке десятков и сотен тысяч строк процесс занимает часы. Анализ кода выявил следующие узкие места:

### Основные проблемы производительности

1. **Построчная обработка в циклах Python** - медленные операции для больших объемов
2. **Генерация эмбеддингов** - самая затратная операция (модель FRIDA на CPU)
3. **Отсутствие bulk-операций** - данные вставляются батчами, но без оптимизации БД
4. **Проверка дубликатов для каждой записи** - множественные запросы к ChromaDB
5. **Нормализация текста в Python циклах** - неэффективно для больших объемов

## Рекомендации по оптимизации

### 1. Оптимизация генерации эмбеддингов (КРИТИЧНО)

**Проблема**: Генерация эмбеддингов на CPU для модели FRIDA - самое медленное место.

**Решения**:

#### A. Использование GPU (рекомендуется)
```python
# В config.yaml или при запуске
embedder = EmbeddingGenerator(
    model_name="ai-forever/FRIDA",
    device="cuda"  # Вместо "cpu"
)
```

**Ожидаемое ускорение**: 10-50x в зависимости от GPU

#### B. Увеличение batch_size для эмбеддингов
```python
# Текущий batch_size=100, увеличить до:
loader = TNVEDLoader(
    db_path="./chroma_db",
    normalizer=normalizer,
    embedder=embedder,
    batch_size=500  # Или 1000 для GPU
)
```

**Ожидаемое ускорение**: 2-3x

#### C. Использование более быстрой модели
```python
# Вместо FRIDA использовать более легкую модель:
embedder = EmbeddingGenerator(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cuda"
)
```

**Ожидаемое ускорение**: 3-5x (но может снизиться качество)

### 2. Оптимизация работы с ChromaDB

#### A. Использование bulk upsert вместо проверок
```python
# В services/chroma_manager.py - метод add_batch уже использует upsert
# Но можно оптимизировать размер батча:

# Для больших загрузок увеличить batch_size
LARGE_BATCH_SIZE = 1000  # Вместо 100

# ChromaDB эффективно обрабатывает большие батчи
self.collection.upsert(
    ids=ids,
    embeddings=embeddings,
    metadatas=metadatas,
    documents=documents
)
```

**Ожидаемое ускорение**: 2-3x

#### B. Отключение проверок дубликатов при первичной загрузке
```python
# В services/product_loader.py - метод _process_batch
# Добавить параметр skip_duplicate_check для первичной загрузки

def load_from_excel(self, file_path: str, source_name: str, 
                    skip_duplicate_check: bool = False) -> int:
    # При skip_duplicate_check=True использовать простую генерацию ID
    # без проверки существующих записей
```

**Ожидаемое ускорение**: 1.5-2x для больших объемов

### 3. Оптимизация обработки данных

#### A. Использование векторизованных операций pandas
```python
# Вместо циклов использовать векторизацию:

# МЕДЛЕННО:
normalized_codes = []
for code in df["Code"]:
    normalized_codes.append(validate_tnved_code(code))

# БЫСТРО:
df["Code"] = df["Code"].astype(str).str.zfill(10)
# Валидация через apply с векторизацией
df["Code"] = df["Code"].apply(lambda x: validate_tnved_code(x, strict=False))
```

**Ожидаемое ускорение**: 2-5x для обработки кодов

#### B. Параллельная обработка батчей
```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def load_from_excel_parallel(self, file_path: str, n_workers: int = 4):
    # Разделить DataFrame на части
    chunks = np.array_split(df, n_workers)
    
    # Обработать параллельно
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = executor.map(self._process_chunk, chunks)
    
    return sum(results)
```

**Ожидаемое ускорение**: 2-4x (зависит от CPU)

### 4. Оптимизация чтения Excel файлов

#### A. Использование более быстрых библиотек
```python
# Вместо pandas.read_excel использовать:
import openpyxl
from openpyxl import load_workbook

# Или для больших файлов:
import pyarrow.parquet as pq

# Конвертировать Excel в Parquet один раз:
df = pd.read_excel("data.xlsx")
df.to_parquet("data.parquet")

# Затем загружать из Parquet (в 10-100 раз быстрее):
df = pd.read_parquet("data.parquet")
```

**Ожидаемое ускорение**: 5-10x для чтения файлов

#### B. Чтение по частям (chunking)
```python
# Для очень больших файлов:
chunk_size = 10000
for chunk in pd.read_excel("data.xlsx", chunksize=chunk_size):
    process_chunk(chunk)
```

### 5. Оптимизация нормализации текста

```python
# В services/text_normalizer.py
# Использовать batch-обработку вместо циклов:

def normalize_batch(self, texts: List[str]) -> List[str]:
    """Batch normalization для ускорения"""
    # Применить все операции векторизованно
    import re
    
    # Создать Series для векторных операций
    s = pd.Series(texts)
    
    # Векторизованная нормализация
    s = s.str.lower()
    s = s.str.replace(r'[^\w\s]', '', regex=True)
    s = s.str.replace(r'\s+', ' ', regex=True)
    s = s.str.strip()
    
    return s.tolist()
```

**Ожидаемое ускорение**: 3-5x

## Практический план оптимизации

### Этап 1: Быстрые победы (1-2 часа работы)

1. **Переключиться на GPU** (если доступен)
   ```bash
   # Проверить наличие GPU
   python -c "import torch; print(torch.cuda.is_available())"
   
   # Запустить с GPU
   python load_tnved.py data.xlsx --device cuda --batch-size 500
   ```
   **Ожидаемый результат**: Ускорение в 10-20 раз

2. **Увеличить batch_size**
   ```bash
   python load_tnved.py data.xlsx --batch-size 500
   ```
   **Ожидаемый результат**: Ускорение в 2-3 раза

3. **Конвертировать Excel в Parquet**
   ```python
   # Один раз конвертировать
   df = pd.read_excel("large_data.xlsx")
   df.to_parquet("large_data.parquet")
   
   # Затем изменить load_from_excel для поддержки Parquet
   ```
   **Ожидаемый результат**: Ускорение чтения в 5-10 раз

### Этап 2: Средние оптимизации (4-8 часов работы)

4. **Добавить batch-нормализацию текста**
   - Модифицировать `TextNormalizer` для batch-обработки
   - Использовать векторизованные операции pandas

5. **Оптимизировать проверку дубликатов**
   - Добавить флаг `skip_duplicate_check` для первичной загрузки
   - Использовать in-memory кэш для проверенных ID

6. **Добавить прогресс-бар**
   ```python
   from tqdm import tqdm
   
   for batch in tqdm(batches, desc="Loading data"):
       process_batch(batch)
   ```

### Этап 3: Продвинутые оптимизации (1-2 дня работы)

7. **Параллельная обработка батчей**
   - Использовать `multiprocessing` для CPU-bound операций
   - Использовать `threading` для I/O-bound операций

8. **Оптимизация ChromaDB**
   - Настроить параметры ChromaDB для bulk-операций
   - Использовать транзакции (если поддерживается)

9. **Профилирование и точечная оптимизация**
   ```python
   import cProfile
   import pstats
   
   profiler = cProfile.Profile()
   profiler.enable()
   
   # Ваш код загрузки
   
   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(20)
   ```

## Ожидаемые результаты

### Текущая производительность (оценка)
- CPU: ~10-50 записей/сек
- Время для 100,000 записей: 30-150 минут

### После оптимизации Этап 1 (GPU + batch_size)
- GPU: ~500-2000 записей/сек
- Время для 100,000 записей: 1-3 минуты
- **Ускорение: 10-50x**

### После оптимизации Этап 2
- GPU + оптимизации: ~1000-3000 записей/сек
- Время для 100,000 записей: 30-100 секунд
- **Ускорение: 20-100x**

### После оптимизации Этап 3
- Полная оптимизация: ~2000-5000 записей/сек
- Время для 100,000 записей: 20-50 секунд
- **Ускорение: 50-200x**

## Пример оптимизированного кода

### Оптимизированный TNVEDLoader

```python
# services/tnved_loader_optimized.py

class OptimizedTNVEDLoader(TNVEDLoader):
    """Оптимизированная версия загрузчика"""
    
    def load_from_excel(
        self, 
        file_path: str,
        use_gpu: bool = True,
        large_batch_size: int = 1000,
        skip_validation: bool = False
    ) -> int:
        """
        Оптимизированная загрузка с поддержкой GPU и больших батчей
        """
        # Быстрое чтение (поддержка Parquet)
        if file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Векторизованная обработка кодов
        df["Code"] = df["Code"].astype(str).str.zfill(10)
        
        # Векторизованная нормализация текста
        df["NormalizedText"] = self._normalize_batch(df["TextEx"].tolist())
        
        # Обработка большими батчами
        total_processed = 0
        for i in range(0, len(df), large_batch_size):
            batch = df.iloc[i:i+large_batch_size]
            
            # Генерация эмбеддингов большим батчем
            embeddings = self.embedder.generate(
                batch["NormalizedText"].tolist(),
                batch_size=large_batch_size,
                prefix="search_document: "
            )
            
            # Bulk upsert
            self.db_manager.add_batch(
                ids=batch["Code"].tolist(),
                embeddings=embeddings.tolist(),
                metadatas=batch.to_dict('records'),
                documents=batch["NormalizedText"].tolist()
            )
            
            total_processed += len(batch)
            
        return total_processed
    
    def _normalize_batch(self, texts: List[str]) -> List[str]:
        """Векторизованная нормализация"""
        s = pd.Series(texts)
        s = s.str.lower()
        s = s.str.replace(r'[^\w\s]', '', regex=True)
        s = s.str.replace(r'\s+', ' ', regex=True)
        s = s.str.strip()
        return s.tolist()
```

## Мониторинг производительности

### Добавить логирование времени

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name: str):
    """Context manager для измерения времени"""
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.info(f"{name} took {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")

# Использование:
with timer("Loading Excel"):
    df = pd.read_excel(file_path)

with timer("Generating embeddings"):
    embeddings = embedder.generate(texts)

with timer("Storing in ChromaDB"):
    db_manager.add_batch(...)
```

## Рекомендации по инфраструктуре

### Для максимальной производительности

1. **Железо**:
   - GPU: NVIDIA с CUDA (минимум 8GB VRAM)
   - RAM: минимум 16GB, рекомендуется 32GB
   - SSD: для ChromaDB (не HDD)

2. **Конфигурация**:
   ```yaml
   # config.yaml
   model:
     device: cuda
     batch_size: 1000
   
   processing:
     batch_size: 1000
     workers: 4
   
   database:
     path: /fast-ssd/chroma_db
   ```

3. **Docker** (если используется):
   ```yaml
   # docker-compose.yml
   services:
     loader:
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: 1
                 capabilities: [gpu]
       shm_size: '2gb'  # Для больших батчей
   ```

## Заключение

Основные рекомендации по приоритетам:

1. **КРИТИЧНО**: Использовать GPU для генерации эмбеддингов (ускорение 10-50x)
2. **ВАЖНО**: Увеличить batch_size до 500-1000 (ускорение 2-3x)
3. **ВАЖНО**: Конвертировать Excel в Parquet (ускорение чтения 5-10x)
4. **ПОЛЕЗНО**: Векторизовать обработку данных (ускорение 2-5x)
5. **ОПЦИОНАЛЬНО**: Параллельная обработка (ускорение 2-4x)

**Суммарное ожидаемое ускорение: 50-200x**

Время загрузки 100,000 записей может сократиться с 2-3 часов до 1-3 минут.
