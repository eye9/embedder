"""Processing result data model."""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class ProcessingResult:
    """Represents the result of processing a single row."""
    
    row_index: int
    original_description: str
    tnved_code: Optional[str]
    selection_reason: str
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate the result data after initialization."""
        if self.row_index < 0:
            raise ValueError("row_index must be non-negative")
        
        if not self.original_description.strip():
            raise ValueError("original_description cannot be empty")
        
        if not self.selection_reason.strip():
            raise ValueError("selection_reason cannot be empty")
        
        if self.confidence_score is not None and not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        
        if self.processing_time_ms is not None and self.processing_time_ms < 0:
            raise ValueError("processing_time_ms must be non-negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingResult':
        """Create result from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessingResult':
        """Create result from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def is_successful(self) -> bool:
        """Check if the processing was successful (found a TNVED code)."""
        return self.tnved_code is not None and self.error_message is None
    
    def has_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if the result has high confidence score."""
        return (self.confidence_score is not None and 
                self.confidence_score >= threshold)