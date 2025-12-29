"""Processing session data model."""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


@dataclass
class ProcessingSession:
    """Represents a user's file processing session."""
    
    session_id: str
    user_id: str
    created_at: datetime
    original_filename: str
    file_path: Path
    process_mode: str      # "all" or "empty_only"
    algorithm: str         # "similarity_top1" or "llm_reasoning"
    task_id: Optional[str] = None
    status: str = "created"  # "created", "processing", "completed", "failed"
    
    def __post_init__(self):
        """Validate the session data after initialization."""
        if self.process_mode not in ["all", "empty_only"]:
            raise ValueError(f"Invalid process_mode: {self.process_mode}. Must be 'all' or 'empty_only'")
        
        if self.algorithm not in ["similarity_top1", "llm_reasoning"]:
            raise ValueError(f"Invalid algorithm: {self.algorithm}. Must be 'similarity_top1' or 'llm_reasoning'")
        
        if self.status not in ["created", "processing", "completed", "failed"]:
            raise ValueError(f"Invalid status: {self.status}. Must be one of: created, processing, completed, failed")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        data = asdict(self)
        # Convert Path to string for JSON serialization
        data['file_path'] = str(self.file_path)
        # Convert datetime to ISO format
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingSession':
        """Create session from dictionary."""
        # Convert string back to Path
        data['file_path'] = Path(data['file_path'])
        # Convert ISO string back to datetime
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert session to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessingSession':
        """Create session from JSON string."""
        return cls.from_dict(json.loads(json_str))