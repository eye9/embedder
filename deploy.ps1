# Production deployment script for Batch Excel Processor (Windows Server)
param(
    [Parameter(Position=0)]
    [ValidateSet("production", "staging", "development", "health", "status", "cleanup")]
    [string]$Environment = "production",
    
    [Parameter()]
    [ValidateSet("linux", "windows", "hybrid", "auto")]
    [string]$ContainerMode = "auto"
)

# Configuration
$ConfigFile = "batch_processor_config.$Environment.yaml"

# Determine container mode and compose file
if ($ContainerMode -eq "auto") {
    # Try to detect current Docker mode
    try {
        $dockerInfo = docker info --format "{{.OSType}}" 2>$null
        if ($dockerInfo -eq "windows") {
            $ContainerMode = "hybrid"  # Use hybrid mode for better compatibility
            $DockerComposeFile = "docker-compose.hybrid.yml"
        } else {
            $ContainerMode = "linux"
            $DockerComposeFile = "docker-compose.yml"
        }
    }
    catch {
        Write-Warning "Could not detect Docker mode, defaulting to hybrid mode"
        $ContainerMode = "hybrid"
        $DockerComposeFile = "docker-compose.hybrid.yml"
    }
} elseif ($ContainerMode -eq "windows") {
    $DockerComposeFile = "docker-compose.windows.yml"
} elseif ($ContainerMode -eq "hybrid") {
    $DockerComposeFile = "docker-compose.hybrid.yml"
} else {
    $DockerComposeFile = "docker-compose.yml"
}

# Colors for output (Windows PowerShell compatible)
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"

# Logging functions
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

# Check prerequisites
function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    Write-Log "Container mode: $ContainerMode"
    Write-Log "Docker Compose file: $DockerComposeFile"
    
    # Check Docker
    try {
        docker --version | Out-Null
    }
    catch {
        Write-Error "Docker is not installed or not in PATH"
    }
    
    # Check Docker mode
    try {
        $dockerInfo = docker info --format "{{.OSType}}" 2>$null
        Write-Log "Docker is running in $dockerInfo mode"
        
        if ($ContainerMode -eq "linux" -and $dockerInfo -eq "windows") {
            Write-Warning "Docker is in Windows mode but Linux containers requested."
            
            # Try different methods to switch to Linux containers
            $switched = $false
            
            # Method 1: DockerCli.exe (Docker Desktop)
            $dockerCliPath = "C:\Program Files\Docker\Docker\DockerCli.exe"
            if (Test-Path $dockerCliPath) {
                try {
                    & $dockerCliPath -SwitchLinuxEngine
                    Write-Log "Switched to Linux containers using DockerCli.exe. Please wait for Docker to restart..."
                    Start-Sleep -Seconds 30
                    $switched = $true
                }
                catch {
                    Write-Warning "Failed to switch using DockerCli.exe"
                }
            }
            
            # Method 2: Docker Desktop API (if available)
            if (-not $switched) {
                try {
                    $response = Invoke-RestMethod -Uri "http://localhost/engine/switch-daemon" -Method POST -Body '{"daemon":"linux"}' -ContentType "application/json" -TimeoutSec 5
                    Write-Log "Switched to Linux containers using API. Please wait for Docker to restart..."
                    Start-Sleep -Seconds 30
                    $switched = $true
                }
                catch {
                    Write-Warning "Failed to switch using Docker API"
                }
            }
            
            # Method 3: Manual instruction
            if (-not $switched) {
                Write-Error "Could not automatically switch to Linux containers. Please switch manually:
1. Right-click Docker icon in system tray
2. Select 'Switch to Linux containers'
3. Wait for Docker to restart
4. Run the script again"
            }
        }
        elseif ($ContainerMode -eq "windows" -and $dockerInfo -eq "linux") {
            Write-Warning "Docker is in Linux mode but Windows containers requested."
            
            # Try different methods to switch to Windows containers
            $switched = $false
            
            # Method 1: DockerCli.exe (Docker Desktop)
            $dockerCliPath = "C:\Program Files\Docker\Docker\DockerCli.exe"
            if (Test-Path $dockerCliPath) {
                try {
                    & $dockerCliPath -SwitchWindowsEngine
                    Write-Log "Switched to Windows containers using DockerCli.exe. Please wait for Docker to restart..."
                    Start-Sleep -Seconds 30
                    $switched = $true
                }
                catch {
                    Write-Warning "Failed to switch using DockerCli.exe"
                }
            }
            
            # Method 2: Docker Desktop API (if available)
            if (-not $switched) {
                try {
                    $response = Invoke-RestMethod -Uri "http://localhost/engine/switch-daemon" -Method POST -Body '{"daemon":"windows"}' -ContentType "application/json" -TimeoutSec 5
                    Write-Log "Switched to Windows containers using API. Please wait for Docker to restart..."
                    Start-Sleep -Seconds 30
                    $switched = $true
                }
                catch {
                    Write-Warning "Failed to switch using Docker API"
                }
            }
            
            # Method 3: Manual instruction
            if (-not $switched) {
                Write-Error "Could not automatically switch to Windows containers. Please switch manually:
1. Right-click Docker icon in system tray
2. Select 'Switch to Windows containers'
3. Wait for Docker to restart
4. Run the script again"
            }
        }
    }
    catch {
        Write-Warning "Could not determine Docker container mode"
    }
    
    # Check Docker Compose
    try {
        docker-compose --version | Out-Null
    }
    catch {
        Write-Error "Docker Compose is not installed or not in PATH"
    }
    
    # Check configuration file
    if (-not (Test-Path $ConfigFile)) {
        Write-Error "Configuration file not found: $ConfigFile"
    }
    
    # Check Docker Compose file
    if (-not (Test-Path $DockerComposeFile)) {
        Write-Error "Docker Compose file not found: $DockerComposeFile"
    }
    
    # Check environment variables for production
    if ($Environment -eq "production") {
        if (-not $env:ADMIN_PASSWORD) {
            Write-Error "ADMIN_PASSWORD environment variable must be set for production"
        }
        
        if (-not $env:SESSION_SECRET_KEY) {
            Write-Error "SESSION_SECRET_KEY environment variable must be set for production"
        }
        
        if (-not $env:REDIS_PASSWORD -and $Environment -eq "production") {
            Write-Warning "REDIS_PASSWORD not set - Redis will run without authentication"
        }
    }
    
    Write-Log "Prerequisites check passed"
}

