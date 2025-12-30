"""
Monitoring and metrics collection service for batch Excel processor.

This module provides comprehensive monitoring capabilities including:
- Performance metrics collection
- System health monitoring
- Processing statistics tracking
- Resource usage monitoring
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json
import threading
from collections import defaultdict, deque

from ..config.settings import get_config


logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for a single processing operation."""
    
    task_id: str
    session_id: str
    user: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # File metrics
    file_size_bytes: int = 0
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    error_count: int = 0
    
    # Processing configuration
    algorithm: str = ""
    process_mode: str = ""
    chunk_size: int = 0
    
    # Performance metrics
    processing_time_seconds: float = 0.0
    average_time_per_row_ms: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Quality metrics
    confidence_scores: List[float] = field(default_factory=list)
    average_confidence: float = 0.0
    low_confidence_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'session_id': self.session_id,
            'user': self.user,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'file_size_bytes': self.file_size_bytes,
            'total_rows': self.total_rows,
            'processed_rows': self.processed_rows,
            'successful_rows': self.successful_rows,
            'error_count': self.error_count,
            'algorithm': self.algorithm,
            'process_mode': self.process_mode,
            'chunk_size': self.chunk_size,
            'processing_time_seconds': self.processing_time_seconds,
            'average_time_per_row_ms': self.average_time_per_row_ms,
            'peak_memory_mb': self.peak_memory_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'average_confidence': self.average_confidence,
            'low_confidence_count': self.low_confidence_count
        }


@dataclass
class SystemMetrics:
    """System-wide metrics and health indicators."""
    
    timestamp: datetime
    
    # System resources
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_gb: float = 0.0
    disk_usage_percent: float = 0.0
    disk_free_gb: float = 0.0
    
    # Application metrics
    active_tasks: int = 0
    queued_tasks: int = 0
    completed_tasks_24h: int = 0
    failed_tasks_24h: int = 0
    
    # Performance metrics
    average_processing_time_minutes: float = 0.0
    total_files_processed: int = 0
    total_rows_processed: int = 0
    
    # Storage metrics
    temp_files_count: int = 0
    temp_files_size_gb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_available_gb': self.memory_available_gb,
            'disk_usage_percent': self.disk_usage_percent,
            'disk_free_gb': self.disk_free_gb,
            'active_tasks': self.active_tasks,
            'queued_tasks': self.queued_tasks,
            'completed_tasks_24h': self.completed_tasks_24h,
            'failed_tasks_24h': self.failed_tasks_24h,
            'average_processing_time_minutes': self.average_processing_time_minutes,
            'total_files_processed': self.total_files_processed,
            'total_rows_processed': self.total_rows_processed,
            'temp_files_count': self.temp_files_count,
            'temp_files_size_gb': self.temp_files_size_gb
        }


