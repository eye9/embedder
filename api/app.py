"""
ТНВЭД Embedder FastAPI Application

This module provides the main FastAPI application for the ТНВЭД Embedder system.
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

from api.models import (
    SearchRequest, SearchResponse, SearchResultResponse,
    LoadRequest, LoadResponse,
    CodeDetailsResponse, HealthResponse, StatsResponse
)
from api.middleware import (
    APIKeyAuth, setup_cors_middleware, setup_rate_limiting, setup_logging_middleware, setup_security_headers
)
from api.exceptions import setup_exception_handlers
from services.tnved_searcher import TNVEDSearcher
from services.tnved_loader import TNVEDLoader
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from utils.config import Config


logger = logging.getLogger(__name__)


class TNVEDAPIService:
    """Main API service class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.searcher: TNVEDSearcher = None
        self.loader: TNVEDLoader = None
        self.normalizer: TextNormalizer = None
        self.embedder: EmbeddingGenerator = None
        self.start_time = time.time()
        self.search_count = 0
        self.total_search_time = 0.0
        
        # Initialize FastAPI app
        self.app = self._create_app()
        
        # Setup middleware and exception handlers
        self._setup_middleware()
        self._setup_exception_handlers()
        
        # Setup routes
        self._setup_routes()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application with proper configuration"""
        return FastAPI(
            title="ТНВЭД Embedder API",
            description="""
## ТНВЭД Embedder API

REST API service for semantic search of ТНВЭД codes using vector embeddings.

### Features
- 🔍 **Semantic Search**: Find ТНВЭД codes by text description using AI embeddings
- 📊 **Data Loading**: Load ТНВЭД data from Excel files into vector database
- 🔒 **Authentication**: API key-based authentication (optional)
- 🚦 **Rate Limiting**: Configurable request rate limiting
- 🌐 **CORS Support**: Cross-origin resource sharing for web applications

### Model Information
- **Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Device**: CUDA (with CPU fallback)
- **Embedding Dimension**: 384
- **Languages**: Multilingual support with Russian optimization

### Authentication
When authentication is enabled, include your API key in requests:
- **Header**: `X-API-Key: your-api-key`
- **Bearer Token**: `Authorization: Bearer your-api-key`

