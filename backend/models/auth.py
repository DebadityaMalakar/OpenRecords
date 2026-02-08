"""
Pydantic models for OpenRecords authentication.
Handles request/response validation and serialization.
"""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic.aliases import AliasChoices


class SignupRequest(BaseModel):
    """Request model for user signup."""

    username: str = Field(..., min_length=3, max_length=32)
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=64,
        validation_alias=AliasChoices("full_name", "fullName"),
    )
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format - alphanumeric and underscore only."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username must contain only alphanumeric characters and underscores"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name - at least 2 characters."""
        if len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v.strip()


class LoginRequest(BaseModel):
    """Request model for user login."""

    email_or_username: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("email_or_username", "emailOrUsername"),
    )
    password: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    """Response model for authentication operations."""

    status: str = "ok"
    user_id: Optional[str] = None
    user: Optional["UserPublic"] = None


class ErrorResponse(BaseModel):
    """Response model for errors."""

    detail: str


class UserInDB(BaseModel):
    """User model as stored in the database."""

    id: str
    username: str
    full_name: str
    email: str
    password_hash: str
    encrypted_master_key: str
    created_at: str
    last_login: Optional[str] = None


class UserPublic(BaseModel):
    """User model for public exposure (without sensitive data)."""

    id: str
    username: str
    full_name: str
    email: str
    created_at: str
    last_login: Optional[str] = None


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user id
    username: str
    exp: int  # expiration timestamp


class AuthContext(BaseModel):
    """Context attached to authenticated requests."""

    user_id: str
    username: str
