# Решение проблемы Docker на Windows Server

## Проблема
```
no matching manifest for windows/amd64 10.0.17763 in the manifest list entries
```

Эта ошибка возникает когда Docker пытается использовать Windows-контейнеры для образов, которые доступны только для Linux.

## Решения

### Решение 1: Переключиться на Linux-контейнеры (Рекомендуется)

#### Через Docker Desktop GUI:
1. Правый клик на иконку Docker в системном трее
2. Выбрать "Switch to Linux containers"
3. Дождаться перезапуска Docker

#### Через PowerShell:
```powershell
# Переключить на Linux-контейнеры
& "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchLinuxEngine

# Проверить режим
docker info --format "{{.OSType}}"
```

#### Запуск с Linux-контейнерами:
```powershell
# Использовать обычный docker-compose.yml
.\deploy.ps1 production -ContainerMode linux
```

### Решение 2: Использовать Windows-контейнеры

#### Переключиться на Windows-контейнеры:
```powershell
# Переключить на Windows-контейнеры
& "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchWindowsEngine

# Проверить режим
docker info --format "{{.OSType}}"
```

#### Запуск с Windows-контейнерами:
```powershell
# Использовать специальный docker-compose.windows.yml
.\deploy.ps1 production -ContainerMode windows
```

### Решение 3: Автоматическое определение режима

```powershell
# Скрипт автоматически определит текущий режим Docker
.\deploy.ps1 production -ContainerMode auto
```

## Требования для Windows-контейнеров

### Windows Server 2019/2022:
```powershell
# Включить контейнеры Windows
Enable-WindowsOptionalFeature -Online -FeatureName containers -All

# Включить Hyper-V (если нужно)
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Перезагрузить сервер
Restart-Computer
```

### Установка Docker для Windows-контейнеров:
```powershell
# Установить Docker Engine
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/microsoft/Windows-Containers/Main/helpful_tools/Install-DockerCE/install-docker-ce.ps1" -o install-docker-ce.ps1
.\install-docker-ce.ps1

# Запустить службу
Start-Service docker
Set-Service -Name docker -StartupType Automatic
```

## Файлы для разных режимов

### Linux-контейнеры (по умолчанию):
- `Dockerfile` - обычный Linux Dockerfile
- `docker-compose.yml` - стандартный compose файл

### Windows-контейнеры:
- `Dockerfile.windows` - Windows-совместимый Dockerfile
- `docker-compose.windows.yml` - Windows compose файл

## Проверка и диагностика

### Проверить текущий режим Docker:
```powershell
docker info --format "{{.OSType}}"
```

### Проверить доступные образы:
```powershell
# Для Linux
docker pull python:3.11-slim

# Для Windows
docker pull mcr.microsoft.com/windows/servercore:ltsc2019
```

### Тестовый запуск:
```powershell
# Linux контейнер
docker run --rm python:3.11-slim python --version

# Windows контейнер
docker run --rm mcr.microsoft.com/windows/servercore:ltsc2019 cmd /c echo "Windows container works"
```

## Рекомендации

1. **Для продакшена**: Используйте Linux-контейнеры (более стабильные и быстрые)
2. **Для совместимости**: Если нужны Windows-специфичные функции, используйте Windows-контейнеры
3. **Для разработки**: Linux-контейнеры проще в использовании

## Команды развертывания

```powershell
# Linux-контейнеры (рекомендуется)
.\deploy.ps1 production -ContainerMode linux

# Windows-контейнеры
.\deploy.ps1 production -ContainerMode windows

# Автоопределение
.\deploy.ps1 production -ContainerMode auto

# Проверка состояния
.\deploy.ps1 status

# Проверка здоровья
.\deploy.ps1 health
```

## Устранение неполадок

### Если Docker не переключается:
1. Перезапустить Docker Desktop
2. Перезапустить службу Docker:
   ```powershell
   Restart-Service docker
   ```
3. Перезагрузить сервер

### Если образы не скачиваются:
1. Проверить интернет-соединение
2. Проверить настройки прокси Docker
3. Очистить кэш Docker:
   ```powershell
   docker system prune -a
   ```

### Логи для диагностики:
```powershell
# Логи Docker
Get-EventLog -LogName Application -Source Docker

# Логи контейнеров
docker-compose -f docker-compose.yml logs
docker-compose -f docker-compose.windows.yml logs
```