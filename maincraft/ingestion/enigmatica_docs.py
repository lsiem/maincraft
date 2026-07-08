"""Fetch Enigmatica documentation from GitBook llms.txt index."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from config import ENIGMATICA_LLMS_URL, RAW_DIR

logger = logging.getLogger(__name__)

CACHE_DIR = RAW_DIR / "enigmatica_docs"
_HEADERS = {
    "User-Agent": "ModpackKnowledgeEngine/0.1 (local research tool)",
}


@dataclass
class DocChunk:
    title: str
    body: str
    source_url: str
    metadata: dict = field(default_factory=dict)


def _fetch_llms_index(url: str = ENIGMATICA_LLMS_URL) -> list[str]:
    """Fetch llms.txt and extract page URLs."""
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    text = resp.text

    urls: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # llms.txt format: "- [Title](url)" or bare URLs
        link_match = re.search(r"\((https?://[^)]+)\)", line)
        if link_match:
            urls.append(link_match.group(1))
        elif line.startswith("http"):
            urls.append(line)

    return urls


def _url_to_md_url(url: str) -> str:
    """Convert a GitBook page URL to its .md variant."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path.endswith(".md"):
        path += ".md"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    segment = path.split("/")[-1]
    return segment.replace("-", " ").replace("_", " ").title()


def fetch_enigmatica_docs(pack_filter: str | None = None) -> list[DocChunk]:
    """Fetch all Enigmatica GitBook pages listed in llms.txt."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        page_urls = _fetch_llms_index()
    except Exception as exc:
        logger.error("Failed to fetch llms.txt: %s", exc)
        return _load_cached_docs(pack_filter)

    if not page_urls:
        logger.warning("No URLs found in llms.txt")
        return _load_cached_docs(pack_filter)

    chunks: list[DocChunk] = []
    for url in page_urls:
        md_url = _url_to_md_url(url)
        title = _title_from_url(url)

        # Filter by pack if requested
        if pack_filter:
            url_lower = url.lower()
            if pack_filter == "e6" and "enigmatica-6" not in url_lower and "e6" not in url_lower:
                continue
            if pack_filter == "e9" and "enigmatica-9" not in url_lower and "e9" not in url_lower:
                continue

        cache_file = CACHE_DIR / f"{title.replace(' ', '_')}.md"
        if cache_file.exists():
            body = cache_file.read_text(encoding="utf-8")
        else:
            try:
                resp = requests.get(md_url, headers=_HEADERS, timeout=30)
                if resp.status_code != 200:
                    logger.debug("Skipping %s (HTTP %d)", md_url, resp.status_code)
                    continue
                body = resp.text
                cache_file.write_text(body, encoding="utf-8")
                time.sleep(0.3)
            except Exception as exc:
                logger.debug("Failed to fetch %s: %s", md_url, exc)
                continue

        pack = "e6" if "enigmatica-6" in url.lower() or "e6" in url.lower() else (
            "e9" if "enigmatica-9" in url.lower() or "e9" in url.lower() else "enigmatica"
        )

        chunks.append(DocChunk(
            title=title,
            body=body,
            source_url=url,
            metadata={
                "pack": pack,
                "type": "doc",
                "title": title,
                "source_url": url,
            },
        ))

    logger.info("Fetched %d Enigmatica doc pages", len(chunks))
    return chunks


def _load_cached_docs(pack_filter: str | None = None) -> list[DocChunk]:
    """Load previously cached doc files."""
    chunks: list[DocChunk] = []
    if not CACHE_DIR.exists():
        return chunks
    for f in sorted(CACHE_DIR.glob("*.md")):
        body = f.read_text(encoding="utf-8")
        title = f.stem.replace("_", " ").title()
        chunks.append(DocChunk(
            title=title,
            body=body,
            source_url="",
            metadata={"pack": "enigmatica", "type": "doc", "title": title},
        ))
    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chunks = fetch_enigmatica_docs()
    print(f"Fetched {len(chunks)} doc pages")
