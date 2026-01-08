# Настройка IIS как Reverse Proxy для Batch Excel Processor

## Обзор

Эта инструкция описывает настройку IIS (Internet Information Services) в качестве reverse proxy для Docker контейнеров Batch Excel Processor на Windows Server.

## Предварительные требования

### Системные требования
- Windows Server 2016/2019/2022
- IIS 10.0+
- Docker Desktop for Windows или Docker Engine
- PowerShell 5.1+

### Установка необходимых компонентов IIS

#### 1. Включение IIS и необходимых модулей
```powershell
# Запустите PowerShell от имени администратора

# Включение IIS
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole, IIS-WebServer, IIS-CommonHttpFeatures, IIS-HttpErrors, IIS-HttpLogging, IIS-RequestFiltering, IIS-StaticContent, IIS-DefaultDocument

# Включение дополнительных модулей
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HealthAndDiagnostics, IIS-HttpCompressionStatic, IIS-HttpCompressionDynamic, IIS-Security, IIS-RequestFiltering, IIS-IPSecurity

# Включение модулей для reverse proxy
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ASPNET45, IIS-NetFxExtensibility45, IIS-ISAPIExtensions, IIS-ISAPIFilter
```

#### 2. Установка Application Request Routing (ARR)
```powershell
# Скачайте и установите ARR 3.0 с официального сайта Microsoft
# https://www.iis.net/downloads/microsoft/application-request-routing

# Или используйте Web Platform Installer
# https://www.microsoft.com/web/downloads/platform.aspx
```

#### 3. Установка URL Rewrite Module
```powershell
# Скачайте и установите URL Rewrite Module 2.1
# https://www.iis.net/downloads/microsoft/url-rewrite

# Проверка установки
Get-WindowsFeature -Name IIS-HttpRedirect
```

## Настройка Docker контейнеров для Windows

### 1. Обновление docker-compose.yml для Windows
```yaml
# docker-compose.windows.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: batch_processor_redis
    ports:
      - "127.0.0.1:6379:6379"  # Только локальный доступ
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    networks:
      - batch_processor_network

  web:
    build:
      context: .
      target: production
    container_name: batch_processor_web
    ports:
      - "127.0.0.1:8000:8000"  # Только локальный доступ
    environment:
      - BATCH_PROCESSOR_CONFIG=/app/batch_processor_config.production.yaml
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./temp_files:/app/temp_files
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
      - ./batch_processor_config.production.yaml:/app/batch_processor_config.production.yaml
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - batch_processor_network

  worker:
    build:
      context: .
      target: production
    container_name: batch_processor_worker
    command: celery -A batch_processor.workers.celery_app worker --loglevel=info --queues=processing,default
    environment:
      - BATCH_PROCESSOR_CONFIG=/app/batch_processor_config.production.yaml
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./temp_files:/app/temp_files
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
      - ./batch_processor_config.production.yaml:/app/batch_processor_config.production.yaml
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - batch_processor_network

  cleanup_worker:
    build:
      context: .
      target: production
    container_name: batch_processor_cleanup_worker
    command: celery -A batch_processor.workers.celery_app worker --loglevel=info --queues=cleanup
    environment:
      - BATCH_PROCESSOR_CONFIG=/app/batch_processor_config.production.yaml
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./temp_files:/app/temp_files
      - ./logs:/app/logs
      - ./batch_processor_config.production.yaml:/app/batch_processor_config.production.yaml
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - batch_processor_network

  scheduler:
    build:
      context: .
      target: production
    container_name: batch_processor_scheduler
    command: celery -A batch_processor.workers.celery_app beat --loglevel=info
    environment:
      - BATCH_PROCESSOR_CONFIG=/app/batch_processor_config.production.yaml
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./logs:/app/logs
      - ./batch_processor_config.production.yaml:/app/batch_processor_config.production.yaml
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - batch_processor_network

  # Flower для мониторинга (опционально)
  flower:
    build:
      context: .
      target: production
    container_name: batch_processor_flower
    command: celery -A batch_processor.workers.celery_app flower --port=5555
    ports:
      - "127.0.0.1:5555:5555"  # Только локальный доступ
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - batch_processor_network
    profiles:
      - monitoring

volumes:
  redis_data:
    driver: local

networks:
  batch_processor_network:
    driver: bridge
```

