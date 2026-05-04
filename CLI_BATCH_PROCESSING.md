# Запуск пакетной обработки из командной строки

## Обзор

Система поддерживает два способа пакетной обработки Excel файлов:
1. **Веб-интерфейс** - через браузер (рекомендуется)
2. **Командная строка** - прямой вызов Python скриптов

## Способ 1: Через веб-интерфейс (рекомендуется)

### Запуск веб-сервера

#### С использованием Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Или для разработки с монтированием кода
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

#### Без Docker

```bash
# 1. Запустите Redis
redis-server

# 2. Запустите веб-сервер
python start_batch_processor.py web

# 3. Запустите worker (в другом терминале)
python start_batch_processor.py worker
```

### Использование

1. Откройте http://localhost:8000
2. Войдите (admin/admin123)
3. Загрузите Excel файл
4. Выберите параметры обработки
5. Скачайте результат

## Способ 2: Прямой вызов из командной строки

### Вариант A: Использование существующих скриптов

Система предоставляет CLI скрипты для работы с ТНВЭД кодами:

#### 1. Загрузка данных в базу

```bash
# Загрузка справочных данных ТНВЭД
python load_tnved.py tnved_full10_new.xlsx --config config.yaml

# Загрузка товарных данных
python load_tnved.py products.xlsx \
    --source-type product \
    --source-name "customs_2024_q1" \
    --config config.yaml
# Загрузка товарных данных 1 строка
python load_tnved.py ../2026/26m1.xlsx --source-type product --source-name "2026m1" --config config.yaml
```

#### 2. Поиск кодов для одного товара

```bash
# Поиск по описанию
python search_tnved.py "кофейные зерна арабика" --config config.yaml

# Интерактивный режим
python search_tnved.py --interactive --config config.yaml
```

### Вариант B: Создание скрипта для пакетной обработки

Создайте файл `batch_process_cli.py`:

```python
#!/usr/bin/env python3
"""
CLI скрипт для пакетной обработки Excel файлов с подбором ТНВЭД кодов.
"""

import sys
import argparse
import logging
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from services import TextNormalizer, EmbeddingGenerator
from services.enhanced_searcher import EnhancedSearcher
from utils.config import Config
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def process_excel_file(
    input_file: Path,
    output_file: Path,
    config: Config,
    process_mode: str = "all",
    top_k: int = 1
) -> None:
    """
    Обработка Excel файла с подбором ТНВЭД кодов.
    
    Args:
        input_file: Путь к входному Excel файлу
        output_file: Путь к выходному Excel файлу
        config: Конфигурация системы
        process_mode: Режим обработки ("all" или "empty_only")
        top_k: Количество результатов для выбора
    """
    logger.info(f"Начало обработки файла: {input_file}")
    
    # Инициализация компонентов
    logger.info("Инициализация компонентов...")
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(
        model_name=config.model.name,
        device=config.model.device
    )
    searcher = EnhancedSearcher(
        db_path=config.database.path,
        normalizer=normalizer,
        embedder=embedder
    )
    
    # Чтение Excel файла
    logger.info("Чтение Excel файла...")
    df = pd.read_excel(input_file, engine='openpyxl')
    
    # Проверка наличия необходимых колонок
    description_col = None
    for col in df.columns:
        if "Product Detailed Description" in str(col):
            description_col = col
            break
    
    if not description_col:
        raise ValueError("Не найдена колонка 'Product Detailed Description'")
    
    logger.info(f"Найдено {len(df)} строк для обработки")
    
    # Фильтрация строк в зависимости от режима
    if process_mode == "empty_only":
        # Найти колонку HTS Code
        hts_col = None
        for col in df.columns:
            if "HTS Code" in str(col) or "HTS_Code" in str(col):
                hts_col = col
                break
        
        if hts_col:
            # Обработать только строки без кода
            mask = df[hts_col].isna() | (df[hts_col].astype(str).str.strip() == '')
            rows_to_process = df[mask].index.tolist()
            logger.info(f"Режим 'empty_only': обработка {len(rows_to_process)} строк без кодов")
        else:
            rows_to_process = df.index.tolist()
            logger.info("Колонка HTS Code не найдена, обработка всех строк")
    else:
        rows_to_process = df.index.tolist()
        logger.info(f"Режим 'all': обработка всех {len(rows_to_process)} строк")
    
    # Добавление новых колонок
    if 'TNVED_Code' not in df.columns:
        df['TNVED_Code'] = ''
    if 'Selection_Reason' not in df.columns:
        df['Selection_Reason'] = ''
    
    # Обработка строк
    processed = 0
    errors = 0
    
    for idx in rows_to_process:
        try:
            description = df.loc[idx, description_col]
            
            # Пропустить пустые описания
            if pd.isna(description) or str(description).strip() == '':
                continue
            
            # Поиск кода
            results = searcher.search(str(description), top_k=top_k)
            
            if results:
                # Взять первый результат
                top_result = results[0]
                df.loc[idx, 'TNVED_Code'] = top_result.code
                
                # Форматирование причины выбора
                reason = f"Similarity Score: {top_result.similarity_score:.3f}"
                if top_result.source_type:
                    reason += f" | Source: {top_result.source_type}"
                if top_result.source_name:
                    reason += f" | {top_result.source_name}"
                
                df.loc[idx, 'Selection_Reason'] = reason
                processed += 1
            else:
                df.loc[idx, 'Selection_Reason'] = "No match found"
                errors += 1
            
            # Прогресс
            if (processed + errors) % 100 == 0:
                logger.info(f"Обработано: {processed + errors}/{len(rows_to_process)}")
        
        except Exception as e:
            logger.error(f"Ошибка обработки строки {idx}: {e}")
            df.loc[idx, 'Selection_Reason'] = f"Error: {str(e)}"
            errors += 1
    
    # Сохранение результата
    logger.info(f"Сохранение результата в {output_file}...")
    df.to_excel(output_file, index=False, engine='openpyxl')
    
    # Статистика
    logger.info("=" * 60)
    logger.info("Обработка завершена!")
    logger.info(f"Успешно обработано: {processed}")
    logger.info(f"Ошибок: {errors}")
    logger.info(f"Результат сохранен: {output_file}")
    logger.info("=" * 60)


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Пакетная обработка Excel файлов с подбором ТНВЭД кодов"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Путь к входному Excel файлу"
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Путь к выходному Excel файлу"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default="config.yaml",
        help="Путь к файлу конфигурации (по умолчанию: config.yaml)"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "empty_only"],
        default="all",
        help="Режим обработки: all (все строки) или empty_only (только пустые)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=1,
        help="Количество результатов для выбора (по умолчанию: 1)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Уровень логирования"
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging(level=args.log_level)
    
    # Проверка входного файла
    if not args.input_file.exists():
        logger.error(f"Входной файл не найден: {args.input_file}")
        sys.exit(1)
    
    # Загрузка конфигурации
    logger.info(f"Загрузка конфигурации из {args.config}")
    config = Config.from_file(str(args.config))
    
    # Обработка файла
    try:
        process_excel_file(
            input_file=args.input_file,
            output_file=args.output_file,
            config=config,
            process_mode=args.mode,
            top_k=args.top_k
        )
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Использование скрипта

```bash
# Базовое использование
python batch_process_cli.py input.xlsx output.xlsx

