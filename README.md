# ТНВЭД Embedder System

Система для автоматического подбора кодов ТНВЭД (Товарная номенклатура внешнеэкономической деятельности) на основе текстового описания товара с использованием векторного поиска.

## Документация по работе
[Quick Cli](docs/QUICK_CLI_GUIDE.md)
[Load Description](docs/CLI_BATCH_PROCESSING.md)

## Основные команды
```bash
# Загрузить справочные данные ТНВЭД
python load_tnved.py xlsx/tnved_full10_new.xlsx

# Загрузить товарные данные с уже подобранными кодами
python load_tnved.py ../2026/26m3.xlsx --source-type product --source-name 2026m3 --config config.yaml

# Загрузить URL маппинги (если используете URL подбор)
python load_urls_fast.py import_26-01.xlsx --source-name import_26-01

# Подбор кодов
python batch_process_cli.py input.xlsx output.xlsx

# Интерактивный режим
python search_tnved.py --interactive

```


## Новые возможности: Поддержка товарных данных

Система теперь поддерживает загрузку и поиск по товарам с уже подобранными кодами ТНВЭД из различных источников:
- **Таможенные декларации** - реальные товары с подобранными кодами
- **Каталоги поставщиков** - товары с назначенными кодами ТНВЭД
- **Базы данных предприятий** - внутренние справочники товаров

Это позволяет значительно улучшить точность подбора кодов за счет использования реальных примеров товаров.

## Описание

Система использует:
- **ChromaDB** - векторная база данных для хранения и поиска
- **ai-forever/FRIDA** - модель эмбеддингов для русского языка с поддержкой task-specific префиксов
- **Natasha** - библиотека для нормализации русских текстов

### Типы данных

Система работает с двумя типами данных:

1. **Справочные записи (reference)** - официальные описания кодов ТНВЭД из справочника
2. **Товарные записи (product)** - реальные товары с подобранными кодами ТНВЭД

При поиске система автоматически ищет по обоим типам данных, приоритизируя справочные записи, но также показывая релевантные товарные примеры.

### Особенности FRIDA модели

Система использует task-specific префиксы для улучшения качества поиска:
- `search_document:` - для индексации описаний товаров в базе данных
- `search_query:` - для поисковых запросов пользователей

Использование правильных префиксов улучшает точность поиска на **20-50%** за счет лучшего разделения релевантных и нерелевантных результатов. Подробнее см. `docs/FRIDA_PREFIX_USAGE.md`.

## Структура проекта

```
.
├── models/              # Модели данных
│   ├── tnved_record.py     # Модель записи ТНВЭД
│   ├── product_record.py   # Модель товарной записи (NEW)
│   └── search_result.py    # Модель результата поиска (ENHANCED)
├── services/            # Сервисы системы
│   ├── chroma_manager.py      # Управление ChromaDB (ENHANCED)
│   ├── embedding_generator.py # Генерация эмбеддингов
│   ├── text_normalizer.py     # Нормализация текста
│   ├── tnved_loader.py        # Загрузка справочных данных
│   ├── product_loader.py      # Загрузка товарных данных (NEW)
│   ├── tnved_searcher.py      # Поиск по базе
│   └── enhanced_searcher.py   # Расширенный поиск (NEW)
├── utils/               # Утилиты
│   ├── config.py           # Управление конфигурацией (ENHANCED)
│   ├── logger.py           # Настройка логирования
│   └── tnved_validator.py  # Валидация кодов ТНВЭД (NEW)
├── benchmarks/          # Тестирование и сравнение моделей
│   ├── test_single_model.py      # Тест одной модели
│   ├── compare_models.py         # Сравнение всех моделей
│   ├── compare_search_results.py # Сравнение результатов
│   └── compare_prefix_impact.py  # Сравнение префиксов
├── docs/                # Документация
│   ├── MODEL_ALTERNATIVES_SUMMARY.md  # Альтернативы FRIDA
│   ├── QUICK_MODEL_COMPARISON.md      # Быстрый старт
│   ├── MODEL_COMPARISON_GUIDE.md      # Полное руководство
│   ├── FAQ_СРАВНЕНИЕ_МОДЕЛЕЙ.md       # FAQ
│   ├── FRIDA_PREFIX_USAGE.md          # Использование префиксов
│   └── ... (другие документы)
├── tests/               # Тесты
│   ├── test_integration.py    # Интеграционные тесты (NEW)
│   ├── test_product_loader.py # Тесты загрузчика товаров (NEW)
│   └── ... (другие тесты)
├── config.yaml          # Конфигурационный файл (ENHANCED)
├── load_tnved.py        # CLI для загрузки данных (ENHANCED)
├── search_tnved.py      # CLI для поиска (ENHANCED)
└── requirements.txt     # Зависимости Python
```

