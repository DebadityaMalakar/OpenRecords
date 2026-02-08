"""
Pydantic models for user settings and profile updates.
"""
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic.aliases import AliasChoices


class UserUpdateRequest(BaseModel):
    """Request model to update a user's profile."""

    username: Optional[str] = Field(default=None, min_length=3, max_length=32)
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=64,
        validation_alias=AliasChoices("full_name", "fullName"),
    )
    email: Optional[EmailStr] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v.strip()


class PasswordChangeRequest(BaseModel):
    """Request model to change a user's password."""

    current_password: str = Field(
        ..., min_length=1, validation_alias=AliasChoices("current_password", "currentPassword")
    )
    new_password: str = Field(
        ..., min_length=8, validation_alias=AliasChoices("new_password", "newPassword")
    )


class DeleteAccountRequest(BaseModel):
    """Request model to delete a user account."""

    password: str = Field(..., min_length=1)


class UserSettingsUpdate(BaseModel):
    """Request model to update user settings."""

    default_chat_model: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("default_chat_model", "defaultChatModel")
    )
    default_embed_model: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("default_embed_model", "defaultEmbedModel")
    )
    theme: Optional[str] = None
    temperature: Optional[float] = None


class UserSettingsResponse(BaseModel):
    """Response model for user settings."""

    default_chat_model: Optional[str] = None
    default_embed_model: Optional[str] = None
    theme: Optional[str] = None
    temperature: Optional[float] = None
    updated_at: Optional[str] = None
