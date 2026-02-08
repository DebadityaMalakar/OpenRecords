"""
Hybrid context retrieval for OpenRecords.

Combines vector (semantic) search with regex/keyword (lexical) search
and fuses results via Reciprocal Rank Fusion (RRF), similar to
NotebookLM's approach.

Pipeline:
  1. Extract key terms, quoted phrases, named entities from the query
  2. Vector search — cosine similarity on embeddings
  3. Regex search  — exact + fuzzy keyword matching on decrypted chunks
  4. RRF merge     — combine both ranked lists into a single ranking
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List

from utils.vectordb import query_vectors

logger = logging.getLogger(__name__)

# ── Reciprocal Rank Fusion constant ──
# Higher k smooths differences between high/low ranks
RRF_K = 60


# ── Data structures ──

@dataclass
class RetrievedChunk:
    """A chunk returned by hybrid retrieval."""

    chunk_id: str
    document: str          # plaintext
    metadata: dict = field(default_factory=dict)
    vector_score: float = 0.0   # cosine similarity (0-1)
    keyword_score: float = 0.0  # regex match quality (0-1)
    rrf_score: float = 0.0      # final fused score
    match_highlights: list[str] = field(default_factory=list)


# ── Query analysis ──

# Common English stop-words to skip during keyword extraction
_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could about above after "
    "again against all am and any at before below between both but by "
    "down during each few for from further get got had has have he her "
    "here hers herself him himself his how i if in into it its itself "
    "just let me more most my myself no nor not now of off on once only "
    "or other our ours ourselves out over own same she so some still "
    "such than that the their theirs them themselves then there these "
    "they this those through to too under until up us very was we were "
    "what when where which while who whom why will with you your yours "
    "yourself yourselves".split()
)


def _extract_query_terms(query: str) -> tuple[list[str], list[str]]:
    """
    Parse a user query into:
      - exact_phrases: quoted strings  e.g. ``"neural network"``
      - keywords: significant individual terms

    Returns (exact_phrases, keywords).
    """
    # 1. Extract quoted phrases
    exact_phrases: list[str] = re.findall(r'"([^"]+)"', query)
    # Remove quoted parts from the remaining text
    remaining = re.sub(r'"[^"]*"', " ", query)

    # 2. Extract keywords (non-stop, length > 2)
    words = re.findall(r"[A-Za-z0-9_\-\.]+", remaining)
    keywords = [
        w for w in words
        if w.lower() not in _STOP_WORDS and len(w) > 2
    ]

    return exact_phrases, keywords


def _build_regex_patterns(
    exact_phrases: list[str],
    keywords: list[str],
) -> list[tuple[re.Pattern[str], float]]:
    """
    Build a list of (compiled_regex, weight) tuples.

    Exact phrases get weight 1.0, individual keywords get 0.5.
    All patterns are case-insensitive and word-boundary-aware.
    """
    patterns: list[tuple[re.Pattern[str], float]] = []

    for phrase in exact_phrases:
        escaped = re.escape(phrase)
        try:
            patterns.append((re.compile(rf"(?i)\b{escaped}\b"), 1.0))
        except re.error:
            pass

    for kw in keywords:
        escaped = re.escape(kw)
        try:
            patterns.append((re.compile(rf"(?i)\b{escaped}\b"), 0.5))
        except re.error:
            pass

    return patterns


# ── Regex scoring ──

def _score_chunk_regex(
    text: str,
    patterns: list[tuple[re.Pattern[str], float]],
) -> tuple[float, list[str]]:
    """
    Score a chunk against the regex patterns.

    Returns (score_0_to_1, list_of_match_snippets).
    Score is the sum of (weight * min(match_count, 3)) / max_possible,
    clamped to [0, 1].
    """
    if not patterns:
        return 0.0, []

    total = 0.0
    max_possible = 0.0
    highlights: list[str] = []

    for pat, weight in patterns:
        max_possible += weight * 3  # cap at 3 hits per pattern
        matches = pat.findall(text)
        count = min(len(matches), 3)
        total += weight * count

        # Build snippet highlights (first match with surrounding context)
        if matches:
            m = pat.search(text)
            if m:
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                snippet = text[start:end].strip()
                if start > 0:
                    snippet = "…" + snippet
                if end < len(text):
                    snippet = snippet + "…"
                highlights.append(snippet)

    score = total / max_possible if max_possible > 0 else 0.0
    return min(score, 1.0), highlights


# ── Reciprocal Rank Fusion ──

def _rrf_merge(
    vector_ranked: list[RetrievedChunk],
    keyword_ranked: list[RetrievedChunk],
    k: int = RRF_K,
) -> list[RetrievedChunk]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.

    RRF score for a document d = Σ  1 / (k + rank_i(d))
    over each ranking list i where d appears.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, RetrievedChunk] = {}

    for rank, chunk in enumerate(vector_ranked, start=1):
        cid = chunk.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunk_map[cid] = chunk

    for rank, chunk in enumerate(keyword_ranked, start=1):
        cid = chunk.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        if cid in chunk_map:
            # Merge keyword info into the existing chunk
            chunk_map[cid].keyword_score = chunk.keyword_score
            chunk_map[cid].match_highlights = chunk.match_highlights
        else:
            chunk_map[cid] = chunk

    # Assign final RRF scores and sort
    result = []
    for cid, rrf in scores.items():
        c = chunk_map[cid]
        c.rrf_score = rrf
        result.append(c)

    result.sort(key=lambda c: c.rrf_score, reverse=True)
    return result


# ── Public API ──

async def hybrid_retrieve(
    record_id: str,
    query: str,
    query_embedding: list[float],
    decrypted_chunks: dict[str, tuple[str, dict]],
    top_k: int = 5,
    vector_top_k: int | None = None,
) -> list[RetrievedChunk]:
    """
    NotebookLM-style hybrid retrieval.

    Args:
        record_id:         The record to search
        query:             Raw user query text
        query_embedding:   Pre-computed query embedding vector
        decrypted_chunks:  dict of {chunk_id: (plaintext, metadata)}
                           — the caller decrypts chunks before passing them in
        top_k:             Final number of results to return
        vector_top_k:      How many vector hits to consider (default: top_k * 3)

    Returns:
        Ranked list of RetrievedChunk with fused scores.
    """
    vtk = vector_top_k or top_k * 3

    # ── 1. Vector (semantic) search ──
    vector_hits = query_vectors(
        record_id=record_id,
        query_embedding=query_embedding,
        top_k=vtk,
    )

    vector_ranked: list[RetrievedChunk] = []
    for hit in vector_hits:
        cid = hit["id"]
        similarity = max(0.0, 1.0 - hit.get("distance", 1.0))
        # Use decrypted text if available, else fall back to stored doc
        if cid in decrypted_chunks:
            text, meta = decrypted_chunks[cid]
        else:
            text = hit.get("document", "")
            meta = hit.get("metadata", {})
        vector_ranked.append(
            RetrievedChunk(
                chunk_id=cid,
                document=text,
                metadata=meta,
                vector_score=similarity,
            )
        )

    # ── 2. Regex (keyword) search ──
    exact_phrases, keywords = _extract_query_terms(query)
    patterns = _build_regex_patterns(exact_phrases, keywords)

    keyword_scored: list[RetrievedChunk] = []
    if patterns:
        for cid, (text, meta) in decrypted_chunks.items():
            score, highlights = _score_chunk_regex(text, patterns)
            if score > 0:
                keyword_scored.append(
                    RetrievedChunk(
                        chunk_id=cid,
                        document=text,
                        metadata=meta,
                        keyword_score=score,
                        match_highlights=highlights,
                    )
                )
        # Sort by keyword score descending, take top vtk
        keyword_scored.sort(key=lambda c: c.keyword_score, reverse=True)
        keyword_ranked = keyword_scored[:vtk]
    else:
        keyword_ranked = []

    logger.info(
        "Hybrid retrieval: %d vector hits, %d keyword hits for record %s",
        len(vector_ranked), len(keyword_ranked), record_id,
    )

    # ── 3. Fuse with RRF ──
    if not keyword_ranked:
        # No keyword matches — just use vector results
        for chunk in vector_ranked:
            chunk.rrf_score = chunk.vector_score
        return vector_ranked[:top_k]

    if not vector_ranked:
        # No vector matches — just use keyword results
        for chunk in keyword_ranked:
            chunk.rrf_score = chunk.keyword_score
        return keyword_ranked[:top_k]

    merged = _rrf_merge(vector_ranked, keyword_ranked)
    return merged[:top_k]
