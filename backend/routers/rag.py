"""
RAG query router for OpenRecords.
Hybrid retrieval (vector + regex/keyword) + LLM generation via OpenRouter.
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Response
from typing import List, Optional, Literal
from pydantic import BaseModel
import base64
from io import BytesIO
from datetime import datetime
import uuid
import httpx
import fitz

from database import get_db_cursor
from middleware.auth import get_current_user
from models.auth import AuthContext
from models.rag import RagQueryRequest, RagQueryResponse, RagSource, InsightRequest, InsightResponse
from utils.encryption import decrypt_master_key, decrypt_text_with_user_key
from utils.auth import get_current_timestamp
from utils.openrouter import (
    chat_completion,
    get_embeddings,
    DEFAULT_CHAT_MODEL,
    OPENROUTER_HTTP_REFERER,
    OPENROUTER_X_TITLE,
)
from utils.retrieval import hybrid_retrieve

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])

RAG_SYSTEM_PROMPT = """You are a helpful research assistant for OpenRecords.
Use the following sources to answer the user's question.
If the sources don't contain enough information to answer, say so honestly.
Always cite which source(s) you used.  Use Markdown formatting for readability:
headings, bullet lists, bold, code blocks where appropriate.  Be concise and accurate."""

RAG_USER_TEMPLATE = """Sources:
{sources}

Question: {query}"""


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(
    payload: RagQueryRequest,
    user: AuthContext = Depends(get_current_user),
):
    """RAG query: embed query → vector search → decrypt → LLM generation."""

    # Validate record ownership
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, chat_model FROM records WHERE id = ? AND user_id = ?",
            (payload.record_id, user.user_id),
        )
        record_row = cursor.fetchone()
        if record_row is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

    record_chat_model = record_row[1]
    user_key = decrypt_master_key(user_row[0])
    query_text = payload.query.strip()

    # 1. Embed the query
    query_embeddings = await get_embeddings([query_text])
    if not query_embeddings or not query_embeddings[0]:
        raise HTTPException(status_code=500, detail="Failed to generate query embedding")

    query_embedding = query_embeddings[0]

    # 2. Decrypt all chunks for this record (needed for keyword search)
    decrypted_chunks: dict[str, tuple[str, dict]] = {}
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id, c.encrypted_text, c.page_number, c.section,
                   d.id, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.record_id = ?
            """,
            (payload.record_id,),
        )
        chunk_rows = cursor.fetchall()

    for chunk_id, encrypted_text, page_number, section, document_id, filename in chunk_rows:
        try:
            plain_text = decrypt_text_with_user_key(user_key, encrypted_text)
        except Exception:
            logger.warning("Failed to decrypt chunk %s", chunk_id)
            continue
        decrypted_chunks[chunk_id] = (
            plain_text,
            {
                "document_id": document_id,
                "filename": filename or "unknown",
                "page_number": page_number,
                "section": section,
            },
        )

    if not decrypted_chunks:
        return RagQueryResponse(
            status="ok",
            answer="No documents found in this record. Upload some files first.",
            sources=[],
            cached=False,
            model=None,
        )

    # 3. Hybrid retrieval (vector + regex, fused with RRF)
    hits = await hybrid_retrieve(
        record_id=payload.record_id,
        query=query_text,
        query_embedding=query_embedding,
        decrypted_chunks=decrypted_chunks,
        top_k=payload.top_k,
    )

    if not hits:
        return RagQueryResponse(
            status="ok",
            answer="No relevant sources found for your query. Try uploading more documents or rephrasing your question.",
            sources=[],
            cached=False,
            model=None,
        )

    # 4. Build sources list
    sources: list[RagSource] = []
    source_texts: list[str] = []

    for hit in hits:
        meta = hit.metadata
        snippet = hit.document[:500].strip().replace("\n", " ")
        # Combined score: RRF is the primary, but expose vector & keyword too
        score = round(hit.rrf_score, 4) if hit.rrf_score else round(hit.vector_score, 4)

        sources.append(
            RagSource(
                document_id=meta.get("document_id", ""),
                filename=meta.get("filename", "unknown"),
                chunk_id=hit.chunk_id,
                snippet=snippet,
                score=score,
                page_number=meta.get("page_number"),
                section=meta.get("section"),
            )
        )
        source_texts.append(hit.document)

    # 5. Build prompt and call LLM
    sources_text = ""
    for i, (src, text) in enumerate(zip(sources, source_texts), 1):
        page_info = f" (page {src.page_number})" if src.page_number else ""
        sources_text += f"[Source {i}: {src.filename}{page_info}]\n{text}\n\n"

    chat_model = payload.model or record_chat_model or DEFAULT_CHAT_MODEL

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": RAG_USER_TEMPLATE.format(
                sources=sources_text,
                query=query_text,
            ),
        },
    ]

    answer = await chat_completion(messages=messages, model=chat_model)

    return RagQueryResponse(
        status="ok",
        answer=answer,
        sources=sources,
        cached=False,
        model=chat_model,
    )