### Rate Limiting
- **Default**: 60 requests per minute per IP
- **Configurable**: Set in configuration file
- **Headers**: Rate limit info included in response headers
            """,
            version="1.0.0",
            contact={
                "name": "ТНВЭД Embedder API",
                "url": "https://github.com/your-repo/tnved-embedder",
            },
            license_info={
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
            },
            docs_url="/docs" if not self.config.api.auth.enabled else None,
            redoc_url="/redoc" if not self.config.api.auth.enabled else None,
            openapi_url="/openapi.json" if not self.config.api.auth.enabled else None,
            servers=[
                {
                    "url": f"http://{self.config.api.host}:{self.config.api.port}",
                    "description": "Development server"
                }
            ],
            tags_metadata=[
                {
                    "name": "search",
                    "description": "Search for ТНВЭД codes by text description",
                },
                {
                    "name": "data",
                    "description": "Data loading and management operations",
                },
                {
                    "name": "system",
                    "description": "System health and statistics",
                },
            ],
        )
    
    def _setup_middleware(self):
        """Setup middleware for CORS, rate limiting, logging, and security"""
        # Setup CORS
        setup_cors_middleware(self.app, self.config.api.cors)
        
        # Setup rate limiting
        setup_rate_limiting(self.app, self.config.api.rate_limit)
        
        # Setup request/response logging
        setup_logging_middleware(self.app)
        
        # Setup security headers
        setup_security_headers(self.app)
    
    def _setup_exception_handlers(self):
        """Setup exception handlers"""
        setup_exception_handlers(self.app)
    
    def _setup_routes(self):
        """Setup API routes"""
        # Authentication dependency
        auth = APIKeyAuth(self.config.api.auth.api_keys) if self.config.api.auth.enabled else None
        
        @self.app.on_event("startup")
        async def startup_event():
            """Initialize services on startup"""
            await self._initialize_services()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Cleanup on shutdown"""
            logger.info("API service shutting down")
        
        @self.app.get("/", response_model=dict)
        async def root():
            """Root endpoint"""
            return {
                "service": "ТНВЭД Embedder API",
                "version": "1.0.0",
                "status": "running",
                "docs": "/docs" if not self.config.api.auth.enabled else "Authentication required"
            }
        
        @self.app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
        async def health_check():
            """Health check endpoint
            
            Returns the current health status of the API service including:
            - Service status (healthy/unhealthy)
            - Number of records in database
            - Whether the embedding model is loaded
            - API version
            """
            try:
                database_records = self.searcher.get_database_stats()["total_records"] if self.searcher else 0
                model_loaded = self.embedder is not None
                
                return HealthResponse(
                    status="healthy",
                    database_records=database_records,
                    model_loaded=model_loaded,
                    version="1.0.0"
                )
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "database_records": 0,
                        "model_loaded": False,
                        "version": "1.0.0",
                        "error": str(e)
                    }
                )
        
        @self.app.get("/api/v1/stats", response_model=StatsResponse, tags=["system"])
        async def get_stats(api_key: str = Depends(auth) if auth else None):
            """Get service statistics
            
            Returns detailed statistics about the API service including:
            - Total number of searches performed
            - Total records in database
            - Average search time
            - Service uptime
            - Database statistics
            """
            uptime = time.time() - self.start_time
            avg_search_time = self.total_search_time / max(self.search_count, 1)
            
            database_stats = {}
            if self.searcher:
                database_stats = self.searcher.get_database_stats()
            
            return StatsResponse(
                total_searches=self.search_count,
                total_records=database_stats.get("total_records", 0),
                avg_search_time_ms=avg_search_time * 1000,
                uptime_seconds=uptime,
                database_stats=database_stats
            )
        
        @self.app.post("/api/v1/search", response_model=SearchResponse, tags=["search"])
        async def search_tnved(
            request: SearchRequest,
            api_key: str = Depends(auth) if auth else None
        ):
            """Search for ТНВЭД codes by text description
            
            Performs semantic search using AI embeddings to find the most relevant ТНВЭД codes
            for a given product description.
            
            **Example request:**
            ```json
            {
                "query": "кофейные зерна арабика",
                "top_k": 5
            }
            ```
            
            **Features:**
            - Semantic similarity search using multilingual embeddings
            - Configurable number of results (1-50)
            - Results ranked by similarity score
            - Fast response times with GPU acceleration
            """
            start_time = time.time()
            
            try:
                # Perform search
                results = self.searcher.search(request.query, request.top_k)
                
                # Convert to API response models
                response_results = [
                    SearchResultResponse.from_search_result(result)
                    for result in results
                ]
                
                # Calculate query time
                query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Update statistics
                self.search_count += 1
                self.total_search_time += query_time / 1000  # Store in seconds
                
                return SearchResponse(
                    results=response_results,
                    query_time_ms=query_time
                )
                
            except Exception as e:
                logger.error(f"Search failed for query '{request.query}': {e}")
                raise
        
        @self.app.post("/api/v1/load", response_model=LoadResponse, tags=["data"])
        async def load_data(
            request: LoadRequest,
            api_key: str = Depends(auth) if auth else None
        ):
            """Load ТНВЭД data from Excel file
            
            Loads ТНВЭД codes and descriptions from an Excel file into the vector database.
            The file should contain 'Code' and 'TextEx' columns.
            
            **Process:**
            1. Reads Excel file and validates required columns
            2. Normalizes text descriptions using Russian language processing
            3. Generates vector embeddings for semantic search
            4. Stores data in ChromaDB with batch processing
            
            **Example request:**
            ```json
            {
                "file_path": "/path/to/tnved_data.xlsx",
                "batch_size": 100
            }
            ```
            
            **Note:** This operation may take several minutes for large files.
            """
            start_time = time.time()
            
            try:
                # Load data
                records_loaded = self.loader.load_from_excel(request.file_path)
                
                # Calculate load time
                load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                return LoadResponse(
                    records_loaded=records_loaded,
                    load_time_ms=load_time
                )
                
            except Exception as e:
                logger.error(f"Data loading failed for file '{request.file_path}': {e}")
                raise
        
        @self.app.get("/api/v1/code/{code}", response_model=CodeDetailsResponse, tags=["search"])
        async def get_code_details(
            code: str,
            api_key: str = Depends(auth) if auth else None
        ):
            """Get details for a specific ТНВЭД code
            
            Retrieves detailed information about a specific ТНВЭД code including:
            - Original description
            - Normalized text used for search
            - Code validation and formatting
            
            **Example:** `/api/v1/code/0901110000`
            
            Returns 404 if the code is not found in the database.
            """
            try:
                result = self.searcher.get_code_details(code)
                
                if result is None:
                    return JSONResponse(
                        status_code=404,
                        content={
                            "error": "not_found",
                            "message": f"ТНВЭД code '{code}' not found",
                            "details": {"code": code}
                        }
                    )
                
                return CodeDetailsResponse.from_search_result(result)
                
            except Exception as e:
                logger.error(f"Failed to get details for code '{code}': {e}")
                raise
    
    async def _initialize_services(self):
        """Initialize all services"""
        try:
            logger.info("Initializing ТНВЭД API services...")
            
            # Initialize text normalizer
            logger.info("Initializing text normalizer...")
            self.normalizer = TextNormalizer()
            
            # Initialize embedding generator
            logger.info("Initializing embedding generator...")
            self.embedder = EmbeddingGenerator(
                model_name=self.config.model.name,
                device=self.config.model.device
            )
            
            # Initialize searcher
            logger.info("Initializing ТНВЭД searcher...")
            self.searcher = TNVEDSearcher(
                db_path=self.config.database.path,
                normalizer=self.normalizer,
                embedder=self.embedder,
                collection_name=self.config.database.collection_name
            )
            
            # Initialize loader
            logger.info("Initializing ТНВЭД loader...")
            self.loader = TNVEDLoader(
                db_path=self.config.database.path,
                normalizer=self.normalizer,
                embedder=self.embedder,
                batch_size=self.config.processing.batch_size,
                collection_name=self.config.database.collection_name
            )
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise


def create_app(config: Config = None) -> FastAPI:
    """
    Create and configure FastAPI application
    
    Args:
        config: Configuration object. If None, loads from default sources.
        
    Returns:
        Configured FastAPI application
    """
    if config is None:
        # Try to load from config file first, then environment
        try:
            config = Config.from_file("config.yaml")
            logger.info("Configuration loaded from config.yaml")
        except FileNotFoundError:
            config = Config.from_env()
            logger.info("Configuration loaded from environment variables")
    
    # Validate configuration
    config.validate()
    
    # Create API service
    api_service = TNVEDAPIService(config)
    
    return api_service.app