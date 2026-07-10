"""Tests for the hybrid BM25 + vector rescoring logic in embeddings.py."""

from __future__ import annotations

import builtins

from embeddings import _minmax_normalize, _tokenize, hybrid_rescore


def test_tokenize():
    assert _tokenize("Bronze Age: smelt!") == ["bronze", "age", "smelt"]
    assert _tokenize("") == []
    assert _tokenize(None) == []


def test_minmax_normalize():
    assert _minmax_normalize([]) == []
    assert _minmax_normalize([5.0]) == [0.5]  # constant -> neutral
    assert _minmax_normalize([0.0, 1.0]) == [0.0, 1.0]
    assert _minmax_normalize([2.0, 4.0, 6.0]) == [0.0, 0.5, 1.0]


def test_hybrid_rescore_bm25_boosts_keyword_match():
    docs = [
        "Bronze Age: smelt bronze ingots in a furnace.",
        "Steam Age: build a steam boiler and turbine.",
        "Electric Blast Furnace: high-temperature smelting.",
    ]
    # Vector distances slightly favor doc index 1, but BM25 should pull doc 0
    # to the top for the query "bronze smelting".
    distances = [0.5, 0.45, 0.55]
    metas = [{"type": "quest"}, {"type": "quest"}, {"type": "wiki"}]

    res = hybrid_rescore("bronze smelting", docs, distances, metas)
    assert res[0][1].startswith("Bronze Age")
    # Sorted descending by score.
    scores = [s for s, _d, _m in res]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_rescore_progression_boost_favors_quests():
    docs = ["Bronze quest chunk", "Steam wiki chunk", "EBF wiki chunk"]
    distances = [0.5, 0.4, 0.45]
    metas = [{"type": "quest"}, {"type": "wiki"}, {"type": "wiki"}]

    res = hybrid_rescore("next quest", docs, distances, metas, progression_boost=True, quest_boost=1.5)
    # The quest chunk should outrank at least one wiki chunk despite mid-pack
    # vector distance.
    top_doc = res[0][1]
    assert top_doc == "Bronze quest chunk"


def test_hybrid_rescore_empty_safe():
    assert hybrid_rescore("x", [], [], []) == []


def test_hybrid_rescore_vector_only_fallback(monkeypatch):
    """If rank_bm25 import fails, scoring degrades to vector-only."""
    real_import = builtins.__import__

    def boom(name, *args, **kwargs):
        if name == "rank_bm25":
            raise ImportError("simulated absence")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", boom)

    docs = ["bronze smelting", "steam boilers"]
    distances = [0.3, 0.5]  # doc 0 closer
    res = hybrid_rescore("anything", docs, distances)
    assert len(res) == 2
    # Vector-only: smallest distance wins.
    assert res[0][1] == "bronze smelting"
