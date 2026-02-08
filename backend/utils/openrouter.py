"""
OpenRouter embeddings and chat completion utilities for OpenRecords.
Uses the official OpenRouter Python SDK for chat, httpx for embeddings.
"""
from __future__ import annotations

import logging
from typing import List

import httpx
from openrouter import OpenRouter

from config import settings

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 32
EMBED_MODEL = "mistralai/mistral-embed-2312"
EMBED_DIMENSIONS = 1024  # mistral-embed-2312 output size
DEFAULT_CHAT_MODEL = "moonshotai/kimi-k2.5"
OPENROUTER_HTTP_REFERER = "https://openrecords.vercel.app"
OPENROUTER_X_TITLE = "OpenRecords"


def _get_client() -> OpenRouter:
    """Create an OpenRouter SDK client."""
    return OpenRouter(
        api_key=settings.openrouter_api_key,
        http_referer=OPENROUTER_HTTP_REFERER,
        x_title=OPENROUTER_X_TITLE,
    )


async def get_embeddings(
    texts: List[str],
    model: str = EMBED_MODEL,
) -> List[List[float]]:
    """
    Get embeddings from OpenRouter API.
    Batches texts in groups of EMBED_BATCH_SIZE.
    Uses httpx directly since the SDK doesn't expose a raw embeddings endpoint.

    Returns list of embedding vectors (one per text).
    """
    if not settings.openrouter_api_key:
        logger.warning("No OpenRouter API key configured — returning empty embeddings")
        return [[0.0] * EMBED_DIMENSIONS for _ in texts]

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]

        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{settings.openrouter_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": OPENROUTER_HTTP_REFERER,
                    "X-Title": OPENROUTER_X_TITLE,
                },
                json={
                    "model": model,
                    "input": batch,
                },
            )

            if resp.status_code != 200:
                logger.error("Embeddings API error %d: %s", resp.status_code, resp.text[:200])
                all_embeddings.extend([[0.0] * EMBED_DIMENSIONS for _ in batch])
                continue

            data = resp.json()
            for item in sorted(data.get("data", []), key=lambda x: x["index"]):
                all_embeddings.append(item["embedding"])

    return all_embeddings


async def chat_completion(
    messages: list[dict],
    model: str = DEFAULT_CHAT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Call OpenRouter chat completion via the official SDK.

    Returns the assistant's response text.
    Handles reasoning models (like kimi-k2.5) that may put output
    in the ``reasoning`` field instead of ``content``.
    """
    if not settings.openrouter_api_key:
        return "OpenRouter API key not configured. Please set OPENROUTER_API_KEY in your .env file."

    try:
        with _get_client() as client:
            res = client.chat.send(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if not res.choices:
                return "No response from AI model."

            msg = res.choices[0].message
            # Prefer content; fall back to reasoning for thinking models
            text = msg.content
            if not text and hasattr(msg, "reasoning") and msg.reasoning:
                text = msg.reasoning
            return text or "No content in response."

    except Exception as e:
        logger.error("Chat API error: %s", e)
        return f"Error from AI model: {str(e)[:200]}. Please try again."