## Форматы данных

### Справочные данные (reference)

Excel файл должен содержать колонки:
- **Code** - код ТНВЭД (10 цифр)
- **TextEx** - описание товара

Пример:
```
Code        | TextEx
0901110000  | КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА
0902000000  | ЧАЙ ЗЕЛЕНЫЙ
1701110000  | САХАР БЕЛЫЙ КРИСТАЛЛИЧЕСКИЙ
```

### Товарные данные (product)

Excel файл должен содержать колонки:
- **Code** - код ТНВЭД (10 цифр)
- **TextEx** - описание товара
- **SourceID** (опционально) - идентификатор в исходной системе

Пример:
```
Code        | TextEx                           | SourceID
0901110000  | Кофе арабика зерновой 1кг       | декларация_001
0901110000  | Кофе арабика молотый 500г       | декларация_002
0902000000  | Чай зеленый листовой премиум    | каталог_003
```

**Примеры источников товарных данных:**
- **Таможенные декларации**: `customs_2024_q1`, `customs_declarations_moscow`
- **Каталоги поставщиков**: `supplier_abc_catalog`, `distributor_xyz_products`
- **Внутренние справочники**: `company_product_base`, `erp_system_export`

`source_name` считается именем набора данных. Повторная загрузка того же `source_name`
заменяет старые product-записи только после явного подтверждения.

Product-записи в ChromaDB получают технический ID:
```text
product:{code}:{source_name}:{excel_row_number}
```
Например: `product:0901110000:customs_2024_q1:2`. Код ТНВЭД хранится в
metadata как `code`; бизнес-логика и поиск не должны извлекать код из ID.

**Пример файла:** См. `examples/example_product_data.csv` для примера формата данных.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте конфигурацию в `config.yaml` (опционально)

### Использование GPU (CUDA)

По умолчанию система использует CPU. Для использования GPU:

**Требования:**
- NVIDIA GPU с поддержкой CUDA
- Минимум 4GB видеопамяти (модель FRIDA требует ~3.1GB)

**Установка PyTorch с CUDA:**
```bash
# Удалить CPU-версию
pip uninstall torch torchvision torchaudio -y

# Установить CUDA-версию (для CUDA 12.x)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Проверить установку
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

**Настройка:**
```yaml
# config.yaml
model:
  device: "cuda"  # Изменить с "cpu" на "cuda"

processing:
  batch_size: 32  # Уменьшить для GPU с малой памятью
```

**⚠️ Важно:** Для GPU с 3GB памяти (например, GTX 1060) рекомендуется использовать CPU из-за ограничений памяти. См. `docs/CUDA_SETUP_RU.md` для деталей.

## Конфигурация

Система поддерживает конфигурацию через:
- **Файл config.yaml** - основной способ конфигурации
- **Переменные окружения** - для переопределения параметров

### Пример config.yaml

```yaml
model:
  name: "ai-forever/FRIDA"
  device: "cpu"  # или "cuda" для GPU

database:
  path: "./chroma_db"
  collection_name: "tnved"
  default_source_name: "unknown"  # NEW: имя источника по умолчанию

processing:
  batch_size: 100

search:
  default_top_k: 5
  group_by_code: false      # NEW: группировка результатов по коду
  prioritize_reference: true # NEW: приоритет справочных записей

