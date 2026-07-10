"""Shared embedding backend with automatic Chroma fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Cached after first probe: "langchain" or "chroma"
_embedding_mode: str | None = None
_langchain_embeddings: Any = None

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    """Simple lowercase word tokenizer for BM25 indexing."""
    return _TOKEN_RE.findall((text or "").lower())


def _minmax_normalize(values: list[float]) -> list[float]:
    """Scale values to [0, 1]; constant arrays map to 0.5 (neutral)."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.5] * len(values)
    rng = hi - lo
    return [(v - lo) / rng for v in values]


def hybrid_rescore(
    query: str,
    documents: list[str],
    distances: list[float],
    metadatas: list[dict] | None = None,
    progression_boost: bool = False,
    quest_boost: float = 1.5,
    bm25_weight: float = 0.4,
    vector_weight: float = 0.6,
) -> list[tuple[float, str, dict]]:
    """Combine cosine vector similarity with BM25 keyword scores.

    Returns a list of (score, document, metadata) tuples sorted descending.
    Falls back to vector-only scoring if ``rank_bm25`` is unavailable or the
    corpus is degenerate. Quest-type chunks receive ``quest_boost`` when
    ``progression_boost`` is True (mirrors the original progression heuristic).
    """
    metadatas = metadatas or [{} for _ in documents]
    if not documents:
        return []

    vector_scores = [1.0 - d for d in distances]
    vec_norm = _minmax_normalize(vector_scores)

    try:
        from rank_bm25 import BM25Okapi

        tokenized = [_tokenize(d) for d in documents]
        bm25 = BM25Okapi(tokenized)
        bm25_scores = list(bm25.get_scores(_tokenize(query)))
        bm25_norm = _minmax_normalize(bm25_scores)
        v_w, b_w = vector_weight, bm25_weight
    except Exception as exc:
        logger.debug("BM25 unavailable (%s) — using vector-only scoring", exc)
        bm25_norm = [0.0] * len(documents)
        v_w, b_w = 1.0, 0.0

    scored: list[tuple[float, str, dict]] = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas)):
        score = v_w * vec_norm[i] + b_w * bm25_norm[i]
        if progression_boost and meta.get("type") == "quest":
            score *= quest_boost
        scored.append((score, doc, meta))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _create_langchain_embeddings():
    from config import EMBED_BACKEND, OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL, OPENAI_API_KEY, OPENAI_EMBED_MODEL

    if EMBED_BACKEND == "openai" and OPENAI_API_KEY:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=OPENAI_EMBED_MODEL, api_key=OPENAI_API_KEY)
    else:
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def get_embedding_mode() -> str:
    """Return 'langchain' if external embeddings work, else 'chroma' (built-in)."""
    global _embedding_mode, _langchain_embeddings
    if _embedding_mode is not None:
        return _embedding_mode

    try:
        _langchain_embeddings = _create_langchain_embeddings()
        _langchain_embeddings.embed_query("probe")
        _embedding_mode = "langchain"
        logger.info("Using configured embedding backend (Ollama/OpenAI)")
    except Exception as exc:
        _langchain_embeddings = None
        _embedding_mode = "chroma"
        logger.warning(
            "External embeddings unavailable (%s) — using Chroma built-in embeddings. "
            "To use Ollama: `ollama pull nomic-embed-text`",
            exc,
        )
    return _embedding_mode


def embed_documents(texts: list[str]) -> list[list[float]] | None:
    """Embed documents via LangChain, or None to let Chroma handle it."""
    if get_embedding_mode() == "langchain":
        return _langchain_embeddings.embed_documents(texts)
    return None


def query_collection(collection, query: str, n_results: int = 8, where: dict | None = None):
    """Query ChromaDB using the appropriate embedding method."""
    kwargs: dict = {"n_results": n_results, "include": ["documents", "metadatas", "distances"]}
    if where:
        kwargs["where"] = where

    if get_embedding_mode() == "langchain":
        embedding = _langchain_embeddings.embed_query(query)
        return collection.query(query_embeddings=[embedding], **kwargs)
    else:
        return collection.query(query_texts=[query], **kwargs)
