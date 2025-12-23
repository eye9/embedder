"""
Product Record data model
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductRecord:
    """
    Represents a product record with assigned ТНВЭД code
    
    Attributes:
        code: ТНВЭД code assigned to the product
        description: Product description
        normalized_text: Normalized text for search
        source_name: Name of the source (e.g., "customs_2024_q1")
        source_id: Optional ID in source system (e.g., "декларация_12345")
    """
    code: str
    description: str
    normalized_text: str
    source_name: str
    source_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate record after initialization"""
        if not self.code:
            raise ValueError("ТНВЭД code cannot be empty")
        if not self.description:
            raise ValueError("Product description cannot be empty")
        if not self.source_name:
            raise ValueError("Source name cannot be empty")