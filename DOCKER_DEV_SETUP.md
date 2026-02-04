# Docker Development Setup - Исправление раскрашивания

## Проблема
Раскрашивание ячеек не работает в Docker, потому что код не монтируется как volume.

## Решение для разработки

### Вариант 1: Использовать docker-compose.dev.yml (РЕКОМЕНДУЕТСЯ)

Этот файл уже настроен для монтирования кода как volume.

#### Шаг 1: Остановите текущие контейнеры

```bash
docker-compose down
```

#### Шаг 2: Запустите с dev конфигурацией

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Или в фоновом режиме:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

#### Шаг 3: Проверьте логи

```bash
# Все сервисы
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Только web
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f web

# Только worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
```

#### Шаг 4: Перезапустите worker после изменений

После изменения кода в `batch_processor/workers/processing_task.py`:

```bash
# Перезапустить только worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker

# Или пересоздать worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --force-recreate worker
```

### Вариант 2: Добавить volume в основной docker-compose.yml

Если хотите использовать основной файл, добавьте монтирование кода:

```yaml
services:
  web:
    volumes:
      - .:/app  # ← Добавьте эту строку
      - ./temp_files:/app/temp_files
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
      - ./batch_processor_config.yaml:/app/batch_processor_config.yaml

  worker:
    volumes:
      - .:/app  # ← Добавьте эту строку
      - ./temp_files:/app/temp_files
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
      - ./batch_processor_config.yaml:/app/batch_processor_config.yaml
```

Затем:

```bash
docker-compose down
docker-compose up -d --build
```

## Проверка исправления

### 1. Убедитесь, что код монтируется

```bash
# Проверьте, что файл изменен в контейнере
docker-compose exec worker cat /app/batch_processor/workers/processing_task.py | grep -A 5 "confidence_score"
```

Должно быть:

```python
results_dict.append({
    'row_index': result.row_index,
    'tnved_code': result.tnved_code or '',
    'selection_reason': result.selection_reason,
    'confidence_score': result.confidence_score  # ← Эта строка должна быть
})
```

### 2. Проверьте логи worker

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
```

Ищите сообщение:
```
Applied color coding to X cells
```

### 3. Загрузите тестовый файл

1. Откройте http://localhost:8000
2. Войдите (admin/admin123)
3. Загрузите `test_web_color_coding.xlsx`
4. Запустите обработку
5. Скачайте результат
6. Проверьте цвета в Excel

## Быстрые команды

### Полный перезапуск с пересборкой

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

### Перезапуск только worker (без пересборки)

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

### Просмотр логов в реальном времени

```bash
# Все сервисы
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Только worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker

# Только web
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f web
```

### Очистка Redis

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec redis redis-cli FLUSHALL
```

### Проверка статуса контейнеров

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

### Вход в контейнер для отладки

```bash
# Web контейнер
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec web bash

# Worker контейнер
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker bash
```

## Отладка проблем

### Проблема: Изменения не применяются

**Решение 1:** Убедитесь, что используете dev конфигурацию

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

**Решение 2:** Проверьте монтирование volume

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker ls -la /app/batch_processor/workers/
```

**Решение 3:** Перезапустите worker

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

### Проблема: Worker не видит изменения

**Причина:** Celery кэширует модули Python

**Решение:** Перезапустите worker с очисткой кэша

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml stop worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml rm -f worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d worker
```

### Проблема: Цвета все еще не применяются

**Проверка 1:** Убедитесь, что код изменен

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker grep -n "confidence_score" /app/batch_processor/workers/processing_task.py
```

Должна быть строка около 1154:
```
1154:                    'confidence_score': result.confidence_score
```

**Проверка 2:** Проверьте логи на ошибки

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs worker | grep -i error
```

**Проверка 3:** Проверьте, что openpyxl установлен

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker python -c "from openpyxl.styles import PatternFill; print('OK')"
```

## Создание alias для удобства

Добавьте в `.bashrc` или `.zshrc`:

```bash
alias dc-dev='docker-compose -f docker-compose.yml -f docker-compose.dev.yml'
```

Затем используйте:

```bash
dc-dev up -d
dc-dev logs -f worker
dc-dev restart worker
dc-dev down
```

## Production vs Development

### Development (с монтированием кода)

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Преимущества:**
- ✅ Изменения кода применяются сразу
- ✅ Не нужно пересобирать образ
- ✅ Быстрая разработка
- ✅ Hot reload для web (uvicorn --reload)

**Недостатки:**
- ⚠️ Медленнее, чем production
- ⚠️ Требует перезапуска worker для применения изменений

### Production (без монтирования кода)

```bash
docker-compose up -d --build
```

**Преимущества:**
- ✅ Быстрее работает
- ✅ Изолированный код в образе
- ✅ Стабильная версия

**Недостатки:**
- ⚠️ Требует пересборки образа при изменениях
- ⚠️ Дольше деплой

## Рекомендации

1. **Для разработки:** Используйте `docker-compose.dev.yml`
2. **Для тестирования:** Используйте `docker-compose.yml` с пересборкой
3. **Для production:** Используйте `docker-compose.yml` с тегированными образами

## Проверочный список

- [ ] Остановлены старые контейнеры: `docker-compose down`
- [ ] Запущены с dev конфигурацией: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
- [ ] Проверено монтирование кода: `docker-compose exec worker ls -la /app/batch_processor/workers/`
- [ ] Проверен файл processing_task.py: `docker-compose exec worker grep confidence_score /app/batch_processor/workers/processing_task.py`
- [ ] Worker перезапущен: `docker-compose restart worker`
- [ ] Логи проверены: `docker-compose logs -f worker`
- [ ] Тестовый файл загружен через веб-интерфейс
- [ ] Результат скачан и проверен в Excel
- [ ] Цвета применены корректно

## Итог

После запуска с `docker-compose.dev.yml` изменения в коде будут применяться автоматически. Для worker может потребоваться перезапуск командой `docker-compose restart worker`.