#!/usr/bin/env python3
"""Import competitor evidence from public pages or user-provided exports."""

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


TODAY = date.today().isoformat()
METRIC_NAMES = ["views", "likes", "favorites", "comments", "shares", "stars", "forks", "orders", "revenue"]


class CompetitorHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.current_tag = ""
        self.skip_tag = ""
        self.title_parts: list[str] = []
        self.text_blocks: list[str] = []
        self.meta: dict[str, str] = {}
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        self.current_tag = tag
        if tag == "title":
            self.in_title = True
        elif tag in {"script", "style", "noscript"}:
            self.skip_tag = tag
        elif tag == "meta":
            key = attrs_map.get("property") or attrs_map.get("name")
            content = attrs_map.get("content")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)
        elif tag == "a" and attrs_map.get("href"):
            self.links.append(attrs_map["href"])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag == self.skip_tag:
            self.skip_tag = ""
        if tag == self.current_tag:
            self.current_tag = ""

    def handle_data(self, data: str) -> None:
        if self.skip_tag:
            return
        text = normalize_space(data)
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if self.current_tag in {"h1", "h2", "h3", "p", "li", "article", "section", "div"}:
            if len(text) >= 3:
                self.text_blocks.append(text)


@dataclass
class SourcePayload:
    kind: str
    source: str
    platform: str
    items: list[Any]
    access_mode: str


