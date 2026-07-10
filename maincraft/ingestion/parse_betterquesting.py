"""Parse BetterQuesting quest data into markdown chunks.

Handles two layouts:
  - GTNH tree: config/betterquesting/DefaultQuests/{Quests,QuestLines}/
  - E2E legacy: config/betterquesting/DefaultQuests.json
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import PACKS, RAW_DIR, PackId

logger = logging.getLogger(__name__)

# Minecraft formatting codes (§x)
_FMT_RE = re.compile(r"§.")

# BetterQuesting BBCode-style tags used in GTNH quest descriptions, e.g.
# [warn]…[/warn], [note]…[/note], [url=href]label[/url]. Inner text is kept.
_BB_TAG_PAIRED = re.compile(r"\[([a-zA-Z]+)(?:=[^\]]*)?\](.*?)\[/\1\]", re.DOTALL)
_BB_OPEN = re.compile(r"\[[a-zA-Z]+(?:=[^\]]*)?\]")
_BB_CLOSE = re.compile(r"\[/[a-zA-Z]+\]")


@dataclass
class QuestChunk:
    pack: str
    quest_id: str
    title: str
    body: str
    questline: str = ""
    tier: str = ""
    metadata: dict = field(default_factory=dict)


def _strip_bbcode(text: str) -> str:
    """Unwrap/strip BetterQuesting BBCode tags, keeping inner text and link labels."""
    if not text:
        return ""
    prev = None
    iterations = 0
    while prev != text and iterations < 10:
        prev = text
        text = _BB_TAG_PAIRED.sub(r"\2", text)
        iterations += 1
    text = _BB_OPEN.sub("", text)
    text = _BB_CLOSE.sub("", text)
    return text


def strip_formatting(text: str) -> str:
    """Remove Minecraft § formatting codes and BetterQuesting BBCode tags, then normalize whitespace."""
    if not text:
        return ""
    text = _FMT_RE.sub("", text)
    text = _strip_bbcode(text)
    return re.sub(r"\s+", " ", text).strip()


def _infer_tier(questline: str) -> str:
    """Guess GTNH voltage tier from questline name.

    Candidates are checked longest/most-specific first so that e.g. ``UHV`` is
    not misreported as ``UH`` and ``LuV`` is reported as ``LUV`` rather than ``LU``.
    """
    upper = questline.upper()
    for tier in (
        "UHV", "UEV", "UIV", "UMV", "UXV", "ULV", "LUV",
        "ZPM", "UV", "IV", "EV", "HV", "MV", "LV",
        "STEAM", "STONE",
    ):
        if tier in upper:
            return tier
    return ""


def _get_field(obj: dict, *keys: str, default: Any = "") -> Any:
    """Try multiple SNBT-style key variants."""
    for k in keys:
        if k in obj:
            return obj[k]
    return default


def _parse_task(task: dict) -> str:
    """Extract human-readable task description from a BQ task object."""
    parts: list[str] = []
    task_type = _get_field(task, "index:3", "taskType", "taskID:8")

    # requiredItems can be a list or nested dict (requiredItems:9 -> 0:10 -> ...)
    items_raw = _get_field(task, "requiredItems", "requiredItems:9", default=None)
    if items_raw:
        if isinstance(items_raw, dict):
            for _k, item in items_raw.items():
                if isinstance(item, dict):
                    count = _get_field(item, "count:3", "Count:3", "count", default=1)
                    name = _get_field(item, "id:8", "id", default="unknown")
                    meta = _get_field(item, "Damage:2", "Damage", default=0)
                    parts.append(f"{count}x {name}" + (f":{meta}" if meta else ""))
        elif isinstance(items_raw, list):
            for item in items_raw:
                if isinstance(item, dict):
                    count = _get_field(item, "count:3", "Count:3", "count", default=1)
                    name = _get_field(item, "id:8", "id", default="unknown")
                    parts.append(f"{count}x {name}")
    elif "required" in task:
        parts.append(str(task["required"]))
    elif "target" in task:
        parts.append(f"Target: {task['target']}")

    if not parts and task_type:
        parts.append(f"Task type: {task_type}")

    return ", ".join(parts) if parts else ""


def _parse_reward(reward: dict) -> str:
    parts: list[str] = []
    if "rewardID" in reward:
        rtype = reward.get("index:3", reward.get("rewardType", ""))
        if "items" in reward or "rewards:9" in reward:
            items = reward.get("items", reward.get("rewards:9", {}).get("0:10", {}))
            if isinstance(items, dict):
                for k, v in items.items():
                    if isinstance(v, dict):
                        count = v.get("Count:3", v.get("count", 1))
                        name = v.get("id:8", v.get("id", ""))
                        parts.append(f"{count}x {name}")
        elif rtype:
            parts.append(rtype)
    return ", ".join(parts) if parts else ""


def _quest_title(quest_data: dict) -> str:
    """Extract a cleaned quest title from a BetterQuesting quest JSON object."""
    props = _get_field(quest_data, "properties:10", "properties", default={})
    quest_id = str(_get_field(quest_data, "questID:8", "questID:3", "questID", default=""))
    bq_props = props.get("betterquesting:10", props) if isinstance(props, dict) else {}
    return strip_formatting(
        _get_field(bq_props, "name:8", "name", default="")
        or _get_field(quest_data, "name", default="")
        or f"Quest {quest_id[:8]}"
    )


def _quest_from_json(
    quest_data: dict,
    questline: str = "",
    pack: str = "",
    id_to_title: dict[str, str] | None = None,
) -> QuestChunk | None:
    """Convert a single BetterQuesting quest JSON object to a QuestChunk.

    If ``id_to_title`` is provided, numeric prerequisite IDs are resolved to
    human-readable quest titles for both the markdown body and metadata.
    """
    quest_id = str(_get_field(quest_data, "questID:8", "questID:3", "questID", default=""))
    title = _quest_title(quest_data)
    props = _get_field(quest_data, "properties:10", "properties", default={})
    bq_props = props.get("betterquesting:10", props) if isinstance(props, dict) else {}
    desc = strip_formatting(
        _get_field(bq_props, "desc:8", "desc", default="")
        or _get_field(quest_data, "desc", default="")
    )

    # Tasks
    tasks_raw = _get_field(quest_data, "tasks:9", "tasks", default={})
    task_lines: list[str] = []
    if isinstance(tasks_raw, dict):
        for _key, task in tasks_raw.items():
            if isinstance(task, dict):
                t = _parse_task(task)
                if t:
                    task_lines.append(t)

    # Rewards
    rewards_raw = _get_field(quest_data, "rewards:9", "rewards", default={})
    reward_lines: list[str] = []
    if isinstance(rewards_raw, dict):
        for _key, reward in rewards_raw.items():
            if isinstance(reward, dict):
                r = _parse_reward(reward)
                if r:
                    reward_lines.append(r)

    # Prerequisites — resolve numeric IDs to quest titles when a map is available
    prereqs_raw = _get_field(quest_data, "preRequisites:11", "preRequisites", default=[])
    prereq_ids: list[str] = []
    if isinstance(prereqs_raw, list):
        prereq_ids = [str(p) for p in prereqs_raw]
    elif isinstance(prereqs_raw, dict):
        prereq_ids = [str(v) for v in prereqs_raw.values()]

    resolved_prereqs: list[str] = []
    for pid in prereq_ids:
        if id_to_title and id_to_title.get(pid):
            resolved_prereqs.append(id_to_title[pid])
        else:
            resolved_prereqs.append(pid)

    # Build markdown body
    lines = [f"# Quest: {title}"]
    if questline:
        lines.append(f"**Questline:** {questline}")
    if desc:
        lines.append(f"\n{desc}")
    if task_lines:
        lines.append("\n**Requires:**")
        for t in task_lines:
            lines.append(f"- {t}")
    if resolved_prereqs:
        lines.append(f"\n**Prerequisites:** {', '.join(resolved_prereqs[:5])}")
    if reward_lines:
        lines.append("\n**Rewards:**")
        for r in reward_lines:
            lines.append(f"- {r}")

    tier = _infer_tier(questline)
    return QuestChunk(
        pack=pack,
        quest_id=quest_id,
        title=title,
        body="\n".join(lines),
        questline=questline,
        tier=tier,
        metadata={
            "pack": pack,
            "type": "quest",
            "quest_id": quest_id,
            "questline": questline,
            "tier": tier,
            "title": title,
            "prerequisites": ", ".join(resolved_prereqs[:10]),
        },
    )


def parse_tree(pack_id: PackId, raw_dir: Path | None = None) -> list[QuestChunk]:
    """Parse GTNH-style DefaultQuests/ directory tree."""
    raw_dir = raw_dir or RAW_DIR / pack_id
    quests_dir = raw_dir / "config/betterquesting/DefaultQuests/Quests"
    questlines_dir = raw_dir / "config/betterquesting/DefaultQuests/QuestLines"

    if not quests_dir.exists():
        logger.warning("Quests directory not found: %s", quests_dir)
        return []

    # Build questline name lookup from QuestLines dirs
    questline_names: dict[str, str] = {}
    if questlines_dir.exists():
        for ql_dir in questlines_dir.iterdir():
            if ql_dir.is_dir():
                name = ql_dir.name.rsplit("-", 1)[0]
                for f in ql_dir.glob("*.json"):
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        ql_id = str(_get_field(data, "questLineID:8", "questLineID:3", "questLineID", "lineID:3"))
                        if ql_id:
                            questline_names[ql_id] = name
                    except (json.JSONDecodeError, OSError):
                        pass

    # Two passes: first build a quest_id -> title map so prerequisite IDs can be
    # resolved to human-readable titles, then build the chunks.
    parsed: list[tuple[str, dict]] = []
    id_to_title: dict[str, str] = {}
    for ql_folder in sorted(quests_dir.iterdir()):
        if not ql_folder.is_dir():
            continue
        questline = ql_folder.name.rsplit("-", 1)[0]
        for quest_file in sorted(ql_folder.glob("*.json")):
            try:
                data = json.loads(quest_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Skipping %s: %s", quest_file, exc)
                continue
            qid = str(_get_field(data, "questID:8", "questID:3", "questID", default=""))
            if qid:
                id_to_title[qid] = _quest_title(data)
            parsed.append((questline, data))

    chunks: list[QuestChunk] = []
    for questline, data in parsed:
        chunk = _quest_from_json(data, questline=questline, pack=pack_id, id_to_title=id_to_title)
        if chunk:
            chunks.append(chunk)

    logger.info("Parsed %d quests from %s tree layout", len(chunks), pack_id)
    return chunks


def parse_monolith(pack_id: PackId, raw_dir: Path | None = None) -> list[QuestChunk]:
    """Parse E2E-style single DefaultQuests.json file."""
    raw_dir = raw_dir or RAW_DIR / pack_id
    quest_file = raw_dir / "config/betterquesting/DefaultQuests.json"

    if not quest_file.exists():
        logger.warning("Quest file not found: %s", quest_file)
        return []

    data = json.loads(quest_file.read_text(encoding="utf-8"))

    # Build questline lookup
    questline_map: dict[str, str] = {}
    questlines = _get_field(data, "questLines:9", "questLines", default={})
    if isinstance(questlines, dict):
        for _key, ql in questlines.items():
            if isinstance(ql, dict):
                ql_id = str(_get_field(ql, "questLineID:8", "questLineID:3", "lineID:3", "questLineID"))
                props = _get_field(ql, "properties:10", "properties", default={})
                bq_props = props.get("betterquesting:10", props) if isinstance(props, dict) else {}
                name = strip_formatting(
                    _get_field(bq_props, "name:8", "name", default="")
                    or ql_id[:8]
                )
                questline_map[ql_id] = name

    # Map quest -> questline via questLine membership
    quest_to_line: dict[str, str] = {}
    if isinstance(questlines, dict):
        for _key, ql in questlines.items():
            if isinstance(ql, dict):
                ql_id = str(_get_field(ql, "questLineID:8", "questLineID:3", "lineID:3", "questLineID"))
                ql_name = questline_map.get(ql_id, "")
                quests_in_line = _get_field(ql, "quests:9", "quests", default={})
                if isinstance(quests_in_line, dict):
                    for _qk, qref in quests_in_line.items():
                        if isinstance(qref, dict):
                            qid = str(_get_field(qref, "id:8", "id:3", "id"))
                            if qid:
                                quest_to_line[qid] = ql_name

    # Two passes: build quest_id -> title map, then build chunks with resolved prereqs.
    quests = _get_field(data, "questDatabase:9", "quests:9", "quests", default={})
    id_to_title: dict[str, str] = {}
    quest_entries: list[dict] = []
    if isinstance(quests, dict):
        for _key, quest_data in quests.items():
            if isinstance(quest_data, dict):
                qid = str(_get_field(quest_data, "questID:8", "questID:3", "questID"))
                if qid:
                    id_to_title[qid] = _quest_title(quest_data)
                quest_entries.append(quest_data)

    chunks: list[QuestChunk] = []
    for quest_data in quest_entries:
        qid = str(_get_field(quest_data, "questID:8", "questID:3", "questID"))
        questline = quest_to_line.get(qid, "")
        chunk = _quest_from_json(quest_data, questline=questline, pack=pack_id, id_to_title=id_to_title)
        if chunk:
            chunks.append(chunk)

    logger.info("Parsed %d quests from %s monolith layout", len(chunks), pack_id)
    return chunks


def parse_betterquesting(pack_id: PackId, raw_dir: Path | None = None) -> list[QuestChunk]:
    """Dispatch to the correct parser based on pack quest format."""
    pack = PACKS[pack_id]
    if pack.quest_format == "betterquesting_tree":
        return parse_tree(pack_id, raw_dir)
    elif pack.quest_format == "betterquesting_json":
        return parse_monolith(pack_id, raw_dir)
    else:
        logger.warning("Pack %s does not use BetterQuesting", pack_id)
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for pid in ("gtnh", "e2e"):
        chunks = parse_betterquesting(pid)  # type: ignore[arg-type]
        print(f"{pid}: {len(chunks)} quests")
