#!/usr/bin/env python3
"""Run real evidence recovery from a local evidence inbox."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
REPORT_DIR = Path("reports/promotion-manager/real-evidence-inbox")


EVIDENCE_KEYS = [
    "publishQueue",
    "publishExecution",
    "publishedItemsJson",
    "publishedUrlFiles",
    "publishedUrls",
    "metricsCsv",
    "metricsXlsx",
    "metricsJson",
    "metricsText",
    "metricsStructuredJson",
    "commentStructuredJson",
    "commentHtml",
    "commentText",
    "businessCsv",
    "businessXlsx",
    "businessJson",
    "businessText",
]


MANIFEST_ALIASES = {
    "publishQueue": "publishQueue",
    "publishQueues": "publishQueue",
    "publishExecution": "publishExecution",
    "publishExecutions": "publishExecution",
    "publishedItemsJson": "publishedItemsJson",
    "publishedItems": "publishedItemsJson",
    "publishedUrlFiles": "publishedUrlFiles",
    "publishedUrlFile": "publishedUrlFiles",
    "publishedUrlsFile": "publishedUrlFiles",
    "publishedUrls": "publishedUrls",
    "publishedUrl": "publishedUrls",
    "metricsCsv": "metricsCsv",
    "metricsXlsx": "metricsXlsx",
    "metricsJson": "metricsJson",
    "metricsText": "metricsText",
    "metricsStructuredJson": "metricsStructuredJson",
    "structuredMetricsJson": "metricsStructuredJson",
    "commentStructuredJson": "commentStructuredJson",
    "commentsStructuredJson": "commentStructuredJson",
    "commentHtml": "commentHtml",
    "commentsHtml": "commentHtml",
    "commentText": "commentText",
    "commentsText": "commentText",
    "businessCsv": "businessCsv",
    "ordersCsv": "businessCsv",
    "businessXlsx": "businessXlsx",
    "ordersXlsx": "businessXlsx",
    "businessJson": "businessJson",
    "ordersJson": "businessJson",
    "businessText": "businessText",
    "ordersText": "businessText",
}


def main() -> None:
    args = parse_args()
    inbox_dir = Path(args.inbox_dir)
    out_dir = Path(args.out_dir)
    report_root = inbox_report_dir(out_dir)
    report_root.mkdir(parents=True, exist_ok=True)
    discovery = discover_evidence(args, inbox_dir, report_root)
    normalized_published_urls = write_normalized_published_urls(discovery, report_root)
    steps = run_pipeline(args, out_dir, discovery, normalized_published_urls)
    report = build_report(args, discovery, normalized_published_urls, steps, out_dir)
    write_report(out_dir, report)
    print(f"Real evidence inbox report written to: {(inbox_report_dir(out_dir) / 'real-evidence-inbox.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrate real published URL, metrics, comments, orders, and revenue evidence from an inbox folder.")
    parser.add_argument("--inbox-dir", default="./promotion-evidence-inbox", help="Folder containing exported real evidence files.")
    parser.add_argument("--manifest", default="", help="Optional inbox-manifest.json with explicit evidence file roles.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--skip-post-publish-capture", action="store_true", help="Skip public/browser-visible capture from registered published URLs.")
    parser.add_argument("--capture-browser-assisted", action="store_true", help="Use browser-visible capture for public published URLs and comments.")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Allow official Playwright Chromium install when browser capture is requested.")
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost URLs for local fixtures/tests only.")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def discover_evidence(args: argparse.Namespace, inbox_dir: Path, report_root: Path) -> dict[str, Any]:
    evidence = {key: [] for key in EVIDENCE_KEYS}
    sources: list[dict[str, Any]] = []
    manifest_path = explicit_manifest_path(args, inbox_dir)
    if manifest_path:
        manifest_evidence, manifest_sources = evidence_from_manifest(manifest_path, inbox_dir)
        merge_evidence(evidence, manifest_evidence)
        sources.extend(manifest_sources)
    if inbox_dir.exists():
        heuristic_evidence, heuristic_sources = evidence_from_files(inbox_dir, manifest_path)
        merge_evidence(evidence, heuristic_evidence)
        sources.extend(heuristic_sources)
    evidence = {key: ordered_unique(values) for key, values in evidence.items()}
    return {
        "inboxDir": str(inbox_dir),
        "manifest": str(manifest_path) if manifest_path else "",
        "sources": dedupe_sources(sources),
        "evidence": evidence,
        "reportRoot": str(report_root),
    }


def explicit_manifest_path(args: argparse.Namespace, inbox_dir: Path) -> Path | None:
    candidates = [Path(args.manifest)] if args.manifest else [inbox_dir / "inbox-manifest.json"]
    for path in candidates:
        if path.exists():
            return path
    return None


def evidence_from_manifest(path: Path, inbox_dir: Path) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    evidence = {key: [] for key in EVIDENCE_KEYS}
    sources: list[dict[str, Any]] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        sources.append({"source": str(path), "role": "manifest", "status": "invalid_json"})
        return evidence, sources
    if not isinstance(payload, dict):
        sources.append({"source": str(path), "role": "manifest", "status": "ignored_non_object"})
        return evidence, sources
    entries = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else payload
    for raw_key, raw_value in entries.items():
        key = MANIFEST_ALIASES.get(str(raw_key))
        if not key:
            continue
        for value in list_values(raw_value):
            if key == "publishedUrls" and looks_like_url_or_platform_url(value):
                evidence[key].append(value)
            else:
                resolved = resolve_inbox_path(inbox_dir, value)
                if is_template_or_example_path(resolved):
                    sources.append({"source": str(value), "role": key, "status": "ignored_template_or_example"})
                    continue
                evidence[key].append(str(resolved))
            sources.append({"source": str(value), "role": key, "status": "manifest"})
    return evidence, sources


def evidence_from_files(inbox_dir: Path, manifest_path: Path | None) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    evidence = {key: [] for key in EVIDENCE_KEYS}
    sources: list[dict[str, Any]] = []
    for path in sorted(inbox_dir.rglob("*")):
        if not path.is_file():
            continue
        if manifest_path and path.resolve() == manifest_path.resolve():
            continue
        if is_template_or_example_path(path):
            sources.append({"source": str(path), "role": "", "status": "ignored_template_or_example"})
            continue
        role = classify_file(path)
        if not role:
            continue
        evidence[role].append(str(path))
        sources.append({"source": str(path), "role": role, "status": "heuristic"})
    return evidence, sources


def is_template_or_example_path(path: Path) -> bool:
    name = path.name.lower()
    stem = path.stem.lower()
    return ".example." in name or name.endswith(".example") or "template" in stem


def classify_file(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    stem = path.stem.lower()
    if name == "inbox-manifest.json":
        return ""
    if suffix == ".json":
        if "publish-queue" in stem:
            return "publishQueue"
        if "publish-execution" in stem or "publish-result" in stem:
            return "publishExecution"
        if "published-items" in stem:
            return "publishedItemsJson"
        if "published-url" in stem or "published_urls" in stem:
            return "publishedUrlFiles"
        if has_any(stem, ["comment", "comments", "reply", "replies"]):
            return "commentStructuredJson"
        if has_any(stem, ["business", "order", "orders", "revenue", "sales", "transaction"]):
            return "businessJson"
        if has_any(stem, ["structured", "snapshot", "analytics-snapshot"]):
            return "metricsStructuredJson"
        if has_any(stem, ["metric", "metrics", "analytics", "performance", "insight"]):
            return "metricsJson"
    if suffix == ".csv":
        if "published" in stem and "url" in stem:
            return "publishedUrlFiles"
        if has_any(stem, ["business", "order", "orders", "revenue", "sales", "transaction"]):
            return "businessCsv"
        if has_any(stem, ["metric", "metrics", "analytics", "performance", "insight", "export"]):
            return "metricsCsv"
    if suffix == ".xlsx":
        if has_any(stem, ["business", "order", "orders", "revenue", "sales", "transaction"]):
            return "businessXlsx"
        if has_any(stem, ["metric", "metrics", "analytics", "performance", "insight", "export"]):
            return "metricsXlsx"
    if suffix in {".txt", ".md"}:
        if "published" in stem and "url" in stem:
            return "publishedUrlFiles"
        if has_any(stem, ["comment", "comments", "reply", "replies"]):
            return "commentText"
        if has_any(stem, ["business", "order", "orders", "revenue", "sales", "transaction"]):
            return "businessText"
        if has_any(stem, ["metric", "metrics", "analytics", "performance", "insight"]):
            return "metricsText"
    if suffix in {".html", ".htm"}:
        if has_any(stem, ["comment", "comments", "reply", "replies"]):
            return "commentHtml"
        if has_any(stem, ["metric", "metrics", "analytics", "performance", "insight"]):
            return "metricsText"
    return ""


def write_normalized_published_urls(discovery: dict[str, Any], report_root: Path) -> Path | None:
    records: list[dict[str, Any]] = []
    evidence = discovery["evidence"]
    for value in evidence.get("publishedUrls", []):
        record = published_record_from_value(value, "manifest")
        if record:
            records.append(record)
    for path_text in evidence.get("publishedUrlFiles", []):
        records.extend(published_records_from_file(Path(path_text)))
    records = dedupe_published_records(records)
    if not records:
        return None
    path = report_root / "normalized-published-urls.json"
    payload = {
        "generatedAt": TODAY,
        "source": "real_evidence_inbox",
        "records": records,
        "guardrails": [
            "These records are normalized only from user-provided or inbox-provided published URL evidence.",
            "No published URL, metric, order, or revenue is inferred when evidence is absent.",
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def published_records_from_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    suffix = path.suffix.lower()
    if suffix == ".json":
        return published_records_from_json(path)
    if suffix == ".csv":
        return published_records_from_csv(path)
    return published_records_from_text(path)


def published_records_from_json(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        rows = first_list(payload, "records", "items", "publishedItems", "published_items", "urls", "publishedUrls")
        if not rows:
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    records = []
    for row in rows:
        if isinstance(row, str):
            record = published_record_from_value(row, str(path))
        elif isinstance(row, dict):
            record = published_record_from_mapping(row, str(path))
        else:
            record = None
        if record:
            records.append(record)
    return records


def published_records_from_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [record for row in csv.DictReader(handle) if (record := published_record_from_mapping(row, str(path)))]


def published_records_from_text(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        record = published_record_from_value(line.strip(), str(path))
        if record:
            records.append(record)
    return records


def published_record_from_value(value: str, source: str) -> dict[str, Any] | None:
    text = value.strip()
    if not text or text.startswith("#"):
        return None
    platform = ""
    url = text
    title = ""
    content_id = ""
    if "=" in text and not text.lower().startswith(("http://", "https://")):
        platform, url = [part.strip() for part in text.split("=", 1)]
    elif "," in text:
        parts = [part.strip() for part in text.split(",")]
        if parts and looks_like_url_or_platform_url(parts[0]):
            url = parts[0]
            title = parts[1] if len(parts) > 1 else ""
        elif len(parts) >= 2:
            platform, url = parts[0], parts[1]
            title = parts[2] if len(parts) > 2 else ""
            content_id = parts[3] if len(parts) > 3 else ""
    if not url or not looks_like_url_or_platform_url(url):
        return None
    return published_record_from_mapping(
        {
            "platform": platform,
            "publishedUrl": url,
            "title": title,
            "contentId": content_id,
            "evidence": source,
        },
        source,
    )


def published_record_from_mapping(row: dict[str, Any], source: str) -> dict[str, Any] | None:
    url = get_alias(row, "publishedUrl", "published_url", "url", "link", "contentUrl", "postUrl")
    if not url:
        return None
    platform = get_alias(row, "platform", "source", "channel")
    return {
        "platform": platform,
        "publishedUrl": url,
        "contentId": get_alias(row, "contentId", "content_id", "videoId", "noteId", "repo", "utm_content"),
        "title": get_alias(row, "title", "name", "headline", "contentTitle"),
        "publishedAt": get_alias(row, "publishedAt", "published_at", "date", "createdAt"),
        "publishStatus": "published",
        "evidence": ordered_unique([source, *split_evidence(get_alias(row, "evidence", "screenshot", "export"))]),
    }


def run_pipeline(
    args: argparse.Namespace,
    out_dir: Path,
    discovery: dict[str, Any],
    normalized_published_urls: Path | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    evidence = discovery["evidence"]
    published_items_inputs = list(evidence["publishedItemsJson"])
    if normalized_published_urls:
        published_items_inputs.append(str(normalized_published_urls))
    published_items_path = out_dir / "reports/promotion-manager/published-items/published-items.json"

    if any([evidence["publishQueue"], evidence["publishExecution"], published_items_inputs]):
        command = [sys.executable, str(SCRIPTS / "published_items.py")]
        append_repeated(command, "--publish-queue", evidence["publishQueue"])
        append_repeated(command, "--publish-execution", evidence["publishExecution"])
        append_repeated(command, "--published-items-json", published_items_inputs)
        command.extend(["--out-dir", str(out_dir)])
        steps.append(run_step("published_items", command, published_items_path, args.dry_run))
    else:
        steps.append(skipped_step("published_items", "no published URL, queue, or execution evidence found"))

    if not args.skip_post_publish_capture and published_items_path.exists():
        command = [
            sys.executable,
            str(SCRIPTS / "post_publish_metrics_capture.py"),
            "--published-items-json",
            str(published_items_path),
            "--out-dir",
            str(out_dir),
            "--limit",
            str(args.limit),
            "--timeout-ms",
            str(args.timeout_ms),
        ]
        append_capture_flags(command, args)
        steps.append(run_step("post_publish_metrics_capture", command, out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json", args.dry_run))
    else:
        reason = "disabled by --skip-post-publish-capture" if args.skip_post_publish_capture else "no published-items report available"
        steps.append(skipped_step("post_publish_metrics_capture", reason))

    comment_input = prepare_comment_input(discovery, inbox_report_dir(out_dir))
    if published_items_path.exists() or comment_input:
        command = [
            sys.executable,
            str(SCRIPTS / "comment_evidence_capture.py"),
            "--out-dir",
            str(out_dir),
            "--limit",
            str(args.limit),
            "--timeout-ms",
            str(args.timeout_ms),
        ]
        if published_items_path.exists():
            command.extend(["--published-items-json", str(published_items_path)])
        if comment_input:
            command.extend([comment_input["flag"], comment_input["path"]])
        append_capture_flags(command, args)
        steps.append(run_step("comment_evidence_capture", command, out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json", args.dry_run))
    else:
        steps.append(skipped_step("comment_evidence_capture", "no published URL or comment evidence found"))

    business_export_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json"
    if any(evidence[key] for key in ["businessCsv", "businessXlsx", "businessJson", "businessText"]):
        command = [sys.executable, str(SCRIPTS / "business_attribution.py")]
        append_repeated(command, "--business-csv", evidence["businessCsv"])
        append_repeated(command, "--business-xlsx", evidence["businessXlsx"])
        append_repeated(command, "--business-json", evidence["businessJson"])
        append_repeated(command, "--business-text", evidence["businessText"])
        if published_items_path.exists():
            command.extend(["--published-items-json", str(published_items_path)])
        command.extend(["--out-dir", str(out_dir)])
        steps.append(run_step("business_attribution", command, out_dir / "reports/promotion-manager/business-attribution/business-attribution.json", args.dry_run))
    else:
        steps.append(skipped_step("business_attribution", "no business order/revenue evidence found"))

    metric_inputs_present = metric_inputs_available(evidence, out_dir, business_export_path)
    if published_items_path.exists() or metric_inputs_present:
        command = [sys.executable, str(SCRIPTS / "metrics_recovery.py")]
        if published_items_path.exists():
            command.extend(["--published-items-json", str(published_items_path)])
        append_repeated(command, "--metrics-csv", evidence["metricsCsv"])
        append_repeated(command, "--metrics-xlsx", evidence["metricsXlsx"])
        append_repeated(command, "--metrics-json", evidence["metricsJson"])
        append_repeated(command, "--metrics-text", evidence["metricsText"])
        append_repeated(command, "--metrics-structured-json", evidence["metricsStructuredJson"])
        post_capture_export = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json"
        if post_capture_export.exists():
            command.extend(["--metrics-json", str(post_capture_export)])
        if business_export_path.exists():
            command.extend(["--business-json", str(business_export_path)])
        command.extend(["--out-dir", str(out_dir)])
        steps.append(run_step("metrics_recovery", command, out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json", args.dry_run))
    else:
        steps.append(skipped_step("metrics_recovery", "no published item or metric evidence found"))

    metrics_recovery_path = out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"
    comment_export_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json"
    business_report_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"
    if metrics_recovery_path.exists() or comment_export_path.exists() or business_report_path.exists():
        command = [sys.executable, str(SCRIPTS / "next_round_optimizer.py")]
        if metrics_recovery_path.exists():
            command.extend(["--metrics-recovery-json", str(metrics_recovery_path)])
        if comment_export_path.exists():
            command.extend(["--comment-evidence-json", str(comment_export_path)])
        if business_report_path.exists():
            command.extend(["--business-attribution-json", str(business_report_path)])
        command.extend(["--out-dir", str(out_dir)])
        steps.append(run_step("next_round_optimizer", command, out_dir / "reports/promotion-manager/optimization/next-round-optimization.json", args.dry_run))
    else:
        steps.append(skipped_step("next_round_optimizer", "no recovered metrics, comments, or business attribution found"))
    return steps


def prepare_comment_input(discovery: dict[str, Any], report_root: Path) -> dict[str, str] | None:
    evidence = discovery["evidence"]
    structured = evidence["commentStructuredJson"]
    if structured and not evidence["commentText"] and not evidence["commentHtml"]:
        return {"flag": "--structured-json", "path": structured[0]}
    text_sources = [*evidence["commentText"], *evidence["commentHtml"]]
    if not text_sources:
        return None
    combined_path = report_root / "combined-comment-evidence.txt"
    parts = []
    for source in text_sources:
        path = Path(source)
        if path.exists():
            parts.append(f"\n# Source: {path}\n")
            parts.append(path.read_text(encoding="utf-8-sig", errors="ignore"))
    if not parts:
        return None
    combined_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return {"flag": "--text-file", "path": str(combined_path)}


def metric_inputs_available(evidence: dict[str, list[str]], out_dir: Path, business_export_path: Path) -> bool:
    if any(evidence[key] for key in ["metricsCsv", "metricsXlsx", "metricsJson", "metricsText", "metricsStructuredJson"]):
        return True
    if business_export_path.exists():
        return True
    return (out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json").exists()


def run_step(step_id: str, command: list[str], expected_report: Path, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "id": step_id,
            "status": "dry_run",
            "command": display_command(command),
            "exitCode": 0,
            "report": str(expected_report),
            "reportExists": expected_report.exists(),
        }
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "status": "ready" if completed.returncode == 0 and expected_report.exists() else "error",
        "command": display_command(command),
        "exitCode": completed.returncode,
        "report": str(expected_report),
        "reportExists": expected_report.exists(),
        "stdoutTail": tail(completed.stdout),
        "stderrTail": tail(completed.stderr),
    }


def skipped_step(step_id: str, reason: str) -> dict[str, Any]:
    return {"id": step_id, "status": "skipped", "reason": reason, "command": [], "exitCode": 0, "report": "", "reportExists": False}


def build_report(
    args: argparse.Namespace,
    discovery: dict[str, Any],
    normalized_published_urls: Path | None,
    steps: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    reports = load_output_reports(out_dir)
    coverage = coverage_summary(reports)
    return {
        "generatedAt": TODAY,
        "status": inbox_status(discovery, steps, coverage),
        "inboxDir": discovery["inboxDir"],
        "manifest": discovery["manifest"],
        "normalizedPublishedUrls": str(normalized_published_urls) if normalized_published_urls else "",
        "discoveredEvidence": discovery["evidence"],
        "sources": discovery["sources"],
        "steps": steps,
        "coverage": coverage,
        "artifacts": artifact_summary(out_dir),
        "unresolvedEvidenceRequests": unresolved_requests(reports),
        "nextActions": next_actions(coverage),
        "guardrails": [
            "Use only inbox files, public pages, official APIs, screenshots/OCR text, structured snapshots, or business exports as evidence.",
            "Do not infer missing views, likes, comments, orders, revenue, or published URLs.",
            "Do not auto-login, bypass captcha, scrape private analytics endpoints, or store credentials.",
            "Treat hidden platform metrics/comments as manual evidence requests, not as zero performance.",
        ],
    }


def load_output_reports(out_dir: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "publishedItems": out_dir / "reports/promotion-manager/published-items/published-items.json",
        "postPublishMetrics": out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json",
        "commentEvidence": out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json",
        "businessAttribution": out_dir / "reports/promotion-manager/business-attribution/business-attribution.json",
        "metricsRecovery": out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json",
        "nextRoundOptimization": out_dir / "reports/promotion-manager/optimization/next-round-optimization.json",
    }
    return {key: read_json(path) for key, path in paths.items()}


def coverage_summary(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    published = reports["publishedItems"].get("summary") or {}
    post_metrics = reports["postPublishMetrics"].get("summary") or {}
    comments = reports["commentEvidence"].get("summary") or {}
    business = reports["businessAttribution"].get("summary") or {}
    recovery = reports["metricsRecovery"].get("coverage") or {}
    recovery_aggregates = reports["metricsRecovery"].get("aggregates") or {}
    optimization = reports["nextRoundOptimization"].get("evidenceCoverage") or {}
    next_round = reports["nextRoundOptimization"].get("nextRoundContent") or []
    totals = recovery_aggregates.get("totals") if isinstance(recovery_aggregates.get("totals"), dict) else {}
    return {
        "publishedRecords": int_value(published.get("published")),
        "pendingPublishedItems": int_value(published.get("pending")),
        "capturedMetricRecords": int_value(post_metrics.get("capturedMetricRecords")),
        "recordsWithMetrics": int_value(recovery.get("recordsWithMetrics") or recovery_aggregates.get("recordsWithMetrics")),
        "commentCount": int_value(comments.get("commentCount") or optimization.get("commentCount")),
        "demandSignalCount": int_value(comments.get("demandSignalCount") or optimization.get("demandSignalCount")),
        "matchedBusinessRows": int_value(business.get("matchedRows")),
        "attributedOrders": number_value(business.get("attributedOrders") or totals.get("orders")),
        "attributedRevenue": number_value(business.get("attributedRevenue") or totals.get("revenue")),
        "manualOrPendingRequirements": int_value(recovery.get("manualOrPendingRequirements") or optimization.get("manualOrPendingRequirements")),
        "nextRoundContent": len(next_round) if isinstance(next_round, list) else int_value(optimization.get("nextRoundContent")),
        "metricFields": recovery.get("metricFields") or recovery_aggregates.get("metricFields") or [],
        "metricFieldCounts": recovery.get("metricFieldCounts") or recovery_aggregates.get("metricFieldCounts") or {},
    }


def inbox_status(discovery: dict[str, Any], steps: list[dict[str, Any]], coverage: dict[str, Any]) -> str:
    if not discovery["sources"] and not any(discovery["evidence"].values()):
        return "waiting_evidence"
    if any(step["status"] == "error" for step in steps):
        return "partial_ready_with_errors"
    has_real_evidence = any(
        [
            coverage["recordsWithMetrics"] > 0,
            coverage["capturedMetricRecords"] > 0,
            coverage["commentCount"] > 0,
            coverage["matchedBusinessRows"] > 0,
            coverage["attributedOrders"] > 0,
            coverage["attributedRevenue"] > 0,
        ]
    )
    if coverage["nextRoundContent"] > 0 and has_real_evidence and coverage["manualOrPendingRequirements"] == 0:
        return "ready"
    if coverage["nextRoundContent"] > 0 and has_real_evidence:
        return "partial_ready"
    if has_real_evidence:
        return "ready_waiting_next_round"
    return "waiting_real_data"


def artifact_summary(out_dir: Path) -> dict[str, str]:
    return {
        "publishedItems": str(out_dir / "reports/promotion-manager/published-items/published-items.json"),
        "postPublishMetrics": str(out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json"),
        "commentEvidence": str(out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"),
        "businessAttribution": str(out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"),
        "metricsRecovery": str(out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"),
        "nextRoundOptimization": str(out_dir / "reports/promotion-manager/optimization/next-round-optimization.json"),
    }


def unresolved_requests(reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for item in reports["metricsRecovery"].get("manualExportRequired", []) if isinstance(reports["metricsRecovery"], dict) else []:
        if isinstance(item, dict):
            requests.append({"source": "metrics_recovery", **item})
    for report_key in ["postPublishMetrics", "commentEvidence"]:
        for item in reports[report_key].get("items", []) if isinstance(reports[report_key], dict) else []:
            if isinstance(item, dict) and item.get("evidenceRequest"):
                requests.append(
                    {
                        "source": report_key,
                        "platform": item.get("platform", ""),
                        "status": item.get("status", ""),
                        "reason": item.get("reason", ""),
                        "evidenceRequest": item.get("evidenceRequest", ""),
                    }
                )
    return requests


def next_actions(coverage: dict[str, Any]) -> list[str]:
    if coverage["nextRoundContent"] > 0:
        return [
            "Review next-round optimization output and generate the next platform drafts/videos from its evidence-backed angles.",
            "Register each newly published URL, then drop fresh metrics/comment/business exports into the inbox and rerun this script.",
        ]
    if coverage["recordsWithMetrics"] or coverage["commentCount"] or coverage["matchedBusinessRows"]:
        return ["Run next_round_optimizer.py after enough metrics, comment, or business attribution evidence is available."]
    return ["Add real published URLs, visible metrics exports, comment evidence, or order/revenue exports to the inbox and rerun."]


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = inbox_report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "real-evidence-inbox.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "real-evidence-inbox.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Evidence Inbox",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Inbox: {report['inboxDir']}",
        "",
        "## Coverage",
    ]
    for key, value in report["coverage"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Steps"])
    for step in report["steps"]:
        lines.append(f"- {step['id']}: `{step['status']}`")
        if step.get("reason"):
            lines.append(f"  Reason: {step['reason']}")
        if step.get("report"):
            lines.append(f"  Report: {step['report']}")
    if report["unresolvedEvidenceRequests"]:
        lines.extend(["", "## Unresolved Evidence Requests"])
        for item in report["unresolvedEvidenceRequests"]:
            lines.append(f"- {item.get('source', '')}/{item.get('platform', '')}: `{item.get('status', '')}` {item.get('reason', '')}")
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in report["nextActions"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def append_capture_flags(command: list[str], args: argparse.Namespace) -> None:
    if args.allow_localhost:
        command.append("--allow-localhost")
    if args.capture_browser_assisted:
        command.append("--capture-browser-assisted")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")


def append_repeated(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        command.extend([flag, value])


def merge_evidence(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
    for key, values in source.items():
        target.setdefault(key, []).extend(values)


def resolve_inbox_path(inbox_dir: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return inbox_dir / path


def list_values(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def looks_like_url_or_platform_url(value: str) -> bool:
    text = value.strip()
    if text.lower().startswith(("http://", "https://")):
        return True
    if "=" in text:
        _, url = text.split("=", 1)
        return url.strip().lower().startswith(("http://", "https://"))
    return False


def get_alias(item: dict[str, Any], *keys: str) -> str:
    normalized = {normalize_key(key): value for key, value in item.items()}
    for key in keys:
        value = normalized.get(normalize_key(key))
        if value not in (None, ""):
            return str(value).strip()
    return ""


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", value).lower()


def first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def split_evidence(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]\s*", value or "") if item.strip()]


def dedupe_published_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for record in records:
        key = f"{record.get('platform')}:{record.get('publishedUrl') or record.get('contentId')}".lower().rstrip("/")
        if key not in seen:
            result.append(record)
            seen.add(key)
    return result


def dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for source in sources:
        key = f"{source.get('source')}:{source.get('role')}"
        if key not in seen:
            result.append(source)
            seen.add(key)
    return result


def ordered_unique(values: list[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        if value in (None, ""):
            continue
        key = str(value)
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def int_value(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def number_value(value: Any) -> float:
    try:
        return float(str(value or "0").replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    return text if len(text) <= limit else text[-limit:]


def inbox_report_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


if __name__ == "__main__":
    main()
