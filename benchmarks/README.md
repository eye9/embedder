# Benchmarks - Тестирование и сравнение моделей

Эта папка содержит скрипты для тестирования и сравнения различных моделей эмбеддингов.

## Скрипты

### `test_single_model.py`
Быстрый тест одной модели эмбеддингов.

**Использование:**
```bash
python benchmarks/test_single_model.py <model_name> [device]
```

**Примеры:**
```bash
# E5-Small на CUDA
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda

# RuBERT-Tiny2 на CPU
python benchmarks/test_single_model.py cointegrated/rubert-tiny2
```

**Что тестирует:**
- Скорость загрузки модели
- Скорость генерации эмбеддингов
- Скорость поиска (если база совместима)
- Примеры результатов поиска

---

### `compare_models.py`
Полное сравнение всех моделей эмбеддингов.

**Использование:**
```bash
python benchmarks/compare_models.py
```

**Что сравнивает:**
- FRIDA (текущая модель)
- E5-Small (рекомендуется)
- MiniLM-L12 (проверенная)
- RuBERT-Tiny2 (самая быстрая)

**Метрики:**
- Время загрузки модели
- Размерность эмбеддингов
- Скорость генерации (эмбеддингов/сек)
- Скорость поиска (только для совместимой базы)
- Средний similarity score

**Результат:**
Итоговая таблица с рекомендациями по выбору модели.

---

### `compare_search_results.py`
Детальное сравнение результатов поиска для разных моделей.

**Использование:**
```bash
python benchmarks/compare_search_results.py
```

**Что показывает:**
- Side-by-side сравнение результатов для одинаковых запросов
- Какие коды ТНВЭД находят разные модели
- Процент пересечения результатов
- Различия в similarity scores

**Примечание:** Требует пересоздания базы данных для каждой модели.

---

### `compare_prefix_impact.py`
Сравнение влияния префиксов на качество поиска.

**Использование:**
```bash
python benchmarks/compare_prefix_impact.py
```

**Что тестирует:**
- Поиск с префиксом "search_query: "
- Поиск без префикса
- Сравнение результатов

---

## Быстрый старт

### 1. Установите зависимости
```bash
pip install tabulate
```

### 2. Протестируйте одну модель
```bash
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda
```

### 3. Сравните все модели
```bash
python benchmarks/compare_models.py
```

---

## Важные замечания

### Размерность эмбеддингов

Разные модели создают эмбеддинги разной размерности:
- FRIDA: 1536
- E5-Small: 384
- MiniLM-L12: 384
- RuBERT-Tiny2: 312

**Это означает:**
- База данных, созданная с одной моделью, несовместима с другой
- При смене модели нужно пересоздать базу: `python load_tnved.py`
- `compare_models.py` покажет поиск только для модели, с которой создана база

### Рекомендуемый workflow

```bash
# 1. Быстрое сравнение всех моделей (без поиска)
python benchmarks/compare_models.py

# 2. Выберите понравившуюся модель

# 3. Протестируйте её с поиском
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda

# 4. Если база несовместима, пересоздайте
# Обновите config.yaml
python load_tnved.py

# 5. Повторите тест
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda
```

---

## Документация

Подробная документация находится в папке `docs/`:
- `MODEL_ALTERNATIVES_SUMMARY.md` - Краткое резюме
- `QUICK_MODEL_COMPARISON.md` - Быстрый старт
- `MODEL_COMPARISON_GUIDE.md` - Полное руководство
- `ВАЖНО_РАЗМЕРНОСТЬ_ЭМБЕДДИНГОВ.md` - Про размерность
- `FAQ_СРАВНЕНИЕ_МОДЕЛЕЙ.md` - FAQ
- `COMMANDS_CHEATSHEET.txt` - Шпаргалка команд
