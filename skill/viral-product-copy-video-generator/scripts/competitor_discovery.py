#!/usr/bin/env python3
"""Create competitor discovery tasks and optional official API search results."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]


PLATFORM_SEARCH = {
    "youtube": {
        "searchUrl": "https://www.youtube.com/results?search_query={query}",
        "mode": "official_api_optional",
        "liveSupport": "YouTube Data API search.list if YOUTUBE_API_KEY is provided.",
        "requiredCredential": "YOUTUBE_API_KEY",
    },
    "zhihu": {
        "searchUrl": "https://www.zhihu.com/search?type=content&q={query}",
        "mode": "browser_assisted",
        "liveSupport": "Browser-assisted review or user exports; do not use private endpoints.",
        "requiredCredential": "",
    },
    "xiaohongshu": {
        "searchUrl": "https://www.xiaohongshu.com/search_result?keyword={query}",
        "mode": "browser_assisted",
        "liveSupport": "Browser-assisted review or user exports; do not bypass anti-bot controls.",
        "requiredCredential": "",
    },
    "douyin": {
        "searchUrl": "https://www.douyin.com/search/{path_query}",
        "mode": "browser_assisted",
        "liveSupport": "Browser-assisted review or official open-platform permissions where available.",
        "requiredCredential": "",
    },
    "github": {
        "searchUrl": "https://github.com/search?q={query}&type=repositories&s=stars&o=desc",
        "mode": "official_api_public",
        "liveSupport": "GitHub Search REST API can return public repositories; token optional for higher rate limits.",
        "requiredCredential": "",
    },
    "tiktok": {
        "searchUrl": "https://www.tiktok.com/search?q={query}",
        "mode": "official_api_optional",
        "liveSupport": "Use official APIs only when app access and creator authorization are available.",
        "requiredCredential": "",
    },
}


def main() -> None:
    args = parse_args()
    platforms = split_csv(args.platforms) if args.platforms else DEFAULT_PLATFORMS
    tasks = [build_task(platform, args.query, args.top_n) for platform in platforms]
    live_results = {}
    if args.live_official:
        for platform in platforms:
            live_results[platform] = live_official_search(platform, args.query, args.top_n)
    report = {
        "generatedAt": TODAY,
        "query": args.query,
        "topN": args.top_n,
        "liveOfficialSearch": args.live_official,
        "tasks": tasks,
        "liveResults": live_results,
        "nextStep": [
            "Open search tasks in a browser or review official API results.",
            "Save useful pages as HTML, JSON exports, screenshots converted to text, or copied transcripts.",
            "Feed saved evidence into scripts/competitor_intake.py.",
        ],
        "guardrails": [
            "Do not bypass captcha, login prompts, rate limits, or platform risk controls.",
            "Do not call private endpoints official APIs.",
            "Do not store or print API keys, cookies, passwords, or browser tokens.",
        ],
    }
    out_dir = Path(args.out_dir) / "reports/promotion-manager/competitors"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "competitor-discovery.json"
    md_path = out_dir / "competitor-discovery.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(f"Competitor discovery written to: {json_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate platform competitor discovery tasks.")
    parser.add_argument("--query", required=True, help="Product category, keyword, or competitor seed query.")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated platforms.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--live-official", action="store_true", help="Call official public APIs where supported.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def build_task(platform: str, query: str, top_n: int) -> dict[str, Any]:
    config = PLATFORM_SEARCH.get(platform, PLATFORM_SEARCH["youtube"])
    encoded = urllib.parse.quote_plus(query)
    path_encoded = urllib.parse.quote(query, safe="")
    search_url = config["searchUrl"].format(query=encoded, path_query=path_encoded)
    return {
        "platform": platform,
        "query": query,
        "searchUrl": search_url,
        "recommendedMode": config["mode"],
        "canRunFullyAutomatedNow": platform == "github",
        "requiredCredential": config["requiredCredential"],
        "liveSupport": config["liveSupport"],
        "targetCount": top_n,
        "captureFields": [
            "creator_or_repo",
            "title",
            "url",
            "format",
            "hook",
            "structure",
            "cta",
            "visible_metrics_if_observed",
            "why_it_works",
        ],
        "handoffCommand": (
            "python scripts/competitor_intake.py --html-file ./saved-competitor.html "
            f"--platform {platform} --out-dir ./promotion-output"
        ),
    }


def live_official_search(platform: str, query: str, top_n: int) -> dict[str, Any]:
    if platform == "github":
        return github_search(query, top_n)
    if platform == "youtube":
        return youtube_search(query, top_n)
    return {
        "status": "not_run",
        "reason": "No safe official unauthenticated search connector is implemented for this platform.",
    }


def github_search(query: str, top_n: int) -> dict[str, Any]:
    params = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": min(top_n, 20)})
    request = urllib.request.Request(
        f"https://api.github.com/search/repositories?{params}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ViralProductPromotionSkill/1.0",
        },
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - keep CLI error report compact and non-fatal.
        return {"status": "error", "reason": str(exc)}
    items = []
    for item in data.get("items", [])[:top_n]:
        items.append(
            {
                "name": item.get("full_name"),
                "url": item.get("html_url"),
                "description": item.get("description"),
                "stars": item.get("stargazers_count"),
                "forks": item.get("forks_count"),
                "language": item.get("language"),
                "updatedAt": item.get("updated_at"),
            }
        )
    return {
        "status": "ready",
        "source": "GitHub Search REST API",
        "credentialStatus": "token_present" if token else "no_token_public_rate_limit",
        "items": items,
    }


def youtube_search(query: str, top_n: int) -> dict[str, Any]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return {
            "status": "requires_env_var",
            "requiredCredential": "YOUTUBE_API_KEY",
            "reason": "YouTube Data API search requires an API key. The key is read from the environment and never written to reports.",
        }
    params = urllib.parse.urlencode(
        {
            "part": "snippet",
            "type": "video",
            "order": "viewCount",
            "maxResults": min(top_n, 25),
            "q": query,
            "key": api_key,
        }
    )
    request = urllib.request.Request(
        f"https://www.googleapis.com/youtube/v3/search?{params}",
        headers={"User-Agent": "ViralProductPromotionSkill/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - keep CLI error report compact and non-fatal.
        return {"status": "error", "reason": str(exc)}
    items = []
    for item in data.get("items", [])[:top_n]:
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        items.append(
            {
                "title": snippet.get("title"),
                "channelTitle": snippet.get("channelTitle"),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                "publishedAt": snippet.get("publishedAt"),
                "description": snippet.get("description"),
            }
        )
    return {
        "status": "ready",
        "source": "YouTube Data API search.list",
        "credentialStatus": "env_key_present",
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Competitor Discovery",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Query: {report['query']}",
        f"- Live official search: {report['liveOfficialSearch']}",
        "",
        "## Search Tasks",
    ]
    for task in report["tasks"]:
        lines.extend(
            [
                "",
                f"### {task['platform']}",
                f"- URL: {task['searchUrl']}",
                f"- Mode: `{task['recommendedMode']}`",
                f"- Fully automated now: {task['canRunFullyAutomatedNow']}",
                f"- Required credential: {task['requiredCredential'] or 'none'}",
                f"- Handoff: `{task['handoffCommand']}`",
            ]
        )
    if report["liveResults"]:
        lines.extend(["", "## Live Official Results"])
        for platform, result in report["liveResults"].items():
            lines.extend(["", f"### {platform}", f"- Status: {result.get('status')}"])
            for item in result.get("items", [])[:5]:
                label = item.get("name") or item.get("title") or item.get("url")
                lines.append(f"- {label}: {item.get('url')}")
    lines.extend(["", "## Next Step"])
    lines.extend([f"- {item}" for item in report["nextStep"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
