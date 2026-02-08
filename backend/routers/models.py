from fastapi import APIRouter, HTTPException
from services.model_cache import get_model_cache_service

router = APIRouter(prefix="/api/models", tags=["models"])

@router.get("/", summary="Get cached models")
def get_cached_models():
    """Fetch cached models."""
    service = get_model_cache_service()
    return service.get_models()

@router.post("/refresh", summary="Force refresh models")
def refresh_models():
    """Force a cache refresh."""
    service = get_model_cache_service()
    result = service.refresh_models()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.get("/embeddings", summary="Get embedding-capable models")
def get_embedding_models():
    """Fetch embedding-capable models."""
    service = get_model_cache_service()
    return service.get_embedding_models()