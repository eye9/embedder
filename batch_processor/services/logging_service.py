"""
Enhanced logging service for batch Excel processor.

This module provides comprehensive logging capabilities including:
- Structured logging with context
- Performance logging
- Security event logging
- Error tracking and analysis
- Log aggregation and analysis
"""

import logging
import json
import time
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict, deque

from ..config.settings import get_config


class LogLevel(str, Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Categories for log events."""
    AUTHENTICATION = "authentication"
    FILE_UPLOAD = "file_upload"
    PROCESSING = "processing"
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    API = "api"
    ERROR = "error"


@dataclass
class LogEvent:
    """Structured log event."""
    
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    
    # Context information
    user: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    
    # Additional data
    extra_data: Optional[Dict[str, Any]] = None
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log event to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert log event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class StructuredLogger:
    """
    Enhanced logger with structured logging capabilities.
    
    Features:
    - Structured log events with context
    - Performance tracking
    - Error aggregation
    - Security event logging
    - Log analysis and metrics
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically module name)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_events: deque = deque(maxlen=10000)  # Keep last 10k events in memory
        self.error_counts = defaultdict(int)
        self.performance_metrics = defaultdict(list)
        self._lock = threading.Lock()
        
        # Setup JSON formatter for structured logging
        self._setup_json_logging()
    
    def _setup_json_logging(self):
        """Setup JSON formatter for structured logging."""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, 'extra_data'):
                    log_data.update(record.extra_data)
                
                return json.dumps(log_data, default=str)
        
        # Add JSON handler if not already present
        json_handler = None
        for handler in self.logger.handlers:
            if isinstance(handler.formatter, JSONFormatter):
                json_handler = handler
                break
        
        if not json_handler:
            config = get_config()
            log_file = Path(config.files.temp_dir) / "batch_processor.json.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            json_handler = logging.FileHandler(log_file)
            json_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(json_handler)
    
    def _log_event(self, event: LogEvent):
        """Log a structured event."""
        with self._lock:
            self.log_events.append(event)
            
            # Track error counts
            if event.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                error_key = f"{event.category}:{event.error_type or 'unknown'}"
                self.error_counts[error_key] += 1
            
            # Track performance metrics
            if event.duration_ms is not None:
                self.performance_metrics[event.category].append(event.duration_ms)
        
        # Log to standard logger with extra context
        extra_data = {
            'category': event.category.value,
            'user': event.user,
            'session_id': event.session_id,
            'task_id': event.task_id,
            'duration_ms': event.duration_ms,
            'extra_data': event.extra_data
        }
        
        log_level = getattr(logging, event.level.value)
        self.logger.log(log_level, event.message, extra={'extra_data': extra_data})
    
    def log_authentication(
        self,
        user: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log authentication event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO if success else LogLevel.WARNING,
            category=LogCategory.AUTHENTICATION,
            message=f"Authentication {'successful' if success else 'failed'} for user {user}",
            user=user,
            extra_data={
                'success': success,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        )
        self._log_event(event)
    
    def log_file_upload(
        self,
        user: str,
        session_id: str,
        filename: str,
        file_size: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log file upload event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO if success else LogLevel.ERROR,
            category=LogCategory.FILE_UPLOAD,
            message=f"File upload {'successful' if success else 'failed'}: {filename}",
            user=user,
            session_id=session_id,
            extra_data={
                'filename': filename,
                'file_size_bytes': file_size,
                'success': success
            },
            error_message=error_message
        )
        self._log_event(event)
    
    def log_processing_start(
        self,
        task_id: str,
        session_id: str,
        user: str,
        filename: str,
        total_rows: int,
        algorithm: str,
        process_mode: str
    ):
        """Log processing start event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            category=LogCategory.PROCESSING,
            message=f"Started processing {filename} with {total_rows} rows using {algorithm}",
            user=user,
            session_id=session_id,
            task_id=task_id,
            extra_data={
                'filename': filename,
                'total_rows': total_rows,
                'algorithm': algorithm,
                'process_mode': process_mode
            }
        )
        self._log_event(event)
    
    def log_processing_progress(
        self,
        task_id: str,
        session_id: str,
        processed_rows: int,
        total_rows: int,
        error_count: int,
        duration_ms: float
    ):
        """Log processing progress event."""
        progress_percent = (processed_rows / total_rows) * 100 if total_rows > 0 else 0
        
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.DEBUG,
            category=LogCategory.PROCESSING,
            message=f"Processing progress: {processed_rows}/{total_rows} rows ({progress_percent:.1f}%)",
            session_id=session_id,
            task_id=task_id,
            duration_ms=duration_ms,
            extra_data={
                'processed_rows': processed_rows,
                'total_rows': total_rows,
                'error_count': error_count,
                'progress_percent': progress_percent
            }
        )
        self._log_event(event)
    
    def log_processing_complete(
        self,
        task_id: str,
        session_id: str,
        user: str,
        success: bool,
        processed_rows: int,
        error_count: int,
        duration_ms: float,
        output_file: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log processing completion event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO if success else LogLevel.ERROR,
            category=LogCategory.PROCESSING,
            message=f"Processing {'completed' if success else 'failed'}: {processed_rows} rows, {error_count} errors",
            user=user,
            session_id=session_id,
            task_id=task_id,
            duration_ms=duration_ms,
            extra_data={
                'success': success,
                'processed_rows': processed_rows,
                'error_count': error_count,
                'output_file': output_file
            },
            error_message=error_message
        )
        self._log_event(event)
    
    def log_api_request(
        self,
        method: str,
        endpoint: str,
        user: Optional[str],
        status_code: int,
        duration_ms: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Log API request event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            category=LogCategory.API,
            message=f"{method} {endpoint} -> {status_code} ({duration_ms:.1f}ms)",
            user=user,
            duration_ms=duration_ms,
            extra_data={
                'method': method,
                'endpoint': endpoint,
                'status_code': status_code,
                'request_size_bytes': request_size,
                'response_size_bytes': response_size
            }
        )
        self._log_event(event)
    
    def log_security_event(
        self,
        event_type: str,
        user: Optional[str],
        ip_address: Optional[str],
        description: str,
        severity: LogLevel = LogLevel.WARNING
    ):
        """Log security event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=severity,
            category=LogCategory.SECURITY,
            message=f"Security event: {event_type} - {description}",
            user=user,
            extra_data={
                'event_type': event_type,
                'ip_address': ip_address,
                'description': description
            }
        )
        self._log_event(event)
    
    def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """Log performance metric."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.DEBUG,
            category=LogCategory.PERFORMANCE,
            message=f"Performance: {operation} took {duration_ms:.1f}ms",
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            extra_data=extra_data
        )
        self._log_event(event)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        """Log error with full context and stack trace."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message=f"Error: {str(error)}",
            user=user,
            session_id=session_id,
            task_id=task_id,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            extra_data=context
        )
        self._log_event(event)
    
    def log_system_event(
        self,
        event_type: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """Log system event."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=level,
            category=LogCategory.SYSTEM,
            message=f"System: {event_type} - {message}",
            extra_data=extra_data
        )
        self._log_event(event)
    
    def log_admin_upload_initiation(
        self,
        user: str,
        upload_id: str,
        upload_type: str,
        filename: str,
        file_size: int,
        source_name: str,
        total_records: int
    ):
        """Log admin upload initiation."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            category=LogCategory.FILE_UPLOAD,
            message=f"Admin upload initiated: {upload_type} upload by {user}",
            user=user,
            session_id=upload_id,
            task_id=upload_id,
            extra_data={
                "upload_type": upload_type,
                "filename": filename,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "source_name": source_name,
                "total_records": total_records,
                "operation": "admin_upload_start"
            }
        )
        self._log_event(event)
    
    def log_admin_validation_failure(
        self,
        user: str,
        upload_id: str,
        upload_type: str,
        filename: str,
        error_type: str,
        error_details: Dict[str, Any]
    ):
        """Log admin upload validation failure."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.WARNING,
            category=LogCategory.FILE_UPLOAD,
            message=f"Admin upload validation failed: {error_type} for {filename}",
            user=user,
            session_id=upload_id,
            task_id=upload_id,
            error_type=error_type,
            error_message=error_details.get("message", "Unknown validation error"),
            extra_data={
                "upload_type": upload_type,
                "filename": filename,
                "error_type": error_type,
                "missing_columns": error_details.get("missing_columns", []),
                "supported_formats": error_details.get("supported_formats", []),
                "file_extension": error_details.get("file_extension"),
                "operation": "admin_validation_failure"
            }
        )
        self._log_event(event)
    
    def log_admin_processing_batch(
        self,
        upload_id: str,
        user: str,
        batch_number: int,
        processed_records: int,
        total_records: int,
        batch_size: int,
        duration_ms: float,
        error_count: int = 0
    ):
        """Log admin upload batch processing progress."""
        progress_percent = (processed_records / total_records) * 100 if total_records > 0 else 0
        
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.DEBUG,
            category=LogCategory.PROCESSING,
            message=f"Admin upload batch {batch_number} processed: {processed_records}/{total_records} records ({progress_percent:.1f}%)",
            user=user,
            session_id=upload_id,
            task_id=upload_id,
            duration_ms=duration_ms,
            extra_data={
                "batch_number": batch_number,
                "processed_records": processed_records,
                "total_records": total_records,
                "batch_size": batch_size,
                "progress_percent": progress_percent,
                "error_count": error_count,
                "records_per_second": (batch_size / duration_ms * 1000) if duration_ms > 0 else 0,
                "operation": "admin_batch_processing"
            }
        )
        self._log_event(event)
    
    def log_admin_upload_completion(
        self,
        user: str,
        upload_id: str,
        upload_type: str,
        filename: str,
        source_name: str,
        success: bool,
        total_records: int,
        successful_records: int,
        failed_records: int,
        processing_time_seconds: float,
        records_per_second: float,
        database_total_records: int,
        error_summary: Optional[Dict[str, int]] = None
    ):
        """Log admin upload completion with comprehensive statistics."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO if success else LogLevel.ERROR,
            category=LogCategory.PROCESSING,
            message=f"Admin upload {'completed' if success else 'failed'}: {successful_records}/{total_records} records processed",
            user=user,
            session_id=upload_id,
            task_id=upload_id,
            duration_ms=processing_time_seconds * 1000,
            extra_data={
                "upload_type": upload_type,
                "filename": filename,
                "source_name": source_name,
                "success": success,
                "total_records": total_records,
                "successful_records": successful_records,
                "failed_records": failed_records,
                "success_rate_percent": (successful_records / total_records * 100) if total_records > 0 else 0,
                "processing_time_seconds": processing_time_seconds,
                "records_per_second": records_per_second,
                "database_total_records": database_total_records,
                "error_summary": error_summary or {},
                "operation": "admin_upload_completion"
            }
        )
        self._log_event(event)
    
    def log_admin_error_context(
        self,
        user: str,
        upload_id: str,
        upload_type: str,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        filename: Optional[str] = None,
        processed_records: Optional[int] = None,
        total_records: Optional[int] = None
    ):
        """Log admin upload error with full context."""
        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message=f"Admin upload error: {error_type} - {error_message}",
            user=user,
            session_id=upload_id,
            task_id=upload_id,
            error_type=error_type,
            error_message=error_message,
            extra_data={
                "upload_type": upload_type,
                "filename": filename,
                "processed_records": processed_records,
                "total_records": total_records,
                "progress_percent": (processed_records / total_records * 100) if (processed_records and total_records) else 0,
                "context": context,
                "operation": "admin_upload_error"
            }
        )
        self._log_event(event)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                event for event in self.log_events
                if event.timestamp >= cutoff_time and event.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            ]
        
        error_types = defaultdict(int)
        error_categories = defaultdict(int)
        
        for event in recent_errors:
            error_types[event.error_type or 'unknown'] += 1
            error_categories[event.category.value] += 1
        
        return {
            'period_hours': hours,
            'total_errors': len(recent_errors),
            'error_types': dict(error_types),
            'error_categories': dict(error_categories),
            'error_rate_per_hour': len(recent_errors) / hours
        }
    
    def get_performance_summary(self, category: LogCategory, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for a specific category."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_events = [
                event for event in self.log_events
                if (event.timestamp >= cutoff_time and 
                    event.category == category and 
                    event.duration_ms is not None)
            ]
        
        if not recent_events:
            return {
                'category': category.value,
                'period_hours': hours,
                'total_operations': 0,
                'average_duration_ms': 0,
                'min_duration_ms': 0,
                'max_duration_ms': 0
            }
        
        durations = [event.duration_ms for event in recent_events]
        
        return {
            'category': category.value,
            'period_hours': hours,
            'total_operations': len(recent_events),
            'average_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'median_duration_ms': sorted(durations)[len(durations) // 2]
        }