# Backup existing data
function Backup-Data {
    if ($Environment -eq "production") {
        Write-Log "Creating backup of existing data..."
        
        $BackupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        
        # Backup temp files if they exist
        if (Test-Path "temp_files") {
            Copy-Item -Path "temp_files" -Destination $BackupDir -Recurse -Force
            Write-Log "Backed up temp files to $BackupDir"
        }
        
        # Backup logs if they exist
        if (Test-Path "logs") {
            Copy-Item -Path "logs" -Destination $BackupDir -Recurse -Force
            Write-Log "Backed up logs to $BackupDir"
        }
        
        # Backup Redis data if container exists
        try {
            $redisContainers = docker ps -a --format "{{.Names}}" | Where-Object { $_ -match "batch_processor_redis" }
            if ($redisContainers) {
                docker exec batch_processor_redis redis-cli BGSAVE
            }
        }
        catch {
            Write-Warning "Could not backup Redis data"
        }
    }
}

# Setup directories
function Initialize-Directories {
    Write-Log "Setting up directories..."
    
    $directories = @("temp_files", "logs", "chroma_db", "backups")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Log "Directories created successfully"
}

# Generate environment file
function New-EnvironmentFile {
    Write-Log "Generating environment file..."
    
    $EnvFile = ".env.$Environment"
    
    $envContent = @"
# Generated environment file for $Environment
BATCH_PROCESSOR_ENV=$Environment
BATCH_PROCESSOR_CONFIG=/app/$ConfigFile

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=$($env:REDIS_PASSWORD)

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Authentication
ADMIN_PASSWORD=$($env:ADMIN_PASSWORD -or "admin123")
OPERATOR_PASSWORD=$($env:OPERATOR_PASSWORD -or "operator123")
SESSION_SECRET_KEY=$($env:SESSION_SECRET_KEY -or "change-this-secret-key")

# Security
HTTPS_ONLY=$($env:HTTPS_ONLY -or "false")
SECURE_COOKIES=$($env:SECURE_COOKIES -or "false")
DOMAIN=$($env:DOMAIN -or "localhost")

# Performance
WEB_WORKERS=$($env:WEB_WORKERS -or "2")
CHUNK_SIZE=$($env:CHUNK_SIZE -or "500")
MAX_FILE_SIZE_MB=$($env:MAX_FILE_SIZE_MB -or "50")

# Monitoring
ENABLE_LLM=$($env:ENABLE_LLM -or "false")
ENABLE_ANALYTICS=$($env:ENABLE_ANALYTICS -or "false")
ENABLE_NOTIFICATIONS=$($env:ENABLE_NOTIFICATIONS -or "false")
"@

    $envContent | Out-File -FilePath $EnvFile -Encoding UTF8
    Write-Log "Environment file generated: $EnvFile"
}

