# Команды для запуска сравнения моделей

## Установка зависимостей
```bash
pip install tabulate
```

## Быстрый тест одной модели

### E5-Small (рекомендуется)
```bash
# CPU
python test_single_model.py intfloat/multilingual-e5-small

# CUDA
python test_single_model.py intfloat/multilingual-e5-small cuda
```

### RuBERT-Tiny2 (самая быстрая)
```bash
# CPU
python test_single_model.py cointegrated/rubert-tiny2

# CUDA
python test_single_model.py cointegrated/rubert-tiny2 cuda
```

### MiniLM-L12
```bash
# CPU
python test_single_model.py sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# CUDA
python test_single_model.py sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 cuda
```

### FRIDA (текущая)
```bash
# CPU
python test_single_model.py ai-forever/FRIDA

# CUDA (требует много памяти!)
python test_single_model.py ai-forever/FRIDA cuda
```

## Полное сравнение всех моделей
```bash
python compare_models.py
```

## Детальное сравнение результатов поиска
```bash
python compare_search_results.py
```

## После выбора модели

### 1. Обновите config.yaml
Например, для E5-Small:
```yaml
model:
  name: "intfloat/multilingual-e5-small"
  device: "cuda"
processing:
  batch_size: 32
```

### 2. Пересоздайте базу данных
```bash
python load_tnved.py
```

### 3. Протестируйте поиск
```bash
python search_tnved.py
```

## Примечания

- Первый запуск модели загрузит её из HuggingFace (может занять время)
- Модели кэшируются локально для последующих запусков
- При смене модели обязательно пересоздайте базу данных
- Для CUDA убедитесь, что PyTorch установлен с поддержкой CUDA
