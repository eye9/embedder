"""
Search Result data model
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SourceType(Enum):
    """Enumeration for source types"""
    REFERENCE = "reference"
    PRODUCT = "product"


@dataclass
class SearchResult:
    """
    Represents a search result
    
    Attributes:
        code: ТНВЭД code
        description: Original description
        normalized_text: Normalized text
        similarity_score: Similarity score (0-1)
        source_type: Type of source (reference or product)
        source_name: Name of the source (optional)
        source_id: ID in source system (optional)
    """
    code: str
    description: str
    normalized_text: str
    similarity_score: float
    source_type: str
    source_name: Optional[str] = None
    source_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate result after initialization"""
        if not self.code:
            raise ValueError("ТНВЭД code cannot be empty")
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError(f"Similarity score must be between 0 and 1, got {self.similarity_score}")
        if self.source_type not in [SourceType.REFERENCE.value, SourceType.PRODUCT.value]:
            raise ValueError(f"Invalid source_type: {self.source_type}. Must be 'reference' or 'product'")