class LoggingService:
    """
    Central logging service for the batch processor.
    
    Provides structured logging with context, performance tracking,
    and log analysis capabilities.
    """
    
    def __init__(self):
        """Initialize logging service."""
        self.loggers: Dict[str, StructuredLogger] = {}
        self._setup_root_logging()
    
    def _setup_root_logging(self):
        """Setup root logging configuration."""
        config = get_config()
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, config.web.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    Path(config.files.temp_dir) / "batch_processor.log",
                    encoding='utf-8'
                )
            ]
        )
        
        # Reduce noise from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('celery').setLevel(logging.INFO)
    
    def get_logger(self, name: str) -> StructuredLogger:
        """
        Get or create a structured logger for the specified name.
        
        Args:
            name: Logger name (typically module name)
            
        Returns:
            StructuredLogger instance
        """
        if name not in self.loggers:
            self.loggers[name] = StructuredLogger(name)
        return self.loggers[name]
    
    def get_system_log_summary(self) -> Dict[str, Any]:
        """Get system-wide log summary."""
        total_events = 0
        total_errors = 0
        categories = defaultdict(int)
        
        for logger in self.loggers.values():
            with logger._lock:
                total_events += len(logger.log_events)
                for event in logger.log_events:
                    categories[event.category.value] += 1
                    if event.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                        total_errors += 1
        
        return {
            'total_events': total_events,
            'total_errors': total_errors,
            'error_rate_percent': (total_errors / max(total_events, 1)) * 100,
            'events_by_category': dict(categories),
            'active_loggers': len(self.loggers)
        }


# Global logging service instance
_logging_service: Optional[LoggingService] = None


def get_logging_service() -> LoggingService:
    """Get the global logging service instance."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger for the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    return get_logging_service().get_logger(name)


# Import datetime for use in methods
from datetime import timedelta