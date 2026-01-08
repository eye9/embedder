"""
Core services for ТНВЭД Embedder System
"""

# Import only safe modules at module level
from services.text_normalizer import TextNormalizer
from services.chroma_manager import ChromaDBManager

# EmbeddingGenerator, TNVEDLoader, TNVEDSearcher, and EnhancedSearcher
# are imported lazily to avoid circular import issues with sentence_transformers

__all__ = [
    'TextNormalizer',
    'EmbeddingGenerator',
    'ChromaDBManager',
    'TNVEDLoader',
    'DataLoadError',
    'TNVEDSearcher',
    'SearchError',
    'EnhancedSearcher',
    'EnhancedSearchError'
]

def __getattr__(name):
    """Lazy import for problematic modules."""
    if name == 'EmbeddingGenerator':
        from services.embedding_generator import EmbeddingGenerator
        return EmbeddingGenerator
    elif name == 'TNVEDLoader':
        from services.tnved_loader import TNVEDLoader
        return TNVEDLoader
    elif name == 'DataLoadError':
        from services.tnved_loader import DataLoadError
        return DataLoadError
    elif name == 'TNVEDSearcher':
        from services.tnved_searcher import TNVEDSearcher
        return TNVEDSearcher
    elif name == 'SearchError':
        from services.tnved_searcher import SearchError
        return SearchError
    elif name == 'EnhancedSearcher':
        from services.enhanced_searcher import EnhancedSearcher
        return EnhancedSearcher
    elif name == 'EnhancedSearchError':
        from services.enhanced_searcher import EnhancedSearchError
        return EnhancedSearchError
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
