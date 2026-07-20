#!/usr/bin/env python3
"""Collect competitor evidence through official/public connectors."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
USER_AGENT = "ViralProductPromotionSkill/1.0"


def main() -> None:
    args = parse_args()
    if args.platform == "youtube":
        report = collect_youtube(args)
    elif args.platform == "github":
        report = collect_github(args)
    else:
        report = unsupported_platform(args)
    write_report(args.out_dir, report)
    print(f"Competitor collection written to: {Path(args.out_dir).resolve() / 'reports/promotion-manager/competitors/auto-collected-competitors.json'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect competitor evidence through official/public APIs.")
    parser.add_argument("--platform", required=True, choices=["youtube", "github", "zhihu", "xiaohongshu", "douyin"])
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--region-code", default="")
    parser.add_argument("--relevance-language", default="")
    parser.add_argument("--include-readme", action="store_true", help="For GitHub, also fetch repository README text when available.")
    parser.add_argument("--youtube-search-json", help="Test fixture for YouTube search.list response.")
    parser.add_argument("--youtube-videos-json", help="Test fixture for YouTube videos.list response.")
    parser.add_argument("--youtube-channels-json", help="Test fixture for YouTube channels.list response.")
    parser.add_argument("--github-search-json", help="Test fixture for GitHub repository search response.")
    return parser.parse_args()


def collect_youtube(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key and not args.youtube_search_json:
        return base_report(
            args,
            [],
            [
                {
                    "platform": "youtube",
                    "status": "requires_env_var",
                    "requiredCredential": "YOUTUBE_API_KEY",
                    "reason": "YouTube official collection requires an API key unless fixture JSON is provided.",
                }
            ],
        )
    search_data = load_json_or_get(
        args.youtube_search_json,
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "type": "video",
            "order": "viewCount",
            "maxResults": str(min(args.top_n, 50)),
            "q": args.query,
            "key": api_key or "fixture",
            **optional_params({"regionCode": args.region_code, "relevanceLanguage": args.relevance_language}),
        },
    )
    if search_data.get("status") == "error":
        return base_report(args, [], [{"platform": "youtube", **search_data}])
    video_ids = [
        item.get("id", {}).get("videoId")
        for item in search_data.get("items", [])
        if item.get("id", {}).get("videoId")
    ][: args.top_n]
    videos_data = {"items": []}
    if video_ids:
        videos_data = load_json_or_get(
            args.youtube_videos_json,
            "https://www.googleapis.com/youtube/v3/videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids), "key": api_key or "fixture"},
        )
    if videos_data.get("status") == "error":
        return base_report(args, [], [{"platform": "youtube", **videos_data}])
    channel_ids = sorted(
        {
            item.get("snippet", {}).get("channelId")
            for item in videos_data.get("items", [])
            if item.get("snippet", {}).get("channelId")
        }
    )
    channels_data = {"items": []}
    if channel_ids:
        channels_data = load_json_or_get(
            args.youtube_channels_json,
            "https://www.googleapis.com/youtube/v3/channels",
            {"part": "snippet,statistics", "id": ",".join(channel_ids), "key": api_key or "fixture"},
        )
    if channels_data.get("status") == "error":
        return base_report(args, [], [{"platform": "youtube", **channels_data}])
    records = youtube_records(video_ids, videos_data, channels_data)
    return base_report(
        args,
        records,
        [
            {
                "platform": "youtube",
                "status": "ready",
                "source": "YouTube Data API search.list, videos.list, channels.list",
                "credentialStatus": "env_key_present" if api_key else "fixture",
            }
        ],
    )


def youtube_records(video_ids: list[str], videos_data: dict[str, Any], channels_data: dict[str, Any]) -> list[dict[str, Any]]:
    videos_by_id = {item.get("id"): item for item in videos_data.get("items", [])}
    channels_by_id = {item.get("id"): item for item in channels_data.get("items", [])}
    records = []
    for index, video_id in enumerate(video_ids, start=1):
        item = videos_by_id.get(video_id, {})
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        channel = channels_by_id.get(snippet.get("channelId"), {})
        channel_stats = channel.get("statistics", {})
        content = " ".join([snippet.get("title", ""), snippet.get("description", "")]).strip()
        metrics = {
            "views": metric_value(stats.get("viewCount")),
            "likes": metric_value(stats.get("likeCount")),
            "comments": metric_value(stats.get("commentCount")),
            "channelSubscribers": metric_value(channel_stats.get("subscriberCount")),
            "channelViews": metric_value(channel_stats.get("viewCount")),
            "channelVideos": metric_value(channel_stats.get("videoCount")),
        }
        records.append(
            competitor_record(
                index=index,
                platform="youtube",
                source_name="YouTube Data API",
                url=f"https://www.youtube.com/watch?v={video_id}",
                creator=snippet.get("channelTitle") or channel.get("snippet", {}).get("title", ""),
                title=snippet.get("title", "Untitled YouTube video"),
                description=snippet.get("description", ""),
                content=content,
                content_format="video",
                metrics=drop_empty_metrics(metrics),
                extra={
                    "contentId": video_id,
                    "publishedAt": snippet.get("publishedAt", ""),
                    "duration": item.get("contentDetails", {}).get("duration", ""),
                    "channelId": snippet.get("channelId", ""),
                    "viralSignals": viral_signals(metrics),
                },
            )
        )
    return records


def collect_github(args: argparse.Namespace) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    search_data = load_json_or_get(
        args.github_search_json,
        "https://api.github.com/search/repositories",
        {"q": args.query, "sort": "stars", "order": "desc", "per_page": str(min(args.top_n, 50))},
        headers=github_headers(token),
    )
    if search_data.get("status") == "error":
        return base_report(args, [], [{"platform": "github", **search_data}])
    records = []
    for index, item in enumerate(search_data.get("items", [])[: args.top_n], start=1):
        full_name = item.get("full_name", "")
        readme = fetch_github_readme(full_name, token) if args.include_readme and full_name and not args.github_search_json else ""
        content = " ".join([item.get("full_name", ""), item.get("description") or "", " ".join(item.get("topics") or []), readme]).strip()
        metrics = {
            "stars": metric_value(item.get("stargazers_count")),
            "forks": metric_value(item.get("forks_count")),
            "watchers": metric_value(item.get("watchers_count")),
            "openIssues": metric_value(item.get("open_issues_count")),
        }
        records.append(
            competitor_record(
                index=index,
                platform="github",
                source_name="GitHub Search REST API",
                url=item.get("html_url", ""),
                creator=(item.get("owner") or {}).get("login", ""),
                title=full_name or item.get("name", "Untitled GitHub repository"),
                description=item.get("description") or "",
                content=content,
                content_format="repository",
                metrics=drop_empty_metrics(metrics),
                extra={
                    "contentId": full_name,
                    "language": item.get("language", ""),
                    "createdAt": item.get("created_at", ""),
                    "updatedAt": item.get("updated_at", ""),
                    "topics": item.get("topics") or [],
                },
            )
        )
    return base_report(
        args,
        records,
        [
            {
                "platform": "github",
                "status": "ready",
                "source": "GitHub Search REST API",
                "credentialStatus": "token_present" if token else "no_token_public_rate_limit",
            }
        ],
    )


def unsupported_platform(args: argparse.Namespace) -> dict[str, Any]:
    task_url = {
        "zhihu": f"https://www.zhihu.com/search?type=content&q={urllib.parse.quote_plus(args.query)}",
        "xiaohongshu": f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote_plus(args.query)}",
        "douyin": f"https://www.douyin.com/search/{urllib.parse.quote(args.query, safe='')}",
    }.get(args.platform, "")
    return base_report(
        args,
        [],
        [
            {
                "platform": args.platform,
                "status": "browser_assisted_required",
                "reason": "No safe official public collection connector is implemented for this platform.",
                "searchUrl": task_url,
                "handoff": f"Save public evidence or exported text, then run scripts/competitor_intake.py --platform {args.platform}.",
            }
        ],
    )


def competitor_record(
    index: int,
    platform: str,
    source_name: str,
    url: str,
    creator: str,
    title: str,
    description: str,
    content: str,
    content_format: str,
    metrics: dict[str, dict[str, Any]],
    extra: dict[str, Any],
) -> dict[str, Any]:
    hook = extract_hook(" ".join([title, description]))
    cta = extract_cta(description)
    record = {
        "id": f"auto-competitor-{index:03d}",
        "platform": platform,
        "source": {"type": "official_or_public_api", "value": source_name, "capturedAt": TODAY},
        "url": url,
        "creatorName": creator,
        "title": title,
        "description": description,
        "contentFormat": content_format,
        "hook": hook,
        "contentExcerpt": trim(content, 900),
        "contentStructure": build_structure(content, hook, cta),
        "cta": cta,
        "visibleMetrics": metrics,
        "reusablePatterns": reusable_patterns(title, hook, cta, metrics),
        "confidence": "high" if metrics else "medium",
        "notes": [
            "Collected through official/public API connector.",
            "Treat platform metrics as observed-at-collection-time snapshots.",
        ],
    }
    record.update(extra)
    return record


def base_report(args: argparse.Namespace, records: list[dict[str, Any]], connector_status: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "query": args.query,
        "platform": args.platform,
        "topN": args.top_n,
        "records": records,
        "aggregatePatterns": aggregate_patterns(records),
        "connectorStatus": connector_status,
        "guardrails": [
            "Use official/public connectors only.",
            "Do not bypass captcha, login prompts, rate limits, or risk controls.",
            "Do not store or print API keys, cookies, passwords, OAuth tokens, or hidden browser tokens.",
            "Do not fabricate views, likes, comments, stars, orders, or revenue.",
        ],
    }


def load_json_or_get(path: str | None, url: str, params: dict[str, str], headers: dict[str, str] | None = None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value not in ("", None)})
    request = urllib.request.Request(f"{url}?{query}", headers=headers or {"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "httpStatus": exc.code, "reason": message[:500]}
    except Exception as exc:  # noqa: BLE001 - CLI connector reports and continues.
        return {"status": "error", "reason": str(exc)}


def fetch_github_readme(full_name: str, token: str) -> str:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}/readme",
        headers={**github_headers(token), "Accept": "application/vnd.github.raw"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def github_headers(token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2026-03-10",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def optional_params(values: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value}


def metric_value(value: Any) -> dict[str, Any]:
    raw = "" if value is None else str(value)
    return {"raw": raw, "normalized": parse_number(raw)}


def parse_number(value: str) -> float | None:
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def drop_empty_metrics(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {key: value for key, value in metrics.items() if value.get("raw") not in ("", None)}


def viral_signals(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    views = number_from_metric(metrics, "views")
    likes = number_from_metric(metrics, "likes")
    comments = number_from_metric(metrics, "comments")
    subscribers = number_from_metric(metrics, "channelSubscribers")
    signals: dict[str, Any] = {}
    if views and likes is not None:
        signals["likeRate"] = round(likes / views, 6)
    if views and comments is not None:
        signals["commentRate"] = round(comments / views, 6)
    if subscribers and views:
        signals["viewsPerSubscriber"] = round(views / subscribers, 6)
    return signals


def number_from_metric(metrics: dict[str, dict[str, Any]], name: str) -> float | None:
    value = metrics.get(name, {}).get("normalized")
    return float(value) if isinstance(value, (int, float)) else None


def extract_hook(text: str) -> str:
    for sentence in split_sentences(text):
        if len(sentence) >= 8:
            return trim(sentence, 180)
    return trim(text, 180)


def extract_cta(text: str) -> str:
    cta_terms = ["try", "visit", "download", "install", "buy", "subscribe", "follow", "star", "learn more"]
    for line in text.splitlines():
        cleaned = normalize_space(line)
        lower = cleaned.lower()
        if "http://" in lower or "https://" in lower or any(term in lower for term in cta_terms):
            return trim(cleaned, 220)
    return ""


def build_structure(text: str, hook: str, cta: str) -> list[dict[str, str]]:
    chunks = [trim(item, 220) for item in split_sentences(text) if item]
    structure: list[dict[str, str]] = []
    if hook:
        structure.append({"role": "hook", "text": hook})
    for label, chunk in zip(["context", "problem", "solution", "proof"], chunks[1:] if chunks else []):
        if chunk and all(chunk != item["text"] for item in structure):
            structure.append({"role": label, "text": chunk})
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


def aggregate_patterns(records: list[dict[str, Any]]) -> dict[str, Any]:
    pattern_counts: dict[str, int] = {}
    for record in records:
        for pattern in record.get("reusablePatterns", []):
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    return {
        "recordCount": len(records),
        "platforms": sorted({record["platform"] for record in records}),
        "recordsWithObservedMetrics": sum(1 for record in records if record.get("visibleMetrics")),
        "titleExamples": [record["title"] for record in records[:5]],
        "hookExamples": [record["hook"] for record in records[:5] if record.get("hook")],
        "patternCounts": dict(sorted(pattern_counts.items())),
    }


def split_sentences(text: str) -> list[str]:
    return [normalize_space(item) for item in re.split(r"(?<=[.!?])\s+|[\r\n]+", text) if normalize_space(item)]


def trim(value: str, limit: int) -> str:
    value = normalize_space(value)
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def write_report(out_dir: str, report: dict[str, Any]) -> None:
    report_dir = Path(out_dir) / "reports/promotion-manager/competitors"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "auto-collected-competitors.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report_dir / "auto-collected-competitors.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Auto-Collected Competitors",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Platform: {report['platform']}",
        f"- Query: {report['query']}",
        f"- Records: {len(report['records'])}",
        "",
        "## Connector Status",
    ]
    for status in report["connectorStatus"]:
        lines.append(f"- {status.get('platform')}: `{status.get('status')}` {status.get('reason', '')}")
    lines.extend(["", "## Records"])
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['id']} - {record['title']}",
                f"- Creator: {record['creatorName'] or 'unknown'}",
                f"- URL: {record['url'] or 'unknown'}",
                f"- Format: {record['contentFormat']}",
                f"- Hook: {record['hook'] or 'needs manual review'}",
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
