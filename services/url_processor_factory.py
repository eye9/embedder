"""
URL Processor Factory for TNVED Code Matching System

This module provides factory functions to create and configure URL processing
components with proper integration to the existing ChromaDB infrastructure.
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from services.url_normalizer import URLNormalizer
from services.url_database_manager import URLDatabaseManager
from services.url_matcher import URLMatcher
from services.url_security import URLSecurity
from services.url_config import URLProcessingConfig, URLPriority


logger = logging.getLogger(__name__)


class URLProcessorFactory:
    """
    Factory for creating URL processing components
    
    Provides centralized creation and configuration of URL processing
    components with proper integration to existing ChromaDB infrastructure.
    """
    
    @staticmethod
    def create_url_normalizer(config: URLProcessingConfig) -> URLNormalizer:
        """
        Creates URL normalizer with configuration
        
        Args:
            config: URL processing configuration
            
        Returns:
            Configured URLNormalizer instance
        """
        normalizer = URLNormalizer()
        
        # Apply configuration if needed (normalizer is currently stateless)
        logger.info(f"Created URLNormalizer with {len(normalizer.get_supported_shops())} supported shops")
        
        return normalizer
    
    @staticmethod
    def create_url_database_manager(
        chroma_client: chromadb.Client,
        config: URLProcessingConfig
    ) -> URLDatabaseManager:
        """
        Creates URL database manager with existing ChromaDB client
        
        Args:
            chroma_client: Existing ChromaDB client
            config: URL processing configuration
            
        Returns:
            Configured URLDatabaseManager instance
        """
        db_manager = URLDatabaseManager(
            chroma_client=chroma_client,
            collection_name=config.database.collection_name
        )
        
        logger.info(f"Created URLDatabaseManager with collection: {config.database.collection_name}")
        
        return db_manager
    
    @staticmethod
    def create_url_matcher(
        url_db_manager: URLDatabaseManager,
        config: URLProcessingConfig
    ) -> URLMatcher:
        """
        Creates URL matcher with database manager
        
        Args:
            url_db_manager: URL database manager instance
            config: URL processing configuration
            
        Returns:
            Configured URLMatcher instance
        """
        matcher = URLMatcher(
            url_db_manager=url_db_manager,
            timeout_seconds=config.timeout_seconds
        )
        
        logger.info(f"Created URLMatcher with timeout: {config.timeout_seconds}s")
        
        return matcher
    
    @staticmethod
    def create_url_security() -> URLSecurity:
        """
        Creates URL security validator
        
        Returns:
            URLSecurity instance
        """
        security = URLSecurity()
        
        logger.info("Created URLSecurity validator")
        
        return security
    
    @staticmethod
    def create_complete_url_processor(
        db_path: str,
        config: URLProcessingConfig
    ) -> dict:
        """
        Creates complete URL processing system with all components
        
        Args:
            db_path: Path to ChromaDB storage
            config: URL processing configuration
            
        Returns:
            Dictionary with all URL processing components
        """
        logger.info(f"Creating complete URL processing system at: {db_path}")
        
        # Create ChromaDB client (reuse existing pattern)
        chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create all components
        normalizer = URLProcessorFactory.create_url_normalizer(config)
        db_manager = URLProcessorFactory.create_url_database_manager(chroma_client, config)
        matcher = URLProcessorFactory.create_url_matcher(db_manager, config)
        security = URLProcessorFactory.create_url_security()
        
        components = {
            "chroma_client": chroma_client,
            "normalizer": normalizer,
            "db_manager": db_manager,
            "matcher": matcher,
            "security": security,
            "config": config
        }
        
        logger.info("Complete URL processing system created successfully")
        
        return components
    
    @staticmethod
    def create_url_processor_from_existing_client(
        chroma_client: chromadb.Client,
        config: URLProcessingConfig
    ) -> dict:
        """
        Creates URL processing system using existing ChromaDB client
        
        Args:
            chroma_client: Existing ChromaDB client
            config: URL processing configuration
            
        Returns:
            Dictionary with URL processing components
        """
        logger.info("Creating URL processing system with existing ChromaDB client")
        
        # Create components using existing client
        normalizer = URLProcessorFactory.create_url_normalizer(config)
        db_manager = URLProcessorFactory.create_url_database_manager(chroma_client, config)
        matcher = URLProcessorFactory.create_url_matcher(db_manager, config)
        security = URLProcessorFactory.create_url_security()
        
        components = {
            "normalizer": normalizer,
            "db_manager": db_manager,
            "matcher": matcher,
            "security": security,
            "config": config
        }
        
        logger.info("URL processing system created with existing client")
        
        return components
    
    @staticmethod
    def validate_url_processing_setup(components: dict) -> bool:
        """
        Validates that URL processing components are properly set up
        
        Args:
            components: Dictionary with URL processing components
            
        Returns:
            True if setup is valid
        """
        required_components = ["normalizer", "db_manager", "matcher", "security", "config"]
        
        for component in required_components:
            if component not in components:
                logger.error(f"Missing required component: {component}")
                return False
        
        try:
            # Test basic functionality
            normalizer = components["normalizer"]
            test_url = "https://example.com/product/123"
            
            if not normalizer.validate_url(test_url):
                logger.error("URL normalizer validation failed")
                return False
            
            # Test database connection
            db_manager = components["db_manager"]
            stats = db_manager.get_statistics()
            
            if "error" in stats:
                logger.error(f"Database manager error: {stats['error']}")
                return False
            
            logger.info("URL processing setup validation passed")
            return True
            
        except Exception as e:
            logger.error(f"URL processing setup validation failed: {e}")
            return False
    
    @staticmethod
    def get_url_processing_info(components: dict) -> dict:
        """
        Gets information about URL processing setup
        
        Args:
            components: Dictionary with URL processing components
            
        Returns:
            Dictionary with setup information
        """
        info = {
            "components_available": list(components.keys()),
            "config": {},
            "database_stats": {},
            "supported_shops": []
        }
        
        try:
            if "config" in components:
                config = components["config"]
                info["config"] = {
                    "enabled": config.enabled,
                    "priority": config.priority.value,
                    "timeout_seconds": config.timeout_seconds,
                    "collection_name": config.database.collection_name,
                    "security_enabled": config.security.enabled
                }
            
            if "db_manager" in components:
                db_manager = components["db_manager"]
                info["database_stats"] = db_manager.get_statistics()
            
            if "normalizer" in components:
                normalizer = components["normalizer"]
                info["supported_shops"] = normalizer.get_supported_shops()
            
        except Exception as e:
            info["error"] = str(e)
        
        return info