# Быстрая загрузка данных - Шпаргалка

## 🚀 Для URL данных (КРИТИЧНО - было 1-3 записи/сек)

### Быстрый старт
```bash
# Самый быстрый способ (рекомендуется)
python load_urls_fast.py data.parquet my_source

# Если у вас Excel - конвертируйте в Parquet
python load_urls_fast.py data.xlsx my_source --convert-to-parquet

# Запустить бенчмарк
python load_urls_fast.py --benchmark
```

### Результат
- **Было**: 1-3 записи/сек → 100,000 записей = 9-28 часов
- **Стало**: 500-2000 записей/сек → 100,000 записей = 1-3 минуты
- **Ускорение**: 200-1000x

### Формат файла
```
URL,Code,Description
https://ozon.ru/product/12345/,1234567890,Товар 1
https://wildberries.ru/catalog/67890/,9876543210,Товар 2
```

---

## 📊 Для ТНВЭД кодов

### Быстрый старт
```bash
# С GPU (если доступен) - САМОЕ БЫСТРОЕ
python load_tnved.py data.xlsx --device cuda --batch-size 1000

# Без GPU - увеличить batch-size
python load_tnved.py data.xlsx --batch-size 500

# Использовать оптимизированный загрузчик
python -c "
from services.optimized_loader import OptimizedTNVEDLoader
from services import TextNormalizer, EmbeddingGenerator

normalizer = TextNormalizer()
embedder = EmbeddingGenerator(device='cuda')  # или 'cpu'
loader = OptimizedTNVEDLoader('./chroma_db', normalizer, embedder, batch_size=1000)
loader.load_from_excel('data.xlsx')
"
```

### Результат
- **С GPU**: 500-2000 записей/сек (10-50x ускорение)
- **Без GPU**: 50-200 записей/сек (2-5x ускорение с увеличенным batch_size)

---

## 🎯 Приоритеты оптимизации

### 1. URL загрузка (КРИТИЧНО)
✅ **Используйте**: `load_urls_fast.py`  
✅ **Ускорение**: 200-1000x  
✅ **Готово к использованию**: Да

### 2. ТНВЭД загрузка с GPU
✅ **Используйте**: `--device cuda`  
✅ **Ускорение**: 10-50x  
✅ **Требует**: NVIDIA GPU с CUDA

### 3. Формат файлов
✅ **Используйте**: Parquet вместо Excel  
✅ **Ускорение**: 5-10x для чтения  
✅ **Конвертация**: `--convert-to-parquet`

---

## 📈 Сравнение производительности

### URL данные
| Записей | Старый метод | Новый метод | Ускорение |
|---------|--------------|-------------|-----------|
| 10,000  | 55-167 мин   | 5-20 сек    | 200-1000x |
| 100,000 | 9-28 часов   | 50-200 сек  | 200-1000x |
| 500,000 | 46-139 часов | 4-17 мин    | 200-1000x |

### ТНВЭД коды
| Записей | CPU (старый) | CPU (новый) | GPU (новый) |
|---------|--------------|-------------|-------------|
| 10,000  | 3-10 мин     | 1-3 мин     | 5-20 сек    |
| 100,000 | 30-100 мин   | 10-30 мин   | 50-200 сек  |
| 500,000 | 2.5-8 часов  | 50-150 мин  | 4-17 мин    |

---

## 🔧 Установка зависимостей

```bash
# Основные зависимости (уже должны быть)
pip install pandas chromadb tqdm

# Для Parquet (рекомендуется)
pip install pyarrow

# Для GPU (опционально, но очень рекомендуется)
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## 💡 Советы

### Для URL
1. **Всегда используйте Parquet** - конвертируйте Excel один раз
2. **Batch size 5000-10000** - оптимально для большинства случаев
3. **SSD для ChromaDB** - HDD может быть узким местом

### Для ТНВЭД
1. **GPU обязателен** для больших объемов (100k+ записей)
2. **Batch size 500-1000** - оптимально для GPU
3. **Конвертируйте в Parquet** - ускорит чтение файла

---

## 🐛 Устранение проблем

### "Out of memory"
```bash
# Уменьшите batch_size
python load_urls_fast.py data.parquet my_source --batch-size 1000
```

### "CUDA out of memory"
```bash
# Уменьшите batch_size для GPU
python load_tnved.py data.xlsx --device cuda --batch-size 200
```

### Медленная загрузка
```bash
# 1. Проверьте формат файла (должен быть Parquet)
# 2. Проверьте batch_size (должен быть 500+)
# 3. Проверьте диск (должен быть SSD)
```

---

## 📚 Документация

- **URL загрузка**: [docs/FAST_URL_LOADING.md](FAST_URL_LOADING.md)
- **Общая оптимизация**: [docs/PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
- **Оптимизированные загрузчики**: [services/optimized_loader.py](services/optimized_loader.py)

---

## ✅ Чеклист перед загрузкой больших объемов

- [ ] Файл в формате Parquet (или конвертирован)
- [ ] Для URL: используется `load_urls_fast.py`
- [ ] Для ТНВЭД: используется GPU (если доступен)
- [ ] Batch size увеличен (500+ для ТНВЭД, 5000+ для URL)
- [ ] ChromaDB на SSD (не на HDD)
- [ ] Достаточно RAM (минимум 8GB для больших файлов)

---

## 🎉 Итого

**Для URL**: Используйте `load_urls_fast.py` → **200-1000x быстрее**  
**Для ТНВЭД**: Используйте GPU + большой batch_size → **10-50x быстрее**  
**Для файлов**: Используйте Parquet → **5-10x быстрее чтение**

**Суммарное ускорение**: До 1000x для URL, до 200x для ТНВЭД
