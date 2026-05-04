@echo off
REM Production deployment script for Batch Excel Processor (Windows Server)
setlocal enabledelayedexpansion

REM Configuration
set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=production
set CONFIG_FILE=batch_processor_config.%ENVIRONMENT%.yaml
set DOCKER_COMPOSE_FILE=docker-compose.yml

REM Logging functions
:log
echo [%date% %time%] %~1
goto :eof

:warn
echo [%date% %time%] WARNING: %~1
goto :eof

:error
echo [%date% %time%] ERROR: %~1
exit /b 1

REM Check prerequisites
:check_prerequisites
call :log "Checking prerequisites..."

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    call :error "Docker is not installed or not in PATH"
)

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :error "Docker Compose is not installed or not in PATH"
)

REM Check configuration file
if not exist "%CONFIG_FILE%" (
    call :error "Configuration file not found: %CONFIG_FILE%"
)

REM Check environment variables for production
if "%ENVIRONMENT%"=="production" (
    if "%ADMIN_PASSWORD%"=="" (
        call :error "ADMIN_PASSWORD environment variable must be set for production"
    )
    
    if "%SESSION_SECRET_KEY%"=="" (
        call :error "SESSION_SECRET_KEY environment variable must be set for production"
    )
    
    if "%REDIS_PASSWORD%"=="" if "%ENVIRONMENT%"=="production" (
        call :warn "REDIS_PASSWORD not set - Redis will run without authentication"
    )
)

call :log "Prerequisites check passed"
goto :eof

REM Backup existing data
:backup_data
if "%ENVIRONMENT%"=="production" (
    call :log "Creating backup of existing data..."
    
    for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set mydate=%%c%%a%%b
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a%%b
    set BACKUP_DIR=backups\%mydate%_%mytime%
    
    if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"
    
    REM Backup temp files if they exist
    if exist "temp_files" (
        xcopy /E /I "temp_files" "!BACKUP_DIR!\temp_files" >nul
        call :log "Backed up temp files to !BACKUP_DIR!"
    )
    
    REM Backup logs if they exist
    if exist "logs" (
        xcopy /E /I "logs" "!BACKUP_DIR!\logs" >nul
        call :log "Backed up logs to !BACKUP_DIR!"
    )
    
    REM Backup Redis data if container exists
    docker ps -a --format "{{.Names}}" | findstr "batch_processor_redis" >nul
    if not errorlevel 1 (
        docker exec batch_processor_redis redis-cli BGSAVE >nul 2>&1 || call :warn "Could not backup Redis data"
    )
)
goto :eof

REM Setup directories
:setup_directories
call :log "Setting up directories..."

if not exist "temp_files" mkdir "temp_files"
if not exist "logs" mkdir "logs"
if not exist "chroma_db" mkdir "chroma_db"
if not exist "backups" mkdir "backups"

call :log "Directories created successfully"
goto :eof

REM Generate environment file
:generate_env_file
call :log "Generating environment file..."

set ENV_FILE=.env.%ENVIRONMENT%

(
echo # Generated environment file for %ENVIRONMENT%
echo BATCH_PROCESSOR_ENV=%ENVIRONMENT%
echo BATCH_PROCESSOR_CONFIG=/app/%CONFIG_FILE%
echo.
echo # Redis Configuration
echo REDIS_HOST=redis
echo REDIS_PORT=6379
echo REDIS_DB=0
echo REDIS_PASSWORD=%REDIS_PASSWORD%
echo.
echo # Celery Configuration
echo CELERY_BROKER_URL=redis://redis:6379/0
echo CELERY_RESULT_BACKEND=redis://redis:6379/0
echo.
echo # Authentication
if "%ADMIN_PASSWORD%"=="" (
    echo ADMIN_PASSWORD=admin123
) else (
    echo ADMIN_PASSWORD=%ADMIN_PASSWORD%
)
if "%OPERATOR_PASSWORD%"=="" (
    echo OPERATOR_PASSWORD=operator123
) else (
    echo OPERATOR_PASSWORD=%OPERATOR_PASSWORD%
)
if "%SESSION_SECRET_KEY%"=="" (
    echo SESSION_SECRET_KEY=change-this-secret-key
) else (
    echo SESSION_SECRET_KEY=%SESSION_SECRET_KEY%
)
echo.
echo # Security
if "%HTTPS_ONLY%"=="" (
    echo HTTPS_ONLY=false
) else (
    echo HTTPS_ONLY=%HTTPS_ONLY%
)
if "%SECURE_COOKIES%"=="" (
    echo SECURE_COOKIES=false
) else (
    echo SECURE_COOKIES=%SECURE_COOKIES%
)
if "%DOMAIN%"=="" (
    echo DOMAIN=localhost
) else (
    echo DOMAIN=%DOMAIN%
)
echo.
echo # Performance
if "%WEB_WORKERS%"=="" (
    echo WEB_WORKERS=2
) else (
    echo WEB_WORKERS=%WEB_WORKERS%
)
if "%CHUNK_SIZE%"=="" (
    echo CHUNK_SIZE=500
) else (
    echo CHUNK_SIZE=%CHUNK_SIZE%
)
if "%MAX_FILE_SIZE_MB%"=="" (
    echo MAX_FILE_SIZE_MB=50
) else (
    echo MAX_FILE_SIZE_MB=%MAX_FILE_SIZE_MB%
)
echo.
echo # Monitoring
if "%ENABLE_LLM%"=="" (
    echo ENABLE_LLM=false
) else (
    echo ENABLE_LLM=%ENABLE_LLM%
)
if "%ENABLE_ANALYTICS%"=="" (
    echo ENABLE_ANALYTICS=false
) else (
    echo ENABLE_ANALYTICS=%ENABLE_ANALYTICS%
)
if "%ENABLE_NOTIFICATIONS%"=="" (
    echo ENABLE_NOTIFICATIONS=false
) else (
    echo ENABLE_NOTIFICATIONS=%ENABLE_NOTIFICATIONS%
)
) > "%ENV_FILE%"

