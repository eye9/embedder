# Подробная инструкция по деплою Docker контейнеров

## Обзор архитектуры

Система состоит из следующих сервисов:
- **Web** - веб-приложение FastAPI с интерфейсом пользователя
- **Worker** - Celery worker для обработки файлов
- **Cleanup Worker** - Celery worker для очистки временных файлов
- **Scheduler** - Celery Beat для периодических задач
- **Redis** - брокер сообщений и кэш
- **Flower** - мониторинг Celery (опционально)

## Предварительные требования

### Системные требования
- Docker 20.10+
- Docker Compose 2.0+
- Минимум 4GB RAM
- Минимум 10GB свободного места на диске

### Установка Docker (если не установлен)
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Перезайдите в систему после добавления в группу docker
```

## Конфигурация окружений

### 1. Разработка (Development)

#### Настройка файлов конфигурации
```bash
# Скопируйте пример конфигурации
cp .env.example .env.development

# Отредактируйте файл .env.development
nano .env.development
```

#### Содержимое .env.development:
```bash
# Development Environment
BATCH_PROCESSOR_ENV=development
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Authentication (простые пароли для разработки)
ADMIN_PASSWORD=admin123
OPERATOR_PASSWORD=operator123
SESSION_SECRET_KEY=dev-secret-key-change-in-production

# Processing
CHUNK_SIZE=1000
CONFIDENCE_THRESHOLD=0.7
MAX_FILE_SIZE_MB=100

# Features (включены для тестирования)
ENABLE_LLM=true
ENABLE_ANALYTICS=true
ENABLE_NOTIFICATIONS=true
DEBUG=true
LOG_LEVEL=debug
```

#### Команды для запуска разработки:
```bash
# Запуск в режиме разработки с hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Запуск в фоновом режиме
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Просмотр логов
docker-compose logs -f web

# Остановка
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### 2. Staging (Тестирование)

#### Настройка переменных окружения
```bash
# Создайте файл окружения для staging
cp .env.example .env.staging

# Отредактируйте файл
nano .env.staging
```

#### Содержимое .env.staging:
```bash
# Staging Environment
BATCH_PROCESSOR_ENV=staging
BATCH_PROCESSOR_CONFIG=/app/batch_processor_config.staging.yaml

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=staging_redis_password_123

# Authentication
ADMIN_PASSWORD=staging_admin_secure_password
TESTER_PASSWORD=tester_password_123
OPERATOR_PASSWORD=operator_password_123
SESSION_SECRET_KEY=staging-very-long-secret-key-change-this

# Security
ALLOWED_HOST=staging.yourdomain.com
STAGING_DOMAIN=staging.yourdomain.com
HTTPS_ONLY=false
SECURE_COOKIES=false

# Performance
WEB_WORKERS=1
CHUNK_SIZE=1000
MAX_FILE_SIZE_MB=100
MAX_STORAGE_GB=10.0

# Features
ENABLE_LLM=true
ENABLE_ANALYTICS=true
ENABLE_NOTIFICATIONS=true
LOG_LEVEL=info
```

#### Команды для staging:
```bash
# Используйте скрипт деплоя
chmod +x scripts/deployment/deploy.sh
./scripts/deployment/deploy.sh staging

# Или вручную:
docker-compose --env-file .env.staging up -d --build

# Проверка статуса
./scripts/deployment/deploy.sh status

# Проверка здоровья сервисов
./scripts/deployment/deploy.sh health
```

### 3. Production (Продакшн)

#### Настройка переменных окружения
```bash
# Создайте файл окружения для продакшн
cp .env.example .env.production

# ВАЖНО: Используйте безопасные пароли!
nano .env.production
```

#### Содержимое .env.production:
```bash
# Production Environment
BATCH_PROCESSOR_ENV=production
BATCH_PROCESSOR_CONFIG=/app/batch_processor_config.production.yaml

# Redis (обязательно установите пароль!)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=very_secure_redis_password_change_this

# Authentication (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!)
ADMIN_PASSWORD=very_secure_admin_password_min_12_chars
OPERATOR_PASSWORD=secure_operator_password_min_12_chars
SESSION_SECRET_KEY=very-long-random-secret-key-for-session-security-change-this

# Security
DOMAIN=spegat.com
ALLOWED_HOST=spegat.com
HTTPS_ONLY=true
SECURE_COOKIES=true

# Performance (оптимизировано для продакшн)
WEB_WORKERS=2
CHUNK_SIZE=500
MAX_FILE_SIZE_MB=50
MAX_STORAGE_GB=5.0
CLEANUP_INTERVAL_HOURS=2

# Features (отключены для безопасности)
ENABLE_LLM=false
ENABLE_ANALYTICS=false
ENABLE_NOTIFICATIONS=false
LOG_LEVEL=warning

# Monitoring
BACKUP_ENABLED=true
BACKUP_DIR=/app/backups
```

