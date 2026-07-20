#!/usr/bin/env python3
"""Import real publication metrics from exports or official public APIs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import metric_parsing

TODAY = date.today().isoformat()
METRIC_FIELDS = metric_parsing.METRIC_FIELDS
METRIC_EXPORT_ALIASES = {
    "views": ["view", "viewCount", "view_count", "playCount", "play_count", "readCount", "read_count", "impressions", "impressionCount", "impression_count"],
    "likes": ["like", "likeCount", "like_count", "diggCount", "digg_count"],
    "favorites": ["favoriteCount", "favorite_count", "saveCount", "save_count", "collectCount", "collect_count", "bookmarkCount", "bookmark_count"],
    "comments": ["commentCount", "comment_count", "replyCount", "reply_count"],
    "shares": ["shareCount", "share_count", "repostCount", "repost_count"],
    "clicks": ["clickCount", "click_count", "linkClicks", "link_clicks", "websiteClicks", "website_clicks"],
    "messages": ["messageCount", "message_count", "dmCount", "dm_count", "consultCount", "consult_count"],
    "leads": ["leadCount", "lead_count", "signupCount", "signup_count", "registrations", "registrationCount", "registration_count"],
    "orders": ["orderCount", "order_count", "purchaseCount", "purchase_count", "paidOrders", "paid_orders"],
    "revenue": ["amount", "paidAmount", "paid_amount", "orderTotal", "order_total", "totalRevenue", "total_revenue", "salesAmount", "sales_amount", "gmv"],
    "stars": ["starCount", "star_count", "stargazers", "stargazersCount", "stargazers_count"],
    "forks": ["forkCount", "fork_count", "forksCount", "forks_count"],
    "watchers": ["watcherCount", "watcher_count", "watchersCount", "watchers_count", "subscriberCount", "subscriber_count", "followers", "followerCount", "follower_count"],
    "openIssues": ["openIssueCount", "open_issue_count", "openIssuesCount", "open_issues_count"],
}
CHINESE_METRIC_EXPORT_ALIASES = {
    "views": ["\u64ad\u653e\u91cf", "\u64ad\u653e\u6b21\u6570", "\u89c2\u770b\u91cf", "\u89c2\u770b\u6b21\u6570", "\u6d4f\u89c8\u91cf", "\u9605\u8bfb\u91cf", "\u66dd\u5149\u91cf", "\u5c55\u73b0\u91cf", "\u5c55\u793a\u91cf"],
    "likes": ["\u70b9\u8d5e", "\u70b9\u8d5e\u6570", "\u70b9\u8d5e\u91cf", "\u83b7\u8d5e\u6570", "\u559c\u6b22\u6570"],
    "favorites": ["\u6536\u85cf", "\u6536\u85cf\u6570", "\u6536\u85cf\u91cf", "\u4fdd\u5b58\u6570"],
    "comments": ["\u8bc4\u8bba", "\u8bc4\u8bba\u6570", "\u7559\u8a00\u6570", "\u56de\u590d\u6570"],
    "shares": ["\u5206\u4eab", "\u5206\u4eab\u6570", "\u8f6c\u53d1", "\u8f6c\u53d1\u6570"],
    "clicks": ["\u70b9\u51fb", "\u70b9\u51fb\u6570", "\u5b98\u7f51\u70b9\u51fb", "\u94fe\u63a5\u70b9\u51fb", "\u8bbf\u95ee\u91cf"],
    "messages": ["\u79c1\u4fe1\u6570", "\u54a8\u8be2\u6570", "\u4f1a\u8bdd\u6570"],
    "leads": ["\u7ebf\u7d22\u6570", "\u7559\u8d44\u6570", "\u6ce8\u518c\u6570"],
    "orders": ["\u8ba2\u5355\u6570", "\u6210\u4ea4\u8ba2\u5355", "\u6210\u4ea4\u8ba2\u5355\u6570", "\u652f\u4ed8\u8ba2\u5355", "\u652f\u4ed8\u8ba2\u5355\u6570"],
    "revenue": ["\u6210\u4ea4\u91d1\u989d", "\u6210\u4ea4\u989d", "\u4ea4\u6613\u989d", "\u9500\u552e\u989d", "\u9500\u552e\u91d1\u989d", "\u6536\u5165", "\u8425\u6536"],
    "stars": ["\u661f\u6807\u6570"],
    "forks": ["fork\u6570", "\u590d\u523b\u6570"],
    "watchers": ["\u5173\u6ce8\u8005\u6570", "\u8ba2\u9605\u6570", "\u7c89\u4e1d\u6570"],
    "openIssues": ["\u5f85\u5904\u7406\u95ee\u9898\u6570", "\u95ee\u9898\u6570"],
}
for field, aliases in CHINESE_METRIC_EXPORT_ALIASES.items():
    METRIC_EXPORT_ALIASES.setdefault(field, []).extend(aliases)

PLATFORM_ALIASES = ("platform", "\u5e73\u53f0", "\u6e20\u9053", "\u6765\u6e90")
URL_ALIASES = ("publishedUrl", "url", "canonicalUrl", "link", "sourceUrl", "\u53d1\u5e03\u94fe\u63a5", "\u5185\u5bb9\u94fe\u63a5", "\u94fe\u63a5", "\u5730\u5740")
CONTENT_ID_ALIASES = ("contentId", "videoId", "repo", "id", "noteId", "\u5185\u5bb9id", "\u5185\u5bb9ID", "\u89c6\u9891id", "\u89c6\u9891ID", "\u7b14\u8bb0id", "\u7b14\u8bb0ID")
TITLE_ALIASES = ("title", "name", "headline", "\u6807\u9898", "\u5185\u5bb9\u6807\u9898", "\u4f5c\u54c1\u6807\u9898")
DATE_ALIASES = ("publishedAt", "date", "createdAt", "capturedAt", "\u53d1\u5e03\u65f6\u95f4", "\u53d1\u5e03\u65e5\u671f", "\u65e5\u671f", "\u65f6\u95f4")
EVIDENCE_ALIASES = ("evidence", "evidenceUrl", "screenshot", "screenshotPath", "export", "\u8bc1\u636e", "\u622a\u56fe", "\u622a\u56fe\u94fe\u63a5", "\u5bfc\u51fa\u6587\u4ef6", "\u6570\u636e\u6765\u6e90")
PLATFORM_VALUE_ALIASES = {
    "youtube": "youtube",
    "yt": "youtube",
    "\u6cb9\u7ba1": "youtube",
    "github": "github",
    "zhihu": "zhihu",
    "\u77e5\u4e4e": "zhihu",
    "xiaohongshu": "xiaohongshu",
    "xhs": "xiaohongshu",
    "\u5c0f\u7ea2\u4e66": "xiaohongshu",
    "douyin": "douyin",
    "\u6296\u97f3": "douyin",
    "tiktok": "tiktok",
}


def main() -> None:
    args = parse_args()
    payload = load_payload(args)
    report = build_report(payload)
    out_dir = Path(args.out_dir) / "reports/promotion-manager/metrics"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "imported-metrics.json"
    md_path = out_dir / "imported-metrics.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(f"Metrics report written to: {json_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import real publication metrics for retrospective analysis.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv-file", help="CSV export with platform/url/metric columns.")
    source.add_argument("--xlsx-file", help="Excel .xlsx export with platform/url/metric columns.")
    source.add_argument("--json-file", help="JSON export with metric records.")
    source.add_argument("--text-file", help="Copied metric text, notes, or transcript.")
    source.add_argument("--structured-json", help="Codex/browser structured snapshot containing a published page or analytics text.")
    source.add_argument("--published-url", help="Published URL to resolve through a supported official connector.")
    source.add_argument("--github-repo", help="GitHub repository in owner/name form.")
    source.add_argument("--youtube-video-id", help="YouTube video ID. Requires YOUTUBE_API_KEY.")
    parser.add_argument("--platform", default="auto")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.csv_file:
        path = Path(args.csv_file)
        return {"inputMode": "csv_file", "source": str(path), "records": records_from_csv(path), "connectorStatus": []}
    if args.xlsx_file:
        path = Path(args.xlsx_file)
        return {"inputMode": "xlsx_file", "source": str(path), "records": records_from_xlsx(path), "connectorStatus": []}
    if args.json_file:
        path = Path(args.json_file)
        return {"inputMode": "json_file", "source": str(path), "records": records_from_json(path), "connectorStatus": []}
    if args.text_file:
        path = Path(args.text_file)
        return {"inputMode": "text_file", "source": str(path), "records": [record_from_text(path.read_text(encoding="utf-8"), str(path), args.platform)], "connectorStatus": []}
    if args.structured_json:
        path = Path(args.structured_json)
        return {"inputMode": "structured_json", "source": str(path), "records": records_from_structured_json(path, args.platform), "connectorStatus": []}
    if args.github_repo:
        record, status = record_from_github_repo(args.github_repo)
        return {"inputMode": "github_repo", "source": args.github_repo, "records": [record] if record else [], "connectorStatus": [status]}
    if args.youtube_video_id:
        record, status = record_from_youtube_video(args.youtube_video_id)
        return {"inputMode": "youtube_video_id", "source": args.youtube_video_id, "records": [record] if record else [], "connectorStatus": [status]}
    return load_from_published_url(args.published_url, args.platform)


def load_from_published_url(url: str, platform: str) -> dict[str, Any]:
    detected = choose_platform(platform, url)
    if detected == "github":
        repo = github_repo_from_url(url)
        if repo:
            record, status = record_from_github_repo(repo, url)
            return {"inputMode": "published_url", "source": url, "records": [record] if record else [], "connectorStatus": [status]}
    if detected == "youtube":
        video_id = youtube_video_id_from_url(url)
        if video_id:
            record, status = record_from_youtube_video(video_id, url)
            return {"inputMode": "published_url", "source": url, "records": [record] if record else [], "connectorStatus": [status]}
    return {
        "inputMode": "published_url",
        "source": url,
        "records": [],
        "connectorStatus": [
            {
                "platform": detected,
                "status": "unsupported",
                "reason": "No safe official metrics connector is implemented for this URL. Use CSV, JSON, or text export.",
            }
        ],
    }


def records_from_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [normalize_mapping(row, str(path)) for row in csv.DictReader(handle)]


def records_from_xlsx(path: Path) -> list[dict[str, Any]]:
    rows = xlsx_rows(path)
    if not rows:
        return []
    headers = [str(value).strip() for value in rows[0]]
    records = []
    for row in rows[1:]:
        if not any(str(value).strip() for value in row):
            continue
        item = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers) if header}
        records.append(normalize_mapping(item, str(path)))
    return records


def xlsx_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = xlsx_shared_strings(workbook)
        sheet_name = xlsx_first_sheet_name(workbook)
        root = ET.fromstring(workbook.read(sheet_name))
    rows = []
    for row in root.findall(".//{*}sheetData/{*}row"):
        values: dict[int, str] = {}
        for cell in row.findall("{*}c"):
            ref = cell.attrib.get("r", "")
            index = xlsx_column_index(ref) if ref else len(values)
            values[index] = xlsx_cell_value(cell, shared_strings)
        if values:
            width = max(values) + 1
            rows.append([values.get(index, "") for index in range(width)])
    return rows


def xlsx_first_sheet_name(workbook: zipfile.ZipFile) -> str:
    names = workbook.namelist()
    if "xl/worksheets/sheet1.xml" in names:
        return "xl/worksheets/sheet1.xml"
    candidates = sorted(name for name in names if name.startswith("xl/worksheets/") and name.endswith(".xml"))
    if not candidates:
        raise ValueError("No worksheet XML found in .xlsx file.")
    return candidates[0]


def xlsx_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("{*}si"):
        parts = [node.text or "" for node in item.findall(".//{*}t")]
        strings.append("".join(parts))
    return strings


def xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//{*}is/{*}t"))
    value_node = cell.find("{*}v")
    if value_node is None or value_node.text is None:
        return ""
    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return value
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    return value


def xlsx_column_index(ref: str) -> int:
    letters = "".join(char for char in ref if char.isalpha())
    index = 0
    for char in letters.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return max(index - 1, 0)


def records_from_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("records", "items", "metrics", "results", "publishedItems"):
            value = data.get(key)
            if isinstance(value, list):
                return [normalize_mapping(item, str(path)) if isinstance(item, dict) else record_from_text(str(item), str(path), "auto") for item in value]
        return [normalize_mapping(data, str(path))]
    if isinstance(data, list):
        return [normalize_mapping(item, str(path)) if isinstance(item, dict) else record_from_text(str(item), str(path), "auto") for item in data]
    return [record_from_text(str(data), str(path), "auto")]


def records_from_structured_json(path: Path, platform: str = "auto") -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        for key in ("records", "items", "metrics", "results", "publishedItems"):
            value = data.get(key)
            if isinstance(value, list):
                return [
                    record_from_structured_mapping(item, str(path), platform) if isinstance(item, dict) else record_from_text(str(item), str(path), platform)
                    for item in value
                ]
        return [record_from_structured_mapping(data, str(path), platform)]
    if isinstance(data, list):
        return [
            record_from_structured_mapping(item, str(path), platform) if isinstance(item, dict) else record_from_text(str(item), str(path), platform)
            for item in data
        ]
    return [record_from_text(str(data), str(path), platform)]


def record_from_structured_mapping(item: dict[str, Any], source: str, platform: str) -> dict[str, Any]:
    url = get_alias(item, *URL_ALIASES)
    detected = choose_platform(first_non_empty(get_alias(item, *PLATFORM_ALIASES), platform), url or source)
    text = structured_text(item)
    metrics = extract_metrics(text)
    for key in ("metrics", "visibleMetrics", "analytics", "stats", "statistics"):
        value = item.get(key)
        if isinstance(value, dict):
            metrics.update(metrics_from_mapping(value))
    evidence = split_evidence(get_alias(item, *EVIDENCE_ALIASES))
    if source and source not in evidence:
        evidence.append(source)
    return {
        "platform": detected,
        "publishedUrl": url,
        "contentId": get_alias(item, *CONTENT_ID_ALIASES),
        "title": get_alias(item, *TITLE_ALIASES) or first_content_line(text),
        "publishedAt": get_alias(item, *DATE_ALIASES),
        "metrics": metrics,
        "evidence": evidence,
        "source": {"type": "structured_snapshot", "value": source, "capturedAt": get_alias(item, "capturedAt") or TODAY},
        "notes": [get_alias(item, "notes", "note")],
    }


def structured_text(item: dict[str, Any]) -> str:
    parts = []
    for key in ("title", "description", "text", "renderedText", "visibleText", "bodyText", "content", "markdown"):
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(entry) for entry in value)
    for key in ("headings", "captions", "comments", "sections"):
        value = item.get(key)
        if isinstance(value, list):
            parts.extend(json.dumps(entry, ensure_ascii=False) if isinstance(entry, (dict, list)) else str(entry) for entry in value)
    return "\n".join(part for part in parts if part)


def metrics_from_mapping(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics = {}
    for field in METRIC_FIELDS:
        value = metric_field_value(item, field)
        if isinstance(value, dict):
            value = first_non_empty(value.get("raw"), value.get("value"), value.get("normalized"))
        if value not in (None, ""):
            metrics[field] = metric_value(value)
    return metrics


def normalize_mapping(item: dict[str, Any], source: str) -> dict[str, Any]:
    url = get_alias(item, *URL_ALIASES)
    platform = choose_platform(get_alias(item, *PLATFORM_ALIASES), url or source)
    metrics = {}
    for field in METRIC_FIELDS:
        value = metric_field_value(item, field)
        if value:
            metrics[field] = metric_value(value)
    evidence = split_evidence(get_alias(item, *EVIDENCE_ALIASES))
    if source and source not in evidence:
        evidence.append(source)
    return {
        "platform": platform,
        "publishedUrl": url,
        "contentId": get_alias(item, *CONTENT_ID_ALIASES),
        "title": get_alias(item, *TITLE_ALIASES),
        "publishedAt": get_alias(item, *DATE_ALIASES),
        "metrics": metrics,
        "evidence": evidence,
        "source": {"type": "user_export", "value": source, "capturedAt": TODAY},
        "notes": [get_alias(item, "notes", "note")],
    }


def record_from_text(text: str, source: str, platform: str) -> dict[str, Any]:
    fields = parse_labeled_lines(text)
    url = first_non_empty(fields.get("publishedurl"), fields.get("url"), first_url(text))
    detected = choose_platform(platform, url or source)
    metrics = extract_metrics(text)
    evidence = split_evidence(first_non_empty(fields.get("evidence"), fields.get("screenshot"), fields.get("export")))
    if source and source not in evidence:
        evidence.append(source)
    return {
        "platform": detected,
        "publishedUrl": url,
        "contentId": first_non_empty(fields.get("contentid"), fields.get("videoid"), fields.get("repo")),
        "title": first_non_empty(fields.get("title"), first_content_line(text)),
        "publishedAt": first_non_empty(fields.get("publishedat"), fields.get("date")),
        "metrics": metrics,
        "evidence": evidence,
        "source": {"type": "user_text", "value": source, "capturedAt": TODAY},
        "notes": [first_non_empty(fields.get("notes"), fields.get("note"))],
    }


def record_from_github_repo(repo: str, source_url: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    repo = repo.strip().removeprefix("https://github.com/").strip("/")
    if "/" not in repo:
        return None, {"platform": "github", "status": "error", "reason": "GitHub repo must be owner/name."}
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ViralProductPromotionSkill/1.0",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI connector should report and continue.
        return None, {"platform": "github", "status": "error", "reason": str(exc)}
    record = {
        "platform": "github",
        "publishedUrl": source_url or data.get("html_url") or f"https://github.com/{repo}",
        "contentId": data.get("full_name") or repo,
        "title": data.get("full_name") or repo,
        "publishedAt": data.get("created_at") or "",
        "metrics": {
            "stars": metric_value(data.get("stargazers_count")),
            "forks": metric_value(data.get("forks_count")),
            "watchers": metric_value(data.get("subscribers_count") or data.get("watchers_count")),
            "openIssues": metric_value(data.get("open_issues_count")),
        },
        "evidence": [f"https://api.github.com/repos/{repo}", data.get("html_url") or f"https://github.com/{repo}"],
        "source": {
            "type": "official_api",
            "value": "GitHub REST API get repository",
            "capturedAt": TODAY,
        },
        "notes": ["Public repository metrics. openIssues may include pull requests in GitHub repository responses."],
    }
    return record, {
        "platform": "github",
        "status": "ready",
        "source": "GitHub REST API get repository",
        "credentialStatus": "token_present" if token else "no_token_public_resource",
    }


def record_from_youtube_video(video_id: str, source_url: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return None, {
            "platform": "youtube",
            "status": "requires_env_var",
            "requiredCredential": "YOUTUBE_API_KEY",
            "reason": "YouTube Data API videos.list statistics requires an API key. The key is read from the environment and never written to reports.",
        }
    params = urllib.parse.urlencode({"part": "snippet,statistics", "id": video_id, "key": api_key})
    request = urllib.request.Request(
        f"https://www.googleapis.com/youtube/v3/videos?{params}",
        headers={"User-Agent": "ViralProductPromotionSkill/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI connector should report and continue.
        return None, {"platform": "youtube", "status": "error", "reason": str(exc)}
    items = data.get("items") or []
    if not items:
        return None, {"platform": "youtube", "status": "not_found", "reason": "No video returned for the supplied ID."}
    item = items[0]
    stats = item.get("statistics", {})
    snippet = item.get("snippet", {})
    record = {
        "platform": "youtube",
        "publishedUrl": source_url or f"https://www.youtube.com/watch?v={video_id}",
        "contentId": video_id,
        "title": snippet.get("title") or "",
        "publishedAt": snippet.get("publishedAt") or "",
        "metrics": {
            "views": metric_value(stats.get("viewCount")),
            "likes": metric_value(stats.get("likeCount")),
            "favorites": metric_value(stats.get("favoriteCount")),
            "comments": metric_value(stats.get("commentCount")),
        },
        "evidence": [f"https://www.googleapis.com/youtube/v3/videos?id={video_id}", source_url or f"https://www.youtube.com/watch?v={video_id}"],
        "source": {"type": "official_api", "value": "YouTube Data API videos.list", "capturedAt": TODAY},
        "notes": ["favoriteCount is deprecated by YouTube and may always be 0."],
    }
    return record, {"platform": "youtube", "status": "ready", "source": "YouTube Data API videos.list", "credentialStatus": "env_key_present"}


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    records = []
    for index, raw in enumerate(payload["records"], start=1):
        metrics = {name: value for name, value in raw.get("metrics", {}).items() if value.get("raw") not in ("", None)}
        record = {
            "id": f"metric-{index:03d}",
            "platform": raw.get("platform") or "unknown",
            "publishedUrl": raw.get("publishedUrl") or "",
            "contentId": raw.get("contentId") or "",
            "title": raw.get("title") or "Untitled published item",
            "publishedAt": raw.get("publishedAt") or "",
            "metrics": metrics,
            "derived": derived_metrics(metrics),
            "evidence": [item for item in raw.get("evidence", []) if item],
            "source": raw.get("source") or {},
            "confidence": confidence_for_record(metrics, raw.get("evidence", [])),
            "notes": [item for item in raw.get("notes", []) if item],
        }
        records.append(record)
    aggregates = aggregate_records(records)
    return {
        "generatedAt": TODAY,
        "inputMode": payload["inputMode"],
        "source": payload["source"],
        "records": records,
        "aggregates": aggregates,
        "connectorStatus": payload.get("connectorStatus", []),
        "retrospective": build_retrospective(records, aggregates),
        "guardrails": [
            "Use only official API responses, platform exports, screenshots, or user-provided evidence.",
            "Do not treat missing metrics as zero.",
            "Do not fabricate views, likes, comments, orders, revenue, or published URLs.",
            "Do not store or print cookies, passwords, API keys, or browser tokens.",
        ],
    }


def derived_metrics(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    views = metric_number(metrics, "views")
    likes = metric_number(metrics, "likes")
    favorites = metric_number(metrics, "favorites")
    comments = metric_number(metrics, "comments")
    shares = metric_number(metrics, "shares")
    clicks = metric_number(metrics, "clicks")
    leads = metric_number(metrics, "leads")
    orders = metric_number(metrics, "orders")
    revenue = metric_number(metrics, "revenue")
    derived: dict[str, Any] = {}
    engagement = sum(value for value in [likes, favorites, comments, shares] if value is not None)
    if views and engagement:
        derived["engagementRate"] = round(engagement / views, 6)
    if views and clicks is not None:
        derived["clickThroughRate"] = round(clicks / views, 6)
    if clicks and leads is not None:
        derived["leadConversionRate"] = round(leads / clicks, 6)
    if clicks and orders is not None:
        derived["orderConversionRate"] = round(orders / clicks, 6)
    if views and revenue is not None:
        derived["revenuePerView"] = round(revenue / views, 6)
    return derived


def aggregate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, float] = {}
    field_counts: dict[str, int] = {}
    for field in METRIC_FIELDS:
        values = [metric_number(record["metrics"], field) for record in records]
        values = [value for value in values if value is not None]
        if values:
            totals[field] = sum(values)
            field_counts[field] = len(values)
    return {
        "recordCount": len(records),
        "recordsWithMetrics": sum(1 for record in records if record["metrics"]),
        "recordsWithEvidence": sum(1 for record in records if record["evidence"]),
        "totals": totals,
        "metricFields": sorted(field_counts),
        "metricFieldCounts": field_counts,
        "bestByViews": best_record(records, "views"),
        "bestByRevenue": best_record(records, "revenue"),
        "platforms": sorted({record["platform"] for record in records}),
    }


def best_record(records: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    candidates = []
    for record in records:
        value = metric_number(record["metrics"], metric)
        if value is not None:
            candidates.append((value, record))
    if not candidates:
        return None
    value, record = max(candidates, key=lambda item: item[0])
    return {"id": record["id"], "platform": record["platform"], "title": record["title"], "value": value}


def build_retrospective(records: list[dict[str, Any]], aggregates: dict[str, Any]) -> dict[str, Any]:
    if not records or not any(record["metrics"] for record in records):
        return {
            "status": "waiting_real_data",
            "bestPerformingContent": None,
            "commercialResult": None,
            "insights": [],
            "nextRoundActions": ["Import real platform metrics, official API data, or business export data before optimizing."],
        }
    insights = []
    if aggregates.get("bestByViews"):
        insights.append(f"Highest observed reach: {aggregates['bestByViews']['title']} on {aggregates['bestByViews']['platform']}.")
    if aggregates.get("bestByRevenue"):
        insights.append(f"Highest observed revenue: {aggregates['bestByRevenue']['title']} on {aggregates['bestByRevenue']['platform']}.")
    totals = aggregates.get("totals", {})
    if totals.get("orders") is not None or totals.get("revenue") is not None:
        insights.append("Commercial metrics are present; compare revenue/order outcomes before increasing posting volume.")
    return {
        "status": "ready",
        "bestPerformingContent": aggregates.get("bestByViews") or aggregates.get("bestByRevenue"),
        "commercialResult": {
            "orders": totals.get("orders"),
            "revenue": totals.get("revenue"),
            "leads": totals.get("leads"),
        },
        "insights": insights,
        "nextRoundActions": [
            "Reuse the strongest observed hook in one new variant.",
            "Keep platform-specific metrics separated; do not compare views to revenue without click/order evidence.",
            "Feed this report into cheat-on-content retrospective only after evidence URLs or exports are attached.",
        ],
    }


def extract_metrics(text: str) -> dict[str, dict[str, Any]]:
    metrics = {}
    aliases = {
        "views": r"(?:views?|播放|浏览|观看)",
        "likes": r"(?:likes?|点赞)",
        "favorites": r"(?:favorites?|saves?|收藏)",
        "comments": r"(?:comments?|评论)",
        "shares": r"(?:shares?|转发|分享)",
        "clicks": r"(?:clicks?|点击)",
        "messages": r"(?:messages?|私信|咨询)",
        "leads": r"(?:leads?|线索)",
        "orders": r"(?:orders?|订单)",
        "revenue": r"(?:revenue|收入|gmv|sales)",
        "stars": r"(?:stars?|星标)",
        "forks": r"(?:forks?)",
        "watchers": r"(?:watchers?|subscribers?)",
    }
    for field, label in aliases.items():
        pattern_after = rf"(?i){label}\s*[:：]?\s*([$¥]?\s*[\d,.]+\s*(?:k|m|万|千)?)"
        pattern_before = rf"(?i)([$¥]?\s*[\d,.]+\s*(?:k|m|万|千)?)\s*{label}"
        match = re.search(pattern_after, text) or re.search(pattern_before, text)
        if match:
            metrics[field] = metric_value(match.group(1))
    return metrics


def metric_value(value: Any) -> dict[str, Any]:
    raw = "" if value is None else str(value).strip()
    return {"raw": raw, "normalized": parse_metric_number(raw)}


def metric_number(metrics: dict[str, dict[str, Any]], field: str) -> float | None:
    item = metrics.get(field)
    if not item:
        return None
    value = item.get("normalized")
    return float(value) if isinstance(value, (int, float)) else None


def parse_metric_number(value: str) -> float | None:
    text = str(value).strip().replace(",", "").replace("$", "").replace("¥", "")
    if not text:
        return None
    multiplier = 1.0
    lower = text.lower()
    if lower.endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    elif lower.endswith("m"):
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


# Browser snapshots and analytics screenshots often contain current English or Chinese
# labels. Keep these definitions after the legacy parser so they override it.
def extract_metrics(text: str) -> dict[str, dict[str, Any]]:
    metrics = {}
    aliases = {
        "views": r"(?:views?|plays?|impressions?|播放量|播放|浏览量|浏览|观看量|观看|曝光)",
        "likes": r"(?:likes?|点赞|赞)",
        "favorites": r"(?:favorites?|saves?|收藏|保存)",
        "comments": r"(?:comments?|评论)",
        "shares": r"(?:shares?|转发|分享)",
        "clicks": r"(?:clicks?|点击|访问)",
        "messages": r"(?:messages?|私信|咨询|会话)",
        "leads": r"(?:leads?|线索|留资)",
        "orders": r"(?:orders?|订单)",
        "revenue": r"(?:revenue|gmv|sales|收入|销售额|成交额)",
        "stars": r"(?:stars?|星标)",
        "forks": r"(?:forks?)",
        "watchers": r"(?:watchers?|subscribers?)",
    }
    number = r"([$¥￥]?\s*[\d,.]+(?:\.\d+)?\s*(?:k|m|万|千)?)"
    for field, label in aliases.items():
        pattern_after = rf"{label}\s*[:：]?\s*{number}"
        pattern_before = rf"{number}\s*{label}"
        match = re.search(pattern_after, text, flags=re.IGNORECASE) or re.search(pattern_before, text, flags=re.IGNORECASE)
        if match:
            metrics[field] = metric_value(match.group(1))
    return metrics


def parse_metric_number(value: str) -> float | None:
    text = (
        str(value)
        .strip()
        .replace(",", "")
        .replace("$", "")
        .replace("¥", "")
        .replace("￥", "")
        .replace("元", "")
    )
    if not text:
        return None
    multiplier = 1.0
    lower = text.lower()
    if lower.endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    elif lower.endswith("m"):
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


def extract_metrics(text: str) -> dict[str, dict[str, Any]]:
    return metric_parsing.extract_metrics(text, METRIC_FIELDS)


def metric_value(value: Any) -> dict[str, Any]:
    return metric_parsing.metric_value(value)


def parse_metric_number(value: str) -> float | None:
    return metric_parsing.parse_metric_number(value)


def confidence_for_record(metrics: dict[str, Any], evidence: list[str]) -> str:
    if metrics and evidence:
        return "high"
    if metrics:
        return "medium"
    return "low"


def choose_platform(value: str, source: str) -> str:
    normalized_value = normalize_header_key(value)
    if value and normalized_value != "auto":
        return PLATFORM_VALUE_ALIASES.get(normalized_value, value.lower())
    host = urllib.parse.urlparse(source).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "github.com" in host:
        return "github"
    if "zhihu.com" in host:
        return "zhihu"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "xiaohongshu"
    if "douyin.com" in host:
        return "douyin"
    if "tiktok.com" in host:
        return "tiktok"
    return "unknown"


def github_repo_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if "github.com" not in parsed.netloc.lower():
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


def youtube_video_id_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/")
    if "youtube.com" in host:
        query = urllib.parse.parse_qs(parsed.query)
        if query.get("v"):
            return query["v"][0]
        parts = [part for part in parsed.path.split("/") if part]
        if "shorts" in parts:
            index = parts.index("shorts")
            if len(parts) > index + 1:
                return parts[index + 1]
    return ""


def parse_labeled_lines(text: str) -> dict[str, str]:
    fields = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = re.sub(r"[^a-zA-Z0-9]", "", key).lower()
        value = value.strip()
        if key and value:
            fields[key] = value
    return fields


def first_content_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line and ":" not in line:
            return line
    return ""


def first_url(text: str) -> str:
    match = re.search(r"https?://[^\s)>\]\"']+", text)
    return match.group(0) if match else ""


def split_evidence(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[;,]\s*", value) if item.strip()]


def metric_field_value(item: dict[str, Any], field: str) -> Any:
    aliases = [field, snake_case(field), *METRIC_EXPORT_ALIASES.get(field, [])]
    for key in aliases:
        if key in item and item[key] not in (None, ""):
            return item[key]
    normalized = {normalize_header_key(key): value for key, value in item.items()}
    normalized_aliases = [(key, normalize_header_key(key)) for key in aliases]
    for _, normalized_key in normalized_aliases:
        value = normalized.get(normalized_key)
        if value not in (None, ""):
            return value
    for header_key, value in normalized.items():
        if value in (None, ""):
            continue
        for _, alias_key in normalized_aliases:
            if cjk_header_alias_match(header_key, alias_key):
                return value
    return ""


def cjk_header_alias_match(header_key: str, alias_key: str) -> bool:
    if not alias_key or not contains_cjk(alias_key) or not header_key.startswith(alias_key):
        return False
    remainder = header_key[len(alias_key) :]
    return not any(token in remainder for token in ("\u7387", "\u6bd4", "\u5360\u6bd4", "\u767e\u5206\u6bd4"))


def contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def normalize_header_key(value: str) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def get_alias(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    normalized = {normalize_header_key(key): value for key, value in item.items()}
    for key in keys:
        value = normalized.get(normalize_header_key(key))
        if value not in (None, ""):
            return str(value)
    return ""


def snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def first_non_empty(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Imported Metrics",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Input mode: `{report['inputMode']}`",
        f"- Records: {len(report['records'])}",
        f"- Retrospective status: `{report['retrospective']['status']}`",
        "",
        "## Aggregates",
    ]
    for key, value in report["aggregates"].get("totals", {}).items():
        lines.append(f"- {key}: {value}")
    if report["connectorStatus"]:
        lines.extend(["", "## Connector Status"])
        for status in report["connectorStatus"]:
            lines.append(f"- {status.get('platform')}: `{status.get('status')}` {status.get('reason', '')}")
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"## {record['id']} - {record['platform']}",
                f"- Title: {record['title']}",
                f"- URL: {record['publishedUrl'] or 'unknown'}",
                f"- Confidence: {record['confidence']}",
                "- Metrics:",
            ]
        )
        if record["metrics"]:
            for metric, value in record["metrics"].items():
                lines.append(f"  - {metric}: {value['raw']}")
        else:
            lines.append("  - none")
        if record["derived"]:
            lines.append("- Derived:")
            for metric, value in record["derived"].items():
                lines.append(f"  - {metric}: {value}")
        lines.append("- Evidence:")
        if record["evidence"]:
            lines.extend([f"  - {item}" for item in record["evidence"]])
        else:
            lines.append("  - missing")
    lines.extend(["", "## Retrospective"])
    lines.extend([f"- {item}" for item in report["retrospective"]["insights"]])
    lines.extend(["", "## Next Round"])
    lines.extend([f"- {item}" for item in report["retrospective"]["nextRoundActions"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
