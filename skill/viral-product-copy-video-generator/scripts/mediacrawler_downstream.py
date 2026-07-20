#!/usr/bin/env python3
"""Adapt normalized MediaCrawler records to existing ENHE Product Promo Maker reports."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any

import comment_evidence_capture
import creator_leaderboard
import mediacrawler_contract
import platform_search_capture
import viral_content_library


def write_downstream_artifacts(
    out_dir: Path,
    run_dir: Path,
    contents: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    *,
    published_items: list[dict[str, Any]],
    top_n: int = 20,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    capture_reports = write_capture_reports(out_dir, run_dir, contents)
    materials = viral_content_library.build_materials(capture_reports, top_n)
    material_tasks = viral_content_library.build_follow_up_tasks(materials, out_dir)
    viral_content_library.write_outputs(out_dir, materials, material_tasks, capture_reports)

    creators = creator_leaderboard.build_creators(materials, top_n)
    creator_tasks = creator_leaderboard.build_creator_tasks(creators)
    creator_leaderboard.write_outputs(out_dir, creators, creator_tasks, materials)

    comment_report = build_comment_report(out_dir, run_dir, contents, comments)
    comment_evidence_capture.write_outputs(out_dir, comment_report)

    creator_records = derive_creator_records(contents)
    creator_records_path = run_dir / "creators.jsonl"
    write_jsonl(creator_records_path, creator_records)

    owned_metrics = match_owned_metrics(contents, published_items)
    owned_metrics_path = run_dir / "owned-metrics.json"
    owned_metrics_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "source": "mediacrawler_strict_published_match",
                "records": owned_metrics,
                "guardrails": [
                    "Only exact registered platform/contentId matches are accepted.",
                    "URL fallback is used only when the registered published item has no contentId.",
                    "Titles, authors, keywords, and similar text never establish ownership.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    competitor_dir = out_dir / "reports" / "promotion-manager" / "competitors"
    comment_dir = out_dir / "reports" / "promotion-manager" / "comment-evidence"
    return {
        "captureReports": [report["_sourceReport"] for report in capture_reports],
        "viralContentLibrary": str(competitor_dir / "viral-content-library.json"),
        "creatorLeaderboard": str(competitor_dir / "creator-leaderboard.json"),
        "commentEvidence": str(comment_dir / "comment-evidence-capture.json"),
        "creatorRecords": str(creator_records_path),
        "ownedMetrics": str(owned_metrics_path),
        "ownedMetricCount": len(owned_metrics),
    }


def write_capture_reports(out_dir: Path, run_dir: Path, contents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for content in contents:
        platform = clean(content.get("platform"))
        if platform:
            grouped[platform].append(content)

    reports = []
    for platform, platform_contents in sorted(grouped.items()):
        query = next((clean(item.get("sourceKeyword")) for item in platform_contents if item.get("sourceKeyword")), "")
        payload = platform_search_capture.SourcePayload(
            input_mode="mediacrawler_jsonl",
            source=str(run_dir / "contents.jsonl"),
            platform=platform,
            query=query,
            items=[search_item(item) for item in platform_contents],
            access_mode="local_sidecar",
        )
        records = platform_search_capture.normalize_records(payload, len(platform_contents))
        report = platform_search_capture.build_report(payload, records)
        platform_search_capture.write_report(str(out_dir), platform, report)
        path = platform_search_capture.report_path(str(out_dir), platform, "json")
        report["_sourceReport"] = str(path)
        reports.append(report)
    return reports


def search_item(content: dict[str, Any]) -> dict[str, Any]:
    metrics = {key: value for key, value in (content.get("metrics") or {}).items() if value is not None}
    return {
        "id": content.get("contentId", ""),
        "platform": content.get("platform", ""),
        "query": content.get("sourceKeyword", ""),
        "url": content.get("sourceUrl", ""),
        "creatorName": content.get("authorDisplayName") or content.get("authorHash") or "",
        "title": content.get("title") or "",
        "description": content.get("text") or "",
        "contentFormat": content.get("contentType") or "unknown",
        "content": content.get("text") or "",
        "visibleMetrics": metrics,
        "evidencePath": content.get("evidencePath", ""),
    }


def build_comment_report(
    out_dir: Path,
    run_dir: Path,
    contents: list[dict[str, Any]],
    comments: list[dict[str, Any]],
) -> dict[str, Any]:
    content_map = {(clean(item.get("platform")), clean(item.get("contentId"))): item for item in contents}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for comment in comments:
        grouped[(clean(comment.get("platform")), clean(comment.get("contentId")))].append(comment)

    items = []
    results = []
    for index, ((platform, content_id), rows) in enumerate(sorted(grouped.items()), start=1):
        content = content_map.get((platform, content_id), {})
        published_url = clean(content.get("sourceUrl")) or clean(rows[0].get("sourceUrl"))
        title = clean(content.get("title"))
        item = {
            "platform": platform,
            "publishedUrl": published_url,
            "contentId": content_id,
            "title": title,
            "publishStatus": "published",
            "source": str(run_dir / "comments.jsonl"),
            "sourceType": "mediacrawler_local_sidecar",
        }
        converted = [comment_item(row, published_url) for row in rows]
        signals = comment_evidence_capture.demand_signals_for_comments(converted)
        items.append(item)
        results.append(
            {
                "id": f"mediacrawler-{index:03d}-{platform}-{content_id}",
                "platform": platform,
                "publishedUrl": published_url,
                "title": title,
                "status": "ready" if converted else "no_results",
                "reason": "",
                "sourceEvidence": str(run_dir / "comments.jsonl"),
                "commentCount": len(converted),
                "comments": converted,
                "demandSignals": signals,
            }
        )

    args = argparse.Namespace(
        out_dir=str(out_dir),
        published_items_json=[],
        published_url=[],
        structured_json=str(run_dir / "comments.jsonl"),
        html_file="",
        text_file="",
        capture_browser_assisted=False,
        dry_run=False,
    )
    return comment_evidence_capture.build_report(args, items, results)


def comment_item(comment: dict[str, Any], published_url: str) -> dict[str, Any]:
    return {
        "commentId": comment.get("commentId", ""),
        "parentCommentId": comment.get("parentCommentId"),
        "author": comment.get("authorDisplayName") or comment.get("authorHash") or "unknown",
        "authorHash": comment.get("authorHash"),
        "text": comment.get("text", ""),
        "likes": comment.get("likes"),
        "replies": comment.get("replyCount"),
        "publishedAt": comment.get("createdAt"),
        "platform": comment.get("platform", ""),
        "publishedUrl": published_url,
        "sourceEvidence": comment.get("evidencePath", ""),
    }


def derive_creator_records(contents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for content in contents:
        platform = clean(content.get("platform"))
        author_hash = clean(content.get("authorHash"))
        if not platform or not author_hash:
            continue
        key = (platform, author_hash)
        creator = grouped.setdefault(
            key,
            {
                "schemaVersion": 1,
                "provider": "mediacrawler",
                "platform": platform,
                "authorHash": author_hash,
                "authorDisplayName": content.get("authorDisplayName"),
                "sourceUrl": None,
                "metrics": {"views": 0, "likes": 0, "favorites": 0, "comments": 0, "shares": 0},
                "contentCount": 0,
                "capturedAt": content.get("capturedAt"),
                "evidencePath": content.get("evidencePath", ""),
            },
        )
        creator["contentCount"] += 1
        for name, value in (content.get("metrics") or {}).items():
            if isinstance(value, (int, float)):
                creator["metrics"][name] = creator["metrics"].get(name, 0) + value
    return list(grouped.values())


def match_owned_metrics(
    contents: list[dict[str, Any]],
    published_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    registered = [item for item in published_items if clean(item.get("publishStatus") or item.get("status")) == "published"]
    by_id = {
        (clean(item.get("platform")), clean(item.get("contentId"))): item
        for item in registered
        if clean(item.get("platform")) and clean(item.get("contentId"))
    }
    by_url = {
        (clean(item.get("platform")), canonical_public_url(item.get("publishedUrl", ""))): item
        for item in registered
        if clean(item.get("platform")) and not clean(item.get("contentId")) and canonical_public_url(item.get("publishedUrl", ""))
    }

    matches = []
    for content in contents:
        platform = clean(content.get("platform"))
        content_id = clean(content.get("contentId"))
        item = by_id.get((platform, content_id)) if content_id else None
        match_mode = "platform_content_id"
        if item is None:
            item = by_url.get((platform, canonical_public_url(content.get("sourceUrl", ""))))
            match_mode = "registered_canonical_url"
        if item is None:
            continue
        metrics = {name: value for name, value in (content.get("metrics") or {}).items() if value is not None}
        if not metrics:
            continue
        matches.append(
            {
                "platform": platform,
                "publishedUrl": item.get("publishedUrl") or content.get("sourceUrl") or "",
                "contentId": item.get("contentId") or content_id,
                "title": item.get("title") or content.get("title") or "",
                "publishedAt": item.get("publishedAt") or content.get("publishedAt"),
                "metrics": metrics,
                "evidence": content.get("evidencePath", ""),
                "capturedAt": content.get("capturedAt"),
                "notes": f"Matched by {match_mode}; competitor and similarity matching are disabled.",
            }
        )
    return matches


def canonical_public_url(value: Any) -> str:
    sanitized = mediacrawler_contract.sanitize_url(clean(value))
    if not sanitized:
        return ""
    parsed = urllib.parse.urlsplit(sanitized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return sanitized.lower().rstrip("/")
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, ""))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()