# С указанием конфига
python batch_process_cli.py input.xlsx output.xlsx --config config.yaml

# Обработка только пустых строк
python batch_process_cli.py input.xlsx output.xlsx --mode empty_only

# С подробным логированием
python batch_process_cli.py input.xlsx output.xlsx --log-level DEBUG

# Полный пример
python batch_process_cli.py \
    xlsx/GUOO-Manifest--500Bags.xlsx \
    output_processed.xlsx \
    --config batch_processor_config.yaml \
    --mode all \
    --log-level INFO
```

## Конфигурация

### Файл config.yaml

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
  file: "batch_processor.log"
```

### Переменные окружения

```bash
# Модель
export TNVED_MODEL_NAME="ai-forever/FRIDA"
export TNVED_MODEL_DEVICE="cpu"

# База данных
export TNVED_DATABASE_PATH="./chroma_db"

# Обработка
export TNVED_BATCH_SIZE=100

# Запуск
python batch_process_cli.py input.xlsx output.xlsx
```

## Сравнение методов

| Метод | Преимущества | Недостатки |
|-------|-------------|-----------|
| **Веб-интерфейс** | ✅ Удобный UI<br>✅ Прогресс в реальном времени<br>✅ Автоматическая очистка<br>✅ Безопасность | ⚠️ Требует запуска сервера<br>⚠️ Требует Redis |
| **CLI скрипт** | ✅ Простой запуск<br>✅ Автоматизация<br>✅ Не требует сервера | ⚠️ Нет UI<br>⚠️ Нет прогресса в реальном времени |
| **Прямой Python** | ✅ Полный контроль<br>✅ Интеграция в код | ⚠️ Требует программирования |

## Примеры использования

### Пример 1: Обработка одного файла

```bash
python batch_process_cli.py \
    xlsx/test_small_file.xlsx \
    output/result.xlsx \
    --config config.yaml
```

### Пример 2: Обработка нескольких файлов

```bash
#!/bin/bash
# process_all.sh

for file in xlsx/*.xlsx; do
    filename=$(basename "$file" .xlsx)
    echo "Processing $filename..."
    python batch_process_cli.py \
        "$file" \
        "output/${filename}_processed.xlsx" \
        --config config.yaml
done
```

### Пример 3: Обработка с фильтрацией

```bash
# Обработать только строки без кодов
python batch_process_cli.py \
    input.xlsx \
    output.xlsx \
    --mode empty_only \
    --config config.yaml
```

## Устранение проблем

### Проблема: Модель не загружается

**Решение:** Проверьте конфигурацию и наличие модели

```bash
python -c "from transformers import AutoModel; AutoModel.from_pretrained('ai-forever/FRIDA')"
```

### Проблема: База данных не найдена

**Решение:** Загрузите данные в базу

```bash
python load_tnved.py tnved_full10_new.xlsx --config config.yaml
```

### Проблема: Недостаточно памяти

**Решение:** Уменьшите batch_size в конфиге

```yaml
processing:
  batch_size: 50  # Уменьшить с 100
```

## Рекомендации

1. **Для разработки:** Используйте CLI скрипт для быстрого тестирования
2. **Для production:** Используйте веб-интерфейс с Docker
3. **Для автоматизации:** Создайте bash/bat скрипты с CLI
4. **Для интеграции:** Используйте прямой вызов Python API

## Дополнительная документация

- `README.md` - Основная документация системы
- `BATCH_PROCESSOR_README.md` - Документация batch процессора
- `docs/QUICK_START_RU.md` - Быстрый старт
- `batch_processor_config.yaml` - Пример конфигурации