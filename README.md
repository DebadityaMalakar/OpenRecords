# OpenRecords

OpenRecords is a local-first, privacy-focused research notebook with RAG, document ingestion, and visual tools (infographics + PDF generation).

## Monorepo Layout

- backend/ - FastAPI + SQLite backend
- frontend/ - Next.js frontend

## Prerequisites

- Python 3.10+ (conda or venv)
- Node.js 18+ (pnpm, npm, or yarn)
- OpenRouter API key for AI features

## Quick Start

### 1) Backend

From the repository root:

```bash
cd backend
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

Install deps and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs on http://localhost:8000.

### 2) Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Frontend runs on http://localhost:3000.

If your backend is not on localhost:8000, set `frontend/.env.local`:

```env
BACKEND_URL=http://localhost:8000
```

## Notes

- Database and cache are initialized automatically on first run.
- PDF generation renders one image per 5 chunks, then compiles an A4 PDF.
- Infographic and PDF generation require OpenRouter access.

## More Docs

- Backend: [backend/README.md](backend/README.md)
- Frontend: [frontend/README.md](frontend/README.md)
- Backend architecture: [backend/BACKEND.md](backend/BACKEND.md)
