"""
Cache database initialization and management for OpenRecords.
Handles SQLite cache for OpenRouter models.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config import settings


# SQL to create the models_cache table
CREATE_MODELS_CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS models_cache (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    context_length INTEGER,
    pricing_prompt REAL,
    pricing_completion REAL,
    categories TEXT,
    supports_streaming INTEGER,
    raw_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_models_provider ON models_cache(provider);
CREATE INDEX IF NOT EXISTS idx_models_categories ON models_cache(categories);
CREATE INDEX IF NOT EXISTS idx_models_updated_at ON models_cache(updated_at);
"""


def ensure_cache_directory() -> None:
    """Ensure the cache directory exists."""
    cache_path = settings.cache_db_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)


def init_cache_database() -> None:
    """Initialize the cache database with required tables."""
    ensure_cache_directory()

    conn = sqlite3.connect(settings.cache_db_path)
    cursor = conn.cursor()

    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    # Create tables
    cursor.executescript(CREATE_MODELS_CACHE_TABLE_SQL)

    conn.commit()
    conn.close()


@contextmanager
def get_cache_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a cache database connection with proper setup."""
    ensure_cache_directory()
    conn = sqlite3.connect(settings.cache_db_path)
    conn.row_factory = sqlite3.Row  # Allow accessing columns by name
    
    # Enable WAL mode
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cache_db_cursor() -> Generator[sqlite3.Cursor, None, None]:
    """Get a cache database cursor with automatic commit."""
    with get_cache_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def check_cache_database_initialized() -> bool:
    """Check if the cache database has been initialized."""
    try:
        with get_cache_db_cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='models_cache';"
            )
            return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def clear_models_cache() -> None:
    """Clear all models from the cache."""
    with get_cache_db_cursor() as cursor:
        cursor.execute("DELETE FROM models_cache")
