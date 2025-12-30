"""
TNVED Code Selection Service

This module provides abstract base class and factory for TNVED code selection algorithms.
Different algorithms can be implemented to select the most appropriate TNVED code
for a given product description.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time

from batch_processor.models.result import ProcessingResult


logger = logging.getLogger(__name__)


class TNVEDSelector(ABC):
    """
    Abstract base class for TNVED code selection algorithms.
    
    This class defines the interface that all TNVED code selection algorithms
    must implement. Different algorithms can use various approaches such as:
    - Similarity-based selection (highest score)
    - LLM-based reasoning and analysis
    - Rule-based selection with business logic
    - Hybrid approaches combining multiple methods
    """
    
    @abstractmethod
    def select_code(self, description: str, row_index: int = 0) -> ProcessingResult:
        """
        Select the most appropriate TNVED code for a product description.
        
        Args:
            description: Product description text to analyze
            row_index: Row index in the source file (for tracking)
            
        Returns:
            ProcessingResult with selected code and reasoning
            
        Raises:
            ValueError: If description is empty or invalid
            Exception: If selection process fails
        """
        pass
    
    def get_algorithm_name(self) -> str:
        """
        Get the name of this selection algorithm.
        
        Returns:
            String identifier for this algorithm
        """
        return self.__class__.__name__


class SelectorFactory:
    """
    Factory class for creating TNVED code selector instances.
    
    This factory provides a centralized way to create different types of
    TNVED selectors based on algorithm configuration. It handles the
    instantiation and configuration of selectors with their dependencies.
    """
    
    # Registry of available selector classes
    _selectors: Dict[str, type] = {}
    
    @classmethod
    def register_selector(cls, algorithm_name: str, selector_class: type) -> None:
        """
        Register a new selector algorithm.
        
        Args:
            algorithm_name: String identifier for the algorithm
            selector_class: Class that implements TNVEDSelector interface
        """
        if not issubclass(selector_class, TNVEDSelector):
            raise ValueError(
                f"Selector class {selector_class.__name__} must inherit from TNVEDSelector"
            )
        
        cls._selectors[algorithm_name] = selector_class
        logger.info(f"Registered selector algorithm: {algorithm_name}")
    
    @classmethod
    def create_selector(
        cls, 
        algorithm: str, 
        tnved_searcher=None,
        **kwargs
    ) -> TNVEDSelector:
        """
        Create a TNVED selector instance for the specified algorithm.
        
        Args:
            algorithm: Algorithm name ("similarity_top1" or "llm_reasoning")
            tnved_searcher: TNVEDSearcher instance (required for most algorithms)
            **kwargs: Additional configuration parameters for the selector
            
        Returns:
            TNVEDSelector instance configured for the specified algorithm
            
        Raises:
            ValueError: If algorithm is unknown or required parameters are missing
            
        Examples:
            >>> factory = SelectorFactory()
            >>> selector = factory.create_selector(
            ...     "similarity_top1",
            ...     tnved_searcher=searcher,
            ...     confidence_threshold=0.7
            ... )
        """
        if algorithm not in cls._selectors:
            available = list(cls._selectors.keys())
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. Available algorithms: {available}"
            )
        
        selector_class = cls._selectors[algorithm]
        
        # Most selectors require a TNVEDSearcher instance
        if tnved_searcher is None:
            logger.warning(
                f"Creating {algorithm} selector without tnved_searcher. "
                "This may cause runtime errors if the selector requires it."
            )
        
        try:
            # Create selector instance with provided parameters
            selector = selector_class(tnved_searcher=tnved_searcher, **kwargs)
            logger.info(f"Created {algorithm} selector: {selector_class.__name__}")
            return selector
            
        except Exception as e:
            error_msg = f"Failed to create {algorithm} selector: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    @classmethod
    def get_available_algorithms(cls) -> list:
        """
        Get list of available algorithm names.
        
        Returns:
            List of registered algorithm names
        """
        return list(cls._selectors.keys())
    
    @classmethod
    def is_algorithm_available(cls, algorithm: str) -> bool:
        """
        Check if an algorithm is available.
        
        Args:
            algorithm: Algorithm name to check
            
        Returns:
            True if algorithm is registered, False otherwise
        """
        return algorithm in cls._selectors


def create_processing_result_with_error(
    row_index: int,
    description: str,
    error_message: str,
    processing_time_ms: Optional[float] = None
) -> ProcessingResult:
    """
    Helper function to create a ProcessingResult for error cases.
    
    Args:
        row_index: Row index in the source file
        description: Original product description
        error_message: Error message explaining the failure
        processing_time_ms: Time taken for processing attempt
        
    Returns:
        ProcessingResult with error information
    """
    return ProcessingResult(
        row_index=row_index,
        original_description=description,
        tnved_code=None,
        selection_reason=f"Error: {error_message}",
        confidence_score=None,
        processing_time_ms=processing_time_ms,
        error_message=error_message
    )


def measure_processing_time(func):
    """
    Decorator to measure processing time for selector methods.
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapper function that measures execution time
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            processing_time_ms = (end_time - start_time) * 1000
            
            # Update processing time if result is ProcessingResult
            if isinstance(result, ProcessingResult):
                result.processing_time_ms = processing_time_ms
            
            return result
        except Exception as e:
            end_time = time.time()
            processing_time_ms = (end_time - start_time) * 1000
            logger.error(f"Processing failed after {processing_time_ms:.2f}ms: {e}")
            raise
    
    return wrapper