"""
Selection Reason Formatter for TNVED Code Matching System

This module provides consistent formatting for selection reasons across different
matching strategies (URL-based, semantic search, hybrid approaches).
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from services.url_matcher import URLMatchResult
from batch_processor.models.result import ProcessingResult


logger = logging.getLogger(__name__)


class MatchSource(Enum):
    """Types of match sources for selection reasons"""
    URL = "url"
    SEMANTIC = "semantic" 
    NONE = "none"
    ERROR = "error"


@dataclass
class SelectionContext:
    """
    Context information for selection reason formatting
    
    Attributes:
        match_source: Source of the match (URL, semantic, etc.)
        original_url: Original URL provided (if any)
        normalized_url: Normalized URL used for matching (if any)
        shop_type: Detected shop type (if any)
        product_id: Extracted product ID (if any)
        source_name: Data source name (if URL match)
        confidence_score: Confidence score of the match
        processing_time_ms: Time taken for processing
        error_message: Error message (if any)
        fallback_used: Whether fallback method was used
        timeout_occurred: Whether timeout occurred during processing
    """
    match_source: MatchSource
    original_url: Optional[str] = None
    normalized_url: Optional[str] = None
    shop_type: Optional[str] = None
    product_id: Optional[str] = None
    source_name: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    fallback_used: bool = False
    timeout_occurred: bool = False


class SelectionReasonFormatter:
    """
    Formats selection reasons consistently across different matching strategies
    
    Features:
    - Consistent formatting for URL matches
    - Fallback explanation formatting for semantic search
    - Error case explanation formatting
    - Configurable verbosity levels
    - Support for multiple languages (extensible)
    """
    
    def __init__(self, verbose: bool = True, include_metadata: bool = True):
        """
        Initialize selection reason formatter
        
        Args:
            verbose: Whether to include detailed information
            include_metadata: Whether to include metadata like timing, shop type
        """
        self.verbose = verbose
        self.include_metadata = include_metadata
        
        logger.debug(f"SelectionReasonFormatter initialized (verbose={verbose}, metadata={include_metadata})")
    
    def format_url_match_reason(
        self, 
        url_result: URLMatchResult, 
        context: Optional[SelectionContext] = None
    ) -> str:
        """
        Formats reason for URL-based matches
        
        Args:
            url_result: URL match result
            context: Additional context information
            
        Returns:
            Formatted selection reason string
            
        Examples:
            >>> formatter = SelectionReasonFormatter()
            >>> reason = formatter.format_url_match_reason(url_result)
            "Found by URL: https://ozon.ru/product/123 | Code: 1234567890 | Description: Product Name | Source: ozon_data"
        """
        if not url_result.found:
            return self._format_no_url_match(context)
        
        # Core information
        reason_parts = [
            f"Found by URL: {url_result.original_url}",
            f"Code: {url_result.tnved_code}",
            f"Description: {self._truncate_description(url_result.description)}"
        ]
        
        # Add source information
        if url_result.source_name:
            reason_parts.append(f"Source: {url_result.source_name}")
        
        # Add metadata if enabled
        if self.include_metadata:
            metadata_parts = []
            
            if url_result.shop_type:
                metadata_parts.append(f"Shop: {url_result.shop_type}")
            
            if url_result.product_id:
                metadata_parts.append(f"ID: {url_result.product_id}")
            
            if url_result.confidence is not None:
                metadata_parts.append(f"Confidence: {url_result.confidence:.2f}")
            
            if context and context.processing_time_ms:
                metadata_parts.append(f"Time: {context.processing_time_ms:.1f}ms")
            
            if metadata_parts:
                reason_parts.extend(metadata_parts)
        
        return " | ".join(reason_parts)
    
    def format_semantic_match_reason(
        self, 
        semantic_result: ProcessingResult, 
        context: Optional[SelectionContext] = None
    ) -> str:
        """
        Formats reason for semantic search matches
        
        Args:
            semantic_result: Semantic search result
            context: Additional context information
            
        Returns:
            Formatted selection reason string
        """
        base_reason = semantic_result.selection_reason
        
        # Determine prefix based on context
        if context:
            if context.fallback_used:
                prefix = "URL not found, used semantic search"
            elif context.match_source == MatchSource.SEMANTIC and not context.original_url:
                prefix = "Used semantic search (no URL provided)"
            elif context.match_source == MatchSource.SEMANTIC:
                prefix = "Used semantic search (URL search disabled)"
            else:
                prefix = "Found by semantic search"
        else:
            prefix = "Found by semantic search"
        
        # Combine prefix with semantic reasoning
        if base_reason and base_reason.strip():
            combined_reason = f"{prefix} | {base_reason}"
        else:
            combined_reason = prefix
        
        # Add metadata if enabled
        if self.include_metadata and context:
            metadata_parts = []
            
            if context.processing_time_ms:
                metadata_parts.append(f"Time: {context.processing_time_ms:.1f}ms")
            
            if semantic_result.confidence_score is not None:
                metadata_parts.append(f"Confidence: {semantic_result.confidence_score:.2f}")
            
            if metadata_parts:
                combined_reason += " | " + " | ".join(metadata_parts)
        
        return combined_reason
    
    def format_no_match_reason(self, context: Optional[SelectionContext] = None) -> str:
        """
        Formats reason when no match is found
        
        Args:
            context: Context information about the failed search
            
        Returns:
            Formatted reason explaining why no match was found
        """
        if not context:
            return "No match found"
        
        reason_parts = []
        
        # Determine what was attempted
        if context.original_url and context.match_source != MatchSource.SEMANTIC:
            reason_parts.append("No URL match found")
            
            if context.match_source != MatchSource.URL:  # Hybrid mode
                reason_parts.append("semantic search also failed")
        else:
            reason_parts.append("No semantic match found")
        
        # Add specific failure reasons
        if context.timeout_occurred:
            reason_parts.append("(timeout occurred)")
        
        if context.error_message:
            reason_parts.append(f"(error: {context.error_message})")
        
        base_reason = ", ".join(reason_parts) if reason_parts else "No match found"
        
        # Add metadata
        if self.include_metadata and context.processing_time_ms:
            base_reason += f" | Time: {context.processing_time_ms:.1f}ms"
        
        return base_reason
    
    def format_error_reason(
        self, 
        error_message: str, 
        context: Optional[SelectionContext] = None
    ) -> str:
        """
        Formats reason for error cases
        
        Args:
            error_message: Error message
            context: Additional context information
            
        Returns:
            Formatted error reason string
        """
        base_reason = f"Processing error: {error_message}"
        
        # Add context if available
        if context:
            context_parts = []
            
            if context.original_url:
                context_parts.append(f"URL: {self._sanitize_url_for_reason(context.original_url)}")
            
            if context.timeout_occurred:
                context_parts.append("timeout occurred")
            
            if context.processing_time_ms:
                context_parts.append(f"after {context.processing_time_ms:.1f}ms")
            
            if context_parts:
                base_reason += f" ({', '.join(context_parts)})"
        
        return base_reason
    
    def format_url_only_mode_reason(self, context: Optional[SelectionContext] = None) -> str:
        """
        Formats reason for URL-only mode when no match is found
        
        Args:
            context: Context information
            
        Returns:
            Formatted reason for URL-only mode failure
        """
        base_reason = "URL-only mode: No matching URL found in database"
        
        if self.include_metadata and context:
            metadata_parts = []
            
            if context.normalized_url:
                metadata_parts.append(f"Searched: {self._sanitize_url_for_reason(context.normalized_url)}")
            
            if context.processing_time_ms:
                metadata_parts.append(f"Time: {context.processing_time_ms:.1f}ms")
            
            if metadata_parts:
                base_reason += f" | {' | '.join(metadata_parts)}"
        
        return base_reason
    
    def _format_no_url_match(self, context: Optional[SelectionContext] = None) -> str:
        """Formats reason when URL search finds no match"""
        if context and context.timeout_occurred:
            return "URL search timeout, no match found"
        return "No URL match found"
    
    def _truncate_description(self, description: str, max_length: int = 100) -> str:
        """
        Truncates description for reason formatting
        
        Args:
            description: Description to truncate
            max_length: Maximum length to keep
            
        Returns:
            Truncated description with ellipsis if needed
        """
        if not description:
            return ""
        
        description = description.strip()
        if len(description) <= max_length:
            return description
        
        return description[:max_length-3] + "..."
    
    def _sanitize_url_for_reason(self, url: str) -> str:
        """
        Sanitizes URL for inclusion in selection reasons
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL safe for logging and display
        """
        if not url:
            return "[EMPTY_URL]"
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Remove credentials if present
            if parsed.username or parsed.password:
                parsed = parsed._replace(username=None, password=None)
            
            # Remove query parameters for cleaner display
            parsed = parsed._replace(query='', fragment='')
            
            from urllib.parse import urlunparse
            return urlunparse(parsed)
            
        except Exception:
            return "[MALFORMED_URL]"
    
    def create_context_from_url_result(
        self, 
        url_result: URLMatchResult,
        processing_time_ms: Optional[float] = None,
        fallback_used: bool = False
    ) -> SelectionContext:
        """
        Creates SelectionContext from URLMatchResult
        
        Args:
            url_result: URL match result
            processing_time_ms: Processing time
            fallback_used: Whether fallback was used
            
        Returns:
            SelectionContext for formatting
        """
        return SelectionContext(
            match_source=MatchSource.URL if url_result.found else MatchSource.NONE,
            original_url=url_result.original_url,
            normalized_url=url_result.normalized_url,
            shop_type=url_result.shop_type,
            product_id=url_result.product_id,
            source_name=url_result.source_name,
            confidence_score=url_result.confidence,
            processing_time_ms=processing_time_ms,
            fallback_used=fallback_used
        )
    
    def create_context_from_semantic_result(
        self, 
        semantic_result: ProcessingResult,
        original_url: Optional[str] = None,
        fallback_used: bool = False
    ) -> SelectionContext:
        """
        Creates SelectionContext from semantic ProcessingResult
        
        Args:
            semantic_result: Semantic search result
            original_url: Original URL (if any)
            fallback_used: Whether this was a fallback search
            
        Returns:
            SelectionContext for formatting
        """
        return SelectionContext(
            match_source=MatchSource.SEMANTIC,
            original_url=original_url,
            confidence_score=semantic_result.confidence_score,
            processing_time_ms=semantic_result.processing_time_ms,
            error_message=semantic_result.error_message,
            fallback_used=fallback_used
        )


# Convenience functions for common formatting scenarios

def format_url_match(url_result: URLMatchResult, verbose: bool = True) -> str:
    """
    Convenience function to format URL match reason
    
    Args:
        url_result: URL match result
        verbose: Whether to include detailed information
        
    Returns:
        Formatted selection reason
    """
    formatter = SelectionReasonFormatter(verbose=verbose)
    return formatter.format_url_match_reason(url_result)


def format_semantic_fallback(
    semantic_result: ProcessingResult, 
    original_url: Optional[str] = None,
    verbose: bool = True
) -> str:
    """
    Convenience function to format semantic fallback reason
    
    Args:
        semantic_result: Semantic search result
        original_url: Original URL that failed to match
        verbose: Whether to include detailed information
        
    Returns:
        Formatted selection reason
    """
    formatter = SelectionReasonFormatter(verbose=verbose)
    context = formatter.create_context_from_semantic_result(
        semantic_result, original_url, fallback_used=True
    )
    return formatter.format_semantic_match_reason(semantic_result, context)


def format_processing_error(error_message: str, url: Optional[str] = None) -> str:
    """
    Convenience function to format processing error reason
    
    Args:
        error_message: Error message
        url: URL being processed (if any)
        
    Returns:
        Formatted error reason
    """
    formatter = SelectionReasonFormatter()
    context = SelectionContext(
        match_source=MatchSource.ERROR,
        original_url=url,
        error_message=error_message
    )
    return formatter.format_error_reason(error_message, context)