### 2. Запуск контейнеров
```powershell
# Запуск контейнеров
docker-compose -f docker-compose.windows.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.windows.yml ps

# Проверка доступности приложения локально
curl http://localhost:8000/health
```

## Настройка IIS Reverse Proxy

### 1. Создание сайта в IIS

#### Через IIS Manager
1. Откройте IIS Manager
2. Правой кнопкой на "Sites" → "Add Website"
3. Заполните параметры:
   - Site name: `BatchProcessor`
   - Physical path: `C:\inetpub\wwwroot\batchprocessor` (создайте папку)
   - Binding: HTTP, Port 80, Host name: `your-domain.com`

#### Через PowerShell
```powershell
# Создание директории сайта
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\batchprocessor" -Force

# Создание сайта
New-IISSite -Name "BatchProcessor" -PhysicalPath "C:\inetpub\wwwroot\batchprocessor" -Port 80 -Protocol http

# Добавление привязки для домена
New-IISSiteBinding -Name "BatchProcessor" -Protocol http -Port 80 -HostHeader "your-domain.com"
```

### 2. Настройка URL Rewrite для Reverse Proxy

#### Создание web.config
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <!-- Включение reverse proxy -->
        <rewrite>
            <rules>
                <!-- Правило для основного приложения -->
                <rule name="ReverseProxyInboundRule1" stopProcessing="true">
                    <match url="^(?!flower/)(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="http" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                        <set name="HTTP_X_ORIGINAL_HOST" value="{HTTP_HOST}" />
                    </serverVariables>
                </rule>
                
                <!-- Правило для Flower мониторинга -->
                <rule name="FlowerReverseProxy" stopProcessing="true">
                    <match url="^flower/(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:5555/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="http" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                        <set name="HTTP_X_ORIGINAL_HOST" value="{HTTP_HOST}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        
        <!-- Настройки безопасности -->
        <security>
            <requestFiltering>
                <requestLimits maxAllowedContentLength="104857600" /> <!-- 100MB -->
            </requestFiltering>
        </security>
        
        <!-- Настройки сжатия -->
        <httpCompression>
            <dynamicTypes>
                <add mimeType="application/json" enabled="true" />
                <add mimeType="application/javascript" enabled="true" />
            </dynamicTypes>
        </httpCompression>
        
        <!-- Заголовки безопасности -->
        <httpProtocol>
            <customHeaders>
                <add name="X-Frame-Options" value="SAMEORIGIN" />
                <add name="X-Content-Type-Options" value="nosniff" />
                <add name="X-XSS-Protection" value="1; mode=block" />
                <add name="Referrer-Policy" value="strict-origin-when-cross-origin" />
            </customHeaders>
        </httpProtocol>
        
        <!-- Настройки таймаутов -->
        <system.web>
            <httpRuntime maxRequestLength="102400" executionTimeout="300" />
        </system.web>
    </system.webServer>
</configuration>
```

#### Размещение web.config
```powershell
# Создание web.config файла
$webConfigContent = @'
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="ReverseProxyInboundRule1" stopProcessing="true">
                    <match url="^(?!flower/)(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="http" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                        <set name="HTTP_X_ORIGINAL_HOST" value="{HTTP_HOST}" />
                    </serverVariables>
                </rule>
                <rule name="FlowerReverseProxy" stopProcessing="true">
                    <match url="^flower/(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:5555/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="http" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                        <set name="HTTP_X_ORIGINAL_HOST" value="{HTTP_HOST}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        <security>
            <requestFiltering>
                <requestLimits maxAllowedContentLength="104857600" />
            </requestFiltering>
        </security>
        <httpProtocol>
            <customHeaders>
                <add name="X-Frame-Options" value="SAMEORIGIN" />
                <add name="X-Content-Type-Options" value="nosniff" />
                <add name="X-XSS-Protection" value="1; mode=block" />
            </customHeaders>
        </httpProtocol>
    </system.webServer>
</configuration>
'@

# Сохранение файла
$webConfigContent | Out-File -FilePath "C:\inetpub\wwwroot\batchprocessor\web.config" -Encoding UTF8
```

### 3. Включение Server Variables в ARR

```powershell
# Включение server variables через PowerShell
Import-Module WebAdministration

