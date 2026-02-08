"""
Pydantic models for RAG queries.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    """Request model for RAG query."""

    record_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    model: Optional[str] = None  # override chat model


class RagSource(BaseModel):
    """Source chunk returned by RAG."""

    document_id: str
    filename: str
    chunk_id: str
    snippet: str
    score: float = 0.0
    page_number: Optional[int] = None
    section: Optional[str] = None


class RagQueryResponse(BaseModel):
    """Response model for RAG query."""

    status: str
    answer: str
    sources: List[RagSource]
    cached: bool = False
    model: Optional[str] = None


class InsightRequest(BaseModel):
    """Request model for full-text insight generation."""

    record_id: str = Field(..., min_length=1)
    prompt: Optional[str] = None  # optional user override
    model: Optional[str] = None   # optional model override


class InsightResponse(BaseModel):
    """Response model for insight generation."""

    status: str
    insights: str
    document_count: int
    chunk_count: int
    model: Optional[str] = None
