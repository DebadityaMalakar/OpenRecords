# API

## Authentication

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/users/me`

## Records

- `POST /api/records/init`
- `GET /api/records`
- `GET /api/records/{id}`
- `PATCH /api/records/{id}`

## Documents

- `POST /api/documents/upload`
- `GET /api/documents/list/{record_id}`
- `GET /api/documents/status/{document_id}`

## RAG / Tools

- `POST /api/rag/query`
- `POST /api/rag/summary`
- `POST /api/rag/outline`
- `POST /api/rag/insights`
- `POST /api/rag/infographic`
- `GET /api/rag/infographics/{record_id}`
- `POST /api/rag/pdf`
- `GET /api/rag/pdfs/{record_id}`
- `GET /api/rag/pdf/{pdf_id}`

## Models

- `GET /api/models`
- `POST /api/models/refresh`
- `GET /api/models/embeddings`
