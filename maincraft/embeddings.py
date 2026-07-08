"""Shared embedding backend with automatic Chroma fallback."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Cached after first probe: "langchain" or "chroma"
_embedding_mode: str | None = None
_langchain_embeddings: Any = None


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
