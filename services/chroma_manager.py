"""
ChromaDB Manager for ТНВЭД Embedder System
"""

import logging
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

from models.search_result import SearchResult


logger = logging.getLogger(__name__)


class ChromaDBManager:
    """
    Manages ChromaDB operations for ТНВЭД embeddings
    
    Handles persistent storage, batch insertion with upsert,
    and similarity search operations.
    """
    
    def __init__(self, db_path: str, collection_name: str = "tnved"):
        """
        Initialize ChromaDB manager with persistent storage
        
        Args:
            db_path: Path to ChromaDB persistent storage directory
            collection_name: Name of the collection to use
        """
        self.db_path = db_path
        self.collection_name = collection_name
        
        logger.info(f"Initializing ChromaDB at {db_path}")
        
        # Initialize persistent client
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "ТНВЭД codes and descriptions"}
        )
        
        logger.info(f"Collection '{collection_name}' initialized with {self.collection.count()} records")
    
    def add_batch(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        documents: List[str]
    ) -> None:
        """
        Add a batch of records to the collection with upsert functionality
        
        If a record with the same ID exists, it will be updated.
        
        Args:
            ids: List of unique identifiers (ТНВЭД codes)
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            documents: List of document texts (normalized descriptions)
            
        Raises:
            ValueError: If input lists have different lengths
        """
        if not (len(ids) == len(embeddings) == len(metadatas) == len(documents)):
            raise ValueError(
                f"All input lists must have the same length. "
                f"Got ids={len(ids)}, embeddings={len(embeddings)}, "
                f"metadatas={len(metadatas)}, documents={len(documents)}"
            )
        
        if not ids:
            logger.warning("add_batch called with empty lists, skipping")
            return
        
        logger.debug(f"Adding batch of {len(ids)} records to collection")
        
        # ChromaDB's add method performs upsert by default
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        logger.info(f"Successfully added/updated {len(ids)} records")
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5
    ) -> Dict:
        """
        Perform similarity search using query embedding
        
        Args:
            query_embedding: Query vector for similarity search
            n_results: Number of top results to return
            
        Returns:
            Dictionary with query results containing:
                - ids: List of matching ТНВЭД codes
                - distances: List of distance scores
                - metadatas: List of metadata dictionaries
                - documents: List of normalized texts
                
        Raises:
            ValueError: If n_results is not positive
        """
        if n_results <= 0:
            raise ValueError(f"n_results must be positive, got {n_results}")
        
        # Get total count to avoid requesting more than available
        total_count = self.collection.count()
        actual_n_results = min(n_results, total_count)
        
        if actual_n_results == 0:
            logger.warning("Collection is empty, returning empty results")
            return {
                "ids": [[]],
                "distances": [[]],
                "metadatas": [[]],
                "documents": [[]]
            }
        
        logger.debug(f"Querying collection for top {actual_n_results} results")
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_n_results
        )
        
        logger.info(f"Query returned {len(results['ids'][0])} results")
        
        return results
    
    def get_by_code(self, code: str) -> Optional[Dict]:
        """
        Retrieve a specific ТНВЭД record by code
        
        Args:
            code: ТНВЭД code to retrieve
            
        Returns:
            Dictionary with record data or None if not found
        """
        try:
            result = self.collection.get(
                ids=[code],
                include=["metadatas", "documents", "embeddings"]
            )
            
            # Check if we got any results
            if len(result["ids"]) > 0:
                embedding_value = None
                if result.get("embeddings") is not None and len(result["embeddings"]) > 0:
                    embedding_value = result["embeddings"][0]
                
                return {
                    "id": result["ids"][0],
                    "metadata": result["metadatas"][0] if result.get("metadatas") else {},
                    "document": result["documents"][0] if result.get("documents") else "",
                    "embedding": embedding_value
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving code {code}: {e}")
            return None
    
    def count(self) -> int:
        """
        Get the total number of records in the collection
        
        Returns:
            Number of records
        """
        return self.collection.count()
    
    def delete_collection(self) -> None:
        """
        Delete the entire collection
        
        Warning: This operation cannot be undone!
        """
        logger.warning(f"Deleting collection '{self.collection_name}'")
        self.client.delete_collection(name=self.collection_name)
        logger.info(f"Collection '{self.collection_name}' deleted")
    
    def reset(self) -> None:
        """
        Reset the collection by deleting and recreating it
        
        Warning: This operation cannot be undone!
        """
        logger.warning(f"Resetting collection '{self.collection_name}'")
        self.delete_collection()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "ТНВЭД codes and descriptions"}
        )
        logger.info(f"Collection '{self.collection_name}' reset")
    
    def to_search_results(self, query_results: Dict) -> List[SearchResult]:
        """
        Convert ChromaDB query results to SearchResult objects
        
        Args:
            query_results: Results from ChromaDB query
            
        Returns:
            List of SearchResult objects
        """
        search_results = []
        
        # ChromaDB returns nested lists, extract first element
        ids = query_results["ids"][0] if query_results["ids"] else []
        distances = query_results["distances"][0] if query_results["distances"] else []
        metadatas = query_results["metadatas"][0] if query_results["metadatas"] else []
        documents = query_results["documents"][0] if query_results["documents"] else []
        
        for i in range(len(ids)):
            # Convert distance to similarity score (1 - normalized_distance)
            # ChromaDB uses L2 distance by default, convert to similarity
            distance = distances[i]
            similarity_score = 1.0 / (1.0 + distance)  # Convert distance to similarity
            
            metadata = metadatas[i]
            
            search_result = SearchResult(
                code=ids[i],
                description=metadata.get("description", ""),
                normalized_text=documents[i],
                similarity_score=similarity_score
            )
            search_results.append(search_result)
        
        return search_results
