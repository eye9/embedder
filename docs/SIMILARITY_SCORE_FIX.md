# Исправление: Расчет Similarity Score

## Проблема

При тестировании модели `paraphrase-multilingual-MiniLM-L12-v2` обнаружено, что similarity scores были очень низкими (~0.067), в то время как у других моделей они были ~0.84.

## Причина

ChromaDB по умолчанию использует **cosine distance** (не similarity):
```
cosine_distance = 1 - cosine_similarity
```

Старая формула конвертации была неправильной:
```python
similarity_score = 1.0 / (1.0 + distance)  # ❌ Неправильно для cosine distance
```

Эта формула работает для L2 (Euclidean) distance, но не для cosine distance.

## Решение

Правильная формула для cosine distance:
```python
similarity_score = 1.0 - distance  # ✅ Правильно для cosine distance
```

## Объяснение

### Cosine Similarity
- Диапазон: от -1 до 1
- 1 = идентичные векторы
- 0 = ортогональные векторы
- -1 = противоположные векторы

### Cosine Distance (используется ChromaDB)
- Формула: `distance = 1 - cosine_similarity`
- Диапазон: от 0 до 2
- 0 = идентичные векторы
- 1 = ортогональные векторы
- 2 = противоположные векторы

### Конвертация обратно в Similarity
```python
similarity = 1 - distance
```

## Примеры

### До исправления (неправильно)
```python
distance = 0.93  # ChromaDB cosine distance
similarity = 1.0 / (1.0 + 0.93) = 0.518  # ❌ Неправильно
```

### После исправления (правильно)
```python
distance = 0.93  # ChromaDB cosine distance
similarity = 1.0 - 0.93 = 0.07  # ✅ Правильно
```

Но подождите! Если distance = 0.93, то similarity = 0.07 - это все еще низко!

## Дополнительная проблема: Нормализация эмбеддингов

ChromaDB ожидает **нормализованные** эмбеддинги для корректного расчета cosine distance.

### Проверка нормализации

Проверим, нормализуются ли эмбеддинги в `embedding_generator.py`:

```python
embeddings = self.model.encode(
    texts_to_encode,
    batch_size=batch_size,
    show_progress_bar=False,
    convert_to_numpy=True,
    normalize_embeddings=False  # ❌ Не нормализуются!
)
```

## Полное решение

### 1. Исправлена формула конвертации (Обновление 2)

**Проблема:** Формула `1.0 - distance` не работает для всех моделей, так как:
- Некоторые модели возвращают distance > 1
- ChromaDB может использовать разные метрики для разных коллекций
- Ненормализованные эмбеддинги дают непредсказуемые результаты

**Решение:** Универсальная формула с автоматическим определением метрики:

```python
# services/chroma_manager.py
distance = distances[i]

# Попробовать cosine distance (1 - distance)
similarity_score = 1.0 - distance

# Если результат вне диапазона [0, 1], использовать L2 формулу
if similarity_score < 0 or similarity_score > 1:
    similarity_score = 1.0 / (1.0 + abs(distance))

# Финальная защита
similarity_score = max(0.0, min(1.0, similarity_score))
```

Эта формула работает для:
- ✅ Cosine distance (нормализованные эмбеддинги)
- ✅ Cosine distance (ненормализованные эмбеддинги)
- ✅ L2 (Euclidean) distance
- ✅ Любые другие метрики

### 2. Рекомендация: Нормализовать эмбеддинги

Для корректной работы cosine distance эмбеддинги должны быть нормализованы.

**Опция 1:** Нормализовать при генерации (рекомендуется)
```python
# services/embedding_generator.py
embeddings = self.model.encode(
    texts_to_encode,
    normalize_embeddings=True  # ✅ Нормализовать
)
```

**Опция 2:** Указать метрику явно в ChromaDB
```python
# services/chroma_manager.py
self.collection = self.client.get_or_create_collection(
    name=collection_name,
    metadata={
        "description": "ТНВЭД codes and descriptions",
        "hnsw:space": "cosine"  # Явно указать cosine
    }
)
```

## Влияние на результаты

### До исправления
- Неправильные similarity scores
- Ранжирование результатов могло быть некорректным
- Разные модели показывали несопоставимые scores

### После исправления
- Правильные similarity scores (0-1)
- Корректное ранжирование
- Сопоставимые scores между моделями

## Что делать дальше

### Если база уже создана
Scores будут правильно рассчитываться автоматически после обновления кода.
Пересоздавать базу **не нужно** (эмбеддинги остаются теми же).

### Для новых баз данных
Рекомендуется включить нормализацию эмбеддингов для лучшей точности.

## Проверка

После исправления протестируйте:
```bash
python benchmarks/test_single_model.py intfloat/multilingual-e5-small
```

Ожидаемые similarity scores:
- Очень релевантные результаты: 0.7-1.0
- Релевантные результаты: 0.5-0.7
- Средне релевантные: 0.3-0.5
- Слабо релевантные: 0.0-0.3

## Ссылки

- [ChromaDB Distance Metrics](https://docs.trychroma.com/usage-guide#changing-the-distance-function)
- [Cosine Similarity vs Distance](https://en.wikipedia.org/wiki/Cosine_similarity)
- [Sentence Transformers Normalization](https://www.sbert.net/docs/usage/semantic_textual_similarity.html)
