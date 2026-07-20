#!/usr/bin/env python3
"""Discover likely product URLs from a public website entry page."""

from __future__ import annotations

import argparse
import gzip
import ipaddress
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from env_loader import load_project_env, preparse_env_file
from web_data_provider import DEFAULT_FIRECRAWL_BASE_URL, WebDataProviderError, map_site


TODAY = date.today().isoformat()
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"
PRODUCT_TERMS = {
    "product",
    "products",
    "tool",
    "tools",
    "app",
    "apps",
    "solution",
    "solutions",
    "use-case",
    "use-cases",
    "features",
    "pricing",
    "demo",
    "launch",
    "generator",
    "template",
    "kit",
    "platform",
    "service",
    "services",
    "shop",
    "store",
    "item",
    "buy",
}
NEGATIVE_TERMS = {
    "login",
    "signin",
    "sign-in",
    "signup",
    "sign-up",
    "account",
    "auth",
    "privacy",
    "terms",
    "legal",
    "cookie",
    "blog",
    "news",
    "docs",
    "documentation",
    "careers",
    "contact",
    "about",
    "support",
    "faq",
    "press",
    "cart",
    "checkout",
    "search",
}


@dataclass
class Page:
    url: str
    source: str
    html: str
    depth: int


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_skip = ""
        self.in_title = False
        self.title_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self.in_skip = tag
        if tag == "title":
            self.in_title = True
        if tag == "a" and attrs_map.get("href"):
            self._href = attrs_map["href"]
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == self.in_skip:
            self.in_skip = ""
        if tag == "title":
            self.in_title = False
        if tag == "a" and self._href:
            text = normalize_space(" ".join(self._text))
            self.links.append({"href": self._href, "text": text})
            self._href = ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self.in_skip:
            return
        text = normalize_space(data)
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if self._href:
            self._text.append(text)


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    pages, fetch_records, sitemap_records, sitemap_urls = load_sources(args)
    web_data_records, web_data_urls = load_web_data_sources(args)
    candidates = rank_candidates(args, pages, sitemap_urls, web_data_urls)
    report = build_report(args, pages, fetch_records, sitemap_records, sitemap_urls, web_data_records, web_data_urls, candidates)
    report["envLoad"] = env_load
    write_report(Path(args.out_dir), report)
    print(f"Product URL discovery written to: {(report_dir(Path(args.out_dir)) / 'product-url-discovery.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover likely product URLs from public website links and sitemaps.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--site-url", help="Public website or landing page URL.")
    source.add_argument("--html-file", help="Saved public website HTML.")
    source.add_argument("--sitemap-url", help="Public sitemap.xml or sitemap index URL.")
    source.add_argument("--sitemap-file", help="Saved sitemap.xml, sitemap index, or .xml.gz file.")
    parser.add_argument("--base-url", default="", help="Base URL for resolving links in --html-file.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before reading provider credentials. Values are never written to reports.")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--min-score", type=float, default=3.0)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--max-sitemap-urls", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--include-external", action="store_true")
    parser.add_argument("--skip-sitemaps", action="store_true", help="Do not try robots.txt or /sitemap.xml when --site-url is used.")
    parser.add_argument("--allow-localhost", action="store_true")
    parser.add_argument("--web-data-provider", default=os.environ.get("WEB_DATA_PROVIDER", "auto"), choices=["auto", "local", "firecrawl"], help="Optional provider for site mapping before ranking product URLs.")
    parser.add_argument("--firecrawl-base-url", default=os.environ.get("FIRECRAWL_BASE_URL", DEFAULT_FIRECRAWL_BASE_URL), help="Firecrawl API base URL. API key is read only from FIRECRAWL_API_KEY.")
    parser.add_argument("--web-data-fixture-json", default="", help="Local web data fixture for tests/offline review.")
    parser.add_argument("--web-data-search", default="", help="Optional provider-side map search term, such as product or pricing.")
    return parser.parse_args()


