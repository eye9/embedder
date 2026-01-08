#!/bin/bash

# Production monitoring script for Batch Excel Processor
set -e

# Configuration
ALERT_EMAIL=${ALERT_EMAIL:-"admin@example.com"}
LOG_FILE="logs/monitor.log"
HEALTH_CHECK_URL="http://localhost:8000/health"
REDIS_CONTAINER="batch_processor_redis"
WEB_CONTAINER="batch_processor_web"
WORKER_CONTAINER="batch_processor_worker"

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85
ERROR_THRESHOLD=10

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

# Check service health
check_service_health() {
    log "Checking service health..."
    
    # Web service health
    if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
        log "✓ Web service is healthy"
    else
        error "✗ Web service health check failed"
        return 1
    fi
    
    # Redis health
    if docker exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
        log "✓ Redis is healthy"
    else
        error "✗ Redis health check failed"
        return 1
    fi
    
    # Celery worker health
    if docker exec "$WORKER_CONTAINER" celery -A batch_processor.workers.celery_app inspect ping > /dev/null 2>&1; then
        log "✓ Celery worker is healthy"
    else
        error "✗ Celery worker health check failed"
        return 1
    fi
    
    return 0
}

# Check container status
check_container_status() {
    log "Checking container status..."
    
    local containers=("$REDIS_CONTAINER" "$WEB_CONTAINER" "$WORKER_CONTAINER")
    local failed=0
    
    for container in "${containers[@]}"; do
        if docker ps | grep -q "$container"; then
            log "✓ Container $container is running"
        else
            error "✗ Container $container is not running"
            failed=1
        fi
    done
    
    return $failed
}

# Check resource usage
check_resource_usage() {
    log "Checking resource usage..."
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l) )); then
        warn "High CPU usage: ${cpu_usage}%"
    else
        log "✓ CPU usage: ${cpu_usage}%"
    fi
    
    # Memory usage
    local memory_info=$(free | grep Mem)
    local total_mem=$(echo $memory_info | awk '{print $2}')
    local used_mem=$(echo $memory_info | awk '{print $3}')
    local memory_percent=$(( used_mem * 100 / total_mem ))
    
    if [ $memory_percent -gt $MEMORY_THRESHOLD ]; then
        warn "High memory usage: ${memory_percent}%"
    else
        log "✓ Memory usage: ${memory_percent}%"
    fi
    
    # Disk usage
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $disk_usage -gt $DISK_THRESHOLD ]; then
        warn "High disk usage: ${disk_usage}%"
    else
        log "✓ Disk usage: ${disk_usage}%"
    fi
}

# Check Docker container resources
check_container_resources() {
    log "Checking container resource usage..."
    
    local containers=("$REDIS_CONTAINER" "$WEB_CONTAINER" "$WORKER_CONTAINER")
    
    for container in "${containers[@]}"; do
        if docker ps | grep -q "$container"; then
            local stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" "$container" | tail -1)
            log "Container $container: $stats"
        fi
    done
}

# Check log errors
check_log_errors() {
    log "Checking for recent errors in logs..."
    
    # Check application logs for errors in the last hour
    local error_count=0
    if [ -f "logs/batch_processor.log" ]; then
        error_count=$(grep -c "ERROR" logs/batch_processor.log | tail -100 || echo 0)
    fi
    
    if [ $error_count -gt $ERROR_THRESHOLD ]; then
        warn "High error count in logs: $error_count errors"
        # Show recent errors
        if [ -f "logs/batch_processor.log" ]; then
            log "Recent errors:"
            grep "ERROR" logs/batch_processor.log | tail -5
        fi
    else
        log "✓ Error count in acceptable range: $error_count errors"
    fi
}

# Check file system
check_file_system() {
    log "Checking file system..."
    
    # Check temp files directory
    if [ -d "temp_files" ]; then
        local temp_size=$(du -sh temp_files | awk '{print $1}')
        local temp_count=$(find temp_files -type f | wc -l)
        log "Temp files: $temp_count files, $temp_size total"
        
        # Check for old files (older than 24 hours)
        local old_files=$(find temp_files -type f -mtime +1 | wc -l)
        if [ $old_files -gt 0 ]; then
            warn "$old_files old temp files found (older than 24 hours)"
        fi
    fi
    
    # Check logs directory
    if [ -d "logs" ]; then
        local log_size=$(du -sh logs | awk '{print $1}')
        log "Log files size: $log_size"
    fi
}

# Check Redis metrics
check_redis_metrics() {
    log "Checking Redis metrics..."
    
    if docker exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
        local redis_info=$(docker exec "$REDIS_CONTAINER" redis-cli info memory | grep used_memory_human)
        local redis_connections=$(docker exec "$REDIS_CONTAINER" redis-cli info clients | grep connected_clients)
        
        log "Redis memory: $redis_info"
        log "Redis connections: $redis_connections"
        
        # Check for Redis errors
        local redis_errors=$(docker exec "$REDIS_CONTAINER" redis-cli info stats | grep keyspace_misses || echo "keyspace_misses:0")
        log "Redis stats: $redis_errors"
    fi
}

