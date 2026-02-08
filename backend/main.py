"""
Main FastAPI application for OpenRecords.
Initializes the app, database, and includes all routers.
"""
from contextlib import asynccontextmanager
import dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from cache_db import check_cache_database_initialized, init_cache_database
from database import check_database_initialized, init_database
from routers import (
    auth_router,
    cache_router,
    chat_router,
    documents_router,
    models_router,
    rag_router,
    records_router,
    references_router,
    users_router,
)
dotenv.load_dotenv(".env.example")  # Load environment variables from .env file

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting OpenRecords in {settings.openrecords_env} mode...")
    print(f"Database path: {settings.database_path}")

    # Initialize database
    if not check_database_initialized():
        print("Initializing database...")
        init_database()
        print("Database initialized.")
    else:
        print("Database already initialized.")

    # Initialize cache database
    if not check_cache_database_initialized():
        print("Initializing cache database...")
        init_cache_database()
        print("Cache database initialized.")
    else:
        print("Cache database already initialized.")

    # Store settings in app state for access in routes
    app.state.settings = settings

    yield

    # Shutdown
    print("Shutting down OpenRecords...")


# Create FastAPI app
app = FastAPI(
    title="OpenRecords API",
    description="Privacy-first, local-first record management system",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
cors_kwargs = {
    "allow_origins": settings.cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

if settings.is_dev:
    cors_kwargs["allow_origin_regex"] = r"http://(localhost|127\.0\.0\.1|\d+\.\d+\.\d+\.\d+)(:\d+)?"

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Import routers
from routers import auth, records, documents, chat, rag, users, cache, references, models

# Register routers - make sure rag is included
app.include_router(auth.router)
app.include_router(records.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(rag.router)  # <-- Ensure this line exists
app.include_router(users.router)
app.include_router(cache.router)
app.include_router(references.router)
app.include_router(models.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "message": "OpenRecords API",
        "version": "0.1.0",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": check_database_initialized(),
    }
