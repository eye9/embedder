#!/bin/bash

# Production environment validation script
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Logging functions
pass() {
    echo -e "${GREEN}✓ $1${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

info() {
    echo -e "ℹ $1"
}

# Check environment variables
check_environment_variables() {
    info "Checking environment variables..."
    
    # Critical environment variables
    if [ -n "$ADMIN_PASSWORD" ] && [ "$ADMIN_PASSWORD" != "admin123" ]; then
        pass "ADMIN_PASSWORD is set and not default"
    else
        fail "ADMIN_PASSWORD must be set and not use default value"
    fi
    
    if [ -n "$SESSION_SECRET_KEY" ] && [ "$SESSION_SECRET_KEY" != "change-this-secret-key" ]; then
        pass "SESSION_SECRET_KEY is set and not default"
    else
        fail "SESSION_SECRET_KEY must be set and not use default value"
    fi
    
    # Optional but recommended
    if [ -n "$REDIS_PASSWORD" ]; then
        pass "REDIS_PASSWORD is set"
    else
        warn "REDIS_PASSWORD is not set - Redis will run without authentication"
    fi
    
    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "localhost" ]; then
        pass "DOMAIN is set to production value: $DOMAIN"
    else
        warn "DOMAIN should be set to production domain name"
    fi
    
    # Security settings
    if [ "$HTTPS_ONLY" = "true" ]; then
        pass "HTTPS_ONLY is enabled"
    else
        warn "HTTPS_ONLY should be enabled in production"
    fi
    
    if [ "$SECURE_COOKIES" = "true" ]; then
        pass "SECURE_COOKIES is enabled"
    else
        warn "SECURE_COOKIES should be enabled in production"
    fi
}

# Check configuration files
check_configuration_files() {
    info "Checking configuration files..."
    
    # Production config
    if [ -f "batch_processor_config.production.yaml" ]; then
        pass "Production configuration file exists"
    else
        fail "Production configuration file not found"
    fi
    
    # Docker files
    if [ -f "Dockerfile" ]; then
        pass "Dockerfile exists"
    else
        fail "Dockerfile not found"
    fi
    
    if [ -f "docker-compose.yml" ]; then
        pass "docker-compose.yml exists"
    else
        fail "docker-compose.yml not found"
    fi
    
    # Check for development files that shouldn't be in production
    if [ -f ".env" ]; then
        warn "Development .env file found - ensure it doesn't contain production secrets"
    fi
    
    if [ -f "docker-compose.dev.yml" ]; then
        info "Development docker-compose override found (this is OK)"
    fi
}

# Check security configuration
check_security_configuration() {
    info "Checking security configuration..."
    
    # Check if debug mode is disabled
    if grep -q "debug: false" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Debug mode is disabled in production config"
    else
        fail "Debug mode should be disabled in production"
    fi
    
    # Check if rate limiting is enabled
    if grep -q "enabled: true" batch_processor_config.production.yaml | grep -A5 "rate_limiting" >/dev/null 2>&1; then
        pass "Rate limiting is enabled"
    else
        warn "Rate limiting should be enabled in production"
    fi
    
    # Check session timeout
    if grep -q "session_timeout_hours: [1-8]" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Session timeout is set to reasonable value"
    else
        warn "Session timeout should be set to 8 hours or less in production"
    fi
    
    # Check file size limits
    if grep -q "max_file_size_mb: [1-5][0-9]" batch_processor_config.production.yaml 2>/dev/null; then
        pass "File size limit is set to reasonable value"
    else
        warn "File size limit should be reasonable for production (50MB or less)"
    fi
}

# Check Docker setup
check_docker_setup() {
    info "Checking Docker setup..."
    
    # Check if Docker is running
    if docker info >/dev/null 2>&1; then
        pass "Docker is running"
    else
        fail "Docker is not running or not accessible"
    fi
    
    # Check if Docker Compose is available
    if command -v docker-compose >/dev/null 2>&1; then
        pass "Docker Compose is available"
    else
        fail "Docker Compose is not installed"
    fi
    
    # Check for multi-stage build in Dockerfile
    if grep -q "FROM.*as production" Dockerfile 2>/dev/null; then
        pass "Multi-stage Docker build is configured"
    else
        warn "Multi-stage Docker build recommended for production"
    fi
    
    # Check for health checks
    if grep -q "HEALTHCHECK" Dockerfile 2>/dev/null; then
        pass "Health checks are configured in Dockerfile"
    else
        warn "Health checks should be configured in Dockerfile"
    fi
}

