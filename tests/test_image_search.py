"""Headless tests for paged online image search (no network access)."""

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


def test_search_page_maps_fields_and_filters_mime(monkeypatch):
    monkeypatch.setattr(image_search, "_fetch_json", lambda url, timeout=20: _payload())
    page = image_search.search_page("cat")
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
    page = image_search.search_page("cat", cont={"gsroffset": 30, "continue": "-||"})
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
    image_search.search_page("cartoon cat")
    request = seen["url"]
    assert "cartoon+cat" in request
    assert "filetype%3Abitmap" in request
    for bias in ("line+art", "clipart", "coloring", "drawing"):
        assert bias not in request
