# OpenRecords - Backend Architecture Specification

## Purpose

This document defines the complete backend system for OpenRecords.

It covers:

- Authentication
- User management
- Record management
- Encrypted storage
- Document processing
- RAG pipeline
- Caching layer
- OpenRouter integration
- Security practices

The backend is designed for local-first, privacy-focused deployment.

---

## Tech Stack

- Framework: FastAPI
- Database: SQLite (main.db)
- Cache: SQLite (cache.db)
- Vector DB: Chroma / Qdrant (local)
- AI Provider: OpenRouter
- Crypto: bcrypt + Fernet
- Auth: JWT + HttpOnly Cookies

---

## Directory Structure

```
backend/
├ main.py
├ config.py
├ db/
│   ├ main.db
│   └ cache.db
├ vault/
│   └ encrypted_files/
├ auth/
├ records/
├ rag/
├ models/
├ cache/
├ crypto/
└ middleware/
```

---

## Environment Variables

```env
OPENRECORDS_SECRET_KEY=
OPENROUTER_API_KEY=
OPENRECORDS_DB_PATH=data/main.db
OPENRECORDS_CACHE_PATH=data/cache.db
VECTOR_DB_PATH=data/vectors
OPENRECORDS_ENV=dev|prod
```

---

## Database Schema

### users

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    full_name TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    encrypted_master_key TEXT,
    created_at TEXT,
    last_login TEXT
);
```

---

### records

```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    created_at TEXT,
    updated_at TEXT,
    chat_model TEXT,
    embed_model TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

---

### documents

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    record_id TEXT,
    filename TEXT,
    encrypted_path TEXT,
    hash TEXT,
    created_at TEXT
);
```

---

### chunks

```sql
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    encrypted_text TEXT,
    token_count INTEGER,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);
```

---

### sessions (optional)

```sql
CREATE TABLE sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT,
    expires_at INTEGER
);
```

---

## Encryption System

### Master Key

- Generated per user
- Encrypted with server secret
- Stored in users.encrypted_master_key

---

### File Encryption

- Algorithm: Fernet (AES-128 + HMAC)
- Files encrypted before disk write
- Decrypted only in RAM

---

### Chunk Encryption

- All text chunks encrypted
- Stored encrypted in DB
- Decrypted only for RAG

---

## Authentication System

See: LoginSignUpBackend.md

Endpoints:

```
POST /auth/signup
POST /auth/login
POST /auth/logout
GET  /users/me
```

JWT + HttpOnly Cookies.

---

## Record Management

### Endpoints

```
POST   /records/init
GET    /records
GET    /records/{id}
PATCH  /records/{id}
DELETE /records/{id}
```

---

### Create Record

- Generate random ID
- Bind to user
- Initialize vector space
- Set default models

---

## Document Upload Pipeline

### Endpoint

```
POST /documents/upload
```

Multipart form.

---

### Processing Flow

1. Receive file
2. Validate type
3. Hash file
4. Encrypt file
5. Store in vault
6. Parse text
7. Chunk
8. Encrypt chunks
9. Embed
10. Store vectors
11. Cache metadata

---

## RAG Pipeline

### Query Endpoint

```
POST /rag/query
```

---

### Flow

1. Authenticate
2. Embed query
3. Vector search
4. Retrieve chunk IDs
5. Cache lookup
6. Decrypt chunks
7. Rank
8. Build prompt
9. Call OpenRouter
10. Return answer + sources

---

## Caching Layer

### Stored in cache.db

Used for:

- Decrypted chunks
- RAG responses
- Metadata
- Model lists

TTL-based eviction.

See: CacheOpenRouterListModelsOpenRouterAIAPI.md

---

## OpenRouter Integration

### Wrapper Service

```
/models/service.py
```

Handles:

- Chat completion
- Embeddings
- Streaming
- Error handling
- Rate limiting

---

### Default Models

```
Chat: moonshotai/kimi-k2.5
Embed: text-embedding-3-large
```

---

## API Routes Overview

```
/auth/*
/users/*
/records/*
/documents/*
/rag/*
/models/*
/cache/*
```

---

## Middleware

### Auth Middleware

- Validates JWT
- Attaches user

### Logging Middleware

- Removes sensitive data
- Logs errors only

### CORS

- Localhost only

---

## Error Handling

All endpoints return:

```json
{
  "status": "error",
  "message": "Readable message"
}
```

No stack traces in prod.

---

## Background Jobs

Scheduled tasks:

- Cache cleanup (daily)
- Vector DB optimization (weekly)
- Orphaned file cleanup (weekly)
- Session purge (daily)

---

## Performance Targets

| Component  | Target |
| ---------- | ------ |
| Auth       | <50ms  |
| Cache read | <5ms   |
| RAG query  | <2s    |
| Upload     | <3s    |
| Model list | <200ms |

---

## Security Practices

- HTTPS in prod
- Localhost binding in dev
- No plaintext logging
- ENV secrets
- Secure cookies
- Input sanitization

---

## Backup and Recovery

User-controlled backups:

```
/export/full
/import/full
```

Encrypted archives.

---

## Deployment

### Development

```bash
uvicorn main:app --reload
```

### Production

```bash
gunicorn -k uvicorn.workers.UvicornWorker main:app
```

Reverse proxy: Nginx / Caddy.

---

## Future Extensions

- Multi-device sync
- Offline LLM mode
- Plugin system
- Collaboration
- Fine-grained permissions

---

OpenRecords
Backend, done right.
