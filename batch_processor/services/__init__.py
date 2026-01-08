"""
Batch Processor Services

This module provides service classes for the batch Excel processor.
"""

from batch_processor.services.tnved_selector import TNVEDSelector, SelectorFactory
from batch_processor.services.similarity_selector import SimilarityTop1Selector

# Try to import LLM selector (optional dependency)
try:
    from batch_processor.services.llm_selector import LLMReasoningSelector, OpenAIProvider
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    LLMReasoningSelector = None
    OpenAIProvider = None

# Register available selectors with the factory
SelectorFactory.register_selector("similarity_top1", SimilarityTop1Selector)

if LLM_AVAILABLE:
    SelectorFactory.register_selector("llm_reasoning", LLMReasoningSelector)

__all__ = [
    'TNVEDSelector',
    'SelectorFactory', 
    'SimilarityTop1Selector',
]

if LLM_AVAILABLE:
    __all__.extend(['LLMReasoningSelector', 'OpenAIProvider'])