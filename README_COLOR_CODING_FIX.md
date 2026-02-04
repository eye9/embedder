# Исправление раскрашивания ячеек в Docker

## 🎯 Проблема
Раскрашивание ячеек по similarity score не работает в Docker, потому что код не монтируется как volume и изменения не попадают в контейнер.

## ✅ Решение
Использовать `docker-compose.dev.yml` для монтирования кода как volume.

---

## 🚀 Быстрый старт

### Шаг 1: Остановите текущие контейнеры

```bash
docker-compose down
```

### Шаг 2: Запустите с dev конфигурацией

**Windows:**
```cmd
restart-dev.bat
```

**Linux/Mac:**
```bash
chmod +x restart-dev.sh
./restart-dev.sh
```

**Или вручную:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

### Шаг 3: Проверьте исправление

**Windows:**
```cmd
VERIFY_DOCKER_FIX.bat
```

**Linux/Mac:**
```bash
chmod +x VERIFY_DOCKER_FIX.sh
./VERIFY_DOCKER_FIX.sh
```

---

## 📋 Что было исправлено

**Файл:** `batch_processor/workers/processing_task.py` (строка ~1154)

**Добавлено:**
```python
'confidence_score': result.confidence_score
```

**Полный контекст:**
```python
results_dict.append({
    'row_index': result.row_index,
    'tnved_code': result.tnved_code or '',
    'selection_reason': result.selection_reason,
    'confidence_score': result.confidence_score  # ← ДОБАВЛЕНО
})
```

---

## 🧪 Тестирование

### 1. Откройте веб-интерфейс
http://localhost:8000

### 2. Войдите
- Username: `admin`
- Password: `admin123`

### 3. Загрузите тестовый файл
`test_web_color_coding.xlsx`

### 4. Запустите обработку
- Processing Mode: All rows
- Algorithm: similarity_top1

### 5. Скачайте результат

### 6. Проверьте цвета в Excel

**Ожидаемые цвета:**

| Confidence Score | Цвет | Описание |
|-----------------|------|----------|
| = 1.0 | ⚪ Белый | Точное совпадение URL |
| >= 0.185 | 🟢 Зеленый | Высокая уверенность |
| < 0.185 | 🔴 Красный | Низкая уверенность |

---

## 📊 Проверка логов

### Просмотр логов worker

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
```

### Что искать в логах

```
Applied color coding to X cells
```

Если это сообщение есть → раскрашивание работает ✅

---

## 🔧 Полезные команды

### Перезапуск worker (после изменений в коде)

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

### Просмотр всех логов

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Просмотр статуса контейнеров

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

### Очистка Redis

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec redis redis-cli FLUSHALL
```

### Вход в контейнер для отладки

```bash
# Worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker bash

# Web
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec web bash
```

### Проверка кода в контейнере

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker grep -n "confidence_score" /app/batch_processor/workers/processing_task.py
```

---

## 🐛 Устранение проблем

### Проблема: Цвета не применяются

**Решение 1:** Проверьте, что используется dev конфигурация

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

**Решение 2:** Перезапустите worker

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

**Решение 3:** Полная перезагрузка

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### Проблема: Worker не видит изменения

**Причина:** Celery кэширует модули Python

**Решение:** Пересоздайте worker

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml stop worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml rm -f worker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d worker
```

### Проблема: Код не монтируется

**Проверка:**

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker ls -la /app/batch_processor/workers/
```

**Решение:** Убедитесь, что используете `docker-compose.dev.yml`

### Проблема: openpyxl не установлен

**Проверка:**

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker python -c "from openpyxl.styles import PatternFill; print('OK')"
```

**Решение:** Пересоберите образ

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

---

## 📚 Дополнительная документация

- `DOCKER_DEV_SETUP.md` - Подробная инструкция по настройке dev окружения
- `QUICK_DOCKER_FIX.md` - Краткая инструкция по исправлению
- `COLOR_CODING_FINAL_FIX.md` - Полное описание исправления
- `WEB_COLOR_CODING_TEST.md` - Инструкции по тестированию

---

## ✅ Проверочный список

- [ ] Остановлены старые контейнеры
- [ ] Запущены с dev конфигурацией
- [ ] Worker перезапущен
- [ ] Проверен код в контейнере (confidence_score присутствует)
- [ ] Проверены логи (нет ошибок)
- [ ] Тестовый файл загружен
- [ ] Результат скачан
- [ ] Цвета проверены в Excel
- [ ] Логи содержат "Applied color coding to X cells"

---

## 🎓 Понимание проблемы

### Почему не работало в Docker?

1. **Production режим:** Код копируется в образ при сборке
2. **Изменения не попадают:** После изменения кода нужна пересборка
3. **Celery кэширование:** Worker кэширует модули Python

### Как работает dev режим?

1. **Монтирование кода:** Код монтируется как volume (`.:/app`)
2. **Изменения видны сразу:** Файлы на хосте = файлы в контейнере
3. **Hot reload:** Web перезагружается автоматически
4. **Worker требует перезапуска:** Celery нужно перезапускать вручную

---

## 🚀 Production деплой

Для production используйте обычный `docker-compose.yml`:

```bash
# Пересоберите образ с изменениями
docker-compose build

# Запустите
docker-compose up -d

# Или с пересборкой
docker-compose up -d --build
```

**Важно:** В production коде изменения требуют пересборки образа!

---

## 💡 Советы

1. **Для разработки:** Всегда используйте `docker-compose.dev.yml`
2. **После изменений в worker:** Перезапускайте worker
3. **Проверяйте логи:** Они покажут, применяется ли раскрашивание
4. **Используйте скрипты:** `restart-dev.bat` / `restart-dev.sh` для быстрого перезапуска
5. **Проверяйте исправление:** `VERIFY_DOCKER_FIX.bat` / `VERIFY_DOCKER_FIX.sh`

---

## 📞 Поддержка

Если проблема сохраняется:

1. Проверьте логи: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs worker`
2. Проверьте код в контейнере: `docker-compose exec worker grep confidence_score /app/batch_processor/workers/processing_task.py`
3. Убедитесь, что используется dev конфигурация
4. Попробуйте полную перезагрузку с очисткой

---

## ✨ Итог

После запуска с `docker-compose.dev.yml` раскрашивание ячеек должно работать корректно. Изменения в коде применяются автоматически, worker требует перезапуска после изменений.