# NEW: Настройки источников данных
sources:
  reference:
    name: "tnved_official"
    display_name: "Официальный справочник ТНВЭД"
  product:
    default_name: "unknown_products"
    display_name: "Товары с подобранными кодами"

logging:
  level: "INFO"
  file: "logs/tnved_embedder.log"
```

### Переменные окружения

- `TNVED_MODEL_NAME` - название модели эмбеддингов
- `TNVED_MODEL_DEVICE` - устройство (cpu/cuda)
- `TNVED_DATABASE_PATH` - путь к базе данных
- `TNVED_BATCH_SIZE` - размер батча для обработки
- `TNVED_DEFAULT_TOP_K` - количество результатов по умолчанию
- `TNVED_LOG_LEVEL` - уровень логирования

## Использование

### Command-Line Interface (CLI)

Система предоставляет два основных CLI скрипта для работы с данными ТНВЭД.

#### 1. Загрузка данных: `load_tnved.py`

Загружает данные из Excel файла в векторную базу данных ChromaDB. Поддерживает два типа данных:

**Справочные данные (reference)** - официальные описания кодов ТНВЭД:
```bash
python load_tnved.py tnved_full10_new.xlsx
# или явно указать тип
python load_tnved.py tnved_full10_new.xlsx --source-type reference
```

**Товарные данные (product)** - реальные товары с подобранными кодами:
```bash
python load_tnved.py products.xlsx --source-type product --source-name "customs_2024_q1"
python load_tnved.py supplier_catalog.xlsx --source-type product --source-name "supplier_abc"

# Повторная загрузка уже существующего source_name без интерактивного вопроса
python load_tnved.py products.xlsx --source-type product --source-name "customs_2024_q1" --replace-source
```

Если `source_name` уже есть в базе, CLI покажет количество существующих product-записей
и спросит подтверждение на замену. В режиме `--quiet` вопрос не задается: для замены
нужно явно указать `--replace-source`.

**⚠️ Важно:** Если у вас есть существующая база данных, созданная до обновления с поддержкой префиксов, рекомендуется переиндексировать данные для улучшения качества поиска:
```bash
python load_tnved.py tnved_full10_new.xlsx --reset
```

**Базовое использование:**
```bash
python load_tnved.py tnved_full10_new.xlsx
```

**С дополнительными параметрами:**
```bash
# Использование конфигурационного файла
python load_tnved.py tnved_full10_new.xlsx --config config.yaml

# Настройка размера батча и пути к БД
python load_tnved.py tnved_full10_new.xlsx --batch-size 50 --db-path ./my_chroma_db

# Сброс базы данных перед загрузкой
python load_tnved.py tnved_full10_new.xlsx --reset

# Проверка конфигурации без загрузки данных
python load_tnved.py tnved_full10_new.xlsx --dry-run

# Подробное логирование
python load_tnved.py tnved_full10_new.xlsx --verbose
```

**Доступные опции:**
- `--source-type` - тип данных: reference (справочные) или product (товарные) (по умолчанию: reference)
- `--source-name` - имя источника данных (обязательно для --source-type product)
- `--replace-source` - заменить существующие product-записи с тем же --source-name без интерактивного подтверждения
- `--config` - путь к файлу конфигурации YAML
- `--db-path` - путь к директории ChromaDB (по умолчанию: ./chroma_db)
- `--collection-name` - имя коллекции ChromaDB (по умолчанию: tnved)
- `--batch-size` - количество записей в батче (по умолчанию: 100)
- `--model-name` - название модели эмбеддингов (по умолчанию: ai-forever/FRIDA)
- `--device` - устройство для вычислений: cpu или cuda (по умолчанию: cpu)
- `--reset` - сбросить базу данных перед загрузкой
- `--dry-run` - проверить конфигурацию без загрузки данных
- `--verbose, -v` - подробное логирование
- `--quiet, -q` - минимальный вывод (только ошибки)
- `--log-file` - путь к файлу логов

**Пример вывода:**
```
======================================================================
ТНВЭД Data Loader
======================================================================

