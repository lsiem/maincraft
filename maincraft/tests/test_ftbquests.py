"""Tests for the FTB Quests SNBT parser."""

from __future__ import annotations

from pathlib import Path

from ingestion.parse_ftbquests import _quest_to_chunk, _regex_parse_snbt, parse_ftbquests

FIXTURES = Path(__file__).parent / "fixtures"
E6_FIXTURE = FIXTURES / "e6"
SNBT_FILE = E6_FIXTURE / "config/ftbquests/quests/chapters/starting_out.snbt"


def test_quest_to_chunk_builds_markdown():
    quest = {
        "id": "q1",
        "title": "Collect Wood",
        "subtitle": "Punch a tree",
        "description": ["Punch a tree to get started", "Collect 16 logs"],
        "dependencies": ["q0"],
    }
    chunk = _quest_to_chunk(quest, chapter="starting_out", pack="e6")

    assert chunk is not None
    assert chunk.title == "Collect Wood"
    assert chunk.chapter == "starting_out"
    assert "Collect Wood" in chunk.body
    assert "Punch a tree" in chunk.body
    assert "Punch a tree to get started" in chunk.body
    assert "q0" in chunk.body  # dependency rendered
    assert chunk.metadata["type"] == "quest"
    assert chunk.metadata["chapter"] == "starting_out"


def test_regex_parse_snbt_extracts_quest_fields():
    content = SNBT_FILE.read_text(encoding="utf-8")
    data = _regex_parse_snbt(content)

    quests = data["quests"]
    titles = [q.get("title") for q in quests]
    assert "Collect Wood" in titles
    assert "Make Planks" in titles

    q1 = next(q for q in quests if q.get("title") == "Collect Wood")
    assert q1.get("subtitle") == "Punch a tree"
    assert q1.get("id") == "q1"
    assert "Punch a tree to get started" in q1.get("description", [])
    assert "q0" in q1.get("dependencies", [])


def test_parse_ftbquests_end_to_end():
    """Black-box: whichever SNBT path runs (library or regex fallback),
    the chapter must yield the two quests with their titles/dependencies."""
    chunks = parse_ftbquests("e6", raw_dir=E6_FIXTURE)
    titles = [c.title for c in chunks]

    assert "Collect Wood" in titles
    assert "Make Planks" in titles

    by_title = {c.title: c for c in chunks}
    collect = by_title["Collect Wood"]
    assert collect.chapter == "starting_out"
    assert "Punch a tree" in collect.body  # subtitle
    assert "q0" in collect.body  # dependency

    planks = by_title["Make Planks"]
    assert "q1" in planks.body  # dependency on q1