def load_sources(args: argparse.Namespace) -> tuple[list[Page], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if args.html_file:
        path = Path(args.html_file)
        base_url = args.base_url or path.resolve().as_uri()
        html = path.read_text(encoding="utf-8-sig")
        return [Page(base_url, str(path), html, 0)], [], [], []
    if args.sitemap_file:
        sitemap_urls, sitemap_records = parse_sitemap_file(Path(args.sitemap_file), args)
        return [], [], sitemap_records, sitemap_urls
    if args.sitemap_url:
        sitemap_urls, sitemap_records = parse_sitemap_url(args.sitemap_url, args)
        return [], [], sitemap_records, sitemap_urls
    pages, fetch_records = crawl_site(args)
    sitemap_urls: list[str] = []
    sitemap_records: list[dict[str, Any]] = []
    if not args.skip_sitemaps:
        sitemap_urls, sitemap_records = discover_sitemap_urls(args)
    return pages, fetch_records, sitemap_records, sitemap_urls


def load_web_data_sources(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[str]]:
    if not args.site_url:
        return [], []
    record: dict[str, Any] = {
        "source": "web_data_provider",
        "provider": args.web_data_provider,
        "status": "skipped",
        "links": 0,
        "apiKeyPresent": False,
        "credentialValuesStored": False,
    }
    try:
        result = map_site(
            args.site_url,
            provider=args.web_data_provider,
            base_url=args.firecrawl_base_url,
            fixture_json=args.web_data_fixture_json,
            search=args.web_data_search,
        )
    except WebDataProviderError as exc:
        record.update({"status": "error", "reason": str(exc)})
        return [record], []

    links = [item.get("url", "") for item in result.get("links", []) if isinstance(item, dict)]
    urls = [url for url in links if is_http_url(url)]
    record.update(
        {
            "provider": result.get("provider", args.web_data_provider),
            "status": result.get("status", "skipped"),
            "reason": result.get("reason", ""),
            "links": len(urls),
            "apiKeyPresent": bool(result.get("apiKeyPresent")),
            "credentialValuesStored": False,
        }
    )
    return [record], dedupe(urls)


def crawl_site(args: argparse.Namespace) -> tuple[list[Page], list[dict[str, Any]]]:
    start_url = normalize_url(args.site_url, args.site_url)
    validate_fetch_url(start_url, args.allow_localhost)
    pages: list[Page] = []
    fetch_records: list[dict[str, Any]] = []
    queue: list[tuple[str, int, str]] = [(start_url, 0, "seed")]
    seen: set[str] = set()
    while queue and len(pages) < max(args.max_pages, 1):
        url, depth, source = queue.pop(0)
        if url in seen or depth > args.max_depth:
            continue
        seen.add(url)
        try:
            html, final_url = fetch_public_html(url, args.timeout)
        except Exception as exc:  # noqa: BLE001 - report and continue.
            fetch_records.append({"url": url, "source": source, "status": "error", "reason": str(exc)})
            continue
        page = Page(final_url, source, html, depth)
        pages.append(page)
        fetch_records.append({"url": url, "finalUrl": final_url, "source": source, "status": "ready", "depth": depth})
        if depth >= args.max_depth:
            continue
        for link in parse_links(page):
            candidate = normalize_url(link["href"], final_url)
            if not candidate or candidate in seen:
                continue
            if not args.include_external and not same_origin(start_url, candidate):
                continue
            if not is_html_like(candidate):
                continue
            try:
                validate_fetch_url(candidate, args.allow_localhost)
            except ValueError:
                continue
            queue.append((candidate, depth + 1, final_url))
    return pages, fetch_records


def rank_candidates(args: argparse.Namespace, pages: list[Page], sitemap_urls: list[str], web_data_urls: list[str] | None = None) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    base_origin = first_origin(args.site_url or args.sitemap_url or args.base_url or (pages[0].url if pages else "") or (sitemap_urls[0] if sitemap_urls else ""))
    for page in pages:
        for link in parse_links(page):
            url = normalize_url(link["href"], page.url)
            if not url or not is_http_url(url):
                continue
            if not args.include_external and base_origin and first_origin(url) != base_origin:
                continue
            score, reasons = product_score(url, link.get("text", ""))
            record = records.get(url)
            if not record or score > record["score"]:
                records[url] = {
                    "url": url,
                    "anchorText": link.get("text", ""),
                    "sourcePage": page.url,
                    "sourceDepth": page.depth,
                    "score": score,
                    "reasons": reasons,
                    "sourceType": "html_link",
                    "selected": False,
                }
    for url in sitemap_urls:
        if not url or not is_http_url(url):
            continue
        if not args.include_external and base_origin and first_origin(url) != base_origin:
            continue
        score, reasons = product_score(url, "")
        record = records.get(url)
        if not record or score > record["score"]:
            records[url] = {
                "url": url,
                "anchorText": "",
                "sourcePage": "sitemap",
                "sourceDepth": 0,
                "score": score,
                "reasons": reasons,
                "sourceType": "sitemap",
                "selected": False,
            }
    for url in web_data_urls or []:
        if not url or not is_http_url(url):
            continue
        if not args.include_external and base_origin and first_origin(url) != base_origin:
            continue
        score, reasons = product_score(url, "")
        record = records.get(url)
        if not record or score > record["score"]:
            records[url] = {
                "url": url,
                "anchorText": "",
                "sourcePage": "web_data_provider",
                "sourceDepth": 0,
                "score": score,
                "reasons": reasons,
                "sourceType": "web_data_map",
                "selected": False,
            }
    candidates = sorted(records.values(), key=lambda item: (item["score"], -item["sourceDepth"], item["url"]), reverse=True)
    selected_count = 0
    for candidate in candidates:
        if candidate["score"] >= args.min_score and selected_count < args.top_n:
            candidate["selected"] = True
            selected_count += 1
    return candidates


def product_score(url: str, text: str) -> tuple[float, list[str]]:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower().strip("/")
    tokens = [item for item in re.split(r"[^a-z0-9\u4e00-\u9fff-]+", f"{path} {text.lower()}") if item]
    token_set = set(tokens)
    score = 0.0
    reasons: list[str] = []
    for term in PRODUCT_TERMS:
        if term in token_set or f"/{term}" in f"/{path}":
            score += 2.0
            reasons.append(f"product_term:{term}")
    if re.search(r"/(products?|tools?|apps?|solutions?|shop|store)/[^/]+", "/" + path):
        score += 4.0
        reasons.append("product_collection_detail_path")
    if re.search(r"/(pricing|demo|buy|checkout)(/|$)", "/" + path):
        score += 1.5
        reasons.append("commercial_intent_path")
    if len([item for item in path.split("/") if item]) >= 2:
        score += 0.5
        reasons.append("specific_path_depth")
    if text and any(term in text.lower() for term in ["try", "start", "buy", "demo", "launch", "product", "tool"]):
        score += 1.0
        reasons.append("commercial_anchor_text")
    for term in NEGATIVE_TERMS:
        if term in token_set or f"/{term}" in f"/{path}":
            score -= 3.0
            reasons.append(f"negative_term:{term}")
    if parsed.query:
        score -= 0.5
        reasons.append("query_string_penalty")
    return round(score, 4), reasons or ["low_signal_link"]


def build_report(
    args: argparse.Namespace,
    pages: list[Page],
    fetch_records: list[dict[str, Any]],
    sitemap_records: list[dict[str, Any]],
    sitemap_urls: list[str],
    web_data_records: list[dict[str, Any]],
    web_data_urls: list[str],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    selected = [item for item in candidates if item["selected"]]
    return {
        "generatedAt": TODAY,
        "status": "ready" if selected else "no_product_urls_found",
        "input": {
            "siteUrl": args.site_url or "",
            "htmlFile": args.html_file or "",
            "sitemapUrl": args.sitemap_url or "",
            "sitemapFile": args.sitemap_file or "",
            "baseUrl": args.base_url or "",
            "topN": args.top_n,
            "minScore": args.min_score,
            "maxPages": args.max_pages,
            "maxDepth": args.max_depth,
            "maxSitemapUrls": args.max_sitemap_urls,
            "includeExternal": bool(args.include_external),
            "skipSitemaps": bool(args.skip_sitemaps),
        },
        "summary": {
            "pagesRead": len(pages),
            "robotsTxtRead": sum(1 for item in sitemap_records if item.get("source") == "robots.txt" and item.get("status") == "ready"),
            "sitemapsRead": sum(1 for item in sitemap_records if item.get("source") in {"sitemap_file", "sitemap_url"} and item.get("status") == "ready"),
            "sitemapUrls": len(sitemap_urls),
            "webDataLinks": len(web_data_urls),
            "candidateUrls": len(candidates),
            "selectedUrls": len(selected),
        },
        "selectedUrls": [item["url"] for item in selected],
        "candidates": candidates,
        "fetchRecords": fetch_records,
        "sitemapRecords": sitemap_records,
        "webDataRecords": web_data_records,
        "artifacts": {
            "urlsFile": str(urls_file(Path(args.out_dir))),
        },
        "guardrails": [
            "Only public HTML links and public sitemap URLs are used for discovery.",
            "Optional Firecrawl Map results are used only for public site URL discovery and read FIRECRAWL_API_KEY from the environment.",
            "No login, captcha bypass, cookie extraction, hidden token reuse, or private endpoint calls.",
            "Private, localhost, and link-local URLs are blocked unless --allow-localhost is supplied for local testing.",
            "Discovered URLs are candidates; product claims still require product_url_reader.py and product_intake.py evidence.",
        ],
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    product_urls = report.get("selectedUrls", [])
    urls_file(out_dir).write_text("\n".join(product_urls) + ("\n" if product_urls else ""), encoding="utf-8")
    (directory / "product-url-discovery.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "product-url-discovery.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Product URL Discovery",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Pages read: {report['summary']['pagesRead']}",
        f"- Robots.txt read: {report['summary'].get('robotsTxtRead', 0)}",
        f"- Sitemaps read: {report['summary'].get('sitemapsRead', 0)}",
        f"- Sitemap URLs: {report['summary'].get('sitemapUrls', 0)}",
        f"- Web data links: {report['summary'].get('webDataLinks', 0)}",
        f"- Candidate URLs: {report['summary']['candidateUrls']}",
        f"- Selected URLs: {report['summary']['selectedUrls']}",
        f"- URLs file: {report['artifacts']['urlsFile']}",
        "",
        "## Selected URLs",
    ]
    if report["selectedUrls"]:
        lines.extend(f"- {url}" for url in report["selectedUrls"])
    else:
        lines.append("- none")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def discover_sitemap_urls(args: argparse.Namespace) -> tuple[list[str], list[dict[str, Any]]]:
    start_url = normalize_url(args.site_url, args.site_url)
    sitemap_sources = default_sitemap_sources(start_url)
    robot_sitemaps, robot_record = robots_sitemaps(start_url, args)
    records = [robot_record]
    sitemap_sources.extend(robot_sitemaps)
    deduped_sources = dedupe(sitemap_sources)
    urls: list[str] = []
    for source in deduped_sources:
        parsed_urls, parsed_records = parse_sitemap_url(source, args)
        records.extend(parsed_records)
        urls.extend(parsed_urls)
        if len(urls) >= args.max_sitemap_urls:
            break
    return dedupe(urls)[: args.max_sitemap_urls], records


def default_sitemap_sources(site_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(site_url)
    if not parsed.scheme or not parsed.netloc:
        return []
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return [urllib.parse.urljoin(origin, "/sitemap.xml")]


def robots_sitemaps(site_url: str, args: argparse.Namespace) -> tuple[list[str], dict[str, Any]]:
    parsed = urllib.parse.urlparse(site_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urllib.parse.urljoin(origin, "/robots.txt")
    record: dict[str, Any] = {"url": robots_url, "source": "robots.txt", "status": "skipped", "sitemaps": []}
    try:
        validate_fetch_url(robots_url, args.allow_localhost)
        text, final_url = fetch_public_text(robots_url, args.timeout)
    except Exception as exc:  # noqa: BLE001 - sitemap discovery should continue.
        record.update({"status": "error", "reason": str(exc)})
        return [], record
    sitemaps = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("sitemap:"):
            sitemap = line.split(":", 1)[1].strip()
            if sitemap:
                sitemaps.append(normalize_url(sitemap, final_url))
    record.update({"status": "ready", "finalUrl": final_url, "sitemaps": sitemaps})
    return sitemaps, record


def parse_sitemap_file(path: Path, args: argparse.Namespace) -> tuple[list[str], list[dict[str, Any]]]:
    record: dict[str, Any] = {"url": str(path), "source": "sitemap_file", "status": "error", "urls": 0}
    try:
        data = path.read_bytes()
        if path.suffix.lower() == ".gz":
            data = gzip.decompress(data)
        urls, nested = parse_sitemap_xml(data, path.resolve().as_uri())
    except Exception as exc:  # noqa: BLE001 - return a structured record.
        record["reason"] = str(exc)
        return [], [record]
    record.update({"status": "ready", "urls": len(urls), "nestedSitemaps": len(nested)})
    return dedupe(urls)[: args.max_sitemap_urls], [record]


def parse_sitemap_url(url: str, args: argparse.Namespace, depth: int = 0) -> tuple[list[str], list[dict[str, Any]]]:
    normalized = normalize_url(url, args.site_url or args.sitemap_url or url)
    record: dict[str, Any] = {"url": normalized, "source": "sitemap_url", "status": "error", "depth": depth, "urls": 0}
    if depth > 2:
        record.update({"status": "skipped", "reason": "Maximum sitemap index depth reached."})
        return [], [record]
    try:
        validate_fetch_url(normalized, args.allow_localhost)
        data, final_url, content_type = fetch_public_bytes(normalized, args.timeout)
        if normalized.lower().endswith(".gz") or "gzip" in content_type.lower():
            data = gzip.decompress(data)
        urls, nested = parse_sitemap_xml(data, final_url)
    except Exception as exc:  # noqa: BLE001 - report and continue.
        record["reason"] = str(exc)
        return [], [record]
    record.update({"status": "ready", "finalUrl": final_url, "urls": len(urls), "nestedSitemaps": len(nested)})
    records = [record]
    all_urls = list(urls)
    for nested_url in nested:
        if len(all_urls) >= args.max_sitemap_urls:
            break
        nested_urls, nested_records = parse_sitemap_url(nested_url, args, depth + 1)
        records.extend(nested_records)
        all_urls.extend(nested_urls)
    return dedupe(all_urls)[: args.max_sitemap_urls], records


def parse_sitemap_xml(data: bytes, source_url: str) -> tuple[list[str], list[str]]:
    root = ET.fromstring(data)
    tag = local_name(root.tag)
    urls: list[str] = []
    nested_sitemaps: list[str] = []
    if tag == "urlset":
        for element in root.iter():
            if local_name(element.tag) == "loc" and element.text:
                urls.append(normalize_url(element.text.strip(), source_url))
    elif tag == "sitemapindex":
        for sitemap in root.iter():
            if local_name(sitemap.tag) == "loc" and sitemap.text:
                nested_sitemaps.append(normalize_url(sitemap.text.strip(), source_url))
    else:
        raise ValueError(f"Unsupported sitemap root element: {tag}")
    return [url for url in dedupe(urls) if is_http_url(url)], [url for url in dedupe(nested_sitemaps) if is_http_url(url)]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_links(page: Page) -> list[dict[str, str]]:
    parser = LinkParser()
    parser.feed(page.html)
    return parser.links


def fetch_public_text(url: str, timeout: float) -> tuple[str, str]:
    data, final_url, _content_type = fetch_public_bytes(url, timeout)
    return data.decode("utf-8", errors="replace"), final_url


def fetch_public_bytes(url: str, timeout: float) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,text/plain,text/html,*/*;q=0.8"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        return response.read(), response.geturl(), content_type


def fetch_public_html(url: str, timeout: float) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        if content_type and "html" not in content_type and "xml" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type}")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace"), response.geturl()


def normalize_url(url: str, base_url: str) -> str:
    if not url:
        return ""
    absolute = urllib.parse.urljoin(base_url, url)
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme not in {"http", "https", "file"}:
        return ""
    if parsed.scheme == "file":
        return absolute
    cleaned = parsed._replace(fragment="")
    return urllib.parse.urlunparse(cleaned)


def validate_fetch_url(url: str, allow_localhost: bool) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Only HTTP(S) URLs can be fetched: {url}")
    host = parsed.hostname or ""
    if is_private_host(host) and not allow_localhost:
        raise ValueError(f"Refusing to fetch private or local host: {host}")


def is_private_host(host: str) -> bool:
    if not host:
        return True
    lowered = host.lower()
    if lowered in {"localhost"} or lowered.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def same_origin(left: str, right: str) -> bool:
    return first_origin(left) == first_origin(right)


def first_origin(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def is_http_url(url: str) -> bool:
    return urllib.parse.urlparse(url).scheme in {"http", "https"}


def is_html_like(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower()
    if not path or path.endswith("/"):
        return True
    return not re.search(r"\.(png|jpe?g|webp|gif|svg|pdf|zip|mp4|mov|mp3|css|js|ico)(\?|$)", path)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/intake"


def urls_file(out_dir: Path) -> Path:
    directory = out_dir / "product-url-discovery"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "product-urls.txt"


def dedupe(values: list[str]) -> list[str]:
    result = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    main()
