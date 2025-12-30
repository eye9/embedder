"""
LLM-based TNVED Code Selection

This module implements TNVED code selection using Large Language Model reasoning.
It analyzes top-k search results and uses LLM to select the most appropriate code
with detailed reasoning explanation.
"""

import logging
import json
from typing import Optional, List, Dict, Any
import openai
from openai import OpenAI

from batch_processor.models.result import ProcessingResult
from batch_processor.services.tnved_selector import (
    TNVEDSelector, 
    create_processing_result_with_error,
    measure_processing_time
)
from batch_processor.services.similarity_selector import SimilarityTop1Selector
from services.tnved_searcher import TNVEDSearcher, SearchError
from models.search_result import SearchResult


logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Abstract interface for LLM providers.
    
    This allows for different LLM implementations (OpenAI, local models, etc.)
    while maintaining a consistent interface for the selector.
    """
    
    def analyze_tnved_options(
        self, 
        description: str, 
        search_results: List[SearchResult]
    ) -> Dict[str, Any]:
        """
        Analyze TNVED options and select the best one.
        
        Args:
            description: Product description
            search_results: List of potential TNVED codes with scores
            
        Returns:
            Dictionary with selected_code and reasoning
        """
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """
    OpenAI-based LLM provider for TNVED code analysis.
    
    Uses OpenAI's GPT models to analyze search results and provide
    reasoned selection of the most appropriate TNVED code.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.1,
        max_tokens: int = 500
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key (if None, uses environment variable)
            model: Model name to use
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"OpenAI provider initialized with model: {model}")
    
    def analyze_tnved_options(
        self, 
        description: str, 
        search_results: List[SearchResult]
    ) -> Dict[str, Any]:
        """
        Use OpenAI to analyze TNVED options and select the best one.
        
        Args:
            description: Product description
            search_results: List of potential TNVED codes
            
        Returns:
            Dictionary with selected_code and reasoning
            
        Raises:
            Exception: If LLM call fails
        """
        # Prepare the prompt
        prompt = self._create_analysis_prompt(description, search_results)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in TNVED (Russian customs tariff) "
                            "classification. Analyze the product description and "
                            "select the most appropriate TNVED code from the options "
                            "provided. Respond with valid JSON only."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                # If not valid JSON, create a structured response
                return {
                    "selected_code": search_results[0].code if search_results else None,
                    "reasoning": response_text,
                    "confidence": "medium"
                }
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _create_analysis_prompt(
        self, 
        description: str, 
        search_results: List[SearchResult]
    ) -> str:
        """
        Create analysis prompt for the LLM.
        
        Args:
            description: Product description
            search_results: Search results to analyze
            
        Returns:
            Formatted prompt string
        """
        options_text = []
        for i, result in enumerate(search_results, 1):
            options_text.append(
                f"{i}. Code: {result.code}\n"
                f"   Description: {result.description}\n"
                f"   Similarity Score: {result.similarity_score:.3f}\n"
            )
        
        prompt = f"""
Product Description: "{description}"

Available TNVED Code Options:
{chr(10).join(options_text)}

Please analyze the product description and select the most appropriate TNVED code from the options above.

Respond with JSON in this exact format:
{{
    "selected_code": "selected_tnved_code",
    "reasoning": "detailed explanation of why this code was chosen, considering the product characteristics and TNVED classification rules",
    "confidence": "high|medium|low",
    "alternative_codes": ["code1", "code2"] // if any other codes were seriously considered
}}

Consider:
1. The specific characteristics of the product
2. The accuracy of the TNVED code descriptions
3. The similarity scores as indicators of relevance
4. Standard TNVED classification principles
"""
        return prompt