# Check Celery queue
check_celery_queue() {
    log "Checking Celery queue status..."
    
    if docker exec "$WORKER_CONTAINER" celery -A batch_processor.workers.celery_app inspect active > /dev/null 2>&1; then
        local active_tasks=$(docker exec "$WORKER_CONTAINER" celery -A batch_processor.workers.celery_app inspect active 2>/dev/null | grep -c "uuid" || echo 0)
        local reserved_tasks=$(docker exec "$WORKER_CONTAINER" celery -A batch_processor.workers.celery_app inspect reserved 2>/dev/null | grep -c "uuid" || echo 0)
        
        log "Active Celery tasks: $active_tasks"
        log "Reserved Celery tasks: $reserved_tasks"
        
        if [ $active_tasks -gt 10 ]; then
            warn "High number of active Celery tasks: $active_tasks"
        fi
    fi
}

# Generate report
generate_report() {
    local report_file="logs/health_report_$(date +'%Y%m%d_%H%M%S').txt"
    
    {
        echo "Batch Excel Processor Health Report"
        echo "Generated: $(date)"
        echo "=================================="
        echo ""
        
        echo "Service Status:"
        check_service_health 2>&1
        echo ""
        
        echo "Container Status:"
        check_container_status 2>&1
        echo ""
        
        echo "Resource Usage:"
        check_resource_usage 2>&1
        echo ""
        
        echo "Container Resources:"
        check_container_resources 2>&1
        echo ""
        
        echo "File System:"
        check_file_system 2>&1
        echo ""
        
        echo "Redis Metrics:"
        check_redis_metrics 2>&1
        echo ""
        
        echo "Celery Queue:"
        check_celery_queue 2>&1
        echo ""
        
        echo "Recent Log Errors:"
        check_log_errors 2>&1
        
    } > "$report_file"
    
    log "Health report generated: $report_file"
}

# Send alert (placeholder - implement with your preferred method)
send_alert() {
    local message="$1"
    local severity="$2"
    
    # Log the alert
    if [ "$severity" = "critical" ]; then
        error "ALERT: $message"
    else
        warn "ALERT: $message"
    fi
    
    # Here you would implement actual alerting (email, Slack, etc.)
    # Example: echo "$message" | mail -s "Batch Processor Alert" "$ALERT_EMAIL"
}

# Main monitoring function
monitor() {
    log "Starting health monitoring check..."
    
    local issues=0
    
    # Run all checks
    if ! check_service_health; then
        send_alert "Service health check failed" "critical"
        issues=$((issues + 1))
    fi
    
    if ! check_container_status; then
        send_alert "Container status check failed" "critical"
        issues=$((issues + 1))
    fi
    
    check_resource_usage
    check_container_resources
    check_file_system
    check_redis_metrics
    check_celery_queue
    check_log_errors
    
    if [ $issues -eq 0 ]; then
        log "✓ All health checks passed"
    else
        error "$issues critical issues found"
    fi
    
    log "Health monitoring check completed"
    return $issues
}

# Cleanup old files
cleanup_old_files() {
    log "Cleaning up old files..."
    
    # Clean temp files older than 24 hours
    if [ -d "temp_files" ]; then
        find temp_files -type f -mtime +1 -delete 2>/dev/null || true
        log "Cleaned old temp files"
    fi
    
    # Clean old log files (keep last 10)
    if [ -d "logs" ]; then
        find logs -name "health_report_*.txt" -type f | sort | head -n -10 | xargs rm -f 2>/dev/null || true
        find logs -name "monitor.log.*" -type f | sort | head -n -5 | xargs rm -f 2>/dev/null || true
        log "Cleaned old log files"
    fi
}

# Restart unhealthy services
restart_services() {
    log "Restarting unhealthy services..."
    
    # Check and restart web service if needed
    if ! curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
        warn "Restarting web service..."
        docker-compose restart web
        sleep 10
    fi
    
    # Check and restart worker if needed
    if ! docker exec "$WORKER_CONTAINER" celery -A batch_processor.workers.celery_app inspect ping > /dev/null 2>&1; then
        warn "Restarting worker service..."
        docker-compose restart worker
        sleep 10
    fi
}

# Main script logic
case "${1:-monitor}" in
    "monitor")
        monitor
        ;;
    "report")
        generate_report
        ;;
    "cleanup")
        cleanup_old_files
        ;;
    "restart")
        restart_services
        ;;
    "full")
        monitor
        generate_report
        cleanup_old_files
        ;;
    *)
        echo "Usage: $0 {monitor|report|cleanup|restart|full}"
        echo ""
        echo "Commands:"
        echo "  monitor  - Run health monitoring checks (default)"
        echo "  report   - Generate detailed health report"
        echo "  cleanup  - Clean up old files"
        echo "  restart  - Restart unhealthy services"
        echo "  full     - Run all monitoring tasks"
        echo ""
        echo "Environment variables:"
        echo "  ALERT_EMAIL - Email address for alerts"
        exit 1
        ;;
esac