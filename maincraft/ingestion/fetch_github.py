"""Download and extract GitHub repository tarballs for modpack data."""

from __future__ import annotations

import io
import logging
import tarfile
from pathlib import Path

import requests

from config import PACKS, RAW_DIR, PackConfig, PackId

logger = logging.getLogger(__name__)

# Paths we care about inside each tarball (prefix-matched after extraction)
QUEST_PATHS: dict[str, tuple[str, ...]] = {
    "betterquesting_tree": ("config/betterquesting/DefaultQuests",),
    "betterquesting_json": ("config/betterquesting/DefaultQuests.json",),
    "ftbquests_snbt": ("config/ftbquests/quests/chapters",),
}


def tarball_url(pack: PackConfig) -> str:
    return (
        f"https://api.github.com/repos/{pack.github_repo}/tarball/{pack.github_branch}"
    )


def download_tarball(pack_id: PackId, force: bool = False) -> Path:
    """Download a GitHub tarball and extract relevant paths into data/raw/<pack_id>/."""
    pack = PACKS[pack_id]
    dest = RAW_DIR / pack_id
    marker = dest / ".downloaded"

    if marker.exists() and not force:
        logger.info("Tarball for %s already cached at %s", pack_id, dest)
        return dest

    dest.mkdir(parents=True, exist_ok=True)
    url = tarball_url(pack)
    logger.info("Downloading %s from %s …", pack.display_name, url)

    resp = requests.get(url, stream=True, timeout=120, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ModpackKnowledgeEngine/0.1",
    })
    resp.raise_for_status()

    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        members = tar.getmembers()
        # GitHub tarballs have a top-level dir like Org-repo-sha/
        top_prefix = members[0].name.split("/")[0] if members else ""

        wanted_prefixes = list(QUEST_PATHS.get(pack.quest_format, ()))
        wanted_prefixes.extend(pack.script_dirs)

        for member in members:
            if not member.isfile():
                continue
            rel = member.name
            if top_prefix and rel.startswith(top_prefix + "/"):
                rel = rel[len(top_prefix) + 1 :]

            if not any(rel.startswith(p) for p in wanted_prefixes):
                continue

            out_path = dest / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            f = tar.extractfile(member)
            if f:
                out_path.write_bytes(f.read())

    marker.write_text(f"source={pack.github_repo}@{pack.github_branch}\n")
    logger.info("Extracted %s data to %s", pack_id, dest)
    return dest


def download_all(force: bool = False) -> dict[PackId, Path]:
    """Download tarballs for all registered packs."""
    results: dict[PackId, Path] = {}
    for pack_id in PACKS:
        results[pack_id] = download_tarball(pack_id, force=force)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="Download modpack GitHub tarballs")
    parser.add_argument("--pack", choices=list(PACKS.keys()), help="Single pack to download")
    parser.add_argument("--all", action="store_true", help="Download all packs")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    if args.all:
        download_all(force=args.force)
    elif args.pack:
        download_tarball(args.pack, force=args.force)
    else:
        parser.print_help()
