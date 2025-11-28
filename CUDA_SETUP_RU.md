# Настройка CUDA для ТНВЭД Embedder

## Текущая ситуация

Вы пытаетесь использовать CUDA, но система возвращается на CPU, потому что:

```
2025-11-28 17:50:43,921 - services.embedding_generator - WARNING - CUDA requested but not available. Falling back to CPU.
```

## Причина

У вас установлена **CPU-версия PyTorch** (`2.8.0+cpu`), которая не поддерживает CUDA.

## Проверка системы

```bash
# Проверить версию PyTorch
python -c "import torch; print(torch.__version__)"
# Результат: 2.8.0+cpu  ← это CPU-версия!

# Проверить доступность CUDA
python -c "import torch; print(torch.cuda.is_available())"
# Результат: False  ← CUDA недоступна

# Проверить GPU
nvidia-smi
# Результат: NVIDIA GeForce GTX 1060 3GB, CUDA 12.6  ← GPU есть!
```

## ⚠️ ВАЖНО: Ограничение памяти

Модель FRIDA требует **~3.1 GB** памяти, а у вас GPU с **3 GB**. Это критично!

## Решение 1: Использовать CPU (РЕКОМЕНДУЕТСЯ)

Самый простой и надежный вариант:

```yaml
# config.yaml
model:
  device: "cpu"
```

**Почему это лучше:**
- ✅ Стабильная работа
- ✅ Нет риска нехватки памяти
- ✅ Можно использовать batch_size: 100
- ✅ Для 13K записей время загрузки приемлемо (~5-10 минут)

## Решение 2: Установить PyTorch с CUDA (РИСКОВАННО)

Если всё же хотите попробовать GPU:

### Шаг 1: Удалить CPU-версию

```bash
pip uninstall torch torchvision torchaudio -y
```

### Шаг 2: Установить CUDA-версию

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Шаг 3: Проверить установку

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

Должно быть: `CUDA available: True`

### Шаг 4: Использовать минимальный batch_size

```yaml
# config.yaml
model:
  device: "cuda"

processing:
  batch_size: 1  # ВАЖНО: только 1 из-за ограничения памяти!
```

### Шаг 5: Запустить с мониторингом

```bash
# В одном терминале - мониторинг GPU
nvidia-smi -l 1

# В другом терминале - загрузка данных
python load_tnved.py tnved_first20.xlsx --device cuda --batch-size 1
```

**Риски:**
- ❌ Может не хватить памяти (Out of Memory)
- ❌ Будет медленнее из-за batch_size=1
- ❌ Возможны сбои

## Решение 3: Использовать более легкую модель

Альтернативная модель, которая точно поместится в GPU:

```yaml
# config.yaml
model:
  name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # ~420 MB
  device: "cuda"

processing:
  batch_size: 32
```

**Преимущества:**
- ✅ Поместится в GPU с запасом
- ✅ Можно использовать нормальный batch_size
- ✅ Быстрая работа

**Недостатки:**
- ❌ Может быть менее точной для русского языка

## Рекомендация

**Для вашей конфигурации (GTX 1060 3GB) используйте CPU:**

1. Откройте `config.yaml`
2. Установите `device: "cpu"`
3. Оставьте `batch_size: 100`
4. Запустите: `python load_tnved.py tnved_full10_new.xlsx`

Это даст вам стабильную и надежную работу без головной боли с памятью GPU.

## Сравнение производительности

| Конфигурация | Время загрузки 13K записей | Стабильность |
|--------------|---------------------------|--------------|
| CPU + batch_size=100 | ~5-10 минут | ✅ Отлично |
| CUDA + batch_size=1 | ~10-15 минут | ❌ Риск OOM |
| CUDA + легкая модель | ~2-3 минуты | ✅ Хорошо |

## Если нужна максимальная скорость

Рассмотрите:
1. Апгрейд GPU до 6+ GB (RTX 3060, RTX 4060)
2. Использование облачных GPU (Google Colab, AWS)
3. Переход на более легкую модель

## Вопросы?

Если возникнут проблемы, проверьте:
- `python -c "import torch; print(torch.__version__)"` - должна быть версия с `+cu121` или `+cu118`
- `nvidia-smi` - GPU должен быть виден
- Логи в `tnved_embedder.log` - там будут детали ошибок
