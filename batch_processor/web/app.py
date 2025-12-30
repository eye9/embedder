"""
FastAPI application for batch Excel processor.

This module provides the main FastAPI application with authentication middleware,
routing, and error handling for the batch Excel processing system.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import secrets
import time
from pathlib import Path

from ..config.settings import get_config, BatchProcessorConfig
from ..models import ProcessingSession, ProcessingResult, TaskMetrics
from .auth import get_current_user, require_auth, session_manager
from .models import HealthResponse, ServiceInfo, ErrorResponse
from .upload import router as upload_router
from .tasks import router as tasks_router
from .websocket import router as websocket_router, startup_websocket
from .health import router as health_router
from ..services.monitoring import initialize_metrics_collector
from ..services.logging_service import get_structured_logger


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize structured logging
structured_logger = get_structured_logger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    pass


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


class ProcessingError(Exception):
    """Custom exception for processing failures."""
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Batch Excel Processor application")
    structured_logger.log_system_event("startup", "Application starting")
    
    config = get_config()
    logger.info(f"Configuration loaded: debug={config.web.debug}")
    
    # Initialize monitoring services
    try:
        metrics_collector = initialize_metrics_collector()
        structured_logger.log_system_event("monitoring", "Metrics collector initialized")
        logger.info("Monitoring services initialized")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring services: {e}")
        structured_logger.log_error(e, {"component": "monitoring", "stage": "initialization"})
    
    # Initialize WebSocket manager
    await startup_websocket()
    
    structured_logger.log_system_event("startup", "Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Batch Excel Processor application")
    structured_logger.log_system_event("shutdown", "Application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="Batch Excel Processor",
        description="Web-based batch processing system for Excel files with TNVED code assignment",
        version="1.0.0",
        debug=config.web.debug,
        lifespan=lifespan
    )
    
    # Setup static files and templates
    static_dir = Path(__file__).parent.parent / "static"
    templates_dir = Path(__file__).parent.parent / "templates"
    
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add API request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all API requests with timing and response information."""
        start_time = time.time()
        
        # Get user from request if available (for authenticated endpoints)
        user = None
        try:
            if hasattr(request.state, 'user'):
                user = request.state.user
        except:
            pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log API request
        structured_logger.log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            user=user,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_size=request.headers.get("content-length"),
            response_size=response.headers.get("content-length")
        )
        
        return response
    
    # Setup authentication - use the auth module
    app.state.get_current_user = get_current_user
    app.state.require_auth = require_auth
    app.state.session_manager = session_manager
    
    # Include routers
    app.include_router(upload_router)
    app.include_router(tasks_router)
    app.include_router(websocket_router)
    app.include_router(health_router)
    
    # Global exception handlers
    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication failed", "detail": str(exc)}
        )
    
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle validation errors."""
        return JSONResponse(
            status_code=400,
            content={"error": "Validation failed", "detail": str(exc)}
        )
    
    @app.exception_handler(ProcessingError)
    async def processing_exception_handler(request: Request, exc: ProcessingError):
        """Handle processing errors."""
        return JSONResponse(
            status_code=500,
            content={"error": "Processing failed", "detail": str(exc)}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        structured_logger.log_error(exc, {
            "endpoint": str(request.url),
            "method": request.method,
            "client": request.client.host if request.client else None
        })
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": "An unexpected error occurred"}
        )
    
    # Main web interface
    @app.get("/", response_class=HTMLResponse)
    async def main_page(request: Request):
        """Serve the main web interface."""
        return templates.TemplateResponse("index.html", {"request": request})
    
    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            service="batch-excel-processor"
        )
    
    # Main web interface
    @app.get("/", response_class=HTMLResponse)
    async def main_page(request: Request):
        """Serve the main web interface."""
        return templates.TemplateResponse("index.html", {"request": request})
    
    # API info endpoint
    @app.get("/api", response_model=ServiceInfo)
    async def api_info():
        """API information endpoint."""
        return ServiceInfo(
            service="Batch Excel Processor",
            version="1.0.0",
            description="Web-based batch processing system for Excel files with TNVED code assignment",
            endpoints=[
                "/health",
                "/upload",
                "/upload/validate",
                "/task/{task_id}/status",
                "/task/{task_id}/summary",
                "/task/{task_id}/download",
                "/task/{task_id}/download/file",
                "/ws/{task_id}",
                "/ws/info/{task_id}"
            ]
        )
    
    return app


# Create the application instance
app = create_app()