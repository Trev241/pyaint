"""Headless tests for paged online image search (no network access)."""

import pytest

import pyaint.image_search as image_search


def _payload():
    return {
        "continue": {"gsroffset": 30, "continue": "-||"},
        "query": {
            "pages": {
                "1": {
                    "title": "File:Cat line art.png",
                    "imageinfo": [
                        {
                            "mime": "image/png",
                            "url": "https://example/full.png",
                            "thumburl": "https://example/thumb.png",
                            "descriptionurl": "https://commons.example/File:Cat",
                            "width": 800,
                            "height": 600,
                        }
                    ],
                },
                "2": {
                    "title": "File:Cat.svg",
                    "imageinfo": [
                        {"mime": "image/svg+xml", "url": "https://example/cat.svg"}
                    ],
                },
                "3": {
                    "title": "File:Cat photo.jpg",
                    "imageinfo": [
                        {
                            "mime": "image/jpeg",
                            "url": "https://example/full.jpg",
                            "width": 1024,
                            "height": 768,
                        }
                    ],
                },
            }
        },
    }


def _openverse_payload():
    return {
        "result_count": 3,
        "page_count": 3,
        "page_size": 30,
        "page": 1,
        "results": [
            {
                "title": "A cat",
                "url": "https://example/cat.jpg",
                "thumbnail": "https://example/cat-thumb.jpg",
                "filetype": "jpg",
                "width": 1024,
                "height": 768,
                "foreign_landing_url": "https://flickr.example/cat",
            },
            {
                "title": "Cat logo",
                "url": "https://example/cat.svg",
                "thumbnail": "https://example/cat.svg",
                "filetype": "svg",
            },
            {
                "title": "Cat png",
                "url": "https://example/cat.png",
                "thumbnail": None,
                "filetype": "png",
                "width": 200,
                "height": 200,
            },
        ],
    }


def test_search_page_maps_fields_and_filters_mime(monkeypatch):
    monkeypatch.setattr(image_search, "_fetch_json", lambda url, timeout=20: _payload())
    page = image_search.search_page("cat", provider="commons")
    assert [c.title for c in page.candidates] == [
        "File:Cat line art.png",
        "File:Cat photo.jpg",
    ]
    first = page.candidates[0]
    assert first.url == "https://example/full.png"
    assert first.thumb_url == "https://example/thumb.png"
    assert first.source_url == "https://commons.example/File:Cat"
    assert (first.width, first.height) == (800, 600)
    # A missing thumbnail falls back to the full URL.
    assert page.candidates[1].thumb_url == "https://example/full.jpg"
    assert page.next_continue == {"gsroffset": 30, "continue": "-||"}


def test_search_page_merges_continuation_token(monkeypatch):
    seen = {}

    def fake_fetch(url, timeout=20):
        seen["url"] = url
        return {"query": {"pages": {}}}

    monkeypatch.setattr(image_search, "_fetch_json", fake_fetch)
    page = image_search.search_page(
        "cat", provider="commons", cont={"gsroffset": 30, "continue": "-||"}
    )
    assert "gsroffset=30" in seen["url"]
    assert "continue=-%7C%7C" in seen["url"]  # url-encoded "-||"
    assert page.candidates == []
    assert page.next_continue is None


def test_search_page_query_has_no_drawing_bias(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        image_search,
        "_fetch_json",
        lambda url, timeout=20: seen.update(url=url) or {"query": {"pages": {}}},
    )
    image_search.search_page("cartoon cat", provider="commons")
    request = seen["url"]
    assert "cartoon+cat" in request
    assert "filetype%3Abitmap" in request
    for bias in ("line+art", "clipart", "coloring", "drawing"):
        assert bias not in request


def test_openverse_maps_fields_filters_svg_and_paginates(monkeypatch):
    monkeypatch.setattr(
        image_search, "_fetch_json", lambda url, timeout=20: _openverse_payload()
    )
    page = image_search.search_page("cat", provider="openverse")
    assert [c.title for c in page.candidates] == ["A cat", "Cat png"]
    first = page.candidates[0]
    assert first.url == "https://example/cat.jpg"
    assert first.thumb_url == "https://example/cat-thumb.jpg"
    assert first.mime == "image/jpeg"
    assert first.source_url == "https://flickr.example/cat"
    assert (first.width, first.height) == (1024, 768)
    # A missing thumbnail falls back to the full URL.
    assert page.candidates[1].thumb_url == "https://example/cat.png"
    assert page.next_continue == {"page": "2"}


def test_openverse_continuation_requests_next_page(monkeypatch):
    seen = {}

    def fake_fetch(url, timeout=20):
        seen["url"] = url
        return {"results": [], "page_count": 1, "page": 2}

    monkeypatch.setattr(image_search, "_fetch_json", fake_fetch)
    page = image_search.search_page("cat", provider="openverse", cont={"page": "2"})
    assert "page=2" in seen["url"]
    assert "page_size=20" in seen["url"]
    assert "q=cat" in seen["url"]
    assert page.candidates == []
    assert page.next_continue is None


def test_openverse_caps_anonymous_page_size(monkeypatch):
    """Openverse 401s above 20/page anonymously, so we must never ask for more."""
    seen = {}

    def fake_fetch(url, timeout=20):
        seen["url"] = url
        return {"results": [], "page_count": 1, "page": 1}

    monkeypatch.setattr(image_search, "_fetch_json", fake_fetch)
    image_search.search_page("cat", provider="openverse", limit=100)
    assert "page_size=20" in seen["url"]
    assert "page_size=100" not in seen["url"]


def test_default_provider_is_openverse():
    assert image_search.DEFAULT_PROVIDER == image_search.PROVIDER_OPENVERSE
    assert image_search.provider_name("openverse") == "Openverse"
    assert {p.id for p in image_search.PROVIDERS} == {"openverse", "commons"}


def test_search_page_dispatches_by_provider(monkeypatch):
    calls = []

    def fake_commons(query, **kwargs):
        calls.append("commons")
        return image_search.SearchPage([], None)

    def fake_openverse(query, **kwargs):
        calls.append("openverse")
        return image_search.SearchPage([], None)

    monkeypatch.setattr(image_search, "_search_commons", fake_commons)
    monkeypatch.setattr(image_search, "_search_openverse", fake_openverse)
    image_search.search_page("cat", provider="commons")
    image_search.search_page("cat", provider="openverse")
    assert calls == ["commons", "openverse"]


def test_search_page_rejects_unknown_provider():
    with pytest.raises(ValueError):
        image_search.search_page("cat", provider="nope")
