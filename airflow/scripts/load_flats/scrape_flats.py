"""Scrape flat listing metadata from the Sheloba website."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen


class _ListingIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.listings: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._text: list[str] = []
        self._element: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and "listing-card" in attributes.get("class", "").split():
            self._current = {"url": attributes.get("href", "")}
        if self._current is not None and tag in {"h2", "p"}:
            self._element = tag
            self._text = []
        if self._current is not None and "photo" in attributes.get("class", "").split():
            style = attributes.get("style", "")
            self._current["image"] = style.split('url("', 1)[-1].rsplit('")', 1)[0]

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._element is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == self._element:
            value = " ".join("".join(self._text).split())
            if tag == "h2":
                self._current["name"] = value
            elif tag == "p":
                self._current["summary"] = value
            self._element = None
            self._text = []
        elif tag == "a":
            self.listings.append(self._current)
            self._current = None


class _DetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attributes: dict[str, str] = {}
        self.address = ""
        self._reading_address = False
        self._address_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id") == "flat-facts":
            self.attributes = {
                key.removeprefix("data-"): value or ""
                for key, value in attributes.items()
                if key.startswith("data-")
            }
        if attributes.get("id") == "address":
            self._reading_address = True

    def handle_data(self, data: str) -> None:
        if self._reading_address:
            self._address_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._reading_address:
            self.address = " ".join("".join(self._address_parts).split())
            self._reading_address = False


def _fetch_html(url: str, user_agent: str, request_timeout_seconds: int) -> str:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=request_timeout_seconds) as response:
        return response.read().decode("utf-8")


def scrape_flats(
    source_url: str,
    user_agent: str,
    request_timeout_seconds: int,
) -> list[dict[str, object]]:
    """Return flat metadata scraped from the listing index and detail pages."""
    index_parser = _ListingIndexParser()
    index_parser.feed(_fetch_html(source_url, user_agent, request_timeout_seconds))

    flats = []
    for listing in index_parser.listings:
        detail_url = urljoin(source_url, listing["url"])
        detail_parser = _DetailParser()
        detail_parser.feed(_fetch_html(detail_url, user_agent, request_timeout_seconds))
        attributes = detail_parser.attributes
        required = {"id", "name", "price", "living-space", "latitude", "longitude"}
        missing = required - attributes.keys()
        if missing:
            raise ValueError(f"Listing {listing['url']} is missing metadata: {sorted(missing)}")

        rooms, separator, address = detail_parser.address.partition(" · ")
        if not separator:
            raise ValueError(f"Listing {listing['url']} has no room and address metadata")
        flats.append(
            {
                "id": attributes["id"],
                "slug": parse_qs(urlparse(detail_url).query).get("slug", [""])[0],
                "name": attributes["name"],
                "price": attributes["price"],
                "livingSpace": attributes["living-space"],
                "rooms": rooms,
                "address": address,
                "latitude": float(attributes["latitude"]),
                "longitude": float(attributes["longitude"]),
                "image": listing.get("image", ""),
            }
        )

    return flats