# ── Insight Generator ── full-text analysis, bypasses retrieval ──

INSIGHT_SYSTEM_PROMPT = """You are a senior research analyst for OpenRecords.
You have access to the COMPLETE text of every document the user has uploaded.
Produce a thorough, well-structured Markdown report covering the following sections.
Use rich Markdown: headers, bullet lists, bold, block-quotes for notable quotes,
and horizontal rules between sections.

## Required Sections

1. **Executive Summary** – 3-5 sentence overview of the entire corpus.
2. **Key Themes** – Major recurring themes across all documents.  List each theme
   with a brief explanation and which document(s) it appears in.
3. **Critical Insights** – Non-obvious findings, patterns, or data points that a
   reader might miss on a first pass.
4. **Notable Quotes** – 3-6 direct quotes that are especially significant.
   Use Markdown block-quotes (> ).
5. **Connections & Cross-References** – How the documents relate to each other:
   shared topics, contradicting claims, complementary evidence.
6. **Contradictions & Tensions** – Any conflicting information between sources.
7. **Open Questions** – 4-8 thought-provoking questions raised by the material
   that are not answered in the sources.
8. **Document Statistics** – A brief table listing each document, its approximate
   word count, and its primary topic.

Be thorough.  Cite documents by filename where possible."""

INSIGHT_USER_TEMPLATE = """Below is the FULL TEXT of all documents in this record.

{documents}

{user_prompt}"""