#### Команды для продакшн:
```bash
# Установите переменные окружения перед деплоем
export ADMIN_PASSWORD="your_secure_admin_password"
export SESSION_SECRET_KEY="your_very_long_secret_key"
export REDIS_PASSWORD="your_redis_password"

# Запуск деплоя
./scripts/deployment/deploy.sh production

# Или вручную с проверками:
docker-compose --env-file .env.production up -d --build

# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs -f web
```

## Структура файлов и директорий

### Обязательные директории
```bash
# Создайте необходимые директории
mkdir -p temp_files
mkdir -p logs
mkdir -p chroma_db
mkdir -p backups

# Установите права доступа
chmod 755 temp_files logs chroma_db backups
```

### Конфигурационные файлы
- `batch_processor_config.yaml` - базовая конфигурация
- `batch_processor_config.docker.yaml` - для Docker
- `batch_processor_config.staging.yaml` - для staging
- `batch_processor_config.production.yaml` - для продакшн

## Команды управления

### Основные команды Docker Compose

#### Запуск сервисов
```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск с пересборкой
docker-compose up -d --build

# Запуск конкретного сервиса
docker-compose up -d web

# Запуск с мониторингом Flower
docker-compose --profile monitoring up -d
```

#### Остановка и очистка
```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes
docker-compose down -v

# Полная очистка (осторожно!)
docker-compose down -v --rmi all
```

#### Мониторинг и логи
```bash
# Просмотр статуса сервисов
docker-compose ps

# Просмотр логов всех сервисов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f web
docker-compose logs -f worker
docker-compose logs -f redis

# Просмотр последних 100 строк логов
docker-compose logs --tail=100 web
```

### Команды для отладки

#### Подключение к контейнерам
```bash
# Подключение к веб-контейнеру
docker-compose exec web bash

# Подключение к Redis
docker-compose exec redis redis-cli

# Подключение к worker
docker-compose exec worker bash
```

#### Проверка состояния Celery
```bash
# Проверка активных worker'ов
docker-compose exec worker celery -A batch_processor.workers.celery_app inspect active

# Проверка статистики
docker-compose exec worker celery -A batch_processor.workers.celery_app inspect stats

# Проверка зарегистрированных задач
docker-compose exec worker celery -A batch_processor.workers.celery_app inspect registered
```

## Мониторинг и здоровье системы

### Health Check endpoints
- `http://localhost:8000/health` - общее состояние системы
- `http://localhost:8000/health/redis` - состояние Redis
- `http://localhost:8000/health/celery` - состояние Celery
- `http://localhost:8000/health/disk` - использование диска

### Flower (мониторинг Celery)
```bash
# Запуск с Flower
docker-compose --profile monitoring up -d

# Доступ к Flower
# http://localhost:5555
```

### Проверка ресурсов
```bash
# Использование ресурсов контейнерами
docker stats

# Размер volumes
docker system df

# Информация о контейнерах
docker-compose top
```

## Резервное копирование и восстановление

### Создание резервной копии
```bash
# Создание директории для бэкапов
mkdir -p backups/$(date +%Y%m%d_%H%M%S)

# Бэкап Redis данных
docker-compose exec redis redis-cli BGSAVE
docker cp batch_processor_redis:/data/dump.rdb backups/$(date +%Y%m%d_%H%M%S)/

# Бэкап файлов
tar -czf backups/$(date +%Y%m%d_%H%M%S)/temp_files.tar.gz temp_files/
tar -czf backups/$(date +%Y%m%d_%H%M%S)/logs.tar.gz logs/
```

### Восстановление из резервной копии
```bash
# Остановка сервисов
docker-compose down

# Восстановление файлов
tar -xzf backups/BACKUP_DATE/temp_files.tar.gz
tar -xzf backups/BACKUP_DATE/logs.tar.gz

# Восстановление Redis
docker-compose up -d redis
docker cp backups/BACKUP_DATE/dump.rdb batch_processor_redis:/data/
docker-compose restart redis

# Запуск остальных сервисов
docker-compose up -d
```

