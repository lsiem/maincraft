"""Agent tools: vector search and session wiki read/write."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from langchain_core.tools import tool

from config import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    PACKS,
    QUEST_CHUNK_BOOST,
    SESSION_WIKI_DIR,
    PackId,
)

logger = logging.getLogger(__name__)

# Module-level active pack (set by CLI)
_active_pack: PackId = "gtnh"


def set_active_pack(pack_id: PackId) -> None:
    global _active_pack
    _active_pack = pack_id


def get_active_pack() -> PackId:
    return _active_pack


def _get_chroma_collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(name=CHROMA_COLLECTION)


from embeddings import hybrid_rescore, query_collection
@tool
def search_modpack_knowledge(query: str, pack_filter: str = "") -> str:
    """Search the modpack knowledge vector database for quest, wiki, and recipe information.

    Args:
        query: The search query (e.g. 'how to make bronze', 'next quest after steam').
        pack_filter: Optional pack filter (gtnh, e2e, e6, e9). Defaults to active pack.
    """
    pack = pack_filter or _active_pack
    try:
        collection = _get_chroma_collection()
        where_filter = {"pack": pack} if pack else None
        results = query_collection(collection, query, n_results=8, where=where_filter)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not docs:
            return f"No results found for '{query}' in pack '{pack}'."

        # Boost quest chunks for progression-like queries
        progression_keywords = {"next", "progress", "quest", "tier", "age", "after", "require", "unlock"}
        is_progression = any(kw in query.lower() for kw in progression_keywords)

        # Hybrid retrieval: combine cosine vector similarity with BM25 keyword scores.
        scored = hybrid_rescore(
            query=query,
            documents=docs,
            distances=distances,
            metadatas=metas,
            progression_boost=is_progression,
            quest_boost=QUEST_CHUNK_BOOST,
        )

        output_lines = [f"Found {len(scored)} results for '{query}' (pack: {pack}):\n"]
        for i, (score, doc, meta) in enumerate(scored[:6], 1):
            source = meta.get("source_url", meta.get("title", ""))
            chunk_type = meta.get("type", "unknown")
            output_lines.append(f"--- Result {i} (score: {score:.2f}, type: {chunk_type}) ---")
            if source:
                output_lines.append(f"Source: {source}")
            output_lines.append(doc[:800])
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as exc:
        logger.error("Vector search failed: %s", exc)
        return f"Search failed: {exc}. The index may not be built yet — run ingestion first."


@tool
def read_player_state(entity: str) -> str:
    """Read a player state markdown file from the session wiki.

    Args:
        entity: The wiki page name without .md extension (e.g. 'progression', 'base_infrastructure', 'bottlenecks', 'index').
    """
    # Always allow reading index
    if entity == "index" or entity == "_all":
        index_path = SESSION_WIKI_DIR / "index.md"
        if index_path.exists():
            return index_path.read_text(encoding="utf-8")
        return "Session wiki index not found."

    path = SESSION_WIKI_DIR / f"{entity}.md"
    if not path.exists():
        available = [f.stem for f in SESSION_WIKI_DIR.glob("*.md") if not f.name.startswith("_")]
        return f"Page '{entity}' not found. Available pages: {', '.join(available)}"

    return path.read_text(encoding="utf-8")


@tool
def update_player_state(entity: str, notes: str) -> str:
    """Write or update a player state markdown file in the session wiki.

    Args:
        entity: The wiki page name without .md extension (e.g. 'progression', 'base_infrastructure', 'bottlenecks').
        notes: The markdown content to write (include frontmatter if creating a new page).
    """
    path = SESSION_WIKI_DIR / f"{entity}.md"
    today = date.today().isoformat()

    path.write_text(notes, encoding="utf-8")

    # Update index.md
    _update_index(entity, notes, today)

    # Append to log.md
    _append_log(entity, today)

    return f"Updated session wiki page '{entity}.md' and refreshed index/log."


def _update_index(entity: str, notes: str, today: str) -> None:
    """Refresh the index.md catalog entry for an entity."""
    index_path = SESSION_WIKI_DIR / "index.md"
    if not index_path.exists():
        return

    # Extract a one-line summary from notes (first non-frontmatter, non-heading line)
    summary = ""
    in_frontmatter = False
    for line in notes.splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter or line.startswith("#"):
            continue
        if line.strip():
            summary = line.strip()[:80]
            break

    pack = _active_pack
    content = index_path.read_text(encoding="utf-8")
    new_row = f"| {entity}.md | {summary or '—'} | {pack} | {today} |"

    if f"| {entity}.md |" in content:
        lines = content.splitlines()
        updated = []
        for line in lines:
            if line.startswith(f"| {entity}.md |"):
                updated.append(new_row)
            else:
                updated.append(line)
        index_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    else:
        index_path.write_text(content.rstrip() + "\n" + new_row + "\n", encoding="utf-8")


def _append_log(entity: str, today: str) -> None:
    """Append an entry to log.md."""
    log_path = SESSION_WIKI_DIR / "log.md"
    entry = f"\n## [{today}] update | {entity}\nPlayer state updated via agent.\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


ALL_TOOLS = [search_modpack_knowledge, read_player_state, update_player_state]