@router.post("/insights", response_model=InsightResponse)
async def generate_insights(
    payload: InsightRequest,
    user: AuthContext = Depends(get_current_user),
):
    """Full-text insight generation — reads every chunk, bypasses retrieval."""

    # Validate record ownership
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, chat_model FROM records WHERE id = ? AND user_id = ?",
            (payload.record_id, user.user_id),
        )
        record_row = cursor.fetchone()
        if record_row is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

    record_chat_model = record_row[1]
    user_key = decrypt_master_key(user_row[0])

    # Decrypt ALL chunks and group by document
    doc_texts: dict[str, list[tuple[int, str]]] = {}  # filename -> [(chunk_index, text)]
    chunk_count = 0

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id, c.encrypted_text, c.chunk_index,
                   d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.record_id = ?
            ORDER BY d.filename, c.chunk_index
            """,
            (payload.record_id,),
        )
        chunk_rows = cursor.fetchall()

    for chunk_id, encrypted_text, chunk_index, filename in chunk_rows:
        try:
            plain_text = decrypt_text_with_user_key(user_key, encrypted_text)
        except Exception:
            logger.warning("Failed to decrypt chunk %s", chunk_id)
            continue
        doc_texts.setdefault(filename or "unknown", []).append((chunk_index or 0, plain_text))
        chunk_count += 1

    if not doc_texts:
        return InsightResponse(
            status="ok",
            insights="No documents found in this record. Upload some files first.",
            document_count=0,
            chunk_count=0,
            model=None,
        )

    # Reconstruct full documents in chunk order
    documents_block = ""
    for filename, chunks in doc_texts.items():
        chunks.sort(key=lambda c: c[0])
        full_text = "\n".join(text for _, text in chunks)
        documents_block += f"\n\n---\n### Document: {filename}\n\n{full_text}"

    # Build prompt
    user_prompt = payload.prompt or "Generate comprehensive insights from these documents."
    chat_model = payload.model or record_chat_model or DEFAULT_CHAT_MODEL

    messages = [
        {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": INSIGHT_USER_TEMPLATE.format(
                documents=documents_block.strip(),
                user_prompt=user_prompt,
            ),
        },
    ]

    logger.info(
        "Insight generation: %d docs, %d chunks, model=%s",
        len(doc_texts), chunk_count, chat_model,
    )

    answer = await chat_completion(messages=messages, model=chat_model, max_tokens=8192)

    return InsightResponse(
        status="ok",
        insights=answer,
        document_count=len(doc_texts),
        chunk_count=chunk_count,
        model=chat_model,
    )


# ── Summary Generator ──

class SummaryResponse(BaseModel):
    summary: str
    document_count: int
    chunk_count: int
    model: str

class SummaryRequest(BaseModel):
    record_id: str
    model: str | None = None

class OutlineResponse(BaseModel):
    outline: str
    document_count: int
    chunk_count: int
    model: str

class OutlineRequest(BaseModel):
    record_id: str
    model: str | None = None

class PdfRequest(BaseModel):
    record_id: str

class PdfResponse(BaseModel):
    pdf_id: str
    page_count: int
    chunk_count: int
    model: str

SUMMARY_SYSTEM_PROMPT = """You are a concise research summarizer for OpenRecords.
Produce a clear, well-structured summary of the entire corpus.
Use Markdown headings and bullet lists. Keep it crisp and factual."""

@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    payload: "SummaryRequest",
    user: AuthContext = Depends(get_current_user),
):
    """Full-text summary generation — reads every chunk, bypasses retrieval."""

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, chat_model FROM records WHERE id = ? AND user_id = ?",
            (payload.record_id, user.user_id),
        )
        record_row = cursor.fetchone()
        if record_row is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

    record_chat_model = record_row[1]
    user_key = decrypt_master_key(user_row[0])

    doc_texts: dict[str, list[tuple[int, str]]] = {}
    chunk_count = 0

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT c.encrypted_text, c.chunk_index, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.record_id = ?
            ORDER BY d.filename, c.chunk_index
            """,
            (payload.record_id,),
        )
        chunk_rows = cursor.fetchall()

    for encrypted_text, chunk_index, filename in chunk_rows:
        try:
            plain_text = decrypt_text_with_user_key(user_key, encrypted_text)
        except Exception:
            logger.warning("Failed to decrypt chunk for summary")
            continue
        doc_texts.setdefault(filename or "unknown", []).append((chunk_index or 0, plain_text))
        chunk_count += 1

    if not doc_texts:
        return SummaryResponse(
            summary="No documents found in this record. Upload some files first.",
            document_count=0,
            chunk_count=0,
            model=record_chat_model or DEFAULT_CHAT_MODEL,
        )

    documents_block = ""
    for filename, chunks in doc_texts.items():
        chunks.sort(key=lambda c: c[0])
        full_text = "\n".join(text for _, text in chunks)
        documents_block += f"\n\n---\n### Document: {filename}\n\n{full_text}"

    chat_model = payload.model or record_chat_model or DEFAULT_CHAT_MODEL

    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": documents_block.strip()},
    ]

    summary = await chat_completion(messages=messages, model=chat_model, max_tokens=4096)

    return SummaryResponse(
        summary=summary,
        document_count=len(doc_texts),
        chunk_count=chunk_count,
        model=chat_model,
    )


# ── Outline Generator ──

OUTLINE_SYSTEM_PROMPT = """You are an expert information architect.
Generate a clean, hierarchical outline of the corpus.
Use Markdown with clear headings and nested bullets."""