def main() -> None:
    args = parse_args()
    payload = load_payload(args)
    records = normalize_records(payload)
    report = {
        "generatedAt": TODAY,
        "inputMode": payload.kind,
        "platform": payload.platform,
        "records": records,
        "aggregatePatterns": aggregate_patterns(records),
        "guardrails": [
            "Imported evidence only. Do not treat missing metrics as zero.",
            "Use public pages, official APIs, user exports, screenshots, or pasted text only.",
            "Do not bypass captcha, login prompts, risk controls, or private endpoints.",
            "Do not fabricate views, likes, comments, orders, or revenue.",
        ],
    }
    out_dir = Path(args.out_dir) / "reports/promotion-manager/competitors"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "imported-competitors.json"
    md_path = out_dir / "imported-competitors.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(f"Competitor evidence written to: {json_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import competitor content evidence into promotion reports.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public competitor URL to fetch as static HTML.")
    source.add_argument("--html-file", help="Saved competitor HTML file.")
    source.add_argument("--json-file", help="User export or structured competitor JSON file.")
    source.add_argument("--text-file", help="Pasted notes, transcript, or copied competitor page text.")
    parser.add_argument("--platform", default="auto", help="youtube, zhihu, xiaohongshu, douyin, github, tiktok, or auto.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> SourcePayload:
    if args.url:
        html = fetch_public_html(args.url)
        platform = choose_platform(args.platform, args.url)
        return SourcePayload("url", args.url, platform, [html_to_item(html, args.url, platform)], "public_url_fetch")
    if args.html_file:
        path = Path(args.html_file)
        html = path.read_text(encoding="utf-8")
        platform = choose_platform(args.platform, str(path))
        return SourcePayload("html_file", str(path), platform, [html_to_item(html, str(path), platform)], "saved_html")
    if args.json_file:
        path = Path(args.json_file)
        data = json.loads(path.read_text(encoding="utf-8"))
        items = json_to_items(data)
        platform = choose_platform(args.platform, infer_url_from_items(items) or str(path))
        return SourcePayload("json_file", str(path), platform, items, "user_export_json")
    path = Path(args.text_file)
    text = path.read_text(encoding="utf-8")
    platform = choose_platform(args.platform, first_url(text) or str(path))
    return SourcePayload("text_file", str(path), platform, [text_to_item(text, str(path), platform)], "user_provided_text")


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


def html_to_item(html: str, source: str, platform: str) -> dict[str, Any]:
    parser = CompetitorHTMLParser()
    parser.feed(html)
    title = first_non_empty(
        parser.meta.get("og:title"),
        parser.meta.get("twitter:title"),
        normalize_space(" ".join(parser.title_parts)),
    )
    description = first_non_empty(
        parser.meta.get("og:description"),
        parser.meta.get("description"),
        parser.meta.get("twitter:description"),
    )
    body_text = normalize_space(" ".join(parser.text_blocks))
    combined = normalize_space(" ".join([title, description, body_text]))
    return {
        "platform": platform,
        "url": source if source.startswith(("http://", "https://")) else first_url(combined),
        "creatorName": parser.meta.get("og:site_name") or "",
        "title": title,
        "description": description,
        "content": combined,
        "contentFormat": infer_format(platform, title, combined),
        "visibleMetrics": extract_metrics(combined),
    }


def text_to_item(text: str, source: str, platform: str) -> dict[str, Any]:
    fields = parse_labeled_lines(text)
    title = first_non_empty(fields.get("title"), first_content_line(text))
    creator = first_non_empty(fields.get("creator"), fields.get("author"), fields.get("account"), fields.get("channel"))
    url = first_non_empty(fields.get("url"), first_url(text))
    content = normalize_space(text)
    return {
        "platform": platform,
        "url": url,
        "creatorName": creator,
        "title": title,
        "description": first_non_empty(fields.get("description"), fields.get("summary")),
        "content": content,
        "contentFormat": first_non_empty(fields.get("format"), infer_format(platform, title, content)),
        "visibleMetrics": extract_metrics(content),
        "sourceFile": source,
    }


def json_to_items(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("competitors", "records", "entries", "items", "videos", "posts", "repositories"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    return [data]


def normalize_records(payload: SourcePayload) -> list[dict[str, Any]]:
    records = []
    for index, item in enumerate(payload.items, start=1):
        if isinstance(item, str):
            raw = text_to_item(item, payload.source, payload.platform)
        elif isinstance(item, dict):
            raw = normalize_mapping(item, payload.platform)
        else:
            raw = text_to_item(str(item), payload.source, payload.platform)
        platform = choose_platform(raw.get("platform") or payload.platform, raw.get("url") or payload.source)
        content = normalize_space(
            " ".join(
                [
                    str(raw.get("title") or ""),
                    str(raw.get("description") or ""),
                    str(raw.get("content") or raw.get("text") or raw.get("transcript") or raw.get("body") or ""),
                ]
            )
        )
        metrics = raw.get("visibleMetrics") if isinstance(raw.get("visibleMetrics"), dict) else {}
        metrics = {**extract_metrics(content), **normalize_metric_mapping(metrics)}
        hook = first_non_empty(str(raw.get("hook") or ""), extract_hook(content))
        cta = first_non_empty(str(raw.get("cta") or ""), extract_cta(content))
        content_format = str(raw.get("contentFormat") or infer_format(platform, str(raw.get("title") or ""), content))
        structure = build_structure(content, hook, cta)
        record = {
            "id": f"competitor-{index:03d}",
            "platform": platform,
            "source": {
                "type": payload.kind,
                "value": payload.source,
                "accessMode": payload.access_mode,
                "capturedAt": TODAY,
            },
            "url": str(raw.get("url") or ""),
            "creatorName": str(raw.get("creatorName") or ""),
            "title": str(raw.get("title") or "Untitled competitor content"),
            "description": str(raw.get("description") or ""),
            "contentFormat": content_format,
            "hook": hook,
            "contentExcerpt": trim(content, 900),
            "contentStructure": structure,
            "contentDeconstruction": content_deconstruction(platform, content_format, str(raw.get("title") or ""), content, hook, cta, structure, metrics),
            "cta": cta,
            "visibleMetrics": metrics,
            "reusablePatterns": reusable_patterns(str(raw.get("title") or ""), hook, cta, metrics),
            "confidence": confidence_for_record(content, metrics),
            "notes": [
                "Record only observed public metrics or user-provided/exported metrics.",
                "Use this as competitor evidence for deconstruction; verify before quoting in final content.",
            ],
        }
        records.append(record)
    return records


def normalize_mapping(item: dict[str, Any], default_platform: str) -> dict[str, Any]:
    content = first_non_empty(
        get_alias(item, "content", "text", "transcript", "body", "script", "postBody", "readme"),
        json.dumps(item, ensure_ascii=False),
    )
    return {
        "platform": first_non_empty(get_alias(item, "platform", "channelPlatform"), default_platform),
        "url": get_alias(item, "url", "sourceUrl", "link", "publishedUrl", "repoUrl", "htmlUrl"),
        "creatorName": get_alias(item, "creatorName", "creator", "author", "account", "channel", "repo", "owner"),
        "title": get_alias(item, "title", "headline", "name", "videoTitle", "postTitle"),
        "description": get_alias(item, "description", "summary", "subtitle"),
        "content": content,
        "contentFormat": get_alias(item, "contentFormat", "format", "type"),
        "hook": get_alias(item, "hook", "opening"),
        "cta": get_alias(item, "cta", "callToAction"),
        "visibleMetrics": {
            name: item[name] for name in METRIC_NAMES if name in item and item[name] not in (None, "")
        },
    }


def get_alias(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def choose_platform(value: str, source: str) -> str:
    if value and value != "auto":
        return value.lower()
    host = urllib.parse.urlparse(source).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "zhihu.com" in host:
        return "zhihu"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "xiaohongshu"
    if "douyin.com" in host:
        return "douyin"
    if "github.com" in host:
        return "github"
    if "tiktok.com" in host:
        return "tiktok"
    return "unknown"


def infer_url_from_items(items: list[Any]) -> str:
    for item in items:
        if isinstance(item, dict):
            url = get_alias(item, "url", "sourceUrl", "link", "publishedUrl", "repoUrl", "htmlUrl")
            if url:
                return url
        elif isinstance(item, str):
            url = first_url(item)
            if url:
                return url
    return ""


def infer_format(platform: str, title: str, content: str) -> str:
    text = f"{title} {content}".lower()
    if platform == "github":
        if "release" in text:
            return "release_or_repo_update"
        return "repository_or_readme"
    if platform == "youtube":
        if "shorts" in text or "#shorts" in text:
            return "short_video"
        return "video"
    if platform in {"douyin", "tiktok"}:
        return "short_video"
    if platform == "xiaohongshu":
        return "note"
    if platform == "zhihu":
        return "article_or_answer"
    return "unknown"


def extract_metrics(text: str) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    patterns = {
        "views": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:views?|plays?|浏览|播放|观看)",
        "likes": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:likes?|点赞)",
        "favorites": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:favorites?|saves?|收藏)",
        "comments": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:comments?|评论)",
        "shares": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:shares?|转发|分享)",
        "stars": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:stars?|星标)",
        "forks": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:forks?)",
        "orders": r"(?i)([\d,.]+\s*(?:k|m|万|千)?)\s*(?:orders?|订单)",
        "revenue": r"(?i)(?:revenue|收入|gmv)[:：]?\s*([$¥]?\s*[\d,.]+\s*(?:k|m|万|千)?)",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            raw = normalize_space(match.group(1))
            metrics[name] = {"raw": raw, "normalized": parse_metric_value(raw)}
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
    text = normalize_space(value).replace(",", "").replace("$", "").replace("¥", "")
    multiplier = 1.0
    if text.lower().endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    elif text.lower().endswith("m"):
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10_000.0
        text = text[:-1]
    elif text.endswith("千"):
        multiplier = 1_000.0
        text = text[:-1]
    try:
        return float(text.strip()) * multiplier
    except ValueError:
        return None


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
        if line and not line.lower().startswith(("url:", "creator:", "author:", "platform:", "metrics:")):
            return line
    return ""


