#!/usr/bin/env python3
"""Build a ranked viral content library from captured platform search reports."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
COMPETITOR_DIR = Path("reports/promotion-manager/competitors")
PUBLIC_CAPTURE_PLATFORMS = {"github", "youtube"}
BROWSER_ASSISTED_PLATFORMS = {"zhihu", "xiaohongshu", "douyin", "tiktok"}
NON_CONTENT_PATH_PARTS = {
    "about",
    "aboutus",
    "agreement",
    "agreements",
    "contact",
    "help",
    "privacy",
    "recovery_account",
    "terms",
}
NON_CONTENT_TITLE_TERMS = {
    "about us",
    "contact us",
    "privacy policy",
    "terms of service",
    "user agreement",
    "用户协议",
    "隐私政策",
    "关于我们",
    "联系我们",
    "账号找回",
}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    reports = load_capture_reports(args, out_dir)
    materials = build_materials(reports, args.top_n)
    tasks = build_follow_up_tasks(materials, out_dir)
    write_outputs(out_dir, materials, tasks, reports)
    print(f"Viral content library written to: {(report_dir(out_dir) / 'viral-content-library.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank captured platform search records and create follow-up content capture tasks.")
    parser.add_argument("--capture-report", action="append", default=[], help="Captured search report JSON. Can be repeated.")
    parser.add_argument("--search-capture-dir", default="", help="Directory containing captured-search-results-<platform>.json files.")
    parser.add_argument("--workflow-manifest", default="", help="Workflow manifest whose searchCaptures paths should be loaded.")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_capture_reports(args: argparse.Namespace, out_dir: Path) -> list[dict[str, Any]]:
    paths: list[Path] = []
    paths.extend(Path(value) for value in args.capture_report)
    if args.search_capture_dir:
        paths.extend(discover_capture_reports(Path(args.search_capture_dir)))
    if args.workflow_manifest:
        paths.extend(paths_from_manifest(Path(args.workflow_manifest)))
    if not paths:
        paths.extend(discover_capture_reports(report_dir(out_dir)))

    reports = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            data["_sourceReport"] = str(path)
            reports.append(data)
    return reports


def discover_capture_reports(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    candidates = list(directory.glob("captured-search-results-*.json"))
    if candidates:
        return sorted(candidates)
    nested = directory / COMPETITOR_DIR
    if nested.exists():
        return sorted(nested.glob("captured-search-results-*.json"))
    return []


def paths_from_manifest(path: Path) -> list[Path]:
    if not path.exists():
        return []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    paths = []
    for item in manifest.get("competitorDiscovery", {}).get("searchCaptures", []):
        capture_path = item.get("path")
        if capture_path:
            paths.append(Path(capture_path))
    return paths


def build_materials(reports: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    materials = []
    for report in reports:
        platform = normalize_space(report.get("platform") or "")
        query = normalize_space(report.get("query") or "")
        source_report = report.get("_sourceReport", "")
        for record in report.get("records", []):
            material = normalize_record(record, platform, query, source_report)
            if material:
                materials.append(material)
    materials.sort(key=material_sort_key, reverse=True)
    limited = materials[: max(top_n, 0)]
    for index, material in enumerate(limited, start=1):
        material["libraryRank"] = index
        material["id"] = f"viral-material-{index:03d}"
    return limited


def normalize_record(record: dict[str, Any], platform: str, query: str, source_report: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    record_platform = normalize_space(record.get("platform") or platform or "unknown")
    title = first_non_empty(record.get("title"), "Untitled viral material")
    url = normalize_space(record.get("url") or "")
    if is_non_content_result(record_platform, url, title):
        return {}
    metrics = record.get("visibleMetrics") if isinstance(record.get("visibleMetrics"), dict) else {}
    viral_signals = record.get("viralSignals") if isinstance(record.get("viralSignals"), dict) else {}
    score = numeric(viral_signals.get("score"), 0.0)
    return {
        "id": "",
        "libraryRank": 0,
        "platform": record_platform,
        "query": first_non_empty(record.get("query"), query),
        "sourceReport": source_report,
        "sourceRecordId": normalize_space(record.get("id") or ""),
        "sourceRank": record.get("rank"),
        "capturedRank": record.get("normalizedRank"),
        "url": url,
        "creatorName": normalize_space(record.get("creatorName") or ""),
        "title": title,
        "description": normalize_space(record.get("description") or ""),
        "contentFormat": normalize_space(record.get("contentFormat") or "unknown"),
        "hook": normalize_space(record.get("hook") or ""),
        "cta": normalize_space(record.get("cta") or ""),
        "contentExcerpt": normalize_space(record.get("contentExcerpt") or ""),
        "visibleMetrics": metrics,
        "viralSignals": {
            "score": score,
            "hasObservedMetrics": bool(metrics) or bool(viral_signals.get("hasObservedMetrics")),
            "metricFields": sorted(metrics),
        },
        "contentStructure": record.get("contentStructure") if isinstance(record.get("contentStructure"), list) else [],
        "contentDeconstruction": record.get("contentDeconstruction") if isinstance(record.get("contentDeconstruction"), dict) else {},
        "reusablePatterns": record.get("reusablePatterns") if isinstance(record.get("reusablePatterns"), list) else [],
        "confidence": normalize_space(record.get("confidence") or "unknown"),
        "followUpCapture": classify_follow_up(record_platform, url),
    }


def classify_follow_up(platform: str, url: str) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).netloc.lower()
    if not url:
        return {
            "mode": "manual_url_required",
            "status": "blocked",
            "reason": "The search record has no URL. Capture the result page manually or provide an exported URL.",
            "command": [],
        }
    if platform in PUBLIC_CAPTURE_PLATFORMS and is_public_http_url(url):
        return {
            "mode": "public_url_capture_candidate",
            "status": "ready",
            "reason": "Use a public page fetch or official API evidence; stop if the page asks for login, captcha, or account verification.",
            "command": ["python", "scripts/competitor_intake.py", "--url", url, "--platform", platform, "--out-dir", "<promotion-output>"],
        }
    if platform in BROWSER_ASSISTED_PLATFORMS:
        return {
            "mode": "browser_assisted_capture_required",
            "status": "queued",
            "reason": "Use browser-visible evidence or user exports. Do not use cookies, hidden tokens, private endpoints, or captcha bypass.",
            "command": [
                "python",
                "scripts/competitor_intake.py",
                "--text-file",
                "<copied-visible-page-or-transcript.txt>",
                "--platform",
                platform,
                "--out-dir",
                "<promotion-output>",
            ],
        }
    if is_public_http_url(url) and host:
        return {
            "mode": "manual_review_then_public_capture",
            "status": "queued",
            "reason": "The platform is not pre-classified. Review access rules before fetching or importing the page.",
            "command": ["python", "scripts/competitor_intake.py", "--url", url, "--platform", platform, "--out-dir", "<promotion-output>"],
        }
    return {
        "mode": "unsupported_or_private_url",
        "status": "blocked",
        "reason": "The URL is missing a public HTTP(S) host or cannot be safely classified.",
        "command": [],
    }


def build_follow_up_tasks(materials: list[dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    tasks = []
    for material in materials:
        capture = dict(material.get("followUpCapture") or {})
        command = [
            str(out_dir) if part == "<promotion-output>" else part
            for part in capture.get("command", [])
        ]
        tasks.append(
            {
                "id": f"follow-up-{material['libraryRank']:03d}",
                "materialId": material["id"],
                "priority": material["libraryRank"],
                "platform": material["platform"],
                "title": material["title"],
                "creatorName": material["creatorName"],
                "url": material["url"],
                "mode": capture.get("mode", "unknown"),
                "status": capture.get("status", "queued"),
                "reason": capture.get("reason", ""),
                "command": command,
                "requiredEvidence": required_evidence_for_mode(capture.get("mode", "")),
            }
        )
    return tasks


def required_evidence_for_mode(mode: str) -> list[str]:
    if mode == "public_url_capture_candidate":
        return ["public URL content", "observed metrics if visible", "source report path"]
    if mode == "browser_assisted_capture_required":
        return ["browser-visible page text or transcript", "screenshot/export if metrics are used", "real public URL"]
    if mode == "manual_url_required":
        return ["real public URL or copied visible page content"]
    return ["manual access-rule review", "evidence source"]


def write_outputs(out_dir: Path, materials: list[dict[str, Any]], tasks: list[dict[str, Any]], reports: list[dict[str, Any]]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    library = {
        "generatedAt": TODAY,
        "recordCount": len(materials),
        "sourceReports": [report.get("_sourceReport", "") for report in reports],
        "platforms": sorted({item["platform"] for item in materials}),
        "materials": materials,
        "aggregatePatterns": aggregate_patterns(materials),
        "guardrails": guardrails(),
    }
    task_report = {
        "generatedAt": TODAY,
        "recordCount": len(tasks),
        "tasks": tasks,
        "summary": summarize_tasks(tasks),
        "guardrails": guardrails(),
    }
    (directory / "viral-content-library.json").write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "viral-content-library.md").write_text(render_library_markdown(library) + "\n", encoding="utf-8")
    (directory / "follow-up-capture-tasks.json").write_text(json.dumps(task_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "follow-up-capture-tasks.md").write_text(render_tasks_markdown(task_report) + "\n", encoding="utf-8")


def report_dir(out_dir: Path) -> Path:
    return out_dir / COMPETITOR_DIR


def aggregate_patterns(materials: list[dict[str, Any]]) -> dict[str, Any]:
    pattern_counts: dict[str, int] = {}
    metric_fields: dict[str, int] = {}
    for item in materials:
        for pattern in item.get("reusablePatterns", []):
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        for field in item.get("viralSignals", {}).get("metricFields", []):
            metric_fields[field] = metric_fields.get(field, 0) + 1
    return {
        "recordsWithObservedMetrics": sum(1 for item in materials if item.get("viralSignals", {}).get("hasObservedMetrics")),
        "topTitles": [item["title"] for item in materials[:5]],
        "topHooks": [item["hook"] for item in materials[:5] if item.get("hook")],
        "patternCounts": dict(sorted(pattern_counts.items())),
        "metricFieldCounts": dict(sorted(metric_fields.items())),
    }


def summarize_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    modes: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for task in tasks:
        modes[task["mode"]] = modes.get(task["mode"], 0) + 1
        statuses[task["status"]] = statuses.get(task["status"], 0) + 1
    return {"modes": dict(sorted(modes.items())), "statuses": dict(sorted(statuses.items()))}


def material_sort_key(item: dict[str, Any]) -> tuple[float, int, int]:
    score = numeric(item.get("viralSignals", {}).get("score"), 0.0)
    has_metrics = 1 if item.get("viralSignals", {}).get("hasObservedMetrics") else 0
    rank = item.get("capturedRank") or item.get("sourceRank") or 9999
    return (score, has_metrics, -int(rank))


def is_public_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_non_content_result(platform: str, url: str, title: str = "") -> bool:
    parsed = urllib.parse.urlparse(url)
    path_parts = {part.lower() for part in parsed.path.split("/") if part}
    normalized_title = normalize_space(title).lower()
    if path_parts & NON_CONTENT_PATH_PARTS:
        return True
    if any(term in normalized_title for term in NON_CONTENT_TITLE_TERMS):
        return True
    return False


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = normalize_space(value or "")
        if text:
            return text
    return ""


def numeric(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def guardrails() -> list[str]:
    return [
        "Use official APIs, public pages, browser-visible snapshots, or user exports only.",
        "Do not bypass captcha, login prompts, rate limits, or platform risk controls.",
        "Do not store cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
        "Do not fabricate views, likes, comments, orders, revenue, or published URLs.",
    ]


def render_library_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Viral Content Library",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Records: {report['recordCount']}",
        f"- Platforms: {', '.join(report['platforms']) if report['platforms'] else 'none'}",
        f"- Records with observed metrics: {report['aggregatePatterns']['recordsWithObservedMetrics']}",
        "",
        "## Top Materials",
    ]
    for item in report["materials"]:
        lines.extend(
            [
                "",
                f"### {item['libraryRank']}. {item['title']}",
                f"- Platform: {item['platform']}",
                f"- Creator: {item['creatorName'] or 'unknown'}",
                f"- URL: {item['url'] or 'unknown'}",
                f"- Viral score: {item['viralSignals']['score']}",
                f"- Hook: {item['hook'] or 'needs manual review'}",
                f"- Capture mode: `{item['followUpCapture']['mode']}`",
                f"- Capture status: `{item['followUpCapture']['status']}`",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_tasks_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Follow-Up Capture Tasks",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Tasks: {report['recordCount']}",
        "",
        "## Summary",
    ]
    for name, count in report["summary"].get("modes", {}).items():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Tasks"])
    for task in report["tasks"]:
        command = " ".join(task["command"]) if task["command"] else "manual evidence required"
        lines.extend(
            [
                "",
                f"### {task['id']} - {task['platform']}",
                f"- Material: {task['materialId']}",
                f"- Title: {task['title']}",
                f"- URL: {task['url'] or 'unknown'}",
                f"- Mode: `{task['mode']}`",
                f"- Status: `{task['status']}`",
                f"- Reason: {task['reason']}",
                f"- Command: `{command}`",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
