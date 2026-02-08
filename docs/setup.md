# Setup

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenRouter API key

## Repository Layout

- backend/
- frontend/
- docs/

## Backend

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

Run:

```bash
uvicorn main:app --reload
```

## Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Optional `frontend/.env.local`:

```env
BACKEND_URL=http://localhost:8000
```

## Common Tasks

- Rebuild frontend: `pnpm build`
- Start frontend prod: `pnpm start`
- Lint frontend: `pnpm lint`

## Troubleshooting

- If the backend crashes on startup, check for missing env vars in `backend/.env.local`.
- If OpenRouter calls fail, confirm `OPENROUTER_API_KEY` is set.
- If CORS blocks requests, verify `cors_origins` in `backend/config.py`.
