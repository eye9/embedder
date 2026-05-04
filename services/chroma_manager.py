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
        documents: List[str],
        source_type: str = "reference"
    ) -> None:
        """
        Add a batch of records to the collection with upsert functionality
        
        If a record with the same ID exists, it will be updated.
        
        Args:
            ids: List of unique identifiers (ТНВЭД codes)
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            documents: List of document texts (normalized descriptions)
            source_type: Type of source ("reference" or "product")
            
        Raises:
            ValueError: If input lists have different lengths or invalid source_type
        """
        if not (len(ids) == len(embeddings) == len(metadatas) == len(documents)):
            raise ValueError(
                f"All input lists must have the same length. "
                f"Got ids={len(ids)}, embeddings={len(embeddings)}, "
                f"metadatas={len(metadatas)}, documents={len(documents)}"
            )
        
        if source_type not in ["reference", "product"]:
            raise ValueError(f"Invalid source_type: {source_type}. Must be 'reference' or 'product'")
        
        if not ids:
            logger.warning("add_batch called with empty lists, skipping")
            return
        
        logger.debug(f"Adding batch of {len(ids)} records to collection with source_type: {source_type}")
        
        # Enhance metadata with source_type information
        enhanced_metadatas = []
        for metadata in metadatas:
            enhanced_metadata = metadata.copy()
            enhanced_metadata["source_type"] = source_type
            
            # Set default source_name if not provided
            if "source_name" not in enhanced_metadata:
                enhanced_metadata["source_name"] = "tnved_official" if source_type == "reference" else "unknown"
            
            enhanced_metadatas.append(enhanced_metadata)
        
        # ChromaDB's add method performs upsert by default
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=enhanced_metadatas,
            documents=documents
        )
        
        logger.info(f"Successfully added/updated {len(ids)} records with source_type: {source_type}")

    def migrate_existing_records(self) -> int:
        """
        Migrate existing records to include source_type metadata
        
        Assigns source_type "reference" to all existing records that don't have it.
        
        Returns:
            Number of records migrated
        """
        logger.info("Starting migration of existing records")
        
        # Get all records
        all_records = self.collection.get(
            include=["metadatas", "documents", "embeddings"]
        )
        
        migrated_count = 0
        batch_size = 100
        
        for i in range(0, len(all_records["ids"]), batch_size):
            batch_ids = all_records["ids"][i:i + batch_size]
            batch_metadatas = all_records["metadatas"][i:i + batch_size]
            batch_documents = all_records["documents"][i:i + batch_size]
            batch_embeddings = all_records["embeddings"][i:i + batch_size]
            
            updated_metadatas = []
            batch_updated = False
            
            for j, metadata in enumerate(batch_metadatas):
                if "source_type" not in metadata:
                    # Need to migrate this record
                    updated_metadata = metadata.copy()
                    updated_metadata["source_type"] = "reference"
                    updated_metadata["source_name"] = "tnved_official"
                    updated_metadatas.append(updated_metadata)
                    batch_updated = True
                    migrated_count += 1
                else:
                    # Already has source_type, keep as is
                    updated_metadatas.append(metadata)
            
            if batch_updated:
                # Update this batch
                self.collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    metadatas=updated_metadatas,
                    documents=batch_documents
                )
        
        logger.info(f"Migration completed. Updated {migrated_count} records")
        return migrated_count
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        source_filter: Optional[str] = None
    ) -> Dict:
        """
        Perform similarity search using query embedding
        
        Args:
            query_embedding: Query vector for similarity search
            n_results: Number of top results to return
            source_filter: Optional filter by source_type ("reference", "product", or None for all)
            
        Returns:
            Dictionary with query results containing:
                - ids: List of matching ТНВЭД codes
                - distances: List of distance scores
                - metadatas: List of metadata dictionaries
                - documents: List of normalized texts
                
        Raises:
            ValueError: If n_results is not positive or invalid source_filter
        """
        if n_results <= 0:
            raise ValueError(f"n_results must be positive, got {n_results}")
        
        if source_filter is not None and source_filter not in ["reference", "product"]:
            raise ValueError(f"Invalid source_filter: {source_filter}. Must be 'reference', 'product', or None")
        
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
        
        # Build where clause for filtering
        where_clause = None
        if source_filter is not None:
            where_clause = {"source_type": source_filter}
            logger.debug(f"Applying source filter: {source_filter}")
        
        logger.debug(f"Querying collection for top {actual_n_results} results")
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_n_results,
            where=where_clause
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
    
    def get_all_records_for_code(self, code: str) -> List[Dict]:
        """
        Retrieve all records (reference and product) for a specific ТНВЭД code
        
        Args:
            code: ТНВЭД code to retrieve
            
        Returns:
            List of dictionaries with record data
        """
        try:
            # Get records where the code matches (both direct ID and code metadata)
            results = self.collection.get(
                where={"code": code},
                include=["metadatas", "documents", "embeddings"]
            )
            
            records = []
            for i in range(len(results["ids"])):
                embedding_value = None
                if results.get("embeddings") is not None and len(results["embeddings"]) > i:
                    embedding_value = results["embeddings"][i]
                
                record = {
                    "id": results["ids"][i],
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                    "document": results["documents"][i] if results.get("documents") else "",
                    "embedding": embedding_value
                }
                records.append(record)
            
            return records
        except Exception as e:
            logger.error(f"Error retrieving records for code {code}: {e}")
            return []

    def count(self) -> int:
        """
        Get the total number of records in the collection
        
        Returns:
            Number of records
        """
        return self.collection.count()

    @staticmethod
    def _product_source_where(source_name: str) -> Dict:
        """
        Build a ChromaDB filter for product records from a specific source.

        Args:
            source_name: Product data source name

        Returns:
            ChromaDB where clause
        """
        if not source_name or not source_name.strip():
            raise ValueError("source_name cannot be empty")

        return {
            "$and": [
                {"source_type": "product"},
                {"source_name": source_name.strip()}
            ]
        }

    def count_product_records_by_source(self, source_name: str) -> int:
        """
        Count product records for a specific source_name.

        Args:
            source_name: Product data source name

        Returns:
            Number of matching product records
        """
        try:
            results = self.collection.get(
                where=self._product_source_where(source_name),
                include=["metadatas"]
            )
            return len(results["ids"])
        except Exception as e:
            logger.error(f"Error counting product records for source {source_name}: {e}")
            raise

    def delete_product_records_by_source(self, source_name: str) -> int:
        """
        Delete product records for a specific source_name.

        Reference records and product records from other sources are preserved.

        Args:
            source_name: Product data source name

        Returns:
            Number of deleted records
        """
        try:
            results = self.collection.get(
                where=self._product_source_where(source_name),
                include=["metadatas"]
            )
            record_ids = results["ids"]

            if not record_ids:
                logger.info(f"No product records found for source {source_name}")
                return 0

            self.collection.delete(ids=record_ids)
            logger.info(f"Deleted {len(record_ids)} product records for source {source_name}")
            return len(record_ids)
        except Exception as e:
            logger.error(f"Error deleting product records for source {source_name}: {e}")
            raise
    
    def get_statistics_by_source_type(self) -> Dict[str, int]:
        """
        Get record counts by source type
        
        Returns:
            Dictionary with counts for each source type
        """
        try:
            # Get reference records count
            ref_results = self.collection.get(
                where={"source_type": "reference"},
                include=["metadatas"]
            )
            reference_count = len(ref_results["ids"])
            
            # Get product records count
            prod_results = self.collection.get(
                where={"source_type": "product"},
                include=["metadatas"]
            )
            product_count = len(prod_results["ids"])
            
            # Get total count
            total_count = self.count()
            
            # Calculate legacy records (records without source_type)
            legacy_count = total_count - reference_count - product_count
            
            return {
                "reference": reference_count,
                "product": product_count,
                "legacy": legacy_count,
                "total": total_count
            }
        except Exception as e:
            logger.error(f"Error getting statistics by source type: {e}")
            return {
                "reference": 0,
                "product": 0,
                "legacy": 0,
                "total": self.count()
            }
    
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
            # Convert distance to similarity score
            # ChromaDB by default uses squared L2 distance (smaller = more similar)
            # We need to convert distance to similarity score in [0, 1] range
            distance = distances[i]
            
            # For L2/squared L2 distance: smaller distance = higher similarity
            # Use inverse formula: similarity = 1 / (1 + distance)
            # This ensures:
            # - distance = 0 → similarity = 1.0 (perfect match)
            # - distance → ∞ → similarity → 0.0 (no match)
            similarity_score = 1.0 / (1.0 + distance)
            
            # Clamp to [0, 1] range for safety
            similarity_score = max(0.0, min(1.0, similarity_score))
            
            metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            
            search_result = SearchResult(
                code=metadata.get("code") or ids[i],
                description=metadata.get("description", ""),
                normalized_text=documents[i],
                similarity_score=similarity_score,
                source_type=metadata.get("source_type", "reference"),
                source_name=metadata.get("source_name"),
                source_id=metadata.get("source_id")
            )
            search_results.append(search_result)
        
        return search_results
