#!/usr/bin/env python3
"""Capture a browser-rendered product page as structured JSON for product intake."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"


class StaticPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.headings: list[dict[str, str]] = []
        self.buttons: list[str] = []
        self.json_ld: list[Any] = []
        self._tag_stack: list[str] = []
        self._title_parts: list[str] = []
        self._heading_tag = ""
        self._heading_parts: list[str] = []
        self._button_parts: list[str] = []
        self._script_type = ""
        self._script_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        self._tag_stack.append(tag)
        if tag == "meta":
            key = attrs_map.get("property") or attrs_map.get("name")
            content = attrs_map.get("content")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)
        elif tag == "link":
            self.links.append(attrs_map)
        elif tag == "img":
            src = attrs_map.get("src") or attrs_map.get("data-src")
            if src:
                self.images.append({"url": src, "alt": attrs_map.get("alt", "")})
        elif tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_parts = []
        elif tag in {"button", "a"}:
            self._button_parts = []
        elif tag == "script":
            self._script_type = attrs_map.get("type", "").lower()
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.title = normalize_space(" ".join(self._title_parts))
            self._title_parts = []
        elif tag == self._heading_tag and self._heading_parts:
            text = normalize_space(" ".join(self._heading_parts))
            if text:
                self.headings.append({"level": self._heading_tag, "text": text})
            self._heading_tag = ""
            self._heading_parts = []
        elif tag in {"button", "a"} and self._button_parts:
            text = normalize_space(" ".join(self._button_parts))
            if looks_like_cta(text):
                self.buttons.append(text)
            self._button_parts = []
        elif tag == "script":
            if self._script_type == "application/ld+json" and self._script_parts:
                self.json_ld.extend(parse_json_ld("".join(self._script_parts)))
            self._script_type = ""
            self._script_parts = []
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        current = self._tag_stack[-1] if self._tag_stack else ""
        if current == "title":
            self._title_parts.append(text)
        elif self._heading_tag:
            self._heading_parts.append(text)
        elif current in {"button", "a"}:
            self._button_parts.append(text)
        elif self._script_type == "application/ld+json":
            self._script_parts.append(data)
        elif current not in {"script", "style", "noscript"}:
            self._text_parts.append(text)

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self._text_parts))


def main() -> None:
    args = parse_args()
    snapshot = capture_snapshot(args)
    out_file = Path(args.out_file) if args.out_file else Path(args.out_dir) / "browser-snapshot/product-page-snapshot.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Browser snapshot written to: {out_file.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a rendered product page snapshot for product_intake.py.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public product URL to open in a browser.")
    source.add_argument("--html-file", help="Saved HTML file to normalize without launching a browser.")
    parser.add_argument("--base-url", default="", help="Canonical/source URL to use with --html-file.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--out-file", default="")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--screenshot", action="store_true", help="Save a screenshot next to the snapshot when using --url.")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Run the official Playwright browser install command if Chromium is missing.")
    return parser.parse_args()


def capture_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    if args.html_file:
        html_path = Path(args.html_file)
        html = html_path.read_text(encoding="utf-8")
        return snapshot_from_html(html, args.base_url or str(html_path), "html_file")
    return snapshot_from_browser(args)


def snapshot_from_browser(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 - CLI reports missing optional dependency.
        raise SystemExit(f"Playwright is not installed for this Python environment: {exc}") from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1200})
            response, navigation = navigate_with_fallback(page, args, PlaywrightTimeoutError)
            try:
                page.wait_for_load_state("networkidle", timeout=min(args.timeout_ms, 10000))
            except PlaywrightTimeoutError:
                pass
            snapshot = page.evaluate(SNAPSHOT_SCRIPT)
            snapshot["source"] = args.url
            snapshot["httpStatus"] = response.status if response else None
            snapshot["snapshotType"] = "browser_rendered"
            snapshot["captureMode"] = "playwright_chromium"
            snapshot["navigation"] = navigation
            if args.screenshot:
                screenshot_path = Path(args.out_dir) / "browser-snapshot/product-page.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True)
                snapshot["screenshot"] = str(screenshot_path)
            browser.close()
            return enrich_snapshot(snapshot)
    except PlaywrightError as exc:
        message = str(exc)
        if "Executable doesn't exist" in message and args.install_browser_if_missing:
            install_chromium()
            return snapshot_from_browser(without_install_retry(args))
        if "Executable doesn't exist" in message:
            raise SystemExit("Playwright Chromium is missing. Run: python -m playwright install chromium") from exc
        raise SystemExit(f"Browser snapshot failed: {message}") from exc


def navigate_with_fallback(page: Any, args: argparse.Namespace, timeout_error: type[Exception]) -> tuple[Any, dict[str, Any]]:
    navigation = {
        "requestedWaitUntil": args.wait_until,
        "usedWaitUntil": args.wait_until,
        "fallbackUsed": False,
        "timeoutMessage": "",
    }
    try:
        return page.goto(args.url, wait_until=args.wait_until, timeout=args.timeout_ms), navigation
    except timeout_error as exc:
        if args.wait_until != "networkidle":
            raise
        navigation["fallbackUsed"] = True
        navigation["timeoutMessage"] = str(exc)
        navigation["usedWaitUntil"] = "domcontentloaded"
        try:
            return page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout_ms), navigation
        except timeout_error as retry_exc:
            navigation["usedWaitUntil"] = "current_dom_after_timeout"
            navigation["fallbackError"] = str(retry_exc)
            return None, navigation


def without_install_retry(args: argparse.Namespace) -> argparse.Namespace:
    args.install_browser_if_missing = False
    return args


def install_chromium() -> None:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


SNAPSHOT_SCRIPT = r"""
() => {
  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const meta = {};
  document.querySelectorAll('meta').forEach((node) => {
    const key = node.getAttribute('property') || node.getAttribute('name');
    const content = node.getAttribute('content');
    if (key && content) meta[key.toLowerCase()] = clean(content);
  });
  const canonical = document.querySelector('link[rel~="canonical"]')?.href || location.href;
  const headings = Array.from(document.querySelectorAll('h1,h2,h3')).slice(0, 30).map((node) => ({
    level: node.tagName.toLowerCase(),
    text: clean(node.innerText)
  })).filter((item) => item.text);
  const images = Array.from(document.images).slice(0, 40).map((node) => ({
    url: node.currentSrc || node.src || '',
    alt: clean(node.alt || '')
  })).filter((item) => item.url);
  const links = Array.from(document.querySelectorAll('a[href]')).slice(0, 120).map((node) => ({
    url: node.href,
    text: clean(node.innerText || node.getAttribute('aria-label') || '')
  })).filter((item) => item.url);
  const ctaCandidates = Array.from(document.querySelectorAll('a,button,[role="button"]')).map((node) => (
    clean(node.innerText || node.getAttribute('aria-label') || node.getAttribute('title') || '')
  )).filter((text) => /try|start|get|buy|download|sign|contact|book|demo|join|launch|pricing|subscribe|开始|免费|购买|下载|联系|预约|体验|登录|注册|试用/.test(text.toLowerCase())).slice(0, 30);
  const jsonLd = Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map((node) => node.textContent || '').filter(Boolean);
  return {
    url: location.href,
    canonicalUrl: canonical,
    title: clean(document.title),
    description: meta['description'] || meta['og:description'] || meta['twitter:description'] || '',
    meta,
    lang: document.documentElement.lang || '',
    headings,
    images,
    links,
    ctaCandidates,
    jsonLdRaw: jsonLd,
    text: clean(document.body ? document.body.innerText : '')
  };
}
"""


def snapshot_from_html(html: str, source: str, capture_mode: str) -> dict[str, Any]:
    parser = StaticPageParser()
    parser.feed(html)
    snapshot = {
        "source": source,
        "url": source,
        "canonicalUrl": canonical_url(parser.links) or source,
        "title": first_non_empty(parser.meta.get("og:title"), parser.meta.get("twitter:title"), parser.title),
        "description": first_non_empty(parser.meta.get("description"), parser.meta.get("og:description"), parser.meta.get("twitter:description")),
        "meta": parser.meta,
        "headings": parser.headings[:30],
        "images": parser.images[:40],
        "links": [{"url": link.get("href", ""), "text": ""} for link in parser.links[:120] if link.get("href")],
        "ctaCandidates": dedupe(parser.buttons)[:30],
        "jsonLd": parser.json_ld,
        "text": parser.text,
        "snapshotType": "browser_rendered",
        "captureMode": capture_mode,
    }
    return enrich_snapshot(snapshot)


def enrich_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    json_ld = snapshot.get("jsonLd") or []
    if not json_ld and snapshot.get("jsonLdRaw"):
        json_ld = []
        for raw in snapshot.get("jsonLdRaw", []):
            json_ld.extend(parse_json_ld(str(raw)))
        snapshot["jsonLd"] = json_ld
    title = str(snapshot.get("title") or "")
    description = str(snapshot.get("description") or "")
    text = str(snapshot.get("text") or "")
    snapshot["productName"] = first_non_empty(value_from_json_ld(json_ld, "name"), first_heading(snapshot), title)
    snapshot["pricing"] = first_non_empty(value_from_json_ld(json_ld, "offers.price"), value_from_json_ld(json_ld, "price"), extract_price(" ".join([title, description, text])))
    snapshot["valueProposition"] = first_non_empty(description, first_paragraph(text))
    snapshot["priceCandidates"] = dedupe(re.findall(r"(?:[$€£¥]\s?\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s?(?:USD|EUR|CNY|RMB|元|美元))", text, flags=re.IGNORECASE))[:20]
    snapshot["jsonLdTypes"] = sorted({str(item.get("@type")) for item in json_ld if isinstance(item, dict) and item.get("@type")})
    snapshot["evidence"] = {
        "observedHeadings": [item.get("text", "") for item in snapshot.get("headings", [])[:8]],
        "observedCtas": snapshot.get("ctaCandidates", [])[:8],
        "observedPrices": snapshot["priceCandidates"][:8],
    }
    snapshot["guardrails"] = [
        "Browser-visible content only.",
        "No cookies, passwords, hidden tokens, private endpoints, captcha bypass, or automatic login.",
        "Verify product claims and pricing before publishing.",
    ]
    return snapshot


def parse_json_ld(raw: str) -> list[Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        graph = parsed.get("@graph")
        if isinstance(graph, list):
            return [parsed, *graph]
        return [parsed]
    return []


def value_from_json_ld(items: list[Any], dotted_key: str) -> str:
    parts = dotted_key.split(".")
    for item in items:
        value: Any = item
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if isinstance(value, list):
            value = value[0] if value else ""
        if value not in (None, ""):
            return normalize_space(str(value))
    return ""


def canonical_url(links: list[dict[str, str]]) -> str:
    for link in links:
        if "canonical" in link.get("rel", "").lower() and link.get("href"):
            return link["href"]
    return ""


def first_heading(snapshot: dict[str, Any]) -> str:
    for item in snapshot.get("headings", []):
        if item.get("level") == "h1" and item.get("text"):
            return str(item["text"])
    return ""


def first_paragraph(text: str) -> str:
    for chunk in re.split(r"\n+", text):
        chunk = normalize_space(chunk)
        if len(chunk) > 30:
            return chunk[:400]
    return normalize_space(text)[:400]


def extract_price(text: str) -> str:
    match = re.search(r"(?:[$€£¥]\s?\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s?(?:USD|EUR|CNY|RMB|元|美元))", text, flags=re.IGNORECASE)
    return normalize_space(match.group(0)) if match else ""


def looks_like_cta(text: str) -> bool:
    return bool(re.search(r"try|start|get|buy|download|sign|contact|book|demo|join|launch|pricing|subscribe|开始|免费|购买|下载|联系|预约|体验|登录|注册|试用", text, re.IGNORECASE))


def first_non_empty(*values: str | None) -> str:
    for value in values:
        normalized = normalize_space(value or "")
        if normalized:
            return normalized
    return ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def dedupe(values: list[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        normalized = normalize_space(str(value))
        key = normalized.lower()
        if normalized and key not in seen:
            output.append(normalized)
            seen.add(key)
    return output


if __name__ == "__main__":
    main()
