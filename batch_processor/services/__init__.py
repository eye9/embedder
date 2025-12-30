"""
Batch Processor Services

This module provides service classes for the batch Excel processor.
"""

from batch_processor.services.tnved_selector import TNVEDSelector, SelectorFactory
from batch_processor.services.similarity_selector import SimilarityTop1Selector
from batch_processor.services.llm_selector import LLMReasoningSelector, OpenAIProvider

# Register available selectors with the factory
SelectorFactory.register_selector("similarity_top1", SimilarityTop1Selector)
SelectorFactory.register_selector("llm_reasoning", LLMReasoningSelector)

__all__ = [
    'TNVEDSelector',
    'SelectorFactory', 
    'SimilarityTop1Selector',
    'LLMReasoningSelector',
    'OpenAIProvider'
]