# Исправление раскрашивания ячеек по similarity score

## Проблема

При проверке через браузер раскрашивание ячеек таблицы кодов в зависимости от similarity score не работало.

## Причина

В файле `batch_processor/workers/processing_task.py` при создании словаря результатов для передачи в Excel процессор не передавался параметр `confidence_score`, который необходим для раскрашивания ячеек.

## Исправление

### Изменения в коде

**Файл:** `batch_processor/workers/processing_task.py`

**До исправления:**
```python
# Convert results to dictionary format for Excel processor
results_dict = []
for result in results:
    results_dict.append({
        'row_index': result.row_index,
        'tnved_code': result.tnved_code or '',
        'selection_reason': result.selection_reason
    })
```

**После исправления:**
```python
# Convert results to dictionary format for Excel processor
results_dict = []
for result in results:
    results_dict.append({
        'row_index': result.row_index,
        'tnved_code': result.tnved_code or '',
        'selection_reason': result.selection_reason,
        'confidence_score': result.confidence_score  # Добавлено для раскрашивания
    })
```

## Как работает раскрашивание

### Логика раскрашивания

Раскрашивание реализовано в методе `_apply_color_coding` класса `ExcelProcessor`:

1. **Зеленый цвет** (`#00FF00`): `confidence_score >= 0.185`
2. **Красный цвет** (`#FF0000`): `confidence_score < 0.185`
3. **Без цвета**: `confidence_score == 1.0` (точное совпадение URL)

### Процесс раскрашивания

1. Результаты обработки содержат `confidence_score` для каждой строки
2. При записи в Excel файл создается словарь `row_colors` с индексами строк и их оценками
3. После записи данных вызывается `_apply_color_coding()`, который:
   - Загружает Excel файл с помощью `openpyxl`
   - Находит колонку `TNVED_Code`
   - Применяет цветовую заливку к ячейкам на основе оценок

## Тестирование

### Автоматический тест

Создан тест `test_color_coding_fix.py` для проверки функциональности:

```bash
python test_color_coding_fix.py
```

Тест создает:
- Входной файл с тестовыми данными
- Результаты с разными оценками confidence_score
- Выходной файл с раскрашенными ячейками

### Ожидаемые результаты

- **Строка 1** (Score 0.950): ЗЕЛЕНЫЙ (высокая уверенность)
- **Строка 2** (Score 0.250): ЗЕЛЕНЫЙ (средняя уверенность)
- **Строка 3** (Score 0.185): ЗЕЛЕНЫЙ (пороговое значение)
- **Строка 4** (Score 0.120): КРАСНЫЙ (низкая уверенность)

## Проверка через веб-интерфейс

1. Запустите веб-приложение:
   ```bash
   python start_batch_web.py
   ```

2. Откройте http://localhost:8000

3. Загрузите тестовый файл `test_web_color_coding.xlsx`

4. После обработки скачайте результат и проверьте раскрашивание в Excel

## Технические детали

### Используемые компоненты

- **ExcelProcessor**: Базовый класс с методом `_apply_color_coding`
- **EnhancedExcelProcessor**: Расширенный класс, наследующий функциональность раскрашивания
- **openpyxl.styles.PatternFill**: Для создания цветовой заливки ячеек

### Цветовые коды

- Зеленый: `PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")`
- Красный: `PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")`

## Статус

✅ **Исправлено** - Раскрашивание ячеек теперь работает корректно в веб-интерфейсе.

Исправление протестировано и готово к использованию.