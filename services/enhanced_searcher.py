"""
Enhanced Search Service for ТНВЭД Embedder System

This module provides enhanced search functionality that works across both
reference records (official ТНВЭД descriptions) and product records (real
products with assigned codes).
"""

import logging
from typing import List, Dict, Optional
from collections import defaultdict

from models.search_result import SearchResult
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from services.chroma_manager import ChromaDBManager


logger = logging.getLogger(__name__)


class EnhancedSearchError(Exception):
    """Raised when enhanced search operation fails"""
    pass


class EnhancedSearcher:
    """
    Enhanced searcher that works across both reference and product records.
    
    This class provides advanced search capabilities:
    1. Unified search across reference and product records
    2. Result grouping and prioritization logic
    3. Code-specific queries for retrieving all records for a ТНВЭД code
    4. Source filtering capabilities
    
    Features:
    - Search across both reference and product records by default
    - Prioritize reference records over product records in results
    - Group results by ТНВЭД code when requested
    - Filter results by source type (reference/product)
    - Retrieve all records for a specific ТНВЭД code
    
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
        Initialize enhanced searcher.
        
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
            f"EnhancedSearcher initialized with db_path={db_path}, "
            f"collection={collection_name}"
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for ТНВЭД codes across both reference and product records.
        
        Performs unified search across all record types with optional filtering
        and automatic result prioritization.
        
        Args:
            query: Text description of the product to search for
            top_k: Number of top results to return (default: 5)
            source_filter: Optional filter by source type ("reference", "product", or None for all)
            
        Returns:
            List of SearchResult objects ordered by priority and similarity score
            
        Raises:
            EnhancedSearchError: If query is empty/invalid or search operation fails
            ValueError: If top_k is not positive or invalid source_filter
            
        Examples:
            >>> searcher = EnhancedSearcher("./chroma_db", normalizer, embedder)
            >>> # Search all records
            >>> results = searcher.search("кофейные зерна арабика", top_k=5)
            >>> # Search only reference records
            >>> ref_results = searcher.search("кофе", source_filter="reference")
            >>> # Search only product records
            >>> prod_results = searcher.search("кофе", source_filter="product")
        """
        # Validate parameters
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        
        if source_filter is not None and source_filter not in ["reference", "product"]:
            raise ValueError(f"Invalid source_filter: {source_filter}. Must be 'reference', 'product', or None")
        
        # Validate query is not empty or whitespace-only
        if not query or not query.strip():
            error_msg = "Search query cannot be empty or whitespace-only"
            logger.error(error_msg)
            raise EnhancedSearchError(error_msg)
        
        logger.info(f"Enhanced search for: '{query}' (top_k={top_k}, source_filter={source_filter})")
        
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
                raise EnhancedSearchError(error_msg)
            
            logger.debug(f"Normalized query: '{normalized_query}'")
            
            # Step 2: Generate embedding for normalized query with search_query prefix
            logger.debug("Generating query embedding")
            query_embedding = self.embedder.generate(
                normalized_query,
                prefix="search_query: "
            )
            
            # Ensure embedding is 1D array and convert to list
            if query_embedding.ndim > 1:
                query_embedding = query_embedding.flatten()
            
            query_embedding_list = query_embedding.tolist()
            
            logger.debug(f"Generated embedding with dimension: {len(query_embedding_list)}")
            
            # Step 3: Perform similarity search in ChromaDB with source filtering
            logger.debug(f"Querying ChromaDB for top {top_k} results with source_filter={source_filter}")
            query_results = self.db_manager.query(
                query_embedding=query_embedding_list,
                n_results=top_k,
                source_filter=source_filter
            )
            
            # Step 4: Convert to SearchResult objects
            search_results = self.db_manager.to_search_results(query_results)
            
            # Step 5: Apply result prioritization logic
            prioritized_results = self._prioritize_results(search_results)
            
            logger.info(
                f"Enhanced search completed successfully. Found {len(prioritized_results)} results"
            )
            
            return prioritized_results
            
        except EnhancedSearchError:
            # Re-raise EnhancedSearchError as-is
            raise
        except ValueError as e:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            error_msg = f"Enhanced search operation failed: {e}"
            logger.error(error_msg, exc_info=True)
            raise EnhancedSearchError(error_msg) from e
    def search_grouped_by_code(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, List[SearchResult]]:
        """
        Search for ТНВЭД codes and group results by code.
        
        Performs search across all records and groups results by ТНВЭД code,
        with reference records prioritized within each group.
        
        Args:
            query: Text description of the product to search for
            top_k: Number of top results to return (default: 5)
            
        Returns:
            Dictionary mapping ТНВЭД codes to lists of SearchResult objects
            
        Raises:
            EnhancedSearchError: If query is empty/invalid or search operation fails
            ValueError: If top_k is not positive
            
        Examples:
            >>> searcher = EnhancedSearcher("./chroma_db", normalizer, embedder)
            >>> grouped_results = searcher.search_grouped_by_code("кофе", top_k=10)
            >>> for code, results in grouped_results.items():
            ...     print(f"Code {code}: {len(results)} records")
        """
        # Perform regular search to get all results
        all_results = self.search(query, top_k)
        
        # Group results by ТНВЭД code
        grouped_results = defaultdict(list)
        for result in all_results:
            grouped_results[result.code].append(result)
        
        # Sort results within each group (reference records first, then by similarity)
        for code in grouped_results:
            grouped_results[code] = self._prioritize_results(grouped_results[code])
        
        logger.debug(f"Grouped {len(all_results)} results into {len(grouped_results)} codes")
        
        return dict(grouped_results)
    
    def get_all_records_for_code(self, code: str) -> List[SearchResult]:
        """
        Retrieve all records (reference and product) for a specific ТНВЭД code.
        
        Args:
            code: ТНВЭД code to retrieve records for
            
        Returns:
            List of SearchResult objects for the specified code, prioritized
            
        Raises:
            ValueError: If code is empty
            
        Examples:
            >>> searcher = EnhancedSearcher("./chroma_db", normalizer, embedder)
            >>> records = searcher.get_all_records_for_code("0901110000")
            >>> for record in records:
            ...     print(f"{record.source_type}: {record.description}")
        """
        if not code or not code.strip():
            raise ValueError("Code cannot be empty")
        
        logger.debug(f"Retrieving all records for code: {code}")
        
        # Get all records for this code from ChromaDB
        raw_records = self.db_manager.get_all_records_for_code(code)
        
        if not raw_records:
            logger.info(f"No records found for code: {code}")
            return []
        
        # Convert to SearchResult objects (similarity score is 1.0 for exact code match)
        search_results = []
        for record in raw_records:
            metadata = record.get("metadata", {})
            search_result = SearchResult(
                code=metadata.get("code", code),
                description=metadata.get("description", ""),
                normalized_text=record.get("document", ""),
                similarity_score=1.0,  # Exact match
                source_type=metadata.get("source_type", "reference"),
                source_name=metadata.get("source_name"),
                source_id=metadata.get("source_id")
            )
            search_results.append(search_result)
        
        # Apply prioritization logic
        prioritized_results = self._prioritize_results(search_results)
        
        logger.debug(f"Retrieved {len(prioritized_results)} records for code: {code}")
        return prioritized_results
    
    def _prioritize_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Apply result prioritization logic.
        
        Prioritizes reference records over product records while maintaining
        similarity score ordering within each type.
        
        Args:
            results: List of SearchResult objects to prioritize
            
        Returns:
            List of SearchResult objects in prioritized order
        """
        if not results:
            return results
        
        # Separate reference and product records
        reference_records = []
        product_records = []
        
        for result in results:
            if result.source_type == "reference":
                reference_records.append(result)
            else:
                product_records.append(result)
        
        # Sort each group by similarity score (descending)
        reference_records.sort(key=lambda x: x.similarity_score, reverse=True)
        product_records.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Combine: reference records first, then product records
        prioritized_results = reference_records + product_records
        
        logger.debug(
            f"Prioritized {len(results)} results: "
            f"{len(reference_records)} reference, {len(product_records)} product"
        )
        
        return prioritized_results
    
    def get_database_stats(self) -> Dict:
        """
        Get enhanced statistics about the database.
        
        Returns:
            Dictionary with database statistics including source type breakdown
        """
        # Get basic stats
        total_records = self.db_manager.count()
        
        # Get records by source type
        try:
            # Query for reference records
            ref_results = self.db_manager.collection.get(
                where={"source_type": "reference"},
                include=["metadatas"]
            )
            reference_count = len(ref_results["ids"])
            
            # Query for product records
            prod_results = self.db_manager.collection.get(
                where={"source_type": "product"},
                include=["metadatas"]
            )
            product_count = len(prod_results["ids"])
            
        except Exception as e:
            logger.warning(f"Could not get source type breakdown: {e}")
            reference_count = 0
            product_count = 0
        
        stats = {
            "total_records": total_records,
            "reference_records": reference_count,
            "product_records": product_count,
            "collection_name": self.db_manager.collection_name
        }
        
        logger.debug(f"Enhanced database stats: {stats}")
        return stats