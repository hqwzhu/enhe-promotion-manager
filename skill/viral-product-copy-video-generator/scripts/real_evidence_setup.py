#!/usr/bin/env python3
"""Generate templates and commands for collecting real promotion evidence."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
REPORT_DIR = Path("reports/promotion-manager/real-evidence-setup")
METRIC_FIELDS = [
    "views",
    "likes",
    "favorites",
    "comments",
    "shares",
    "clicks",
    "messages",
    "leads",
    "orders",
    "revenue",
]
SOCIAL_PLATFORMS = {"youtube", "zhihu", "xiaohongshu", "douyin", "tiktok"}
OFFICIAL_OR_PUBLIC_METRIC_HINTS = {
    "youtube": "Use YouTube Data API, YouTube Studio export, or a browser-visible analytics/page snapshot.",
    "github": "Use public GitHub REST repository metrics, release/issue evidence, or repository traffic export when available.",
    "zhihu": "Use browser-visible page text, screenshot OCR, or a creator analytics export.",
    "xiaohongshu": "Use browser-visible note text, screenshot OCR, or a creator analytics export.",
    "douyin": "Use public/browser-visible page evidence or an official creator/open-platform export.",
    "tiktok": "Use public/browser-visible page evidence or an official creator analytics export.",
}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    sources = load_sources(args, out_dir)
    records = build_records(args, sources)
    artifacts = write_artifacts(out_dir, records, sources)
    report = build_report(args, sources, records, artifacts)
    write_report(out_dir, report)
    print(f"Real evidence setup written to: {(report_dir(out_dir) / 'real-evidence-setup.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create real metrics, comments, orders, and revenue evidence templates.")
    parser.add_argument("--publish-queue", default="", help="Path to publish-queue.json. Defaults to <out-dir>/reports/promotion-manager/publish-queue/publish-queue.json.")
    parser.add_argument("--publish-readiness", default="", help="Optional publish-readiness.json for platform readiness context.")
    parser.add_argument("--published-items-json", action="append", default=[], help="Published items evidence JSON. Can repeat.")
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_sources(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    queue_path = first_existing([args.publish_queue, out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"])
    readiness_path = first_existing([args.publish_readiness, out_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json"])
    published_paths = explicit_existing(args.published_items_json)
    default_published = out_dir / "reports/promotion-manager/published-items/published-items.json"
    if default_published.exists() and default_published not in published_paths:
        published_paths.append(default_published)
    return {
        "publishQueuePath": queue_path,
        "publishReadinessPath": readiness_path,
        "publishedItemsPaths": published_paths,
        "publishQueue": read_json(queue_path),
        "publishReadiness": read_json(readiness_path),
        "publishedItems": [read_json(path) for path in published_paths],
    }


def build_records(args: argparse.Namespace, sources: dict[str, Any]) -> list[dict[str, Any]]:
    selected = split_csv(args.platforms)
    records: list[dict[str, Any]] = []
    for item in queue_records(sources.get("publishQueue", {})):
        platform = clean(item.get("platform")).lower()
        if selected and platform not in selected:
            continue
        records.append(record_from_queue(item, sources.get("publishQueuePath")))
    for item in published_item_records(sources.get("publishedItems", [])):
        platform = clean(item.get("platform")).lower()
        if selected and platform not in selected:
            continue
        records.append(record_from_published_item(item))
    return dedupe_records(records)


def record_from_queue(item: dict[str, Any], source_path: Path | None) -> dict[str, Any]:
    platform = clean(item.get("platform")).lower()
    tracking = item.get("trackingPlan") if isinstance(item.get("trackingPlan"), dict) else {}
    official = item.get("officialExecution") if isinstance(item.get("officialExecution"), dict) else {}
    return build_record(
        platform=platform,
        title=draft_title(item.get("contentDraft")) or clean(item.get("title")),
        published_url=clean(official.get("publishedUrl")),
        content_id=first_non_empty(tracking.get("contentId"), item.get("contentId")),
        publish_status="published" if official.get("publishedUrl") else clean(item.get("status")) or "queued",
        source=str(source_path or ""),
        tracking=tracking,
        publish_mode=clean(item.get("publishMode")),
    )


def record_from_published_item(item: dict[str, Any]) -> dict[str, Any]:
    official = item.get("officialExecution") if isinstance(item.get("officialExecution"), dict) else {}
    platform = clean(item.get("platform")).lower()
    url = first_non_empty(item.get("publishedUrl"), item.get("url"), item.get("link"), official.get("publishedUrl"))
    return build_record(
        platform=platform,
        title=first_non_empty(item.get("title"), item.get("name"), item.get("headline")),
        published_url=url,
        content_id=first_non_empty(item.get("contentId"), item.get("videoId"), item.get("repo"), item.get("id")),
        publish_status="published" if url else clean(item.get("status")) or "published",
        source=clean(item.get("source")) or "published_items",
        tracking={},
        publish_mode=clean(item.get("publishMode")),
    )


def build_record(
    platform: str,
    title: str,
    published_url: str,
    content_id: str,
    publish_status: str,
    source: str,
    tracking: dict[str, Any],
    publish_mode: str,
) -> dict[str, Any]:
    evidence_status = "ready_for_public_capture" if published_url and publish_status == "published" else "waiting_published_url"
    tracked_url = clean(tracking.get("trackedUrl"))
    utm = tracking.get("utm") if isinstance(tracking.get("utm"), dict) else {}
    return {
        "platform": platform,
        "title": title,
        "publishedUrl": published_url,
        "contentId": content_id,
        "publishStatus": publish_status,
        "publishMode": publish_mode,
        "evidenceStatus": evidence_status,
        "source": source,
        "trackingPlan": {
            "trackedUrl": tracked_url,
            "utm_source": first_non_empty(tracking.get("utm_source"), utm.get("utm_source")),
            "utm_medium": first_non_empty(tracking.get("utm_medium"), utm.get("utm_medium")),
            "utm_campaign": first_non_empty(tracking.get("utm_campaign"), utm.get("utm_campaign")),
            "utm_content": first_non_empty(tracking.get("utm_content"), utm.get("utm_content")),
            "campaignId": clean(tracking.get("campaignId")),
            "contentId": clean(tracking.get("contentId")),
        },
        "requiredEvidence": required_evidence(platform),
        "collectionPlan": collection_plan(platform, published_url, tracked_url),
        "importCommands": import_commands(platform, published_url),
        "guardrail": "Missing metrics are unknown, not zero. Orders and revenue require business export or analytics evidence.",
    }


def required_evidence(platform: str) -> list[str]:
    fields = ["real published URL or official execution report"]
    if platform in SOCIAL_PLATFORMS:
        fields.extend(["views/plays", "likes", "comments", "shares or saves when visible"])
    if platform == "github":
        fields.extend(["stars", "forks", "watchers or release/issue engagement when relevant"])
    fields.extend(["comment text export or screenshot OCR", "business export for clicks, leads, orders, and revenue"])
    return fields


def collection_plan(platform: str, published_url: str, tracked_url: str) -> list[str]:
    hint = OFFICIAL_OR_PUBLIC_METRIC_HINTS.get(platform, "Use official exports, browser-visible snapshots, or screenshot OCR.")
    plan = [hint]
    if published_url:
        plan.append("Run public/browser-visible metric and comment capture against the registered URL.")
    else:
        plan.append("Register the real published URL before running public metrics or comment capture.")
    if tracked_url:
        plan.append("Export orders/revenue with UTM or referrer fields that include the tracked URL or utm_content.")
    else:
        plan.append("Use the business template to include publishedUrl, referrer, landingPage, utm_content, orders, and revenue.")
    return plan


def import_commands(platform: str, published_url: str) -> dict[str, str]:
    published_arg = f" --published-url \"{platform}={published_url}\"" if published_url else ""
    return {
        "registerPublishedUrl": f"python scripts/published_items.py --platform {platform} --published-url \"https://...\" --title \"Published {platform} promotion\" --evidence \"./screenshots/{platform}-published.png\" --out-dir \"<promotion-output>\"",
        "capturePublicMetrics": f"python scripts/post_publish_metrics_capture.py{published_arg} --out-dir \"<promotion-output>\"",
        "captureComments": f"python scripts/comment_evidence_capture.py{published_arg} --out-dir \"<promotion-output>\"",
        "importMetricsTemplate": "python scripts/metrics_recovery.py --metrics-csv \"real-platform-metrics.csv\" --out-dir \"<promotion-output>\"",
        "importBusinessTemplate": "python scripts/business_attribution.py --business-csv \"business-attribution-template.csv\" --out-dir \"<promotion-output>\"",
    }


def write_artifacts(out_dir: Path, records: list[dict[str, Any]], sources: dict[str, Any]) -> dict[str, str]:
    directory = report_dir(out_dir)
    templates = directory / "templates"
    commands_dir = directory / "commands"
    templates.mkdir(parents=True, exist_ok=True)
    commands_dir.mkdir(parents=True, exist_ok=True)
    metric_csv = templates / "platform-metrics-template.csv"
    comments_csv = templates / "comment-evidence-template.csv"
    business_csv = templates / "business-attribution-template.csv"
    published_csv = templates / "published-url-template.csv"
    structured_json = templates / "structured-metrics-snapshot.example.json"
    checklist = directory / "real-evidence-checklist.md"
    command_file = commands_dir / "import-real-evidence.ps1"
    write_csv(metric_csv, metric_header(), metric_rows(records))
    write_csv(comments_csv, comment_header(), comment_rows(records))
    write_csv(business_csv, business_header(), business_rows(records))
    write_csv(published_csv, published_header(), published_rows(records))
    structured_json.write_text(json.dumps(structured_example(records), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    checklist.write_text(render_checklist(records, sources) + "\n", encoding="utf-8")
    command_file.write_text(render_commands(records) + "\n", encoding="utf-8")
    return {
        "checklist": str(checklist),
        "platformMetricsTemplate": str(metric_csv),
        "commentEvidenceTemplate": str(comments_csv),
        "businessAttributionTemplate": str(business_csv),
        "publishedUrlTemplate": str(published_csv),
        "structuredMetricsSnapshotExample": str(structured_json),
        "importCommands": str(command_file),
    }


def build_report(args: argparse.Namespace, sources: dict[str, Any], records: list[dict[str, Any]], artifacts: dict[str, str]) -> dict[str, Any]:
    published = sum(1 for item in records if item.get("publishedUrl") and item.get("publishStatus") == "published")
    return {
        "generatedAt": TODAY,
        "status": "ready" if records else "waiting_publish_queue_or_published_items",
        "input": {
            "publishQueue": str(sources.get("publishQueuePath") or ""),
            "publishReadiness": str(sources.get("publishReadinessPath") or ""),
            "publishedItemsJson": [str(path) for path in sources.get("publishedItemsPaths", [])],
            "platforms": args.platforms,
        },
        "summary": {
            "targets": len(records),
            "publishedTargets": published,
            "waitingPublishedUrl": len(records) - published,
            "trackedUrls": sum(1 for item in records if item.get("trackingPlan", {}).get("trackedUrl")),
            "templateFiles": len(artifacts),
        },
        "records": records,
        "artifacts": artifacts,
        "nextCommands": next_commands(artifacts),
        "guardrails": [
            "Templates contain field names and placeholders only; they must not contain secrets.",
            "Do not treat blank metrics as zero.",
            "Do not fabricate comments, orders, revenue, or platform engagement.",
            "Use public pages, official APIs/exports, screenshot OCR, structured browser snapshots, or business exports only.",
            "Do not save cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
        ],
    }


def next_commands(artifacts: dict[str, str]) -> list[str]:
    return [
        f"python scripts/metrics_recovery.py --metrics-csv \"{artifacts['platformMetricsTemplate']}\" --out-dir \"<promotion-output>\"",
        f"python scripts/comment_evidence_capture.py --text-file \"{artifacts['commentEvidenceTemplate']}\" --out-dir \"<promotion-output>\"",
        f"python scripts/business_attribution.py --business-csv \"{artifacts['businessAttributionTemplate']}\" --out-dir \"<promotion-output>\"",
        "python scripts/next_round_optimizer.py --metrics-recovery-json \"<promotion-output>/reports/promotion-manager/metrics-recovery/metrics-recovery.json\" --out-dir \"<promotion-output>\"",
    ]


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "real-evidence-setup.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (directory / "real-evidence-setup.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Evidence Setup",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Targets: {report['summary']['targets']}",
        f"- Published targets: {report['summary']['publishedTargets']}",
        f"- Waiting published URL: {report['summary']['waitingPublishedUrl']}",
        "",
        "## Artifacts",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["artifacts"].items())
    lines.extend(["", "## Targets"])
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record.get('platform', 'unknown')} - {record.get('title') or record.get('contentId') or 'untitled'}",
                f"- Status: `{record.get('evidenceStatus', '')}`",
                f"- URL: {record.get('publishedUrl') or 'waiting'}",
                f"- Tracked URL: {record.get('trackingPlan', {}).get('trackedUrl') or 'none'}",
                "- Required evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in record.get("requiredEvidence", []))
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in report["nextCommands"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_checklist(records: list[dict[str, Any]], sources: dict[str, Any]) -> str:
    lines = [
        "# Real Evidence Checklist",
        "",
        f"- Publish queue: {sources.get('publishQueuePath') or ''}",
        f"- Publish readiness: {sources.get('publishReadinessPath') or ''}",
        "",
    ]
    for record in records:
        lines.extend(["", f"## {record.get('platform')} - {record.get('title') or record.get('contentId') or 'untitled'}"])
        lines.append(f"- [ ] Register real published URL: {record.get('publishedUrl') or 'missing'}")
        for item in record.get("requiredEvidence", []):
            lines.append(f"- [ ] Collect {item}")
        lines.append("- [ ] Import metrics/comment/business evidence with the generated commands.")
    return "\n".join(lines)


def render_commands(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Generated by scripts/real_evidence_setup.py",
        "# Replace <promotion-output> with the actual run directory before executing.",
        "",
    ]
    for record in records:
        lines.append(f"# {record.get('platform')} - {record.get('title') or record.get('contentId') or 'untitled'}")
        for command in record.get("importCommands", {}).values():
            lines.append(command)
        lines.append("")
    return "\n".join(lines).rstrip()


def write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def metric_header() -> list[str]:
    return ["platform", "publishedUrl", "contentId", "title", *METRIC_FIELDS, "evidence", "notes"]


def metric_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        row = base_row(record)
        row.update({"evidence": "", "notes": "Fill only real public/API/export/screenshot-derived metrics."})
        rows.append(row)
    return rows


def comment_header() -> list[str]:
    return ["platform", "publishedUrl", "contentId", "title", "author", "comment", "commentLikes", "commentReplies", "evidence", "notes"]


def comment_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**base_row(record), "author": "", "comment": "", "commentLikes": "", "commentReplies": "", "evidence": "", "notes": "One row per real visible/exported comment."} for record in records]


def business_header() -> list[str]:
    return ["orderId", "platform", "publishedUrl", "referrer", "landingPage", "utm_source", "utm_medium", "utm_campaign", "utm_content", "contentId", "title", "clicks", "leads", "orders", "revenue", "status", "evidence"]


def business_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        tracking = record.get("trackingPlan", {})
        rows.append(
            {
                "orderId": "",
                "platform": record.get("platform", ""),
                "publishedUrl": record.get("publishedUrl", ""),
                "referrer": "",
                "landingPage": tracking.get("trackedUrl", ""),
                "utm_source": tracking.get("utm_source", ""),
                "utm_medium": tracking.get("utm_medium", ""),
                "utm_campaign": tracking.get("utm_campaign", ""),
                "utm_content": tracking.get("utm_content", "") or record.get("contentId", ""),
                "contentId": record.get("contentId", ""),
                "title": record.get("title", ""),
                "clicks": "",
                "leads": "",
                "orders": "",
                "revenue": "",
                "status": "paid",
                "evidence": "",
            }
        )
    return rows


def published_header() -> list[str]:
    return ["platform", "publishedUrl", "contentId", "title", "publishedAt", "evidence", "notes"]


def published_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**base_row(record), "publishedAt": "", "evidence": "", "notes": "Register only final public URLs, not drafts, editors, previews, or login pages."} for record in records]


def structured_example(records: list[dict[str, Any]]) -> dict[str, Any]:
    sample = records[0] if records else {}
    return {
        "platform": sample.get("platform", "xiaohongshu"),
        "publishedUrl": sample.get("publishedUrl", "https://..."),
        "contentId": sample.get("contentId", "content-id"),
        "title": sample.get("title", "Published promotion"),
        "metrics": {field: "" for field in METRIC_FIELDS},
        "comments": [{"author": "", "text": "", "likes": "", "replies": ""}],
        "evidence": "public page, official export, screenshot OCR, or business export path",
    }


def base_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": record.get("platform", ""),
        "publishedUrl": record.get("publishedUrl", ""),
        "contentId": record.get("contentId", ""),
        "title": record.get("title", ""),
    }


def queue_records(queue: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in queue.get("records", []) if isinstance(item, dict)] if isinstance(queue, dict) else []


def published_item_records(payloads: list[Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for payload in payloads:
        if isinstance(payload, list):
            records.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            items = first_list(payload, "records", "items", "publishedItems", "published_items")
            records.extend(item for item in items if isinstance(item, dict))
            if not items and payload.get("publishedUrl"):
                records.append(payload)
    return records


def first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def draft_title(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    path = Path(text)
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- Title:"):
            return line.split(":", 1)[1].strip()
    return path.stem


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for record in records:
        key = "|".join(
            [
                clean(record.get("platform")).lower(),
                clean(record.get("publishedUrl")).lower().rstrip("/"),
                clean(record.get("contentId")).lower(),
                clean(record.get("title")).lower(),
            ]
        )
        if key and key not in seen:
            result.append(record)
            seen.add(key)
    return result


def first_existing(values: list[Any]) -> Path | None:
    for value in values:
        if not value:
            continue
        path = Path(value)
        if path.exists():
            return path
    return None


def explicit_existing(values: list[str]) -> list[Path]:
    return [Path(value) for value in values if value and Path(value).exists()]


def read_json(path: Path | None) -> Any:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def report_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


if __name__ == "__main__":
    main()