# Разрешение server variables
Set-WebConfigurationProperty -Filter "system.webServer/rewrite/allowedServerVariables" -Name "." -Value @{name="HTTP_X_FORWARDED_PROTO"} -PSPath "IIS:\" -Location "BatchProcessor"
Set-WebConfigurationProperty -Filter "system.webServer/rewrite/allowedServerVariables" -Name "." -Value @{name="HTTP_X_FORWARDED_FOR"} -PSPath "IIS:\" -Location "BatchProcessor"
Set-WebConfigurationProperty -Filter "system.webServer/rewrite/allowedServerVariables" -Name "." -Value @{name="HTTP_X_ORIGINAL_HOST"} -PSPath "IIS:\" -Location "BatchProcessor"
```

### 4. Настройка Application Request Routing

#### Через IIS Manager
1. Откройте IIS Manager
2. Выберите сервер (корневой узел)
3. Откройте "Application Request Routing Cache"
4. В правой панели нажмите "Server Proxy Settings"
5. Установите флажок "Enable proxy"
6. Нажмите "Apply"

#### Через PowerShell
```powershell
# Включение proxy в ARR
Set-WebConfigurationProperty -Filter "system.webServer/proxy" -Name "enabled" -Value $true -PSPath "IIS:\"
Set-WebConfigurationProperty -Filter "system.webServer/proxy" -Name "preserveHostHeader" -Value $true -PSPath "IIS:\"
Set-WebConfigurationProperty -Filter "system.webServer/proxy" -Name "reverseRewriteHostInResponseHeaders" -Value $false -PSPath "IIS:\"
```

## Настройка HTTPS с SSL сертификатом

### 1. Получение SSL сертификата

#### Вариант A: Самоподписанный сертификат (для тестирования)
```powershell
# Создание самоподписанного сертификата
$cert = New-SelfSignedCertificate -DnsName "your-domain.com" -CertStoreLocation "cert:\LocalMachine\My"

# Привязка сертификата к сайту
New-IISSiteBinding -Name "BatchProcessor" -Protocol https -Port 443 -CertificateThumbPrint $cert.Thumbprint -CertStoreLocation "Cert:\LocalMachine\My"
```

#### Вариант B: Коммерческий сертификат
1. Получите сертификат от CA (Let's Encrypt, DigiCert, etc.)
2. Импортируйте сертификат в Windows Certificate Store
3. Привяжите к сайту через IIS Manager

### 2. Обновление web.config для HTTPS
```xml
<!-- Добавьте в web.config правило редиректа HTTP -> HTTPS -->
<rule name="Redirect to HTTPS" stopProcessing="true">
    <match url=".*" />
    <conditions>
        <add input="{HTTPS}" pattern="off" ignoreCase="true" />
    </conditions>
    <action type="Redirect" url="https://{HTTP_HOST}/{R:0}" redirectType="Permanent" />
</rule>
```

### 3. Обновление server variables для HTTPS
```xml
<serverVariables>
    <set name="HTTP_X_FORWARDED_PROTO" value="https" />
    <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
    <set name="HTTP_X_ORIGINAL_HOST" value="{HTTP_HOST}" />
</serverVariables>
```

## Настройка аутентификации для Flower

### 1. Создание пользователя для Flower
```powershell
# Создание пользователя Windows для аутентификации
net user FlowerAdmin "SecurePassword123!" /add
net localgroup "IIS_IUSRS" FlowerAdmin /add
```

### 2. Настройка Basic Authentication для Flower
```xml
<!-- Добавьте в web.config для пути /flower/ -->
<location path="flower">
    <system.webServer>
        <security>
            <authentication>
                <basicAuthentication enabled="true" />
                <anonymousAuthentication enabled="false" />
            </authentication>
            <authorization>
                <add accessType="Allow" users="FlowerAdmin" />
                <add accessType="Deny" users="*" />
            </authorization>
        </security>
    </system.webServer>
</location>
```

## Мониторинг и логирование

### 1. Настройка логирования IIS
```powershell
# Включение расширенного логирования
Set-WebConfigurationProperty -Filter "system.applicationHost/sites/site[@name='BatchProcessor']/logFile" -Name "logExtFileFlags" -Value "Date,Time,ClientIP,UserName,SiteName,ComputerName,ServerIP,Method,UriStem,UriQuery,HttpStatus,Win32Status,BytesSent,BytesRecv,TimeTaken,ServerPort,UserAgent,Cookie,Referer,ProtocolVersion,Host,HttpSubStatus"