def first_url(text: str) -> str:
    match = re.search(r"https?://[^\s)>\]\"']+", text)
    return match.group(0) if match else ""


def extract_hook(text: str) -> str:
    fields = parse_labeled_lines(text)
    if fields.get("hook"):
        return fields["hook"]
    for sentence in split_sentences(text):
        cleaned = normalize_space(sentence)
        if len(cleaned) >= 8:
            return trim(cleaned, 180)
    return ""


def extract_cta(text: str) -> str:
    cta_terms = [
        "try",
        "visit",
        "download",
        "install",
        "buy",
        "order",
        "subscribe",
        "follow",
        "comment",
        "star",
        "join",
        "link in bio",
        "learn more",
    ]
    lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
    for line in lines:
        lower = line.lower()
        if "http://" in lower or "https://" in lower or any(term in lower for term in cta_terms):
            return trim(line, 220)
    return ""


def build_structure(text: str, hook: str, cta: str) -> list[dict[str, str]]:
    sentences = [trim(item, 220) for item in split_sentences(text) if normalize_space(item)]
    structure: list[dict[str, str]] = []
    if hook:
        structure.append({"role": "hook", "text": hook})
    labels = ["context", "problem", "solution", "proof"]
    for label, sentence in zip(labels, sentences[1:] if hook and sentences else sentences):
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
    if not patterns:
        patterns.append("needs_manual_pattern_review")
    return patterns


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
            "Reuse the beat order and persuasion function, not the competitor wording.",
            "Keep all performance metrics attached to source evidence; do not transfer them into product claims.",
            "Adapt hook, proof, and CTA to the promoted product's factual page evidence.",
        ],
        "evidence": {
            "sourceType": "public_page_or_user_export",
            "hasObservedMetrics": bool(metrics),
            "confidence": confidence_for_record(content, metrics),
        },
    }


