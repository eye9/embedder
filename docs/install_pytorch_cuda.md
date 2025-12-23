# Установка PyTorch с поддержкой CUDA

## Проблема
У вас установлена CPU-версия PyTorch (`2.8.0+cpu`), которая не может использовать GPU.

## Решение

### Вариант 1: CUDA 12.x (рекомендуется для вашей системы)

```bash
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Вариант 2: CUDA 11.8 (если первый вариант не работает)

```bash
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Проверка установки

После установки проверьте, что CUDA доступна:

```bash
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Вы должны увидеть:
```
PyTorch version: 2.x.x+cu121 (или cu118)
CUDA available: True
CUDA device: NVIDIA GeForce GTX 1060 3GB
```

## Обновление requirements.txt

После успешной установки обновите `requirements.txt`:

```bash
pip freeze | grep torch > torch_requirements.txt
```

## Использование CUDA в системе

После установки PyTorch с CUDA, вы сможете использовать GPU:

```bash
# В config.yaml установите:
model:
  device: "cuda"

# Или через командную строку:
python load_tnved.py tnved_first20.xlsx --device cuda
python search_tnved.py "кофе" --device cuda
```

## Примечание о памяти GPU

У вас GTX 1060 с 3GB памяти. Модель FRIDA может занимать значительную память.
Если возникнут проблемы с памятью, используйте меньший batch_size:

```bash
python load_tnved.py tnved_first20.xlsx --device cuda --batch-size 32
```

## Альтернатива: Использование CPU

Если установка CUDA-версии вызывает проблемы, можно продолжить использовать CPU:

```bash
# В config.yaml:
model:
  device: "cpu"

# Или через командную строку:
python load_tnved.py tnved_first20.xlsx --device cpu
```

CPU будет медленнее, но для небольших датасетов это приемлемо.
