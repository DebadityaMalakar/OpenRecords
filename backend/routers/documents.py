"""
Document upload router for OpenRecords.
Full multi-format parsing pipeline with background processing.
"""
import hashlib
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from config import settings
from database import get_db_cursor
from middleware.auth import get_current_user
from models.auth import AuthContext
from models.documents import DocumentInfo, DocumentsListResponse, DocumentUploadResponse
from utils.auth import get_current_timestamp
from utils.chunking import chunk_pages, count_tokens
from utils.encryption import (
    decrypt_master_key,
    encrypt_bytes_with_user_key,
    encrypt_text_with_user_key,
)
from utils.openrouter import get_embeddings
from utils.parsing import SUPPORTED_EXTENSIONS, detect_extension, extract_text
from utils.vectordb import add_vectors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _process_document(
    document_id: str,
    record_id: str,
    user_id: str,
    raw_bytes: bytes,
    extension: str,
    filename: str,
    encrypted_master_key: str,
) -> None:
    """
    Background task: parse -> chunk -> encrypt -> embed -> index.
    Updates document status in the database throughout.
    """
    try:
        user_key = decrypt_master_key(encrypted_master_key)

        # 1. Extract text
        pages = extract_text(raw_bytes, extension)
        if not pages:
            _set_document_error(document_id, "No extractable text found in file")
            return

        page_count = len(pages)
        full_text = "\n".join(text for _, text in pages)
        total_tokens = count_tokens(full_text)

        # 2. Chunk
        chunks = chunk_pages(pages)
        if not chunks:
            _set_document_error(document_id, "Failed to create text chunks")
            return

        # 3. Encrypt and store chunks
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

        # 4. Generate embeddings
        embeddings = await get_embeddings(chunk_texts)

        # 5. Index in vector DB
        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk.index,
                "page_number": chunk.page_number or 0,
                "section": chunk.section or "",
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

        # 6. Update document status
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET status = 'indexed', page_count = ?, token_count = ?
                WHERE id = ?
                """,
                (page_count, total_tokens, document_id),
            )

        logger.info(
            "Document %s processed: %d pages, %d chunks, %d tokens",
            document_id, page_count, len(chunks), total_tokens,
        )

    except Exception as e:
        logger.error("Error processing document %s: %s", document_id, e)
        _set_document_error(document_id, str(e)[:500])


def _set_document_error(document_id: str, error: str) -> None:
    """Set document status to error."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE documents SET status = 'error', error_message = ? WHERE id = ?",
            (error, document_id),
        )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    record_id: str = Form(...),
    file: UploadFile = File(...),
    user: AuthContext = Depends(get_current_user),
):
    """Upload a document and kick off background processing."""

    # Validate record ownership
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
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")

    encrypted_master_key = row[0]

    # Validate file type
    filename = file.filename or "document"
    content_type = file.content_type
    extension = detect_extension(filename, content_type)

    if extension is None:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    # Read and validate size
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    # Compute hash and create document record
    user_key = decrypt_master_key(encrypted_master_key)
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    document_id = f"doc_{uuid.uuid4().hex}"
    created_at = get_current_timestamp()

    # Store encrypted file on disk
    vault_root = settings.vault_path
    user_dir = Path(vault_root) / user.user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    encrypted_path = user_dir / f"{document_id}.bin"

    encrypted_bytes = encrypt_bytes_with_user_key(user_key, raw_bytes)
    encrypted_path.write_bytes(encrypted_bytes)

    # Insert document record with status = 'processing'
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (
                id, record_id, filename, encrypted_path, hash,
                source_type, status, created_at
            ) VALUES (?, ?, ?, ?, ?, 'file', 'processing', ?)
            """,
            (document_id, record_id, filename, str(encrypted_path), file_hash, created_at),
        )

    # Kick off background processing
    background_tasks.add_task(
        _process_document,
        document_id=document_id,
        record_id=record_id,
        user_id=user.user_id,
        raw_bytes=raw_bytes,
        extension=extension,
        filename=filename,
        encrypted_master_key=encrypted_master_key,
    )

    return DocumentUploadResponse(
        status="ok",
        document_id=document_id,
        chunk_count=0,
        message="Document uploaded. Processing in background.",
    )


@router.get("/list/{record_id}", response_model=DocumentsListResponse)
async def list_documents(
    record_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """List all documents for a record."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            """
            SELECT
                documents.id,
                documents.record_id,
                documents.filename,
                documents.hash,
                documents.source_type,
                documents.status,
                documents.page_count,
                documents.token_count,
                documents.error_message,
                documents.created_at,
                COUNT(chunks.id) as chunk_count
            FROM documents
            LEFT JOIN chunks ON chunks.document_id = documents.id
            WHERE documents.record_id = ?
            GROUP BY documents.id
            ORDER BY documents.created_at DESC
            """,
            (record_id,),
        )
        rows = cursor.fetchall()

    documents = [
        DocumentInfo(
            id=row[0],
            record_id=row[1],
            filename=row[2],
            hash=row[3],
            source_type=row[4] or "file",
            status=row[5] or "processing",
            page_count=row[6],
            token_count=row[7],
            error_message=row[8],
            created_at=row[9],
            chunk_count=row[10] or 0,
        )
        for row in rows
    ]

    return DocumentsListResponse(documents=documents)


@router.get("/status/{document_id}")
async def document_status(
    document_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """Get processing status for a document."""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT d.id, d.status, d.page_count, d.token_count, d.error_message
            FROM documents d
            JOIN records r ON r.id = d.record_id
            WHERE d.id = ? AND r.user_id = ?
            """,
            (document_id, user.user_id),
        )
        row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": row[0],
        "status": row[1],
        "page_count": row[2],
        "token_count": row[3],
        "error_message": row[4],
    }
