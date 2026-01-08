"""
Progress tracking service for real-time updates.

This module provides Redis-based progress tracking with WebSocket notification
publishing for real-time updates to web clients.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
import redis
import redis.asyncio as aioredis
from dataclasses import dataclass, asdict

from batch_processor.config.settings import get_config


logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Represents a progress update for a processing task."""
    
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    processed_rows: int
    total_rows: int
    error_count: int = 0
    stage: str = "processing"  # "validation", "processing", "finalizing"
    message: str = ""
    estimated_time_remaining: Optional[int] = None  # seconds
    timestamp: float = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressUpdate':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProgressUpdate':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


class ProgressTracker:
    """
    Redis-based progress tracking system with WebSocket notifications.
    
    This class manages progress updates for background processing tasks,
    storing progress data in Redis and publishing updates for real-time
    WebSocket notifications to web clients.
    
    Features:
    - Redis-based progress storage with TTL
    - WebSocket notification publishing
    - Progress history tracking
    - Automatic cleanup of expired progress data
    - Support for multiple concurrent tasks
    - Detailed progress metadata (stage, errors, time estimates)
    
    Attributes:
        redis_client: Redis client for data storage and pub/sub
        progress_ttl: Time-to-live for progress data in seconds
        channel_prefix: Prefix for Redis pub/sub channels
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize progress tracker.
        
        Args:
            redis_client: Redis client instance. If None, creates from config.
        """
        if redis_client is None:
            try:
                config = get_config()
                self.redis_client = redis.Redis.from_url(config.redis.url)
                # Test Redis connection
                self.redis_client.ping()
                logger.info("ProgressTracker initialized with Redis connection")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Progress tracking will be disabled.")
                self.redis_client = None
        else:
            self.redis_client = redis_client
        
        self.progress_ttl = 3600  # 1 hour TTL for progress data
        self.channel_prefix = "progress_channel"
        self.progress_key_prefix = "progress"
        self.history_key_prefix = "progress_history"
    
    def update_progress(
        self,
        task_id: str,
        status: str = "processing",
        progress: float = 0.0,
        processed_rows: int = 0,
        total_rows: int = 0,
        error_count: int = 0,
        stage: str = "processing",
        message: str = "",
        estimated_time_remaining: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Update progress for a task and publish notification.
        
        Args:
            task_id: Unique task identifier
            status: Task status ("pending", "processing", "completed", "failed")
            progress: Progress percentage (0.0 to 1.0)
            processed_rows: Number of rows processed
            total_rows: Total number of rows to process
            error_count: Number of processing errors
            stage: Current processing stage
            message: Human-readable progress message
            estimated_time_remaining: Estimated seconds remaining
            **kwargs: Additional metadata to include
        """
        if not (0.0 <= progress <= 1.0):
            raise ValueError("Progress must be between 0.0 and 1.0")
        
        if processed_rows < 0 or total_rows < 0 or error_count < 0:
            raise ValueError("Row counts must be non-negative")
        
        # If Redis is not available, just log the progress
        if self.redis_client is None:
            logger.info(
                f"Progress for task {task_id}: {progress:.1%} "
                f"({processed_rows}/{total_rows} rows, {error_count} errors) - {message}"
            )
            return
        
        # Create progress update
        update = ProgressUpdate(
            task_id=task_id,
            status=status,
            progress=progress,
            processed_rows=processed_rows,
            total_rows=total_rows,
            error_count=error_count,
            stage=stage,
            message=message,
            estimated_time_remaining=estimated_time_remaining
        )
        
        # Add any additional metadata
        update_dict = update.to_dict()
        update_dict.update(kwargs)
        
        try:
            # Store progress in Redis with TTL
            progress_key = f"{self.progress_key_prefix}:{task_id}"
            self.redis_client.setex(
                progress_key,
                self.progress_ttl,
                json.dumps(update_dict)
            )
            
            # Add to progress history
            self._add_to_history(task_id, update_dict)
            
            # Publish notification for WebSocket clients
            channel = f"{self.channel_prefix}:{task_id}"
            self.redis_client.publish(channel, json.dumps(update_dict))
            
            logger.debug(
                f"Progress updated for task {task_id}: {progress:.1%} "
                f"({processed_rows}/{total_rows} rows, {error_count} errors)"
            )
            
        except Exception as e:
            logger.error(f"Failed to update progress for task {task_id}: {e}")
            # Don't raise the exception, just log it to avoid breaking the processing
    
    async def get_progress_async(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current progress for a task (async version).
        
        Args:
            task_id: Task identifier
            
        Returns:
            Progress dictionary or None if not found
        """
        if self.redis_client is None:
            logger.debug(f"Redis not available, cannot get progress for task {task_id}")
            return None
            
        try:
            # Create async Redis client if needed
            if isinstance(self.redis_client, redis.Redis):
                config = get_config()
                async_client = aioredis.from_url(config.redis.url)
            else:
                async_client = self.redis_client
            
            progress_key = f"{self.progress_key_prefix}:{task_id}"
            data = await async_client.get(progress_key)
            
            if data is None:
                logger.debug(f"No progress data found for task {task_id}")
                return None
            
            progress_dict = json.loads(data)
            return progress_dict
            
        except Exception as e:
            logger.error(f"Failed to get progress for task {task_id}: {e}")
            return None

    def get_progress(self, task_id: str) -> Optional[ProgressUpdate]:
        """
        Get current progress for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            ProgressUpdate object or None if not found
        """
        if self.redis_client is None:
            logger.debug(f"Redis not available, cannot get progress for task {task_id}")
            return None
            
        try:
            progress_key = f"{self.progress_key_prefix}:{task_id}"
            data = self.redis_client.get(progress_key)
            
            if data is None:
                logger.debug(f"No progress data found for task {task_id}")
                return None
            
            progress_dict = json.loads(data)
            return ProgressUpdate.from_dict(progress_dict)
            
        except Exception as e:
            logger.error(f"Failed to get progress for task {task_id}: {e}")
            return None
    
    def get_progress_history(
        self, 
        task_id: str, 
        limit: int = 100
    ) -> List[ProgressUpdate]:
        """
        Get progress history for a task.
        
        Args:
            task_id: Task identifier
            limit: Maximum number of history entries to return
            
        Returns:
            List of ProgressUpdate objects in chronological order
        """
        try:
            history_key = f"{self.history_key_prefix}:{task_id}"
            
            # Get recent history entries
            history_data = self.redis_client.lrange(history_key, 0, limit - 1)
            
            history = []
            for data in history_data:
                try:
                    progress_dict = json.loads(data)
                    history.append(ProgressUpdate.from_dict(progress_dict))
                except Exception as e:
                    logger.warning(f"Failed to parse history entry: {e}")
                    continue
            
            # Sort by timestamp (oldest first)
            history.sort(key=lambda x: x.timestamp)
            
            logger.debug(f"Retrieved {len(history)} history entries for task {task_id}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get progress history for task {task_id}: {e}")
            return []
    
    def delete_progress(self, task_id: str) -> bool:
        """
        Delete progress data for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if data was deleted, False if not found
        """
        try:
            progress_key = f"{self.progress_key_prefix}:{task_id}"
            history_key = f"{self.history_key_prefix}:{task_id}"
            
            # Delete both current progress and history
            deleted_count = self.redis_client.delete(progress_key, history_key)
            
            if deleted_count > 0:
                logger.info(f"Deleted progress data for task {task_id}")
                return True
            else:
                logger.debug(f"No progress data found to delete for task {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete progress for task {task_id}: {e}")
            return False
    
    def get_all_active_tasks(self) -> List[str]:
        """
        Get list of all tasks with active progress tracking.
        
        Returns:
            List of task IDs with active progress data
        """
        try:
            pattern = f"{self.progress_key_prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            # Extract task IDs from keys
            task_ids = []
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                task_id = key_str.replace(f"{self.progress_key_prefix}:", "")
                task_ids.append(task_id)
            
            logger.debug(f"Found {len(task_ids)} active tasks")
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return []
    
    def cleanup_expired_progress(self) -> int:
        """
        Clean up expired progress data.
        
        This method is typically called by a periodic cleanup task
        to remove old progress data that has exceeded its TTL.
        
        Returns:
            Number of expired entries cleaned up
        """
        try:
            cleaned_count = 0
            
            # Get all progress keys
            progress_pattern = f"{self.progress_key_prefix}:*"
            history_pattern = f"{self.history_key_prefix}:*"
            
            progress_keys = self.redis_client.keys(progress_pattern)
            history_keys = self.redis_client.keys(history_pattern)
            
            # Check each progress key for expiration
            for key in progress_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    cleaned_count += 1
            
            # Clean up orphaned history keys (where progress key is gone)
            for history_key in history_keys:
                key_str = history_key.decode('utf-8') if isinstance(history_key, bytes) else history_key
                task_id = key_str.replace(f"{self.history_key_prefix}:", "")
                progress_key = f"{self.progress_key_prefix}:{task_id}"
                
                if not self.redis_client.exists(progress_key):
                    self.redis_client.delete(history_key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired progress entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired progress: {e}")
            return 0
    
    def subscribe_to_progress(self, task_id: str):
        """
        Subscribe to progress updates for a specific task.
        
        This method returns a Redis pubsub object that can be used
        to listen for real-time progress updates.
        
        Args:
            task_id: Task identifier to subscribe to
            
        Returns:
            Redis pubsub object
        """
        try:
            pubsub = self.redis_client.pubsub()
            channel = f"{self.channel_prefix}:{task_id}"
            pubsub.subscribe(channel)
            
            logger.debug(f"Subscribed to progress updates for task {task_id}")
            return pubsub
            
        except Exception as e:
            logger.error(f"Failed to subscribe to progress for task {task_id}: {e}")
            raise
    
    def _add_to_history(self, task_id: str, progress_dict: Dict[str, Any]) -> None:
        """
        Add progress update to history.
        
        Args:
            task_id: Task identifier
            progress_dict: Progress data dictionary
        """
        try:
            history_key = f"{self.history_key_prefix}:{task_id}"
            
            # Add to list (newest first)
            self.redis_client.lpush(history_key, json.dumps(progress_dict))
            
            # Trim to keep only recent entries (max 1000)
            self.redis_client.ltrim(history_key, 0, 999)
            
            # Set TTL for history (longer than progress TTL)
            self.redis_client.expire(history_key, self.progress_ttl * 2)
            
        except Exception as e:
            logger.warning(f"Failed to add progress to history: {e}")
    
    def create_task_started_update(
        self,
        task_id: str,
        total_rows: int,
        message: str = "Task started"
    ) -> None:
        """
        Create initial progress update when task starts.
        
        Args:
            task_id: Task identifier
            total_rows: Total number of rows to process
            message: Initial message
        """
        self.update_progress(
            task_id=task_id,
            status="processing",
            progress=0.0,
            processed_rows=0,
            total_rows=total_rows,
            error_count=0,
            stage="starting",
            message=message
        )
    
    def create_task_completed_update(
        self,
        task_id: str,
        processed_rows: int,
        error_count: int,
        message: str = "Task completed"
    ) -> None:
        """
        Create final progress update when task completes.
        
        Args:
            task_id: Task identifier
            processed_rows: Number of rows processed
            error_count: Number of errors encountered
            message: Completion message
        """
        self.update_progress(
            task_id=task_id,
            status="completed",
            progress=1.0,
            processed_rows=processed_rows,
            total_rows=processed_rows,
            error_count=error_count,
            stage="completed",
            message=message,
            estimated_time_remaining=0
        )
    
    def create_task_failed_update(
        self,
        task_id: str,
        error_message: str,
        processed_rows: int = 0
    ) -> None:
        """
        Create progress update when task fails.
        
        Args:
            task_id: Task identifier
            error_message: Error message
            processed_rows: Number of rows processed before failure
        """
        self.update_progress(
            task_id=task_id,
            status="failed",
            progress=0.0,
            processed_rows=processed_rows,
            total_rows=0,
            error_count=1,
            stage="failed",
            message=f"Task failed: {error_message}",
            estimated_time_remaining=None
        )


# Global progress tracker instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """
    Get the global progress tracker instance.
    
    Returns:
        ProgressTracker instance
    """
    global _progress_tracker
    if _progress_tracker is None:
        try:
            _progress_tracker = ProgressTracker()
        except Exception as e:
            logger.warning(f"Failed to create progress tracker: {e}. Creating fallback instance.")
            # Create a fallback instance with no Redis client
            _progress_tracker = ProgressTracker(redis_client=None)
    return _progress_tracker


def set_progress_tracker(tracker: ProgressTracker) -> None:
    """
    Set the global progress tracker instance.
    
    Args:
        tracker: ProgressTracker instance to use globally
    """
    global _progress_tracker
    _progress_tracker = tracker