"""Parse FTB Quests SNBT chapter files into markdown chunks."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from config import PACKS, RAW_DIR, PackId

logger = logging.getLogger(__name__)

_FMT_RE = re.compile(r"\{@[^}]*\}|\\n")


@dataclass
class QuestChunk:
    pack: str
    quest_id: str
    title: str
    body: str
    chapter: str = ""
    tier: str = ""
    metadata: dict = field(default_factory=dict)


def _clean_snbt_text(text: str) -> str:
    """Strip SNBT formatting tokens and normalize."""
    if not text:
        return ""
    text = _FMT_RE.sub("", text)
    text = text.replace("\\n", "\n")
    return re.sub(r"\s+", " ", text).strip()


def _parse_snbt_file(path: Path) -> dict | None:
    """Parse an SNBT file using ftb-snbt-lib if available, else regex fallback."""
    content = path.read_text(encoding="utf-8", errors="replace")

    try:
        from ftbsnbt import SNBT  # type: ignore[import-untyped]

        return SNBT.parse(content)
    except ImportError:
        logger.debug("ftb-snbt-lib not installed, using regex fallback for %s", path.name)
    except Exception as exc:
        logger.debug("ftb-snbt-lib parse failed for %s: %s, using fallback", path.name, exc)

    return _regex_parse_snbt(content)


def _regex_parse_snbt(content: str) -> dict:
    """Minimal regex-based SNBT quest extractor as fallback."""
    quests: list[dict] = []

    # Split on quest blocks (indented with tabs)
    quest_blocks = re.split(r"\n\t\t\{", content)
    for block in quest_blocks[1:]:  # skip preamble
        quest: dict = {}

        title_m = re.search(r'title:\s*"([^"]*)"', block)
        if title_m:
            quest["title"] = title_m.group(1)

        subtitle_m = re.search(r'subtitle:\s*"([^"]*)"', block)
        if subtitle_m:
            quest["subtitle"] = subtitle_m.group(1)

        id_m = re.search(r'id:\s*"([^"]*)"', block)
        if id_m:
            quest["id"] = id_m.group(1)

        # Description array
        desc_parts = re.findall(r'"([^"]*)"', re.search(r"description:\s*\[(.*?)\]", block, re.DOTALL).group(1) if re.search(r"description:\s*\[", block) else "")
        if desc_parts:
            quest["description"] = desc_parts

        # Dependencies
        deps = re.findall(r'"([^"]*)"', re.search(r"dependencies:\s*\[(.*?)\]", block, re.DOTALL).group(1) if re.search(r"dependencies:\s*\[", block) else "")
        if deps:
            quest["dependencies"] = deps

        if quest.get("title") or quest.get("id"):
            quests.append(quest)

    return {"quests": quests}


def _quest_to_chunk(quest: dict, chapter: str, pack: str) -> QuestChunk | None:
    title = _clean_snbt_text(quest.get("title", ""))
    subtitle = _clean_snbt_text(quest.get("subtitle", ""))
    quest_id = quest.get("id", "")

    if not title and not subtitle:
        return None

    display_title = title or subtitle

    # Description
    desc_raw = quest.get("description", [])
    if isinstance(desc_raw, list):
        desc = "\n".join(_clean_snbt_text(d) for d in desc_raw if d)
    elif isinstance(desc_raw, str):
        desc = _clean_snbt_text(desc_raw)
    else:
        desc = ""

    # Dependencies
    deps = quest.get("dependencies", [])
    dep_str = ", ".join(str(d) for d in deps[:5]) if deps else ""

    # Tasks
    tasks_raw = quest.get("tasks", [])
    task_lines: list[str] = []
    if isinstance(tasks_raw, list):
        for task in tasks_raw:
            if isinstance(task, dict):
                t_title = _clean_snbt_text(task.get("title", ""))
                t_type = task.get("type", "")
                if t_title:
                    task_lines.append(t_title)
                elif t_type:
                    task_lines.append(f"Task: {t_type}")

    # Rewards
    rewards_raw = quest.get("rewards", [])
    reward_lines: list[str] = []
    if isinstance(rewards_raw, list):
        for reward in rewards_raw:
            if isinstance(reward, dict):
                r_type = reward.get("type", "")
                if r_type:
                    reward_lines.append(r_type)

    lines = [f"# Quest: {display_title}"]
    if subtitle and subtitle != title:
        lines.append(f"**Subtitle:** {subtitle}")
    lines.append(f"**Chapter:** {chapter}")
    if desc:
        lines.append(f"\n{desc}")
    if task_lines:
        lines.append("\n**Tasks:**")
        for t in task_lines:
            lines.append(f"- {t}")
    if dep_str:
        lines.append(f"\n**Dependencies:** {dep_str}")
    if reward_lines:
        lines.append("\n**Rewards:**")
        for r in reward_lines:
            lines.append(f"- {r}")

    return QuestChunk(
        pack=pack,
        quest_id=quest_id,
        title=display_title,
        body="\n".join(lines),
        chapter=chapter,
        metadata={
            "pack": pack,
            "type": "quest",
            "quest_id": quest_id,
            "chapter": chapter,
            "title": display_title,
        },
    )


def parse_ftbquests(pack_id: PackId, raw_dir: Path | None = None) -> list[QuestChunk]:
    """Parse all SNBT chapter files for a pack."""
    raw_dir = raw_dir or RAW_DIR / pack_id
    chapters_dir = raw_dir / "config/ftbquests/quests/chapters"

    if not chapters_dir.exists():
        logger.warning("FTB Quests chapters dir not found: %s", chapters_dir)
        return []

    chunks: list[QuestChunk] = []
    for snbt_file in sorted(chapters_dir.glob("*.snbt")):
        chapter = snbt_file.stem
        data = _parse_snbt_file(snbt_file)
        if not data:
            continue

        quests = data.get("quests", [])
        if isinstance(quests, list):
            for quest in quests:
                if isinstance(quest, dict):
                    chunk = _quest_to_chunk(quest, chapter=chapter, pack=pack_id)
                    if chunk:
                        chunks.append(chunk)

    logger.info("Parsed %d FTB quests from %s", len(chunks), pack_id)
    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for pid in ("e6", "e9"):
        chunks = parse_ftbquests(pid)  # type: ignore[arg-type]
        print(f"{pid}: {len(chunks)} quests")
