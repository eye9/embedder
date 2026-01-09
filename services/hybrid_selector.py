"""
Hybrid Selector for TNVED Code Matching System

This module provides a hybrid approach to TNVED code selection that combines
URL-based matching with semantic search fallback. It integrates with the existing
batch processor infrastructure while adding URL-first search capabilities.
"""

import logging
import time
import signal
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from batch_processor.services.tnved_selector import TNVEDSelector
from batch_processor.models.result import ProcessingResult
from services.url_matcher import URLMatcher, URLMatchResult
from services.selection_reason_formatter import (
    SelectionReasonFormatter, 
    SelectionContext, 
    MatchSource
)


logger = logging.getLogger(__name__)


class URLPriority(Enum):
    """URL search priority modes"""
    FIRST = "first"      # URL search first, then semantic fallback
    ONLY = "only"        # Only URL search, no semantic fallback
    DISABLED = "disabled" # Only semantic search, skip URL


@dataclass
class HybridProcessingResult:
    """
    Extended processing result with URL-specific information
    
    This extends the standard ProcessingResult with additional metadata
    about URL processing and hybrid selection behavior.
    """
    row_index: int
    original_description: str
    original_url: Optional[str]
    tnved_code: Optional[str]
    selection_reason: str
    match_source: str  # "url", "semantic", "none"
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    url_normalized: Optional[str] = None
    shop_type: Optional[str] = None
    product_id: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_processing_result(self) -> ProcessingResult:
        """
        Converts to standard ProcessingResult for compatibility
        
        Returns:
            ProcessingResult compatible with existing batch processor
        """
        return ProcessingResult(
            row_index=self.row_index,
            original_description=self.original_description,
            tnved_code=self.tnved_code,
            selection_reason=self.selection_reason,
            confidence_score=self.confidence_score,
            processing_time_ms=self.processing_time_ms,
            error_message=self.error_message
        )


