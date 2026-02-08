"""
References (web links) router for OpenRecords.
Handles URL scraping, parsing, chunking, and indexing.
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from database import get_db_cursor
from middleware.auth import get_current_user
from models.auth import AuthContext
from models.documents import (
    ReferenceAddRequest,
    ReferenceAddResponse,
    ReferenceInfo,
    ReferencesListResponse,
)
from utils.auth import get_current_timestamp
from utils.chunking import chunk_text, count_tokens
from utils.encryption import (
    decrypt_master_key,
    encrypt_text_with_user_key,
)
from utils.openrouter import get_embeddings
from utils.scraping import scrape_url
from utils.vectordb import add_vectors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/references", tags=["references"])


async def _process_reference(
    reference_id: str,
    record_id: str,
    url: str,
    encrypted_master_key: str,
) -> None:
    """
    Background task: scrape → chunk → encrypt → embed → index.
    """
    try:
        # 1. Scrape
        text, title, err = await scrape_url(url)
        if err or not text:
            _set_reference_error(reference_id, err or "No content extracted")
            return

        # Update title
        if title:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE references_table SET title = ? WHERE id = ?",
                    (title, reference_id),
                )

        user_key = decrypt_master_key(encrypted_master_key)

        # 2. Create a virtual document for this reference
        document_id = f"doc_{uuid.uuid4().hex}"
        created_at = get_current_timestamp()
        total_tokens = count_tokens(text)

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (
                    id, record_id, filename, encrypted_path, hash,
                    source_type, status, token_count, created_at
                ) VALUES (?, ?, ?, NULL, '', 'link', 'processing', ?, ?)
                """,
                (document_id, record_id, title or url, total_tokens, created_at),
            )

        # 3. Chunk
        chunks = chunk_text(text)
        if not chunks:
            _set_reference_error(reference_id, "No chunks created from scraped content")
            return

        # 4. Encrypt and store chunks
        chunk_ids: list[str] = []
        chunk_texts: list[str] = []

        with get_db_cursor() as cursor:
            for chunk in chunks:
                chunk_id = f"chunk_{uuid.uuid4().hex}"
                encrypted_chunk = encrypt_text_with_user_key(user_key, chunk.text)

                cursor.execute(
                    """
                    INSERT INTO chunks (
                        id, document_id, encrypted_text, token_count,
                        chunk_index, page_number, section
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        document_id,
                        encrypted_chunk,
                        chunk.token_count,
                        chunk.index,
                        chunk.page_number,
                        chunk.section,
                    ),
                )
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk.text)

        # 5. Generate embeddings
        embeddings = await get_embeddings(chunk_texts)

        # 6. Index in vector DB
        metadatas = [
            {
                "document_id": document_id,
                "filename": title or url,
                "chunk_index": chunk.index,
                "source_type": "link",
                "url": url,
            }
            for chunk in chunks
        ]

        add_vectors(
            record_id=record_id,
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        # 7. Update statuses
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE documents SET status = 'indexed' WHERE id = ?",
                (document_id,),
            )
            cursor.execute(
                """
                UPDATE references_table
                SET status = 'indexed', document_id = ?
                WHERE id = ?
                """,
                (document_id, reference_id),
            )

        logger.info(
            "Reference %s processed: %s → %d chunks",
            reference_id, url, len(chunks),
        )

    except Exception as e:
        logger.error("Error processing reference %s: %s", reference_id, e)
        _set_reference_error(reference_id, str(e)[:500])


def _set_reference_error(reference_id: str, error: str) -> None:
    """Set reference status to error."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE references_table SET status = 'error', error_message = ? WHERE id = ?",
            (error, reference_id),
        )


@router.post("/add", response_model=ReferenceAddResponse)
async def add_reference(
    payload: ReferenceAddRequest,
    background_tasks: BackgroundTasks,
    user: AuthContext = Depends(get_current_user),
):
    """Add a web reference to a record."""

    # Validate record ownership
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (payload.record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")

    encrypted_master_key = row[0]
    reference_id = f"ref_{uuid.uuid4().hex}"
    created_at = get_current_timestamp()

    # Insert reference record
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO references_table (
                id, record_id, url, title, status, created_at
            ) VALUES (?, ?, ?, NULL, 'processing', ?)
            """,
            (reference_id, payload.record_id, payload.url, created_at),
        )

    # Kick off background scraping
    background_tasks.add_task(
        _process_reference,
        reference_id=reference_id,
        record_id=payload.record_id,
        url=payload.url,
        encrypted_master_key=encrypted_master_key,
    )

    return ReferenceAddResponse(
        status="ok",
        reference_id=reference_id,
        message="Reference added. Scraping in background.",
    )


@router.get("/list/{record_id}", response_model=ReferencesListResponse)
async def list_references(
    record_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """List all references for a record."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            """
            SELECT id, record_id, url, title, status, document_id, error_message, created_at
            FROM references_table
            WHERE record_id = ?
            ORDER BY created_at DESC
            """,
            (record_id,),
        )
        rows = cursor.fetchall()

    references = [
        ReferenceInfo(
            id=row[0],
            record_id=row[1],
            url=row[2],
            title=row[3],
            status=row[4],
            document_id=row[5],
            error_message=row[6],
            created_at=row[7],
        )
        for row in rows
    ]

    return ReferencesListResponse(references=references)
