"""
ТНВЭД Search Service

This module provides functionality to search for ТНВЭД codes by text description
using semantic similarity search with ChromaDB.
"""

import logging
from typing import List, Optional

from models.search_result import SearchResult
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from services.chroma_manager import ChromaDBManager


logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Raised when search operation fails"""
    pass


class TNVEDSearcher:
    """
    Searches for ТНВЭД codes by text description using semantic similarity.
    
    This class handles the complete search pipeline:
    1. Normalizing search query text
    2. Generating query embeddings
    3. Performing similarity search in ChromaDB
    4. Formatting and ranking results
    
    Features:
    - Query normalization using same pipeline as data loading
    - Semantic similarity search with configurable top-k results
    - Result ranking by similarity score
    - Error handling for invalid queries
    
    Attributes:
        db_manager: ChromaDB manager instance
        normalizer: Text normalizer instance
        embedder: Embedding generator instance
    """
    
    def __init__(
        self,
        db_path: str,
        normalizer: TextNormalizer,
        embedder: EmbeddingGenerator,
        collection_name: str = "tnved"
    ):
        """
        Initialize ТНВЭД searcher.
        
        Args:
            db_path: Path to ChromaDB storage directory
            normalizer: TextNormalizer instance for text processing
            embedder: EmbeddingGenerator instance for creating embeddings
            collection_name: Name of ChromaDB collection (default: "tnved")
        """
        self.normalizer = normalizer
        self.embedder = embedder
        
        # Initialize ChromaDB manager
        self.db_manager = ChromaDBManager(db_path, collection_name)
        
        logger.info(
            f"TNVEDSearcher initialized with db_path={db_path}, "
            f"collection={collection_name}"
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Search for ТНВЭД codes by text description.
        
        Normalizes the query text, generates embeddings, performs similarity
        search in ChromaDB, and returns ranked results with similarity scores.
        
        Args:
            query: Text description of the product to search for
            top_k: Number of top results to return (default: 5)
            
        Returns:
            List of SearchResult objects ordered by similarity score (descending)
            
        Raises:
            SearchError: If query is empty/invalid or search operation fails
            ValueError: If top_k is not positive
            
        Examples:
            >>> searcher = TNVEDSearcher("./chroma_db", normalizer, embedder)
            >>> results = searcher.search("кофейные зерна арабика", top_k=3)
            >>> for result in results:
            ...     print(f"{result.code}: {result.similarity_score:.3f}")
        """
        # Validate top_k parameter
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        
        # Validate query is not empty or whitespace-only
        if not query or not query.strip():
            error_msg = "Search query cannot be empty or whitespace-only"
            logger.error(error_msg)
            raise SearchError(error_msg)
        
        logger.info(f"Searching for: '{query}' (top_k={top_k})")
        
        try:
            # Step 1: Normalize query text using same pipeline as loader
            logger.debug("Normalizing query text")
            normalized_query = self.normalizer.normalize(query)
            
            if not normalized_query:
                error_msg = (
                    f"Query normalization resulted in empty text. "
                    f"Original query: '{query}'"
                )
                logger.error(error_msg)
                raise SearchError(error_msg)
            
            logger.debug(f"Normalized query: '{normalized_query}'")
            
            # Step 2: Generate embedding for normalized query
            logger.debug("Generating query embedding")
            query_embedding = self.embedder.generate(normalized_query)
            
            # Ensure embedding is 1D array and convert to list
            if query_embedding.ndim > 1:
                query_embedding = query_embedding.flatten()
            
            query_embedding_list = query_embedding.tolist()
            
            logger.debug(f"Generated embedding with dimension: {len(query_embedding_list)}")
            
            # Step 3: Perform similarity search in ChromaDB
            logger.debug(f"Querying ChromaDB for top {top_k} results")
            query_results = self.db_manager.query(
                query_embedding=query_embedding_list,
                n_results=top_k
            )
            
            # Step 4: Convert to SearchResult objects and format results
            search_results = self.db_manager.to_search_results(query_results)
            
            logger.info(
                f"Search completed successfully. Found {len(search_results)} results"
            )
            
            # Results are already ranked by similarity score (descending)
            # due to ChromaDB's query behavior
            return search_results
            
        except SearchError:
            # Re-raise SearchError as-is
            raise
        except ValueError as e:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            error_msg = f"Search operation failed: {e}"
            logger.error(error_msg, exc_info=True)
            raise SearchError(error_msg) from e
    
    def get_code_details(self, code: str) -> Optional[SearchResult]:
        """
        Get detailed information about a specific ТНВЭД code.
        
        Args:
            code: ТНВЭД code to retrieve
            
        Returns:
            SearchResult object with code details or None if not found
            
        Raises:
            ValueError: If code is empty
            
        Examples:
            >>> searcher = TNVEDSearcher("./chroma_db", normalizer, embedder)
            >>> result = searcher.get_code_details("0901110000")
            >>> if result:
            ...     print(f"{result.code}: {result.description}")
        """
        if not code or not code.strip():
            raise ValueError("Code cannot be empty")
        
        logger.debug(f"Retrieving details for code: {code}")
        
        record = self.db_manager.get_by_code(code)
        
        if record is None:
            logger.info(f"Code not found: {code}")
            return None
        
        # Convert to SearchResult (similarity score is 1.0 for exact match)
        search_result = SearchResult(
            code=record["id"],
            description=record["metadata"].get("description", ""),
            normalized_text=record["document"],
            similarity_score=1.0
        )
        
        logger.debug(f"Retrieved details for code: {code}")
        return search_result
    
    def get_database_stats(self) -> dict:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with database statistics:
                - total_records: Total number of ТНВЭД codes in database
                - collection_name: Name of the ChromaDB collection
        """
        stats = {
            "total_records": self.db_manager.count(),
            "collection_name": self.db_manager.collection_name
        }
        
        logger.debug(f"Database stats: {stats}")
        return stats
