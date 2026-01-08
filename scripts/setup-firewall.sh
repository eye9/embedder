#!/bin/bash

# Скрипт для настройки firewall для Batch Excel Processor
# Поддерживает UFW (Ubuntu/Debian) и firewalld (CentOS/RHEL)

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

# Проверка что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    error "Скрипт должен быть запущен от root (используйте sudo)"
fi

# Определение системы и firewall
detect_firewall() {
    if command -v ufw &> /dev/null; then
        echo "ufw"
    elif command -v firewall-cmd &> /dev/null; then
        echo "firewalld"
    elif command -v iptables &> /dev/null; then
        echo "iptables"
    else
        echo "none"
    fi
}

FIREWALL=$(detect_firewall)
log "Обнаружен firewall: $FIREWALL"

# Функция для настройки UFW (Ubuntu/Debian)
setup_ufw() {
    log "Настройка UFW firewall..."
    
    # Установка UFW если не установлен
    if ! command -v ufw &> /dev/null; then
        log "Установка UFW..."
        apt update
        apt install -y ufw
    fi
    
    # Сброс правил к дефолтным
    ufw --force reset
    
    # Базовые правила
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH (важно разрешить до включения firewall!)
    ufw allow ssh
    ufw allow 22/tcp
    
    # HTTP и HTTPS
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    
    # Закрыть прямой доступ к приложению (если используется Nginx)
    read -p "Используете ли вы Nginx reverse proxy? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Закрываем прямой доступ к портам приложения..."
        ufw deny 8000/tcp comment 'Block direct app access'
        ufw deny 5555/tcp comment 'Block direct Flower access'
    else
        log "Разрешаем прямой доступ к приложению..."
        ufw allow 8000/tcp comment 'Batch Processor Web'
        
        read -p "Разрешить доступ к Flower мониторингу? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ufw allow 5555/tcp comment 'Flower monitoring'
        fi
    fi
    
    # Дополнительные порты
    read -p "Нужно ли разрешить дополнительные порты? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Введите порты через пробел (например: 3000 9000): " EXTRA_PORTS
        for port in $EXTRA_PORTS; do
            ufw allow $port/tcp comment "Custom port $port"
            log "Разрешен порт: $port"
        done
    fi
    
    # Ограничение по IP (опционально)
    read -p "Ограничить доступ только с определенных IP? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Введите разрешенные IP/подсети (например: 192.168.1.0/24 203.0.113.5): " ALLOWED_IPS
        
        # Удаляем общие правила для HTTP/HTTPS
        ufw delete allow 80/tcp
        ufw delete allow 443/tcp
        
        # Добавляем правила для конкретных IP
        for ip in $ALLOWED_IPS; do
            ufw allow from $ip to any port 80 comment "HTTP from $ip"
            ufw allow from $ip to any port 443 comment "HTTPS from $ip"
            log "Разрешен доступ с IP: $ip"
        done
    fi
    
    # Включение firewall
    log "Включение UFW firewall..."
    ufw --force enable
    
    # Показать статус
    log "Статус UFW:"
    ufw status verbose
}

# Функция для настройки firewalld (CentOS/RHEL)
setup_firewalld() {
    log "Настройка firewalld..."
    
    # Установка firewalld если не установлен
    if ! command -v firewall-cmd &> /dev/null; then
        log "Установка firewalld..."
        yum install -y firewalld
    fi
    
    # Запуск и включение firewalld
    systemctl start firewalld
    systemctl enable firewalld
    
    # Базовые сервисы
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    
    # Проверка использования Nginx
    read -p "Используете ли вы Nginx reverse proxy? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Разрешаем прямой доступ к приложению..."
        firewall-cmd --permanent --add-port=8000/tcp
        
        read -p "Разрешить доступ к Flower мониторингу? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            firewall-cmd --permanent --add-port=5555/tcp
        fi
    fi
    
    # Дополнительные порты
    read -p "Нужно ли разрешить дополнительные порты? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Введите порты через пробел (например: 3000 9000): " EXTRA_PORTS
        for port in $EXTRA_PORTS; do
            firewall-cmd --permanent --add-port=$port/tcp
            log "Разрешен порт: $port"
        done
    fi
    
    # Применение правил
    firewall-cmd --reload
    
    # Показать статус
    log "Статус firewalld:"
    firewall-cmd --list-all
}

# Функция для настройки iptables
setup_iptables() {
    log "Настройка iptables..."
    
    # Сохранение текущих правил
    iptables-save > /tmp/iptables.backup
    
    # Очистка правил
    iptables -F
    iptables -X
    iptables -t nat -F
    iptables -t nat -X
    iptables -t mangle -F
    iptables -t mangle -X
    
    # Базовые правила
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT ACCEPT
    
    # Разрешить loopback
    iptables -A INPUT -i lo -j ACCEPT
    iptables -A OUTPUT -o lo -j ACCEPT
    
    # Разрешить установленные соединения
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    
    # SSH
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    
    # HTTP и HTTPS
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT
    
    # Проверка использования Nginx
    read -p "Используете ли вы Nginx reverse proxy? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Разрешаем прямой доступ к приложению..."
        iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
        
        read -p "Разрешить доступ к Flower мониторингу? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            iptables -A INPUT -p tcp --dport 5555 -j ACCEPT
        fi
    fi
    
    # Сохранение правил
    if command -v iptables-save &> /dev/null; then
        iptables-save > /etc/iptables/rules.v4
    fi
    
    log "Правила iptables настроены"
    iptables -L -n
}

