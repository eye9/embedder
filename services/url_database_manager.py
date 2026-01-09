"""
URL Database Manager for TNVED Code Matching System

This module manages URL-to-TNVED code mappings in ChromaDB, providing
functionality for storing, retrieving, and managing URL-based code associations.
"""

import logging
import hashlib
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings
from dataclasses import dataclass

from services.url_normalizer import URLNormalizer, NormalizedURL


logger = logging.getLogger(__name__)


@dataclass
class URLRecord:
    """
    Represents a URL-to-TNVED code mapping record
    
    Attributes:
        id: Unique record identifier
        original_url: Original URL as provided
        normalized_url: Normalized URL used for matching
        tnved_code: Associated TNVED code
        description: Product description
        source_name: Name of data source
        domain: Domain extracted from URL
        product_id: Product ID extracted from URL (if available)
        shop_type: Shop type detected (if available)
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """
    id: str
    original_url: str
    normalized_url: str
    tnved_code: str
    description: str
    source_name: str
    domain: str
    product_id: Optional[str] = None
    shop_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class URLDatabaseManager:
    """
    Manages URL-to-TNVED code mappings in ChromaDB
    
    Features:
    - Stores URL records with normalized URLs as keys
    - Supports batch loading from Excel files
    - Handles duplicate URL updates
    - Provides statistics and management operations
    - Integrates with existing ChromaDB infrastructure
    """
    
    def __init__(
        self, 
        chroma_client: chromadb.Client, 
        collection_name: str = "url_tnved_mapping"
    ):
        """
        Initialize URL database manager
        
        Args:
            chroma_client: ChromaDB client instance
            collection_name: Name of collection for URL mappings
        """
        self.client = chroma_client
        self.collection_name = collection_name
        self.normalizer = URLNormalizer()
        
        # Get or create collection for URL mappings
        self.collection = self._get_or_create_collection()
        
        logger.info(
            f"URLDatabaseManager initialized with collection '{collection_name}' "
            f"containing {self.collection.count()} records"
        )
    
    def _get_or_create_collection(self):
        """Creates or retrieves the URL mapping collection"""
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            return self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "URL to TNVED code mappings",
                    "source_type": "url"
                }
            )
    
    def add_url_record(
        self, 
        url: str, 
        tnved_code: str, 
        description: str, 
        source_name: str
    ) -> bool:
        """
        Adds or updates a URL-to-TNVED code mapping
        
        Args:
            url: Product URL
            tnved_code: Associated TNVED code
            description: Product description
            source_name: Name of data source
            
        Returns:
            True if record was added/updated successfully
        """
        # Normalize URL
        normalized = self.normalizer.normalize_url(url)
        if not normalized:
            logger.warning(f"Failed to normalize URL: {url}")
            return False
        
        # Validate TNVED code format (basic validation)
        if not self._validate_tnved_code(tnved_code):
            logger.warning(f"Invalid TNVED code format: {tnved_code}")
            return False
        
        # Generate record ID based on normalized URL
        record_id = self._generate_record_id(normalized.normalized_url)
        
        try:
            # Check if record already exists
            existing_record = self._get_record_by_id(record_id)
            timestamp = self._get_timestamp()
            
            metadata = {
                "original_url": normalized.original_url,
                "normalized_url": normalized.normalized_url,
                "tnved_code": tnved_code,
                "source_type": "url",
                "source_name": source_name,
                "domain": normalized.domain,
                "product_id": normalized.product_id or "",
                "shop_type": normalized.shop_type or "",
                "updated_at": timestamp
            }
            
            # Set creation timestamp for new records
            if not existing_record:
                metadata["created_at"] = timestamp
            else:
                # Preserve original creation timestamp
                metadata["created_at"] = existing_record.get("created_at", timestamp)
            
            # Upsert record
            self.collection.upsert(
                ids=[record_id],
                documents=[description],
                metadatas=[metadata]
            )
            
            action = "updated" if existing_record else "added"
            logger.info(f"Successfully {action} URL record: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding URL record: {e}")
            return False
    
    def find_by_url(self, url: str) -> Optional[URLRecord]:
        """
        Finds TNVED code mapping by URL
        
        Args:
            url: URL to search for
            
        Returns:
            URLRecord if found, None otherwise
        """
        # Normalize URL for lookup
        normalized = self.normalizer.normalize_url(url)
        if not normalized:
            logger.debug(f"Cannot normalize URL for lookup: {url}")
            return None
        
        record_id = self._generate_record_id(normalized.normalized_url)
        
        try:
            results = self.collection.get(
                ids=[record_id],
                include=["documents", "metadatas"]
            )
            
            if results['ids']:
                metadata = results['metadatas'][0]
                document = results['documents'][0]
                
                return URLRecord(
                    id=record_id,
                    original_url=metadata['original_url'],
                    normalized_url=metadata['normalized_url'],
                    tnved_code=metadata['tnved_code'],
                    description=document,
                    source_name=metadata['source_name'],
                    domain=metadata['domain'],
                    product_id=metadata.get('product_id') or None,
                    shop_type=metadata.get('shop_type') or None,
                    created_at=metadata.get('created_at'),
                    updated_at=metadata.get('updated_at')
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding URL record: {e}")
            return None
    
    def batch_load_from_excel(
        self, 
        file_path: str, 
        source_name: str
    ) -> Dict[str, int]:
        """
        Loads URL records from Excel file
        
        Args:
            file_path: Path to Excel file with URL, Code, Description columns
            source_name: Name to assign as source for all records
            
        Returns:
            Dictionary with loading statistics
        """
        import pandas as pd
        
        stats = {
            "total": 0,
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "invalid_urls": 0,
            "invalid_codes": 0
        }
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = ['URL', 'Code', 'Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            logger.info(f"Loading URL data from {file_path} with {len(df)} rows")
            
            # Process each row
            for index, row in df.iterrows():
                stats["total"] += 1
                
                # Extract and validate data
                url = str(row['URL']).strip() if pd.notna(row['URL']) else ""
                code = str(row['Code']).strip() if pd.notna(row['Code']) else ""
                description = str(row['Description']).strip() if pd.notna(row['Description']) else ""
                
                # Skip rows with missing data
                if not url or not code or not description:
                    stats["skipped"] += 1
                    logger.debug(f"Skipping row {index + 1}: missing data")
                    continue
                
                # Validate URL
                if not self.normalizer.validate_url(url):
                    stats["invalid_urls"] += 1
                    logger.debug(f"Skipping row {index + 1}: invalid URL")
                    continue
                
                # Validate TNVED code
                if not self._validate_tnved_code(code):
                    stats["invalid_codes"] += 1
                    logger.debug(f"Skipping row {index + 1}: invalid TNVED code")
                    continue
                
                # Add record
                if self.add_url_record(url, code, description, source_name):
                    stats["success"] += 1
                else:
                    stats["errors"] += 1
            
            logger.info(f"Batch load completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during batch load: {e}")
            stats["errors"] = stats["total"] - stats["success"]
            return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Returns statistics about the URL database
        
        Returns:
            Dictionary with database statistics
        """
        try:
            total_count = self.collection.count()
            
            if total_count == 0:
                return {
                    "total_records": 0,
                    "by_source": {},
                    "by_domain": {},
                    "by_shop_type": {}
                }
            
            # Get all records to analyze
            all_records = self.collection.get(include=["metadatas"])
            
            source_stats = {}
            domain_stats = {}
            shop_stats = {}
            
            for metadata in all_records['metadatas']:
                # Count by source
                source = metadata.get('source_name', 'unknown')
                source_stats[source] = source_stats.get(source, 0) + 1
                
                # Count by domain
                domain = metadata.get('domain', 'unknown')
                domain_stats[domain] = domain_stats.get(domain, 0) + 1
                
                # Count by shop type
                shop = metadata.get('shop_type', 'unknown')
                if shop:  # Only count non-empty shop types
                    shop_stats[shop] = shop_stats.get(shop, 0) + 1
            
            return {
                "total_records": total_count,
                "by_source": source_stats,
                "by_domain": domain_stats,
                "by_shop_type": shop_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    def delete_by_source(self, source_name: str) -> int:
        """
        Deletes all records from a specific source
        
        Args:
            source_name: Name of source to delete
            
        Returns:
            Number of records deleted
        """
        try:
            # Get records from the specified source
            results = self.collection.get(
                where={"source_name": source_name},
                include=["metadatas"]
            )
            
            if not results['ids']:
                logger.info(f"No records found for source: {source_name}")
                return 0
            
            # Delete the records
            self.collection.delete(ids=results['ids'])
            
            deleted_count = len(results['ids'])
            logger.info(f"Deleted {deleted_count} records from source: {source_name}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting records by source: {e}")
            return 0
    
    def delete_by_domain_pattern(self, domain_pattern: str) -> int:
        """
        Deletes records matching a domain pattern
        
        Args:
            domain_pattern: Regex pattern to match domains
            
        Returns:
            Number of records deleted
        """
        try:
            # Get all records to filter by domain pattern
            all_records = self.collection.get(include=["metadatas"])
            
            matching_ids = []
            for i, metadata in enumerate(all_records['metadatas']):
                domain = metadata.get('domain', '')
                if re.search(domain_pattern, domain, re.IGNORECASE):
                    matching_ids.append(all_records['ids'][i])
            
            if not matching_ids:
                logger.info(f"No records found matching domain pattern: {domain_pattern}")
                return 0
            
            # Delete matching records
            self.collection.delete(ids=matching_ids)
            
            deleted_count = len(matching_ids)
            logger.info(f"Deleted {deleted_count} records matching domain pattern: {domain_pattern}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting records by domain pattern: {e}")
            return 0
    
    def export_to_excel(self, output_path: str) -> bool:
        """
        Exports all URL mappings to Excel file
        
        Args:
            output_path: Path for output Excel file
            
        Returns:
            True if export successful
        """
        try:
            import pandas as pd
            
            # Get all records
            all_records = self.collection.get(
                include=["documents", "metadatas"]
            )
            
            if not all_records['ids']:
                logger.warning("No records to export")
                return False
            
            # Prepare data for DataFrame
            export_data = []
            for i, record_id in enumerate(all_records['ids']):
                metadata = all_records['metadatas'][i]
                description = all_records['documents'][i]
                
                export_data.append({
                    'URL': metadata.get('original_url', ''),
                    'Normalized_URL': metadata.get('normalized_url', ''),
                    'Code': metadata.get('tnved_code', ''),
                    'Description': description,
                    'Source': metadata.get('source_name', ''),
                    'Domain': metadata.get('domain', ''),
                    'Shop_Type': metadata.get('shop_type', ''),
                    'Product_ID': metadata.get('product_id', ''),
                    'Created_At': metadata.get('created_at', ''),
                    'Updated_At': metadata.get('updated_at', '')
                })
            
            # Create DataFrame and export
            df = pd.DataFrame(export_data)
            df.to_excel(output_path, index=False)
            
            logger.info(f"Exported {len(export_data)} records to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return False
    
    def _generate_record_id(self, normalized_url: str) -> str:
        """Generates unique ID for URL record"""
        return f"url_{hashlib.md5(normalized_url.encode()).hexdigest()}"
    
    def _get_timestamp(self) -> str:
        """Returns current ISO timestamp"""
        return datetime.now().isoformat()
    
    def _validate_tnved_code(self, code: str) -> bool:
        """
        Validates TNVED code format
        
        Args:
            code: TNVED code to validate
            
        Returns:
            True if code format is valid
        """
        if not code or not isinstance(code, str):
            return False
        
        # Basic validation: should be 10 digits
        code = code.strip()
        return bool(re.match(r'^\d{10}$', code))
    
    def _get_record_by_id(self, record_id: str) -> Optional[Dict]:
        """Gets record metadata by ID"""
        try:
            results = self.collection.get(
                ids=[record_id],
                include=["metadatas"]
            )
            
            if results['ids']:
                return results['metadatas'][0]
            return None
            
        except Exception:
            return None