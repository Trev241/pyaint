"""Keyless image search for the Image field.

When the Image field holds neither a URL nor an existing path, Pyaint treats it
as a search query and pages through an online image source for a gallery. Two
keyless providers are supported:

* **Openverse** (``api.openverse.org``) aggregates CC-licensed images from
  Flickr, museums, and more, so it has the broadest coverage. It is the default.
* **Wikimedia Commons** is encyclopedic: excellent for diagrams and notable
  subjects, thin for general stock.

There is deliberately **no drawing/photo bias**: results come back in the
search engine's relevance order and the user picks. The only filter is on the
file format, which keeps out what PIL cannot open (SVG, PDF, ...).

All network access goes through :func:`fetch_bytes` / ``_fetch_json`` so tests
can stub it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
USER_AGENT = "Pyaint/1.0 (desktop drawing assistant; image search; Python-urllib)"
#: Commons MIME types PIL can open; everything else is filtered out.
ACCEPTED_MIME = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})
#: Openverse filetypes PIL can open (``svg`` is deliberately excluded).
OPENVERSE_RASTER = frozenset({"jpg", "jpeg", "png", "gif", "webp", "bmp"})
DEFAULT_PAGE_SIZE = 30
DEFAULT_THUMB_WIDTH = 240
#: Openverse rejects anonymous requests above this page size with HTTP 401
#: ("page_size may not exceed 20 for anonymous requests").
OPENVERSE_ANONYMOUS_PAGE_SIZE = 20
_MAX_BYTES = 20 * 1024 * 1024

PROVIDER_OPENVERSE = "openverse"
PROVIDER_COMMONS = "commons"
DEFAULT_PROVIDER = PROVIDER_OPENVERSE


@dataclass(frozen=True)
class Provider:
    """One selectable online image source."""

    id: str
    name: str
    description: str


PROVIDERS: tuple = (
    Provider(PROVIDER_OPENVERSE, "Openverse", "Broad — CC-licensed photos, art and more"),
    Provider(PROVIDER_COMMONS, "Wikimedia Commons", "Encyclopedic — great for diagrams"),
)
PROVIDER_IDS = frozenset(provider.id for provider in PROVIDERS)


def provider_name(provider_id: str) -> str:
    """Human-readable name for a provider id (falls back to the id itself)."""
    for provider in PROVIDERS:
        if provider.id == provider_id:
            return provider.name
    return provider_id


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
    try:
        with _urlopen(url, timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Surface the API's own explanation (e.g. Openverse's page-size cap)
        # instead of a bare "HTTP Error 401: Unauthorized".
        try:
            detail = exc.read().decode("utf-8", "ignore").strip()
        except Exception:  # noqa: BLE001 - body may be unreadable
            detail = ""
        message = f"HTTP {exc.code} {exc.reason}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    """Download ``url`` (capped at ~20 MB); used for thumbnails and commits."""
    with _urlopen(url, timeout) as response:
        return response.read(_MAX_BYTES)


def _mime_for_filetype(filetype: str) -> str:
    return "image/jpeg" if filetype == "jpg" else f"image/{filetype}"


def _filetype_from_url(url: Optional[str]) -> str:
    if not url:
        return ""
    path = urllib.parse.urlparse(url).path
    _, _, extension = path.rpartition(".")
    return extension.lower() if extension else ""


def _search_commons(
    query: str,
    *,
    cont: Optional[Dict[str, str]] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    thumb_width: int = DEFAULT_THUMB_WIDTH,
) -> SearchPage:
    """One page of Wikimedia Commons results for ``query``.

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


def _search_openverse(
    query: str,
    *,
    cont: Optional[Dict[str, str]] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    thumb_width: int = DEFAULT_THUMB_WIDTH,
) -> SearchPage:
    """One page of Openverse results for ``query``.

    Openverse paginates with a page number rather than a continuation token, so
    ``cont`` carries ``{"page": "<n>"}``. Its own ``thumbnail`` proxy is used
    for the gallery; ``url`` is the original file.
    """
    page = 1
    if cont:
        try:
            page = max(1, int(cont.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
    # Anonymous Openverse requests are capped at 20 results per page; asking
    # for more is a hard 401, not a silent trim.
    page_size = max(1, min(int(limit), OPENVERSE_ANONYMOUS_PAGE_SIZE))
    params: Dict[str, str] = {
        "q": query,
        "page": str(page),
        "page_size": str(page_size),
    }
    data = _fetch_json(f"{OPENVERSE_API}?{urllib.parse.urlencode(params)}")

    candidates: List[ImageCandidate] = []
    for item in data.get("results") or []:
        url = item.get("url")
        if not url:
            continue
        filetype = str(item.get("filetype") or "").lower() or _filetype_from_url(url)
        if filetype not in OPENVERSE_RASTER:
            continue
        candidates.append(
            ImageCandidate(
                url=url,
                thumb_url=item.get("thumbnail") or url,
                mime=_mime_for_filetype(filetype),
                title=item.get("title") or "",
                source_url=item.get("foreign_landing_url") or url,
                width=int(item.get("width") or 0),
                height=int(item.get("height") or 0),
            )
        )

    next_continue: Optional[Dict[str, str]] = None
    try:
        page_count = int(data.get("page_count") or 0)
    except (TypeError, ValueError):
        page_count = 0
    if page_count and page < page_count:
        next_continue = {"page": str(page + 1)}
    return SearchPage(candidates=candidates, next_continue=next_continue)


def search_page(
    query: str,
    *,
    provider: str = DEFAULT_PROVIDER,
    cont: Optional[Dict[str, str]] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    thumb_width: int = DEFAULT_THUMB_WIDTH,
) -> SearchPage:
    """Return one page of results from ``provider`` for ``query``."""
    # Resolve through the module namespace so tests can monkeypatch a provider.
    searcher = {
        PROVIDER_COMMONS: _search_commons,
        PROVIDER_OPENVERSE: _search_openverse,
    }.get(provider)
    if searcher is None:
        raise ValueError(f"Unknown image source: {provider!r}")
    return searcher(query, cont=cont, limit=limit, thumb_width=thumb_width)
