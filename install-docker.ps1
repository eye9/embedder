# Автоматическая установка Docker на Windows Server
param(
    [Parameter()]
    [ValidateSet("Desktop", "Engine", "WSL2")]
    [string]$Type = "Desktop",
    
    [switch]$Force
)

# Проверка прав администратора
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Этот скрипт должен быть запущен от имени администратора"
    exit 1
}

# Функции логирования
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] WARNING: $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] ERROR: $Message" -ForegroundColor Red
    exit 1
}

# Проверка существующей установки Docker
function Test-DockerInstalled {
    try {
        docker --version | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Установка Docker Desktop
function Install-DockerDesktop {
    Write-Log "Установка Docker Desktop..."
    
    # Проверить существующую установку
    if ((Test-DockerInstalled) -and (-not $Force)) {
        Write-Warning "Docker уже установлен. Используйте -Force для переустановки."
        return
    }
    
    try {
        # Попробовать через winget
        Write-Log "Попытка установки через winget..."
        winget install Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker Desktop успешно установлен через winget"
            return
        }
    }
    catch {
        Write-Warning "Установка через winget не удалась, пробуем альтернативный метод..."
    }
    
    try {
        # Альтернативный метод - прямое скачивание
        Write-Log "Скачивание Docker Desktop..."
        $url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
        $installer = "$env:TEMP\DockerDesktopInstaller.exe"
        
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        
        Write-Log "Запуск установщика Docker Desktop..."
        Start-Process $installer -ArgumentList "install --quiet" -Wait
        
        # Удалить установщик
        Remove-Item $installer -Force
        
        Write-Log "Docker Desktop установлен успешно"
    }
    catch {
        Write-Error "Не удалось установить Docker Desktop: $($_.Exception.Message)"
    }
}

# Установка Docker Engine
function Install-DockerEngine {
    Write-Log "Установка Docker Engine..."
    
    # Включить контейнеры Windows
    Write-Log "Включение функции контейнеров Windows..."
    try {
        Enable-WindowsOptionalFeature -Online -FeatureName containers -All -NoRestart
    }
    catch {
        Write-Warning "Не удалось включить функцию контейнеров: $($_.Exception.Message)"
    }
    
    # Включить Hyper-V (если доступно)
    Write-Log "Включение Hyper-V..."
    try {
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All -NoRestart
    }
    catch {
        Write-Warning "Не удалось включить Hyper-V: $($_.Exception.Message)"
    }
    
    # Установить Docker Engine
    try {
        Write-Log "Скачивание и установка Docker Engine..."
        
        # Скачать скрипт установки Microsoft
        $installScript = "$env:TEMP\install-docker-ce.ps1"
        Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/microsoft/Windows-Containers/Main/helpful_tools/Install-DockerCE/install-docker-ce.ps1" -OutFile $installScript
        
        # Запустить установку
        & $installScript
        
        # Удалить скрипт
        Remove-Item $installScript -Force
        
        Write-Log "Docker Engine установлен успешно"
    }
    catch {
        Write-Error "Не удалось установить Docker Engine: $($_.Exception.Message)"
    }
    
    # Настроить службу Docker
    try {
        Write-Log "Настройка службы Docker..."
        Set-Service -Name docker -StartupType Automatic
        Start-Service docker
        Write-Log "Служба Docker настроена и запущена"
    }
    catch {
        Write-Warning "Не удалось настроить службу Docker: $($_.Exception.Message)"
    }
}

# Установка через WSL2
function Install-DockerWSL2 {
    Write-Log "Установка Docker через WSL2..."
    
    # Включить WSL
    Write-Log "Включение WSL..."
    try {
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    }
    catch {
        Write-Warning "Не удалось включить WSL: $($_.Exception.Message)"
    }
    
    # Установить WSL2
    try {
        Write-Log "Установка WSL2..."
        wsl --install --no-launch
        
        Write-Log "WSL2 установлен. После перезагрузки запустите:"
        Write-Host "wsl --install -d Ubuntu" -ForegroundColor Cyan
        Write-Host "Затем в Ubuntu выполните:" -ForegroundColor Cyan
        Write-Host "curl -fsSL https://get.docker.com -o get-docker.sh" -ForegroundColor Cyan
        Write-Host "sudo sh get-docker.sh" -ForegroundColor Cyan
    }
    catch {
        Write-Error "Не удалось установить WSL2: $($_.Exception.Message)"
    }
}

# Установка Docker Compose
function Install-DockerCompose {
    Write-Log "Установка Docker Compose..."
    
    try {
        # Проверить, установлен ли уже Docker Compose
        docker-compose --version | Out-Null
        Write-Log "Docker Compose уже установлен"
        return
    }
    catch {
        # Docker Compose не установлен, устанавливаем
    }
    
    try {
        # Скачать Docker Compose
        $composeVersion = "v2.24.5"
        $url = "https://github.com/docker/compose/releases/download/$composeVersion/docker-compose-windows-x86_64.exe"
        $composePath = "C:\Program Files\Docker\docker\docker-compose.exe"
        
        # Создать директорию если не существует
        $dockerDir = Split-Path $composePath -Parent
        if (-not (Test-Path $dockerDir)) {
            New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
        }
        
        Write-Log "Скачивание Docker Compose..."
        Invoke-WebRequest -Uri $url -OutFile $composePath -UseBasicParsing
        
        Write-Log "Docker Compose установлен успешно"
    }
    catch {
        Write-Warning "Не удалось установить Docker Compose: $($_.Exception.Message)"
    }
}

# Проверка установки
function Test-Installation {
    Write-Log "Проверка установки Docker..."
    
    try {
        $dockerVersion = docker --version
        Write-Log "Docker установлен: $dockerVersion"
        
        try {
            $composeVersion = docker-compose --version
            Write-Log "Docker Compose установлен: $composeVersion"
        }
        catch {
            try {
                $composeVersion = docker compose version
                Write-Log "Docker Compose установлен: $composeVersion"
            }
            catch {
                Write-Warning "Docker Compose не найден"
            }
        }
        
        # Тестовый запуск
        Write-Log "Тестирование Docker..."
        docker run --rm hello-world
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker работает корректно!"
        }
        else {
            Write-Warning "Docker установлен, но тест не прошел"
        }
    }
    catch {
        Write-Error "Docker не установлен или не работает: $($_.Exception.Message)"
    }
}

