"""
API Request and Response Models

This module defines Pydantic models for API requests and responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator
from models.search_result import SearchResult


class SearchRequest(BaseModel):
    """Request model for search endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="Text description to search for")
    top_k: int = Field(5, ge=1, le=50, description="Number of top results to return")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query is not just whitespace"""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace-only")
        return v.strip()


class SearchResultResponse(BaseModel):
    """Response model for individual search result"""
    code: str = Field(..., description="ТНВЭД code")
    description: str = Field(..., description="Original description")
    normalized_text: str = Field(..., description="Normalized text used for search")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    
    @classmethod
    def from_search_result(cls, result: SearchResult) -> "SearchResultResponse":
        """Convert SearchResult to API response model"""
        return cls(
            code=result.code,
            description=result.description,
            normalized_text=result.normalized_text,
            similarity_score=result.similarity_score
        )


class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    results: List[SearchResultResponse] = Field(..., description="List of search results")
    query_time_ms: float = Field(..., ge=0, description="Query execution time in milliseconds")


class LoadRequest(BaseModel):
    """Request model for load endpoint"""
    file_path: str = Field(..., min_length=1, description="Path to Excel file to load")
    batch_size: int = Field(100, ge=1, le=1000, description="Batch size for processing")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        """Validate file path is not empty"""
        if not v.strip():
            raise ValueError("File path cannot be empty")
        return v.strip()


class LoadResponse(BaseModel):
    """Response model for load endpoint"""
    records_loaded: int = Field(..., ge=0, description="Number of records successfully loaded")
    load_time_ms: float = Field(..., ge=0, description="Load time in milliseconds")


class CodeDetailsResponse(BaseModel):
    """Response model for code details endpoint"""
    code: str = Field(..., description="ТНВЭД code")
    description: str = Field(..., description="Original description")
    normalized_text: str = Field(..., description="Normalized text")
    
    @classmethod
    def from_search_result(cls, result: SearchResult) -> "CodeDetailsResponse":
        """Convert SearchResult to code details response model"""
        return cls(
            code=result.code,
            description=result.description,
            normalized_text=result.normalized_text
        )


class HealthResponse(BaseModel):
    """Response model for health endpoint"""
    status: str = Field(..., description="Service status")
    database_records: int = Field(..., ge=0, description="Number of records in database")
    model_loaded: bool = Field(..., description="Whether embedding model is loaded")
    version: str = Field("1.0.0", description="API version")


class StatsResponse(BaseModel):
    """Response model for stats endpoint"""
    total_searches: int = Field(..., ge=0, description="Total number of searches performed")
    total_records: int = Field(..., ge=0, description="Total number of records in database")
    avg_search_time_ms: float = Field(..., ge=0, description="Average search time in milliseconds")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime in seconds")
    database_stats: dict = Field(..., description="Database statistics")


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")