# Check file permissions and directories
check_file_system() {
    info "Checking file system setup..."
    
    # Check required directories
    local dirs=("temp_files" "logs" "chroma_db")
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            pass "Directory $dir exists"
        else
            warn "Directory $dir should be created before deployment"
        fi
    done
    
    # Check .dockerignore
    if [ -f ".dockerignore" ]; then
        pass ".dockerignore file exists"
        
        # Check if it excludes development files
        if grep -q "\.env" .dockerignore 2>/dev/null; then
            pass ".dockerignore excludes .env files"
        else
            warn ".dockerignore should exclude .env files"
        fi
    else
        warn ".dockerignore file should exist to optimize builds"
    fi
    
    # Check for sensitive files
    if [ -f ".env" ]; then
        warn ".env file found - ensure it's not committed to version control"
    fi
    
    if find . -name "*.key" -o -name "*.pem" -o -name "*.p12" | grep -q .; then
        warn "Certificate/key files found - ensure they're properly secured"
    fi
}

# Check network security
check_network_security() {
    info "Checking network security configuration..."
    
    # Check if services are properly networked in docker-compose
    if grep -q "networks:" docker-compose.yml 2>/dev/null; then
        pass "Docker networks are configured"
    else
        warn "Docker networks should be configured for service isolation"
    fi
    
    # Check for exposed ports
    local exposed_ports=$(grep -c "ports:" docker-compose.yml 2>/dev/null || echo 0)
    if [ "$exposed_ports" -le 3 ]; then
        pass "Minimal ports are exposed ($exposed_ports)"
    else
        warn "Too many ports exposed - minimize for security"
    fi
    
    # Check for Redis password in production
    if grep -q "REDIS_PASSWORD" docker-compose.yml 2>/dev/null; then
        pass "Redis password configuration found"
    else
        warn "Redis should be password protected in production"
    fi
}

# Check monitoring and logging
check_monitoring() {
    info "Checking monitoring and logging setup..."
    
    # Check for log configuration
    if grep -q "logging:" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Logging configuration found"
    else
        warn "Logging should be properly configured"
    fi
    
    # Check for monitoring configuration
    if grep -q "monitoring:" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Monitoring configuration found"
    else
        warn "Monitoring should be configured for production"
    fi
    
    # Check for health check endpoints
    if [ -f "batch_processor/web/health.py" ]; then
        pass "Health check endpoint exists"
    else
        warn "Health check endpoint should be implemented"
    fi
    
    # Check monitoring scripts
    if [ -f "monitor.sh" ]; then
        pass "Monitoring script exists"
    else
        warn "Monitoring script should be available for production"
    fi
}

# Check backup configuration
check_backup_configuration() {
    info "Checking backup configuration..."
    
    # Check for backup configuration
    if grep -q "backup:" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Backup configuration found"
    else
        warn "Backup configuration should be set up for production"
    fi
    
    # Check for backup directory
    if [ -d "backups" ]; then
        pass "Backup directory exists"
    else
        warn "Backup directory should be created"
    fi
    
    # Check deployment script
    if [ -f "deploy.sh" ]; then
        pass "Deployment script exists"
        
        # Check if it includes backup functionality
        if grep -q "backup" deploy.sh 2>/dev/null; then
            pass "Deployment script includes backup functionality"
        else
            warn "Deployment script should include backup functionality"
        fi
    else
        warn "Deployment script should be available"
    fi
}

# Check performance configuration
check_performance_configuration() {
    info "Checking performance configuration..."
    
    # Check worker configuration
    if grep -q "workers: [2-9]" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Multiple web workers configured"
    else
        warn "Multiple web workers should be configured for production"
    fi
    
    # Check chunk size
    if grep -q "chunk_size: [1-5][0-9][0-9]" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Reasonable chunk size configured"
    else
        warn "Chunk size should be optimized for production (500-1000)"
    fi
    
    # Check connection limits
    if grep -q "max_connections:" batch_processor_config.production.yaml 2>/dev/null; then
        pass "Connection limits configured"
    else
        warn "Connection limits should be configured"
    fi
}

# Generate summary report
generate_summary() {
    echo ""
    echo "=================================="
    echo "Production Readiness Summary"
    echo "=================================="
    echo ""
    
    if [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All critical checks passed${NC}"
    else
        echo -e "${RED}✗ $CHECKS_FAILED critical checks failed${NC}"
    fi
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warnings found${NC}"
    fi
    
    echo -e "ℹ $CHECKS_PASSED checks passed"
    echo ""
    
    if [ $CHECKS_FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 System is ready for production deployment!${NC}"
        exit 0
    elif [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${YELLOW}⚠ System can be deployed but warnings should be addressed${NC}"
        exit 0
    else
        echo -e "${RED}❌ System is NOT ready for production deployment${NC}"
        echo "Please fix the failed checks before deploying to production."
        exit 1
    fi
}

# Main validation process
main() {
    echo "Batch Excel Processor - Production Readiness Validation"
    echo "======================================================"
    echo ""
    
    check_environment_variables
    echo ""
    
    check_configuration_files
    echo ""
    
    check_security_configuration
    echo ""
    
    check_docker_setup
    echo ""
    
    check_file_system
    echo ""
    
    check_network_security
    echo ""
    
    check_monitoring
    echo ""
    
    check_backup_configuration
    echo ""
    
    check_performance_configuration
    echo ""
    
    generate_summary
}

# Run validation
main