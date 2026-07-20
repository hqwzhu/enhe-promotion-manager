#!/usr/bin/env python3
"""Capture multi-result platform search evidence into competitor records."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import metric_parsing


TODAY = date.today().isoformat()
METRIC_NAMES = [
    "views",
    "likes",
    "favorites",
    "comments",
    "shares",
    "clicks",
    "stars",
    "forks",
    "subscribers",
]
NON_CONTENT_PATH_PARTS = {
    "about",
    "aboutus",
    "agreement",
    "agreements",
    "contact",
    "help",
    "privacy",
    "recovery_account",
    "terms",
}
NON_CONTENT_TITLE_TERMS = {
    "about us",
    "contact us",
    "privacy policy",
    "terms of service",
    "user agreement",
    "用户协议",
    "隐私政策",
    "关于我们",
    "联系我们",
    "账号找回",
}
ITEM_LIST_KEYS = [
    "items",
    "results",
    "records",
    "videos",
    "posts",
    "notes",
    "answers",
    "articles",
    "creators",
]


class SearchHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_skip = ""
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_blocks: list[str] = []
        self.links: list[dict[str, str]] = []
        self._link_href = ""
        self._link_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self.in_skip = tag
        if tag == "title":
            self.in_title = True
        if tag == "a" and attrs_map.get("href"):
            self._link_href = attrs_map["href"]
            self._link_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == self.in_skip:
            self.in_skip = ""
        if tag == "title":
            self.in_title = False
        if tag == "a" and self._link_href:
            text = normalize_space(" ".join(self._link_parts))
            if text:
                self.links.append({"url": self._link_href, "title": text})
            self._link_href = ""
            self._link_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_skip:
            return
        text = normalize_space(data)
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if self._link_href:
            self._link_parts.append(text)
        if len(text) >= 3:
            self.text_blocks.append(text)


@dataclass
class SourcePayload:
    input_mode: str
    source: str
    platform: str
    query: str
    items: list[Any]
    access_mode: str


def main() -> None:
    args = parse_args()
    payload = load_payload(args)
    records = normalize_records(payload, args.top_n)
    report = build_report(payload, records)
    write_report(args.out_dir, payload.platform, report)
    path = report_path(args.out_dir, payload.platform, "json")
    print(f"Platform search capture written to: {path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture platform search results from public HTML, text, URL, or structured browser snapshots.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--structured-json", help="Structured search snapshot from Codex/browser tooling.")
    source.add_argument("--html-file", help="Saved rendered/static search page HTML.")
    source.add_argument("--text-file", help="Copied search results text.")
    source.add_argument("--url", help="Public URL to fetch as static HTML. Do not use for login-only or captcha-protected pages.")
    parser.add_argument("--platform", required=True, choices=["youtube", "zhihu", "xiaohongshu", "douyin", "github", "tiktok", "other"])
    parser.add_argument("--query", default="")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> SourcePayload:
    if args.structured_json:
        path = Path(args.structured_json)
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return SourcePayload("structured_json", str(path), args.platform, args.query or query_from_data(data), items_from_json(data), "codex_or_browser_snapshot")
    if args.html_file:
        path = Path(args.html_file)
        html = path.read_text(encoding="utf-8-sig")
        return SourcePayload("html_file", str(path), args.platform, args.query, items_from_html(html, str(path), args.platform), "saved_rendered_or_static_html")
    if args.text_file:
        path = Path(args.text_file)
        text = path.read_text(encoding="utf-8-sig")
        return SourcePayload("text_file", str(path), args.platform, args.query, items_from_text(text), "copied_search_text")
    html = fetch_public_html(args.url)
    return SourcePayload("url", args.url, args.platform, args.query, items_from_html(html, args.url, args.platform), "public_static_url_fetch")


def items_from_json(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ITEM_LIST_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                return value
        for value in data.values():
            if isinstance(value, dict):
                nested = items_from_json(value)
                if len(nested) > 1:
                    return nested
        return [data]
    return [str(data)]


def items_from_html(html: str, source: str, platform: str) -> list[dict[str, Any]]:
    parser = SearchHTMLParser()
    parser.feed(html)
    base = source if source.startswith(("http://", "https://")) else ""
    candidates = []
    seen: set[str] = set()
    for link in parser.links:
        title = normalize_space(link.get("title", ""))
        if len(title) < 4:
            continue
        url = absolutize_url(link.get("url", ""), base)
        if not relevant_url(platform, url) and platform != "other":
            continue
        if is_non_content_result(platform, url, title):
            continue
        key = url or title.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"title": title, "url": url, "content": title})
    if candidates:
        return candidates
    text = normalize_space(" ".join(parser.text_blocks))
    return items_from_text(text) or [{"title": normalize_space(" ".join(parser.title_parts)), "content": text, "url": base}]


def items_from_text(text: str) -> list[dict[str, Any]]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n|^-{3,}$", text, flags=re.MULTILINE) if block.strip()]
    if len(blocks) <= 1:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        blocks = ["\n".join(lines[index : index + 6]) for index in range(0, len(lines), 6)] if lines else []
    return [item_from_text_block(block) for block in blocks if normalize_space(block)]


def item_from_text_block(block: str) -> dict[str, Any]:
    fields = parse_labeled_lines(block)
    return {
        "platform": fields.get("platform", ""),
        "title": first_non_empty(fields.get("title"), first_content_line(block)),
        "url": first_non_empty(fields.get("url"), first_url(block)),
        "creatorName": first_non_empty(fields.get("creator"), fields.get("author"), fields.get("account"), fields.get("channel")),
        "description": first_non_empty(fields.get("description"), fields.get("summary")),
        "hook": fields.get("hook", ""),
        "cta": fields.get("cta", ""),
        "content": block,
        "visibleMetrics": extract_metrics(block),
    }


def normalize_records(payload: SourcePayload, top_n: int) -> list[dict[str, Any]]:
    records = []
    for index, item in enumerate(payload.items[:top_n], start=1):
        raw = normalize_item(item, payload.platform)
        content = normalize_space(
            " ".join(
                [
                    raw.get("title", ""),
                    raw.get("description", ""),
                    raw.get("hook", ""),
                    raw.get("content", ""),
                ]
            )
        )
        metrics = {**extract_metrics(content), **normalize_metric_mapping(raw.get("visibleMetrics") or {})}
        title = first_non_empty(raw.get("title"), f"{payload.platform} search result {index}")
        url = raw.get("url", "")
        if is_non_content_result(payload.platform, url, title):
            continue
        creator = raw.get("creatorName", "")
        hook = first_non_empty(raw.get("hook"), extract_hook(content), title)
        cta = first_non_empty(raw.get("cta"), extract_cta(content))
        content_format = first_non_empty(raw.get("contentFormat"), infer_format(payload.platform, title, content))
        structure = build_structure(content, hook, cta)
        score = viral_score(metrics, index)
        records.append(
            {
                "id": f"search-result-{index:03d}",
                "platform": first_non_empty(raw.get("platform"), payload.platform),
                "query": payload.query,
                "rank": index,
                "source": {"type": payload.input_mode, "value": payload.source, "accessMode": payload.access_mode, "capturedAt": TODAY},
                "url": url,
                "creatorName": creator,
                "title": title,
                "description": raw.get("description", ""),
                "contentFormat": content_format,
                "hook": hook,
                "cta": cta,
                "contentExcerpt": trim(content, 900),
                "visibleMetrics": metrics,
                "viralSignals": {
                    "score": score,
                    "hasObservedMetrics": bool(metrics),
                    "metricFields": sorted(metrics),
                },
                "contentStructure": structure,
                "contentDeconstruction": content_deconstruction(payload.platform, content_format, title, content, hook, cta, structure, metrics),
                "reusablePatterns": reusable_patterns(title, hook, cta, metrics),
                "confidence": confidence_for_result(url, content, metrics),
                "notes": [
                    "Captured from search evidence. Verify page context before quoting.",
                    "Do not treat missing metrics as zero or infer private performance.",
                ],
            }
        )
    records.sort(key=lambda item: item["viralSignals"]["score"], reverse=True)
    for rank, record in enumerate(records, start=1):
        record["normalizedRank"] = rank
    return records


def normalize_item(item: Any, default_platform: str) -> dict[str, Any]:
    if isinstance(item, str):
        return item_from_text_block(item)
    if not isinstance(item, dict):
        return item_from_text_block(str(item))
    content = first_non_empty(
        get_alias(item, "content", "text", "body", "transcript", "caption", "note", "answer", "article"),
        json.dumps(item, ensure_ascii=False),
    )
    metrics = item.get("visibleMetrics") if isinstance(item.get("visibleMetrics"), dict) else {}
    for name in METRIC_NAMES:
        if name in item and item[name] not in (None, ""):
            metrics[name] = item[name]
    return {
        "platform": first_non_empty(get_alias(item, "platform"), default_platform),
        "url": get_alias(item, "url", "link", "href", "sourceUrl", "publishedUrl", "shareUrl"),
        "creatorName": get_alias(item, "creatorName", "creator", "author", "account", "channel", "nickname", "owner"),
        "title": get_alias(item, "title", "headline", "name", "videoTitle", "postTitle", "noteTitle"),
        "description": get_alias(item, "description", "summary", "subtitle", "excerpt"),
        "contentFormat": get_alias(item, "contentFormat", "format", "type"),
        "hook": get_alias(item, "hook", "opening"),
        "cta": get_alias(item, "cta", "callToAction"),
        "content": content,
        "visibleMetrics": metrics,
    }


def build_report(payload: SourcePayload, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "platform": payload.platform,
        "query": payload.query,
        "inputMode": payload.input_mode,
        "source": payload.source,
        "recordCount": len(records),
        "records": records,
        "aggregatePatterns": aggregate_patterns(records),
        "guardrails": [
            "Use official APIs, public pages, browser-visible snapshots, or user exports only.",
            "Do not bypass captcha, login prompts, rate limits, or platform risk controls.",
            "Do not store cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
            "Do not fabricate views, likes, comments, orders, revenue, or published URLs.",
        ],
    }


def fetch_public_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def write_report(out_dir: str, platform: str, report: dict[str, Any]) -> None:
    directory = Path(out_dir) / "reports/promotion-manager/competitors"
    directory.mkdir(parents=True, exist_ok=True)
    report_path(out_dir, platform, "json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path(out_dir, platform, "md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def report_path(out_dir: str, platform: str, suffix: str) -> Path:
    return Path(out_dir) / "reports/promotion-manager/competitors" / f"captured-search-results-{platform}.{suffix}"


def get_alias(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def query_from_data(data: Any) -> str:
    if isinstance(data, dict):
        return first_non_empty(str(data.get("query") or ""), str(data.get("keyword") or ""), str(data.get("searchTerm") or ""))
    return ""


def relevant_url(platform: str, url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
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
    return bool(url)


def is_non_content_result(platform: str, url: str, title: str = "") -> bool:
    parsed = urllib.parse.urlparse(url)
    path_parts = {part.lower() for part in parsed.path.split("/") if part}
    normalized_title = normalize_space(title).lower()
    if path_parts & NON_CONTENT_PATH_PARTS:
        return True
    if any(term in normalized_title for term in NON_CONTENT_TITLE_TERMS):
        return True
    if platform == "douyin":
        return not any(part in path_parts for part in {"video", "user", "search"}) and bool(path_parts & {"aboutus", "agreements"})
    return False


def absolutize_url(url: str, base: str) -> str:
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if base:
        return urllib.parse.urljoin(base, url)
    return url


def parse_labeled_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = normalize_space(key).lower()
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


def extract_metrics(text: str) -> dict[str, dict[str, Any]]:
    metrics = metric_parsing.extract_metrics(text, [name for name in METRIC_NAMES if name != "subscribers"] + ["watchers"])
    if "watchers" in metrics and "subscribers" not in metrics:
        metrics["subscribers"] = metrics.pop("watchers")
    return metrics


def normalize_metric_mapping(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized = {}
    for name, value in metrics.items():
        if value in (None, ""):
            continue
        if isinstance(value, dict) and "raw" in value:
            normalized[name] = value
        else:
            raw = str(value)
            normalized[name] = {"raw": raw, "normalized": parse_metric_value(raw)}
    return normalized


def parse_metric_value(value: str) -> float | None:
    return metric_parsing.parse_metric_number(value)


def viral_score(metrics: dict[str, dict[str, Any]], index: int) -> float:
    weights = {
        "views": 1.0,
        "likes": 4.0,
        "favorites": 5.0,
        "comments": 8.0,
        "shares": 8.0,
        "stars": 3.0,
        "forks": 4.0,
        "subscribers": 0.2,
    }
    score = 0.0
    for name, item in metrics.items():
        value = item.get("normalized")
        if isinstance(value, (int, float)):
            score += min(float(value), 10_000_000.0) * weights.get(name, 1.0)
    return score + max(0, 1000 - index)


def infer_format(platform: str, title: str, content: str) -> str:
    text = f"{title} {content}".lower()
    if platform == "youtube":
        return "short_video" if "shorts" in text or "#shorts" in text else "video"
    if platform in {"douyin", "tiktok"}:
        return "short_video"
    if platform == "xiaohongshu":
        return "note"
    if platform == "zhihu":
        return "article_or_answer"
    if platform == "github":
        return "repository"
    return "search_result"


def extract_hook(text: str) -> str:
    fields = parse_labeled_lines(text)
    if fields.get("hook"):
        return fields["hook"]
    for sentence in split_sentences(text):
        if len(sentence) >= 8:
            return trim(sentence, 180)
    return ""


def extract_cta(text: str) -> str:
    terms = ["try", "visit", "download", "install", "buy", "subscribe", "follow", "comment", "star", "learn more"]
    for line in text.splitlines():
        cleaned = normalize_space(line)
        lower = cleaned.lower()
        if "http://" in lower or "https://" in lower or any(term in lower for term in terms):
            return trim(cleaned, 220)
    return ""


def build_structure(text: str, hook: str, cta: str) -> list[dict[str, str]]:
    sentences = [trim(item, 220) for item in split_sentences(text)]
    structure: list[dict[str, str]] = []
    if hook:
        structure.append({"role": "hook", "text": hook})
    for label, sentence in zip(["context", "problem", "solution", "proof"], sentences[1:] if hook else sentences):
        if sentence and all(sentence != item["text"] for item in structure):
            structure.append({"role": label, "text": sentence})
        if len(structure) >= 5:
            break
    if cta:
        structure.append({"role": "cta", "text": cta})
    return structure[:6]


def reusable_patterns(title: str, hook: str, cta: str, metrics: dict[str, Any]) -> list[str]:
    patterns = []
    if "?" in title or "?" in hook:
        patterns.append("question_hook")
    if re.search(r"\d", title):
        patterns.append("numbered_title_or_claim")
    if metrics:
        patterns.append("visible_social_proof")
    if cta:
        patterns.append("explicit_call_to_action")
    return patterns or ["needs_manual_pattern_review"]


def content_deconstruction(
    platform: str,
    content_format: str,
    title: str,
    content: str,
    hook: str,
    cta: str,
    structure: list[dict[str, str]],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    roles = [item.get("role", "") for item in structure if item.get("role")]
    return {
        "summary": deconstruction_summary(platform, content_format, roles, metrics),
        "beatCount": len(structure),
        "beats": [
            {
                "order": index,
                "role": item.get("role", "unknown"),
                "function": beat_function(item.get("role", "")),
                "sourceText": item.get("text", ""),
            }
            for index, item in enumerate(structure, start=1)
        ],
        "videoArchitecture": video_architecture(platform, content_format, structure),
        "copyMechanics": copy_mechanics(title, hook, cta, metrics),
        "reuseGuidance": [
            "Reuse the observed structure and persuasion function, not the competitor wording.",
            "Treat search-result metrics as evidence only when they are visibly present in the source.",
            "Deep-capture the source page before relying on this as final competitor evidence.",
        ],
        "evidence": {
            "sourceType": "search_result_snapshot",
            "hasObservedMetrics": bool(metrics),
            "confidence": confidence_for_result("", content, metrics),
        },
    }


def deconstruction_summary(platform: str, content_format: str, roles: list[str], metrics: dict[str, Any]) -> str:
    observed = "with visible social proof" if metrics else "without visible social proof"
    role_text = " -> ".join(roles) if roles else "needs manual beat review"
    return f"{platform}/{content_format} search structure {role_text} {observed}."


def beat_function(role: str) -> str:
    functions = {
        "hook": "stop-scroll opener or curiosity trigger",
        "context": "sets the situation and audience frame",
        "problem": "names the pain point or friction",
        "solution": "shows the mechanism or promised path",
        "proof": "adds evidence, specificity, or credibility",
        "cta": "converts attention into the next action",
    }
    return functions.get(role, "requires manual interpretation")


def video_architecture(platform: str, content_format: str, structure: list[dict[str, str]]) -> list[dict[str, str]]:
    if platform not in {"youtube", "douyin", "tiktok"} and "video" not in content_format:
        return []
    windows = ["0-3s", "3-8s", "8-18s", "18-28s", "28-35s", "35s+"]
    return [
        {
            "timeWindow": window,
            "role": beat.get("role", "unknown"),
            "screenAction": screen_action_for_role(beat.get("role", "")),
            "voiceoverPurpose": beat_function(beat.get("role", "")),
        }
        for window, beat in zip(windows, structure)
    ]


def screen_action_for_role(role: str) -> str:
    actions = {
        "hook": "large claim, surprising result, or direct problem text",
        "context": "show the product/category situation or creator setup",
        "problem": "show friction, failed workflow, or before state",
        "solution": "show demo steps, transformation, or key feature",
        "proof": "show evidence, checklist, metric, repo, or testimonial source",
        "cta": "show next action, URL, comment prompt, or save/share cue",
    }
    return actions.get(role, "show supporting visual evidence")


def copy_mechanics(title: str, hook: str, cta: str, metrics: dict[str, Any]) -> list[str]:
    mechanics = []
    combined = f"{title} {hook}"
    if "?" in combined:
        mechanics.append("question_or_open_loop")
    if re.search(r"\d", combined):
        mechanics.append("number_or_specificity")
    if metrics:
        mechanics.append("visible_metric_proof")
    if cta:
        mechanics.append("explicit_conversion_prompt")
    return mechanics or ["plain_explainer_structure"]


def aggregate_patterns(records: list[dict[str, Any]]) -> dict[str, Any]:
    pattern_counts: dict[str, int] = {}
    for record in records:
        for pattern in record.get("reusablePatterns", []):
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    return {
        "recordCount": len(records),
        "recordsWithObservedMetrics": sum(1 for record in records if record.get("visibleMetrics")),
        "topTitles": [record["title"] for record in records[:5]],
        "topHooks": [record["hook"] for record in records[:5] if record.get("hook")],
        "patternCounts": dict(sorted(pattern_counts.items())),
    }


def confidence_for_result(url: str, content: str, metrics: dict[str, Any]) -> str:
    score = 0
    if url:
        score += 1
    if len(content) >= 60:
        score += 1
    if metrics:
        score += 1
    return {0: "low", 1: "medium", 2: "high", 3: "high"}[score]


def split_sentences(text: str) -> list[str]:
    return [normalize_space(item) for item in re.split(r"(?<=[.!?])\s+|[\r\n]+", text) if normalize_space(item)]


def first_non_empty(*values: str | None) -> str:
    for value in values:
        normalized = normalize_space(value or "")
        if normalized:
            return normalized
    return ""


def trim(value: str, limit: int) -> str:
    value = normalize_space(value)
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Captured Platform Search Results",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Platform: {report['platform']}",
        f"- Query: {report['query'] or 'unknown'}",
        f"- Input mode: `{report['inputMode']}`",
        f"- Records: {report['recordCount']}",
        "",
        "## Aggregate Patterns",
        f"- Records with observed metrics: {report['aggregatePatterns']['recordsWithObservedMetrics']}",
    ]
    for name, count in report["aggregatePatterns"]["patternCounts"].items():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Records"])
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['id']} - {record['title']}",
                f"- Platform: {record['platform']}",
                f"- Creator: {record['creatorName'] or 'unknown'}",
                f"- URL: {record['url'] or 'unknown'}",
                f"- Rank: {record['normalizedRank']}",
                f"- Viral score: {record['viralSignals']['score']}",
                f"- Hook: {record['hook'] or 'needs manual review'}",
                f"- CTA: {record['cta'] or 'none observed'}",
                f"- Deconstruction: {(record.get('contentDeconstruction') or {}).get('summary', 'needs review')}",
                "- Metrics:",
            ]
        )
        if record["visibleMetrics"]:
            for metric, value in record["visibleMetrics"].items():
                lines.append(f"  - {metric}: {value['raw']}")
        else:
            lines.append("  - none observed")
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
