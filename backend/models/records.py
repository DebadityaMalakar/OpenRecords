"""
Pydantic models for record management.
"""
from typing import Optional

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    """Request model to create a record."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    chat_model: Optional[str] = None
    embed_model: Optional[str] = None


class RecordUpdate(BaseModel):
    """Request model to update a record."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    chat_model: Optional[str] = None
    embed_model: Optional[str] = None


class RecordResponse(BaseModel):
    """Response model for a record."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    last_opened: Optional[str] = None
    chat_model: Optional[str] = None
    embed_model: Optional[str] = None
    doc_count: int = 0


class RecordsListResponse(BaseModel):
    """Response model for listing records."""

    records: list[RecordResponse]
