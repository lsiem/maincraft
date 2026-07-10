"""Tests for the GTNH wiki fetcher (no network — uses mocks and fixtures)."""

from __future__ import annotations

from pathlib import Path

from ingestion import gtnh_wiki as gw

FIXTURES = Path(__file__).parent / "fixtures"
EXPORT_XML = FIXTURES / "gtnh_wiki_export.xml"


class _FakeResp:
    def __init__(self, payload: dict, text: str = "json"):
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        return self._payload


def test_is_bot_challenge():
    assert gw._is_bot_challenge("Checking your connection before proceeding")
    assert gw._is_bot_challenge("We detected unusual activity from your IP")
    assert not gw._is_bot_challenge("Normal page content")


def test_wikitext_to_plain():
    assert gw._wikitext_to_plain("'''bold'''") == "**bold**"
    assert gw._wikitext_to_plain("''italic''") == "*italic*"
    assert gw._wikitext_to_plain("[[Main Page|Home]]") == "Home"
    assert gw._wikitext_to_plain("[[Main Page]]") == "Main Page"
    assert gw._wikitext_to_plain("before {{stub}} after") == "before  after"
    assert gw._wikitext_to_plain("= Heading =") == "# Heading"
    assert gw._wikitext_to_plain("text <ref>cite</ref> end") == "text  end"


def test_parse_export_xml():
    chunks = gw._parse_export_xml(EXPORT_XML)
    titles = [c.title for c in chunks]
    assert "Test Page" in titles
    assert "Another Page" in titles

    test_page = next(c for c in chunks if c.title == "Test Page")
    # wikitext markup converted
    assert "**Hello**" in test_page.body
    assert "Home" in test_page.body  # [[Main Page|Home]] -> Home
    assert "{{stub}}" not in test_page.body  # template removed
    assert "stub" not in test_page.body
    # metadata
    assert test_page.metadata["pack"] == "gtnh"
    assert test_page.metadata["type"] == "wiki"


def test_api_list_allpages_paginates(monkeypatch):
    pages1 = {
        "query": {"allpages": [{"title": "A"}, {"title": "B"}]},
        "continue": {"apcontinue": "C", "continue": "-||"},
    }
    pages2 = {"query": {"allpages": [{"title": "C"}, {"title": "D"}]}}

    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params.get("apcontinue"))
        return _FakeResp(pages1 if not params.get("apcontinue") else pages2)

    monkeypatch.setattr(gw.requests, "get", fake_get)
    monkeypatch.setattr(gw.time, "sleep", lambda _s: None)

    titles = gw._api_list_allpages()
    assert titles == ["A", "B", "C", "D"]
    # Continue token was threaded into the second request.
    assert calls == [None, "C"]


def test_api_list_allpages_max_pages_cap(monkeypatch):
    pages1 = {
        "query": {"allpages": [{"title": "A"}, {"title": "B"}, {"title": "C"}, {"title": "D"}]},
        "continue": {"apcontinue": "E", "continue": "-||"},
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResp(pages1)

    monkeypatch.setattr(gw.requests, "get", fake_get)
    monkeypatch.setattr(gw.time, "sleep", lambda _s: None)

    titles = gw._api_list_allpages(max_pages=3)
    assert titles == ["A", "B", "C"]


def test_api_list_allpages_stops_on_bot_challenge(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResp({}, text="Checking your connection")

    monkeypatch.setattr(gw.requests, "get", fake_get)
    titles = gw._api_list_allpages()
    assert titles == []
