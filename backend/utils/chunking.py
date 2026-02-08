"""
Text chunking utilities for OpenRecords.
Uses tiktoken for token-aware chunking with overlap.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import tiktoken

# Default encoding for token counting
_enc = tiktoken.get_encoding("cl100k_base")

DEFAULT_CHUNK_SIZE = 500  # tokens
DEFAULT_CHUNK_OVERLAP = 50  # tokens


@dataclass
class Chunk:
    """A text chunk with metadata."""

    text: str
    token_count: int
    page_number: int | None = None
    section: str | None = None
    index: int = 0


def count_tokens(text: str) -> int:
    """Count tokens in a string using cl100k_base encoding."""
    return len(_enc.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    page_number: int | None = None,
    section: str | None = None,
) -> List[Chunk]:
    """
    Split text into token-aware overlapping chunks.

    Args:
        text: Source text to chunk
        chunk_size: Target chunk size in tokens
        chunk_overlap: Number of overlapping tokens between chunks
        page_number: Optional page number metadata
        section: Optional section name metadata

    Returns:
        List of Chunk objects
    """
    if not text or not text.strip():
        return []

    tokens = _enc.encode(text)
    total_tokens = len(tokens)

    if total_tokens <= chunk_size:
        return [
            Chunk(
                text=text.strip(),
                token_count=total_tokens,
                page_number=page_number,
                section=section,
                index=0,
            )
        ]

    chunks: List[Chunk] = []
    start = 0
    idx = 0

    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text_str = _enc.decode(chunk_tokens).strip()

        if chunk_text_str:
            chunks.append(
                Chunk(
                    text=chunk_text_str,
                    token_count=len(chunk_tokens),
                    page_number=page_number,
                    section=section,
                    index=idx,
                )
            )
            idx += 1

        if end >= total_tokens:
            break

        start = end - chunk_overlap

    return chunks


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """
    Chunk a list of (page_number, text) tuples.
    Preserves page metadata on each chunk.
    """
    all_chunks: List[Chunk] = []
    global_idx = 0

    for page_num, text in pages:
        page_chunks = chunk_text(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            page_number=page_num,
        )
        for c in page_chunks:
            c.index = global_idx
            global_idx += 1
            all_chunks.append(c)

    return all_chunks
