"""Tests for the BetterQuesting parser (prereq resolution, BBCode, tiers, layouts)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.parse_betterquesting import (
    _infer_tier,
    _quest_from_json,
    parse_monolith,
    parse_tree,
    strip_formatting,
)

FIXTURES = Path(__file__).parent / "fixtures"
GTNH_FIXTURE = FIXTURES / "gtnh"
E2E_FIXTURE = FIXTURES / "e2e"


# --------------------------------------------------------------------------
# strip_formatting: BBCode + Minecraft formatting codes
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("§aGreen [warn]careful[/warn]", "Green careful"),
        ("[warn]Danger![/warn]", "Danger!"),
        ("[note]Safe.[/note]", "Safe."),
        ("[url=https://x.com]click here[/url]", "click here"),
        ("[url]https://x.com[/url]", "https://x.com"),
        ("[warn][note]nested[/note][/warn]", "nested"),
        ("plain text", "plain text"),
    ],
)
def test_strip_formatting(raw, expected):
    assert strip_formatting(raw) == expected


# --------------------------------------------------------------------------
# _infer_tier: longest/most-specific first
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "questline,expected",
    [
        ("UHV", "UHV"),
        ("Ultra High Voltage (UHV)", "UHV"),
        ("LuV", "LUV"),
        ("LuV Age", "LUV"),
        ("UV", "UV"),
        ("Ultimate Voltage (UV)", "UV"),
        ("ULV", "ULV"),
        ("LV", "LV"),
        ("Low Voltage (LV)", "LV"),
        ("IV", "IV"),
        ("HV", "HV"),
        ("EV", "EV"),
        ("MV", "MV"),
        ("ZPM", "ZPM"),
        ("Steam Age", "STEAM"),
        ("Stone Age", "STONE"),
        ("Random Questline", ""),
    ],
)
def test_infer_tier(questline, expected):
    assert _infer_tier(questline) == expected


# --------------------------------------------------------------------------
# _quest_from_json: prerequisite resolution
# --------------------------------------------------------------------------

def test_quest_from_json_resolves_prereqs_to_titles():
    data = {
        "questID:8": 239,
        "properties:10": {"betterquesting:10": {"name:8": "Yet another brick"}},
        "preRequisites:11": [251, 999],
    }
    id_map = {"251": "Infusion Start"}  # 999 intentionally unresolved

    chunk = _quest_from_json(data, questline="LV", pack="gtnh", id_to_title=id_map)

    assert chunk is not None
    assert "Infusion Start" in chunk.body
    # Unresolved IDs fall back to the raw id.
    assert "999" in chunk.body
    assert chunk.metadata["prerequisites"] == "Infusion Start, 999"


def test_quest_from_json_without_id_map_keeps_raw_ids():
    data = {
        "questID:8": 239,
        "properties:10": {"betterquesting:10": {"name:8": "Brick"}},
        "preRequisites:11": [251],
    }
    chunk = _quest_from_json(data, pack="gtnh")
    assert "251" in chunk.body
    assert chunk.metadata["prerequisites"] == "251"


# --------------------------------------------------------------------------
# parse_tree: GTNH tree layout end-to-end
# --------------------------------------------------------------------------

def test_parse_tree_resolves_prereqs_and_strips_bbcode():
    chunks = parse_tree("gtnh", raw_dir=GTNH_FIXTURE)
    by_id = {c.quest_id: c for c in chunks}

    assert "239" in by_id
    assert "251" in by_id

    q239 = by_id["239"]
    # Prereq 251 resolved to its title.
    assert "Infusion Start" in q239.body
    assert q239.metadata["prerequisites"] == "Infusion Start"
    # BBCode tags stripped from description.
    assert "[warn]" not in q239.body
    assert "[/warn]" not in q239.body
    assert "[url=" not in q239.body
    assert "guide" in q239.body  # link label kept
    # Tier inferred from questline folder name "Steam Age".
    assert q239.tier == "STEAM"
    assert q239.metadata["tier"] == "STEAM"

    q251 = by_id["251"]
    assert q251.title == "Infusion Start"
    # No prerequisites line when preRequisites is empty.
    assert "Prerequisites" not in q251.body


# --------------------------------------------------------------------------
# parse_monolith: E2E single-file layout end-to-end
# --------------------------------------------------------------------------

def test_parse_monolith_resolves_prereqs_and_questline():
    chunks = parse_monolith("e2e", raw_dir=E2E_FIXTURE)
    by_id = {c.quest_id: c for c in chunks}

    assert "10" in by_id
    assert "20" in by_id

    q20 = by_id["20"]
    assert q20.title == "Smelting 101"
    # Prereq 10 resolved to its title.
    assert "First Steps" in q20.body
    assert q20.metadata["prerequisites"] == "First Steps"
    # Questline resolved via questLines membership.
    assert q20.questline == "Main Line"

    q10 = by_id["10"]
    assert q10.title == "First Steps"
    assert "Prerequisites" not in q10.body
