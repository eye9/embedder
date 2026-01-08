# PowerShell скрипт для автоматического деплоя Batch Excel Processor с IIS
# Использование: .\deploy-iis.ps1 -Domain "your-domain.com" [-EnableSSL] [-CertificateThumbprint "thumbprint"]

param(
    [Parameter(Mandatory=$true, HelpMessage="Доменное имя для сайта")]
    [string]$Domain,
    
    [Parameter(Mandatory=$false, HelpMessage="Thumbprint SSL сертификата")]
    [string]$CertificateThumbprint,
    
    [Parameter(Mandatory=$false, HelpMessage="Включить SSL")]
    [switch]$EnableSSL,
    
    [Parameter(Mandatory=$false, HelpMessage="Пропустить проверки Docker")]
    [switch]$SkipDockerCheck,
    
    [Parameter(Mandatory=$false, HelpMessage="Режим разработки")]
    [switch]$Development
)

# Настройки
$ErrorActionPreference = "Stop"
$SiteName = "BatchProcessor"
$SitePath = "C:\inetpub\wwwroot\batchprocessor"
$LogPath = "C:\logs\batch-processor-deploy.log"

# Функции логирования
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage -ForegroundColor $(if($Level -eq "ERROR") {"Red"} elseif($Level -eq "WARN") {"Yellow"} else {"Green"})
    
    # Создание директории логов если не существует
    $logDir = Split-Path $LogPath -Parent
    if (!(Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    $logMessage | Out-File -FilePath $LogPath -Append -Encoding UTF8
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Prerequisites {
    Write-Log "Проверка предварительных требований..."
    
    # Проверка прав администратора
    if (!(Test-Administrator)) {
        throw "Скрипт должен быть запущен от имени администратора"
    }
    
    # Проверка IIS
    $iisFeature = Get-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole
    if ($iisFeature.State -ne "Enabled") {
        throw "IIS не установлен или не включен"
    }
    
    # Проверка URL Rewrite Module
    $rewriteModule = Get-Module -ListAvailable -Name WebAdministration
    if (!$rewriteModule) {
        throw "WebAdministration модуль не найден"
    }
    
    # Проверка Docker (если не пропускаем)
    if (!$SkipDockerCheck) {
        try {
            $dockerVersion = docker --version
            Write-Log "Docker найден: $dockerVersion"
        } catch {
            throw "Docker не установлен или недоступен"
        }
    }
    
    Write-Log "Все предварительные требования выполнены"
}

function Stop-DockerContainers {
    if ($SkipDockerCheck) {
        Write-Log "Пропуск остановки Docker контейнеров"
        return
    }
    
    Write-Log "Остановка существующих Docker контейнеров..."
    
    try {
        $composeFile = if ($Development) { "docker-compose.dev.yml" } else { "docker-compose.windows.yml" }
        
        if (Test-Path $composeFile) {
            docker-compose -f $composeFile down
            Write-Log "Docker контейнеры остановлены"
        } else {
            Write-Log "Файл $composeFile не найден, используем стандартный docker-compose.yml"
            docker-compose down
        }
    } catch {
        Write-Log "Ошибка при остановке контейнеров: $($_.Exception.Message)" "WARN"
    }
}

function Update-ApplicationCode {
    Write-Log "Обновление кода приложения..."
    
    try {
        # Проверка наличия git репозитория
        if (Test-Path ".git") {
            Write-Log "Получение последних изменений из git..."
            git pull origin main
        } else {
            Write-Log "Git репозиторий не найден, пропуск обновления кода" "WARN"
        }
    } catch {
        Write-Log "Ошибка при обновлении кода: $($_.Exception.Message)" "WARN"
    }
}

function Start-DockerContainers {
    if ($SkipDockerCheck) {
        Write-Log "Пропуск запуска Docker контейнеров"
        return
    }
    
    Write-Log "Сборка и запуск Docker контейнеров..."
    
    try {
        $composeFile = if ($Development) { 
            "docker-compose.yml -f docker-compose.dev.yml" 
        } else { 
            if (Test-Path "docker-compose.windows.yml") {
                "docker-compose.windows.yml"
            } else {
                "docker-compose.yml"
            }
        }
        
        Write-Log "Используется файл конфигурации: $composeFile"
        
        if ($Development) {
            docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
        } else {
            docker-compose -f $composeFile up -d --build
        }
        
        Write-Log "Docker контейнеры запущены"
    } catch {
        throw "Ошибка при запуске Docker контейнеров: $($_.Exception.Message)"
    }
}

function Wait-ForApplication {
    if ($SkipDockerCheck) {
        Write-Log "Пропуск ожидания готовности приложения"
        return
    }
    
    Write-Log "Ожидание готовности приложения..."
    
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        Start-Sleep -Seconds 5
        
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
            $ready = $response.StatusCode -eq 200
            
            if ($ready) {
                Write-Log "Приложение готово к работе"
                return
            }
        } catch {
            Write-Log "Попытка $attempt/$maxAttempts: приложение еще не готово..." "WARN"
        }
        
    } while ($attempt -lt $maxAttempts)
    
    throw "Приложение не готово после $maxAttempts попыток"
}

