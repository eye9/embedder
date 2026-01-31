# Реализация цветовой индикации кодов ТНВЭД

## Обзор изменений

Добавлена автоматическая цветовая индикация ячеек с кодами ТНВЭД в выходных Excel-файлах на основе уровня уверенности (similarity score).

## Дата реализации

31 января 2026

## Измененные файлы

### 1. `batch_processor/services/excel_processor.py`

**Изменения:**
- Обновлен метод `write_results()` для поддержки цветовой индикации
- Добавлен новый метод `_apply_color_coding()` для применения цветов к ячейкам

**Ключевые изменения:**

```python
def write_results(self, original_file, results, output_file, preserve_existing_hts=True):
    """
    Write processing results to a new Excel file with color-coded TNVED codes.
    
    Color coding based on similarity score:
    - Score = 1.0 (URL match): No color (white)
    - Score >= 0.185: Green background
    - Score < 0.185: Red background
    """
    # ... existing code ...
    
    # Track which rows need coloring and their scores
    row_colors = {}  # {row_idx: confidence_score}
    
    # Apply results and collect scores
    for result in results:
        # ... existing code ...
        confidence_score = result.get('confidence_score')
        if confidence_score is not None:
            row_colors[row_idx] = confidence_score
    
    # Write to Excel file
    df_output.to_excel(output_file, index=False, engine='openpyxl')
    
    # Apply color coding to TNVED_Code column
    self._apply_color_coding(output_file, row_colors)

def _apply_color_coding(self, excel_file, row_colors):
    """
    Apply color coding to TNVED_Code cells based on similarity scores.
    """
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    
    # Define color fills
    green_fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
    red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    
    # Apply colors based on scores
    for row_idx, confidence_score in row_colors.items():
        if confidence_score == 1.0:
            pass  # URL match - no color
        elif confidence_score >= 0.185:
            cell.fill = green_fill  # High confidence
        else:
            cell.fill = red_fill  # Low confidence
```

### 2. `batch_processor/services/enhanced_excel_processor.py`

**Изменения:**
- Обновлен метод `write_hybrid_results()` для поддержки цветовой индикации
- Добавлена документация о цветовой схеме

**Ключевые изменения:**

```python
def write_hybrid_results(self, original_file, results, output_file, preserve_existing_hts=True):
    """
    Write hybrid processing results to Excel file with URL metadata and color coding.
    
    Color coding based on similarity score:
    - Score = 1.0 (URL match): No color (white)
    - Score >= 0.185: Green background
    - Score < 0.185: Red background
    """
    # Convert hybrid results to standard format
    standard_results = [...]
    
    # Use parent class method for writing (includes color coding)
    self.write_results(original_file, standard_results, output_file, preserve_existing_hts)
```

### 3. Новые файлы

#### `docs/COLOR_CODING_GUIDE.md`
Полное руководство по цветовой индикации, включающее:
- Правила раскраски
- Технические детали реализации
- Примеры использования
- Настройку порогового значения
- Устранение неполадок

#### `test_color_coding.py`
Тестовый скрипт для проверки работы цветовой индикации:
- Создает тестовый Excel-файл
- Генерирует результаты с различными similarity scores
- Применяет цветовую индикацию
- Проверяет корректность работы

#### `COLOR_CODING_IMPLEMENTATION.md`
Этот документ - описание реализации.

### 4. Обновленные файлы документации

#### `BATCH_PROCESSOR_README.md`
Добавлена секция о цветовой индикации в разделе "Excel File Format".

## Правила цветовой индикации

### Зеленый цвет (00FF00)
- **Условие:** `SIMILARITY SCORE >= 0.185`
- **Значение:** Высокая уверенность в подобранном коде
- **Действие:** Код можно использовать

### Красный цвет (FF0000)
- **Условие:** `SIMILARITY SCORE < 0.185`
- **Значение:** Низкая уверенность в подобранном коде
- **Действие:** Требуется ручная проверка

### Без цвета (белый)
- **Условие:** `SIMILARITY SCORE = 1.0`
- **Значение:** Код найден точным совпадением по URL
- **Действие:** Максимальная надежность, код можно использовать

## Пороговое значение

Выбрано значение **0.185** на основе:
- Анализа качества подбора кодов
- Баланса между точностью и полнотой
- Практического опыта использования системы

## Технические детали

### Зависимости
- `openpyxl` - для работы с Excel и применения стилей
- `pandas` - для обработки данных

### Производительность
- Цветовая индикация применяется после записи данных
- Минимальное влияние на время обработки
- Обработка ошибок не влияет на создание файла

### Обратная совместимость
- Существующий код продолжает работать без изменений
- Цветовая индикация применяется автоматически
- При ошибках файл создается без цветов

## Тестирование

### Запуск тестов

```bash
# Тест цветовой индикации
python test_color_coding.py

# Проверка результата
# Откройте test_color_coding_output.xlsx и проверьте цвета
```

### Ожидаемые результаты

| Row | Score | Expected Color |
|-----|-------|----------------|
| 1   | 1.0   | Белый (no color) |
| 2   | 0.850 | Зеленый |
| 3   | 0.250 | Зеленый |
| 4   | 0.185 | Зеленый |
| 5   | 0.120 | Красный |

## Использование

### Автоматическое применение

Цветовая индикация применяется автоматически при:
1. Обработке через веб-интерфейс
2. Использовании API
3. Запуске через командную строку

### Программное использование

```python
from batch_processor.services.excel_processor import ExcelProcessor

processor = ExcelProcessor()

results = [
    {
        'row_index': 0,
        'tnved_code': '0901110000',
        'selection_reason': 'Found by URL',
        'confidence_score': 1.0  # Белый
    },
    {
        'row_index': 1,
        'tnved_code': '0902100000',
        'selection_reason': 'Similarity Score: 0.850',
        'confidence_score': 0.850  # Зеленый
    },
    {
        'row_index': 2,
        'tnved_code': '1806320000',
        'selection_reason': 'Similarity Score: 0.120',
        'confidence_score': 0.120  # Красный
    }
]

processor.write_results(
    original_file=Path("input.xlsx"),
    results=results,
    output_file=Path("output.xlsx")
)
# Цвета применяются автоматически
```

## Будущие улучшения

### Возможные расширения

1. **Настраиваемые цвета**
   - Позволить пользователям выбирать цветовую схему
   - Поддержка тем (светлая/темная)

2. **Дополнительные уровни**
   - Добавить промежуточные уровни уверенности
   - Использовать градиент цветов

3. **Условное форматирование**
   - Использовать встроенное условное форматирование Excel
   - Динамическое обновление при изменении данных

4. **Легенда**
   - Добавить легенду на отдельный лист
   - Объяснение цветовой схемы в файле

5. **Статистика**
   - Добавить сводку по цветам
   - Процент зеленых/красных/белых кодов

## Заключение

Цветовая индикация значительно улучшает пользовательский опыт:
- Быстрая визуальная оценка качества результатов
- Легкая идентификация кодов, требующих проверки
- Повышение доверия к автоматически подобранным кодам
- Упрощение процесса ручной проверки

Реализация полностью обратно совместима и не требует изменений в существующем коде.
