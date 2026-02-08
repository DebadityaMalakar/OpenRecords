"""
Database initialization and management for OpenRecords.
Handles SQLite connection and schema creation.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config import settings


# SQL to create the users table
CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    encrypted_master_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_login TEXT
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""

# SQL to create the user_settings table
CREATE_USER_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    default_chat_model TEXT,
    default_embed_model TEXT,
    theme TEXT,
    temperature REAL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);
"""

# SQL to create records table
CREATE_RECORDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_opened TEXT,
    chat_model TEXT,
    embed_model TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_records_user_id ON records(user_id);
CREATE INDEX IF NOT EXISTS idx_records_created_at ON records(created_at);
CREATE INDEX IF NOT EXISTS idx_records_last_opened ON records(last_opened);
"""

# SQL to create documents table
CREATE_DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'file',
    encrypted_path TEXT,
    hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    page_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_documents_record_id ON documents(record_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
"""

# SQL to create chunks table
CREATE_CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    encrypted_text TEXT NOT NULL,
    token_count INTEGER,
    page_number INTEGER,
    section TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
"""

# SQL to create references table
CREATE_REFERENCES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS references_table (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    document_id TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_references_record_id ON references_table(record_id);
CREATE INDEX IF NOT EXISTS idx_references_url ON references_table(url);
"""

# SQL to create sessions table (optional)
CREATE_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
"""

# SQL to create chat_messages table
CREATE_CHAT_MESSAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources TEXT,
    model TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_record_id ON chat_messages(record_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
"""

# SQL to create generated_images table
CREATE_GENERATED_IMAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS generated_images (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'infographic',
    image_data TEXT NOT NULL,
    prompt TEXT,
    depth TEXT,
    model TEXT,
    created_at TEXT NOT NULL,
    document_count INTEGER,
    chunk_count INTEGER,
    FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_generated_images_record_user ON generated_images(record_id, user_id);
CREATE INDEX IF NOT EXISTS idx_generated_images_created_at ON generated_images(created_at);
"""

# SQL to create generated_pdfs table
CREATE_GENERATED_PDFS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS generated_pdfs (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    pdf_data BLOB NOT NULL,
    created_at TEXT NOT NULL,
    chunk_count INTEGER,
    page_count INTEGER,
    model TEXT,
    FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_generated_pdfs_record_user ON generated_pdfs(record_id, user_id);
CREATE INDEX IF NOT EXISTS idx_generated_pdfs_created_at ON generated_pdfs(created_at);
"""


def ensure_data_directory() -> None:
    """Ensure the data directory exists."""
    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


def init_database() -> None:
    """Initialize the database with required tables."""
    ensure_data_directory()

    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create tables
    cursor.executescript(CREATE_USERS_TABLE_SQL)
    cursor.executescript(CREATE_USER_SETTINGS_TABLE_SQL)
    cursor.executescript(CREATE_RECORDS_TABLE_SQL)
    cursor.executescript(CREATE_DOCUMENTS_TABLE_SQL)
    cursor.executescript(CREATE_CHUNKS_TABLE_SQL)
    cursor.executescript(CREATE_REFERENCES_TABLE_SQL)
    cursor.executescript(CREATE_SESSIONS_TABLE_SQL)
    cursor.executescript(CREATE_CHAT_MESSAGES_TABLE_SQL)
    cursor.executescript(CREATE_GENERATED_IMAGES_TABLE_SQL)
    cursor.executescript(CREATE_GENERATED_PDFS_TABLE_SQL)

    conn.commit()
    conn.close()


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with proper setup."""
    ensure_data_directory()
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row  # Allow accessing columns by name
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_cursor() -> Generator[sqlite3.Cursor, None, None]:
    """Get a database cursor with automatic commit."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def check_database_initialized() -> bool:
    """Check if the database has been initialized."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                AND name IN ('users', 'user_settings', 'records', 'documents', 'chunks', 'sessions', 'references_table', 'chat_messages', 'generated_images', 'generated_pdfs');
                """
            )
            rows = cursor.fetchall()
            existing = {row[0] for row in rows}
            required = {
                "users",
                "user_settings",
                "records",
                "documents",
                "chunks",
                "sessions",
                "references_table",
                "chat_messages",
                "generated_images",
                "generated_pdfs",
            }
            return required.issubset(existing)
    except sqlite3.Error:
        return False


async def init_db():
    """Ensure SQLite tables and indexes exist for generated images."""
    with get_db_cursor() as cursor:
        cursor.executescript(CREATE_GENERATED_IMAGES_TABLE_SQL)
        cursor.executescript(CREATE_GENERATED_PDFS_TABLE_SQL)
