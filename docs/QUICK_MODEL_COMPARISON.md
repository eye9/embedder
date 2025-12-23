# Быстрое сравнение моделей

## Три альтернативы FRIDA

### 🚀 E5-Small (рекомендуется)
```yaml
model:
  name: "intfloat/multilingual-e5-small"
  device: "cuda"  # или "cpu"
```
- **Размер**: 470 MB (в 6.5 раз меньше FRIDA)
- **Скорость**: ~3-5x быстрее FRIDA
- **Качество**: Отличное для мультиязычных задач
- **CUDA**: ✅ Отлично работает на GTX 1060 3GB

### ⚡ RuBERT-Tiny2 (самая быстрая)
```yaml
model:
  name: "cointegrated/rubert-tiny2"
  device: "cuda"  # или "cpu"
```
- **Размер**: 120 MB (в 25 раз меньше FRIDA!)
- **Скорость**: ~10x быстрее FRIDA
- **Качество**: Хорошее для русского языка
- **CUDA**: ✅ Минимальные требования к памяти

### 🎯 MiniLM-L12 (баланс)
```yaml
model:
  name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  device: "cuda"  # или "cpu"
```
- **Размер**: 470 MB
- **Скорость**: ~4x быстрее FRIDA
- **Качество**: Проверенное временем
- **CUDA**: ✅ Хорошо работает на 3GB GPU

## Быстрый старт

### 1. Установите tabulate
```bash
pip install tabulate
```

### 2. Быстрый тест одной модели (рекомендуется начать с этого)
```bash
# Тест E5-Small на CPU
python benchmarks/test_single_model.py intfloat/multilingual-e5-small

# Тест E5-Small на CUDA
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda

# Тест RuBERT-Tiny2
python benchmarks/test_single_model.py cointegrated/rubert-tiny2
```

Это покажет:
- Время загрузки модели
- Скорость генерации эмбеддингов
- Скорость поиска
- Примеры результатов

### 3. Полное сравнение всех моделей
```bash
python benchmarks/compare_models.py
```

Это покажет:
- Сравнительную таблицу всех моделей
- Скорость загрузки каждой модели
- Скорость генерации эмбеддингов
- Скорость поиска (только для модели, с которой создана база)
- Средний score качества

**Примечание**: Тест поиска работает только для модели, с которой создана текущая база данных. Для других моделей будут показаны только скорость загрузки и генерации эмбеддингов.

### 4. Детальное сравнение результатов
```bash
python benchmarks/compare_search_results.py
```

Это покажет:
- Side-by-side сравнение результатов
- Какие коды находят разные модели
- Процент пересечения результатов
- Различия в scores

## Что выбрать?

### Для GTX 1060 3GB + CUDA
```yaml
model:
  name: "intfloat/multilingual-e5-small"
  device: "cuda"
processing:
  batch_size: 32
```

### Для CPU-only систем
```yaml
model:
  name: "cointegrated/rubert-tiny2"
  device: "cpu"
processing:
  batch_size: 100
```

### Для максимального качества
```yaml
model:
  name: "ai-forever/FRIDA"
  device: "cpu"
processing:
  batch_size: 50
```

## После выбора модели

1. Обновите `config.yaml` с выбранной моделью
2. Пересоздайте базу данных:
   ```bash
   python load_tnved.py
   ```
3. Протестируйте поиск:
   ```bash
   python search_tnved.py
   ```

## Ожидаемые результаты

| Модель | Загрузка | Эмбеддинги/сек | Поиск (мс) | Память GPU |
|--------|----------|----------------|------------|------------|
| FRIDA | ~10-15с | ~5-10 | ~200-300 | ~3.1 GB |
| E5-Small | ~3-5с | ~30-50 | ~50-100 | ~500 MB |
| MiniLM-L12 | ~3-5с | ~25-40 | ~60-120 | ~500 MB |
| RuBERT-Tiny2 | ~1-2с | ~80-120 | ~30-60 | ~150 MB |

*Примечание: Реальные цифры зависят от вашего железа*

## Важно! ⚠️

При смене модели **обязательно** пересоздайте базу данных:
```bash
python load_tnved.py
```

Разные модели создают эмбеддинги разной размерности, поэтому старая база не будет работать с новой моделью.