## Обновление системы

### Обновление кода
```bash
# Получение последних изменений
git pull origin main

# Пересборка и перезапуск
docker-compose down
docker-compose up -d --build

# Проверка здоровья после обновления
./scripts/deployment/deploy.sh health
```

### Обновление конфигурации
```bash
# После изменения конфигурации
docker-compose restart web worker cleanup_worker scheduler
```

## Решение проблем

### Частые проблемы и решения

#### 1. Контейнер не запускается
```bash
# Проверка логов
docker-compose logs web

# Проверка конфигурации
docker-compose config

# Пересборка образа
docker-compose build --no-cache web
```

#### 2. Redis недоступен
```bash
# Проверка состояния Redis
docker-compose exec redis redis-cli ping

# Перезапуск Redis
docker-compose restart redis

# Проверка подключения
docker-compose exec web python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
```

#### 3. Celery worker не работает
```bash
# Проверка статуса worker
docker-compose exec worker celery -A batch_processor.workers.celery_app inspect ping

# Перезапуск worker
docker-compose restart worker

# Проверка очереди задач
docker-compose exec redis redis-cli llen celery
```

#### 4. Проблемы с правами доступа
```bash
# Исправление прав на директории
sudo chown -R $USER:$USER temp_files logs chroma_db

# Или внутри контейнера
docker-compose exec web chown -R appuser:appuser /app/temp_files /app/logs
```

#### 5. Нехватка места на диске
```bash
# Очистка старых образов
docker image prune -f

# Очистка неиспользуемых volumes
docker volume prune -f

# Очистка временных файлов
docker-compose exec web find /app/temp_files -type f -mtime +1 -delete
```

## Безопасность

### Рекомендации по безопасности

1. **Пароли**: Всегда используйте сложные пароли в продакшн
2. **Секретные ключи**: Генерируйте длинные случайные ключи
3. **HTTPS**: Включите HTTPS в продакшн окружении
4. **Firewall**: Ограничьте доступ к портам
5. **Обновления**: Регулярно обновляйте образы Docker

### Генерация безопасных паролей
```bash
# Генерация случайного пароля
openssl rand -base64 32

# Генерация секретного ключа для сессий
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Производительность

### Оптимизация для продакшн

1. **Ресурсы**: Выделите достаточно RAM и CPU
2. **Workers**: Настройте количество web workers
3. **Chunk size**: Уменьшите размер чанков для стабильности
4. **Cleanup**: Настройте автоматическую очистку
5. **Мониторинг**: Включите мониторинг производительности

### Настройка ресурсов в docker-compose.yml
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## Настройка доступа через интернет

### Вариант 1: Доступ по IP адресу

#### Настройка сервера
```bash
# 1. Убедитесь, что порты открыты в firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # Если используете прямой доступ

# 2. Проверьте, что Docker слушает на всех интерфейсах
# В docker-compose.yml порты должны быть настроены как:
ports:
  - "0.0.0.0:8000:8000"  # Явно указываем все интерфейсы
```

#### Обновление конфигурации для IP доступа
```bash
# Отредактируйте .env.production
nano .env.production

# Добавьте ваш внешний IP
DOMAIN=YOUR_SERVER_IP
ALLOWED_HOST=YOUR_SERVER_IP
CORS_ORIGINS=http://YOUR_SERVER_IP:8000,https://YOUR_SERVER_IP

# Для начала отключите HTTPS (настроим позже)
HTTPS_ONLY=false
SECURE_COOKIES=false
```

#### Проверка доступа
```bash
# Локальная проверка
curl http://localhost:8000/health

# Внешняя проверка (замените IP)
curl http://YOUR_SERVER_IP:8000/health

# Доступ через браузер
# http://YOUR_SERVER_IP:8000
```

### Вариант 2: Доступ по доменному имени

#### Настройка DNS
```bash
# 1. Купите домен (например, на reg.ru, namecheap.com)
# 2. Настройте A-запись в DNS:
#    batch-processor.yourdomain.com -> YOUR_SERVER_IP
#    
# 3. Проверьте DNS (может занять до 24 часов)
nslookup batch-processor.yourdomain.com
```

#### Обновление конфигурации для домена
```bash
# Отредактируйте .env.production
nano .env.production

# Настройте домен
DOMAIN=batch-processor.yourdomain.com
ALLOWED_HOST=batch-processor.yourdomain.com
CORS_ORIGINS=https://batch-processor.yourdomain.com

