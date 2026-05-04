# Полное руководство по установке Docker на Windows Server

## Вариант 1: Docker Desktop (Рекомендуется для разработки)

### Системные требования:
- Windows 10/11 или Windows Server 2019/2022
- WSL 2 (для Linux-контейнеров)
- Hyper-V (для Windows-контейнеров)

### Установка через официальный сайт:
```powershell
# Скачать с https://www.docker.com/products/docker-desktop/
# Или автоматически:
$url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
Invoke-WebRequest -Uri $url -OutFile "DockerDesktopInstaller.exe"

# Установить
Start-Process "DockerDesktopInstaller.exe" -ArgumentList "install --quiet" -Wait

# Перезагрузить систему
Restart-Computer
```

### Установка через Chocolatey:
```powershell
# Установить Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Установить Docker Desktop
choco install docker-desktop -y

# Перезагрузить систему
Restart-Computer
```

### Установка через winget:
```powershell
# Установить Docker Desktop
winget install Docker.DockerDesktop

# Перезагрузить систему
Restart-Computer
```

## Вариант 2: Docker Engine (Для серверов без GUI)

### Подготовка системы:
```powershell
# Включить контейнеры Windows
Enable-WindowsOptionalFeature -Online -FeatureName containers -All

# Включить Hyper-V (если нужны Windows-контейнеры)
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Перезагрузить систему
Restart-Computer
```

### Установка Docker Engine:
```powershell
# Метод 1: Через скрипт Microsoft
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/microsoft/Windows-Containers/Main/helpful_tools/Install-DockerCE/install-docker-ce.ps1" -o install-docker-ce.ps1
.\install-docker-ce.ps1

# Метод 2: Ручная установка
$dockerVersion = "24.0.7"
$url = "https://download.docker.com/win/static/stable/x86_64/docker-$dockerVersion.zip"

# Скачать Docker
Invoke-WebRequest -Uri $url -OutFile "docker.zip"

# Создать директорию и распаковать
New-Item -ItemType Directory -Path "C:\Program Files\Docker" -Force
Expand-Archive -Path "docker.zip" -DestinationPath "C:\Program Files\Docker" -Force

# Добавить в PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", [EnvironmentVariableTarget]::Machine)
if ($currentPath -notlike "*C:\Program Files\Docker\docker*") {
    $newPath = $currentPath + ";C:\Program Files\Docker\docker"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, [EnvironmentVariableTarget]::Machine)
}

# Обновить PATH в текущей сессии
$env:PATH += ";C:\Program Files\Docker\docker"

# Зарегистрировать службу Docker
& "C:\Program Files\Docker\docker\dockerd.exe" --register-service

# Запустить службу
Start-Service docker
Set-Service -Name docker -StartupType Automatic
```

## Вариант 3: Docker через WSL2 (Для Linux-контейнеров)

### Установка WSL2:
```powershell
# Включить WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Включить виртуализацию
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Перезагрузить систему
Restart-Computer

# После перезагрузки - установить WSL2
wsl --install

# Установить Ubuntu
wsl --install -d Ubuntu

# Установить Docker в WSL2
wsl -d Ubuntu -e bash -c "
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker \$USER
sudo service docker start
"
```

## Установка Docker Compose

### Если установлен Docker Desktop:
Docker Compose уже включен в Docker Desktop.

### Для Docker Engine:
```powershell
# Метод 1: Скачать бинарный файл
$composeVersion = "v2.24.5"
$url = "https://github.com/docker/compose/releases/download/$composeVersion/docker-compose-windows-x86_64.exe"
Invoke-WebRequest -Uri $url -OutFile "C:\Program Files\Docker\docker\docker-compose.exe"

# Метод 2: Через pip (если установлен Python)
pip install docker-compose

# Метод 3: Через Chocolatey
choco install docker-compose -y
```

## Проверка установки

```powershell
# Проверить Docker
docker --version
docker info

# Проверить Docker Compose
docker-compose --version
# или новый синтаксис
docker compose version

# Тестовый запуск
docker run hello-world
```

## Настройка после установки

### Настройка службы Docker:
```powershell
# Автозапуск службы
Set-Service -Name docker -StartupType Automatic

# Запустить службу
Start-Service docker

# Проверить статус
Get-Service docker
```

### Добавление пользователя в группу docker-users:
```powershell
# Добавить текущего пользователя
Add-LocalGroupMember -Group "docker-users" -Member $env:USERNAME

# Или конкретного пользователя
Add-LocalGroupMember -Group "docker-users" -Member "ИмяПользователя"
```

### Настройка Docker для работы без sudo (WSL2):
```bash
# В WSL2
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
```

## Переключение между режимами контейнеров

### Через Docker Desktop GUI:
1. Правый клик на иконку Docker в системном трее
2. Выбрать "Switch to Linux containers" или "Switch to Windows containers"

### Через PowerShell (если есть DockerCli.exe):
```powershell
# Переключить на Linux-контейнеры
& "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchLinuxEngine

# Переключить на Windows-контейнеры
& "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchWindowsEngine
```

### Проверить текущий режим:
```powershell
docker info --format "{{.OSType}}"
```

## Устранение неполадок

### Если Docker не запускается:
```powershell
# Перезапустить службу
Restart-Service docker

# Проверить логи
Get-EventLog -LogName Application -Source Docker -Newest 10

# Проверить статус Hyper-V
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V
```

### Если не хватает прав:
```powershell
# Запустить PowerShell от имени администратора
Start-Process powershell -Verb RunAs

# Добавить пользователя в группу docker-users
Add-LocalGroupMember -Group "docker-users" -Member $env:USERNAME
```

### Очистка Docker:
```powershell
# Остановить все контейнеры
docker stop $(docker ps -aq)

# Удалить все контейнеры
docker rm $(docker ps -aq)

# Очистить систему
docker system prune -a --volumes
```

## Рекомендации по выбору

### Для разработки:
- **Docker Desktop** - полнофункциональное решение с GUI

### Для продакшн серверов:
- **Docker Engine** - минимальная установка без GUI
- **WSL2 + Docker** - для Linux-контейнеров на Windows

### Для гибридных сред:
- **Docker Desktop** с возможностью переключения между Linux и Windows контейнерами

## Автоматическая установка (скрипт)

```powershell
# Полный скрипт установки Docker Desktop
param(
    [switch]$Desktop,
    [switch]$Engine,
    [switch]$WSL2
)

if ($Desktop) {
    # Установка Docker Desktop
    winget install Docker.DockerDesktop
    Write-Host "Docker Desktop установлен. Требуется перезагрузка."
}
elseif ($Engine) {
    # Установка Docker Engine
    Enable-WindowsOptionalFeature -Online -FeatureName containers -All
    Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/microsoft/Windows-Containers/Main/helpful_tools/Install-DockerCE/install-docker-ce.ps1" -o install-docker-ce.ps1
    .\install-docker-ce.ps1
}
elseif ($WSL2) {
    # Установка через WSL2
    wsl --install
    Write-Host "WSL2 установлен. Требуется перезагрузка."
}
else {
    Write-Host "Использование: .\scripts\deployment\install-docker.ps1 -Desktop|-Engine|-WSL2"
}
```

Сохраните этот скрипт как `scripts\deployment\install-docker.ps1` и запустите с нужным параметром.