Excel file:      products.xlsx
Database path:   ./chroma_db
Collection:      tnved
Batch size:      100
Model:           ai-forever/FRIDA
Device:          cpu
Source type:     product
Source name:     customs_2024_q1

Initializing components...
✓ Components initialized

Current database: 13265 records
  Reference records: 13265
  Product records:   0

Loading data from Excel file...

======================================================================
Load Complete!
======================================================================
Records loaded:  1250
Total records:   14515
  Reference records: 13265
  Product records:   1250
Time elapsed:    89.45 seconds
Processing rate: 14.0 records/second
```

#### 2. Поиск кодов: `search_tnved.py`

Выполняет семантический поиск кодов ТНВЭД по текстовому описанию. Автоматически ищет по всем типам данных (справочные и товарные записи).

**Базовое использование:**
```bash
python search_tnved.py "кофейные зерна арабика"
```

**Поиск с фильтрацией по типу источника:**
```bash
# Только справочные записи
python search_tnved.py "кофе" --source-filter reference

# Только товарные записи
python search_tnved.py "кофе" --source-filter product
```

**С дополнительными параметрами:**
```bash
# Указать количество результатов
python search_tnved.py "зеленый чай" --top-k 10

# Использование конфигурационного файла
python search_tnved.py "сахар белый" --config config.yaml

# Поиск конкретного кода
python search_tnved.py --code 0901110000

# Интерактивный режим
python search_tnved.py --interactive

# Вывод в формате JSON
python search_tnved.py "молоко" --format json

# Показать нормализованный текст
python search_tnved.py "пшеница" --show-normalized
```

**Доступные опции:**
- `--top-k, -k` - количество результатов (по умолчанию: 5)
- `--source-filter` - фильтр по типу источника: reference, product или не указывать для поиска по всем
- `--code` - получить информацию о конкретном коде
- `--interactive, -i` - интерактивный режим поиска
- `--config` - путь к файлу конфигурации YAML
- `--db-path` - путь к директории ChromaDB
- `--collection-name` - имя коллекции ChromaDB
- `--model-name` - название модели эмбеддингов
- `--device` - устройство: cpu или cuda
- `--format` - формат вывода: table, json, или simple (по умолчанию: table)
- `--show-normalized` - показать нормализованный текст
- `--verbose, -v` - подробное логирование
- `--quiet, -q` - минимальный вывод
- `--log-file` - путь к файлу логов

**Пример вывода (table format):**
```
======================================================================
ТНВЭД Search
======================================================================

Initializing components...
✓ Components initialized
  Database: 14515 records
    Reference: 13265
    Product: 1250

Searching for: 'кофейные зерна арабика'
Top-k: 5

====================================================================================================
Found 5 result(s)
====================================================================================================

1. Code: 0901110000
   Similarity: 0.8934
   Description: КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА
   Source: reference

2. Code: 0901110000
   Similarity: 0.8821
   Description: Кофе арабика зерновой 1кг
   Source: product
   Source Name: customs_2024_q1
   Source ID: декларация_12345

3. Code: 0901120000
   Similarity: 0.8521
   Description: КОФЕ НЕЖАРЕНЫЙ ОСВОБОЖДЕННЫЙ ОТ КОФЕИНА
   Source: reference
```

**Интерактивный режим:**
```bash
python search_tnved.py --interactive
```

В интерактивном режиме доступны команды:
- Введите описание товара для поиска
- `code:<код>` - получить информацию о конкретном коде
- `top-k:<число>` - изменить количество результатов
- `filter:<type>` - установить фильтр источника (reference/product/none)
- `quit` или `exit` - выход

**Пример интерактивной сессии:**
```
======================================================================
ТНВЭД Interactive Search
======================================================================

Enter search queries or commands:
  - Type a description to search
  - Type 'code:<code>' to look up a specific code
  - Type 'top-k:<n>' to change number of results
  - Type 'filter:<type>' to set source filter (reference/product/none)
  - Type 'quit' or 'exit' to exit

Search> кофе
[результаты поиска...]

Search> filter:product
✓ Source filter set to product

