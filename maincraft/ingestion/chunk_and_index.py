"""Chunk all ingested data and embed into ChromaDB."""

from __future__ import annotations

import argparse
import logging
import uuid
from typing import Any

import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    PACKS,
    PackId,
)
from ingestion.enigmatica_docs import fetch_enigmatica_docs
from ingestion.fetch_github import download_all, download_tarball
from ingestion.gtnh_wiki import fetch_gtnh_wiki
from ingestion.parse_betterquesting import parse_betterquesting
from ingestion.parse_ftbquests import parse_ftbquests
from ingestion.parse_scripts import parse_scripts

logger = logging.getLogger(__name__)

_enc = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_enc.encode(text))


from embeddings import embed_documents, get_embedding_mode
def _get_chroma_collection():
    """Get or create the ChromaDB collection."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _split_long_text(text: str, metadata: dict) -> list[dict[str, Any]]:
    """Split text longer than CHUNK_SIZE tokens; return list of {text, metadata} dicts."""
    if _token_count(text) <= CHUNK_SIZE:
        return [{"text": text, "metadata": metadata}]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE * 4,  # chars ≈ tokens * 4
        chunk_overlap=CHUNK_OVERLAP * 4,
        length_function=len,
    )
    parts = splitter.split_text(text)
    results = []
    for i, part in enumerate(parts):
        part_meta = {**metadata, "chunk_part": i, "chunk_total": len(parts)}
        results.append({"text": part, "metadata": part_meta})
    return results


def _collect_chunks_for_pack(pack_id: PackId) -> list[dict[str, Any]]:
    """Run all parsers for a pack and return flat chunk list."""
    pack = PACKS[pack_id]
    all_chunks: list[dict[str, Any]] = []

    # Quests
    if pack.quest_format in ("betterquesting_tree", "betterquesting_json"):
        for qc in parse_betterquesting(pack_id):
            all_chunks.append({"text": qc.body, "metadata": qc.metadata})
    elif pack.quest_format == "ftbquests_snbt":
        for qc in parse_ftbquests(pack_id):
            all_chunks.append({"text": qc.body, "metadata": qc.metadata})

    # Scripts
    for sc in parse_scripts(pack_id):
        parts = _split_long_text(sc.body, sc.metadata)
        all_chunks.extend(parts)

    return all_chunks


def ingest_pack(
    pack_id: PackId,
    force_download: bool = False,
    skip_wiki: bool = False,
    wiki_playwright: bool = False,
) -> int:
    """Download, parse, and index a single pack. Returns chunk count."""
    download_tarball(pack_id, force=force_download)
    chunks = _collect_chunks_for_pack(pack_id)

    # Wiki / docs
    if pack_id == "gtnh" and not skip_wiki:
        for wc in fetch_gtnh_wiki(use_playwright=wiki_playwright):
            parts = _split_long_text(wc.body, wc.metadata)
            chunks.extend(parts)
    elif pack_id in ("e6", "e9") and not skip_wiki:
        for dc in fetch_enigmatica_docs(pack_filter=pack_id):
            parts = _split_long_text(dc.body, dc.metadata)
            chunks.extend(parts)

    if not chunks:
        logger.warning("No chunks produced for %s", pack_id)
        return 0

    _index_chunks(chunks)
    logger.info("Indexed %d chunks for %s", len(chunks), pack_id)
    return len(chunks)


def _index_chunks(chunks: list[dict[str, Any]]) -> None:
    """Embed and upsert chunks into ChromaDB."""
    collection = _get_chroma_collection()
    get_embedding_mode()  # probe once up front

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [str(uuid.uuid4()) for _ in chunks]

    clean_metas = []
    for m in metadatas:
        clean = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v for k, v in m.items()}
        clean_metas.append(clean)

    batch_size = 64
    total_batches = (len(texts) + batch_size - 1) // batch_size
    for i in range(0, len(texts), batch_size):
        batch_num = i // batch_size + 1
        if total_batches > 1:
            logger.info("Embedding batch %d/%d (%d chunks)", batch_num, total_batches, len(texts))

        batch_texts = texts[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_metas = clean_metas[i : i + batch_size]

        batch_embeddings = embed_documents(batch_texts)
        if batch_embeddings is not None:
            collection.upsert(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_texts,
                metadatas=batch_metas,
            )
        else:
            collection.upsert(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metas,
            )


def ingest_all(
    force_download: bool = False,
    skip_wiki: bool = False,
    wiki_playwright: bool = False,
) -> dict[str, int]:
    """Ingest all packs. Returns {pack_id: chunk_count}."""
    results: dict[str, int] = {}
    for pack_id in PACKS:
        try:
            count = ingest_pack(
                pack_id,
                force_download=force_download,
                skip_wiki=skip_wiki,
                wiki_playwright=wiki_playwright,
            )
            results[pack_id] = count
        except Exception as exc:
            logger.error("Failed to ingest %s: %s", pack_id, exc)
            results[pack_id] = 0
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Chunk and index modpack knowledge")
    parser.add_argument("--pack", choices=list(PACKS.keys()), help="Single pack to ingest")
    parser.add_argument("--all", action="store_true", help="Ingest all packs")
    parser.add_argument("--force", action="store_true", help="Re-download tarballs")
    parser.add_argument("--skip-wiki", action="store_true", help="Skip wiki/doc fetching (quests + scripts only)")
    parser.add_argument(
        "--wiki-playwright",
        action="store_true",
        help="Use Playwright browser fallback for GTNH wiki if API is blocked (slow)",
    )
    args = parser.parse_args()

    if args.all:
        results = ingest_all(
            force_download=args.force,
            skip_wiki=args.skip_wiki,
            wiki_playwright=args.wiki_playwright,
        )
        for pid, count in results.items():
            print(f"  {pid}: {count} chunks")
    elif args.pack:
        count = ingest_pack(
            args.pack,  # type: ignore[arg-type]
            force_download=args.force,
            skip_wiki=args.skip_wiki,
            wiki_playwright=args.wiki_playwright,
        )
        print(f"  {args.pack}: {count} chunks")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