def deconstruction_summary(platform: str, content_format: str, roles: list[str], metrics: dict[str, Any]) -> str:
    observed = "with visible social proof" if metrics else "without visible social proof"
    role_text = " -> ".join(roles) if roles else "needs manual beat review"
    return f"{platform}/{content_format} structure {role_text} {observed}."


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
    architecture = []
    for window, beat in zip(windows, structure):
        architecture.append(
            {
                "timeWindow": window,
                "role": beat.get("role", "unknown"),
                "screenAction": screen_action_for_role(beat.get("role", "")),
                "voiceoverPurpose": beat_function(beat.get("role", "")),
            }
        )
    return architecture


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
    titles = [record["title"] for record in records if record.get("title")]
    hooks = [record["hook"] for record in records if record.get("hook")]
    ctas = [record["cta"] for record in records if record.get("cta")]
    metric_records = [record for record in records if record.get("visibleMetrics")]
    pattern_counts: dict[str, int] = {}
    for record in records:
        for pattern in record.get("reusablePatterns", []):
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    return {
        "recordCount": len(records),
        "platforms": sorted({record["platform"] for record in records}),
        "titleExamples": titles[:5],
        "hookExamples": hooks[:5],
        "ctaExamples": ctas[:5],
        "recordsWithObservedMetrics": len(metric_records),
        "patternCounts": dict(sorted(pattern_counts.items())),
        "nextUse": "Feed these records into content generation and cheat-on-content review; keep metrics evidence-linked.",
    }


def confidence_for_record(content: str, metrics: dict[str, Any]) -> str:
    score = 0
    if len(content) >= 80:
        score += 1
    if metrics:
        score += 1
    if first_url(content):
        score += 1
    return {0: "low", 1: "medium", 2: "high", 3: "high"}[score]


def split_sentences(text: str) -> list[str]:
    return [item for item in re.split(r"(?<=[.!?。！？])\s+|[\r\n]+", text) if normalize_space(item)]


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
        "# Imported Competitor Evidence",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Input mode: `{report['inputMode']}`",
        f"- Records: {len(report['records'])}",
        "",
        "## Aggregate Patterns",
        "",
        f"- Platforms: {', '.join(report['aggregatePatterns']['platforms'])}",
        f"- Records with observed metrics: {report['aggregatePatterns']['recordsWithObservedMetrics']}",
    ]
    for name, count in report["aggregatePatterns"]["patternCounts"].items():
        lines.append(f"- {name}: {count}")
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"## {record['id']} - {record['platform']}",
                f"- Title: {record['title']}",
                f"- Creator: {record['creatorName'] or 'unknown'}",
                f"- URL: {record['url'] or 'unknown'}",
                f"- Format: {record['contentFormat']}",
                f"- Hook: {record['hook'] or 'needs manual review'}",
                f"- CTA: {record['cta'] or 'none observed'}",
                f"- Confidence: {record['confidence']}",
                "- Metrics:",
            ]
        )
        if record["visibleMetrics"]:
            for metric, value in record["visibleMetrics"].items():
                lines.append(f"  - {metric}: {value['raw']}")
        else:
            lines.append("  - none observed")
        lines.append("- Structure:")
        for item in record["contentStructure"]:
            lines.append(f"  - {item['role']}: {item['text']}")
        deconstruction = record.get("contentDeconstruction") or {}
        if deconstruction:
            lines.append(f"- Deconstruction: {deconstruction.get('summary', 'needs review')}")
            for beat in deconstruction.get("beats", [])[:6]:
                lines.append(f"  - {beat.get('role', 'unknown')}: {beat.get('function', '')}")
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
