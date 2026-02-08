"""
Record management router for OpenRecords.
"""
import logging
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from database import get_db_cursor
from middleware.auth import get_current_user
from models.auth import AuthContext
from models.documents import ReindexResponse
from models.records import RecordCreate, RecordResponse, RecordsListResponse, RecordUpdate
from utils.auth import get_current_timestamp
from utils.chunking import count_tokens
from utils.encryption import decrypt_master_key, decrypt_text_with_user_key
from utils.openrouter import get_embeddings
from utils.vectordb import add_vectors, delete_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/records", tags=["records"])

DEFAULT_CHAT_MODEL = "moonshotai/kimi-k2.5"
DEFAULT_EMBED_MODEL = "text-embedding-3-large"


@router.post("/init", response_model=RecordResponse)
async def create_record(
    payload: RecordCreate,
    user: AuthContext = Depends(get_current_user),
):
    """Create a new record for the current user."""
    record_id = f"rec_{uuid.uuid4().hex}"
    timestamp = get_current_timestamp()

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT default_chat_model, default_embed_model
            FROM user_settings
            WHERE user_id = ?
            """,
            (user.user_id,),
        )
        settings_row = cursor.fetchone()

    default_chat_model = settings_row[0] if settings_row else None
    default_embed_model = settings_row[1] if settings_row else None

    chat_model = payload.chat_model or default_chat_model or DEFAULT_CHAT_MODEL
    embed_model = payload.embed_model or default_embed_model or DEFAULT_EMBED_MODEL

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO records (
                id, user_id, name, description, created_at, updated_at, last_opened, chat_model, embed_model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                user.user_id,
                payload.name,
                payload.description,
                timestamp,
                timestamp,
                timestamp,
                chat_model,
                embed_model,
            ),
        )

    return RecordResponse(
        id=record_id,
        user_id=user.user_id,
        name=payload.name,
        description=payload.description,
        created_at=timestamp,
        updated_at=timestamp,
        last_opened=timestamp,
        chat_model=chat_model,
        embed_model=embed_model,
        doc_count=0,
    )


@router.get("", response_model=RecordsListResponse)
async def list_records(user: AuthContext = Depends(get_current_user)):
    """List records for the current user."""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                records.id,
                records.user_id,
                records.name,
                records.description,
                records.created_at,
                records.updated_at,
                records.last_opened,
                records.chat_model,
                records.embed_model,
                COUNT(documents.id) as doc_count
            FROM records
            LEFT JOIN documents ON documents.record_id = records.id
            WHERE records.user_id = ?
            GROUP BY records.id
            ORDER BY records.updated_at DESC
            """,
            (user.user_id,),
        )
        rows = cursor.fetchall()

    records: List[RecordResponse] = [
        RecordResponse(
            id=row[0],
            user_id=row[1],
            name=row[2],
            description=row[3],
            created_at=row[4],
            updated_at=row[5],
            last_opened=row[6],
            chat_model=row[7],
            embed_model=row[8],
            doc_count=row[9] or 0,
        )
        for row in rows
    ]

    return RecordsListResponse(records=records)


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(record_id: str, user: AuthContext = Depends(get_current_user)):
    """Get a record by ID for the current user."""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, user_id, name, description, created_at, updated_at, last_opened, chat_model, embed_model
            FROM records
            WHERE id = ? AND user_id = ?
            """,
            (record_id, user.user_id),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    last_opened = get_current_timestamp()
    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE records SET last_opened = ? WHERE id = ? AND user_id = ?",
            (last_opened, record_id, user.user_id),
        )

    return RecordResponse(
        id=row[0],
        user_id=row[1],
        name=row[2],
        description=row[3],
        created_at=row[4],
        updated_at=row[5],
        last_opened=last_opened,
        chat_model=row[7],
        embed_model=row[8],
        doc_count=0,
    )


@router.patch("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: str,
    payload: RecordUpdate,
    user: AuthContext = Depends(get_current_user),
):
    """Update a record for the current user."""
    updates = {
        "name": payload.name,
        "description": payload.description,
        "chat_model": payload.chat_model,
        "embed_model": payload.embed_model,
    }

    if all(value is None for value in updates.values()):
        raise HTTPException(status_code=400, detail="No updates provided")

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, user_id, name, description, created_at, updated_at, last_opened, chat_model, embed_model
            FROM records
            WHERE id = ? AND user_id = ?
            """,
            (record_id, user.user_id),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        name = updates["name"] if updates["name"] is not None else row[2]
        description = (
            updates["description"] if updates["description"] is not None else row[3]
        )
        chat_model = updates["chat_model"] if updates["chat_model"] is not None else row[7]
        embed_model = updates["embed_model"] if updates["embed_model"] is not None else row[8]
        updated_at = get_current_timestamp()

        cursor.execute(
            """
            UPDATE records
            SET name = ?, description = ?, updated_at = ?, chat_model = ?, embed_model = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, description, updated_at, chat_model, embed_model, record_id, user.user_id),
        )

    return RecordResponse(
        id=record_id,
        user_id=user.user_id,
        name=name,
        description=description,
        created_at=row[4],
        updated_at=updated_at,
        last_opened=row[6],
        chat_model=chat_model,
        embed_model=embed_model,
        doc_count=0,
    )


@router.delete("/{record_id}")
async def delete_record(record_id: str, user: AuthContext = Depends(get_current_user)):
    """Delete a record for the current user."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")

    # Clean up vector collection
    try:
        delete_collection(record_id)
    except Exception:
        pass

    return {"status": "ok"}


@router.post("/{record_id}/reindex", response_model=ReindexResponse)
async def reindex_record(
    record_id: str,
    background_tasks: BackgroundTasks,
    user: AuthContext = Depends(get_current_user),
):
    """Re-index all chunks for a record into the vector DB."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

    encrypted_master_key = user_row[0]

    background_tasks.add_task(
        _reindex_record_task,
        record_id=record_id,
        encrypted_master_key=encrypted_master_key,
    )

    return ReindexResponse(
        status="ok",
        message="Re-indexing started in background.",
        chunks_indexed=0,
    )


async def _reindex_record_task(record_id: str, encrypted_master_key: str) -> None:
    """Background task to rebuild the vector index for a record."""
    try:
        user_key = decrypt_master_key(encrypted_master_key)

        # Delete existing collection
        delete_collection(record_id)

        # Fetch all chunks
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.encrypted_text, c.chunk_index, c.page_number, c.section,
                       d.id, d.filename
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.record_id = ?
                ORDER BY c.chunk_index
                """,
                (record_id,),
            )
            rows = cursor.fetchall()

        if not rows:
            logger.info("No chunks to reindex for record %s", record_id)
            return

        chunk_ids: list[str] = []
        chunk_texts: list[str] = []
        metadatas: list[dict] = []

        for row in rows:
            cid, enc_text, chunk_index, page_num, section, doc_id, filename = row
            try:
                plain = decrypt_text_with_user_key(user_key, enc_text)
            except Exception:
                continue
            chunk_ids.append(cid)
            chunk_texts.append(plain)
            metadatas.append({
                "document_id": doc_id,
                "filename": filename or "unknown",
                "chunk_index": chunk_index or 0,
                "page_number": page_num or 0,
                "section": section or "",
            })

        # Embed all chunks
        embeddings = await get_embeddings(chunk_texts)

        # Index into vector DB
        add_vectors(
            record_id=record_id,
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        logger.info("Reindexed %d chunks for record %s", len(chunk_ids), record_id)

    except Exception as e:
        logger.error("Reindex error for record %s: %s", record_id, e)
