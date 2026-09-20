#!/usr/bin/env python3
"""Serve the Dummy Flats site without exposing listing metadata as a public file."""

from __future__ import annotations

import json
import os
from html import escape
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "flats.json"
HOST = os.environ.get("SHELOBA_HOST", "127.0.0.1")
PORT = 8765
BLOCKED_PREFIXES = ("/data", "/server.py")
BLOCKED_NAMES = {"flats.js", "flats.json", "listing.js"}

FLATS = json.loads(DATA_FILE.read_text(encoding="utf-8"))
INDEX_TEMPLATE = (ROOT / "index.html").read_text(encoding="utf-8")
FLAT_TEMPLATE = (ROOT / "flat.html").read_text(encoding="utf-8")


def get_flat(slug: str | None) -> dict | None:
    if not slug:
        return None
    return next((flat for flat in FLATS if flat["slug"] == slug), None)


def listing_cards() -> str:
    cards = []
    for flat in FLATS:
        slug = escape(flat["slug"], quote=True)
        name = escape(flat["name"])
        price = escape(flat["price"])
        space = escape(flat["livingSpace"])
        image = escape(flat["image"], quote=True)
        cards.append(
            (
                f'<article class="property-tile">'
                f'<div class="photo" style="background-image: url(&quot;{image}&quot;)"></div>'
                f'<div class="body">'
                f'<span class="eyebrow">Listing</span>'
                f'<a class="property-link" href="./flat.html?slug={slug}">{name}</a>'
                f'<p>{price} · {space}</p>'
                f"</div></article>"
            )
        )
    return "".join(cards)


def render_index() -> bytes:
    html = INDEX_TEMPLATE.replace("{{LISTINGS}}", listing_cards())
    return html.encode("utf-8")


def render_flat(flat: dict) -> bytes:
    replacements = {
        "{{NAME}}": escape(flat["name"]),
        "{{IMAGE}}": escape(flat["image"], quote=True),
        "{{PRICE}}": escape(flat["price"], quote=True),
        "{{LIVING_SPACE}}": escape(flat["livingSpace"], quote=True),
        "{{ID}}": escape(flat["id"], quote=True),
        "{{ROOMS}}": escape(flat["rooms"]),
        "{{ADDRESS}}": escape(flat["address"]),
        "{{LATITUDE}}": escape(str(flat["latitude"])),
        "{{LONGITUDE}}": escape(str(flat["longitude"])),
    }
    html = FLAT_TEMPLATE
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html.encode("utf-8")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _denied_file(self, full: Path) -> bool:
        try:
            relative = full.resolve().relative_to(ROOT)
        except ValueError:
            return True
        parts = {part.lower() for part in relative.parts}
        if "data" in parts or relative.name.lower() in BLOCKED_NAMES:
            return True
        return relative.name.lower() == "server.py"

    def translate_path(self, path):
        full = Path(super().translate_path(path))
        if self._denied_file(full):
            return str(ROOT / "__not_found__")
        return str(full)

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if self._denied_file(Path(self.translate_path(path))) or any(
            path.lower().startswith(prefix) for prefix in BLOCKED_PREFIXES
        ):
            self.send_error(404, "Not found")
            return

        if path in ("/", "/index.html"):
            body = render_index()
            self._send_html(body)
            return

        if path in ("/flat.html", "/flat"):
            slug = parse_qs(parsed.query).get("slug", [None])[0]
            flat = get_flat(slug)
            if flat is None:
                self.send_error(404, "Flat not found")
                return
            self._send_html(render_flat(flat))
            return

        super().do_GET()

    def _send_html(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving Dummy Flats on http://{HOST}:{PORT}/")
    server.serve_forever()
