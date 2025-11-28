"""
Search Result data model
"""

from dataclasses import dataclass


@dataclass
class SearchResult:
    """
    Represents a search result
    
    Attributes:
        code: ТНВЭД code
        description: Original description
        normalized_text: Normalized text
        similarity_score: Similarity score (0-1)
    """
    code: str
    description: str
    normalized_text: str
    similarity_score: float
    
    def __post_init__(self):
        """Validate result after initialization"""
        if not self.code:
            raise ValueError("ТНВЭД code cannot be empty")
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError(f"Similarity score must be between 0 and 1, got {self.similarity_score}")