class MetricsCollector:
    """
    Collects and manages performance metrics for the batch processor.
    
    Features:
    - Real-time system metrics collection
    - Processing operation tracking
    - Historical data retention
    - Performance analytics
    """
    
    def __init__(self, retention_hours: int = 168):  # 7 days default
        """
        Initialize metrics collector.
        
        Args:
            retention_hours: How long to retain metrics data
        """
        self.retention_hours = retention_hours
        self.processing_metrics: Dict[str, ProcessingMetrics] = {}
        self.system_metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 system snapshots
        self.task_counters = defaultdict(int)
        self.performance_history = deque(maxlen=100)  # Keep last 100 processing operations
        self._lock = threading.Lock()
        
        # Start background metrics collection
        self._start_system_monitoring()
        
        logger.info("Metrics collector initialized")
    
    def _start_system_monitoring(self):
        """Start background thread for system metrics collection."""
        def collect_system_metrics():
            while True:
                try:
                    metrics = self._collect_system_metrics()
                    with self._lock:
                        self.system_metrics_history.append(metrics)
                    time.sleep(60)  # Collect every minute
                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
        logger.info("System monitoring thread started")
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        config = get_config()
        
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(config.files.temp_dir)
        
        # Temp files statistics
        temp_dir = Path(config.files.temp_dir)
        temp_files_count = 0
        temp_files_size = 0
        
        if temp_dir.exists():
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    temp_files_count += 1
                    temp_files_size += file_path.stat().st_size
        
        # Task statistics (from recent history)
        now = datetime.utcnow()
        cutoff_24h = now - timedelta(hours=24)
        
        completed_24h = 0
        failed_24h = 0
        total_processing_time = 0
        
        with self._lock:
            for metrics in self.performance_history:
                if metrics.start_time >= cutoff_24h:
                    if metrics.end_time:
                        if metrics.error_count == 0:
                            completed_24h += 1
                        else:
                            failed_24h += 1
                        total_processing_time += metrics.processing_time_seconds
        
        avg_processing_time = (total_processing_time / max(completed_24h + failed_24h, 1)) / 60.0
        
        return SystemMetrics(
            timestamp=now,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_gb=memory.available / (1024**3),
            disk_usage_percent=disk.percent,
            disk_free_gb=disk.free / (1024**3),
            active_tasks=len([m for m in self.processing_metrics.values() if m.end_time is None]),
            queued_tasks=0,  # Would need Celery integration to get actual queue size
            completed_tasks_24h=completed_24h,
            failed_tasks_24h=failed_24h,
            average_processing_time_minutes=avg_processing_time,
            total_files_processed=len(self.performance_history),
            total_rows_processed=sum(m.processed_rows for m in self.performance_history),
            temp_files_count=temp_files_count,
            temp_files_size_gb=temp_files_size / (1024**3)
        )
    
    def start_processing_metrics(
        self,
        task_id: str,
        session_id: str,
        user: str,
        file_size_bytes: int,
        total_rows: int,
        algorithm: str,
        process_mode: str,
        chunk_size: int
    ) -> None:
        """
        Start tracking metrics for a processing operation.
        
        Args:
            task_id: Unique task identifier
            session_id: Session identifier
            user: Username
            file_size_bytes: Size of input file
            total_rows: Total rows in file
            algorithm: Processing algorithm used
            process_mode: Processing mode
            chunk_size: Chunk size for processing
        """
        metrics = ProcessingMetrics(
            task_id=task_id,
            session_id=session_id,
            user=user,
            start_time=datetime.utcnow(),
            file_size_bytes=file_size_bytes,
            total_rows=total_rows,
            algorithm=algorithm,
            process_mode=process_mode,
            chunk_size=chunk_size
        )
        
        with self._lock:
            self.processing_metrics[task_id] = metrics
            self.task_counters['started'] += 1
        
        logger.info(
            f"Started metrics tracking for task {task_id}: "
            f"file_size={file_size_bytes}, rows={total_rows}, algorithm={algorithm}"
        )
    
    def update_processing_progress(
        self,
        task_id: str,
        processed_rows: int,
        successful_rows: int,
        error_count: int,
        confidence_scores: Optional[List[float]] = None
    ) -> None:
        """
        Update processing progress metrics.
        
        Args:
            task_id: Task identifier
            processed_rows: Number of rows processed so far
            successful_rows: Number of successfully processed rows
            error_count: Number of errors encountered
            confidence_scores: List of confidence scores for quality tracking
        """
        with self._lock:
            if task_id in self.processing_metrics:
                metrics = self.processing_metrics[task_id]
                metrics.processed_rows = processed_rows
                metrics.successful_rows = successful_rows
                metrics.error_count = error_count
                
                if confidence_scores:
                    metrics.confidence_scores.extend(confidence_scores)
                    metrics.average_confidence = sum(metrics.confidence_scores) / len(metrics.confidence_scores)
                    metrics.low_confidence_count = sum(1 for score in metrics.confidence_scores if score < 0.7)
                
                # Update system resource usage
                try:
                    process = psutil.Process()
                    memory_info = process.memory_info()
                    metrics.peak_memory_mb = max(metrics.peak_memory_mb, memory_info.rss / (1024**2))
                    metrics.cpu_usage_percent = process.cpu_percent()
                except:
                    pass  # Ignore errors in resource monitoring
    
    def complete_processing_metrics(
        self,
        task_id: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Complete metrics tracking for a processing operation.
        
        Args:
            task_id: Task identifier
            success: Whether processing completed successfully
            error_message: Error message if processing failed
        """
        with self._lock:
            if task_id in self.processing_metrics:
                metrics = self.processing_metrics[task_id]
                metrics.end_time = datetime.utcnow()
                
                if metrics.start_time:
                    metrics.processing_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
                    
                    if metrics.processed_rows > 0:
                        metrics.average_time_per_row_ms = (metrics.processing_time_seconds * 1000) / metrics.processed_rows
                
                # Add to performance history
                self.performance_history.append(metrics)
                
                # Update counters
                if success:
                    self.task_counters['completed'] += 1
                else:
                    self.task_counters['failed'] += 1
                
                logger.info(
                    f"Completed metrics for task {task_id}: "
                    f"success={success}, time={metrics.processing_time_seconds:.2f}s, "
                    f"rows={metrics.processed_rows}, errors={metrics.error_count}"
                )
                
                if error_message:
                    logger.error(f"Task {task_id} failed: {error_message}")
    
    def get_processing_metrics(self, task_id: str) -> Optional[ProcessingMetrics]:
        """Get metrics for a specific processing task."""
        with self._lock:
            return self.processing_metrics.get(task_id)
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        return self._collect_system_metrics()
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with performance statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_metrics = [
                m for m in self.performance_history 
                if m.start_time >= cutoff_time and m.end_time is not None
            ]
        
        if not recent_metrics:
            return {
                'period_hours': hours,
                'total_tasks': 0,
                'successful_tasks': 0,
                'failed_tasks': 0,
                'total_files_processed': 0,
                'total_rows_processed': 0,
                'average_processing_time_seconds': 0,
                'average_confidence_score': 0,
                'total_processing_time_hours': 0
            }
        
        successful_tasks = [m for m in recent_metrics if m.error_count == 0]
        failed_tasks = [m for m in recent_metrics if m.error_count > 0]
        
        total_processing_time = sum(m.processing_time_seconds for m in recent_metrics)
        total_rows = sum(m.processed_rows for m in recent_metrics)
        
        all_confidence_scores = []
        for m in recent_metrics:
            all_confidence_scores.extend(m.confidence_scores)
        
        return {
            'period_hours': hours,
            'total_tasks': len(recent_metrics),
            'successful_tasks': len(successful_tasks),
            'failed_tasks': len(failed_tasks),
            'success_rate_percent': (len(successful_tasks) / len(recent_metrics)) * 100,
            'total_files_processed': len(recent_metrics),
            'total_rows_processed': total_rows,
            'average_processing_time_seconds': total_processing_time / len(recent_metrics),
            'average_rows_per_minute': (total_rows / (total_processing_time / 60)) if total_processing_time > 0 else 0,
            'average_confidence_score': sum(all_confidence_scores) / len(all_confidence_scores) if all_confidence_scores else 0,
            'total_processing_time_hours': total_processing_time / 3600
        }
    
    def cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            # Clean up completed processing metrics
            to_remove = [
                task_id for task_id, metrics in self.processing_metrics.items()
                if metrics.end_time and metrics.end_time < cutoff_time
            ]
            
            for task_id in to_remove:
                del self.processing_metrics[task_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old processing metrics")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def initialize_metrics_collector(retention_hours: int = 168) -> MetricsCollector:
    """
    Initialize the global metrics collector.
    
    Args:
        retention_hours: How long to retain metrics data
        
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    _metrics_collector = MetricsCollector(retention_hours)
    return _metrics_collector