Search [filter: product]> кофе
[только товарные записи...]

Search [filter: product]> top-k:10
✓ Top-k set to 10

Search [filter: product]> code:0901110000
[информация о коде...]

Search [filter: product]> quit
Goodbye!
```

### Программное использование

#### Загрузка конфигурации

```python
from utils.config import Config

# Из файла
config = Config.from_file("config.yaml")

# Из переменных окружения
config = Config.from_env()

# Валидация конфигурации
config.validate()
```

#### Настройка логирования

```python
from utils.logger import setup_logging, get_logger

# Настройка логирования
setup_logging(
    level="INFO",
    log_file="logs/tnved_embedder.log"
)

# Получение логгера
logger = get_logger(__name__)
logger.info("Приложение запущено")
```

#### Загрузка справочных данных

```python
from services import TextNormalizer, EmbeddingGenerator, TNVEDLoader

# Инициализация компонентов
normalizer = TextNormalizer()
embedder = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")

# Создание загрузчика
loader = TNVEDLoader(
    db_path="./chroma_db",
    normalizer=normalizer,
    embedder=embedder,
    batch_size=100
)

# Загрузка данных
total_loaded = loader.load_from_excel("tnved_full10_new.xlsx")
print(f"Загружено {total_loaded} записей")
```

#### Загрузка товарных данных

```python
from services.product_loader import ProductLoader

# Инициализация компонентов
normalizer = TextNormalizer()
embedder = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")

# Создание загрузчика товаров
product_loader = ProductLoader(
    db_path="./chroma_db",
    normalizer=normalizer,
    embedder=embedder,
    batch_size=100
)

# Загрузка товарных данных
total_loaded = product_loader.load_from_excel(
    "products.xlsx", 
    source_name="customs_2024_q1"
)
print(f"Загружено {total_loaded} товарных записей")

# Повторная загрузка того же source_name требует явного разрешения
total_loaded = product_loader.load_from_excel(
    "products.xlsx",
    source_name="customs_2024_q1",
    replace_existing=True
)

# Получение статистики по типам источников
stats = product_loader.get_statistics_by_source_type()
print(f"Справочные записи: {stats['reference']}")
print(f"Товарные записи: {stats['product']}")
```

#### Расширенный поиск

```python
from services.enhanced_searcher import EnhancedSearcher

# Инициализация компонентов
normalizer = TextNormalizer()
embedder = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")

# Создание расширенного поисковика
searcher = EnhancedSearcher(
    db_path="./chroma_db",
    normalizer=normalizer,
    embedder=embedder
)

# Поиск по всем типам данных
results = searcher.search("кофейные зерна арабика", top_k=5)

for result in results:
    print(f"{result.code}: {result.description}")
    print(f"  Источник: {result.source_type}")
    if result.source_name:
        print(f"  Имя источника: {result.source_name}")
    print(f"  Схожесть: {result.similarity_score:.4f}")
    print()

# Поиск только по товарным записям
product_results = searcher.search(
    "кофе арабика", 
    top_k=5, 
    source_filter="product"
)

# Поиск только по справочным записям
reference_results = searcher.search(
    "кофе арабика", 
    top_k=5, 
    source_filter="reference"
)

# Получение всех записей для конкретного кода
code_results = searcher.get_all_records_for_code("0901110000")
print(f"Найдено {len(code_results)} записей для кода 0901110000")

# Группировка результатов по кодам
grouped_results = searcher.search_grouped_by_code("кофе", top_k=10)
for code, records in grouped_results.items():
    print(f"Код {code}: {len(records)} записей")
```

## Примеры использования

### Пример 1: Загрузка справочных данных

```bash
# Загрузка официального справочника ТНВЭД
python load_tnved.py tnved_full10_new.xlsx --source-type reference

# Поиск по справочным данным
python search_tnved.py "кофе в зернах" --source-filter reference
```

### Пример 2: Добавление товарных данных

```bash
# Загрузка товаров из таможенных деклараций
python load_tnved.py customs_declarations.xlsx \
    --source-type product \
    --source-name "customs_2024_q1"

