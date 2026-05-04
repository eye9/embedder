# Batch Excel Processor - Deployment Guide

This guide covers the deployment of the Batch Excel Processor in production, staging, and development environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Production Deployment](#production-deployment)
- [Staging Deployment](#staging-deployment)
- [Development Deployment](#development-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: Minimum 20GB free space (50GB+ recommended for production)
- **CPU**: 2+ cores (4+ cores recommended for production)

### Network Requirements

- **Ports**: 8000 (web), 6379 (Redis), 5555 (Flower - optional)
- **Internet Access**: Required for Docker image pulls and LLM services (if enabled)

## Environment Configuration

### Environment Variables

Create environment-specific configuration by setting these variables:

#### Required for Production

```bash
# Authentication (REQUIRED)
export ADMIN_PASSWORD="your-secure-admin-password"
export SESSION_SECRET_KEY="your-long-random-secret-key"

# Domain configuration
export DOMAIN="spegat.com"
export HTTPS_ONLY="true"
export SECURE_COOKIES="true"

# Redis security (recommended)
export REDIS_PASSWORD="your-redis-password"
```

#### Optional Configuration

```bash
# Performance tuning
export WEB_WORKERS="2"
export CHUNK_SIZE="500"
export MAX_FILE_SIZE_MB="50"

# Feature flags
export ENABLE_LLM="false"
export ENABLE_ANALYTICS="true"
export ENABLE_NOTIFICATIONS="false"

# Monitoring
export ALERT_EMAIL="admin@your-domain.com"
```

### Configuration Files

The system uses environment-specific YAML configuration files:

- `batch_processor_config.production.yaml` - Production settings
- `batch_processor_config.staging.yaml` - Staging settings
- `batch_processor_config.docker.yaml` - Docker-specific settings

## Production Deployment

### Pre-deployment Validation

1. **Validate Environment**:
   ```bash
   chmod +x scripts/deployment/validate-production.sh
   ./scripts/deployment/validate-production.sh
   ```

2. **Set Required Environment Variables**:
   ```bash
   export ADMIN_PASSWORD="your-secure-password-here"
   export SESSION_SECRET_KEY="your-very-long-random-secret-key-here"
   export DOMAIN="your-production-domain.com"
   export HTTPS_ONLY="true"
   export SECURE_COOKIES="true"
   export REDIS_PASSWORD="your-redis-password"
   ```

### Deployment Steps

1. **Deploy to Production**:
   ```bash
   chmod +x scripts/deployment/deploy.sh
   ./scripts/deployment/deploy.sh production
   ```

2. **Verify Deployment**:
   ```bash
   ./scripts/deployment/deploy.sh health
   ```

3. **Check Status**:
   ```bash
   ./scripts/deployment/deploy.sh status
   ```

### Post-deployment

1. **Set up Monitoring**:
   ```bash
   chmod +x scripts/deployment/monitor.sh
   # Add to crontab for regular monitoring
   echo "*/5 * * * * /path/to/scripts/deployment/monitor.sh monitor" | crontab -
   ```

2. **Configure Backup** (if enabled):
   ```bash
   # Backup runs automatically if configured
   # Manual backup can be triggered via the monitoring script
   ./scripts/deployment/monitor.sh full
   ```

## Staging Deployment

Staging deployment is similar to production but with relaxed security settings:

```bash
export ADMIN_PASSWORD="staging123"
export SESSION_SECRET_KEY="staging-secret-key"
export STAGING_DOMAIN="staging.your-domain.com"

./scripts/deployment/deploy.sh staging
```

## Development Deployment

For development with hot reload:

```bash
# Use development override
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Or use the deployment script
./scripts/deployment/deploy.sh development
```

## Docker Commands Reference

### Basic Operations

```bash
# Build and start all services
make up

# Start in development mode
make dev

# View logs
make logs

# Stop services
make down

# Clean up
make clean

# Scale workers
make scale-workers

# Health check
make health
```

### Manual Docker Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale worker=3

# Execute commands in containers
docker-compose exec web bash
docker-compose exec redis redis-cli
```

## Monitoring and Maintenance

### Health Monitoring

The system includes comprehensive health monitoring:

```bash
# Run health checks
./scripts/deployment/monitor.sh monitor

# Generate detailed report
./scripts/deployment/monitor.sh report

# Clean up old files
./scripts/deployment/monitor.sh cleanup

# Restart unhealthy services
./scripts/deployment/monitor.sh restart

# Full monitoring cycle
./scripts/deployment/monitor.sh full
```

### Log Management

Logs are stored in the `logs/` directory:

- `logs/batch_processor.log` - Application logs
- `health_report_*.txt` - Health check reports
- `monitor.log` - Monitoring script logs

### Performance Monitoring

Access Flower (Celery monitoring) at `http://localhost:5555` (if enabled):

```bash
# Start Flower
docker-compose --profile monitoring up flower -d
```

## Security Considerations

### Production Security Checklist

- [ ] Strong admin password set
- [ ] Unique session secret key configured
- [ ] HTTPS enforced (`HTTPS_ONLY=true`)
- [ ] Secure cookies enabled (`SECURE_COOKIES=true`)
- [ ] Redis password protection enabled
- [ ] Rate limiting configured
- [ ] File size limits set appropriately
- [ ] Debug mode disabled
- [ ] Minimal ports exposed
- [ ] Security headers enabled
- [ ] CSRF protection enabled

### Network Security

- Use Docker networks for service isolation
- Implement reverse proxy (Nginx) for SSL termination
- Configure firewall rules to restrict access
- Use VPN for administrative access

### Data Security

- Regular backups of critical data
- Encryption at rest for sensitive data
- Secure file cleanup policies
- Session timeout configuration
- Failed login attempt protection

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check Docker status
docker info

# Check logs
docker-compose logs

# Restart services
docker-compose restart
```

#### High Memory Usage

```bash
# Check container resources
docker stats

# Scale down workers if needed
docker-compose up -d --scale worker=1

# Clean up old files
./scripts/deployment/monitor.sh cleanup
```

#### Redis Connection Issues

```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis

# Check Redis logs
docker-compose logs redis
```

#### Web Service Unresponsive

```bash
# Check health endpoint
curl http://localhost:8000/health

# Restart web service
docker-compose restart web

# Check web service logs
docker-compose logs web
```

### Performance Issues

#### Slow File Processing

- Reduce chunk size in configuration
- Scale up worker processes
- Check available memory and CPU
- Optimize TNVED database queries

#### High CPU Usage

- Reduce concurrent uploads limit
- Implement request queuing
- Scale horizontally with more workers
- Check for infinite loops in logs

### Log Analysis

```bash
# Search for errors
grep "ERROR" logs/batch_processor.log

# Monitor real-time logs
tail -f logs/batch_processor.log

# Check specific time period
grep "2024-01-01" logs/batch_processor.log
```

## Backup and Recovery

### Automated Backups

Backups are configured in the production configuration:

```yaml
backup:
  enabled: true
  interval_hours: 24
  retention_days: 7
  backup_path: "/app/backups"
```

### Manual Backup

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)

# Backup application data
cp -r temp_files logs backups/$(date +%Y%m%d_%H%M%S)/

# Backup Redis data
docker exec batch_processor_redis redis-cli BGSAVE
```

### Recovery

```bash
# Stop services
docker-compose down

# Restore data
cp -r backups/YYYYMMDD_HHMMSS/* ./

# Restart services
docker-compose up -d
```

## Scaling

### Horizontal Scaling

```bash
# Scale web workers
docker-compose up -d --scale web=2

# Scale Celery workers
docker-compose up -d --scale worker=3

# Scale cleanup workers
docker-compose up -d --scale cleanup_worker=2
```

### Load Balancing

For multiple web instances, configure a load balancer (Nginx example):

```nginx
upstream batch_processor {
    server localhost:8000;
    server localhost:8001;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://batch_processor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Support

For issues and questions:

1. Check the logs first: `docker-compose logs`
2. Run health checks: `./scripts/deployment/monitor.sh monitor`
3. Validate configuration: `./scripts/deployment/validate-production.sh`
4. Review this deployment guide
5. Check the main README.md for application-specific information

## Version Information

- **Application Version**: 1.0.0
- **Docker Compose Version**: 3.8
- **Python Version**: 3.11
- **Redis Version**: 7-alpine
