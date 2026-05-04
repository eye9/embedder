# Быстрый старт ТНВЭД Embedder

## 1. Установка

```bash
# Установить зависимости
pip install -r requirements.txt
```

## 2. Загрузка данных

```bash
# Базовая загрузка
python load_tnved.py tnved_full10_new.xlsx

# С настройками
python load_tnved.py tnved_full10_new.xlsx --batch-size 100 --verbose
```

**Ожидаемое время:** ~5-10 минут для 13,265 записей на CPU

## 3. Поиск кодов

```bash
# Простой поиск
python search_tnved.py "кофейные зерна арабика"

# С большим количеством результатов
python search_tnved.py "зеленый чай" --top-k 10

# Интерактивный режим
python search_tnved.py --interactive
```

## 4. Конфигурация

Отредактируйте `config.yaml`:

```yaml
model:
  device: "cpu"  # Используйте "cpu" для стабильности

processing:
  batch_size: 100  # Оптимально для CPU

search:
  default_top_k: 5  # Количество результатов по умолчанию
```

## 5. Использование CUDA (опционально)

**Только если у вас GPU с 4+ GB памяти!**

```bash
# Установить PyTorch с CUDA
pip uninstall torch torchvision torchaudio -y
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Проверить
python -c "import torch; print(torch.cuda.is_available())"

# Использовать
python load_tnved.py tnved_full10_new.xlsx --device cuda --batch-size 32
```

**Для GTX 1060 3GB:** Используйте CPU! См. `CUDA_SETUP_RU.md`

## 6. Примеры поиска

```bash
# Кофе
python search_tnved.py "кофейные зерна арабика"

# Чай
python search_tnved.py "зеленый чай листовой"

# Сахар
python search_tnved.py "сахар белый кристаллический"

# Молоко
python search_tnved.py "молоко коровье пастеризованное"

# Пшеница
python search_tnved.py "пшеничная мука высшего сорта"
```

## 7. Форматы вывода

```bash
# Таблица (по умолчанию)
python search_tnved.py "кофе" --format table

# JSON
python search_tnved.py "кофе" --format json

# Простой (для скриптов)
python search_tnved.py "кофе" --format simple
```

## 8. Поиск конкретного кода

```bash
python search_tnved.py --code 0901110000
```

## 9. Интерактивный режим

```bash
python search_tnved.py --interactive

# В интерактивном режиме:
Search> кофе
Search> top-k:10
Search> code:0901110000
Search> quit
```

## 10. Проверка статуса

```bash
# Проверить количество записей в базе
python -c "from services import TNVEDSearcher, TextNormalizer, EmbeddingGenerator; s = TNVEDSearcher('./chroma_db', TextNormalizer(), EmbeddingGenerator()); print(s.get_database_stats())"
```

## Решение проблем

### База данных пуста
```bash
# Загрузите данные
python load_tnved.py tnved_full10_new.xlsx
```

### CUDA не работает
```bash
# Проверьте версию PyTorch
python -c "import torch; print(torch.__version__)"

# Должна быть версия с +cu121 или +cu118
# Если видите +cpu, переустановите PyTorch (см. раздел 5)
```

### Медленная работа
```bash
# Увеличьте batch_size для CPU
python load_tnved.py tnved_full10_new.xlsx --batch-size 200

# Или используйте GPU (если есть 4+ GB памяти)
```

## Полезные команды

```bash
# Помощь
python load_tnved.py --help
python search_tnved.py --help

# Проверка конфигурации без загрузки
python load_tnved.py tnved_full10_new.xlsx --dry-run

# Сброс базы данных
python load_tnved.py tnved_full10_new.xlsx --reset

# Подробные логи
python load_tnved.py tnved_full10_new.xlsx --verbose
python search_tnved.py "кофе" --verbose

# Минимальный вывод
python load_tnved.py tnved_full10_new.xlsx --quiet
python search_tnved.py "кофе" --quiet
```

## Документация

- `README.md` - Полная документация
- `CUDA_SETUP_RU.md` - Настройка CUDA
- `GPU_RECOMMENDATIONS.md` - Рекомендации по GPU
- `install_pytorch_cuda.md` - Установка PyTorch с CUDA

## Поддержка

При возникновении проблем проверьте:
1. Логи в `logs/tnved_embedder.log`
2. Версию PyTorch: `python -c "import torch; print(torch.__version__)"`
3. Доступность CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
4. Память GPU: `nvidia-smi`
