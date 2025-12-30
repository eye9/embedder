"""
Health check and monitoring endpoints for batch Excel processor.

This module provides comprehensive health monitoring including:
- System health checks
- Service dependency checks
- Performance metrics endpoints
- Monitoring dashboard data
"""

import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import redis
from pathlib import Path

from ..config.settings import get_config
from ..services.monitoring import get_metrics_collector, SystemMetrics
from ..services.logging_service import get_logging_service
from .models import HealthResponse, ServiceInfo
from .auth import get_current_user


router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth:
    """Service health checker."""
    
    def __init__(self):
        """Initialize health checker."""
        self.config = get_config()
        self.metrics_collector = get_metrics_collector()
        self.logging_service = get_logging_service()
    
    def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            start_time = time.time()
            
            # Create Redis connection
            redis_client = redis.Redis.from_url(self.config.redis.url)
            
            # Test basic operations
            redis_client.ping()
            redis_client.set("health_check", "ok", ex=60)
            value = redis_client.get("health_check")
            
            response_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = redis_client.info()
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / (1024**2), 2),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "version": info.get("redis_version", "unknown")
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "response_time_ms": None
            }
    
    def check_disk_health(self) -> Dict[str, Any]:
        """Check disk space and I/O health."""
        try:
            # Check temp directory disk usage
            temp_dir = Path(self.config.files.temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            disk_usage = psutil.disk_usage(str(temp_dir))
            free_gb = disk_usage.free / (1024**3)
            total_gb = disk_usage.total / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Test write performance
            start_time = time.time()
            test_file = temp_dir / "health_check_write_test.tmp"
            test_data = b"health check test data" * 1000  # ~22KB
            
            with open(test_file, 'wb') as f:
                f.write(test_data)
                f.flush()
                f.fsync()  # Force write to disk
            
            write_time = (time.time() - start_time) * 1000
            
            # Clean up test file
            test_file.unlink(missing_ok=True)
            
            # Determine health status
            if used_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif used_percent > 85:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                "status": status,
                "free_space_gb": round(free_gb, 2),
                "total_space_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 1),
                "write_test_ms": round(write_time, 2),
                "temp_directory": str(temp_dir)
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)
            }
    
    def check_memory_health(self) -> Dict[str, Any]:
        """Check system memory health."""
        try:
            memory = psutil.virtual_memory()
            
            # Determine health status based on memory usage
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                "status": status,
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": round(memory.percent, 1),
                "free_gb": round(memory.free / (1024**3), 2)
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)
            }
    
    def check_cpu_health(self) -> Dict[str, Any]:
        """Check CPU health and load."""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # Determine health status
            if cpu_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 85:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                "status": status,
                "usage_percent": round(cpu_percent, 1),
                "cpu_count": cpu_count,
                "load_average_1m": round(load_avg[0], 2),
                "load_average_5m": round(load_avg[1], 2),
                "load_average_15m": round(load_avg[2], 2)
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)
            }
    
    def check_tnved_integration_health(self) -> Dict[str, Any]:
        """Check TNVED integration health."""
        try:
            from ..services.tnved_integration import get_tnved_integration
            
            start_time = time.time()
            tnved_integration = get_tnved_integration()
            
            # Test basic search functionality
            test_results = tnved_integration.search("test product", top_k=1)
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round(response_time, 2),
                "search_results_count": len(test_results),
                "integration_available": True
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "error": str(e),
                "integration_available": False
            }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        checks = {
            "redis": self.check_redis_health(),
            "disk": self.check_disk_health(),
            "memory": self.check_memory_health(),
            "cpu": self.check_cpu_health(),
            "tnved_integration": self.check_tnved_integration_health()
        }
        
        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }


# Initialize health checker
health_checker = ServiceHealth()