# Настройка ротации логов
Set-WebConfigurationProperty -Filter "system.applicationHost/sites/site[@name='BatchProcessor']/logFile" -Name "period" -Value "Daily"
Set-WebConfigurationProperty -Filter "system.applicationHost/sites/site[@name='BatchProcessor']/logFile" -Name "truncateSize" -Value "1048576"
```

### 2. Создание скрипта мониторинга
```powershell
# Создание скрипта мониторинга IIS и Docker
$monitoringScript = @'
# Скрипт мониторинга Batch Processor на IIS
$logFile = "C:\logs\batch-processor-monitor.log"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log {
    param($message)
    "[$date] $message" | Out-File -FilePath $logFile -Append
}

# Проверка статуса IIS сайта
$site = Get-IISSite -Name "BatchProcessor"
if ($site.State -ne "Started") {
    Write-Log "WARNING: IIS site BatchProcessor is not running"
    Start-IISSite -Name "BatchProcessor"
}

# Проверка Docker контейнеров
$containers = docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "batch_processor"
if ($containers.Count -lt 4) {
    Write-Log "WARNING: Not all Docker containers are running"
}

# Проверка доступности приложения
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10
    if ($response.StatusCode -ne 200) {
        Write-Log "ERROR: Application health check failed"
    }
} catch {
    Write-Log "ERROR: Cannot connect to application: $($_.Exception.Message)"
}

# Проверка использования диска
$disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeSpacePercent = ($disk.FreeSpace / $disk.Size) * 100
if ($freeSpacePercent -lt 10) {
    Write-Log "WARNING: Low disk space: $([math]::Round($freeSpacePercent, 2))% free"
}

Write-Log "Monitoring check completed"
'@

# Сохранение скрипта
$monitoringScript | Out-File -FilePath "C:\scripts\monitor-batch-processor.ps1" -Encoding UTF8

# Создание задачи в Task Scheduler
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\scripts\monitor-batch-processor.ps1"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "BatchProcessorMonitoring" -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM"
```

## Настройка Windows Firewall

### 1. Открытие необходимых портов
```powershell
# Разрешение HTTP и HTTPS трафика
New-NetFirewallRule -DisplayName "HTTP Inbound" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "HTTPS Inbound" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow

# Блокировка прямого доступа к Docker портам (безопасность)
New-NetFirewallRule -DisplayName "Block Docker Direct Access" -Direction Inbound -Protocol TCP -LocalPort 8000,5555 -Action Block -RemoteAddress Any
```

### 2. Настройка IP Security (опционально)
```powershell
# Ограничение доступа по IP (если нужно)
# Замените на ваши разрешенные IP адреса
$allowedIPs = @("192.168.1.0/24", "203.0.113.0/24")

foreach ($ip in $allowedIPs) {
    New-NetFirewallRule -DisplayName "Allow HTTP from $ip" -Direction Inbound -Protocol TCP -LocalPort 80 -RemoteAddress $ip -Action Allow
    New-NetFirewallRule -DisplayName "Allow HTTPS from $ip" -Direction Inbound -Protocol TCP -LocalPort 443 -RemoteAddress $ip -Action Allow
}

# Блокировка всех остальных
New-NetFirewallRule -DisplayName "Block HTTP from others" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Block -Priority 1000
New-NetFirewallRule -DisplayName "Block HTTPS from others" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Block -Priority 1000
```

## Автоматизация деплоя

### 1. Создание PowerShell скрипта деплоя
```powershell
# deploy-iis.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    
    [Parameter(Mandatory=$false)]
    [string]$CertificateThumbprint,
    
    [Parameter(Mandatory=$false)]
    [switch]$EnableSSL
)

$ErrorActionPreference = "Stop"

Write-Host "Deploying Batch Excel Processor with IIS..." -ForegroundColor Green

# 1. Остановка Docker контейнеров
Write-Host "Stopping existing Docker containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.windows.yml down

