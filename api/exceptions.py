"""
API Exception Handlers

This module provides custom exception handlers for the API.
"""

import logging
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.models import ErrorResponse
from services.tnved_searcher import SearchError
from services.tnved_loader import DataLoadError
from utils.config import ConfigurationError


logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error for {request.method} {request.url.path}: {exc.errors()}")
    
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Request validation failed",
            details={"errors": error_details}
        ).dict()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} for {request.method} {request.url.path}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="http_error",
            message=str(exc.detail),
            details={"status_code": exc.status_code}
        ).dict()
    )


async def search_exception_handler(request: Request, exc: SearchError):
    """Handle search-related errors"""
    logger.error(f"Search error for {request.method} {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="search_error",
            message=str(exc),
            details={"type": "search_operation_failed"}
        ).dict()
    )


async def data_load_exception_handler(request: Request, exc: DataLoadError):
    """Handle data loading errors"""
    logger.error(f"Data load error for {request.method} {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="data_load_error",
            message=str(exc),
            details={"type": "data_loading_failed"}
        ).dict()
    )


async def configuration_exception_handler(request: Request, exc: ConfigurationError):
    """Handle configuration errors"""
    logger.error(f"Configuration error for {request.method} {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="configuration_error",
            message="Service configuration error",
            details={"type": "invalid_configuration"}
        ).dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        f"Unhandled exception for {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message="Internal server error",
            details={"type": "unexpected_error"}
        ).dict()
    )


def setup_exception_handlers(app):
    """Setup all exception handlers"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SearchError, search_exception_handler)
    app.add_exception_handler(DataLoadError, data_load_exception_handler)
    app.add_exception_handler(ConfigurationError, configuration_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers configured")