# Основная логика
Write-Log "Начало установки Docker (тип: $Type)"

switch ($Type) {
    "Desktop" {
        Install-DockerDesktop
        Install-DockerCompose
        Write-Log "Установка Docker Desktop завершена. Требуется перезагрузка системы."
        Write-Host "После перезагрузки запустите Docker Desktop из меню Пуск." -ForegroundColor Cyan
    }
    "Engine" {
        Install-DockerEngine
        Install-DockerCompose
        Write-Log "Установка Docker Engine завершена. Требуется перезагрузка системы."
    }
    "WSL2" {
        Install-DockerWSL2
        Write-Log "Установка WSL2 завершена. Требуется перезагрузка системы."
    }
}

# Проверка установки (только если не WSL2)
if ($Type -ne "WSL2") {
    Test-Installation
}

Write-Log "Установка завершена!"

# Показать следующие шаги
Write-Host "`nСледующие шаги:" -ForegroundColor Yellow
Write-Host "1. Перезагрузите систему: Restart-Computer" -ForegroundColor Cyan

if ($Type -eq "Desktop") {
    Write-Host "2. Запустите Docker Desktop из меню Пуск" -ForegroundColor Cyan
    Write-Host "3. Дождитесь полной загрузки Docker Desktop" -ForegroundColor Cyan
}
elseif ($Type -eq "Engine") {
    Write-Host "2. Проверьте службу Docker: Get-Service docker" -ForegroundColor Cyan
    Write-Host "3. Запустите службу: Start-Service docker" -ForegroundColor Cyan
}

Write-Host "4. Проверьте установку: docker --version" -ForegroundColor Cyan
Write-Host "5. Запустите развертывание: .\deploy.ps1 production" -ForegroundColor Cyan