#!/usr/bin/env python3
"""Recover real promotion metrics from publish evidence and business exports."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

import metrics_intake


TODAY = date.today().isoformat()
MANUAL_EXPORT_PLATFORMS = {"zhihu", "xiaohongshu", "douyin", "tiktok"}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    workflow_path = optional_path(args.workflow_manifest) or default_workflow_manifest(out_dir)
    queue_path = optional_path(args.publish_queue) or default_publish_queue(out_dir)

    published_items = []
    source_status = []
    if workflow_path:
        source_status.append({"source": str(workflow_path), "type": "workflow_manifest", "status": "loaded"})
        if not queue_path:
            published_items.extend(items_from_workflow_manifest(workflow_path))
    if queue_path:
        source_status.append({"source": str(queue_path), "type": "publish_queue", "status": "loaded"})
        published_items.extend(items_from_publish_queue(queue_path))

    published_item_paths = [Path(value) for value in args.published_items_json]
    default_items_path = default_published_items(out_dir)
    if default_items_path and default_items_path not in published_item_paths:
        published_item_paths.append(default_items_path)
    for path in published_item_paths:
        source_status.append({"source": str(path), "type": "published_items_json", "status": "loaded"})
        published_items.extend(items_from_published_items_json(path))
    published_items.extend(items_from_direct_args(args))

    records, connector_status = collect_official_records(published_items)
    metric_records, metric_sources = collect_metric_records(args)
    business_records, business_sources = collect_business_records(args)
    records.extend(metric_records)
    records.extend(business_records)

    merged_records = merge_records(records)
    manual_required = manual_export_requirements(published_items, merged_records)
    report = build_recovery_report(
        workflow_path=workflow_path,
        queue_path=queue_path,
        published_items=published_items,
        records=merged_records,
        connector_status=connector_status,
        source_status=source_status,
        metric_sources=metric_sources,
        business_sources=business_sources,
        manual_required=manual_required,
    )
    write_report(out_dir, report)
    print(f"Metrics recovery report written to: {(recovery_dir(out_dir) / 'metrics-recovery.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover real metrics from workflow manifests, publish queues, published URLs, and business exports.")
    parser.add_argument("--workflow-manifest", default="", help="Path to workflow-manifest.json.")
    parser.add_argument("--publish-queue", default="", help="Path to publish-queue.json.")
    parser.add_argument("--published-items-json", action="append", default=[], help="JSON list or object containing platform/url/contentId records.")
    parser.add_argument("--published-url", action="append", default=[], help="Published URL to inspect through supported official connectors.")
    parser.add_argument("--github-repo", action="append", default=[], help="GitHub owner/repo to inspect through the public REST API.")
    parser.add_argument("--youtube-video-id", action="append", default=[], help="YouTube video ID to inspect through the YouTube Data API when YOUTUBE_API_KEY is set.")
    parser.add_argument("--metrics-csv", action="append", default=[], help="CSV export containing platform metrics.")
    parser.add_argument("--metrics-xlsx", action="append", default=[], help="Excel .xlsx export containing platform metrics.")
    parser.add_argument("--metrics-json", action="append", default=[], help="JSON export containing platform metrics.")
    parser.add_argument("--metrics-text", action="append", default=[], help="Text evidence containing platform metrics.")
    parser.add_argument("--metrics-structured-json", action="append", default=[], help="Codex/browser structured snapshot containing published-page or analytics metrics.")
    parser.add_argument("--business-csv", action="append", default=[], help="CSV export containing orders, revenue, clicks, or platform metrics.")
    parser.add_argument("--business-xlsx", action="append", default=[], help="Excel .xlsx export containing orders, revenue, clicks, or platform metrics.")
    parser.add_argument("--business-json", action="append", default=[], help="JSON export containing orders, revenue, clicks, or platform metrics.")
    parser.add_argument("--business-text", action="append", default=[], help="Text evidence containing real metrics.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def optional_path(value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def default_workflow_manifest(out_dir: Path) -> Path | None:
    path = out_dir / "reports/promotion-manager/agent-run/workflow-manifest.json"
    return path if path.exists() else None


def default_publish_queue(out_dir: Path) -> Path | None:
    path = out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"
    return path if path.exists() else None


def default_published_items(out_dir: Path) -> Path | None:
    path = out_dir / "reports/promotion-manager/published-items/published-items.json"
    return path if path.exists() else None


def items_from_workflow_manifest(path: Path) -> list[dict[str, Any]]:
    manifest = read_json(path)
    items = []
    for item in manifest.get("publishAutomation", []):
        platform = clean_text(item.get("platform"))
        if not platform:
            continue
        items.append(
            {
                "platform": platform,
                "publishedUrl": "",
                "contentId": "",
                "title": "",
                "publishStatus": "planned",
                "source": str(path),
                "sourceType": "workflow_manifest",
                "publishMode": item.get("publishMode", ""),
            }
        )
    return items


def items_from_publish_queue(path: Path) -> list[dict[str, Any]]:
    queue = read_json(path)
    items = []
    for record in queue.get("records", []):
        official = record.get("officialExecution") or {}
        status = clean_text(record.get("status"))
        published_url = clean_text(official.get("publishedUrl"))
        publish_status = "published" if status == "published" and published_url else status or "queued"
        items.append(
            {
                "platform": clean_text(record.get("platform")),
                "publishedUrl": published_url,
                "contentId": "",
                "title": title_from_draft(record.get("contentDraft")),
                "publishStatus": publish_status,
                "source": str(path),
                "sourceType": "publish_queue",
                "publishMode": record.get("publishMode", ""),
                "contentDraft": record.get("contentDraft", ""),
            }
        )
    return [item for item in items if item["platform"]]


def title_from_draft(value: Any) -> str:
    path = Path(str(value)) if value else None
    if not path or not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- Title:"):
            return line.split(":", 1)[1].strip()
    return path.stem


def items_from_published_items_json(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict):
        records = first_list(data, "records", "items", "publishedItems", "published_items")
        if not records:
            records = [data]
    elif isinstance(data, list):
        records = data
    else:
        records = []
    return [normalize_published_item(item, str(path), "published_items_json") for item in records if isinstance(item, dict)]


def normalize_published_item(item: dict[str, Any], source: str, source_type: str) -> dict[str, Any]:
    official = item.get("officialExecution") or {}
    url = first_non_empty(item.get("publishedUrl"), item.get("url"), item.get("link"), official.get("publishedUrl"))
    platform = clean_text(item.get("platform")) or metrics_intake.choose_platform("auto", url or source)
    status = clean_text(item.get("publishStatus") or item.get("status") or "published")
    return {
        "platform": platform,
        "publishedUrl": url,
        "contentId": first_non_empty(item.get("contentId"), item.get("videoId"), item.get("repo"), item.get("id")),
        "title": first_non_empty(item.get("title"), item.get("name"), item.get("headline")),
        "publishedAt": first_non_empty(item.get("publishedAt"), item.get("date"), item.get("createdAt")),
        "publishStatus": "published" if url and status in {"", "ready", "published"} else status,
        "source": source,
        "sourceType": source_type,
        "publishMode": item.get("publishMode", ""),
    }


def items_from_direct_args(args: argparse.Namespace) -> list[dict[str, Any]]:
    items = []
    for url in args.published_url:
        items.append(
            {
                "platform": metrics_intake.choose_platform("auto", url),
                "publishedUrl": url,
                "contentId": "",
                "title": "",
                "publishStatus": "published",
                "source": "cli",
                "sourceType": "published_url",
            }
        )
    for repo in args.github_repo:
        items.append(
            {
                "platform": "github",
                "publishedUrl": f"https://github.com/{repo.strip().removeprefix('https://github.com/').strip('/')}",
                "contentId": repo,
                "title": repo,
                "publishStatus": "published",
                "source": "cli",
                "sourceType": "github_repo",
            }
        )
    for video_id in args.youtube_video_id:
        items.append(
            {
                "platform": "youtube",
                "publishedUrl": f"https://www.youtube.com/watch?v={video_id}",
                "contentId": video_id,
                "title": video_id,
                "publishStatus": "published",
                "source": "cli",
                "sourceType": "youtube_video_id",
            }
        )
    return items


def collect_official_records(published_items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    seen = set()
    for item in published_items:
        key = item_key(item)
        if key in seen:
            continue
        seen.add(key)
        platform = item.get("platform", "")
        if item.get("publishStatus") != "published":
            statuses.append(
                {
                    "platform": platform,
                    "status": "publish_pending",
                    "reason": "No published URL or published status is available yet.",
                    "source": item.get("source", ""),
                }
            )
            continue
        if platform == "github":
            record, status = recover_github_item(item)
        elif platform == "youtube":
            record, status = recover_youtube_item(item)
        elif platform in MANUAL_EXPORT_PLATFORMS:
            record, status = None, {
                "platform": platform,
                "status": "manual_export_required",
                "reason": "No safe official metrics connector is configured. Import a platform export, screenshot-derived text, CSV, or JSON evidence.",
                "publishedUrl": item.get("publishedUrl", ""),
            }
        else:
            record, status = None, {
                "platform": platform or "unknown",
                "status": "unsupported",
                "reason": "No safe official metrics connector is implemented for this platform.",
                "publishedUrl": item.get("publishedUrl", ""),
            }
        if record:
            record["notes"] = [*record.get("notes", []), f"Recovered from {item.get('sourceType', 'published evidence')}."]
            records.append(record)
        statuses.append(status)
    return records, statuses


def recover_github_item(item: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    repo = metrics_intake.github_repo_from_url(item.get("publishedUrl", "")) or clean_text(item.get("contentId"))
    if "/" not in repo:
        return None, {"platform": "github", "status": "missing_repo", "reason": "GitHub item needs owner/repo or github.com/owner/repo URL."}
    return metrics_intake.record_from_github_repo(repo, item.get("publishedUrl") or None)


def recover_youtube_item(item: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    video_id = clean_text(item.get("contentId")) or metrics_intake.youtube_video_id_from_url(item.get("publishedUrl", ""))
    if not video_id:
        return None, {"platform": "youtube", "status": "missing_video_id", "reason": "YouTube item needs videoId or watch/shorts URL."}
    return metrics_intake.record_from_youtube_video(video_id, item.get("publishedUrl") or None)


def collect_business_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for value in args.business_csv:
        path = Path(value)
        loaded = metrics_intake.records_from_csv(path)
        records.extend(loaded)
        sources.append({"type": "business_csv", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    for value in args.business_xlsx:
        path = Path(value)
        loaded = metrics_intake.records_from_xlsx(path)
        records.extend(loaded)
        sources.append({"type": "business_xlsx", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    for value in args.business_json:
        path = Path(value)
        loaded = metrics_intake.records_from_json(path)
        records.extend(loaded)
        sources.append({"type": "business_json", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    for value in args.business_text:
        path = Path(value)
        record = metrics_intake.record_from_text(path.read_text(encoding="utf-8"), str(path), "auto")
        records.append(record)
        sources.append({"type": "business_text", "source": str(path), "status": "loaded", "recordCount": 1})
    return records, sources


def collect_metric_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for value in args.metrics_csv:
        path = Path(value)
        loaded = metrics_intake.records_from_csv(path)
        records.extend(loaded)
        sources.append({"type": "metrics_csv", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    for value in args.metrics_xlsx:
        path = Path(value)
        loaded = metrics_intake.records_from_xlsx(path)
        records.extend(loaded)
        sources.append({"type": "metrics_xlsx", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    for value in args.metrics_json:
        path = Path(value)
        loaded = metrics_intake.records_from_json(path)
        records.extend(loaded)
        sources.append({"type": "metrics_json", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    for value in args.metrics_text:
        path = Path(value)
        record = metrics_intake.record_from_text(path.read_text(encoding="utf-8"), str(path), "auto")
        records.append(record)
        sources.append({"type": "metrics_text", "source": str(path), "status": "loaded", "recordCount": 1})
    for value in args.metrics_structured_json:
        path = Path(value)
        loaded = metrics_intake.records_from_structured_json(path)
        records.extend(loaded)
        sources.append({"type": "metrics_structured_json", "source": str(path), "status": "loaded", "recordCount": len(loaded)})
    return records, sources


def merge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record_key(record)
        current = merged.get(key)
        if not current:
            current = {
                **record,
                "metrics": dict(record.get("metrics", {})),
                "evidence": list(record.get("evidence", [])),
                "notes": list(record.get("notes", [])),
                "source": {
                    "type": "metrics_recovery",
                    "value": "merged_sources",
                    "capturedAt": TODAY,
                    "sources": [record.get("source", {})],
                },
            }
            merged[key] = current
            continue
        current["publishedUrl"] = first_non_empty(current.get("publishedUrl"), record.get("publishedUrl"))
        current["contentId"] = first_non_empty(current.get("contentId"), record.get("contentId"))
        current["title"] = first_non_empty(current.get("title"), record.get("title"))
        current["publishedAt"] = first_non_empty(current.get("publishedAt"), record.get("publishedAt"))
        for name, value in record.get("metrics", {}).items():
            current.setdefault("metrics", {}).setdefault(name, value)
        current["evidence"] = unique([*current.get("evidence", []), *record.get("evidence", [])])
        current["notes"] = unique([*current.get("notes", []), *record.get("notes", [])])
        current.setdefault("source", {}).setdefault("sources", []).append(record.get("source", {}))
    return list(merged.values())


def manual_export_requirements(published_items: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metric_keys = {record_key(record) for record in records if record.get("metrics")}
    required = []
    seen = set()
    for item in published_items:
        platform = item.get("platform", "")
        key = item_key(item)
        if key in seen:
            continue
        seen.add(key)
        if item.get("publishStatus") != "published":
            required.append(
                {
                    "platform": platform,
                    "status": "publish_pending",
                    "reason": "Content is planned, queued, dry-run, or browser-assisted but not proven published.",
                    "source": item.get("source", ""),
                }
            )
        elif platform in MANUAL_EXPORT_PLATFORMS and key not in metric_keys:
            required.append(
                {
                    "platform": platform,
                    "status": "manual_export_required",
                    "publishedUrl": item.get("publishedUrl", ""),
                    "reason": "Import real platform export, screenshot-derived text, CSV, or JSON evidence before retrospective optimization.",
                }
            )
    return required


def build_recovery_report(
    workflow_path: Path | None,
    queue_path: Path | None,
    published_items: list[dict[str, Any]],
    records: list[dict[str, Any]],
    connector_status: list[dict[str, Any]],
    source_status: list[dict[str, Any]],
    metric_sources: list[dict[str, Any]],
    business_sources: list[dict[str, Any]],
    manual_required: list[dict[str, Any]],
) -> dict[str, Any]:
    report = metrics_intake.build_report(
        {
            "inputMode": "metrics_recovery",
            "source": "workflow_manifest_publish_queue_business_exports",
            "records": records,
            "connectorStatus": connector_status,
        }
    )
    report.update(
        {
            "workflowManifest": str(workflow_path) if workflow_path else "",
            "publishQueue": str(queue_path) if queue_path else "",
            "publishedItems": published_items,
            "sourceStatus": source_status,
            "metricSources": metric_sources,
            "businessSources": business_sources,
            "manualExportRequired": manual_required,
            "coverage": coverage_summary(published_items, report, manual_required),
            "recoveryStatus": recovery_status(report, manual_required, connector_status),
        }
    )
    report["guardrails"].extend(
        [
            "Only YouTube and GitHub official/public connectors are attempted automatically in this runner.",
            "Zhihu, Xiaohongshu, Douyin, TikTok, orders, and revenue require official access or user-provided exports/evidence.",
        ]
    )
    return report


def coverage_summary(published_items: list[dict[str, Any]], report: dict[str, Any], manual_required: list[dict[str, Any]]) -> dict[str, Any]:
    published_count = sum(1 for item in published_items if item.get("publishStatus") == "published")
    aggregates = report.get("aggregates", {}) if isinstance(report.get("aggregates"), dict) else {}
    return {
        "publishedItemsDiscovered": published_count,
        "plannedOrQueuedItems": len(published_items) - published_count,
        "metricRecords": len(report.get("records", [])),
        "recordsWithMetrics": aggregates.get("recordsWithMetrics", 0),
        "manualOrPendingRequirements": len(manual_required),
        "metricFields": aggregates.get("metricFields", []),
        "metricFieldCounts": aggregates.get("metricFieldCounts", {}),
        "totals": aggregates.get("totals", {}),
        "platforms": sorted({item.get("platform", "unknown") for item in published_items if item.get("platform")}),
    }


def recovery_status(report: dict[str, Any], manual_required: list[dict[str, Any]], connector_status: list[dict[str, Any]]) -> str:
    has_metrics = report.get("aggregates", {}).get("recordsWithMetrics", 0) > 0
    if has_metrics and manual_required:
        return "partial_ready"
    if has_metrics:
        return "ready"
    return "waiting_real_data"


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = recovery_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "metrics-recovery.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "metrics-recovery.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Metrics Recovery",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Recovery status: `{report['recoveryStatus']}`",
        f"- Retrospective status: `{report['retrospective']['status']}`",
        f"- Metric records: {len(report['records'])}",
        f"- Records with metrics: {report['aggregates']['recordsWithMetrics']}",
        "",
        "## Coverage",
    ]
    for key, value in report["coverage"].items():
        lines.append(f"- {key}: {value}")
    if report["businessSources"]:
        lines.extend(["", "## Business Sources"])
        for item in report["businessSources"]:
            lines.append(f"- {item['type']}: `{item['status']}` records={item['recordCount']} source={item['source']}")
    if report.get("metricSources"):
        lines.extend(["", "## Metric Sources"])
        for item in report["metricSources"]:
            lines.append(f"- {item['type']}: `{item['status']}` records={item['recordCount']} source={item['source']}")
    if report["connectorStatus"]:
        lines.extend(["", "## Connector Status"])
        for status in report["connectorStatus"]:
            lines.append(f"- {status.get('platform', 'unknown')}: `{status.get('status')}` {status.get('reason', '')}")
    if report["manualExportRequired"]:
        lines.extend(["", "## Manual Or Pending Requirements"])
        for item in report["manualExportRequired"]:
            lines.append(f"- {item.get('platform', 'unknown')}: `{item.get('status')}` {item.get('reason', '')}")
    lines.extend(["", "## Records"])
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['id']} - {record['platform']}",
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
    lines.extend(["", "## Next Round"])
    lines.extend([f"- {item}" for item in report["retrospective"]["nextRoundActions"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


def recovery_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/metrics-recovery"


def first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def item_key(item: dict[str, Any]) -> str:
    return record_key(
        {
            "platform": item.get("platform", ""),
            "publishedUrl": item.get("publishedUrl", ""),
            "contentId": item.get("contentId", ""),
            "title": item.get("title", ""),
        }
    )


def record_key(record: dict[str, Any]) -> str:
    platform = clean_text(record.get("platform")) or "unknown"
    url = clean_text(record.get("publishedUrl"))
    content_id = clean_text(record.get("contentId"))
    if platform == "youtube":
        video_id = content_id or metrics_intake.youtube_video_id_from_url(url)
        if video_id:
            return f"youtube:{video_id.lower()}"
    if platform == "github":
        repo = metrics_intake.github_repo_from_url(url) or content_id
        if repo:
            return f"github:{repo.strip().lower().removeprefix('https://github.com/').strip('/')}"
    if url:
        return f"{platform}:url:{canonical_url(url)}"
    if content_id:
        return f"{platform}:id:{content_id.lower()}"
    title = clean_text(record.get("title")).lower()
    return f"{platform}:title:{title or 'unknown'}"


def canonical_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url.strip().lower().rstrip("/")
    clean = parsed._replace(fragment="").geturl()
    return clean.lower().rstrip("/")


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


def unique(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


if __name__ == "__main__":
    main()
