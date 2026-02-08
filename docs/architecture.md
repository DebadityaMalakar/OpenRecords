# Architecture

## High-Level

- Frontend (Next.js) communicates with backend through a proxy at `/api/*`.
- Backend (FastAPI) stores data in SQLite and indexes embeddings for RAG.
- OpenRouter provides chat and image generation.

## Datastores

- `data/main.db` - users, records, documents, chunks, chats, generated media
- `data/cache.db` - cached model list
- `vault/encrypted_files/` - encrypted document binaries

## Processing Pipeline

1. Upload document
2. Extract text and chunk
3. Encrypt chunks and store
4. Embed chunks and index
5. RAG retrieval + chat completion

## Tooling

- Summary/Outline/Insights are full-text generation tools.
- Infographic generates a single image from record content.
- PDF generates one image per 5 chunks, then composes an A4 PDF.
