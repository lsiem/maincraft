"""Fetch GTNH wiki pages via MediaWiki API with optional Playwright fallback."""

from __future__ import annotations

import logging
import re
import time
import defusedxml.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from config import GTNH_WIKI_PRIORITY_PAGES, RAW_DIR

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Playwright

logger = logging.getLogger(__name__)

WIKI_API = "https://wiki.gtnewhorizons.com/api.php"
WIKI_BASE = "https://wiki.gtnewhorizons.com/wiki"
CACHE_DIR = RAW_DIR / "gtnh_wiki"
PAGE_TIMEOUT_MS = 20_000

_HEADERS = {
    "User-Agent": "ModpackKnowledgeEngine/0.1 (local research tool; contact: github.com)",
}


@dataclass
class WikiChunk:
    title: str
    body: str
    source_url: str
    metadata: dict = field(default_factory=dict)


def _is_bot_challenge(response_text: str) -> bool:
    return "Checking your connection" in response_text or "unusual activity" in response_text


def _api_fetch_page(title: str) -> str | None:
    """Try fetching a single page via MediaWiki parse API."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    try:
        resp = requests.get(WIKI_API, params=params, headers=_HEADERS, timeout=15)
        if _is_bot_challenge(resp.text):
            return None
        data = resp.json()
        return data.get("parse", {}).get("wikitext", "")
    except Exception as exc:
        logger.debug("API fetch failed for %s: %s", title, exc)
        return None


def _api_list_allpages(max_pages: int | None = None) -> list[str]:
    """Enumerate all page titles in the main namespace via the MediaWiki allpages API.

    Paginates via the continue tokens MediaWiki returns. Returns an empty list
    if the API is blocked or unreachable. ``max_pages`` caps the result count
    (useful for testing).
    """
    titles: list[str] = []
    params: dict = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "aplimit": "500",
        "formatversion": "2",
    }
    while True:
        try:
            resp = requests.get(WIKI_API, params=params, headers=_HEADERS, timeout=20)
            if _is_bot_challenge(resp.text):
                logger.warning("allpages blocked by bot challenge; stopping at %d pages", len(titles))
                break
            data = resp.json()
        except Exception as exc:
            logger.warning("allpages request failed: %s", exc)
            break

        for p in data.get("query", {}).get("allpages", []):
            t = p.get("title")
            if t:
                titles.append(t)

        if max_pages and len(titles) >= max_pages:
            return titles[:max_pages]

        cont = data.get("continue") or {}
        if not cont:
            break
        # Merge continuation tokens (apcontinue + generic continue) back in.
        params = {**params, **cont}
        time.sleep(0.3)

    return titles


def _playwright_fetch_pages(titles: list[str]) -> dict[str, str | None]:
    """Fetch multiple pages with a single shared browser instance."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed — cannot use browser fallback")
        return {t: None for t in titles}

    results: dict[str, str | None] = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            for i, title in enumerate(titles, 1):
                logger.info("Playwright fetching wiki page %d/%d: %s", i, len(titles), title)
                results[title] = _playwright_fetch_one(page, title)
            browser.close()
    except Exception as exc:
        logger.warning("Playwright session failed: %s", exc)
        for title in titles:
            results.setdefault(title, None)
    return results


def _playwright_fetch_one(page: "Page", title: str) -> str | None:
    """Fetch one page using an existing browser page."""
    url = f"{WIKI_BASE}/{title}?action=raw"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        # Miraheze challenge pages need a moment to resolve
        page.wait_for_timeout(2000)
        content = page.inner_text("body")
        if _is_bot_challenge(content):
            return None
        return content if content.strip() else None
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", title, exc)
        return None


