"""
ТНВЭД Record data model
"""

from dataclasses import dataclass


@dataclass
class TNVEDRecord:
    """
    Represents a ТНВЭД record
    
    Attributes:
        code: ТНВЭД code (unique identifier)
        text_ex: Original description from TextEx column
        normalized_text: Normalized text for search
    """
    code: str
    text_ex: str
    normalized_text: str
    
    def __post_init__(self):
        """Validate record after initialization"""
        if not self.code:
            raise ValueError("ТНВЭД code cannot be empty")
        if not self.text_ex:
            raise ValueError("TextEx description cannot be empty")
