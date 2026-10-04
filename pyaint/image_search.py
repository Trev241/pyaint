"""Keyless image search for the Image field.

When the Image field holds neither a URL nor an existing path, Pyaint treats it
as a search query. We query Wikimedia Commons (no API key, permissively
licensed) for raster images and page through the results for a gallery.

There is deliberately **no drawing/photo bias**: results come back in the
search engine's relevance order and the user picks. The only filter is
``filetype:bitmap``, which keeps out formats PIL cannot open (SVG, PDF, ...).

All network access goes through :func:`fetch_bytes` / ``_fetch_json`` so tests
can stub it.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Pyaint/1.0 (desktop drawing assistant; image search; Python-urllib)"
#: Commons MIME types PIL can open; everything else is filtered out.
ACCEPTED_MIME = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})
DEFAULT_PAGE_SIZE = 30
DEFAULT_THUMB_WIDTH = 240
_MAX_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class ImageCandidate:
    """One search hit: where to get it, at what size, and where it came from."""

    url: str  # full/original image, used when the user commits
    thumb_url: str  # small preview for the gallery grid
    mime: str
    title: str
    source_url: str
    width: int
    height: int


@dataclass
class SearchPage:
    """A page of results plus the token needed to fetch the next page."""

    candidates: List[ImageCandidate]
    next_continue: Optional[Dict[str, str]]


def _urlopen(url: str, timeout: int = 20):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def _fetch_json(url: str, timeout: int = 20) -> dict:
    with _urlopen(url, timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    """Download ``url`` (capped at ~20 MB); used for thumbnails and commits."""
    with _urlopen(url, timeout) as response:
        return response.read(_MAX_BYTES)


def search_page(
    query: str,
    *,
    cont: Optional[Dict[str, str]] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    thumb_width: int = DEFAULT_THUMB_WIDTH,
) -> SearchPage:
    """Return one page of Commons results for ``query``.

    ``cont`` is the ``next_continue`` value from the previous page (``None`` for
    the first page). It is merged into the request verbatim, so the MediaWiki
    continuation mechanism works without us modelling its keys.
    """
    params: Dict[str, str] = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6",  # File: namespace
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": str(thumb_width),
    }
    if cont:
        params.update(cont)
    data = _fetch_json(f"{COMMONS_API}?{urllib.parse.urlencode(params)}")

    pages = (data.get("query") or {}).get("pages") or {}
    candidates: List[ImageCandidate] = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = str(info.get("mime") or "").lower()
        url = info.get("url")
        if not url or mime not in ACCEPTED_MIME:
            continue
        candidates.append(
            ImageCandidate(
                url=url,
                thumb_url=info.get("thumburl") or url,
                mime=mime,
                title=page.get("title", ""),
                source_url=info.get("descriptionurl") or url,
                width=int(info.get("width") or 0),
                height=int(info.get("height") or 0),
            )
        )
    return SearchPage(candidates=candidates, next_continue=data.get("continue"))