class HybridSelector(TNVEDSelector):
    """
    Hybrid TNVED code selector combining URL matching with semantic search
    
    This selector implements a two-stage approach:
    1. First attempts to find codes using URL-based exact matching
    2. Falls back to semantic search if URL matching fails or is disabled
    
    Features:
    - Configurable URL priority modes (first, only, disabled)
    - Timeout handling for URL database queries
    - Seamless integration with existing TNVEDSelector interface
    - Detailed selection reason formatting
    - Error recovery and fallback mechanisms
    """
    
    def __init__(
        self,
        url_matcher: URLMatcher,
        semantic_selector: TNVEDSelector,
        url_priority: URLPriority = URLPriority.FIRST,
        url_timeout_seconds: float = 5.0,
        verbose_reasons: bool = True
    ):
        """
        Initialize hybrid selector
        
        Args:
            url_matcher: URLMatcher instance for URL-based lookups
            semantic_selector: Existing TNVEDSelector for semantic search
            url_priority: Priority mode for URL vs semantic search
            url_timeout_seconds: Timeout for URL database queries
            verbose_reasons: Whether to include detailed selection reasons
        """
        self.url_matcher = url_matcher
        self.semantic_selector = semantic_selector
        self.url_priority = url_priority
        self.url_timeout_seconds = url_timeout_seconds
        self.reason_formatter = SelectionReasonFormatter(
            verbose=verbose_reasons, 
            include_metadata=True
        )
        
        logger.info(
            f"HybridSelector initialized with priority: {url_priority.value}, "
            f"timeout: {url_timeout_seconds}s, verbose_reasons: {verbose_reasons}"
        )
    
    def select_code(self, description: str, row_index: int = 0) -> ProcessingResult:
        """
        Selects TNVED code using hybrid approach (URL first, then semantic)
        
        This method maintains compatibility with the TNVEDSelector interface
        while providing enhanced URL-based matching capabilities.
        
        Args:
            description: Product description text
            row_index: Row index for tracking
            
        Returns:
            ProcessingResult with selected code and reasoning
        """
        # For compatibility with existing interface, we don't have URL here
        # This method delegates to the enhanced version with no URL
        return self.select_code_with_url(description, None, row_index).to_processing_result()
    
    def select_code_with_url(
        self, 
        description: str, 
        url: Optional[str] = None, 
        row_index: int = 0
    ) -> HybridProcessingResult:
        """
        Enhanced code selection with URL support
        
        Args:
            description: Product description text
            url: Product URL (optional)
            row_index: Row index for tracking
            
        Returns:
            HybridProcessingResult with detailed selection information
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not description or not description.strip():
                return self._create_error_result(
                    row_index, description, url, 
                    "Empty or invalid product description", start_time
                )
            
            # Check URL priority configuration
            if self.url_priority == URLPriority.DISABLED or not url:
                return self._use_semantic_only(description, url, row_index, start_time)
            
            # Attempt URL-based search
            url_result = self._try_url_search(url)
            
            if url_result.found:
                # URL match found - return immediately
                processing_time = (time.time() - start_time) * 1000
                
                # Create context for formatting
                context = self.reason_formatter.create_context_from_url_result(
                    url_result, processing_time
                )
                
                return HybridProcessingResult(
                    row_index=row_index,
                    original_description=description,
                    original_url=url,
                    tnved_code=url_result.tnved_code,
                    selection_reason=self.reason_formatter.format_url_match_reason(url_result, context),
                    match_source="url",
                    confidence_score=url_result.confidence,
                    processing_time_ms=processing_time,
                    url_normalized=url_result.normalized_url,
                    shop_type=url_result.shop_type,
                    product_id=url_result.product_id
                )
            
            # URL search failed - check priority mode
            if self.url_priority == URLPriority.ONLY:
                processing_time = (time.time() - start_time) * 1000
                
                # Create context for URL-only mode
                context = SelectionContext(
                    match_source=MatchSource.NONE,
                    original_url=url,
                    normalized_url=getattr(url_result, 'normalized_url', None),
                    processing_time_ms=processing_time
                )
                
                return HybridProcessingResult(
                    row_index=row_index,
                    original_description=description,
                    original_url=url,
                    tnved_code=None,
                    selection_reason=self.reason_formatter.format_url_only_mode_reason(context),
                    match_source="none",
                    processing_time_ms=processing_time,
                    url_normalized=getattr(url_result, 'normalized_url', None)
                )
            
            # Fallback to semantic search
            return self._use_semantic_fallback(description, url, row_index, start_time)
            
        except Exception as e:
            logger.error(f"Error in hybrid selection: {e}")
            return self._create_error_result(
                row_index, description, url, str(e), start_time
            )
    
    def _try_url_search(self, url: str) -> URLMatchResult:
        """
        Attempts URL search with timeout protection
        
        Args:
            url: URL to search for
            
        Returns:
            URLMatchResult with search results
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("URL search timeout")
        
        try:
            # Set up timeout (Unix-like systems only)
            old_handler = None
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(self.url_timeout_seconds))
            
            # Perform URL search
            result = self.url_matcher.find_code_by_url(url)
            
            # Clear timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            return result
            
        except TimeoutError:
            logger.warning(f"URL search timeout after {self.url_timeout_seconds}s")
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            return URLMatchResult(found=False)
        except Exception as e:
            logger.error(f"Error during URL search: {e}")
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            return URLMatchResult(found=False)
        finally:
            # Restore original signal handler
            if old_handler is not None and hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, old_handler)
    
    def _use_semantic_only(
        self, 
        description: str, 
        url: Optional[str], 
        row_index: int, 
        start_time: float
    ) -> HybridProcessingResult:
        """
        Uses only semantic search (URL disabled or not provided)
        
        Args:
            description: Product description
            url: Product URL (may be None)
            row_index: Row index
            start_time: Processing start time
            
        Returns:
            HybridProcessingResult with semantic search results
        """
        try:
            semantic_result = self.semantic_selector.select_code(description, row_index)
            processing_time = (time.time() - start_time) * 1000
            
            # Create context for semantic-only search
            context = self.reason_formatter.create_context_from_semantic_result(
                semantic_result, url, fallback_used=False
            )
            context.processing_time_ms = processing_time
            
            return HybridProcessingResult(
                row_index=row_index,
                original_description=description,
                original_url=url,
                tnved_code=semantic_result.tnved_code,
                selection_reason=self.reason_formatter.format_semantic_match_reason(semantic_result, context),
                match_source="semantic",
                confidence_score=semantic_result.confidence_score,
                processing_time_ms=processing_time,
                error_message=semantic_result.error_message
            )
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            # Create error context
            context = SelectionContext(
                match_source=MatchSource.ERROR,
                original_url=url,
                processing_time_ms=processing_time,
                error_message=str(e)
            )
            
            return HybridProcessingResult(
                row_index=row_index,
                original_description=description,
                original_url=url,
                tnved_code=None,
                selection_reason=self.reason_formatter.format_error_reason(str(e), context),
                match_source="none",
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    def _use_semantic_fallback(
        self, 
        description: str, 
        url: Optional[str], 
        row_index: int, 
        start_time: float
    ) -> HybridProcessingResult:
        """
        Uses semantic search as fallback after failed URL search
        
        Args:
            description: Product description
            url: Product URL
            row_index: Row index
            start_time: Processing start time
            
        Returns:
            HybridProcessingResult with fallback search results
        """
        try:
            semantic_result = self.semantic_selector.select_code(description, row_index)
            processing_time = (time.time() - start_time) * 1000
            
            # Create context for fallback search
            context = self.reason_formatter.create_context_from_semantic_result(
                semantic_result, url, fallback_used=True
            )
            context.processing_time_ms = processing_time
            
            return HybridProcessingResult(
                row_index=row_index,
                original_description=description,
                original_url=url,
                tnved_code=semantic_result.tnved_code,
                selection_reason=self.reason_formatter.format_semantic_match_reason(semantic_result, context),
                match_source="semantic",
                confidence_score=semantic_result.confidence_score,
                processing_time_ms=processing_time,
                error_message=semantic_result.error_message
            )
            
        except Exception as e:
            logger.error(f"Error in semantic fallback: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            # Create error context for fallback failure
            context = SelectionContext(
                match_source=MatchSource.ERROR,
                original_url=url,
                processing_time_ms=processing_time,
                error_message=str(e),
                fallback_used=True
            )
            
            return HybridProcessingResult(
                row_index=row_index,
                original_description=description,
                original_url=url,
                tnved_code=None,
                selection_reason=self.reason_formatter.format_error_reason(
                    f"Both URL and semantic search failed: {e}", context
                ),
                match_source="none",
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    def _create_error_result(
        self, 
        row_index: int, 
        description: str, 
        url: Optional[str], 
        error_message: str, 
        start_time: float
    ) -> HybridProcessingResult:
        """
        Creates error result for failed processing
        
        Args:
            row_index: Row index
            description: Product description
            url: Product URL
            error_message: Error message
            start_time: Processing start time
            
        Returns:
            HybridProcessingResult with error information
        """
        processing_time = (time.time() - start_time) * 1000
        
        # Create error context
        context = SelectionContext(
            match_source=MatchSource.ERROR,
            original_url=url,
            processing_time_ms=processing_time,
            error_message=error_message
        )
        
        return HybridProcessingResult(
            row_index=row_index,
            original_description=description,
            original_url=url,
            tnved_code=None,
            selection_reason=self.reason_formatter.format_error_reason(error_message, context),
            match_source="none",
            processing_time_ms=processing_time,
            error_message=error_message
        )
    
    def get_algorithm_name(self) -> str:
        """
        Returns algorithm name for this selector
        
        Returns:
            Algorithm name string
        """
        return "hybrid_url_semantic"
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Returns current configuration of the hybrid selector
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            "algorithm": self.get_algorithm_name(),
            "url_priority": self.url_priority.value,
            "url_timeout_seconds": self.url_timeout_seconds,
            "verbose_reasons": self.reason_formatter.verbose,
            "include_metadata": self.reason_formatter.include_metadata,
            "semantic_algorithm": self.semantic_selector.get_algorithm_name(),
            "url_matcher_stats": self.url_matcher.get_matcher_statistics()
        }