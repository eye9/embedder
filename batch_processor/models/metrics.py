"""Task metrics data model."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class TaskMetrics:
    """Represents metrics for a processing task."""
    
    task_id: str
    total_rows: int
    processed_rows: int
    successful_rows: int
    error_count: int
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    average_time_per_row_ms: Optional[float] = None
    
    def __post_init__(self):
        """Validate the metrics data after initialization."""
        if self.total_rows < 0:
            raise ValueError("total_rows must be non-negative")
        
        if self.processed_rows < 0:
            raise ValueError("processed_rows must be non-negative")
        
        if self.successful_rows < 0:
            raise ValueError("successful_rows must be non-negative")
        
        if self.error_count < 0:
            raise ValueError("error_count must be non-negative")
        
        if self.processed_rows > self.total_rows:
            raise ValueError("processed_rows cannot exceed total_rows")
        
        if self.successful_rows > self.processed_rows:
            raise ValueError("successful_rows cannot exceed processed_rows")
        
        if self.successful_rows + self.error_count != self.processed_rows:
            raise ValueError("successful_rows + error_count must equal processed_rows")
        
        if self.processing_time_seconds is not None and self.processing_time_seconds < 0:
            raise ValueError("processing_time_seconds must be non-negative")
        
        if self.average_time_per_row_ms is not None and self.average_time_per_row_ms < 0:
            raise ValueError("average_time_per_row_ms must be non-negative")
    
    def calculate_completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_rows == 0:
            return 100.0
        return (self.processed_rows / self.total_rows) * 100.0
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.processed_rows == 0:
            return 0.0
        return (self.successful_rows / self.processed_rows) * 100.0
    
    def calculate_error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.processed_rows == 0:
            return 0.0
        return (self.error_count / self.processed_rows) * 100.0
    
    def update_timing(self) -> None:
        """Update timing calculations when end_time is set."""
        if self.end_time is not None:
            self.processing_time_seconds = (self.end_time - self.start_time).total_seconds()
            
            if self.processed_rows > 0 and self.processing_time_seconds > 0:
                self.average_time_per_row_ms = (self.processing_time_seconds * 1000) / self.processed_rows
    
    def is_complete(self) -> bool:
        """Check if the task is complete."""
        return self.processed_rows >= self.total_rows
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        data['start_time'] = self.start_time.isoformat()
        if self.end_time is not None:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMetrics':
        """Create metrics from dictionary."""
        # Convert ISO string back to datetime
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert metrics to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TaskMetrics':
        """Create metrics from JSON string."""
        return cls.from_dict(json.loads(json_str))