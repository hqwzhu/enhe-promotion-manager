#!/usr/bin/env python3
"""Capture public browser-visible search result snapshots for promotion competitors."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from env_loader import load_project_env, preparse_env_file
from web_data_provider import DEFAULT_FIRECRAWL_BASE_URL, WebDataProviderError, search_web


TODAY = date.today().isoformat()
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]


PLATFORM_SEARCH = {
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "zhihu": "https://www.zhihu.com/search?type=content&q={query}",
    "xiaohongshu": "https://www.xiaohongshu.com/search_result?keyword={query}",
    "douyin": "https://www.douyin.com/search/{path_query}",
    "github": "https://github.com/search?q={query}&type=repositories&s=stars&o=desc",
    "tiktok": "https://www.tiktok.com/search?q={query}",
}


class SearchSnapshotHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_skip = ""
        self.title_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self.blocks: list[str] = []
        self._stack: list[str] = []
        self._link_href = ""
        self._link_text: list[str] = []
        self._block_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        self._stack.append(tag)
        if tag in {"script", "style", "noscript"}:
            self.in_skip = tag
        if tag == "a" and attrs_map.get("href"):
            self._link_href = attrs_map["href"]
            self._link_text = []
        if tag in {"article", "section", "li", "div"}:
            self._block_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == self.in_skip:
            self.in_skip = ""
        if tag == "a" and self._link_href:
            text = normalize_space(" ".join(self._link_text))
            if text:
                self.links.append({"url": self._link_href, "title": text})
            self._link_href = ""
            self._link_text = []
        if tag in {"article", "section", "li", "div"} and self._block_text:
            text = normalize_space(" ".join(self._block_text))
            if len(text) >= 20:
                self.blocks.append(text)
            self._block_text = []
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self.in_skip:
            return
        text = normalize_space(data)
        if not text:
            return
        current = self._stack[-1] if self._stack else ""
        if current == "title":
            self.title_parts.append(text)
        if self._link_href:
            self._link_text.append(text)
        self._block_text.append(text)


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    platforms = split_csv(args.platforms) or DEFAULT_PLATFORMS
    snapshot_dir = Path(args.snapshot_dir) if args.snapshot_dir else Path(args.out_dir) / "search-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for platform in platforms:
        result = capture_platform(args, platform, snapshot_dir)
        records.append(result)
    report = {
        "generatedAt": TODAY,
        "query": args.query,
        "envLoad": env_load,
        "snapshotDir": str(snapshot_dir),
        "records": records,
        "guardrails": [
            "Only browser-visible public search evidence is captured.",
            "No automatic login, captcha bypass, cookie extraction, hidden token reuse, or private endpoint calls.",
            "Missing metrics are left missing; do not infer views, likes, comments, revenue, or orders.",
        ],
    }
    write_report(args.out_dir, report)
    print(f"Platform browser search snapshots written to: {(report_dir(args.out_dir) / 'browser-search-snapshots.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture platform search pages into structured snapshot JSON files.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated platforms.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before reading provider credentials. Values are never written to reports.")
    parser.add_argument("--snapshot-dir", default="", help="Directory to write <platform>.json snapshots.")
    parser.add_argument("--html-snapshot-dir", default="", help="Optional fixture/export directory with <platform>.html files.")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--install-browser-if-missing", action="store_true")
    parser.add_argument("--web-data-provider", default=os.environ.get("WEB_DATA_PROVIDER", "auto"), choices=["auto", "local", "firecrawl"], help="Optional provider for public web search before browser capture.")
    parser.add_argument("--firecrawl-base-url", default=os.environ.get("FIRECRAWL_BASE_URL", DEFAULT_FIRECRAWL_BASE_URL), help="Firecrawl API base URL. API key is read only from FIRECRAWL_API_KEY.")
    parser.add_argument("--web-data-fixture-json", default="", help="Local web data fixture for tests/offline review.")
    return parser.parse_args()


def capture_platform(args: argparse.Namespace, platform: str, snapshot_dir: Path) -> dict[str, Any]:
    search_url = search_url_for(platform, args.query)
    html_file = html_snapshot_file(args.html_snapshot_dir, platform)
    if html_file:
        snapshot = snapshot_from_html(html_file.read_text(encoding="utf-8-sig"), platform, args.query, search_url, args.top_n, str(html_file))
        status = "ready"
    else:
        snapshot, status = snapshot_from_web_data(args, platform, search_url)
    if status not in {"ready"} and not html_file:
        snapshot, status = snapshot_from_browser(args, platform, search_url)
    snapshot_path = snapshot_dir / f"{platform}.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "platform": platform,
        "status": status,
        "searchUrl": search_url,
        "snapshot": str(snapshot_path),
        "recordCount": len(snapshot.get("items", [])),
        "reason": snapshot.get("reason", ""),
    }


def snapshot_from_web_data(args: argparse.Namespace, platform: str, search_url: str) -> tuple[dict[str, Any], str]:
    provider_query = web_data_query(platform, args.query)
    try:
        result = search_web(
            provider_query,
            limit=max(args.top_n, 5),
            provider=args.web_data_provider,
            base_url=args.firecrawl_base_url,
            fixture_json=args.web_data_fixture_json,
        )
    except WebDataProviderError as exc:
        return blocked_snapshot(platform, args.query, search_url, f"Web data provider failed: {exc}"), "blocked"

    status = str(result.get("status") or "skipped")
    if status != "ready":
        return {
            "platform": platform,
            "query": args.query,
            "source": search_url,
            "searchUrl": search_url,
            "snapshotType": "platform_search_browser",
            "captureMode": "web_data_provider",
            "status": status,
            "reason": result.get("reason", ""),
            "webDataProvider": result.get("provider", ""),
            "webDataQuery": provider_query,
            "apiKeyPresent": bool(result.get("apiKeyPresent")),
            "items": [],
            "guardrails": snapshot_guardrails(),
        }, status

    items = []
    seen: set[str] = set()
    for row in result.get("results", []):
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "")
        title = normalize_space(row.get("title") or first_sentence(row.get("markdown", "")) or url)
        if not title or not relevant_url(platform, url):
            continue
        key = f"{url}::{title.lower()}"
        if key in seen:
            continue
        seen.add(key)
        content = normalize_space(row.get("markdown") or row.get("description") or title)
        items.append({"title": title, "url": url, "content": content})
        if len(items) >= args.top_n:
            break

    snapshot = {
        "platform": platform,
        "query": args.query,
        "source": result.get("baseUrl", ""),
        "searchUrl": search_url,
        "snapshotType": "platform_search_browser",
        "captureMode": "firecrawl_search",
        "title": f"{platform} search results for {args.query}",
        "webDataProvider": result.get("provider", ""),
        "webDataQuery": provider_query,
        "apiKeyPresent": bool(result.get("apiKeyPresent")),
        "items": items,
        "guardrails": snapshot_guardrails(),
    }
    if not items:
        snapshot["reason"] = "Web data provider returned no platform-relevant results."
        return snapshot, "partial_ready"
    return snapshot, "ready"


def snapshot_from_browser(args: argparse.Namespace, platform: str, search_url: str) -> tuple[dict[str, Any], str]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 - optional dependency.
        return blocked_snapshot(platform, args.query, search_url, f"Playwright is not installed: {exc}"), "blocked"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1400})
            response = page.goto(search_url, wait_until=args.wait_until, timeout=args.timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(args.timeout_ms, 10000))
            except PlaywrightTimeoutError:
                pass
            data = page.evaluate(BROWSER_SEARCH_SCRIPT, {"platform": platform, "query": args.query, "topN": args.top_n})
            browser.close()
            data["httpStatus"] = response.status if response else None
            data["source"] = search_url
            data["searchUrl"] = search_url
            data["captureMode"] = "playwright_chromium"
            data["snapshotType"] = "platform_search_browser"
            data["guardrails"] = snapshot_guardrails()
            return data, "ready"
    except PlaywrightError as exc:
        message = str(exc)
        if "Executable doesn't exist" in message and args.install_browser_if_missing:
            install_chromium()
            retry_args = argparse.Namespace(**vars(args))
            retry_args.install_browser_if_missing = False
            return snapshot_from_browser(retry_args, platform, search_url)
        if "Executable doesn't exist" in message:
            return blocked_snapshot(platform, args.query, search_url, "Playwright Chromium is missing. Run: python -m playwright install chromium"), "blocked"
        return blocked_snapshot(platform, args.query, search_url, f"Browser search failed: {message}"), "blocked"


BROWSER_SEARCH_SCRIPT = r"""
({platform, query, topN}) => {
  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const anchors = Array.from(document.querySelectorAll('a[href]'));
  const items = [];
  const seen = new Set();
  const hostOk = (url) => {
    try {
      const host = new URL(url).host.toLowerCase();
      if (platform === 'youtube') return host.includes('youtube.com') || host.includes('youtu.be');
      if (platform === 'zhihu') return host.includes('zhihu.com');
      if (platform === 'xiaohongshu') return host.includes('xiaohongshu.com') || host.includes('xhslink.com');
      if (platform === 'douyin') return host.includes('douyin.com');
      if (platform === 'github') return host.includes('github.com');
      if (platform === 'tiktok') return host.includes('tiktok.com');
      return true;
    } catch {
      return false;
    }
  };
  for (const anchor of anchors) {
    const url = anchor.href || '';
    const title = clean(anchor.innerText || anchor.getAttribute('aria-label') || anchor.getAttribute('title') || '');
    if (!url || !title || title.length < 4 || !hostOk(url)) continue;
    const key = `${url}::${title.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const container = anchor.closest('article, li, section, div') || anchor;
    const content = clean(container.innerText || title);
    items.push({title, url, content});
    if (items.length >= topN * 3) break;
  }
  return {
    platform,
    query,
    url: location.href,
    title: clean(document.title),
    items: items.slice(0, topN)
  };
}
"""


def snapshot_from_html(html: str, platform: str, query: str, search_url: str, top_n: int, source: str) -> dict[str, Any]:
    parser = SearchSnapshotHTMLParser()
    parser.feed(html)
    items = []
    seen: set[str] = set()
    for link in parser.links:
        url = absolutize_url(link["url"], search_url)
        title = normalize_space(link["title"])
        if not title or not relevant_url(platform, url):
            continue
        key = f"{url}::{title.lower()}"
        if key in seen:
            continue
        seen.add(key)
        content = matching_block(title, parser.blocks) or title
        items.append({"title": title, "url": url, "content": content})
        if len(items) >= top_n:
            break
    if not items:
        for index, block in enumerate(parser.blocks[:top_n], start=1):
            items.append({"title": first_sentence(block) or f"{platform} search result {index}", "url": "", "content": block})
    return {
        "platform": platform,
        "query": query,
        "source": source,
        "searchUrl": search_url,
        "snapshotType": "platform_search_browser",
        "captureMode": "saved_html_snapshot",
        "title": normalize_space(" ".join(parser.title_parts)),
        "items": items,
        "guardrails": snapshot_guardrails(),
    }


def blocked_snapshot(platform: str, query: str, search_url: str, reason: str) -> dict[str, Any]:
    return {
        "platform": platform,
        "query": query,
        "source": search_url,
        "searchUrl": search_url,
        "snapshotType": "platform_search_browser",
        "captureMode": "blocked",
        "status": "blocked",
        "reason": reason,
        "items": [],
        "guardrails": snapshot_guardrails(),
    }


def install_chromium() -> None:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def write_report(out_dir: str, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "browser-search-snapshots.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "browser-search-snapshots.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Browser Search Snapshots",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Query: {report['query']}",
        f"- Snapshot dir: {report['snapshotDir']}",
        "",
        "## Platforms",
    ]
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['platform']}",
                f"- Status: `{record['status']}`",
                f"- Search URL: {record['searchUrl']}",
                f"- Snapshot: {record['snapshot']}",
                f"- Records: {record['recordCount']}",
            ]
        )
        if record.get("reason"):
            lines.append(f"- Reason: {record['reason']}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def search_url_for(platform: str, query: str) -> str:
    encoded = urllib.parse.quote_plus(query)
    path_encoded = urllib.parse.quote(query, safe="")
    template = PLATFORM_SEARCH.get(platform, PLATFORM_SEARCH["youtube"])
    return template.format(query=encoded, path_query=path_encoded)


def web_data_query(platform: str, query: str) -> str:
    domain = {
        "youtube": "youtube.com",
        "zhihu": "zhihu.com",
        "xiaohongshu": "xiaohongshu.com",
        "douyin": "douyin.com",
        "github": "github.com",
        "tiktok": "tiktok.com",
    }.get(platform)
    return f"site:{domain} {query}" if domain else query


def html_snapshot_file(directory: str, platform: str) -> Path | None:
    if not directory:
        return None
    base = Path(directory)
    for suffix in [".html", ".htm"]:
        path = base / f"{platform}{suffix}"
        if path.exists():
            return path
    return None


def relevant_url(platform: str, url: str) -> bool:
    if not url:
        return False
    host = urllib.parse.urlparse(url).netloc.lower()
    hostname = urllib.parse.urlparse(url).hostname or ""
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    if platform == "youtube":
        return "youtube.com" in host or "youtu.be" in host
    if platform == "zhihu":
        return "zhihu.com" in host
    if platform == "xiaohongshu":
        return "xiaohongshu.com" in host or "xhslink.com" in host
    if platform == "douyin":
        return "douyin.com" in host
    if platform == "github":
        return "github.com" in host
    if platform == "tiktok":
        return "tiktok.com" in host
    return True


def absolutize_url(url: str, base: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return urllib.parse.urljoin(base, url)


def matching_block(title: str, blocks: list[str]) -> str:
    title_lower = title.lower()
    for block in blocks:
        if title_lower in block.lower():
            return block
    return ""


def first_sentence(value: str) -> str:
    return normalize_space(re.split(r"(?<=[.!?])\s+|[\r\n]+", value)[0])[:120]


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def report_dir(out_dir: str) -> Path:
    return Path(out_dir) / "reports/promotion-manager/competitors"


def snapshot_guardrails() -> list[str]:
    return [
        "Browser-visible public search evidence only.",
        "No automatic login, captcha bypass, cookie extraction, hidden token reuse, or private endpoint calls.",
        "Metrics must be observed in the source or imported from official/user-provided evidence.",
    ]


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


if __name__ == "__main__":
    main()