def _wikitext_to_plain(wikitext: str) -> str:
    """Rough wikitext → plain text conversion."""
    text = wikitext
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"^=+\s*(.+?)\s*=+$", r"# \1", text, flags=re.MULTILINE)
    text = re.sub(r"'''(.+?)'''", r"**\1**", text)
    text = re.sub(r"''(.+?)''", r"*\1*", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _chunk_from_body(title: str, body: str) -> WikiChunk:
    return WikiChunk(
        title=title,
        body=body,
        source_url=f"{WIKI_BASE}/{title}",
        metadata={
            "pack": "gtnh",
            "type": "wiki",
            "title": title,
            "source_url": f"{WIKI_BASE}/{title}",
        },
    )


def _parse_export_xml(xml_path: Path) -> list[WikiChunk]:
    """Parse a MediaWiki Special:Export XML dump."""
    chunks: list[WikiChunk] = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        for page in root.findall(".//mw:page", ns):
            title_el = page.find("mw:title", ns)
            text_el = page.find(".//mw:text", ns)
            if title_el is not None and text_el is not None and text_el.text:
                title = title_el.text
                plain = _wikitext_to_plain(text_el.text)
                chunks.append(_chunk_from_body(title, f"# {title}\n\n{plain}"))
    except Exception as exc:
        logger.error("Failed to parse export XML %s: %s", xml_path, exc)
    return chunks


def fetch_gtnh_wiki(
    pages: list[str] | None = None,
    use_playwright: bool = False,
    all_pages: bool = False,
    max_pages: int | None = None,
) -> list[WikiChunk]:
    """Fetch GTNH wiki pages, using cache when available.

    By default only uses the MediaWiki API and cached files. Playwright fallback
    is opt-in because Miraheze challenge pages are slow and unreliable.
    Place a manual export at data/raw/gtnh_wiki/export.xml to bulk-import pages.

    If ``all_pages`` is True, enumerate the full main-namespace page list via the
    MediaWiki ``allpages`` API instead of the curated priority list, for much
    broader RAG coverage. Requires API access (or pre-cached files); falls back
    to the curated list if enumeration is blocked. ``max_pages`` caps enumeration.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    export_xml = CACHE_DIR / "export.xml"
    if export_xml.exists():
        logger.info("Loading GTNH wiki from manual export: %s", export_xml)
        return _parse_export_xml(export_xml)

    if all_pages:
        enumerated = _api_list_allpages(max_pages=max_pages)
        if enumerated:
            pages = enumerated
            logger.info("Enumerated %d pages via allpages API", len(pages))
        else:
            logger.warning(
                "allpages enumeration returned no titles (API blocked?). "
                "Falling back to curated page list + cache."
            )
            pages = pages or GTNH_WIKI_PRIORITY_PAGES
    else:
        pages = pages or GTNH_WIKI_PRIORITY_PAGES

    chunks: list[WikiChunk] = []
    to_fetch: list[str] = []

    # Load cache hits first
    for title in pages:
        cache_file = CACHE_DIR / f"{title}.md"
        if cache_file.exists():
            body = cache_file.read_text(encoding="utf-8")
            chunks.append(_chunk_from_body(title, body))
        else:
            to_fetch.append(title)

    if not to_fetch:
        logger.info("All %d GTNH wiki pages loaded from cache", len(chunks))
        return chunks

    # Probe API with first uncached page
    api_works = _api_fetch_page(to_fetch[0]) is not None
    if api_works:
        logger.info("MediaWiki API accessible — fetching %d uncached pages", len(to_fetch))
    elif use_playwright:
        logger.info("API blocked — using Playwright for %d uncached pages", len(to_fetch))
    else:
        logger.warning(
            "GTNH wiki API is blocked and Playwright fallback is disabled. "
            "Skipping %d uncached pages. Options:\n"
            "  1. Re-run with --wiki-playwright (slow, ~20s/page)\n"
            "  2. Export pages to data/raw/gtnh_wiki/export.xml (see README)\n"
            "  3. Pre-cache individual pages as data/raw/gtnh_wiki/<Page>.md",
            len(to_fetch),
        )
        logger.info("Loaded %d GTNH wiki pages from cache (skipped %d)", len(chunks), len(to_fetch))
        return chunks

    # Fetch uncached pages
    if api_works:
        for title in to_fetch:
            wikitext = _api_fetch_page(title)
            time.sleep(0.3)
            if wikitext:
                plain = _wikitext_to_plain(wikitext)
                body = f"# {title}\n\n{plain}"
                (CACHE_DIR / f"{title}.md").write_text(body, encoding="utf-8")
                chunks.append(_chunk_from_body(title, body))
            else:
                logger.warning("Could not fetch wiki page via API: %s", title)
    else:
        pw_results = _playwright_fetch_pages(to_fetch)
        for title, wikitext in pw_results.items():
            if wikitext:
                plain = _wikitext_to_plain(wikitext)
                body = f"# {title}\n\n{plain}"
                (CACHE_DIR / f"{title}.md").write_text(body, encoding="utf-8")
                chunks.append(_chunk_from_body(title, body))
            else:
                logger.warning("Could not fetch wiki page via Playwright: %s", title)

    logger.info("Fetched %d GTNH wiki pages total", len(chunks))
    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="Fetch GTNH wiki pages")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright fallback if API blocked")
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Enumerate the full main-namespace page list via the allpages API instead of the curated list",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Cap the number of pages enumerated with --all-pages (useful for testing)",
    )
    args = parser.parse_args()
    result = fetch_gtnh_wiki(
        use_playwright=args.playwright,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    print(f"Fetched {len(result)} pages")