# Пока отключите HTTPS (настроим с SSL)
HTTPS_ONLY=false
SECURE_COOKIES=false
```

### Вариант 3: Настройка с IIS Reverse Proxy (для Windows Server)

Если у вас Windows Server с IIS, используйте специальную инструкцию:

**📋 Подробная инструкция:** [IIS_REVERSE_PROXY_SETUP.md](IIS_REVERSE_PROXY_SETUP.md)

#### Быстрая настройка IIS
```powershell
# Запустите PowerShell от имени администратора

# 1. Установите необходимые компоненты IIS
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole, IIS-WebServer, IIS-CommonHttpFeatures

# 2. Скачайте и установите:
# - Application Request Routing (ARR) 3.0
# - URL Rewrite Module 2.1

# 3. Настройте Docker контейнеры для локального доступа
docker-compose -f docker-compose.windows.yml up -d --build

# 4. Запустите автоматический деплой
.\scripts\deploy-iis.ps1 -Domain "your-domain.com"

# Для SSL:
.\scripts\deploy-iis.ps1 -Domain "your-domain.com" -EnableSSL -CertificateThumbprint "YOUR_CERT_THUMBPRINT"
```

#### Основные файлы для IIS:
- `iis/web.config` - конфигурация reverse proxy
- `scripts/deploy-iis.ps1` - автоматический деплой
- `docker-compose.windows.yml` - Docker для Windows

### Вариант 4: Настройка с Nginx Reverse Proxy (для Linux)

#### Установка Nginx
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

#### Создание конфигурации Nginx
```bash
# Создайте конфигурацию сайта
sudo nano /etc/nginx/sites-available/batch-processor

