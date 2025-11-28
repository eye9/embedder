# ТНВЭД Embedder System

Система для автоматического подбора кодов ТНВЭД (Товарная номенклатура внешнеэкономической деятельности) на основе текстового описания товара с использованием векторного поиска.

## Описание

Система использует:
- **ChromaDB** - векторная база данных для хранения и поиска
- **ai-forever/FRIDA** - модель эмбеддингов для русского языка
- **Natasha** - библиотека для нормализации русских текстов

## Структура проекта

```
.
├── models/              # Модели данных
│   ├── tnved_record.py  # Модель записи ТНВЭД
│   └── search_result.py # Модель результата поиска
├── services/            # Сервисы (будут добавлены)
├── utils/               # Утилиты
│   ├── config.py        # Управление конфигурацией
│   └── logger.py        # Настройка логирования
├── tests/               # Тесты
├── config.yaml          # Конфигурационный файл
└── requirements.txt     # Зависимости Python
```

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

**⚠️ Важно:** Для GPU с 3GB памяти (например, GTX 1060) рекомендуется использовать CPU из-за ограничений памяти. См. `CUDA_SETUP_RU.md` для деталей.

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

processing:
  batch_size: 100

search:
  default_top_k: 5

logging:
  level: "INFO"
  file: "tnved_embedder.log"
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

Загружает данные из Excel файла в векторную базу данных ChromaDB.

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

Excel file:      tnved_full10_new.xlsx
Database path:   ./chroma_db
Collection:      tnved
Batch size:      100
Model:           ai-forever/FRIDA
Device:          cpu

Initializing components...
✓ Components initialized

Current database: 0 records

Loading data from Excel file...

======================================================================
Load Complete!
======================================================================
Records loaded:  13265
Total records:   13265
Time elapsed:    245.32 seconds
Processing rate: 54.1 records/second
```

#### 2. Поиск кодов: `search_tnved.py`

Выполняет семантический поиск кодов ТНВЭД по текстовому описанию.

**Базовое использование:**
```bash
python search_tnved.py "кофейные зерна арабика"
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
  Database: 13265 records

Searching for: 'кофейные зерна арабика'
Top-k: 5

====================================================================================================
Found 5 result(s)
====================================================================================================

1. Code: 0901110000
   Similarity: 0.8934
   Description: КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА

2. Code: 0901120000
   Similarity: 0.8521
   Description: КОФЕ НЕЖАРЕНЫЙ ОСВОБОЖДЕННЫЙ ОТ КОФЕИНА

3. Code: 0901210000
   Similarity: 0.7892
   Description: КОФЕ ЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА
```

**Интерактивный режим:**
```bash
python search_tnved.py --interactive
```

В интерактивном режиме доступны команды:
- Введите описание товара для поиска
- `code:<код>` - получить информацию о конкретном коде
- `top-k:<число>` - изменить количество результатов
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
  - Type 'quit' or 'exit' to exit

Search> кофе
[результаты поиска...]

Search> top-k:10
✓ Top-k set to 10

Search> code:0901110000
[информация о коде...]

Search> quit
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
    log_file="tnved_embedder.log"
)

# Получение логгера
logger = get_logger(__name__)
logger.info("Приложение запущено")
```

#### Загрузка данных

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

#### Поиск кодов

```python
from services import TextNormalizer, EmbeddingGenerator, TNVEDSearcher

# Инициализация компонентов
normalizer = TextNormalizer()
embedder = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")

# Создание поисковика
searcher = TNVEDSearcher(
    db_path="./chroma_db",
    normalizer=normalizer,
    embedder=embedder
)

# Поиск
results = searcher.search("кофейные зерна арабика", top_k=5)

for result in results:
    print(f"{result.code}: {result.description} (score: {result.similarity_score:.4f})")
```

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
