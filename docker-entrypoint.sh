#!/bin/bash
set -e

# Docker entrypoint script for Batch Excel Processor

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    while ! redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
        echo "Redis is unavailable - sleeping"
        sleep 1
    done
    echo "Redis is ready!"
}

# Function to create necessary directories
create_directories() {
    echo "Creating necessary directories..."
    mkdir -p /app/temp_files
    mkdir -p /app/logs
    mkdir -p /app/chroma_db
    
    # Ensure proper permissions
    chown -R appuser:appuser /app/temp_files /app/logs /app/chroma_db 2>/dev/null || true
}

# Function to validate configuration
validate_config() {
    echo "Validating configuration..."
    if [ ! -f "/app/batch_processor_config.yaml" ] && [ ! -f "/app/batch_processor_config.docker.yaml" ]; then
        echo "Warning: No configuration file found, using defaults"
    fi
}

# Main execution
main() {
    echo "Starting Batch Excel Processor..."
    echo "Environment: ${BATCH_PROCESSOR_ENV:-production}"
    
    # Create directories
    create_directories
    
    # Validate configuration
    validate_config
    
    # Wait for Redis if this is a worker or web service
    if [[ "$1" == *"celery"* ]] || [[ "$1" == *"uvicorn"* ]] || [[ "$1" == "python" && "$2" == "start_batch_web.py" ]]; then
        wait_for_redis
    fi
    
    # Execute the command
    echo "Executing: $@"
    exec "$@"
}

# Run main function with all arguments
main "$@"