function Setup-IISSite {
    Write-Log "Настройка IIS сайта..."
    
    # Импорт модуля WebAdministration
    Import-Module WebAdministration -Force
    
    # Создание директории сайта
    if (!(Test-Path $SitePath)) {
        New-Item -ItemType Directory -Path $SitePath -Force | Out-Null
        Write-Log "Создана директория сайта: $SitePath"
    }
    
    # Удаление существующего сайта если есть
    if (Get-IISSite -Name $SiteName -ErrorAction SilentlyContinue) {
        Remove-IISSite -Name $SiteName -Confirm:$false
        Write-Log "Удален существующий сайт: $SiteName"
    }
    
    # Создание нового сайта
    New-IISSite -Name $SiteName -PhysicalPath $SitePath -Port 80 -Protocol http
    Write-Log "Создан IIS сайт: $SiteName"
    
    # Удаление дефолтной привязки
    Remove-IISSiteBinding -Name $SiteName -Protocol http -Port 80 -Confirm:$false
    
    # Добавление привязки с доменом
    New-IISSiteBinding -Name $SiteName -Protocol http -Port 80 -HostHeader $Domain
    Write-Log "Добавлена HTTP привязка для домена: $Domain"
    
    # Настройка SSL если требуется
    if ($EnableSSL) {
        if ([string]::IsNullOrEmpty($CertificateThumbprint)) {
            throw "Для SSL требуется указать CertificateThumbprint"
        }
        
        # Проверка существования сертификата
        $cert = Get-ChildItem -Path "Cert:\LocalMachine\My" | Where-Object { $_.Thumbprint -eq $CertificateThumbprint }
        if (!$cert) {
            throw "Сертификат с thumbprint $CertificateThumbprint не найден"
        }
        
        New-IISSiteBinding -Name $SiteName -Protocol https -Port 443 -HostHeader $Domain -CertificateThumbPrint $CertificateThumbprint -CertStoreLocation "Cert:\LocalMachine\My"
        Write-Log "Добавлена HTTPS привязка с сертификатом"
    }
}

function Setup-WebConfig {
    Write-Log "Настройка web.config..."
    
    $webConfigPath = Join-Path $SitePath "web.config"
    $sourceWebConfig = "iis\web.config"
    
    if (Test-Path $sourceWebConfig) {
        Copy-Item $sourceWebConfig $webConfigPath -Force
        Write-Log "Скопирован web.config из $sourceWebConfig"
    } else {
        # Создание базового web.config если исходный не найден
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
                        <set name="HTTP_X_FORWARDED_PROTO" value="{HTTPS}" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                        <set name="HTTP_X_ORIGINAL_HOST" value="{HTTP_HOST}" />
                    </serverVariables>
                </rule>
                <rule name="FlowerReverseProxy" stopProcessing="true">
                    <match url="^flower/(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:5555/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="{HTTPS}" />
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
    </system.webServer>
</configuration>
'@
        
        $webConfigContent | Out-File -FilePath $webConfigPath -Encoding UTF8
        Write-Log "Создан базовый web.config"
    }
    
    # Обновление web.config для SSL если включен
    if ($EnableSSL) {
        Write-Log "Обновление web.config для HTTPS..."
        
        $webConfig = [xml](Get-Content $webConfigPath)
        
        # Добавление правила редиректа HTTP -> HTTPS
        $httpsRedirectRule = $webConfig.CreateElement("rule")
        $httpsRedirectRule.SetAttribute("name", "Redirect to HTTPS")
        $httpsRedirectRule.SetAttribute("stopProcessing", "true")
        
        $match = $webConfig.CreateElement("match")
        $match.SetAttribute("url", ".*")
        $httpsRedirectRule.AppendChild($match)
        
        $conditions = $webConfig.CreateElement("conditions")
        $condition = $webConfig.CreateElement("add")
        $condition.SetAttribute("input", "{HTTPS}")
        $condition.SetAttribute("pattern", "off")
        $condition.SetAttribute("ignoreCase", "true")
        $conditions.AppendChild($condition)
        $httpsRedirectRule.AppendChild($conditions)
        
        $action = $webConfig.CreateElement("action")
        $action.SetAttribute("type", "Redirect")
        $action.SetAttribute("url", "https://{HTTP_HOST}/{R:0}")
        $action.SetAttribute("redirectType", "Permanent")
        $httpsRedirectRule.AppendChild($action)
        
        # Вставка правила в начало списка
        $rules = $webConfig.configuration.'system.webServer'.rewrite.rules
        $rules.InsertBefore($httpsRedirectRule, $rules.FirstChild)
        
        $webConfig.Save($webConfigPath)
        Write-Log "Добавлено правило редиректа HTTPS"
    }
}