# 2. Обновление кода
Write-Host "Updating application code..." -ForegroundColor Yellow
git pull origin main

# 3. Пересборка и запуск контейнеров
Write-Host "Building and starting Docker containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.windows.yml up -d --build

# 4. Ожидание готовности приложения
Write-Host "Waiting for application to be ready..." -ForegroundColor Yellow
do {
    Start-Sleep -Seconds 5
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
        $ready = $response.StatusCode -eq 200
    } catch {
        $ready = $false
    }
} while (-not $ready)

# 5. Обновление IIS конфигурации
Write-Host "Updating IIS configuration..." -ForegroundColor Yellow

# Обновление привязки домена
if (Get-IISSiteBinding -Name "BatchProcessor" -Protocol http -Port 80) {
    Remove-IISSiteBinding -Name "BatchProcessor" -Protocol http -Port 80 -Confirm:$false
}
New-IISSiteBinding -Name "BatchProcessor" -Protocol http -Port 80 -HostHeader $Domain

# Настройка SSL если требуется
if ($EnableSSL -and $CertificateThumbprint) {
    if (Get-IISSiteBinding -Name "BatchProcessor" -Protocol https -Port 443) {
        Remove-IISSiteBinding -Name "BatchProcessor" -Protocol https -Port 443 -Confirm:$false
    }
    New-IISSiteBinding -Name "BatchProcessor" -Protocol https -Port 443 -HostHeader $Domain -CertificateThumbPrint $CertificateThumbprint -CertStoreLocation "Cert:\LocalMachine\My"
}

# 6. Перезапуск IIS сайта
Write-Host "Restarting IIS site..." -ForegroundColor Yellow
Stop-IISSite -Name "BatchProcessor" -Confirm:$false
Start-IISSite -Name "BatchProcessor"

# 7. Проверка доступности
Write-Host "Testing deployment..." -ForegroundColor Yellow
$testUrl = if ($EnableSSL) { "https://$Domain/health" } else { "http://$Domain/health" }

try {
    $response = Invoke-WebRequest -Uri $testUrl -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Deployment successful!" -ForegroundColor Green
        Write-Host "🌐 Application available at: $testUrl" -ForegroundColor Green
    } else {
        Write-Host "❌ Deployment failed - HTTP $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
}
```

### 2. Использование скрипта деплоя
```powershell
# Деплой без SSL
.\deploy-iis.ps1 -Domain "batch-processor.yourdomain.com"

# Деплой с SSL
.\deploy-iis.ps1 -Domain "batch-processor.yourdomain.com" -EnableSSL -CertificateThumbprint "YOUR_CERT_THUMBPRINT"
```

## Проверка и тестирование

### 1. Проверка конфигурации
```powershell
# Проверка статуса IIS сайта
Get-IISSite -Name "BatchProcessor"

# Проверка привязок
Get-IISSiteBinding -Name "BatchProcessor"

# Проверка Docker контейнеров
docker-compose -f docker-compose.windows.yml ps

# Проверка доступности приложения
Invoke-WebRequest -Uri "http://localhost:8000/health"
Invoke-WebRequest -Uri "http://your-domain.com/health"
```

### 2. Тестирование функциональности
```powershell
# Тест загрузки файла через веб-интерфейс
# Откройте браузер и перейдите на http://your-domain.com

# Тест API
$headers = @{ "Content-Type" = "application/json" }
$body = @{ "test" = "data" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://your-domain.com/api/health" -Method GET -Headers $headers
```

## Резюме настройки IIS

**Основные шаги:**
1. Установите IIS с необходимыми модулями
2. Установите ARR и URL Rewrite
3. Настройте Docker контейнеры для локального доступа
4. Создайте IIS сайт с reverse proxy правилами
5. Настройте SSL сертификат (для продакшн)
6. Настройте мониторинг и логирование

**Преимущества использования IIS:**
- Интеграция с Windows Server
- Централизованное управление SSL сертификатами
- Встроенные возможности балансировки нагрузки
- Интеграция с Windows Authentication
- Профессиональные инструменты мониторинга

**Важные моменты:**
- Docker контейнеры должны слушать только localhost (127.0.0.1)
- IIS выступает как единственная точка входа
- Все настройки безопасности применяются на уровне IIS
- Регулярно обновляйте SSL сертификаты