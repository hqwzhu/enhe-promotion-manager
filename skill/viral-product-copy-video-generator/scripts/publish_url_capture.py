#!/usr/bin/env python3
"""Capture a browser-visible post-publish page and register its URL."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import metrics_intake
import published_items


TODAY = date.today().isoformat()
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"


class PublishedHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.headings: list[str] = []
        self.text_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._title_parts: list[str] = []
        self._heading_tag = ""
        self._heading_parts: list[str] = []

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
        elif tag in {"h1", "h2"}:
            self._heading_tag = tag
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.title = normalize_space(" ".join(self._title_parts))
            self._title_parts = []
        elif tag == self._heading_tag and self._heading_parts:
            text = normalize_space(" ".join(self._heading_parts))
            if text:
                self.headings.append(text)
            self._heading_tag = ""
            self._heading_parts = []
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
        elif current not in {"script", "style", "noscript"}:
            self.text_parts.append(text)

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


def main() -> None:
    args = parse_args()
    capture = load_capture(args)
    report = build_capture_report(args, capture)
    write_capture_report(Path(args.out_dir), report)
    if report["status"] == "ready":
        update_published_items(Path(args.out_dir), report["record"])
    print(f"Publish URL capture written to: {(capture_dir(Path(args.out_dir)) / 'publish-url-capture.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a real published URL from browser-visible evidence and register it for metrics recovery.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--structured-json", help="Browser/Codex structured snapshot after publishing.")
    source.add_argument("--html-file", help="Saved published page HTML.")
    source.add_argument("--text-file", help="Copied post-publish URL/title text.")
    source.add_argument("--url", help="Public published URL to fetch as static HTML when accessible.")
    parser.add_argument("--base-url", default="", help="Base/current URL for --html-file.")
    parser.add_argument("--platform", default="", help="Override detected platform.")
    parser.add_argument("--title", default="", help="Override detected title.")
    parser.add_argument("--content-id", default="", help="Override detected platform content id.")
    parser.add_argument("--published-at", default="", help="Override published date.")
    parser.add_argument("--evidence", action="append", default=[], help="Evidence URL, screenshot path, or export path.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_capture(args: argparse.Namespace) -> dict[str, Any]:
    if args.structured_json:
        path = Path(args.structured_json)
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return capture_from_structured_json(data, str(path))
    if args.html_file:
        path = Path(args.html_file)
        return capture_from_html(path.read_text(encoding="utf-8-sig"), args.base_url or str(path), str(path), "html_file")
    if args.text_file:
        path = Path(args.text_file)
        return capture_from_text(path.read_text(encoding="utf-8-sig"), str(path))
    html = fetch_public_html(args.url)
    return capture_from_html(html, args.url, args.url, "public_url_fetch")


def capture_from_structured_json(data: Any, source: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        text = json.dumps(data, ensure_ascii=False)
        return capture_from_text(text, source)
    url = first_non_empty(
        data.get("publishedUrl"),
        data.get("url"),
        data.get("currentUrl"),
        data.get("canonicalUrl"),
        data.get("sourceUrl"),
        data.get("source"),
        first_url(json.dumps(data, ensure_ascii=False)),
    )
    title = first_non_empty(
        data.get("title"),
        data.get("name"),
        data.get("headline"),
        first_heading(data),
        first_content_line(str(data.get("text") or "")),
    )
    evidence = clean_list(data.get("evidence"))
    screenshot = data.get("screenshot")
    if screenshot:
        evidence.append(str(screenshot))
    return {
        "inputMode": "structured_json",
        "source": source,
        "publishedUrl": url,
        "title": title,
        "text": str(data.get("text") or ""),
        "evidence": evidence,
    }


def capture_from_html(html: str, current_url: str, source: str, mode: str) -> dict[str, Any]:
    parser = PublishedHTMLParser()
    parser.feed(html)
    url = first_non_empty(
        parser.meta.get("og:url"),
        parser.meta.get("twitter:url"),
        canonical_url(parser.links),
        current_url if current_url.startswith(("http://", "https://")) else "",
        first_url(parser.text),
    )
    title = first_non_empty(parser.meta.get("og:title"), parser.meta.get("twitter:title"), parser.headings[0] if parser.headings else "", parser.title)
    return {
        "inputMode": mode,
        "source": source,
        "publishedUrl": url,
        "title": title,
        "text": parser.text,
        "evidence": [source],
    }


def capture_from_text(text: str, source: str) -> dict[str, Any]:
    fields = parse_labeled_lines(text)
    return {
        "inputMode": "text_file",
        "source": source,
        "publishedUrl": first_non_empty(fields.get("url"), fields.get("publishedurl"), first_url(text)),
        "title": first_non_empty(fields.get("title"), fields.get("name"), first_content_line(text)),
        "platform": fields.get("platform", ""),
        "contentId": first_non_empty(fields.get("contentid"), fields.get("videoid"), fields.get("repo")),
        "publishedAt": first_non_empty(fields.get("publishedat"), fields.get("date")),
        "evidence": split_evidence(fields.get("evidence", "")) or [source],
        "text": text,
    }


def build_capture_report(args: argparse.Namespace, capture: dict[str, Any]) -> dict[str, Any]:
    url = first_non_empty(capture.get("publishedUrl"))
    platform = args.platform or capture.get("platform") or metrics_intake.choose_platform("auto", url)
    title = first_non_empty(args.title, capture.get("title"), "Untitled published item")
    content_id = first_non_empty(args.content_id, capture.get("contentId"), published_items.content_id_from_url(platform, url))
    evidence = unique([url, *capture.get("evidence", []), *args.evidence])
    issues = validation_issues(url, platform)
    record = None
    if not issues:
        record = published_items.normalize_record(
            {
                "platform": platform,
                "publishedUrl": url,
                "contentId": content_id,
                "title": title,
                "publishedAt": first_non_empty(args.published_at, capture.get("publishedAt"), TODAY),
                "evidence": evidence,
                "source": {"type": "publish_url_capture", "value": capture.get("source", ""), "capturedAt": TODAY},
            }
        )
    return {
        "generatedAt": TODAY,
        "status": "ready" if record else "blocked",
        "inputMode": capture.get("inputMode", ""),
        "source": capture.get("source", ""),
        "record": record,
        "candidate": {
            "platform": platform,
            "publishedUrl": url,
            "contentId": content_id,
            "title": title,
            "evidence": evidence,
        },
        "issues": issues,
        "guardrails": [
            "Capture browser-visible post-publish evidence only.",
            "Do not save cookies, passwords, hidden browser tokens, or private API responses.",
            "Do not treat drafts, editor URLs, preview URLs, or dry-runs as published content.",
            "Register metrics only after real platform or business evidence exists.",
        ],
    }


def validation_issues(url: str, platform: str) -> list[str]:
    issues = []
    if not url:
        issues.append("missing_published_url")
    if not platform or platform == "unknown":
        issues.append("unknown_platform")
    lowered = url.lower()
    if any(marker in lowered for marker in ["/edit", "/draft", "preview", "localhost", "127.0.0.1"]):
        issues.append("url_looks_like_draft_or_preview")
    return issues


def update_published_items(out_dir: Path, record: dict[str, Any]) -> None:
    existing_path = published_items.published_items_dir(out_dir) / "published-items.json"
    existing = published_items.records_from_published_items_json(existing_path) if existing_path.exists() else []
    report = published_items.build_report([*existing, record], [], [{"type": "publish_url_capture", "source": record["publishedUrl"], "records": 1, "pending": 0}])
    published_items.write_report(out_dir, report)


def write_capture_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = capture_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "publish-url-capture.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "publish-url-capture.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    candidate = report["candidate"]
    lines = [
        "# Publish URL Capture",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Input mode: `{report['inputMode']}`",
        f"- Platform: {candidate['platform']}",
        f"- URL: {candidate['publishedUrl'] or 'missing'}",
        f"- Title: {candidate['title']}",
    ]
    if report["issues"]:
        lines.extend(["", "## Issues"])
        lines.extend([f"- {item}" for item in report["issues"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


def capture_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/publish-capture"


def fetch_public_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def first_heading(data: dict[str, Any]) -> str:
    headings = data.get("headings")
    if isinstance(headings, list):
        for item in headings:
            if isinstance(item, dict) and item.get("text"):
                return str(item["text"])
            if isinstance(item, str) and item:
                return item
    return ""


def canonical_url(links: list[dict[str, str]]) -> str:
    for link in links:
        if "canonical" in link.get("rel", "").lower() and link.get("href"):
            return link["href"]
    return ""


def parse_labeled_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = re.sub(r"[^a-zA-Z0-9]", "", key).lower()
        value = normalize_space(value)
        if key and value:
            fields[key] = value
    return fields


def first_content_line(text: str) -> str:
    for line in text.splitlines():
        line = normalize_space(line)
        if line and ":" not in line[:40]:
            return line
    return ""


def first_url(text: str) -> str:
    match = re.search(r"https?://[^\s)>\]\"']+", text)
    return match.group(0) if match else ""


def split_evidence(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[;,]\s*", value) if item.strip()]


def clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False, sort_keys=True)]
    if isinstance(value, str):
        return split_evidence(value)
    return []


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = normalize_space(value)
        if text:
            return text
    return ""


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def unique(values: list[Any]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


if __name__ == "__main__":
    main()
