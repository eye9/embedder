#!/bin/bash

# Production deployment script for Batch Excel Processor
set -e

# Configuration
ENVIRONMENT=${1:-production}
CONFIG_FILE="batch_processor_config.${ENVIRONMENT}.yaml"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check configuration file
    if [ ! -f "$CONFIG_FILE" ]; then
        error "Configuration file not found: $CONFIG_FILE"
    fi
    
    # Check environment variables for production
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ -z "$ADMIN_PASSWORD" ]; then
            error "ADMIN_PASSWORD environment variable must be set for production"
        fi
        
        if [ -z "$SESSION_SECRET_KEY" ]; then
            error "SESSION_SECRET_KEY environment variable must be set for production"
        fi
        
        if [ -z "$REDIS_PASSWORD" ] && [ "$ENVIRONMENT" = "production" ]; then
            warn "REDIS_PASSWORD not set - Redis will run without authentication"
        fi
    fi
    
    log "Prerequisites check passed"
}

# Backup existing data
backup_data() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log "Creating backup of existing data..."
        
        BACKUP_DIR="backups/$(date +'%Y%m%d_%H%M%S')"
        mkdir -p "$BACKUP_DIR"
        
        # Backup temp files if they exist
        if [ -d "temp_files" ]; then
            cp -r temp_files "$BACKUP_DIR/"
            log "Backed up temp files to $BACKUP_DIR"
        fi
        
        # Backup logs if they exist
        if [ -d "logs" ]; then
            cp -r logs "$BACKUP_DIR/"
            log "Backed up logs to $BACKUP_DIR"
        fi
        
        # Backup Redis data if container exists
        if docker ps -a | grep -q "batch_processor_redis"; then
            docker exec batch_processor_redis redis-cli BGSAVE || warn "Could not backup Redis data"
        fi
    fi
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    mkdir -p temp_files
    mkdir -p logs
    mkdir -p chroma_db
    mkdir -p backups
    
    # Set proper permissions
    chmod 755 temp_files logs chroma_db backups
    
    log "Directories created successfully"
}

# Generate environment file
generate_env_file() {
    log "Generating environment file..."
    
    ENV_FILE=".env.${ENVIRONMENT}"
    
    cat > "$ENV_FILE" << EOF
# Generated environment file for $ENVIRONMENT
BATCH_PROCESSOR_ENV=$ENVIRONMENT
BATCH_PROCESSOR_CONFIG=/app/$CONFIG_FILE

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=${REDIS_PASSWORD:-}

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Authentication
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
OPERATOR_PASSWORD=${OPERATOR_PASSWORD:-operator123}
SESSION_SECRET_KEY=${SESSION_SECRET_KEY:-change-this-secret-key}

# Security
HTTPS_ONLY=${HTTPS_ONLY:-false}
SECURE_COOKIES=${SECURE_COOKIES:-false}
DOMAIN=${DOMAIN:-localhost}

# Performance
WEB_WORKERS=${WEB_WORKERS:-2}
CHUNK_SIZE=${CHUNK_SIZE:-500}
MAX_FILE_SIZE_MB=${MAX_FILE_SIZE_MB:-50}

# Monitoring
ENABLE_LLM=${ENABLE_LLM:-false}
ENABLE_ANALYTICS=${ENABLE_ANALYTICS:-false}
ENABLE_NOTIFICATIONS=${ENABLE_NOTIFICATIONS:-false}
EOF

    log "Environment file generated: $ENV_FILE"
}

# Build and deploy
deploy() {
    log "Starting deployment for environment: $ENVIRONMENT"
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose down || warn "No existing containers to stop"
    
    # Build images
    log "Building Docker images..."
    docker-compose build --no-cache
    
    # Start services
    log "Starting services..."
    docker-compose --env-file ".env.${ENVIRONMENT}" up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    health_check
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check web service
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "Web service is healthy"
    else
        error "Web service health check failed"
    fi
    
    # Check Redis
    if docker exec batch_processor_redis redis-cli ping > /dev/null 2>&1; then
        log "Redis is healthy"
    else
        error "Redis health check failed"
    fi
    
    # Check Celery worker
    if docker exec batch_processor_worker celery -A batch_processor.workers.celery_app inspect ping > /dev/null 2>&1; then
        log "Celery worker is healthy"
    else
        warn "Celery worker health check failed"
    fi
    
    log "Health check completed"
}

# Show status
show_status() {
    log "Deployment status:"
    docker-compose ps
    
    log "Service URLs:"
    echo "  Web Application: http://localhost:8000"
    echo "  Flower (if enabled): http://localhost:5555"
    
    log "Logs can be viewed with:"
    echo "  docker-compose logs -f [service_name]"
}

# Cleanup old images
cleanup() {
    log "Cleaning up old Docker images..."
    docker image prune -f
    docker system prune -f
}

# Main deployment process
main() {
    log "Starting Batch Excel Processor deployment"
    log "Environment: $ENVIRONMENT"
    
    check_prerequisites
    backup_data
    setup_directories
    generate_env_file
    deploy
    show_status
    
    if [ "$ENVIRONMENT" = "production" ]; then
        cleanup
    fi
    
    log "Deployment completed successfully!"
    log "Access the application at: http://localhost:8000"
}

# Handle script arguments
case "${1:-}" in
    "production"|"staging"|"development")
        main
        ;;
    "health")
        health_check
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 {production|staging|development|health|status|cleanup}"
        echo ""
        echo "Commands:"
        echo "  production   - Deploy to production environment"
        echo "  staging      - Deploy to staging environment"
        echo "  development  - Deploy to development environment"
        echo "  health       - Run health check on existing deployment"
        echo "  status       - Show deployment status"
        echo "  cleanup      - Clean up old Docker images"
        echo ""
        echo "Environment variables for production:"
        echo "  ADMIN_PASSWORD     - Admin user password (required)"
        echo "  SESSION_SECRET_KEY - Session secret key (required)"
        echo "  REDIS_PASSWORD     - Redis password (optional)"
        echo "  DOMAIN             - Application domain (optional)"
        echo "  HTTPS_ONLY         - Enable HTTPS only mode (optional)"
        exit 1
        ;;
esac