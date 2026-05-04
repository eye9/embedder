# Быстрое руководство: Запуск подбора из командной строки

## Важно!

CLI скрипт теперь использует **тот же алгоритм**, что и веб-интерфейс:
- ✅ Подбор через URL (если есть колонка URL)
- ✅ Семантический поиск как fallback
- ✅ Гибридный режим с приоритетом URL
- ✅ Раскрашивание ячеек по confidence score

## Подготовка

### 1. Убедитесь, что данные загружены в базу

```bash
# Загрузить справочные данные ТНВЭД
python load_tnved.py xlsx/tnved_full10_new.xlsx

# Загрузить товарные данные с уже подобранными кодами
python load_tnved.py products.xlsx --source-type product --source-name customs_2024_q1

# Загрузить URL маппинги (если используете URL подбор)
python load_urls_fast.py xlsx/import_26-01.xlsx --source-name import_26-01

# Проверить, что данные загружены
python search_tnved.py "кофе"
```

Если product-источник с таким `--source-name` уже есть, `load_tnved.py` спросит
подтверждение перед заменой. Для автоматических запусков используйте:

```bash
python load_tnved.py products.xlsx --source-type product --source-name customs_2024_q1 --replace-source
```

### 2. Подготовьте Excel файл

Файл должен содержать колонку: **Product Detailed Description**

Опционально: колонка **URL** для подбора через URL

## Запуск обработки

### Базовое использование (с URL подбором)

```bash
python batch_process_cli.py input.xlsx output.xlsx
```

### Режимы обработки

```bash
# Обработать все строки
python batch_process_cli.py input.xlsx output.xlsx --mode all

# Обработать только пустые строки
python batch_process_cli.py input.xlsx output.xlsx --mode empty_only
```

### URL подбор

```bash
# С URL подбором (по умолчанию)
python batch_process_cli.py input.xlsx output.xlsx

# Только URL (без семантического fallback)
python batch_process_cli.py input.xlsx output.xlsx --url-priority only

# Отключить URL подбор (только семантический)
python batch_process_cli.py input.xlsx output.xlsx --url-processing disabled
```

### Полный пример

```bash
python batch_process_cli.py \
    GUOO-Manifest--500Bags_small.xlsx \
    output_processed.xlsx \
    --mode all \
    --algorithm similarity_top1 \
    --url-processing enabled \
    --url-priority first \
    --log-level INFO
```

## Параметры

- `--mode` - режим обработки:
  - `all` - обработать все строки (по умолчанию)
  - `empty_only` - только строки без кодов
  
- `--algorithm` - алгоритм подбора:
  - `similarity_top1` - топ-1 по схожести (по умолчанию)
  - `llm_reasoning` - с использованием LLM
  
- `--url-processing` - использование URL подбора:
  - `enabled` - включен (по умолчанию)
  - `disabled` - отключен
  
- `--url-priority` - приоритет URL:
  - `first` - сначала URL, потом семантика (по умолчанию)
  - `only` - только URL, без fallback
  - `disabled` - отключить URL подбор
  
- `--threshold` - порог для раскрашивания (по умолчанию: 0.185)
- `--log-level` - уровень логирования: DEBUG, INFO, WARNING, ERROR

## Примеры

### С URL подбором (рекомендуется)

```bash
python batch_process_cli.py input.xlsx output.xlsx
```

### Только семантический поиск

```bash
python batch_process_cli.py input.xlsx output.xlsx --url-processing disabled
```

### Только URL (без семантики)

```bash
python batch_process_cli.py input.xlsx output.xlsx --url-priority only
```

### С подробным логированием

```bash
python batch_process_cli.py input.xlsx output.xlsx --log-level DEBUG
```

### Обработка нескольких файлов (Windows)

```cmd
@echo off
for %%f in (xlsx\*.xlsx) do (
    echo Processing %%f...
    python batch_process_cli.py "%%f" "output\%%~nf_processed.xlsx"
)
```

### Обработка нескольких файлов (Linux/Mac)

```bash
#!/bin/bash
for file in xlsx/*.xlsx; do
    filename=$(basename "$file" .xlsx)
    echo "Processing $filename..."
    python batch_process_cli.py \
        "$file" \
        "output/${filename}_processed.xlsx"
done
```

## Результат

Выходной файл будет содержать:

- **TNVED_Code** - подобранный код (с раскрашиванием)
- **Selection_Reason** - причина выбора:
  - Для URL: `Found by URL: [URL] | Code: [CODE] | ...`
  - Для семантики: `Similarity Score: [SCORE] | ...`

### Раскрашивание

- 🟢 **Зеленый** (score >= 0.185) - высокая уверенность
- 🔴 **Красный** (score < 0.185) - низкая уверенность
- ⚪ **Белый** (score = 1.0) - точное совпадение URL

## Статистика

После обработки вы увидите:

```
PROCESSING COMPLETE
======================================================================
Successfully processed: 500
Errors:                0
URL matches:           350
Semantic matches:      150
URL match rate:        70.0%
Total time:            45.23 seconds
Processing rate:       11.05 records/second
Output file:           output_processed.xlsx
======================================================================
```

## Устранение проблем

### База данных не найдена

```bash
# Загрузите данные
python load_tnved.py xlsx/tnved_full10_new.xlsx
```

### URL маппинги не найдены

```bash
# Загрузите URL маппинги
python load_urls_fast.py xlsx/import_26-01.xlsx --source-name import_26-01
```

### Колонка не найдена

Убедитесь, что в Excel файле есть колонка **Product Detailed Description**

### Модель загружается заново

Удалите папку `.no_exist` из кэша модели:
```bash
# Windows
Remove-Item "$env:USERPROFILE\.cache\huggingface\hub\models--*\.no_exist" -Recurse -Force

# Linux/Mac
rm -rf ~/.cache/huggingface/hub/models--*/.no_exist
```

## Сравнение с веб-интерфейсом

| Функция | CLI | Web |
|---------|-----|-----|
| URL подбор | ✅ | ✅ |
| Семантический поиск | ✅ | ✅ |
| Гибридный режим | ✅ | ✅ |
| Раскрашивание | ✅ | ✅ |
| Прогресс в реальном времени | ⚠️ Консоль | ✅ WebSocket |
| UI | ❌ | ✅ |
| Автоматизация | ✅ | ⚠️ |

## Дополнительная информация

- Полная документация: `CLI_BATCH_PROCESSING.md`
- Основная документация: `README.md`
- Конфигурация: `batch_processor_config.yaml`
