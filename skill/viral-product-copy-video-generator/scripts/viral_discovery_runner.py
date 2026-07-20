#!/usr/bin/env python3
"""Run standalone viral content and creator discovery across supported platforms."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    discovery = run_competitor_discovery(args, out_dir, steps)
    official_collections = run_official_collectors(args, out_dir, steps)
    browser_search = run_browser_search(args, out_dir, steps)
    search_captures = run_search_captures(args, out_dir, browser_search, steps)
    viral_library = run_viral_library(args, out_dir, search_captures, steps)
    creator_leaderboard = run_creator_leaderboard(args, out_dir, viral_library, steps)
    creator_follow_up = run_creator_follow_up(args, out_dir, creator_leaderboard, steps)
    follow_up_captures = run_follow_up_captures(args, out_dir, viral_library, steps)

    report = build_report(
        args,
        out_dir,
        discovery,
        official_collections,
        browser_search,
        search_captures,
        viral_library,
        creator_leaderboard,
        creator_follow_up,
        follow_up_captures,
        steps,
    )
    write_report(out_dir, report)
    print(f"Viral discovery run written to: {(report_dir(out_dir) / 'viral-discovery-run.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run search, capture, viral ranking, and creator discovery as a standalone pipeline.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--platforms", default=DEFAULT_PLATFORMS)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--snapshot-dir", default="", help="Directory to write/read browser search snapshots.")
    parser.add_argument("--html-snapshot-dir", default="", help="Optional directory containing saved <platform>.html search pages.")
    parser.add_argument("--browser-search-timeout-ms", type=int, default=30000)
    parser.add_argument("--browser-search-wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--install-browser-if-missing", action="store_true")
    parser.add_argument("--live-official", action="store_true", help="Run supported official/public collectors for YouTube/GitHub.")
    parser.add_argument("--collector-platforms", default="youtube,github")
    parser.add_argument("--skip-browser-search", action="store_true")
    parser.add_argument("--skip-viral-library", action="store_true")
    parser.add_argument("--skip-creator-leaderboard", action="store_true")
    parser.add_argument("--run-creator-follow-up", action="store_true")
    parser.add_argument("--creator-follow-up-limit", type=int, default=20)
    parser.add_argument("--creator-follow-up-top-n", type=int, default=5)
    parser.add_argument("--creator-follow-up-dry-run", action="store_true")
    parser.add_argument("--run-follow-up-captures", action="store_true")
    parser.add_argument("--follow-up-capture-limit", type=int, default=20)
    parser.add_argument("--follow-up-dry-run", action="store_true")
    parser.add_argument("--allow-localhost-follow-up", action="store_true")
    parser.add_argument("--sample-video-frames", action="store_true", help="Sample browser-visible video metadata and frame screenshots during follow-up captures.")
    parser.add_argument("--video-sample-count", type=int, default=5)
    parser.add_argument(
        "--capture-browser-assisted-follow-ups",
        action="store_true",
        help="Attempt browser-visible snapshots for queued Zhihu/Xiaohongshu/Douyin/TikTok follow-up capture tasks.",
    )
    return parser.parse_args()


def run_competitor_discovery(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPTS / "competitor_discovery.py"),
        "--query",
        args.query,
        "--platforms",
        args.platforms,
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    if args.live_official:
        command.append("--live-official")
    step = run_command("competitor_discovery", command, check=False)
    steps.append(step)
    path = out_dir / "reports/promotion-manager/competitors/competitor-discovery.json"
    return {"status": "ready" if path.exists() else "error", "report": str(path), "exitCode": step["exitCode"]}


def run_official_collectors(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not args.live_official:
        return []
    records = []
    for platform in split_csv(args.collector_platforms):
        collector_dir = out_dir / "reports/promotion-manager/competitors/official-collections" / platform
        command = [
            sys.executable,
            str(SCRIPTS / "competitor_collector.py"),
            "--platform",
            platform,
            "--query",
            args.query,
            "--top-n",
            str(args.top_n),
            "--out-dir",
            str(collector_dir),
        ]
        step = run_command(f"competitor_collector_{platform}", command, check=False)
        steps.append(step)
        report_path = collector_dir / "reports/promotion-manager/competitors/auto-collected-competitors.json"
        summary: dict[str, Any] = {}
        if report_path.exists():
            payload = read_json(report_path)
            summary = {
                "recordCount": len(payload.get("records", [])),
                "connectorStatus": payload.get("connectorStatus", []),
            }
        records.append(
            {
                "platform": platform,
                "status": "ready" if report_path.exists() and step["exitCode"] == 0 else "error",
                "report": str(report_path),
                "summary": summary,
                "exitCode": step["exitCode"],
            }
        )
    return records


def run_browser_search(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot_dir = Path(args.snapshot_dir) if args.snapshot_dir else out_dir / "search-snapshots/browser-search"
    if args.skip_browser_search:
        return {
            "status": "skipped",
            "reason": "--skip-browser-search was supplied.",
            "snapshotDir": str(snapshot_dir),
            "records": [],
        }
    command = [
        sys.executable,
        str(SCRIPTS / "platform_search_browser.py"),
        "--query",
        args.query,
        "--platforms",
        args.platforms,
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
        "--snapshot-dir",
        str(snapshot_dir),
        "--timeout-ms",
        str(args.browser_search_timeout_ms),
        "--wait-until",
        args.browser_search_wait_until,
    ]
    if args.html_snapshot_dir:
        command.extend(["--html-snapshot-dir", args.html_snapshot_dir])
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    step = run_command("platform_search_browser", command, check=False)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/competitors/browser-search-snapshots.json"
    payload = read_json(report_path) if report_path.exists() else {}
    return {
        "status": "ready" if report_path.exists() and step["exitCode"] == 0 else "error",
        "report": str(report_path),
        "snapshotDir": payload.get("snapshotDir", str(snapshot_dir)),
        "records": payload.get("records", []),
        "exitCode": step["exitCode"],
    }


def run_search_captures(
    args: argparse.Namespace,
    out_dir: Path,
    browser_search: dict[str, Any],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    snapshot_dir = Path(str(browser_search.get("snapshotDir") or args.snapshot_dir or ""))
    records = []
    for platform in split_csv(args.platforms):
        source = search_snapshot_source(snapshot_dir, platform)
        if not source:
            records.append(
                {
                    "platform": platform,
                    "status": "missing_snapshot",
                    "expected": str(snapshot_dir / f"{platform}.json"),
                }
            )
            continue
        command = [
            sys.executable,
            str(SCRIPTS / "platform_search_capture.py"),
            "--platform",
            platform,
            "--query",
            args.query,
            "--top-n",
            str(args.top_n),
            "--out-dir",
            str(out_dir),
            str(source["flag"]),
            str(source["path"]),
        ]
        step = run_command(f"platform_search_capture_{platform}", command, check=False)
        steps.append(step)
        report_path = out_dir / "reports/promotion-manager/competitors" / f"captured-search-results-{platform}.json"
        payload = read_json(report_path) if report_path.exists() else {}
        records.append(
            {
                "platform": platform,
                "status": "ready" if report_path.exists() and step["exitCode"] == 0 else "error",
                "report": str(report_path),
                "recordCount": len(payload.get("records", [])),
                "inputMode": payload.get("inputMode", ""),
                "exitCode": step["exitCode"],
            }
        )
    return records


def run_viral_library(
    args: argparse.Namespace,
    out_dir: Path,
    search_captures: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    if args.skip_viral_library:
        return {"status": "skipped", "reason": "--skip-viral-library was supplied."}
    capture_paths = [item["report"] for item in search_captures if item.get("status") == "ready" and Path(item.get("report", "")).exists()]
    if not capture_paths:
        return {"status": "skipped", "reason": "No captured search result reports were available."}
    command = [
        sys.executable,
        str(SCRIPTS / "viral_content_library.py"),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    for path in capture_paths:
        command.extend(["--capture-report", path])
    step = run_command("viral_content_library", command, check=False)
    steps.append(step)
    library_path = out_dir / "reports/promotion-manager/competitors/viral-content-library.json"
    tasks_path = out_dir / "reports/promotion-manager/competitors/follow-up-capture-tasks.json"
    payload = read_json(library_path) if library_path.exists() else {}
    tasks = read_json(tasks_path) if tasks_path.exists() else {}
    return {
        "status": "ready" if library_path.exists() and step["exitCode"] == 0 else "error",
        "library": str(library_path),
        "followUpTasks": str(tasks_path),
        "recordCount": payload.get("recordCount", 0),
        "platforms": payload.get("platforms", []),
        "taskSummary": tasks.get("summary", {}),
        "exitCode": step["exitCode"],
    }


def run_creator_leaderboard(
    args: argparse.Namespace,
    out_dir: Path,
    viral_library: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    if args.skip_creator_leaderboard:
        return {"status": "skipped", "reason": "--skip-creator-leaderboard was supplied."}
    library_path = Path(str(viral_library.get("library", "")))
    if viral_library.get("status") != "ready" or not library_path.exists():
        return {"status": "skipped", "reason": "No viral content library was available."}
    command = [
        sys.executable,
        str(SCRIPTS / "creator_leaderboard.py"),
        "--viral-library",
        str(library_path),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    step = run_command("creator_leaderboard", command, check=False)
    steps.append(step)
    leaderboard_path = out_dir / "reports/promotion-manager/competitors/creator-leaderboard.json"
    tasks_path = out_dir / "reports/promotion-manager/competitors/creator-follow-up-tasks.json"
    payload = read_json(leaderboard_path) if leaderboard_path.exists() else {}
    tasks = read_json(tasks_path) if tasks_path.exists() else {}
    return {
        "status": "ready" if leaderboard_path.exists() and step["exitCode"] == 0 else "error",
        "leaderboard": str(leaderboard_path),
        "followUpTasks": str(tasks_path),
        "creatorCount": payload.get("creatorCount", 0),
        "summary": payload.get("summary", {}),
        "taskSummary": tasks.get("summary", {}),
        "exitCode": step["exitCode"],
    }


def run_creator_follow_up(
    args: argparse.Namespace,
    out_dir: Path,
    creator_leaderboard: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    if not args.run_creator_follow_up:
        return {"status": "skipped", "reason": "--run-creator-follow-up was not supplied."}
    tasks_path = Path(str(creator_leaderboard.get("followUpTasks", "")))
    if not tasks_path.exists():
        return {"status": "skipped", "reason": "No creator follow-up tasks were available."}
    command = [
        sys.executable,
        str(SCRIPTS / "creator_follow_up_runner.py"),
        "--tasks-json",
        str(tasks_path),
        "--limit",
        str(args.creator_follow_up_limit),
        "--top-n",
        str(args.creator_follow_up_top_n),
        "--out-dir",
        str(out_dir),
    ]
    if args.creator_follow_up_dry_run:
        command.append("--dry-run")
    step = run_command("creator_follow_up_runner", command, check=False)
    steps.append(step)
    results_path = out_dir / "reports/promotion-manager/competitors/creator-follow-up-results.json"
    deep_path = out_dir / "reports/promotion-manager/competitors/creator-deep-library.json"
    payload = read_json(results_path) if results_path.exists() else {}
    return {
        "status": "ready" if results_path.exists() and step["exitCode"] == 0 else "error",
        "results": str(results_path),
        "creatorDeepLibrary": str(deep_path),
        "summary": payload.get("summary", {}),
        "exitCode": step["exitCode"],
    }


def run_follow_up_captures(
    args: argparse.Namespace,
    out_dir: Path,
    viral_library: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    if not args.run_follow_up_captures:
        return {"status": "skipped", "reason": "--run-follow-up-captures was not supplied."}
    tasks_path = Path(str(viral_library.get("followUpTasks", "")))
    if not tasks_path.exists():
        return {"status": "skipped", "reason": "No follow-up capture tasks were available."}
    command = [
        sys.executable,
        str(SCRIPTS / "follow_up_capture_runner.py"),
        "--tasks-json",
        str(tasks_path),
        "--limit",
        str(args.follow_up_capture_limit),
        "--out-dir",
        str(out_dir),
    ]
    if args.follow_up_dry_run:
        command.append("--dry-run")
    if args.allow_localhost_follow_up:
        command.append("--allow-localhost")
    if args.capture_browser_assisted_follow_ups:
        command.append("--capture-browser-assisted")
    if args.sample_video_frames:
        command.append("--sample-video-frames")
        command.extend(["--video-sample-count", str(args.video_sample_count)])
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    step = run_command("follow_up_capture_runner", command, check=False)
    steps.append(step)
    results_path = out_dir / "reports/promotion-manager/competitors/follow-up-capture-results.json"
    deep_path = out_dir / "reports/promotion-manager/competitors/deep-competitor-library.json"
    payload = read_json(results_path) if results_path.exists() else {}
    capture_results = payload.get("results", []) if isinstance(payload.get("results"), list) else []
    return {
        "status": "ready" if results_path.exists() and step["exitCode"] == 0 else "error",
        "results": str(results_path),
        "deepCompetitorLibrary": str(deep_path),
        "summary": payload.get("summary", {}),
        "browserVisibleCaptureAttempts": sum(1 for item in capture_results if item.get("mode") == "browser_visible_capture"),
        "browserVisibleCaptureReady": sum(
            1 for item in capture_results if item.get("mode") == "browser_visible_capture" and item.get("status") == "ready"
        ),
        "publicCaptureReady": sum(1 for item in capture_results if item.get("mode") == "public_url_capture_candidate" and item.get("status") == "ready"),
        "manualEvidenceQueued": sum(1 for item in capture_results if item.get("status") == "queued_manual_evidence"),
        "exitCode": step["exitCode"],
    }


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    discovery: dict[str, Any],
    official_collections: list[dict[str, Any]],
    browser_search: dict[str, Any],
    search_captures: list[dict[str, Any]],
    viral_library: dict[str, Any],
    creator_leaderboard: dict[str, Any],
    creator_follow_up: dict[str, Any],
    follow_up_captures: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "query": args.query,
        "platforms": split_csv(args.platforms),
        "outDir": str(out_dir),
        "status": discovery_status(browser_search, search_captures, viral_library, creator_leaderboard),
        "competitorDiscovery": discovery,
        "officialCollections": official_collections,
        "browserSearch": browser_search,
        "searchCaptures": search_captures,
        "viralContentLibrary": viral_library,
        "creatorLeaderboard": creator_leaderboard,
        "creatorFollowUp": creator_follow_up,
        "followUpCaptures": follow_up_captures,
        "coverage": coverage_summary(args, browser_search, search_captures, viral_library, creator_leaderboard, follow_up_captures),
        "guardrails": [
            "Automatic capture is limited to official APIs, public pages, and browser-visible evidence.",
            "Zhihu, Xiaohongshu, Douyin, and TikTok records may require browser-visible/manual follow-up evidence when login, captcha, or risk controls appear.",
            "Do not extract cookies, hidden tokens, private endpoints, passwords, or API keys.",
            "Do not fabricate views, likes, comments, orders, revenue, creator income, or published URLs.",
        ],
        "steps": steps,
    }


def discovery_status(
    browser_search: dict[str, Any],
    search_captures: list[dict[str, Any]],
    viral_library: dict[str, Any],
    creator_leaderboard: dict[str, Any],
) -> str:
    if viral_library.get("status") == "ready" and creator_leaderboard.get("status") == "ready":
        return "ready"
    if any(item.get("status") == "ready" for item in search_captures):
        return "partial_ready"
    if browser_search.get("status") == "ready":
        return "search_ready_capture_failed"
    return "blocked"


def coverage_summary(
    args: argparse.Namespace,
    browser_search: dict[str, Any],
    search_captures: list[dict[str, Any]],
    viral_library: dict[str, Any],
    creator_leaderboard: dict[str, Any],
    follow_up_captures: dict[str, Any],
) -> dict[str, Any]:
    platform_count = len(split_csv(args.platforms))
    browser_ready = sum(1 for item in browser_search.get("records", []) if item.get("status") == "ready")
    captures_ready = sum(1 for item in search_captures if item.get("status") == "ready")
    task_summary = viral_library.get("taskSummary") if isinstance(viral_library.get("taskSummary"), dict) else {}
    task_modes = task_summary.get("modes") if isinstance(task_summary.get("modes"), dict) else {}
    follow_summary = follow_up_captures.get("summary") if isinstance(follow_up_captures.get("summary"), dict) else {}
    follow_statuses = follow_summary.get("statuses") if isinstance(follow_summary.get("statuses"), dict) else {}
    follow_modes = follow_summary.get("modes") if isinstance(follow_summary.get("modes"), dict) else {}
    follow_up_runs = sum(int_value(value) for value in follow_statuses.values())
    return {
        "requestedPlatforms": platform_count,
        "browserSearchReady": browser_ready,
        "searchCapturesReady": captures_ready,
        "viralMaterials": viral_library.get("recordCount", 0),
        "creators": creator_leaderboard.get("creatorCount", 0),
        "followUpTasksQueued": sum(int_value(value) for value in task_modes.values()),
        "followUpPublicUrlTasks": int_value(task_modes.get("public_url_capture_candidate")),
        "followUpBrowserAssistedTasks": int_value(task_modes.get("browser_assisted_capture_required")),
        "followUpCaptureStatus": follow_up_captures.get("status", "skipped"),
        "followUpCaptureRuns": follow_up_runs,
        "followUpImportedRecords": int_value(follow_summary.get("importedRecords")),
        "followUpPublicCaptureReady": int_value(follow_up_captures.get("publicCaptureReady")),
        "followUpBrowserVisibleAttempts": int_value(follow_up_captures.get("browserVisibleCaptureAttempts") or follow_modes.get("browser_visible_capture")),
        "followUpBrowserVisibleReady": int_value(follow_up_captures.get("browserVisibleCaptureReady")),
        "followUpManualEvidenceQueued": int_value(follow_up_captures.get("manualEvidenceQueued")),
        "videoSampleRuns": int_value(follow_summary.get("videoSampleRuns")),
        "videoSampleReady": int_value(follow_summary.get("videoSampleReady")),
        "videoSampleFrames": int_value(follow_summary.get("videoSampleFrames")),
        "fullyCapturedAcrossRequestedPlatforms": captures_ready == platform_count and platform_count > 0,
    }


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "viral-discovery-run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "viral-discovery-run.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Viral Discovery Run",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Query: {report['query']}",
        f"- Status: `{report['status']}`",
        f"- Platforms: {', '.join(report['platforms'])}",
        "",
        "## Coverage",
    ]
    for key, value in report["coverage"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Artifacts",
            f"- Browser search: {report['browserSearch'].get('report', '')}",
            f"- Viral library: {report['viralContentLibrary'].get('library', '')}",
            f"- Creator leaderboard: {report['creatorLeaderboard'].get('leaderboard', '')}",
            f"- Creator follow-up tasks: {report['creatorLeaderboard'].get('followUpTasks', '')}",
            f"- Follow-up capture tasks: {report['viralContentLibrary'].get('followUpTasks', '')}",
            "",
            "## Platform Captures",
        ]
    )
    for item in report["searchCaptures"]:
        lines.append(f"- {item['platform']}: `{item['status']}` records={item.get('recordCount', 0)}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def run_command(name: str, command: list[str], check: bool = True) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    step = {
        "name": name,
        "status": "ready" if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }
    if check and result.returncode != 0:
        raise SystemExit(f"{name} failed: {step['stderrTail'] or step['stdoutTail']}")
    return step


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def search_snapshot_source(snapshot_dir: Path, platform: str) -> dict[str, Path | str] | None:
    for suffix, flag in [(".json", "--structured-json"), (".txt", "--text-file"), (".html", "--html-file"), (".htm", "--html-file")]:
        path = snapshot_dir / f"{platform}{suffix}"
        if path.exists():
            return {"path": path, "flag": flag}
    return None


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/competitors"


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