# Повторная загрузка того же source_name с заменой старого набора
python load_tnved.py customs_declarations.xlsx \
    --source-type product \
    --source-name "customs_2024_q1" \
    --replace-source

# Загрузка каталога поставщика
python load_tnved.py supplier_catalog.xlsx \
    --source-type product \
    --source-name "supplier_abc_catalog"

# Поиск по всем данным (справочные + товарные)
python search_tnved.py "кофе арабика зерновой"
```

### Пример 3: Работа с фильтрами

```bash
# Поиск только по товарным записям
python search_tnved.py "кофе" --source-filter product

# Поиск только по справочным записям
python search_tnved.py "кофе" --source-filter reference

# Поиск по всем типам данных (по умолчанию)
python search_tnved.py "кофе"
```

### Пример 4: Интерактивная работа

```bash
python search_tnved.py --interactive

# В интерактивном режиме:
Search> кофе арабика
# [результаты поиска по всем типам]

Search> filter:product
# ✓ Source filter set to product

Search [filter: product]> кофе арабика
# [только товарные записи]

Search [filter: product]> code:0901110000
# [все записи для кода 0901110000]
```

### Пример 5: Программное использование

```python
from services.product_loader import ProductLoader
from services.enhanced_searcher import EnhancedSearcher
from services import TextNormalizer, EmbeddingGenerator

# Инициализация
normalizer = TextNormalizer()
embedder = EmbeddingGenerator("ai-forever/FRIDA", "cpu")

# Загрузка товарных данных
loader = ProductLoader("./chroma_db", normalizer, embedder)
loader.load_from_excel("products.xlsx", "my_source")

# Если source_name уже существует, используйте явную замену
loader.load_from_excel("products.xlsx", "my_source", replace_existing=True)

# Поиск с приоритизацией
searcher = EnhancedSearcher("./chroma_db", normalizer, embedder)
results = searcher.search("кофе арабика", top_k=5)

# Результаты автоматически приоритизированы:
# 1. Справочные записи (source_type="reference")
# 2. Товарные записи (source_type="product")
for result in results:
    print(f"{result.code}: {result.description}")
    print(f"  Тип: {result.source_type}")
    if result.source_name:
        print(f"  Источник: {result.source_name}")
```

## Сравнение моделей эмбеддингов

Система поддерживает несколько моделей эмбеддингов. Помимо FRIDA, доступны более быстрые и компактные альтернативы:

### Альтернативные модели

1. **E5-Small** (рекомендуется для GTX 1060 3GB)
   - Размер: 470 MB (в 6.5 раз меньше FRIDA)
   - Скорость: в 3-5 раз быстрее
   - Качество: отличное для русского языка

2. **RuBERT-Tiny2** (самая быстрая)
   - Размер: 120 MB (в 25 раз меньше FRIDA)
   - Скорость: в 10 раз быстрее
   - Качество: хорошее для русского языка

3. **MiniLM-L12** (проверенная)
   - Размер: 470 MB
   - Скорость: в 4 раза быстрее
   - Качество: надежное

### Быстрое тестирование

```bash
# Установить зависимости
pip install tabulate

# Протестировать одну модель
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda

# Сравнить все модели
python benchmarks/compare_models.py
```

### Смена модели

```bash
# 1. Обновите config.yaml
# model:
#   name: "intfloat/multilingual-e5-small"
#   device: "cuda"

# 2. Пересоздайте базу данных
python load_tnved.py tnved_full10_new.xlsx --reset

# 3. Протестируйте поиск
python search_tnved.py "кофе в зернах"
```

**Подробнее:** См. `docs/MODEL_ALTERNATIVES_SUMMARY.md` и `benchmarks/README.md`

---

## Тестирование

Запуск всех тестов:
```bash
pytest tests/ -v
```

Запуск конкретного теста:
```bash
pytest tests/test_config.py -v
```

## Требования

- Python >= 3.9
- См. requirements.txt для полного списка зависимостей

## Лицензия

[Укажите лицензию]

## Авторы

[Укажите авторов]