function Enable-ARRProxy {
    Write-Log "Включение Application Request Routing proxy..."
    
    try {
        # Включение proxy на уровне сервера
        Set-WebConfigurationProperty -Filter "system.webServer/proxy" -Name "enabled" -Value $true -PSPath "IIS:\"
        Set-WebConfigurationProperty -Filter "system.webServer/proxy" -Name "preserveHostHeader" -Value $true -PSPath "IIS:\"
        Set-WebConfigurationProperty -Filter "system.webServer/proxy" -Name "reverseRewriteHostInResponseHeaders" -Value $false -PSPath "IIS:\"
        
        Write-Log "ARR proxy включен"
    } catch {
        Write-Log "Ошибка при включении ARR proxy: $($_.Exception.Message)" "WARN"
        Write-Log "Убедитесь, что Application Request Routing установлен"
    }
}

function Setup-FlowerAuthentication {
    Write-Log "Настройка аутентификации для Flower..."
    
    try {
        # Создание пользователя для Flower если не существует
        $flowerUser = "FlowerAdmin"
        $flowerPassword = "FlowerAdmin123!"
        
        try {
            Get-LocalUser -Name $flowerUser -ErrorAction Stop
            Write-Log "Пользователь $flowerUser уже существует"
        } catch {
            New-LocalUser -Name $flowerUser -Password (ConvertTo-SecureString $flowerPassword -AsPlainText -Force) -Description "Flower Monitoring User"
            Add-LocalGroupMember -Group "IIS_IUSRS" -Member $flowerUser
            Write-Log "Создан пользователь $flowerUser для Flower"
            Write-Log "Пароль для Flower: $flowerPassword" "WARN"
        }
        
    } catch {
        Write-Log "Ошибка при настройке аутентификации Flower: $($_.Exception.Message)" "WARN"
    }
}

function Test-Deployment {
    Write-Log "Тестирование деплоя..."
    
    # Проверка статуса IIS сайта
    $site = Get-IISSite -Name $SiteName
    if ($site.State -ne "Started") {
        Start-IISSite -Name $SiteName
        Write-Log "Запущен IIS сайт"
    }
    
    # Тестирование доступности
    $testUrls = @()
    
    if ($EnableSSL) {
        $testUrls += "https://$Domain/health"
        $testUrls += "https://$Domain/"
    } else {
        $testUrls += "http://$Domain/health"
        $testUrls += "http://$Domain/"
    }
    
    foreach ($url in $testUrls) {
        try {
            Write-Log "Тестирование URL: $url"
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 30 -UseBasicParsing
            
            if ($response.StatusCode -eq 200) {
                Write-Log "✅ $url - OK (HTTP $($response.StatusCode))"
            } else {
                Write-Log "⚠️ $url - HTTP $($response.StatusCode)" "WARN"
            }
        } catch {
            Write-Log "❌ $url - Ошибка: $($_.Exception.Message)" "ERROR"
        }
    }
}

function Show-DeploymentSummary {
    Write-Log "=== СВОДКА ДЕПЛОЯ ==="
    Write-Log "Сайт: $SiteName"
    Write-Log "Домен: $Domain"
    Write-Log "Путь: $SitePath"
    Write-Log "SSL: $(if($EnableSSL) {'Включен'} else {'Отключен'})"
    
    if ($EnableSSL) {
        Write-Log "🌐 Приложение доступно по адресу: https://$Domain"
        Write-Log "🔍 Flower мониторинг: https://$Domain/flower/"
    } else {
        Write-Log "🌐 Приложение доступно по адресу: http://$Domain"
        Write-Log "🔍 Flower мониторинг: http://$Domain/flower/"
    }
    
    Write-Log "📊 Статус IIS сайта: $((Get-IISSite -Name $SiteName).State)"
    
    if (!$SkipDockerCheck) {
        Write-Log "🐳 Docker контейнеры:"
        docker-compose ps --format "table {{.Name}}\t{{.Status}}" | ForEach-Object { Write-Log "   $_" }
    }
    
    Write-Log "📝 Логи деплоя: $LogPath"
    Write-Log "===================="
}

# Основная функция деплоя
function Start-Deployment {
    try {
        Write-Log "Начало деплоя Batch Excel Processor с IIS"
        Write-Log "Домен: $Domain"
        Write-Log "SSL: $(if($EnableSSL) {'Включен'} else {'Отключен'})"
        Write-Log "Режим: $(if($Development) {'Разработка'} else {'Продакшн'})"
        
        Test-Prerequisites
        Stop-DockerContainers
        Update-ApplicationCode
        Start-DockerContainers
        Wait-ForApplication
        Setup-IISSite
        Setup-WebConfig
        Enable-ARRProxy
        Setup-FlowerAuthentication
        Test-Deployment
        Show-DeploymentSummary
        
        Write-Log "✅ Деплой завершен успешно!"
        
    } catch {
        Write-Log "❌ Ошибка деплоя: $($_.Exception.Message)" "ERROR"
        Write-Log "Проверьте логи: $LogPath"
        exit 1
    }
}

# Запуск деплоя
Start-Deployment