@router.get("/", response_model=HealthResponse)
async def basic_health_check():
    """
    Basic health check endpoint.
    
    Returns simple health status for load balancers and monitoring systems.
    """
    try:
        # Quick system check
        memory = psutil.virtual_memory()
        if memory.percent > 95:
            raise HTTPException(status_code=503, detail="System memory critically low")
        
        return HealthResponse(
            status="healthy",
            service="batch-excel-processor",
            timestamp=datetime.utcnow(),
            version="1.0.0"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check with all system components.
    
    Requires authentication and provides comprehensive health information.
    """
    health_data = health_checker.get_overall_health()
    
    # Add system metrics
    system_metrics = health_checker.metrics_collector.get_system_metrics()
    health_data["system_metrics"] = system_metrics.to_dict()
    
    # Add recent error summary
    log_summary = health_checker.logging_service.get_system_log_summary()
    health_data["log_summary"] = log_summary
    
    # Set HTTP status code based on health
    status_code = 200
    if health_data["status"] == HealthStatus.DEGRADED:
        status_code = 200  # Still operational
    elif health_data["status"] == HealthStatus.UNHEALTHY:
        status_code = 503  # Service unavailable
    
    return JSONResponse(content=health_data, status_code=status_code)


@router.get("/metrics")
async def get_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="Hours of metrics to retrieve"),
    user: str = Depends(get_current_user)
):
    """
    Get system performance metrics.
    
    Requires authentication. Returns performance metrics for the specified time period.
    """
    try:
        metrics_collector = get_metrics_collector()
        
        # Get performance summary
        performance_summary = metrics_collector.get_performance_summary(hours)
        
        # Get current system metrics
        current_metrics = metrics_collector.get_system_metrics()
        
        # Get error summary from logging service
        logging_service = get_logging_service()
        error_summary = {}
        for logger_name, logger in logging_service.loggers.items():
            error_summary[logger_name] = logger.get_error_summary(hours)
        
        return {
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
            "performance_summary": performance_summary,
            "current_system_metrics": current_metrics.to_dict(),
            "error_summary": error_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")


@router.get("/performance/{category}")
async def get_performance_metrics(
    category: str,
    hours: int = Query(default=24, ge=1, le=168),
    user: str = Depends(get_current_user)
):
    """
    Get performance metrics for a specific category.
    
    Categories: processing, authentication, file_upload, api, system
    """
    try:
        from ..services.logging_service import LogCategory
        
        # Validate category
        try:
            log_category = LogCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid category. Valid categories: {[c.value for c in LogCategory]}"
            )
        
        logging_service = get_logging_service()
        performance_data = {}
        
        for logger_name, logger in logging_service.loggers.items():
            summary = logger.get_performance_summary(log_category, hours)
            if summary["total_operations"] > 0:
                performance_data[logger_name] = summary
        
        return {
            "category": category,
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
            "performance_data": performance_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")


@router.get("/status")
async def get_service_status():
    """
    Get service status information.
    
    Public endpoint that provides basic service information and status.
    """
    config = get_config()
    
    return {
        "service": "Batch Excel Processor",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "configuration": {
            "max_file_size_mb": config.processing.max_file_size_mb,
            "supported_formats": config.processing.supported_extensions,
            "authentication_enabled": config.auth.enabled,
            "processing_algorithms": ["similarity_top1", "llm_reasoning"]
        },
        "uptime_check": {
            "redis_available": health_checker.check_redis_health()["status"] == HealthStatus.HEALTHY,
            "disk_space_ok": health_checker.check_disk_health()["status"] != HealthStatus.UNHEALTHY,
            "memory_ok": health_checker.check_memory_health()["status"] != HealthStatus.UNHEALTHY
        }
    }


@router.get("/readiness")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if service is ready to accept traffic, 503 otherwise.
    """
    try:
        # Check critical dependencies
        redis_health = health_checker.check_redis_health()
        memory_health = health_checker.check_memory_health()
        disk_health = health_checker.check_disk_health()
        
        # Service is ready if critical components are not unhealthy
        critical_checks = [redis_health, memory_health, disk_health]
        unhealthy_checks = [check for check in critical_checks if check["status"] == HealthStatus.UNHEALTHY]
        
        if unhealthy_checks:
            return JSONResponse(
                content={
                    "ready": False,
                    "reason": "Critical components unhealthy",
                    "unhealthy_components": [
                        check.get("error", "Unknown error") for check in unhealthy_checks
                    ]
                },
                status_code=503
            )
        
        return JSONResponse(
            content={
                "ready": True,
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "ready": False,
                "reason": f"Readiness check failed: {str(e)}"
            },
            status_code=503
        )


@router.get("/liveness")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if service is alive, 503 if it should be restarted.
    """
    try:
        # Basic liveness check - can we respond and access basic system info?
        memory = psutil.virtual_memory()
        
        # If memory is critically low, service should be restarted
        if memory.percent > 98:
            return JSONResponse(
                content={
                    "alive": False,
                    "reason": "Critical memory shortage"
                },
                status_code=503
            )
        
        return JSONResponse(
            content={
                "alive": True,
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "alive": False,
                "reason": f"Liveness check failed: {str(e)}"
            },
            status_code=503
        )