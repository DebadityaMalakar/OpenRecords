"""
Vector database utilities for OpenRecords.
Lightweight SQLite + NumPy implementation for vector storage and cosine similarity search.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import List

import numpy as np

from config import settings

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None

VECTOR_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS vectors (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    embedding BLOB NOT NULL,
    document TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_vectors_record ON vectors(record_id);
"""


def _get_conn() -> sqlite3.Connection:
    """Get or create the vector DB connection."""
    global _conn
    if _conn is None:
        db_path = Path(settings.vector_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        db_file = db_path / "vectors.db"
        _conn = sqlite3.connect(str(db_file), check_same_thread=False)
        _conn.executescript(VECTOR_DB_SCHEMA)
    return _conn


def _to_blob(embedding: List[float]) -> bytes:
    """Convert embedding list to numpy bytes."""
    return np.array(embedding, dtype=np.float32).tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    """Convert bytes back to numpy array."""
    return np.frombuffer(blob, dtype=np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.
    Handles dimension mismatches by truncating to the shorter length.
    """
    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0
    a, b = a[:min_len], b[:min_len]
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def add_vectors(
    record_id: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[dict] | None = None,
) -> None:
    """Add vectors to the store."""
    if not ids:
        return

    conn = _get_conn()
    metas = metadatas or [{}] * len(ids)

    for i, vid in enumerate(ids):
        conn.execute(
            "INSERT OR REPLACE INTO vectors (id, record_id, embedding, document, metadata) VALUES (?, ?, ?, ?, ?)",
            (
                vid,
                record_id,
                _to_blob(embeddings[i]),
                documents[i] if i < len(documents) else "",
                json.dumps(metas[i]),
            ),
        )
    conn.commit()
    logger.info("Indexed %d chunks into record %s", len(ids), record_id)


def query_vectors(
    record_id: str,
    query_embedding: List[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Query vectors for a record using cosine similarity.
    Returns list of dicts with keys: id, distance, document, metadata.
    """
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT id, embedding, document, metadata FROM vectors WHERE record_id = ?",
        (record_id,),
    )
    rows = cursor.fetchall()

    if not rows:
        return []

    query_vec = np.array(query_embedding, dtype=np.float32)
    scored: list[tuple[float, dict]] = []

    for vid, emb_blob, doc, meta_json in rows:
        emb = _from_blob(emb_blob)
        sim = _cosine_similarity(query_vec, emb)
        # Convert similarity to distance (lower = more similar, for compatibility)
        distance = 1.0 - sim
        scored.append((distance, {
            "id": vid,
            "distance": distance,
            "document": doc or "",
            "metadata": json.loads(meta_json) if meta_json else {},
        }))

    scored.sort(key=lambda x: x[0])
    return [item[1] for item in scored[:top_k]]


def delete_collection(record_id: str) -> None:
    """Delete all vectors for a record."""
    conn = _get_conn()
    conn.execute("DELETE FROM vectors WHERE record_id = ?", (record_id,))
    conn.commit()
    logger.info("Deleted vectors for record %s", record_id)


def collection_count(record_id: str) -> int:
    """Get the number of vectors for a record."""
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM vectors WHERE record_id = ?",
        (record_id,),
    )
    return cursor.fetchone()[0]
