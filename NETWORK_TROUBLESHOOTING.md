# Решение проблем с сетью в Windows-контейнерах

## Проблема
```
Invoke-WebRequest : The remote name could not be resolved: 'www.python.org'
```

Эта ошибка возникает когда Windows-контейнер не может получить доступ к интернету.

## Причины проблемы

1. **Сетевые настройки Windows-контейнеров**
2. **Проблемы с DNS в контейнере**
3. **Ограничения корпоративного файрвола**
4. **Проблемы с NAT в Docker**

## Решения

### Решение 1: Использовать готовый Python образ (Рекомендуется)

Вместо установки Python в контейнере, используйте готовый образ:

```dockerfile
# Вместо установки Python вручную
FROM python:3.11-windowsservercore-ltsc2019

# Python уже установлен и настроен
```

### Решение 2: Переключиться на Linux-контейнеры

```powershell
# Переключить Docker на Linux-контейнеры
& "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchLinuxEngine

# Использовать обычный Dockerfile
.\deploy.ps1 production -ContainerMode linux
```

### Решение 3: Использовать гибридный режим

```powershell
# Использовать Linux-контейнеры на Windows (рекомендуется)
.\deploy.ps1 production -ContainerMode hybrid
```

### Решение 4: Настройка DNS для Windows-контейнеров

```powershell
# Остановить Docker
Stop-Service docker

# Настроить DNS для контейнеров
$dockerConfig = @"
{
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
"@

$dockerConfig | Out-File -FilePath "C:\ProgramData\docker\config\daemon.json" -Encoding UTF8

# Запустить Docker
Start-Service docker
```

### Решение 5: Настройка прокси (для корпоративных сетей)

```powershell
# Если используется корпоративный прокси
$dockerConfig = @"
{
  "proxies": {
    "default": {
      "httpProxy": "http://proxy.company.com:8080",
      "httpsProxy": "http://proxy.company.com:8080",
      "noProxy": "localhost,127.0.0.1"
    }
  },
  "dns": ["8.8.8.8", "8.8.4.4"]
}
"@

$dockerConfig | Out-File -FilePath "C:\ProgramData\docker\config\daemon.json" -Encoding UTF8
Restart-Service docker
```

## Диагностика проблем

### Проверить сетевое подключение в контейнере:

```powershell
# Запустить тестовый Windows-контейнер
docker run --rm -it mcr.microsoft.com/windows/servercore:ltsc2019 powershell

# В контейнере выполнить:
Test-NetConnection -ComputerName "www.python.org" -Port 443
nslookup www.python.org
Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing
```

### Проверить настройки Docker:

```powershell
# Проверить конфигурацию Docker
docker info

# Проверить сети Docker
docker network ls
docker network inspect bridge
```

### Проверить DNS настройки:

```powershell
# Проверить DNS на хосте
nslookup www.python.org
Test-NetConnection -ComputerName "8.8.8.8" -Port 53

# Проверить настройки сети Windows
Get-NetAdapter
Get-DnsClientServerAddress
```

## Альтернативные Dockerfile

### Dockerfile с предустановленным Python:
```dockerfile
FROM python:3.11-windowsservercore-ltsc2019
# Python уже установлен
```

### Dockerfile с локальной установкой Python:
```dockerfile
FROM mcr.microsoft.com/windows/servercore:ltsc2019

# Копировать Python установщик из локальной папки
COPY python-3.11.7-amd64.exe C:\temp\
RUN C:\temp\python-3.11.7-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
```

### Dockerfile с Chocolatey:
```dockerfile
FROM mcr.microsoft.com/windows/servercore:ltsc2019

# Установить Chocolatey и Python
RUN powershell -Command \
    Set-ExecutionPolicy Bypass -Scope Process -Force; \
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; \
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1')); \
    choco install python --version=3.11.7 -y
```

## Рекомендации

### Для продакшена:
1. **Используйте Linux-контейнеры** - более стабильные и быстрые
2. **Гибридный режим** - Linux-контейнеры на Windows хосте
3. **Готовые образы** - избегайте установки ПО в контейнере

### Для разработки:
1. **Docker Desktop с Linux-контейнерами**
2. **WSL2 backend** для лучшей производительности

### Команды для быстрого решения:

```powershell
# Быстрое решение - переключиться на Linux-контейнеры
& "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchLinuxEngine
.\deploy.ps1 production -ContainerMode linux

# Альтернатива - гибридный режим
.\deploy.ps1 production -ContainerMode hybrid

# Если нужны именно Windows-контейнеры
.\deploy.ps1 production -ContainerMode windows
```

## Файлы для разных сценариев

- `docker-compose.yml` - Linux-контейнеры (рекомендуется)
- `docker-compose.hybrid.yml` - Linux-контейнеры на Windows
- `docker-compose.windows.yml` - Windows-контейнеры
- `Dockerfile.windows` - Исправленный Windows Dockerfile
- `Dockerfile.windows.alt` - Альтернативная версия
- `Dockerfile.windows.nano` - Легковесная версия

## Мониторинг и логи

```powershell
# Логи Docker службы
Get-EventLog -LogName Application -Source Docker -Newest 10

# Логи контейнера
docker logs batch_processor_web

# Сетевая диагностика
docker exec batch_processor_web powershell -Command "Test-NetConnection -ComputerName google.com -Port 443"
```