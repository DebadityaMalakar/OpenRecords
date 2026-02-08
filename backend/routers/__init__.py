"""Routers package for OpenRecords."""
from routers.auth import router as auth_router
from routers.models import router as models_router
from routers.users import router as users_router
from routers.records import router as records_router
from routers.documents import router as documents_router
from routers.references import router as references_router
from routers.rag import router as rag_router
from routers.cache import router as cache_router
from routers.chat import router as chat_router

__all__ = [
	"auth_router",
	"models_router",
	"users_router",
	"records_router",
	"documents_router",
	"references_router",
	"rag_router",
	"cache_router",
	"chat_router",
]
