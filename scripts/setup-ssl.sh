#!/bin/bash

# Скрипт для настройки SSL сертификата с Let's Encrypt
# Использование: ./setup-ssl.sh yourdomain.com admin@yourdomain.com

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функции логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Проверка аргументов
if [ $# -lt 2 ]; then
    echo "Использование: $0 <domain> <email>"
    echo "Пример: $0 batch-processor.yourdomain.com admin@yourdomain.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

log "Настройка SSL для домена: $DOMAIN"
log "Email для уведомлений: $EMAIL"

# Проверка что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    error "Скрипт должен быть запущен от root (используйте sudo)"
fi

# Проверка что домен резолвится на этот сервер
log "Проверка DNS для домена $DOMAIN..."
DOMAIN_IP=$(dig +short $DOMAIN)
SERVER_IP=$(curl -s ifconfig.me)

if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    warn "Домен $DOMAIN резолвится на $DOMAIN_IP, но IP сервера $SERVER_IP"
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Установка Certbot если не установлен
if ! command -v certbot &> /dev/null; then
    log "Установка Certbot..."
    
    # Определение дистрибутива
    if [ -f /etc/debian_version ]; then
        apt update
        apt install -y certbot python3-certbot-nginx
    elif [ -f /etc/redhat-release ]; then
        yum install -y epel-release
        yum install -y certbot python3-certbot-nginx
    else
        error "Неподдерживаемый дистрибутив"
    fi
fi

# Проверка что Nginx установлен
if ! command -v nginx &> /dev/null; then
    error "Nginx не установлен. Установите его сначала."
fi

# Создание базовой конфигурации Nginx для получения сертификата
log "Создание временной конфигурации Nginx..."

TEMP_CONFIG="/etc/nginx/sites-available/temp-$DOMAIN"
cat > $TEMP_CONFIG << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 200 'SSL setup in progress...';
        add_header Content-Type text/plain;
    }
}
EOF

# Создание директории для challenge
mkdir -p /var/www/html

# Активация временной конфигурации
ln -sf $TEMP_CONFIG /etc/nginx/sites-enabled/temp-$DOMAIN

# Удаление дефолтной конфигурации если существует
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi

# Проверка конфигурации Nginx
nginx -t || error "Ошибка в конфигурации Nginx"

# Перезапуск Nginx
systemctl restart nginx

# Получение SSL сертификата
log "Получение SSL сертификата от Let's Encrypt..."

certbot certonly \
    --webroot \
    --webroot-path=/var/www/html \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --domains $DOMAIN \
    --non-interactive

if [ $? -ne 0 ]; then
    error "Не удалось получить SSL сертификат"
fi

log "SSL сертификат успешно получен!"

# Создание финальной конфигурации Nginx
log "Создание финальной конфигурации Nginx..."

FINAL_CONFIG="/etc/nginx/sites-available/batch-processor"
cat > $FINAL_CONFIG << EOF
# HTTP -> HTTPS редирект
server {
    listen 80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS конфигурация
server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    
    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL настройки безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Заголовки безопасности
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Ограничение размера файлов
    client_max_body_size 100M;
    client_body_timeout 300s;
    
    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Port 443;
        
        # WebSocket поддержка
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Flower мониторинг
    location /flower/ {
        proxy_pass http://127.0.0.1:5555/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        
        auth_basic "Flower Monitoring";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    
    # Логи
    access_log /var/log/nginx/batch-processor.access.log;
    error_log /var/log/nginx/batch-processor.error.log;
}
EOF

# Удаление временной конфигурации
rm -f /etc/nginx/sites-enabled/temp-$DOMAIN
rm -f $TEMP_CONFIG

# Активация финальной конфигурации
ln -sf $FINAL_CONFIG /etc/nginx/sites-enabled/batch-processor

# Создание пароля для Flower
log "Создание пароля для Flower мониторинга..."
read -p "Введите имя пользователя для Flower: " FLOWER_USER
htpasswd -c /etc/nginx/.htpasswd $FLOWER_USER

# Проверка конфигурации
nginx -t || error "Ошибка в финальной конфигурации Nginx"

# Перезапуск Nginx
systemctl restart nginx

# Настройка автоматического обновления сертификатов
log "Настройка автоматического обновления сертификатов..."

# Создание скрипта обновления
cat > /usr/local/bin/renew-ssl.sh << 'EOF'
#!/bin/bash
/usr/bin/certbot renew --quiet
if [ $? -eq 0 ]; then
    /usr/bin/systemctl reload nginx
    echo "$(date): SSL certificates renewed successfully" >> /var/log/ssl-renewal.log
else
    echo "$(date): SSL certificate renewal failed" >> /var/log/ssl-renewal.log
fi
EOF

chmod +x /usr/local/bin/renew-ssl.sh

# Добавление в crontab
(crontab -l 2>/dev/null; echo "0 */12 * * * /usr/local/bin/renew-ssl.sh") | crontab -

# Проверка SSL
log "Проверка SSL конфигурации..."
sleep 5

if curl -s -I https://$DOMAIN/health | grep -q "200 OK"; then
    log "✅ SSL настроен успешно!"
    log "🌐 Ваше приложение доступно по адресу: https://$DOMAIN"
    log "🔍 Flower мониторинг: https://$DOMAIN/flower/"
else
    warn "SSL настроен, но приложение может быть недоступно"
    warn "Проверьте что Docker контейнеры запущены"
fi

# Информация о сертификате
log "Информация о сертификате:"
certbot certificates | grep -A 10 $DOMAIN

log "Настройка SSL завершена!"
log ""
log "Следующие шаги:"
log "1. Обновите .env.production файл:"
log "   DOMAIN=$DOMAIN"
log "   HTTPS_ONLY=true"
log "   SECURE_COOKIES=true"
log ""
log "2. Перезапустите Docker контейнеры:"
log "   docker-compose restart"
log ""
log "3. Проверьте работу приложения:"
log "   https://$DOMAIN"