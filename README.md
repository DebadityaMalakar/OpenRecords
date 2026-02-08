# OpenRecords

OpenRecords is a local-first, privacy-focused research notebook and an open-source alternative to NotebookLM.  
It is designed for reliable, minimal, and fully user-controlled research workflows.

The system provides document ingestion, retrieval-augmented generation (RAG), visual synthesis, and archival PDF generation without cloud lock-in.

---

## Why OpenRecords

Most AI research notebooks prioritize cloud features, accounts, and experimental interfaces.

OpenRecords focuses on:

- Local execution
- Data ownership
- Predictable behavior
- Clean export formats
- Minimal configuration

It was built to remain usable, inspectable, and maintainable over time.

---

## Monorepo Layout

```

backend/   FastAPI + SQLite backend
frontend/  Next.js frontend

````

---

## Features

| Feature | Supported |
|---------|-----------|
| Document Summarization | Yes |
| Q&A over Sources | Yes |
| RAG Search | Yes |
| Infographics | Yes |
| PDF Compilation (A4) | Yes |
| Cloud Dependency | No |
| Mandatory Accounts | No |

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- pnpm, npm, or yarn
- OpenRouter API key (for AI features)

---

## Quick Start

### 1. Backend Setup

From the repository root:

```bash
cd backend
````

Create `backend/.env.local`:

```env
OPENROUTER_API_KEY=your_key_here
OPENRECORDS_SECRET_KEY=dev-secret-key-change-in-production
OPENRECORDS_ENV=dev
OPENRECORDS_DB_PATH=data/main.db
OPENRECORDS_CACHE_PATH=data/cache.db
VECTOR_DB_PATH=data/vectors
```

Install dependencies and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend will run at:

```
http://localhost:8000
```

---

### 2. Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend will run at:

```
http://localhost:3000
```

If the backend is running on a different address, create `frontend/.env.local`:

```env
BACKEND_URL=http://localhost:8000
```

---

## Notes

* Databases and caches are initialized automatically on first launch.
* PDF export renders one image per five chunks and compiles them into an A4 document.
* Infographic and PDF generation require OpenRouter access.
* Designed primarily for individual researchers, students, and writers.

---

## Documentation

* Backend: `backend/README.md`
* Frontend: `frontend/README.md`
* Architecture: `backend/BACKEND.md`

---

## Roadmap

Planned improvements include:

* Study guides and structured summaries
* Offline embedding models
* Plugin system
* Export presets
* Improved theming

---

## Contributing

Contributions, bug reports, and feature suggestions are welcome.
Please open an issue or pull request to discuss proposed changes.