# Build and deploy
function Start-Deployment {
    Write-Log "Starting deployment for environment: $Environment"
    
    # Stop existing containers
    Write-Log "Stopping existing containers..."
    try {
        docker-compose -f $DockerComposeFile down
    }
    catch {
        Write-Warning "No existing containers to stop"
    }
    
    # Build images
    Write-Log "Building Docker images..."
    docker-compose -f $DockerComposeFile build --no-cache
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed"
    }
    
    # Start services
    Write-Log "Starting services..."
    docker-compose -f $DockerComposeFile --env-file ".env.$Environment" up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start services"
    }
    
    # Wait for services to be ready
    Write-Log "Waiting for services to be ready..."
    Start-Sleep -Seconds 30
    
    # Health check
    Test-Health
}

# Health check
function Test-Health {
    Write-Log "Performing health check..."
    
    # Check web service
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Log "Web service is healthy"
        }
        else {
            Write-Error "Web service health check failed"
        }
    }
    catch {
        Write-Error "Web service health check failed: $($_.Exception.Message)"
    }
    
    # Check Redis
    try {
        $redisResult = docker exec batch_processor_redis redis-cli ping
        if ($redisResult -eq "PONG") {
            Write-Log "Redis is healthy"
        }
        else {
            Write-Error "Redis health check failed"
        }
    }
    catch {
        Write-Error "Redis health check failed: $($_.Exception.Message)"
    }
    
    # Check Celery worker
    try {
        docker exec batch_processor_worker celery -A batch_processor.workers.celery_app inspect ping | Out-Null
        Write-Log "Celery worker is healthy"
    }
    catch {
        Write-Warning "Celery worker health check failed"
    }
    
    Write-Log "Health check completed"
}

# Show status
function Show-Status {
    Write-Log "Deployment status:"
    docker-compose -f $DockerComposeFile ps
    
    Write-Log "Service URLs:"
    Write-Host "  Web Application: http://localhost:8000"
    Write-Host "  Flower (if enabled): http://localhost:5555"
    
    Write-Log "Logs can be viewed with:"
    Write-Host "  docker-compose -f $DockerComposeFile logs -f [service_name]"
}

# Cleanup old images
function Remove-OldImages {
    Write-Log "Cleaning up old Docker images..."
    docker image prune -f
    docker system prune -f
}

# Main deployment process
function Start-Main {
    Write-Log "Starting Batch Excel Processor deployment"
    Write-Log "Environment: $Environment"
    
    Test-Prerequisites
    Backup-Data
    Initialize-Directories
    New-EnvironmentFile
    Start-Deployment
    Show-Status
    
    if ($Environment -eq "production") {
        Remove-OldImages
    }
    
    Write-Log "Deployment completed successfully!"
    Write-Log "Access the application at: http://localhost:8000"
}

# Handle script arguments
switch ($Environment) {
    { $_ -in @("production", "staging", "development") } {
        Start-Main
    }
    "health" {
        Test-Health
    }
    "status" {
        Show-Status
    }
    "cleanup" {
        Remove-OldImages
    }
    default {
        Write-Host "Usage: .\deploy.ps1 {production|staging|development|health|status|cleanup} [-ContainerMode {linux|windows|auto}]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  production   - Deploy to production environment"
        Write-Host "  staging      - Deploy to staging environment"
        Write-Host "  development  - Deploy to development environment"
        Write-Host "  health       - Run health check on existing deployment"
        Write-Host "  status       - Show deployment status"
        Write-Host "  cleanup      - Clean up old Docker images"
        Write-Host ""
        Write-Host "Container Modes:"
        Write-Host "  -ContainerMode linux   - Use Linux containers (default)"
        Write-Host "  -ContainerMode windows - Use Windows containers"
        Write-Host "  -ContainerMode hybrid  - Use Linux containers (recommended for Windows)"
        Write-Host "  -ContainerMode auto    - Auto-detect current Docker mode"
        Write-Host ""
        Write-Host "Environment variables for production:"
        Write-Host "  ADMIN_PASSWORD     - Admin user password (required)"
        Write-Host "  SESSION_SECRET_KEY - Session secret key (required)"
        Write-Host "  REDIS_PASSWORD     - Redis password (optional)"
        Write-Host "  DOMAIN             - Application domain (optional)"
        Write-Host "  HTTPS_ONLY         - Enable HTTPS only mode (optional)"
        exit 1
    }
}