"""Scrape flat listing metadata with a persisted, refreshable DOM definition."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

DOM_DEFINITION_PATH = Path(__file__).with_name("dom_definition.json")


class _DOMStructureError(ValueError):
    """The saved selectors no longer describe the source page."""


def _read_dom_definition() -> dict[str, object]:
    try:
        definition = json.loads(DOM_DEFINITION_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise _DOMStructureError("No valid saved DOM definition") from error
    if not isinstance(definition, dict) or not definition.get("index") or not definition.get("detail"):
        raise _DOMStructureError("The saved DOM definition is incomplete")
    return definition


def _write_dom_definition(definition: dict[str, object]) -> None:
    DOM_DEFINITION_PATH.write_text(json.dumps(definition, indent=2) + "\n")


def _text(locator, selector: str) -> str:
    try:
        target = locator.locator(selector)
        count = target.count()
    except Exception as error:
        raise _DOMStructureError(f"Invalid text selector: {selector}") from error
    if not count:
        raise _DOMStructureError(f"Selector matched no text: {selector}")
    return " ".join(target.first.inner_text().split())


def _attribute(locator, selector: str, attribute: str) -> str:
    try:
        target = locator.locator(selector)
        count = target.count()
    except Exception as error:
        raise _DOMStructureError(f"Invalid attribute selector: {selector}") from error
    if not count:
        raise _DOMStructureError(f"Selector matched no attribute: {selector}")
    return target.first.get_attribute(attribute) or ""


def _scrape_with_definition(
    source_url: str,
    request_timeout_seconds: int,
    definition: dict[str, object],
) -> list[dict[str, object]]:
    from playwright.sync_api import sync_playwright

    index = definition["index"]
    detail = definition["detail"]
    timeout = request_timeout_seconds * 1000
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            index_page = browser.new_page()
            index_page.goto(source_url, wait_until="domcontentloaded", timeout=timeout)
            listings = index_page.locator(index["listing_selector"])
            if not listings.count():
                raise _DOMStructureError("The listing selector matched no elements")

            detail_page = browser.new_page()
            flats = []
            for number in range(listings.count()):
                listing = listings.nth(number)
                relative_url = _attribute(listing, index["url_selector"], "href")
                if not relative_url:
                    raise _DOMStructureError("A listing has no detail URL")
                detail_url = urljoin(source_url, relative_url)
                detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=timeout)
                facts_raw = _attribute(detail_page, detail["facts_selector"], detail["facts_attribute"])
                address_value = _text(detail_page, detail["address_selector"])
                if not facts_raw or " · " not in address_value:
                    raise _DOMStructureError(f"Listing {relative_url} has missing detail metadata")
                try:
                    facts = json.loads(facts_raw)
                except json.JSONDecodeError as error:
                    raise _DOMStructureError(f"Listing {relative_url} has invalid facts") from error
                if not isinstance(facts, dict):
                    raise _DOMStructureError(f"Listing {relative_url} has non-object facts")
                rooms, address = address_value.split(" · ", 1)
                required = {"id", "name", "price", "livingSpace", "latitude", "longitude"}
                if not required <= facts.keys():
                    raise _DOMStructureError(f"Listing {relative_url} has incomplete facts")
                flats.append(
                    {
                        "id": str(facts["id"]),
                        "slug": parse_qs(urlparse(detail_url).query).get("slug", [""])[0],
                        "name": str(facts["name"]),
                        "price": str(facts["price"]),
                        "livingSpace": str(facts["livingSpace"]),
                        "rooms": rooms,
                        "address": address,
                        "latitude": float(facts["latitude"]),
                        "longitude": float(facts["longitude"]),
                    }
                )
            return flats
        finally:
            browser.close()


def _generate_dom_definition(index_html: str, detail_html: str) -> dict[str, object]:
    from openai import OpenAI

    prompt = """
Inspect the index and detail HTML and return JSON only in this exact shape:
{
    "index": {"listing_selector": "...", "url_selector": "..."},
  "detail": {"facts_selector": "...", "facts_attribute": "...", "address_selector": "..."}
}
Use CSS selectors. The listing selector must identify each repeated listing. The facts attribute
contains one JSON object with id, name, price, livingSpace, latitude, and longitude. Do not explain.

INDEX HTML:
"""
    response = OpenAI(
        api_key=os.environ["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    ).chat.completions.create(
        model=os.getenv("SHELOBA_LLM_MODEL", "gemini-3.6-flash"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Return valid JSON matching the requested schema."},
            {"role": "user", "content": prompt + index_html + "\n\nDETAIL HTML:\n" + detail_html},
        ],
    )
    try:
        definition = json.loads(response.choices[0].message.content or "{}")
        if not isinstance(definition, dict) or not definition.get("index") or not definition.get("detail"):
            raise ValueError
        return definition
    except (json.JSONDecodeError, ValueError) as error:
        raise _DOMStructureError("The LLM returned an invalid DOM definition") from error


def _refresh_dom_definition(
    source_url: str,
    request_timeout_seconds: int,
) -> dict[str, object]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(source_url, wait_until="domcontentloaded", timeout=request_timeout_seconds * 1000)
            links = page.locator("a[href]")
            href = next(
                (
                    links.nth(index).get_attribute("href")
                    for index in range(links.count())
                    if links.nth(index).get_attribute("href")
                    and "flat" in links.nth(index).get_attribute("href").lower()
                ),
                None,
            )
            if not href:
                raise _DOMStructureError("The browser found no detail link")
            detail_page = browser.new_page()
            detail_page.goto(urljoin(source_url, href), wait_until="domcontentloaded", timeout=request_timeout_seconds * 1000)
            return _generate_dom_definition(page.locator("body").inner_html(), detail_page.locator("body").inner_html())
        finally:
            browser.close()


def scrape_flats(
    source_url: str,
    request_timeout_seconds: int,
) -> list[dict[str, object]]:
    """Run static scraping and refresh the saved selectors only when they fail."""
    try:
        definition = _read_dom_definition()
        return _scrape_with_definition(source_url, request_timeout_seconds, definition)
    except _DOMStructureError:
        for attempt in range(2):
            definition = _refresh_dom_definition(source_url, request_timeout_seconds)
            try:
                flats = _scrape_with_definition(source_url, request_timeout_seconds, definition)
                _write_dom_definition(definition)
                return flats
            except _DOMStructureError:
                if attempt == 1:
                    raise
        raise RuntimeError("DOM definition refresh did not complete")
