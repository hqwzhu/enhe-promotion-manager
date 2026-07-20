#!/usr/bin/env python3
"""Import user-provided viral competitor evidence from a local inbox."""

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

import platform_search_capture as capture


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
REPORT_DIR = Path("reports/promotion-manager/competitors/viral-evidence-inbox")
COMPETITOR_DIR = Path("reports/promotion-manager/competitors")
SUPPORTED_PLATFORMS = {"youtube", "zhihu", "xiaohongshu", "douyin", "github", "tiktok", "other"}
ROLE_ALIASES = {
    "sourceCsv": "sourceCsv",
    "sourcesCsv": "sourceCsv",
    "csv": "sourceCsv",
    "csvFiles": "sourceCsv",
    "structuredJson": "structuredJson",
    "json": "structuredJson",
    "jsonFiles": "structuredJson",
    "textFiles": "textFile",
    "textFile": "textFile",
    "text": "textFile",
    "transcript": "textFile",
    "htmlFiles": "htmlFile",
    "htmlFile": "htmlFile",
    "html": "htmlFile",
    "screenshots": "screenshot",
    "screenshotFiles": "screenshot",
}
CSV_METRIC_FIELDS = {"views", "likes", "favorites", "comments", "shares", "subscribers", "stars", "forks"}


def main() -> None:
    args = parse_args()
    inbox_dir = Path(args.inbox_dir)
    out_dir = Path(args.out_dir)
    report_root = inbox_report_dir(out_dir)
    report_root.mkdir(parents=True, exist_ok=True)
    discovery = discover_evidence(args, inbox_dir)
    records_by_platform, source_results = normalize_evidence(args, discovery)
    capture_reports = write_capture_reports(args, out_dir, records_by_platform, source_results)
    pipeline_steps = run_library_pipeline(args, out_dir, capture_reports)
    report = build_report(args, discovery, records_by_platform, source_results, capture_reports, pipeline_steps, out_dir)
    write_report(out_dir, report)
    print(f"Viral evidence inbox report written to: {(inbox_report_dir(out_dir) / 'viral-evidence-inbox.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import real competitor/viral evidence from a local inbox into the viral material library.")
    parser.add_argument("--inbox-dir", default="./viral-evidence-inbox", help="Folder containing competitor evidence files.")
    parser.add_argument("--manifest", default="", help="Optional inbox-manifest.json with explicit evidence file roles.")
    parser.add_argument("--platforms", default="", help="Optional comma-separated platform allowlist.")
    parser.add_argument("--query", default="", help="Optional query/context label for imported evidence.")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--skip-library", action="store_true", help="Only write captured-search-results reports; skip viral library and creator leaderboard.")
    parser.add_argument("--skip-creator-leaderboard", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def discover_evidence(args: argparse.Namespace, inbox_dir: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    manifest_path = explicit_manifest_path(args, inbox_dir)
    if manifest_path:
        manifest_entries, manifest_sources = entries_from_manifest(manifest_path, inbox_dir)
        entries.extend(manifest_entries)
        sources.extend(manifest_sources)
    if inbox_dir.exists():
        heuristic_entries, heuristic_sources = entries_from_files(inbox_dir, manifest_path)
        entries.extend(heuristic_entries)
        sources.extend(heuristic_sources)
    entries = dedupe_entries(entries)
    platform_allowlist = set(split_csv(args.platforms))
    if platform_allowlist:
        entries = [entry for entry in entries if not entry.get("platform") or entry.get("platform") in platform_allowlist]
    return {
        "inboxDir": str(inbox_dir),
        "manifest": str(manifest_path) if manifest_path else "",
        "entries": entries,
        "sources": dedupe_sources(sources),
    }


def explicit_manifest_path(args: argparse.Namespace, inbox_dir: Path) -> Path | None:
    candidates = [Path(args.manifest)] if args.manifest else [inbox_dir / "inbox-manifest.json"]
    for path in candidates:
        if path.exists():
            return path
    return None


def entries_from_manifest(path: Path, inbox_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return [], [{"source": str(path), "role": "manifest", "status": "invalid_json"}]
    if not isinstance(payload, dict):
        return [], [{"source": str(path), "role": "manifest", "status": "ignored_non_object"}]
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else payload
    for raw_key, raw_value in evidence.items():
        role = ROLE_ALIASES.get(str(raw_key))
        if not role:
            continue
        for value in list_values(raw_value):
            entry = entry_from_manifest_value(inbox_dir, role, value)
            entries.append(entry)
            sources.append({"source": entry["source"], "role": role, "status": "manifest"})
    return entries, sources


def entry_from_manifest_value(inbox_dir: Path, role: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        source = str(value.get("path") or value.get("file") or value.get("source") or "")
        platform = normalize_platform(value.get("platform") or "")
        query = normalize_space(value.get("query") or "")
    else:
        source = str(value)
        platform = ""
        query = ""
    path = resolve_inbox_path(inbox_dir, source)
    return {
        "role": role,
        "source": str(path),
        "platform": platform or infer_platform_from_path_or_text(path, ""),
        "query": query,
        "status": "manifest",
    }


def entries_from_files(inbox_dir: Path, manifest_path: Path | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for path in sorted(inbox_dir.rglob("*")):
        if not path.is_file():
            continue
        if manifest_path and path.resolve() == manifest_path.resolve():
            continue
        if is_template_or_ignored_path(path):
            sources.append({"source": str(path), "role": "", "status": "ignored_template_or_reference"})
            continue
        role = classify_file(path)
        if not role:
            continue
        entries.append(
            {
                "role": role,
                "source": str(path),
                "platform": infer_platform_from_path_or_text(path, ""),
                "query": "",
                "status": "heuristic",
            }
        )
        sources.append({"source": str(path), "role": role, "status": "heuristic"})
    return entries, sources


def is_template_or_ignored_path(path: Path) -> bool:
    name = path.name.lower()
    stem = path.stem.lower()
    if name in {"readme.md", "inbox-manifest.json"}:
        return True
    if ".example." in name or name.endswith(".example") or "template" in stem:
        return True
    if "commands" in {part.lower() for part in path.parts}:
        return True
    return False


def classify_file(path: Path) -> str:
    suffix = path.suffix.lower()
    stem = path.stem.lower()
    if suffix == ".csv" and has_any(stem, ["viral", "competitor", "source", "creator", "material"]):
        return "sourceCsv"
    if suffix == ".json" and has_any(stem, ["viral", "competitor", "search", "creator", "material", "export"]):
        return "structuredJson"
    if suffix in {".txt", ".md"} and has_any(stem, ["viral", "competitor", "copied", "visible", "transcript", "note", "video", "creator"]):
        return "textFile"
    if suffix in {".html", ".htm"} and has_any(stem, ["viral", "competitor", "search", "note", "video", "creator", "html"]):
        return "htmlFile"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "screenshot"
    return ""


def normalize_evidence(args: argparse.Namespace, discovery: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    records_by_platform: dict[str, list[dict[str, Any]]] = {}
    source_results: list[dict[str, Any]] = []
    for entry in discovery["entries"]:
        path = Path(entry["source"])
        result = {"source": str(path), "role": entry["role"], "platform": entry.get("platform", ""), "status": "ready", "recordCount": 0}
        if not path.exists():
            result["status"] = "missing"
            source_results.append(result)
            continue
        if entry["role"] == "screenshot":
            result["status"] = "manual_text_required"
            result["note"] = "Screenshot files are evidence references only; provide OCR/copy text before metrics are imported."
            source_results.append(result)
            continue
        if path.stat().st_size == 0:
            result["status"] = "empty"
            source_results.append(result)
            continue
        try:
            records = records_from_entry(args, entry, path)
        except Exception as exc:  # pragma: no cover - defensive report path
            result["status"] = "error"
            result["error"] = str(exc)
            source_results.append(result)
            continue
        for record in records:
            platform = normalize_platform(record.get("platform") or entry.get("platform") or "other")
            records_by_platform.setdefault(platform, []).append(record)
        result["recordCount"] = len(records)
        result["platform"] = normalize_platform(entry.get("platform") or infer_platform_from_path_or_text(path, ""))
        source_results.append(result)
    for platform, records in records_by_platform.items():
        records.sort(key=lambda item: item.get("viralSignals", {}).get("score", 0), reverse=True)
        for index, record in enumerate(records[: max(args.top_n, 0)], start=1):
            record["id"] = f"inbox-search-result-{index:03d}"
            record["normalizedRank"] = index
        records_by_platform[platform] = records[: max(args.top_n, 0)]
    return records_by_platform, source_results


def records_from_entry(args: argparse.Namespace, entry: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    role = entry["role"]
    query = entry.get("query") or args.query
    if role == "sourceCsv":
        return records_from_csv(args, entry, path, query)
    if role == "structuredJson":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return records_from_items(args, entry, path, query, capture.items_from_json(data), "structured_json")
    if role == "htmlFile":
        html = path.read_text(encoding="utf-8-sig")
        platform = platform_for_entry(entry, path, html)
        payload = capture.SourcePayload("viral_evidence_inbox_html", str(path), platform, query, capture.items_from_html(html, str(path), platform), "user_inbox_saved_html")
        return mark_records(capture.normalize_records(payload, max(args.top_n, 1)), path)
    text = path.read_text(encoding="utf-8-sig")
    platform = platform_for_entry(entry, path, text)
    payload = capture.SourcePayload("viral_evidence_inbox_text", str(path), platform, query, capture.items_from_text(text), "user_inbox_visible_text")
    return mark_records(capture.normalize_records(payload, max(args.top_n, 1)), path)


def records_from_csv(args: argparse.Namespace, entry: dict[str, Any], path: Path, query: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [normalize_csv_row(row) for row in reader if has_row_content(row)]
    rows_by_platform: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        platform = normalize_platform(row.get("platform") or entry.get("platform") or infer_platform_from_path_or_text(path, row.get("url", "")) or "other")
        rows_by_platform.setdefault(platform, []).append(row)
    for platform, platform_rows in rows_by_platform.items():
        payload = capture.SourcePayload("viral_evidence_inbox_csv", str(path), platform, query, platform_rows, "user_inbox_csv_export")
        records.extend(mark_records(capture.normalize_records(payload, max(args.top_n, 1)), path))
    return records


def records_from_items(args: argparse.Namespace, entry: dict[str, Any], path: Path, query: str, items: list[Any], mode: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = {}
    for item in items:
        platform = ""
        if isinstance(item, dict):
            platform = normalize_platform(item.get("platform") or "")
            if not platform:
                platform = infer_platform_from_path_or_text(path, str(item.get("url") or ""))
        platform = platform or normalize_platform(entry.get("platform") or "") or "other"
        grouped.setdefault(platform, []).append(item)
    records: list[dict[str, Any]] = []
    for platform, platform_items in grouped.items():
        payload = capture.SourcePayload(f"viral_evidence_inbox_{mode}", str(path), platform, query, platform_items, "user_inbox_structured_export")
        records.extend(mark_records(capture.normalize_records(payload, max(args.top_n, 1)), path))
    return records


def normalize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        key = normalize_space(key)
        value = normalize_space(value)
        if key:
            normalized[key] = value
    metrics = {}
    for field in CSV_METRIC_FIELDS:
        if normalized.get(field):
            metrics[field] = normalized[field]
    if metrics:
        normalized["visibleMetrics"] = metrics
    return normalized


def mark_records(records: list[dict[str, Any]], path: Path) -> list[dict[str, Any]]:
    marked = []
    for record in records:
        item = dict(record)
        source = dict(item.get("source") or {})
        source["type"] = "viral_evidence_inbox"
        source["value"] = str(path)
        source["accessMode"] = source.get("accessMode") or "user_inbox"
        item["source"] = source
        item["notes"] = list(item.get("notes") or []) + ["Imported from user-provided viral evidence inbox."]
        marked.append(item)
    return marked


def write_capture_reports(
    args: argparse.Namespace,
    out_dir: Path,
    records_by_platform: dict[str, list[dict[str, Any]]],
    source_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports = []
    for platform, records in sorted(records_by_platform.items()):
        if not records:
            continue
        payload = capture.SourcePayload("viral_evidence_inbox", str(Path(args.inbox_dir)), platform, args.query, [], "user_inbox_import")
        report = capture.build_report(payload, records)
        report["sourceFiles"] = [item["source"] for item in source_results if item.get("recordCount", 0)]
        if not args.dry_run:
            capture.write_report(str(out_dir), platform, report)
        reports.append(
            {
                "platform": platform,
                "path": str(capture.report_path(str(out_dir), platform, "json")),
                "recordCount": len(records),
                "status": "ready",
            }
        )
    return reports


def run_library_pipeline(args: argparse.Namespace, out_dir: Path, capture_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps = []
    if args.dry_run or args.skip_library or not capture_reports:
        return steps
    library_command = [
        sys.executable,
        str(SCRIPTS / "viral_content_library.py"),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    for report in capture_reports:
        library_command.extend(["--capture-report", report["path"]])
    steps.append(run_step("viral_content_library", library_command))
    if args.skip_creator_leaderboard:
        return steps
    library_path = out_dir / COMPETITOR_DIR / "viral-content-library.json"
    leaderboard_command = [
        sys.executable,
        str(SCRIPTS / "creator_leaderboard.py"),
        "--viral-library",
        str(library_path),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    steps.append(run_step("creator_leaderboard", leaderboard_command))
    return steps


def run_step(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {
        "name": name,
        "command": command,
        "exitCode": result.returncode,
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }


def build_report(
    args: argparse.Namespace,
    discovery: dict[str, Any],
    records_by_platform: dict[str, list[dict[str, Any]]],
    source_results: list[dict[str, Any]],
    capture_reports: list[dict[str, Any]],
    pipeline_steps: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    record_count = sum(len(records) for records in records_by_platform.values())
    library_path = out_dir / COMPETITOR_DIR / "viral-content-library.json"
    leaderboard_path = out_dir / COMPETITOR_DIR / "creator-leaderboard.json"
    status = "ready" if record_count else "waiting_evidence"
    if any(step["exitCode"] != 0 for step in pipeline_steps):
        status = "partial_ready_pipeline_error"
    screenshot_count = sum(1 for item in source_results if item.get("status") == "manual_text_required")
    return {
        "generatedAt": TODAY,
        "status": status,
        "input": {
            "inboxDir": args.inbox_dir,
            "manifest": discovery.get("manifest", ""),
            "outDir": str(out_dir),
            "query": args.query,
            "topN": args.top_n,
            "dryRun": bool(args.dry_run),
        },
        "summary": {
            "sources": len(source_results),
            "importedSources": sum(1 for item in source_results if item.get("recordCount", 0)),
            "records": record_count,
            "platforms": sorted(records_by_platform),
            "captureReports": len(capture_reports),
            "screenshotEvidenceNeedingText": screenshot_count,
            "libraryReady": library_path.exists(),
            "creatorLeaderboardReady": leaderboard_path.exists(),
        },
        "sources": source_results,
        "capturedSearchReports": capture_reports,
        "viralContentLibrary": str(library_path) if library_path.exists() else "",
        "creatorLeaderboard": str(leaderboard_path) if leaderboard_path.exists() else "",
        "pipelineSteps": pipeline_steps,
        "nextCommands": next_commands(args, out_dir),
        "guardrails": guardrails(),
    }


def next_commands(args: argparse.Namespace, out_dir: Path) -> list[str]:
    return [
        f"python scripts/viral_evidence_inbox.py --inbox-dir \"{args.inbox_dir}\" --out-dir \"{out_dir}\"",
        f"python scripts/competitor_content_enhancer.py --viral-library \"{out_dir / COMPETITOR_DIR / 'viral-content-library.json'}\" --out-dir \"{out_dir}\"",
    ]


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = inbox_report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "viral-evidence-inbox.json"
    md_path = directory / "viral-evidence-inbox.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Viral Evidence Inbox",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Sources: {report['summary']['sources']}",
        f"- Imported sources: {report['summary']['importedSources']}",
        f"- Records: {report['summary']['records']}",
        f"- Platforms: {', '.join(report['summary']['platforms']) if report['summary']['platforms'] else 'none'}",
        "",
        "## Captured Reports",
    ]
    if report["capturedSearchReports"]:
        for item in report["capturedSearchReports"]:
            lines.append(f"- `{item['platform']}`: `{item['path']}` ({item['recordCount']} records)")
    else:
        lines.append("- none")
    lines.extend(["", "## Sources"])
    for item in report["sources"]:
        lines.append(f"- `{item['role']}` `{item['source']}`: {item['status']} ({item.get('recordCount', 0)} records)")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def platform_for_entry(entry: dict[str, Any], path: Path, text: str) -> str:
    return normalize_platform(entry.get("platform") or infer_platform_from_path_or_text(path, text) or "other")


def infer_platform_from_path_or_text(path: Path, text: str) -> str:
    haystack = f"{path.name} {text}".lower()
    if "youtu" in haystack:
        return "youtube"
    if "zhihu" in haystack or "知乎" in haystack:
        return "zhihu"
    if "xiaohongshu" in haystack or "xhslink" in haystack or "小红书" in haystack:
        return "xiaohongshu"
    if "douyin" in haystack or "抖音" in haystack:
        return "douyin"
    if "github" in haystack:
        return "github"
    if "tiktok" in haystack:
        return "tiktok"
    return ""


def normalize_platform(value: Any) -> str:
    text = normalize_space(value).lower().replace("-", "_")
    aliases = {"xhs": "xiaohongshu", "rednote": "xiaohongshu", "bilibili": "other"}
    text = aliases.get(text, text)
    return text if text in SUPPORTED_PLATFORMS else ""


def resolve_inbox_path(inbox_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else inbox_dir / path


def list_values(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]


def dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    result = []
    for entry in entries:
        key = (entry.get("role", ""), str(Path(entry.get("source", "")).resolve()), entry.get("platform", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for source in sources:
        key = (source.get("source"), source.get("role"), source.get("status"))
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def split_csv(value: str) -> list[str]:
    return [normalize_platform(item) or normalize_space(item) for item in value.split(",") if normalize_space(item)]


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def has_row_content(row: dict[str, Any]) -> bool:
    return any(normalize_space(value) for value in row.values())


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def tail(text: str, limit: int = 1200) -> str:
    text = text.strip()
    return text[-limit:] if len(text) > limit else text


def inbox_report_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


def guardrails() -> list[str]:
    return [
        "Use public pages, browser-visible snapshots, official APIs, platform exports, screenshots/OCR text, or copied visible text only.",
        "Screenshot files are evidence references only until OCR/copy text is provided.",
        "Do not use private endpoints, hidden browser tokens, cookies, or captcha bypass.",
        "Do not treat missing metrics as zero.",
        "Do not fabricate views, likes, comments, creator identity, orders, revenue, or published URLs.",
        "Competitor wording is evidence for structure analysis only; reuse patterns, not wording.",
    ]


if __name__ == "__main__":
    main()
