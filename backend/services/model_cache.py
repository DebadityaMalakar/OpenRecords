"""
Model cache service for OpenRecords.
Manages OpenRouter model listing and caching.
"""
import json
import time
from typing import Any, Dict, List, Optional

from openrouter import OpenRouter, operations

from cache_db import get_cache_db_cursor
from config import settings
from utils.openrouter import OPENROUTER_HTTP_REFERER, OPENROUTER_X_TITLE


class ModelCacheService:
    """Service for managing OpenRouter model cache."""

    def __init__(self):
        """Initialize the model cache service."""
        self.client: Optional[OpenRouter] = None
        if settings.openrouter_api_key:
            self.client = OpenRouter(
                api_key=settings.openrouter_api_key,
                http_referer=OPENROUTER_HTTP_REFERER,
                x_title=OPENROUTER_X_TITLE,
            )

    def _get_cache_age(self) -> Optional[int]:
        """
        Get the age of the cache in seconds.
        
        Returns:
            Age in seconds, or None if cache is empty
        """
        with get_cache_db_cursor() as cursor:
            cursor.execute("SELECT MAX(updated_at) as latest FROM models_cache")
            row = cursor.fetchone()
            
            if row and row[0]:
                latest_timestamp = row[0]
                current_time = int(time.time())
                return current_time - latest_timestamp
            
            return None

    def is_cache_expired(self) -> bool:
        """
        Check if the cache is expired.
        
        Returns:
            True if cache is expired or empty, False otherwise
        """
        cache_age = self._get_cache_age()
        
        if cache_age is None:
            return True  # No cache exists
        
        return cache_age > settings.cache_ttl_seconds

    def _fetch_models_from_openrouter(self) -> List[Dict[str, Any]]:
        """
        Fetch models from OpenRouter API.
        
        Returns:
            List of model dictionaries
        
        Raises:
            Exception if API call fails
        """
        if not self.client:
            raise Exception("OpenRouter API key not configured")

        try:
            # Try to get user-specific models first
            response = self.client.models.list_for_user(
                security=operations.ListModelsUserSecurity(
                    bearer=settings.openrouter_api_key,
                )
            )
            models = response.data
        except Exception as e:
            print(f"Error fetching models for user from OpenRouter: {e}")
            # Fallback: try without user filtering
            try:
                response = self.client.models.list()
                models = response.data
            except Exception as fallback_error:
                raise Exception(f"Failed to fetch models: {fallback_error}")

        return [model.model_dump() for model in models]

    def _normalize_model(self, raw_model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a raw OpenRouter model into our schema.
        
        Args:
            raw_model: Raw model data from OpenRouter
        
        Returns:
            Normalized model dictionary
        """
        # Extract pricing information
        pricing = raw_model.get("pricing", {})
        pricing_prompt = pricing.get("prompt")
        pricing_completion = pricing.get("completion")
        
        # Convert pricing from string to float if needed
        if isinstance(pricing_prompt, str):
            pricing_prompt = float(pricing_prompt)
        if isinstance(pricing_completion, str):
            pricing_completion = float(pricing_completion)

        # Extract categories
        categories = raw_model.get("categories")
        if categories is None:
            categories = raw_model.get("architecture", {}).get("modality")
        if isinstance(categories, list):
            categories = ",".join(categories)
        elif categories is None:
            categories = ""

        return {
            "id": raw_model.get("id", ""),
            "provider": raw_model.get("provider")
            or (raw_model.get("id", "").split("/")[0] if "/" in raw_model.get("id", "") else ""),
            "name": raw_model.get("name", ""),
            "context_length": raw_model.get("context_length"),
            "pricing_prompt": pricing_prompt,
            "pricing_completion": pricing_completion,
            "categories": categories,
            "supports_streaming": 1 if raw_model.get("supports_streaming", False) else 0,
            "raw_json": json.dumps(raw_model),
            "updated_at": int(time.time()),
        }

    def _store_models_in_cache(self, models: List[Dict[str, Any]]) -> int:
        """
        Store models in the cache database.
        
        Args:
            models: List of normalized model dictionaries
        
        Returns:
            Number of models stored
        """
        with get_cache_db_cursor() as cursor:
            # Clear existing cache
            cursor.execute("DELETE FROM models_cache")
            
            # Bulk insert new models
            for model in models:
                cursor.execute(
                    """
                    INSERT INTO models_cache (
                        id, provider, name, context_length,
                        pricing_prompt, pricing_completion,
                        categories, supports_streaming,
                        raw_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model["id"],
                        model["provider"],
                        model["name"],
                        model["context_length"],
                        model["pricing_prompt"],
                        model["pricing_completion"],
                        model["categories"],
                        model["supports_streaming"],
                        model["raw_json"],
                        model["updated_at"],
                    ),
                )
            
            return len(models)

    def _fetch_embedding_models_from_openrouter(self) -> List[Dict[str, Any]]:
        """
        Fetch embedding models from OpenRouter API.

        Returns:
            List of embedding model dictionaries

        Raises:
            Exception if API call fails
        """
        if not self.client:
            raise Exception("OpenRouter API key not configured")

        try:
            response = self.client.embeddings.list_models()
            models = response.data
        except Exception as e:
            raise Exception(f"Failed to fetch embedding models: {e}")

        return [model.model_dump() for model in models]

    def get_models(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get models from cache or fetch from OpenRouter if expired.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
        
        Returns:
            Dictionary with cached status, timestamp, and models list
        """
        # Check if we need to refresh
        should_refresh = force_refresh or self.is_cache_expired()

        if should_refresh:
            try:
                # Fetch from OpenRouter
                raw_models = self._fetch_models_from_openrouter()
                
                # Normalize models
                normalized_models = [self._normalize_model(m) for m in raw_models]
                
                # Store in cache
                count = self._store_models_in_cache(normalized_models)
                
                print(f"Refreshed model cache: {count} models stored")
            except Exception as e:
                print(f"Failed to refresh models, using stale cache: {e}")
                # Continue to serve stale cache if available

        # Retrieve from cache
        with get_cache_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, provider, name, context_length,
                       pricing_prompt, pricing_completion,
                       categories, supports_streaming, updated_at
                FROM models_cache
                ORDER BY provider, name
                """
            )
            
            rows = cursor.fetchall()
            
            models = []
            updated_at = None
            
            for row in rows:
                if updated_at is None:
                    updated_at = row[8]  # updated_at column
                
                models.append({
                    "id": row[0],
                    "provider": row[1],
                    "name": row[2],
                    "context_length": row[3],
                    "pricing_prompt": row[4],
                    "pricing_completion": row[5],
                    "categories": row[6].split(",") if row[6] else [],
                    "supports_streaming": bool(row[7]),
                })

        return {
            "cached": not should_refresh,
            "updated_at": updated_at or int(time.time()),
            "models": models,
        }

    def refresh_models(self) -> Dict[str, Any]:
        """
        Force refresh models from OpenRouter.
        
        Returns:
            Dictionary with status and count
        """
        try:
            result = self.get_models(force_refresh=True)
            
            return {
                "status": "ok",
                "refreshed": True,
                "count": len(result["models"]),
            }
        except Exception as e:
            return {
                "status": "error",
                "refreshed": False,
                "error": str(e),
            }

    def get_embedding_models(self) -> Dict[str, Any]:
        """
        Get models that support embeddings.

        Returns:
            Dictionary with embedding-capable models
        """
        try:
            raw_models = self._fetch_embedding_models_from_openrouter()
            normalized_models = [self._normalize_model(m) for m in raw_models]
            return {
                "cached": False,
                "updated_at": int(time.time()),
                "models": normalized_models,
            }
        except Exception as e:
            print(f"Failed to fetch embedding models from OpenRouter: {e}")
            # Fallback to cached embedding models
            models_data = self.get_models()
            embedding_models = [
                model
                for model in models_data["models"]
                if "embedding" in model.get("categories", [])
                or "embed" in model["id"].lower()
            ]
            return {
                "cached": models_data["cached"],
                "updated_at": models_data["updated_at"],
                "models": embedding_models,
            }


# Global service instance
_model_cache_service: Optional[ModelCacheService] = None


def get_model_cache_service() -> ModelCacheService:
    """Get the global model cache service instance."""
    global _model_cache_service
    
    if _model_cache_service is None:
        _model_cache_service = ModelCacheService()
    
    return _model_cache_service
