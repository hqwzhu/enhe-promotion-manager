#!/usr/bin/env python3
"""Register proven published URLs for later metrics recovery."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

import metrics_intake


TODAY = date.today().isoformat()


def main() -> None:
    args = parse_args()
    records: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    for path in source_paths(args.publish_queue):
        queue_records, queue_pending = records_from_publish_queue(path)
        records.extend(queue_records)
        pending.extend(queue_pending)
        sources.append({"type": "publish_queue", "source": str(path), "records": len(queue_records), "pending": len(queue_pending)})
    for path in source_paths(args.publish_execution):
        execution_record = record_from_publish_execution(path)
        if execution_record:
            records.append(execution_record)
            sources.append({"type": "publish_execution", "source": str(path), "records": 1, "pending": 0})
        else:
            sources.append({"type": "publish_execution", "source": str(path), "records": 0, "pending": 1})
    for path in source_paths(args.published_items_json):
        imported = records_from_published_items_json(path)
        records.extend(imported)
        sources.append({"type": "published_items_json", "source": str(path), "records": len(imported), "pending": 0})
    direct = record_from_direct_args(args)
    if direct:
        records.append(direct)
        sources.append({"type": "direct_cli", "source": direct["publishedUrl"], "records": 1, "pending": 0})

    report = build_report(records, pending, sources)
    write_report(Path(args.out_dir), report)
    print(f"Published items report written to: {(published_items_dir(Path(args.out_dir)) / 'published-items.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register real published URLs from publish queues, execution reports, or manual evidence.")
    parser.add_argument("--publish-queue", action="append", default=[], help="Path to publish-queue.json.")
    parser.add_argument("--publish-execution", action="append", default=[], help="Path to publish-execution.json.")
    parser.add_argument("--published-items-json", action="append", default=[], help="Existing published-items JSON to merge.")
    parser.add_argument("--platform", default="", help="Platform for direct manual registration.")
    parser.add_argument("--published-url", default="", help="Real published URL for direct manual registration.")
    parser.add_argument("--title", default="")
    parser.add_argument("--content-id", default="")
    parser.add_argument("--published-at", default="")
    parser.add_argument("--evidence", action="append", default=[], help="Evidence URL, export path, or screenshot path.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def records_from_publish_queue(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue = read_json(path)
    records = []
    pending = []
    for item in queue.get("records", []):
        platform = clean_text(item.get("platform"))
        official = item.get("officialExecution") or {}
        published_url = clean_text(official.get("publishedUrl"))
        status = clean_text(item.get("status"))
        if status == "published" and published_url:
            records.append(
                normalize_record(
                    {
                        "platform": platform,
                        "publishedUrl": published_url,
                        "title": title_from_draft(item.get("contentDraft")) or title_from_execution_report(official.get("report")),
                        "contentId": content_id_from_execution_report(official.get("report")) or content_id_from_url(platform, published_url),
                        "evidence": [published_url, official.get("report", "")],
                        "source": {"type": "publish_queue", "value": str(path), "capturedAt": TODAY},
                    }
                )
            )
        else:
            pending.append(
                {
                    "platform": platform,
                    "status": status or "unknown",
                    "publishMode": item.get("publishMode", ""),
                    "reason": item.get("reason") or official.get("reason") or "No proven published URL is available.",
                    "source": str(path),
                }
            )
    return records, pending


def record_from_publish_execution(path: Path) -> dict[str, Any] | None:
    report = read_json(path)
    if report.get("status") != "published" or not report.get("publishedUrl"):
        return None
    return normalize_record(
        {
            "platform": report.get("platform", ""),
            "publishedUrl": report.get("publishedUrl", ""),
            "contentId": report.get("contentId") or content_id_from_url(report.get("platform", ""), report.get("publishedUrl", "")),
            "title": title_from_publish_execution(report),
            "publishedAt": report.get("publishedAt", ""),
            "evidence": [*(report.get("evidence") or []), str(path)],
            "source": {"type": "publish_execution", "value": str(path), "capturedAt": TODAY},
        }
    )


def records_from_published_items_json(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict):
        items = first_list(data, "records", "items", "publishedItems", "published_items")
        if not items and data.get("publishedUrl"):
            items = [data]
    elif isinstance(data, list):
        items = data
    else:
        items = []
    records = []
    for item in items:
        if isinstance(item, dict) and item.get("publishedUrl"):
            item = {**item, "source": item.get("source") or {"type": "published_items_json", "value": str(path), "capturedAt": TODAY}}
            records.append(normalize_record(item))
    return records


def record_from_direct_args(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.published_url:
        return None
    platform = args.platform or metrics_intake.choose_platform("auto", args.published_url)
    return normalize_record(
        {
            "platform": platform,
            "publishedUrl": args.published_url,
            "contentId": args.content_id or content_id_from_url(platform, args.published_url),
            "title": args.title,
            "publishedAt": args.published_at,
            "evidence": [args.published_url, *args.evidence],
            "source": {"type": "direct_cli", "value": "manual_registration", "capturedAt": TODAY},
        }
    )


def normalize_record(item: dict[str, Any]) -> dict[str, Any]:
    url = clean_text(first_non_empty(item.get("publishedUrl"), item.get("url"), item.get("link")))
    platform = clean_text(item.get("platform")) or metrics_intake.choose_platform("auto", url)
    record = {
        "platform": platform,
        "publishedUrl": url,
        "contentId": clean_text(first_non_empty(item.get("contentId"), item.get("videoId"), item.get("repo"), content_id_from_url(platform, url))),
        "title": clean_text(first_non_empty(item.get("title"), item.get("name"), item.get("headline"), "Untitled published item")),
        "publishedAt": clean_text(first_non_empty(item.get("publishedAt"), item.get("date"), item.get("createdAt"))) or TODAY,
        "publishStatus": "published",
        "evidence": unique([clean_text(value) for value in evidence_values(item)]),
        "source": item.get("source") or {"type": "unknown", "value": "", "capturedAt": TODAY},
    }
    record["id"] = stable_id(record)
    return record


def evidence_values(item: dict[str, Any]) -> list[Any]:
    evidence = item.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [part.strip() for part in evidence.split(",")]
    if not isinstance(evidence, list):
        evidence = [evidence]
    return [item.get("publishedUrl", ""), *evidence]


def build_report(records: list[dict[str, Any]], pending: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    deduped = dedupe_records(records)
    pending = dedupe_pending(pending, deduped)
    return {
        "generatedAt": TODAY,
        "records": deduped,
        "pendingQueueItems": pending,
        "summary": {
            "published": len(deduped),
            "pending": len(pending),
            "platforms": sorted({record["platform"] for record in deduped}),
        },
        "sources": sources,
        "guardrails": [
            "Register only real published URLs or official execution reports with status published.",
            "Dry-runs, blocked writes, queued manual tasks, and browser-assisted tasks stay pending.",
            "Do not fabricate published URLs, platform IDs, views, likes, comments, orders, or revenue.",
        ],
    }


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record_key(record)
        current = merged.get(key)
        if not current:
            merged[key] = record
            continue
        current["title"] = first_non_empty(current.get("title"), record.get("title"))
        current["contentId"] = first_non_empty(current.get("contentId"), record.get("contentId"))
        current["evidence"] = unique([*current.get("evidence", []), *record.get("evidence", [])])
    return list(merged.values())


def dedupe_pending(pending: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    published_platforms = {record["platform"] for record in records}
    result = []
    seen = set()
    for item in pending:
        key = f"{item.get('platform')}:{item.get('status')}:{item.get('publishMode')}:{item.get('source')}"
        if item.get("platform") in published_platforms and item.get("status") == "published":
            continue
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = published_items_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "published-items.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "published-items.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Published Items",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Published records: {report['summary']['published']}",
        f"- Pending queue items: {report['summary']['pending']}",
        "",
        "## Records",
    ]
    if report["records"]:
        for record in report["records"]:
            lines.extend(
                [
                    "",
                    f"### {record['platform']} - {record['title']}",
                    f"- URL: {record['publishedUrl']}",
                    f"- Content ID: {record['contentId'] or 'unknown'}",
                    f"- Published at: {record['publishedAt']}",
                ]
            )
    else:
        lines.append("- none")
    if report["pendingQueueItems"]:
        lines.extend(["", "## Pending Queue Items"])
        for item in report["pendingQueueItems"]:
            lines.append(f"- {item.get('platform')}: `{item.get('status')}` {item.get('reason', '')}")
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


def published_items_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/published-items"


def title_from_draft(value: Any) -> str:
    path = Path(str(value)) if value else None
    if not path or not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- Title:"):
            return line.split(":", 1)[1].strip()
    return path.stem


def title_from_execution_report(value: Any) -> str:
    path = Path(str(value)) if value else None
    if not path or not path.exists():
        return ""
    return title_from_publish_execution(read_json(path))


def title_from_publish_execution(report: dict[str, Any]) -> str:
    request = report.get("request") or {}
    return clean_text(first_non_empty(request.get("title"), report.get("title"), report.get("repository"), report.get("publishedUrl")))


def content_id_from_execution_report(value: Any) -> str:
    path = Path(str(value)) if value else None
    if not path or not path.exists():
        return ""
    report = read_json(path)
    return clean_text(first_non_empty(report.get("contentId"), report.get("commitSha"), content_id_from_url(report.get("platform", ""), report.get("publishedUrl", ""))))


def content_id_from_url(platform: str, url: str) -> str:
    if platform == "youtube":
        return metrics_intake.youtube_video_id_from_url(url)
    if platform == "github":
        return metrics_intake.github_repo_from_url(url)
    parsed = urllib.parse.urlparse(url)
    return parsed.path.strip("/").split("/")[-1] if parsed.path else ""


def record_key(record: dict[str, Any]) -> str:
    return f"{record.get('platform')}:{record.get('publishedUrl') or record.get('contentId')}".lower().rstrip("/")


def stable_id(record: dict[str, Any]) -> str:
    platform = clean_slug(record.get("platform", "unknown"))
    content_id = clean_slug(record.get("contentId") or record.get("publishedUrl") or record.get("title"))
    return f"{platform}-{content_id[:80] or 'published'}"


def clean_slug(value: Any) -> str:
    import re

    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", clean_text(value).lower()).strip("-")
    return slug or "item"


def source_paths(values: list[str]) -> list[Path]:
    return [Path(value) for value in values if value and Path(value).exists()]


def first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


if __name__ == "__main__":
    main()