class LLMReasoningSelector(TNVEDSelector):
    """
    TNVED code selector that uses LLM reasoning to analyze top-k results.
    
    This selector retrieves multiple potential TNVED codes and uses a Large
    Language Model to analyze them and select the most appropriate one based
    on detailed reasoning about the product characteristics and classification rules.
    
    Features:
    - LLM-based analysis of multiple search results
    - Detailed reasoning explanations
    - Fallback to similarity_top1 when LLM fails
    - Configurable top-k results for analysis
    - Support for different LLM providers
    
    Attributes:
        tnved_searcher: TNVEDSearcher instance for code lookup
        llm_provider: LLM provider for analysis
        fallback_selector: Similarity selector for fallback cases
        top_k: Number of results to analyze with LLM
    """
    
    def __init__(
        self,
        tnved_searcher: TNVEDSearcher,
        llm_provider: Optional[LLMProvider] = None,
        top_k: int = 5,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-3.5-turbo"
    ):
        """
        Initialize LLM-based selector.
        
        Args:
            tnved_searcher: TNVEDSearcher instance for performing searches
            llm_provider: LLM provider instance (if None, creates OpenAI provider)
            top_k: Number of search results to analyze with LLM
            openai_api_key: OpenAI API key (used if llm_provider is None)
            openai_model: OpenAI model name (used if llm_provider is None)
            
        Raises:
            ValueError: If parameters are invalid
        """
        if tnved_searcher is None:
            raise ValueError("tnved_searcher is required")
        
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        
        self.tnved_searcher = tnved_searcher
        self.top_k = top_k
        
        # Initialize LLM provider
        if llm_provider is None:
            self.llm_provider = OpenAIProvider(
                api_key=openai_api_key,
                model=openai_model
            )
        else:
            self.llm_provider = llm_provider
        
        # Create fallback selector for when LLM fails
        self.fallback_selector = SimilarityTop1Selector(
            tnved_searcher=tnved_searcher,
            confidence_threshold=0.7,
            top_k=1  # Only need top result for fallback
        )
        
        logger.info(
            f"LLMReasoningSelector initialized with top_k={top_k}, "
            f"llm_provider={type(self.llm_provider).__name__}"
        )
    
    @measure_processing_time
    def select_code(self, description: str, row_index: int = 0) -> ProcessingResult:
        """
        Select TNVED code using LLM reasoning.
        
        Searches for potential TNVED codes and uses LLM to analyze them
        and select the most appropriate one with detailed reasoning.
        Falls back to similarity_top1 if LLM analysis fails.
        
        Args:
            description: Product description to analyze
            row_index: Row index in source file for tracking
            
        Returns:
            ProcessingResult with LLM-selected code and reasoning
            
        Raises:
            ValueError: If description is empty or invalid
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")
        
        description = description.strip()
        logger.debug(f"LLM analyzing description: '{description[:100]}...'")
        
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
            
            # Try LLM analysis
            try:
                llm_result = self.llm_provider.analyze_tnved_options(
                    description, search_results
                )
                
                selected_code = llm_result.get("selected_code")
                reasoning = llm_result.get("reasoning", "LLM analysis completed")
                confidence_level = llm_result.get("confidence", "medium")
                
                # Validate that selected code is in search results
                if selected_code:
                    # Find the selected result to get similarity score
                    selected_result = None
                    for result in search_results:
                        if result.code == selected_code:
                            selected_result = result
                            break
                    
                    if selected_result:
                        # Format detailed reasoning
                        selection_reason = self._format_llm_reasoning(
                            selected_result,
                            reasoning,
                            confidence_level,
                            search_results
                        )
                        
                        logger.debug(
                            f"LLM selected code {selected_code} with "
                            f"confidence {confidence_level}"
                        )
                        
                        return ProcessingResult(
                            row_index=row_index,
                            original_description=description,
                            tnved_code=selected_code,
                            selection_reason=selection_reason,
                            confidence_score=selected_result.similarity_score
                        )
                
                # If we get here, LLM selection was invalid - fall back
                logger.warning(
                    f"LLM selected invalid code '{selected_code}', "
                    "falling back to similarity_top1"
                )
                
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}, falling back to similarity_top1")
            
            # Fallback to similarity-based selection
            fallback_result = self.fallback_selector.select_code(description, row_index)
            
            # Update reasoning to indicate fallback
            if fallback_result.tnved_code:
                fallback_result.selection_reason = (
                    f"LLM analysis failed, used similarity fallback. "
                    f"{fallback_result.selection_reason}"
                )
            
            return fallback_result
            
        except SearchError as e:
            error_msg = f"Search failed: {e}"
            logger.error(error_msg)
            return create_processing_result_with_error(
                row_index=row_index,
                description=description,
                error_message=error_msg
            )
        
        except Exception as e:
            error_msg = f"LLM code selection failed: {e}"
            logger.error(error_msg, exc_info=True)
            return create_processing_result_with_error(
                row_index=row_index,
                description=description,
                error_message=error_msg
            )
    
    def _format_llm_reasoning(
        self,
        selected_result: SearchResult,
        llm_reasoning: str,
        confidence_level: str,
        all_results: List[SearchResult]
    ) -> str:
        """
        Format LLM reasoning with additional context.
        
        Args:
            selected_result: The result selected by LLM
            llm_reasoning: Reasoning provided by LLM
            confidence_level: Confidence level from LLM
            all_results: All search results for context
            
        Returns:
            Formatted selection reason string
        """
        reason_parts = [
            f"Code: {selected_result.code}",
            f"LLM Confidence: {confidence_level.title()}",
            f"Similarity Score: {selected_result.similarity_score:.3f}",
            f"Reasoning: {llm_reasoning}",
            f"Algorithm: llm_reasoning"
        ]
        
        # Add information about alternatives considered
        if len(all_results) > 1:
            other_codes = [r.code for r in all_results if r.code != selected_result.code]
            if other_codes:
                reason_parts.append(
                    f"Alternatives considered: {', '.join(other_codes[:3])}"
                )
        
        return " | ".join(reason_parts)
    
    def get_algorithm_name(self) -> str:
        """Get algorithm name."""
        return "llm_reasoning"
    
    def get_configuration(self) -> dict:
        """
        Get current configuration parameters.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            "algorithm": self.get_algorithm_name(),
            "top_k": self.top_k,
            "llm_provider": type(self.llm_provider).__name__,
            "fallback_algorithm": self.fallback_selector.get_algorithm_name()
        }