# Установка fail2ban для дополнительной защиты
setup_fail2ban() {
    log "Настройка fail2ban для защиты от брутфорса..."
    
    # Установка fail2ban
    if command -v apt &> /dev/null; then
        apt update
        apt install -y fail2ban
    elif command -v yum &> /dev/null; then
        yum install -y epel-release
        yum install -y fail2ban
    fi
    
    # Создание конфигурации
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Время блокировки (в секундах)
bantime = 3600
# Время окна для подсчета попыток (в секундах)
findtime = 600
# Максимальное количество попыток
maxretry = 5
# Игнорировать локальные IP
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 1800

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/*.log
maxretry = 3
bantime = 3600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/*.log
maxretry = 10
bantime = 600

[nginx-botsearch]
enabled = true
filter = nginx-botsearch
logpath = /var/log/nginx/*.log
maxretry = 2
bantime = 86400
EOF
    
    # Создание фильтра для nginx
    cat > /etc/fail2ban/filter.d/nginx-botsearch.conf << 'EOF'
[Definition]
failregex = ^<HOST> -.*"(GET|POST).*HTTP.*" (404|444) .*$
ignoreregex =
EOF
    
    # Запуск fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    
    log "fail2ban настроен и запущен"
}

# Создание скрипта мониторинга
create_monitoring_script() {
    log "Создание скрипта мониторинга firewall..."
    
    cat > /usr/local/bin/firewall-monitor.sh << 'EOF'
#!/bin/bash

# Скрипт мониторинга firewall и безопасности

LOG_FILE="/var/log/firewall-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Функция логирования
log_message() {
    echo "[$DATE] $1" >> $LOG_FILE
}

# Проверка активных соединений
check_connections() {
    CONNECTIONS=$(netstat -tn | grep :80 | wc -l)
    if [ $CONNECTIONS -gt 100 ]; then
        log_message "WARNING: High number of HTTP connections: $CONNECTIONS"
    fi
    
    HTTPS_CONNECTIONS=$(netstat -tn | grep :443 | wc -l)
    if [ $HTTPS_CONNECTIONS -gt 100 ]; then
        log_message "WARNING: High number of HTTPS connections: $HTTPS_CONNECTIONS"
    fi
}

# Проверка fail2ban статуса
check_fail2ban() {
    if command -v fail2ban-client &> /dev/null; then
        BANNED_IPS=$(fail2ban-client status | grep "Jail list" | cut -d: -f2 | wc -w)
        if [ $BANNED_IPS -gt 0 ]; then
            log_message "INFO: fail2ban active jails: $BANNED_IPS"
        fi
    fi
}

# Проверка подозрительной активности
check_suspicious_activity() {
    # Проверка попыток подключения к закрытым портам
    SUSPICIOUS=$(grep "$(date '+%b %d')" /var/log/syslog | grep -i "blocked\|denied\|drop" | wc -l)
    if [ $SUSPICIOUS -gt 50 ]; then
        log_message "WARNING: High number of blocked connections today: $SUSPICIOUS"
    fi
}

# Основная функция
main() {
    log_message "Starting firewall monitoring check"
    check_connections
    check_fail2ban
    check_suspicious_activity
    log_message "Firewall monitoring check completed"
}

main
EOF
    
    chmod +x /usr/local/bin/firewall-monitor.sh
    
    # Добавление в crontab для запуска каждые 15 минут
    (crontab -l 2>/dev/null; echo "*/15 * * * * /usr/local/bin/firewall-monitor.sh") | crontab -
    
    log "Скрипт мониторинга создан: /usr/local/bin/firewall-monitor.sh"
}

# Главная функция
main() {
    log "Начало настройки firewall для Batch Excel Processor"
    
    case $FIREWALL in
        "ufw")
            setup_ufw
            ;;
        "firewalld")
            setup_firewalld
            ;;
        "iptables")
            setup_iptables
            ;;
        "none")
            error "Firewall не найден. Установите ufw, firewalld или iptables"
            ;;
    esac
    
    # Установка fail2ban
    read -p "Установить fail2ban для защиты от брутфорса? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        setup_fail2ban
    fi
    
    # Создание скрипта мониторинга
    read -p "Создать скрипт мониторинга безопасности? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        create_monitoring_script
    fi
    
    log "Настройка firewall завершена!"
    log ""
    log "Рекомендации по безопасности:"
    log "1. Регулярно проверяйте логи: /var/log/firewall-monitor.log"
    log "2. Мониторьте fail2ban статус: fail2ban-client status"
    log "3. Проверяйте активные соединения: netstat -tn"
    log "4. Обновляйте систему: apt update && apt upgrade"
    log ""
    log "Полезные команды:"
    case $FIREWALL in
        "ufw")
            log "  Статус: ufw status verbose"
            log "  Логи: tail -f /var/log/ufw.log"
            ;;
        "firewalld")
            log "  Статус: firewall-cmd --list-all"
            log "  Логи: journalctl -u firewalld -f"
            ;;
        "iptables")
            log "  Статус: iptables -L -n"
            log "  Логи: tail -f /var/log/syslog"
            ;;
    esac
}

# Запуск главной функции
main