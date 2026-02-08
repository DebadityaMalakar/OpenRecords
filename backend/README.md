# OpenRecords Backend

FastAPI backend providing authentication, records, document ingestion, RAG, and generation tools.

## Setup

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env.local`:

```env
OPENROUTER_API_KEY=your_key_here
OPENRECORDS_SECRET_KEY=dev-secret-key-change-in-production
OPENRECORDS_ENV=dev
OPENRECORDS_DB_PATH=data/main.db
OPENRECORDS_CACHE_PATH=data/cache.db
VECTOR_DB_PATH=data/vectors
```

Run the server:

```bash
uvicorn main:app --reload
```

Backend runs at http://localhost:8000.

## Key Endpoints

- `POST /api/auth/signup` - create account
- `POST /api/auth/login` - login
- `GET /api/users/me` - current user
- `POST /api/records/init` - create record
- `GET /api/records/{id}` - fetch record
- `POST /api/documents/upload` - upload document
- `POST /api/rag/query` - chat over record
- `POST /api/rag/summary` - summary generator
- `POST /api/rag/outline` - outline generator
- `POST /api/rag/insights` - insight generator
- `POST /api/rag/infographic` - infographic generator
- `POST /api/rag/pdf` - chunked PDF generator
- `GET /api/models` - cached OpenRouter models

## Notes

- Databases are SQLite and auto-initialized on first run.
- Generated PDFs and images are stored in SQLite tables.
- OpenRouter headers are set for all requests with referer `https://openrecords.vercel.app`.

## Architecture Doc

See [BACKEND.md](BACKEND.md) for deeper architecture details.
