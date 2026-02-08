"""
Pydantic models for OpenRouter model management.
Handles request/response validation for model endpoints.
"""
from typing import List, Optional

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Model information returned to frontend."""

    id: str
    provider: str
    name: str
    context_length: Optional[int] = None
    pricing_prompt: Optional[float] = None
    pricing_completion: Optional[float] = None
    categories: List[str] = []
    supports_streaming: bool = False


class ModelsResponse(BaseModel):
    """Response model for model listing."""

    cached: bool
    updated_at: int
    models: List[ModelInfo]


class RefreshResponse(BaseModel):
    """Response model for refresh operation."""

    status: str
    refreshed: bool
    count: Optional[int] = None
    error: Optional[str] = None
