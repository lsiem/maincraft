"""Tests for the KubeJS / ZenScript script parser."""

from __future__ import annotations

from pathlib import Path

from ingestion.parse_scripts import parse_scripts

FIXTURES = Path(__file__).parent / "fixtures"
E6_FIXTURE = FIXTURES / "e6"
E2E_FIXTURE = FIXTURES / "e2e"


def test_parse_scripts_kubejs():
    chunks = parse_scripts("e6", raw_dir=E6_FIXTURE)
    assert chunks, "expected script chunks from kubejs fixture"

    by_subtype = {}
    for c in chunks:
        by_subtype.setdefault(c.metadata.get("subtype"), []).append(c)

    # Comment chunk
    comment_chunks = by_subtype.get("comment", [])
    assert comment_chunks, "expected a comment chunk"
    assert any("Remove the default bronze ingot recipe" in c.body for c in comment_chunks)

    # Recipe-op chunk
    op_chunks = by_subtype.get("recipe_op", [])
    assert op_chunks, "expected a recipe-op chunk"
    op_body = " ".join(c.body for c in op_chunks)
    assert "event.recipes.remove" in op_body
    assert "event.recipes.custom" in op_body
    assert "event.recipes.replaceInput" in op_body
    # Context comments are attached to the op lines.
    assert "Add a custom alloy recipe" in op_body

    # Metadata
    assert all(c.metadata["type"] == "recipe_change" for c in chunks)
    assert all(c.metadata["pack"] == "e6" for c in chunks)


def test_parse_scripts_zenscript():
    chunks = parse_scripts("e2e", raw_dir=E2E_FIXTURE)
    assert chunks, "expected script chunks from zenscript fixture"

    op_body = " ".join(c.body for c in chunks if c.metadata.get("subtype") == "recipe_op")
    assert "recipes.remove" in op_body
    assert "recipes.addShaped" in op_body
    assert "recipes.removeFurnace" in op_body

    comment_body = " ".join(c.body for c in chunks if c.metadata.get("subtype") == "comment")
    assert "Add a shaped bronze recipe" in comment_body

    assert all(c.metadata["pack"] == "e2e" for c in chunks)


def test_parse_scripts_missing_dir_returns_empty():
    chunks = parse_scripts("e6", raw_dir=FIXTURES / "does-not-exist")
    assert chunks == []