# Содержимое файла:
```

```nginx
server {
    listen 80;
    server_name batch-processor.yourdomain.com;  # Замените на ваш домен или IP
    
    # Ограничение размера загружаемых файлов
    client_max_body_size 100M;
    
    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket поддержка
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Таймауты для длительных операций
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
    
    # Flower мониторинг (опционально)
    location /flower/ {
        proxy_pass http://127.0.0.1:5555/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Базовая аутентификация для Flower
        auth_basic "Flower Monitoring";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    
    # Статические файлы (если есть)
    location /static/ {
        alias /path/to/your/static/files/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Логи
    access_log /var/log/nginx/batch-processor.access.log;
    error_log /var/log/nginx/batch-processor.error.log;
}
```

#### Активация конфигурации Nginx
```bash
# Создайте символическую ссылку
sudo ln -s /etc/nginx/sites-available/batch-processor /etc/nginx/sites-enabled/

# Проверьте конфигурацию
sudo nginx -t

# Перезапустите Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

# Создайте пароль для Flower (опционально)
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

#### Обновление Docker конфигурации для Nginx
```bash
# Отредактируйте docker-compose.yml
nano docker-compose.yml

# Измените порты на локальные (только для localhost)
ports:
  - "127.0.0.1:8000:8000"  # Только локальный доступ
  - "127.0.0.1:5555:5555"  # Flower только локально
```

### Вариант 4: Настройка SSL/HTTPS с Let's Encrypt

#### Установка Certbot
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx
```

#### Получение SSL сертификата
```bash
# Остановите Nginx временно
sudo systemctl stop nginx

# Получите сертификат (замените домен)
sudo certbot certonly --standalone -d batch-processor.yourdomain.com

# Или если Nginx уже настроен
sudo certbot --nginx -d batch-processor.yourdomain.com

# Запустите Nginx
sudo systemctl start nginx
```

#### Обновление Nginx конфигурации для HTTPS
```bash
sudo nano /etc/nginx/sites-available/batch-processor
```

```nginx
# HTTP -> HTTPS редирект
server {
    listen 80;
    server_name batch-processor.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS конфигурация
server {
    listen 443 ssl http2;
    server_name batch-processor.yourdomain.com;
    
    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/batch-processor.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/batch-processor.yourdomain.com/privkey.pem;
    
    # SSL настройки безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS заголовок
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Ограничение размера файлов
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Port 443;
        
        # WebSocket поддержка
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
    
    # Flower с SSL
    location /flower/ {
        proxy_pass http://127.0.0.1:5555/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        
        auth_basic "Flower Monitoring";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

#### Обновление приложения для HTTPS
```bash
# Отредактируйте .env.production
nano .env.production

# Включите HTTPS настройки
DOMAIN=batch-processor.yourdomain.com
ALLOWED_HOST=batch-processor.yourdomain.com
HTTPS_ONLY=true
SECURE_COOKIES=true
CORS_ORIGINS=https://batch-processor.yourdomain.com

# Перезапустите приложение
docker-compose restart web
```

#### Автоматическое обновление сертификатов
```bash
# Добавьте в crontab
sudo crontab -e

# Добавьте строку для автоматического обновления (каждые 12 часов)
0 */12 * * * /usr/bin/certbot renew --quiet && /usr/bin/systemctl reload nginx
```

### Настройка Firewall

#### UFW (Ubuntu/Debian)
```bash
# Базовые правила
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Разрешить SSH
sudo ufw allow ssh

# Разрешить HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Закрыть прямой доступ к приложению (если используете Nginx)
sudo ufw deny 8000/tcp

# Включить firewall
sudo ufw enable

# Проверить статус
sudo ufw status
```

#### iptables (CentOS/RHEL)
```bash
# Разрешить HTTP и HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Закрыть прямой доступ к приложению
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP

# Сохранить правила
sudo service iptables save
```

### Мониторинг и логи

#### Настройка логирования Nginx
```bash
# Создайте директорию для логов
sudo mkdir -p /var/log/nginx

# Настройте ротацию логов
sudo nano /etc/logrotate.d/nginx
```

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 nginx nginx
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}
```

#### Мониторинг доступности
```bash
# Создайте скрипт проверки
nano /home/user/check_service.sh
```

```bash
#!/bin/bash
URL="https://batch-processor.yourdomain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): Service is UP"
else
    echo "$(date): Service is DOWN (HTTP $RESPONSE)"
    # Отправить уведомление или перезапустить сервис
    # docker-compose restart web
fi
```

```bash
# Сделайте скрипт исполняемым
chmod +x /home/user/check_service.sh

# Добавьте в crontab для проверки каждые 5 минут
crontab -e
*/5 * * * * /home/user/check_service.sh >> /var/log/service_check.log
```

### Безопасность для интернет доступа

#### Дополнительные настройки безопасности
```bash
# 1. Отключите ненужные сервисы
sudo systemctl disable apache2  # если установлен
sudo systemctl stop apache2

# 2. Настройте fail2ban для защиты от брутфорса
sudo apt install fail2ban

# Создайте конфигурацию для Nginx
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/batch-processor.error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/batch-processor.error.log
maxretry = 10
```

#### Ограничение доступа по IP (опционально)
```nginx
# В конфигурации Nginx добавьте
location / {
    # Разрешить доступ только с определенных IP
    allow 192.168.1.0/24;  # Локальная сеть
    allow 203.0.113.0/24;  # Офисная сеть
    deny all;
    
    proxy_pass http://127.0.0.1:8000;
    # ... остальные настройки
}
```

### Проверка доступности

#### Тестирование доступа
```bash
# Проверка HTTP
curl -I http://your-domain.com

# Проверка HTTPS
curl -I https://your-domain.com

# Проверка health endpoint
curl https://your-domain.com/health

# Проверка с разных локаций
# Используйте онлайн сервисы:
# - https://www.whatsmydns.net/
# - https://tools.pingdom.com/
# - https://gtmetrix.com/
```

#### Мониторинг производительности
```bash
# Установите htop для мониторинга ресурсов
sudo apt install htop

# Мониторинг сетевых соединений
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Проверка использования портов
sudo ss -tulpn
```

### Резюме по настройке интернет доступа

**Для простого тестирования:**
- Используйте доступ по IP с портом 8000
- Откройте порт в firewall
- Обновите ALLOWED_HOST в конфигурации

**Для продакшн использования:**
- Настройте домен с DNS
- Используйте Nginx как reverse proxy
- Установите SSL сертификат от Let's Encrypt
- Настройте firewall и мониторинг
- Включите все настройки безопасности

**Обязательные шаги для продакшн:**
1. Смените все пароли по умолчанию
2. Настройте HTTPS
3. Ограничьте доступ через firewall
4. Настройте мониторинг и логирование
5. Регулярно обновляйте систему и сертификаты

## Заключение

Эта инструкция покрывает все основные аспекты деплоя системы в Docker. Для продакшн окружения обязательно:

1. Измените все пароли по умолчанию
2. Настройте HTTPS
3. Включите мониторинг
4. Настройте резервное копирование
5. Регулярно обновляйте систему

При возникновении проблем обращайтесь к разделу "Решение проблем" или проверяйте логи сервисов.