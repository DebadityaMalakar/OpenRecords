"""
Pydantic models for document and reference management.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Document models ---


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    status: str
    document_id: str
    chunk_count: int
    message: str = ""


class DocumentInfo(BaseModel):
    """Info about a single document."""

    id: str
    record_id: str
    filename: str
    hash: str
    source_type: str = "file"
    status: str = "processing"
    page_count: Optional[int] = None
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    chunk_count: int = 0


class DocumentsListResponse(BaseModel):
    """Response model for listing documents."""

    documents: List[DocumentInfo]


# --- Reference (web link) models ---


class ReferenceAddRequest(BaseModel):
    """Request to add a web reference."""

    record_id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)


class ReferenceInfo(BaseModel):
    """Info about a web reference."""

    id: str
    record_id: str
    url: str
    title: Optional[str] = None
    status: str = "processing"
    document_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


class ReferenceAddResponse(BaseModel):
    """Response after adding a reference."""

    status: str
    reference_id: str
    message: str = ""


class ReferencesListResponse(BaseModel):
    """Response model for listing references."""

    references: List[ReferenceInfo]


# --- Reindex models ---


class ReindexResponse(BaseModel):
    """Response for reindex operation."""

    status: str
    message: str
    chunks_indexed: int = 0
