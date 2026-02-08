"""
Chat messages router for OpenRecords.
Persists and retrieves chat history per record.
"""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import get_db_cursor
from middleware.auth import get_current_user
from models.auth import AuthContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ─── Models ──────────────────────────────────────────

class ChatMessageIn(BaseModel):
    """A single chat message to persist."""
    id: str = Field(..., min_length=1)
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str
    sources: Optional[list] = None
    model: Optional[str] = None
    timestamp: str


class SaveMessagesRequest(BaseModel):
    """Request to save chat messages for a record."""
    record_id: str = Field(..., min_length=1)
    messages: List[ChatMessageIn]


class ChatMessageOut(BaseModel):
    """Chat message returned from the API."""
    id: str
    role: str
    content: str
    sources: Optional[list] = None
    model: Optional[str] = None
    timestamp: str


class ChatHistoryResponse(BaseModel):
    """Response with full chat history for a record."""
    record_id: str
    messages: List[ChatMessageOut]


# ─── Endpoints ───────────────────────────────────────

@router.get("/{record_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    record_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """Get all chat messages for a record."""
    # Verify record ownership
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            """
            SELECT id, role, content, sources, model, created_at
            FROM chat_messages
            WHERE record_id = ?
            ORDER BY created_at ASC
            """,
            (record_id,),
        )
        rows = cursor.fetchall()

    messages = []
    for row in rows:
        sources = None
        if row[3]:
            try:
                sources = json.loads(row[3])
            except (json.JSONDecodeError, TypeError):
                sources = None

        messages.append(ChatMessageOut(
            id=row[0],
            role=row[1],
            content=row[2],
            sources=sources,
            model=row[4],
            timestamp=row[5],
        ))

    return ChatHistoryResponse(record_id=record_id, messages=messages)


@router.post("/{record_id}", response_model=ChatHistoryResponse)
async def save_chat_messages(
    record_id: str,
    payload: SaveMessagesRequest,
    user: AuthContext = Depends(get_current_user),
):
    """Save (upsert) chat messages for a record. Replaces the full history."""
    if payload.record_id != record_id:
        raise HTTPException(status_code=400, detail="Record ID mismatch")

    # Verify record ownership
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        # Delete existing messages and replace
        cursor.execute("DELETE FROM chat_messages WHERE record_id = ?", (record_id,))

        for msg in payload.messages:
            sources_json = json.dumps(msg.sources) if msg.sources else None
            cursor.execute(
                """
                INSERT INTO chat_messages (id, record_id, role, content, sources, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (msg.id, record_id, msg.role, msg.content, sources_json, msg.model, msg.timestamp),
            )

    logger.info("Saved %d messages for record %s", len(payload.messages), record_id)

    # Return saved messages
    return await get_chat_history(record_id, user)


@router.delete("/{record_id}")
async def clear_chat_history(
    record_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """Clear all chat messages for a record."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute("DELETE FROM chat_messages WHERE record_id = ?", (record_id,))

    return {"status": "ok", "detail": "Chat history cleared"}
