# Быстрое исправление для Docker

## Проблема
Раскрашивание не работает в Docker, потому что код не монтируется как volume.

## Решение (3 команды)

### Windows:

```cmd
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

### Linux/Mac:

```bash
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

## Или используйте скрипт:

### Windows:
```cmd
restart-dev.bat
```

### Linux/Mac:
```bash
chmod +x restart-dev.sh
./restart-dev.sh
```

## Проверка

1. Откройте http://localhost:8000
2. Войдите: admin / admin123
3. Загрузите файл `test_web_color_coding.xlsx`
4. Скачайте результат
5. Проверьте цвета в Excel:
   - 🟢 Зеленый = высокая уверенность (score >= 0.185)
   - 🔴 Красный = низкая уверенность (score < 0.185)
   - ⚪ Белый = точное совпадение URL (score = 1.0)

## Проверка логов

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
```

Ищите сообщение:
```
Applied color coding to X cells
```

## Если не работает

### 1. Проверьте, что код монтируется:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec worker grep -n "confidence_score" /app/batch_processor/workers/processing_task.py
```

Должна быть строка ~1154:
```python
'confidence_score': result.confidence_score
```

### 2. Перезапустите worker:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

### 3. Полная перезагрузка:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Важно!

После изменений в коде worker нужно перезапускать:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

Web сервис перезагружается автоматически (uvicorn --reload).