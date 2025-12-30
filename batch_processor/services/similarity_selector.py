"""
Similarity-based TNVED Code Selection

This module implements TNVED code selection based on similarity scores.
It selects the code with the highest similarity score from the search results.
"""

import logging
from typing import Optional

from batch_processor.models.result import ProcessingResult
from batch_processor.services.tnved_selector import (
    TNVEDSelector, 
    create_processing_result_with_error,
    measure_processing_time
)
from batch_processor.services.tnved_code_utils import get_tnved_code_from_search_result
from services.tnved_searcher import TNVEDSearcher, SearchError


logger = logging.getLogger(__name__)


class SimilarityTop1Selector(TNVEDSelector):
    """
    TNVED code selector that chooses the result with highest similarity score.
    
    This selector integrates with the existing TNVEDSearcher to find potential
    TNVED codes and selects the one with the highest similarity score. It includes
    confidence threshold handling and quality indicators in the selection reasoning.
    
    Features:
    - Selects code with highest similarity score
    - Configurable confidence threshold for quality assessment
    - Detailed selection reasoning with score and source information
    - Quality indicators (Low Confidence, High Confidence)
    - Graceful error handling for search failures
    
    Attributes:
        tnved_searcher: TNVEDSearcher instance for code lookup
        confidence_threshold: Minimum confidence score for quality assessment
        top_k: Number of results to retrieve from search (default: 5)
    """
    
    def __init__(
        self, 
        tnved_searcher: TNVEDSearcher,
        confidence_threshold: float = 0.7,
        top_k: int = 5
    ):
        """
        Initialize similarity-based selector.
        
        Args:
            tnved_searcher: TNVEDSearcher instance for performing searches
            confidence_threshold: Minimum score for high confidence (0.0-1.0)
            top_k: Number of search results to consider
            
        Raises:
            ValueError: If parameters are invalid
        """
        if tnved_searcher is None:
            raise ValueError("tnved_searcher is required")
        
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        
        self.tnved_searcher = tnved_searcher
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        
        logger.info(
            f"SimilarityTop1Selector initialized with "
            f"confidence_threshold={confidence_threshold}, top_k={top_k}"
        )
    
    @measure_processing_time
    def select_code(self, description: str, row_index: int = 0) -> ProcessingResult:
        """
        Select TNVED code with highest similarity score.
        
        Searches for potential TNVED codes using the description and selects
        the one with the highest similarity score. Includes quality assessment
        and detailed reasoning in the result.
        
        Args:
            description: Product description to analyze
            row_index: Row index in source file for tracking
            
        Returns:
            ProcessingResult with selected code and detailed reasoning
            
        Raises:
            ValueError: If description is empty or invalid
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")
        
        description = description.strip()
        logger.debug(f"Selecting code for description: '{description[:100]}...'")
        
        try:
            # Search for potential TNVED codes
            search_results = self.tnved_searcher.search(
                query=description,
                top_k=self.top_k
            )
            
            # Handle case where no results found
            if not search_results:
                return ProcessingResult(
                    row_index=row_index,
                    original_description=description,
                    tnved_code=None,
                    selection_reason=(
                        "No matching TNVED codes found. "
                        "Manual review recommended for this product description."
                    ),
                    confidence_score=0.0
                )
            
            # Select the top result (highest similarity score)
            top_result = search_results[0]
            
            # Extract clean TNVED code (remove sequence numbers like _003)
            clean_tnved_code = get_tnved_code_from_search_result(top_result)
            
            if not clean_tnved_code:
                return ProcessingResult(
                    row_index=row_index,
                    original_description=description,
                    tnved_code=None,
                    selection_reason=(
                        f"Found result {top_result.code} but could not extract valid TNVED code. "
                        "TNVED codes must be exactly 10 digits."
                    ),
                    confidence_score=top_result.similarity_score
                )
            
            # Format selection reason with detailed information
            selection_reason = self._format_selection_reason(
                top_result, 
                search_results,
                description,
                clean_tnved_code
            )
            
            # Determine confidence level
            confidence_score = top_result.similarity_score
            
            logger.debug(
                f"Selected code {top_result.code} with score {confidence_score:.3f}"
            )
            
            return ProcessingResult(
                row_index=row_index,
                original_description=description,
                tnved_code=clean_tnved_code,  # Use clean code instead of database identifier
                selection_reason=selection_reason,
                confidence_score=confidence_score
            )
            
        except SearchError as e:
            error_msg = f"Search failed: {e}"
            logger.error(error_msg)
            return create_processing_result_with_error(
                row_index=row_index,
                description=description,
                error_message=error_msg
            )
        
        except Exception as e:
            error_msg = f"Code selection failed: {e}"
            logger.error(error_msg, exc_info=True)
            return create_processing_result_with_error(
                row_index=row_index,
                description=description,
                error_message=error_msg
            )
    
    def _format_selection_reason(
        self, 
        top_result, 
        all_results, 
        original_description: str,
        clean_tnved_code: str
    ) -> str:
        """
        Format detailed selection reasoning.
        
        Creates a comprehensive explanation of why this code was selected,
        including similarity score, source information, and quality indicators.
        
        Args:
            top_result: The selected search result
            all_results: All search results for context
            original_description: Original product description
            clean_tnved_code: Clean 10-digit TNVED code
            
        Returns:
            Formatted selection reason string
        """
        # Basic selection information
        reason_parts = [
            f"Code: {clean_tnved_code}",  # Use clean code in reason
            f"Similarity Score: {top_result.similarity_score:.3f}",
            f"Source: {top_result.source_name or 'TNVED Database'}",
            f"Description: {top_result.description[:200]}..."
        ]
        
        # Add database identifier for reference if different from clean code
        if top_result.code != clean_tnved_code:
            reason_parts.append(f"DB ID: {top_result.code}")
        
        # Add quality assessment
        if top_result.similarity_score >= self.confidence_threshold:
            quality_indicator = "High Confidence"
        else:
            quality_indicator = "Low Confidence"
        
        reason_parts.append(f"Quality: {quality_indicator}")
        
        # Check for uncertainty (multiple similar scores)
        if len(all_results) > 1:
            second_best = all_results[1]
            score_difference = top_result.similarity_score - second_best.similarity_score
            
            if score_difference < 0.05:  # Very close scores
                # Extract clean code for second best result too
                from batch_processor.services.tnved_code_utils import get_tnved_code_from_search_result
                second_clean_code = get_tnved_code_from_search_result(second_best)
                
                reason_parts.append(
                    f"Note: Close competition with {second_clean_code or second_best.code} "
                    f"(score: {second_best.similarity_score:.3f}). "
                    f"Manual review may be beneficial."
                )
        
        # Add algorithm information
        reason_parts.append("Algorithm: similarity_top1")
        
        return " | ".join(reason_parts)
    
    def get_algorithm_name(self) -> str:
        """Get algorithm name."""
        return "similarity_top1"
    
    def get_configuration(self) -> dict:
        """
        Get current configuration parameters.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            "algorithm": self.get_algorithm_name(),
            "confidence_threshold": self.confidence_threshold,
            "top_k": self.top_k
        }
    
    def update_confidence_threshold(self, threshold: float) -> None:
        """
        Update confidence threshold.
        
        Args:
            threshold: New confidence threshold (0.0-1.0)
            
        Raises:
            ValueError: If threshold is invalid
        """
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        
        old_threshold = self.confidence_threshold
        self.confidence_threshold = threshold
        
        logger.info(
            f"Updated confidence threshold from {old_threshold} to {threshold}"
        )