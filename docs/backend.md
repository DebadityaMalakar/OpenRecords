# Backend

FastAPI backend for authentication, records, ingestion, RAG, and generation tools.

## Core Services

- Auth and session cookies
- Record and document management
- Chunking + embeddings
- RAG query pipeline
- Tool generation (summary, outline, insights, infographic, PDF)

## Storage

- SQLite main DB: `data/main.db`
- SQLite cache DB: `data/cache.db`
- Encrypted files: `vault/encrypted_files/`
- Vector index: `data/vectors/`

## Key Endpoints

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/users/me`
- `POST /api/records/init`
- `GET /api/records/{id}`
- `POST /api/documents/upload`
- `POST /api/rag/query`
- `POST /api/rag/summary`
- `POST /api/rag/outline`
- `POST /api/rag/insights`
- `POST /api/rag/infographic`
- `POST /api/rag/pdf`
- `GET /api/models`

## Notes

- SQLite databases are initialized on first run.
- Generated PDFs and images are stored in SQLite.
- OpenRouter headers include `HTTP-Referer: https://openrecords.vercel.app` and `X-Title: OpenRecords`.

## Data Flow (Docs -> RAG)

1. Upload document
2. Extract text and chunk
3. Encrypt and store chunks
4. Embed chunks and index
5. RAG query retrieves and summarizes