call :log "Environment file generated: %ENV_FILE%"
goto :eof

REM Build and deploy
:deploy
call :log "Starting deployment for environment: %ENVIRONMENT%"

REM Stop existing containers
call :log "Stopping existing containers..."
docker-compose down 2>nul || call :warn "No existing containers to stop"

REM Build images
call :log "Building Docker images..."
docker-compose build --no-cache
if errorlevel 1 (
    call :error "Docker build failed"
)

REM Start services
call :log "Starting services..."
docker-compose --env-file ".env.%ENVIRONMENT%" up -d
if errorlevel 1 (
    call :error "Failed to start services"
)

REM Wait for services to be ready
call :log "Waiting for services to be ready..."
timeout /t 30 /nobreak >nul

REM Health check
call :health_check
goto :eof

REM Health check
:health_check
call :log "Performing health check..."

REM Check web service
curl -f http://localhost:8000/health >nul 2>&1
if not errorlevel 1 (
    call :log "Web service is healthy"
) else (
    call :error "Web service health check failed"
)

REM Check Redis
docker exec batch_processor_redis redis-cli ping >nul 2>&1
if not errorlevel 1 (
    call :log "Redis is healthy"
) else (
    call :error "Redis health check failed"
)

REM Check Celery worker
docker exec batch_processor_worker celery -A batch_processor.workers.celery_app inspect ping >nul 2>&1
if not errorlevel 1 (
    call :log "Celery worker is healthy"
) else (
    call :warn "Celery worker health check failed"
)

call :log "Health check completed"
goto :eof

REM Show status
:show_status
call :log "Deployment status:"
docker-compose ps

call :log "Service URLs:"
echo   Web Application: http://localhost:8000
echo   Flower (if enabled): http://localhost:5555

call :log "Logs can be viewed with:"
echo   docker-compose logs -f [service_name]
goto :eof

REM Cleanup old images
:cleanup
call :log "Cleaning up old Docker images..."
docker image prune -f
docker system prune -f
goto :eof

REM Main deployment process
:main
call :log "Starting Batch Excel Processor deployment"
call :log "Environment: %ENVIRONMENT%"

call :check_prerequisites
call :backup_data
call :setup_directories
call :generate_env_file
call :deploy
call :show_status

if "%ENVIRONMENT%"=="production" (
    call :cleanup
)

call :log "Deployment completed successfully!"
call :log "Access the application at: http://localhost:8000"
goto :eof

REM Handle script arguments
if "%1"=="production" goto main
if "%1"=="staging" goto main
if "%1"=="development" goto main
if "%1"=="health" goto health_check
if "%1"=="status" goto show_status
if "%1"=="cleanup" goto cleanup
if "%1"=="" goto main

REM Show usage
echo Usage: %0 {production^|staging^|development^|health^|status^|cleanup}
echo.
echo Commands:
echo   production   - Deploy to production environment
echo   staging      - Deploy to staging environment
echo   development  - Deploy to development environment
echo   health       - Run health check on existing deployment
echo   status       - Show deployment status
echo   cleanup      - Clean up old Docker images
echo.
echo Environment variables for production:
echo   ADMIN_PASSWORD     - Admin user password (required)
echo   SESSION_SECRET_KEY - Session secret key (required)
echo   REDIS_PASSWORD     - Redis password (optional)
echo   DOMAIN             - Application domain (optional)
echo   HTTPS_ONLY         - Enable HTTPS only mode (optional)
exit /b 1