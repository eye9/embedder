"""
TNVED System Integration for Batch Processor

This module provides integration between the batch processor and the existing
TNVED embedder system, including proper initialization of all required components.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from services.tnved_searcher import TNVEDSearcher
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from batch_processor.services.tnved_selector import SelectorFactory
from batch_processor.services.similarity_selector import SimilarityTop1Selector
from batch_processor.services.llm_selector import LLMReasoningSelector


logger = logging.getLogger(__name__)


class TNVEDIntegrationError(Exception):
    """Exception raised when TNVED integration fails."""
    pass


class TNVEDSystemIntegration:
    """
    Manages integration with the existing TNVED embedder system.
    
    This class handles:
    - Loading TNVED system configuration
    - Initializing text normalizer and embedding generator
    - Creating TNVEDSearcher instance
    - Registering selector algorithms with the factory
    - Providing configured selectors for batch processing
    
    The integration ensures that the batch processor uses the same
    configuration and components as the main TNVED system for consistency.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        tnved_config_path: Optional[str] = None
    ):
        """
        Initialize TNVED system integration.
        
        Args:
            config_path: Path to batch processor config (optional)
            tnved_config_path: Path to TNVED system config (optional)
        """
        self.config_path = config_path or "batch_processor_config.yaml"
        self.tnved_config_path = tnved_config_path or "config.yaml"
        
        # Components will be initialized lazily
        self._batch_config = None
        self._tnved_config = None
        self._text_normalizer = None
        self._embedding_generator = None
        self._tnved_searcher = None
        self._initialized = False
        
        logger.info("TNVEDSystemIntegration created")
    
    def initialize(self) -> None:
        """
        Initialize all TNVED system components.
        
        This method loads configurations, creates the text normalizer,
        embedding generator, and TNVED searcher, then registers the
        selector algorithms with the factory.
        
        Raises:
            TNVEDIntegrationError: If initialization fails
        """
        if self._initialized:
            logger.debug("TNVED integration already initialized")
            return
        
        try:
            logger.info("Initializing TNVED system integration...")
            
            # Load configurations
            self._load_configurations()
            
            # Initialize core components
            self._initialize_text_normalizer()
            self._initialize_embedding_generator()
            self._initialize_tnved_searcher()
            
            # Register selector algorithms
            self._register_selectors()
            
            self._initialized = True
            logger.info("TNVED system integration initialized successfully")
            
        except Exception as e:
            # If initialization fails due to missing dependencies or other issues,
            # we still mark as initialized but with limited functionality
            logger.warning(f"TNVED integration initialization failed: {e}")
            logger.warning("Falling back to basic processing without TNVED codes")
            self._initialized = True  # Mark as initialized to prevent retry loops
            raise TNVEDIntegrationError(f"TNVED integration unavailable: {e}") from e
        except Exception as e:
            error_msg = f"Failed to initialize TNVED integration: {e}"
            logger.error(error_msg, exc_info=True)
            raise TNVEDIntegrationError(error_msg) from e
    
    def _load_configurations(self) -> None:
        """Load batch processor and TNVED system configurations."""
        # Load batch processor config
        try:
            batch_config_path = Path(self.config_path)
            if batch_config_path.exists():
                with open(batch_config_path, 'r', encoding='utf-8') as f:
                    self._batch_config = yaml.safe_load(f)
                logger.debug(f"Loaded batch processor config from {batch_config_path}")
            else:
                logger.warning(f"Batch config not found at {batch_config_path}, using defaults")
                self._batch_config = self._get_default_batch_config()
        except Exception as e:
            logger.error(f"Failed to load batch processor config: {e}")
            self._batch_config = self._get_default_batch_config()
        
        # Load TNVED system config
        try:
            tnved_config_path = Path(self.tnved_config_path)
            if tnved_config_path.exists():
                with open(tnved_config_path, 'r', encoding='utf-8') as f:
                    self._tnved_config = yaml.safe_load(f)
                logger.debug(f"Loaded TNVED config from {tnved_config_path}")
            else:
                logger.warning(f"TNVED config not found at {tnved_config_path}, using defaults")
                self._tnved_config = self._get_default_tnved_config()
        except Exception as e:
            logger.error(f"Failed to load TNVED config: {e}")
            self._tnved_config = self._get_default_tnved_config()
    
    def _initialize_text_normalizer(self) -> None:
        """Initialize text normalizer component."""
        try:
            self._text_normalizer = TextNormalizer()
            logger.debug("Text normalizer initialized")
        except Exception as e:
            raise TNVEDIntegrationError(f"Failed to initialize text normalizer: {e}")
    
    def _initialize_embedding_generator(self) -> None:
        """Initialize embedding generator component."""
        try:
            # Get model configuration from TNVED config
            model_config = self._tnved_config.get('model', {})
            model_name = model_config.get('name', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            device = model_config.get('device', 'cpu')
            
            self._embedding_generator = EmbeddingGenerator(
                model_name=model_name,
                device=device
            )
            logger.debug(f"Embedding generator initialized with model: {model_name}")
        except Exception as e:
            raise TNVEDIntegrationError(f"Failed to initialize embedding generator: {e}")
    
    def _initialize_tnved_searcher(self) -> None:
        """Initialize TNVED searcher component."""
        try:
            # Get database configuration
            db_config = self._tnved_config.get('database', {})
            db_path = db_config.get('path', './chroma_db')
            collection_name = db_config.get('collection_name', 'tnved')
            
            self._tnved_searcher = TNVEDSearcher(
                db_path=db_path,
                normalizer=self._text_normalizer,
                embedder=self._embedding_generator,
                collection_name=collection_name
            )
            
            # Verify database has data
            stats = self._tnved_searcher.get_database_stats()
            total_records = stats.get('total_records', 0)
            
            if total_records == 0:
                logger.warning("TNVED database appears to be empty")
            else:
                logger.info(f"TNVED searcher initialized with {total_records} records")
                
        except Exception as e:
            raise TNVEDIntegrationError(f"Failed to initialize TNVED searcher: {e}")
    
    def _register_selectors(self) -> None:
        """Register selector algorithms with the factory."""
        try:
            # Register similarity-based selector
            SelectorFactory.register_selector('similarity_top1', SimilarityTop1Selector)
            
            # Register LLM-based selector
            SelectorFactory.register_selector('llm_reasoning', LLMReasoningSelector)
            
            logger.debug("Selector algorithms registered with factory")
        except Exception as e:
            raise TNVEDIntegrationError(f"Failed to register selectors: {e}")
    
    def get_tnved_searcher(self) -> TNVEDSearcher:
        """
        Get the initialized TNVED searcher instance.
        
        Returns:
            TNVEDSearcher instance
            
        Raises:
            TNVEDIntegrationError: If not initialized
        """
        if not self._initialized:
            raise TNVEDIntegrationError("TNVED integration not initialized")
        
        return self._tnved_searcher
    
    def create_selector(
        self,
        algorithm: str,
        **kwargs
    ) -> Any:
        """
        Create a configured TNVED selector.
        
        Args:
            algorithm: Algorithm name ('similarity_top1' or 'llm_reasoning')
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured TNVEDSelector instance
            
        Raises:
            TNVEDIntegrationError: If not initialized or algorithm unknown
        """
        if not self._initialized:
            raise TNVEDIntegrationError("TNVED integration not initialized")
        
        try:
            # Get default parameters from configuration
            processing_config = self._batch_config.get('processing', {})
            
            # Prepare selector parameters
            selector_params = {
                'tnved_searcher': self._tnved_searcher,
                'confidence_threshold': kwargs.get(
                    'confidence_threshold',
                    processing_config.get('confidence_threshold', 0.7)
                ),
                'top_k': kwargs.get(
                    'top_k',
                    processing_config.get('llm_top_k', 5)
                )
            }
            
            # Add any additional parameters
            selector_params.update(kwargs)
            
            # Create selector using factory
            selector = SelectorFactory.create_selector(algorithm, **selector_params)
            logger.debug(f"Created {algorithm} selector")
            
            return selector
            
        except Exception as e:
            raise TNVEDIntegrationError(f"Failed to create {algorithm} selector: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get information about the integrated TNVED system.
        
        Returns:
            Dictionary with system information
        """
        if not self._initialized:
            return {"status": "not_initialized"}
        
        try:
            # Get database statistics
            db_stats = self._tnved_searcher.get_database_stats()
            
            # Get model information
            model_config = self._tnved_config.get('model', {})
            
            # Get available algorithms
            available_algorithms = SelectorFactory.get_available_algorithms()
            
            return {
                "status": "initialized",
                "database": {
                    "total_records": db_stats.get('total_records', 0),
                    "collection_name": db_stats.get('collection_name', 'unknown'),
                    "path": self._tnved_config.get('database', {}).get('path', 'unknown')
                },
                "model": {
                    "name": model_config.get('name', 'unknown'),
                    "device": model_config.get('device', 'unknown'),
                    "embedding_dimension": self._embedding_generator.get_embedding_dimension() if self._embedding_generator else 0
                },
                "algorithms": available_algorithms,
                "config_files": {
                    "batch_config": self.config_path,
                    "tnved_config": self.tnved_config_path
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def test_integration(self, test_query: str = "кофейные зерна") -> Dict[str, Any]:
        """
        Test the TNVED integration with a sample query.
        
        Args:
            test_query: Test query to use for testing
            
        Returns:
            Dictionary with test results
        """
        if not self._initialized:
            return {
                "status": "error",
                "error": "Integration not initialized"
            }
        
        try:
            logger.info(f"Testing TNVED integration with query: '{test_query}'")
            
            # Test search functionality
            search_results = self._tnved_searcher.search(test_query, top_k=3)
            
            # Test selector creation
            similarity_selector = self.create_selector('similarity_top1')
            
            # Test selector functionality
            selector_result = similarity_selector.select_code(test_query, row_index=0)
            
            return {
                "status": "success",
                "test_query": test_query,
                "search_results_count": len(search_results),
                "top_result": {
                    "code": search_results[0].code if search_results else None,
                    "similarity_score": search_results[0].similarity_score if search_results else None,
                    "description": search_results[0].description[:100] if search_results else None
                } if search_results else None,
                "selector_result": {
                    "tnved_code": selector_result.tnved_code,
                    "confidence_score": selector_result.confidence_score,
                    "has_error": selector_result.error_message is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_default_batch_config(self) -> Dict[str, Any]:
        """Get default batch processor configuration."""
        return {
            "processing": {
                "confidence_threshold": 0.7,
                "llm_top_k": 5,
                "default_algorithm": "similarity_top1"
            }
        }
    
    def _get_default_tnved_config(self) -> Dict[str, Any]:
        """Get default TNVED system configuration."""
        return {
            "model": {
                "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "device": "cpu"
            },
            "database": {
                "path": "./chroma_db",
                "collection_name": "tnved"
            }
        }


# Global integration instance
_integration_instance: Optional[TNVEDSystemIntegration] = None


def get_tnved_integration(
    config_path: Optional[str] = None,
    tnved_config_path: Optional[str] = None,
    force_reinit: bool = False
) -> TNVEDSystemIntegration:
    """
    Get or create the global TNVED integration instance.
    
    Args:
        config_path: Path to batch processor config (optional)
        tnved_config_path: Path to TNVED system config (optional)
        force_reinit: Force reinitialization even if already exists
        
    Returns:
        TNVEDSystemIntegration instance
    """
    global _integration_instance
    
    if _integration_instance is None or force_reinit:
        _integration_instance = TNVEDSystemIntegration(
            config_path=config_path,
            tnved_config_path=tnved_config_path
        )
        _integration_instance.initialize()
    
    return _integration_instance


def initialize_tnved_integration(
    config_path: Optional[str] = None,
    tnved_config_path: Optional[str] = None
) -> None:
    """
    Initialize the global TNVED integration.
    
    Args:
        config_path: Path to batch processor config (optional)
        tnved_config_path: Path to TNVED system config (optional)
    """
    get_tnved_integration(config_path, tnved_config_path)
    logger.info("Global TNVED integration initialized")