@router.post("/outline", response_model=OutlineResponse)
async def generate_outline(
    payload: "OutlineRequest",
    user: AuthContext = Depends(get_current_user),
):
    """Full-text outline generation — reads every chunk, bypasses retrieval."""

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, chat_model FROM records WHERE id = ? AND user_id = ?",
            (payload.record_id, user.user_id),
        )
        record_row = cursor.fetchone()
        if record_row is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

    record_chat_model = record_row[1]
    user_key = decrypt_master_key(user_row[0])

    doc_texts: dict[str, list[tuple[int, str]]] = {}
    chunk_count = 0

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT c.encrypted_text, c.chunk_index, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.record_id = ?
            ORDER BY d.filename, c.chunk_index
            """,
            (payload.record_id,),
        )
        chunk_rows = cursor.fetchall()

    for encrypted_text, chunk_index, filename in chunk_rows:
        try:
            plain_text = decrypt_text_with_user_key(user_key, encrypted_text)
        except Exception:
            logger.warning("Failed to decrypt chunk for outline")
            continue
        doc_texts.setdefault(filename or "unknown", []).append((chunk_index or 0, plain_text))
        chunk_count += 1

    if not doc_texts:
        return OutlineResponse(
            outline="No documents found in this record. Upload some files first.",
            document_count=0,
            chunk_count=0,
            model=record_chat_model or DEFAULT_CHAT_MODEL,
        )

    documents_block = ""
    for filename, chunks in doc_texts.items():
        chunks.sort(key=lambda c: c[0])
        full_text = "\n".join(text for _, text in chunks)
        documents_block += f"\n\n---\n### Document: {filename}\n\n{full_text}"

    chat_model = payload.model or record_chat_model or DEFAULT_CHAT_MODEL

    summary_messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": documents_block.strip()},
    ]

    summary_text = await chat_completion(messages=summary_messages, model=chat_model, max_tokens=4096)

    outline_messages = [
        {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Summary:\n{summary_text}"},
    ]

    outline = await chat_completion(messages=outline_messages, model=chat_model, max_tokens=2048)

    return OutlineResponse(
        outline=outline,
        document_count=len(doc_texts),
        chunk_count=chunk_count,
        model=chat_model,
    )

class InfographicRequest(BaseModel):
    record_id: str
    depth: Literal["standard", "detailed"] = "standard"
    custom_prompt: str | None = None

class InfographicResponse(BaseModel):
    image_url: str  # base64 data URL or storage path
    image_id: str   # for future retrieval
    prompt_used: str
    document_count: int
    chunk_count: int
    model: str


@router.post("/infographic", response_model=InfographicResponse)
async def generate_infographic(
    req: InfographicRequest,
    user: AuthContext = Depends(get_current_user),
):
    """
    Generate an infographic visualization from all documents in a record.
    Supports standard (summary-based) or detailed (chunk-by-chunk) depth.
    """
    from config import settings

    # ── Verify record ownership and get user key ──
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (req.record_id, user.user_id),
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

    user_key = decrypt_master_key(user_row[0])

    # ── Gather all document chunks (decrypt) ──
    doc_chunks: dict[str, list[tuple[int, str]]] = {}
    doc_titles: dict[str, str] = {}
    chunk_count = 0

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT c.encrypted_text, c.chunk_index, d.id, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.record_id = ?
            ORDER BY d.id, c.chunk_index
            """,
            (req.record_id,),
        )
        chunk_rows = cursor.fetchall()

    for encrypted_text, chunk_index, document_id, filename in chunk_rows:
        try:
            plain_text = decrypt_text_with_user_key(user_key, encrypted_text)
        except Exception:
            logger.warning("Failed to decrypt chunk for document %s", document_id)
            continue

        doc_chunks.setdefault(document_id, []).append((chunk_index or 0, plain_text))
        if document_id not in doc_titles:
            doc_titles[document_id] = filename or "unknown"
        chunk_count += 1

    if not doc_chunks:
        raise HTTPException(status_code=400, detail="No document chunks found. Upload sources first.")

    doc_ids = list(doc_chunks.keys())

    # ── Build the content for infographic generation ──
    if req.depth == "detailed":
        chunk_summaries: list[str] = []
        for document_id, chunks in doc_chunks.items():
            title = doc_titles.get(document_id, document_id)
            chunks.sort(key=lambda c: c[0])
            for i, (_, text) in enumerate(chunks[:20]):
                snippet = text.strip()
                if not snippet:
                    continue
                snippet = snippet[:300] + ("..." if len(snippet) > 300 else "")
                chunk_summaries.append(f"**{title} - Chunk {i + 1}**: {snippet}")

        content_text = "\n\n".join(chunk_summaries[:50])
    else:
        summaries: list[str] = []
        for document_id, chunks in doc_chunks.items():
            title = doc_titles.get(document_id, document_id)
            chunks.sort(key=lambda c: c[0])
            combined = " ".join(text for _, text in chunks)
            combined = combined[:2000]
            summaries.append(f"**{title}**: {combined}")

        content_text = "\n\n".join(summaries)

    # Truncate to fit context
    MAX_CHARS = 4000
    if len(content_text) > MAX_CHARS:
        content_text = content_text[:MAX_CHARS] + "\n\n[...truncated...]"

    # ── Build the prompt ──
    if req.custom_prompt and req.custom_prompt.strip():
        final_prompt = f"{req.custom_prompt.strip()}\n\n---\n\nSource content:\n{content_text}"
    else:
        system_base = (
            "Create a visually stunning infographic that summarizes the following research content. "
            "Use a professional design with clear sections, icons, charts, and data visualizations. "
            "Include key statistics, main themes, and important findings. "
            "Use a modern color palette and readable typography."
        )
        final_prompt = f"{system_base}\n\n---\n\nContent to visualize:\n{content_text}"

    # ── Call OpenRouter image generation API ──
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or getattr(settings, "openrouter_api_key", None)
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured in settings")

    model = "google/gemini-3-pro-image-preview"

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": OPENROUTER_HTTP_REFERER,
                    "X-Title": OPENROUTER_X_TITLE,
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": final_prompt}],
                    "modalities": ["image", "text"],
                },
            )

            if response.status_code != 200:
                error_text = response.text
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenRouter API error ({response.status_code}): {error_text[:200]}"
                )

            data = response.json()

        # Extract image from response
        message = data.get("choices", [{}])[0].get("message", {})
        images = message.get("images", [])

        if not images:
            # Some models return image in content as base64
            content = message.get("content", "")
            if content and content.startswith("data:image"):
                image_data = content
            else:
                raise HTTPException(status_code=502, detail="No image generated by model. Response: " + str(message)[:200])
        else:
            image_data = images[0].get("image_url", {}).get("url", "")
            if not image_data:
                image_data = images[0].get("url", "")

        if not image_data:
            raise HTTPException(status_code=502, detail="Invalid image response format")

        # ── Store image in database ──
        image_id = f"img_{uuid.uuid4().hex}"
        created_at = get_current_timestamp()
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO generated_images (
                    id, record_id, user_id, type, image_data, prompt,
                    depth, model, created_at, document_count, chunk_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    req.record_id,
                    user.user_id,
                    "infographic",
                    image_data,
                    final_prompt,
                    req.depth,
                    model,
                    created_at,
                    len(doc_ids),
                    chunk_count,
                ),
            )

        return InfographicResponse(
            image_url=image_data,
            image_id=image_id,
            prompt_used=final_prompt,
            document_count=len(doc_ids),
            chunk_count=chunk_count,
            model=model,
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image generation timed out. Please try again.")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/infographic/{image_id}")
async def get_infographic(
    image_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """Retrieve a previously generated infographic"""

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, image_data, prompt, depth, model, created_at, document_count, chunk_count
            FROM generated_images
            WHERE id = ? AND user_id = ?
            """,
            (image_id, user.user_id),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "image_id": row[0],
        "image_url": row[1],
        "prompt": row[2] or "",
        "depth": row[3] or "standard",
        "model": row[4] or "",
        "created_at": row[5],
        "document_count": row[6],
        "chunk_count": row[7],
    }


@router.get("/infographics/{record_id}")
async def list_infographics(
    record_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """List all infographics for a record"""
    logger.info(f"Listing infographics for record: {record_id}")
    
    try:
        logger.debug(f"User ID: {user.user_id}")

        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT id FROM records WHERE id = ? AND user_id = ?",
                (record_id, user.user_id),
            )
            if cursor.fetchone() is None:
                logger.warning(f"Record not found: {record_id} for user: {user.user_id}")
                raise HTTPException(status_code=404, detail="Record not found")

            cursor.execute(
                """
                SELECT id, created_at, depth, model
                FROM generated_images
                WHERE record_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (record_id, user.user_id),
            )
            rows = cursor.fetchall()

        logger.info(f"Found {len(rows)} infographics")

        return {
            "infographics": [
                {
                    "image_id": row[0],
                    "created_at": row[1],
                    "depth": row[2] or "standard",
                    "model": row[3] or "",
                }
                for row in rows
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error listing infographics: {e}")
        return {"infographics": []}


def _decode_image_bytes(image_data: str) -> bytes:
    if image_data.startswith("data:image"):
        _, b64 = image_data.split(",", 1)
        return base64.b64decode(b64)
    raise ValueError("Unsupported image format")


@router.post("/pdf", response_model=PdfResponse)
async def generate_pdf(
    payload: PdfRequest,
    user: AuthContext = Depends(get_current_user),
):
    """Generate a PDF by rendering each chunk as an image and combining into A4 pages."""
    from config import settings

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, chat_model FROM records WHERE id = ? AND user_id = ?",
            (payload.record_id, user.user_id),
        )
        record_row = cursor.fetchone()
        if record_row is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            "SELECT encrypted_master_key FROM users WHERE id = ?",
            (user.user_id,),
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

    user_key = decrypt_master_key(user_row[0])

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT c.encrypted_text, c.chunk_index, d.id, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.record_id = ?
            ORDER BY d.filename, c.chunk_index
            """,
            (payload.record_id,),
        )
        chunk_rows = cursor.fetchall()

    if not chunk_rows:
        raise HTTPException(status_code=400, detail="No document chunks found. Upload sources first.")

    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or getattr(settings, "openrouter_api_key", None)
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured in settings")

    model = "google/gemini-3-pro-image-preview"
    images: list[bytes] = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        for start in range(0, len(chunk_rows), 5):
            batch = chunk_rows[start : start + 5]
            combined_parts: list[str] = []

            for encrypted_text, chunk_index, document_id, filename in batch:
                try:
                    plain_text = decrypt_text_with_user_key(user_key, encrypted_text)
                except Exception:
                    logger.warning("Failed to decrypt chunk for document %s", document_id)
                    continue

                snippet = plain_text.strip().replace("\n", " ")
                snippet = snippet[:800]
                combined_parts.append(
                    f"Document: {filename or 'unknown'} | Chunk: {chunk_index or 0}\n{snippet}"
                )

            if not combined_parts:
                continue

            combined_text = "\n\n".join(combined_parts)

            prompt = (
                "Create a clean, printable page image that summarizes the following text. "
                "Use a white background, subtle section headers, and clear typography. "
                "Group the content into 5 short sections when possible. "
                f"\n\nContent:\n{combined_text}"
            )

            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": OPENROUTER_HTTP_REFERER,
                    "X-Title": OPENROUTER_X_TITLE,
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "modalities": ["image", "text"],
                },
            )

            if response.status_code != 200:
                error_text = response.text
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenRouter API error ({response.status_code}): {error_text[:200]}"
                )

            data = response.json()
            message = data.get("choices", [{}])[0].get("message", {})
            images_list = message.get("images", [])

            image_data = ""
            if images_list:
                image_data = images_list[0].get("image_url", {}).get("url", "")
                if not image_data:
                    image_data = images_list[0].get("url", "")
            else:
                content = message.get("content", "")
                if content and content.startswith("data:image"):
                    image_data = content

            if not image_data:
                raise HTTPException(status_code=502, detail="No image generated by model for PDF")

            if image_data.startswith("http"):
                img_resp = await client.get(image_data)
                if img_resp.status_code != 200:
                    raise HTTPException(status_code=502, detail="Failed to fetch generated image")
                images.append(img_resp.content)
            else:
                images.append(_decode_image_bytes(image_data))

    if not images:
        raise HTTPException(status_code=502, detail="No images generated for PDF")

    pdf = fitz.open()
    a4_width = 595
    a4_height = 842
    margin = 36
    rect = fitz.Rect(margin, margin, a4_width - margin, a4_height - margin)

    for image_bytes in images:
        page = pdf.new_page(width=a4_width, height=a4_height)
        page.insert_image(rect, stream=image_bytes, keep_proportion=True)

    pdf_bytes = pdf.tobytes()
    pdf.close()

    pdf_id = f"pdf_{uuid.uuid4().hex}"
    created_at = get_current_timestamp()

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO generated_pdfs (
                id, record_id, user_id, pdf_data, created_at, chunk_count, page_count, model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pdf_id,
                payload.record_id,
                user.user_id,
                pdf_bytes,
                created_at,
                len(chunk_rows),
                len(images),
                model,
            ),
        )

    return PdfResponse(
        pdf_id=pdf_id,
        page_count=len(images),
        chunk_count=len(chunk_rows),
        model=model,
    )


@router.get("/pdf/{pdf_id}")
async def get_pdf(
    pdf_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """Retrieve a previously generated PDF."""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT pdf_data
            FROM generated_pdfs
            WHERE id = ? AND user_id = ?
            """,
            (pdf_id, user.user_id),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="PDF not found")

    return Response(content=row[0], media_type="application/pdf")


@router.get("/pdfs/{record_id}")
async def list_pdfs(
    record_id: str,
    user: AuthContext = Depends(get_current_user),
):
    """List all PDFs for a record."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM records WHERE id = ? AND user_id = ?",
            (record_id, user.user_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute(
            """
            SELECT id, created_at, page_count, model
            FROM generated_pdfs
            WHERE record_id = ? AND user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (record_id, user.user_id),
        )
        rows = cursor.fetchall()

    return {
        "pdfs": [
            {
                "pdf_id": row[0],
                "created_at": row[1],
                "page_count": row[2],
                "model": row[3],
            }
            for row in rows
        ]
    }
