#!/usr/bin/env python3
"""Run scheduled promotion workflow jobs from a local JSON config."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PUBLISH_QUEUE = SCRIPTS / "publish_queue.py"
BROWSER_PUBLISH_ASSISTANT = SCRIPTS / "browser_publish_assistant.py"
BROWSER_PUBLISH_FORM_FILL = SCRIPTS / "browser_publish_form_fill.py"
POST_PUBLISH_METRICS_CAPTURE = SCRIPTS / "post_publish_metrics_capture.py"
COMMENT_EVIDENCE_CAPTURE = SCRIPTS / "comment_evidence_capture.py"
BUSINESS_ATTRIBUTION = SCRIPTS / "business_attribution.py"
METRICS_RECOVERY = SCRIPTS / "metrics_recovery.py"
MULTI_QUERY_VIRAL_DISCOVERY = SCRIPTS / "multi_query_viral_discovery.py"
NEXT_ROUND_OPTIMIZER = SCRIPTS / "next_round_optimizer.py"
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]


def main() -> None:
    args = parse_args()
    if args.command == "init":
        init_config(args)
    elif args.command == "run":
        run_due_jobs(args)
    elif args.command == "windows-task":
        write_windows_task_script(args)
    else:
        raise SystemExit(f"Unsupported command: {args.command}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Schedule and run product promotion workflow jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Write a starter automation config.")
    init.add_argument("--config", required=True)
    init.add_argument("--job-id", default="product-weekly")
    source = init.add_mutually_exclusive_group(required=True)
    source.add_argument("--browser-url")
    source.add_argument("--product-url")
    source.add_argument("--html-file")
    source.add_argument("--text-file")
    source.add_argument("--structured-json")
    init.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS))
    init.add_argument("--interval-days", type=int, default=7)
    init.add_argument("--output-root", default="./promotion-output/automation")
    init.add_argument("--skip-video", action="store_true")
    init.add_argument("--install-browser-if-missing", action="store_true")
    init.add_argument("--auto-search-competitors", action="store_true")
    init.add_argument("--search-html-snapshot-dir", default="")
    init.add_argument("--capture-browser-assisted-follow-ups", action="store_true")
    init.add_argument("--run-follow-up-captures", action="store_true")
    init.add_argument("--sample-video-frames", action="store_true")
    init.add_argument("--video-sample-count", type=int, default=5)
    init.add_argument("--skip-creator-leaderboard", action="store_true")
    init.add_argument("--run-creator-follow-up", action="store_true")
    init.add_argument("--creator-follow-up-dry-run", action="store_true")
    init.add_argument("--enable-multi-query-viral-discovery", action="store_true")
    init.add_argument("--multi-query-dry-run", action="store_true")
    init.add_argument("--skip-competitor-informed-content", action="store_true")
    init.add_argument("--enable-publish-queue", action="store_true")
    init.add_argument("--enable-browser-publish-assistant", action="store_true")
    init.add_argument("--enable-browser-form-fill", action="store_true")
    init.add_argument("--enable-post-publish-metrics-capture", action="store_true")
    init.add_argument("--enable-comment-evidence-capture", action="store_true")
    init.add_argument("--enable-business-attribution", action="store_true")
    init.add_argument("--enable-metrics-recovery", action="store_true")
    init.add_argument("--enable-next-round-optimization", action="store_true")

    run = subparsers.add_parser("run", help="Run jobs that are due.")
    run.add_argument("--config", required=True)
    run.add_argument("--state-file", default="")
    run.add_argument("--now", default="", help="ISO timestamp override for tests, e.g. 2026-07-07T00:00:00+00:00.")
    run.add_argument("--force", action="store_true")
    run.add_argument("--dry-run", action="store_true")

    task = subparsers.add_parser("windows-task", help="Write a PowerShell script that registers this scheduler with Windows Task Scheduler.")
    task.add_argument("--config", required=True)
    task.add_argument("--out-file", required=True)
    task.add_argument("--task-name", default="ENHE Promotion Manager")
    task.add_argument("--time", default="09:00", help="Daily run time in HH:MM.")
    task.add_argument("--state-file", default="")
    return parser.parse_args()


def init_config(args: argparse.Namespace) -> None:
    path = Path(args.config)
    path.parent.mkdir(parents=True, exist_ok=True)
    publish_enabled = (
        args.enable_publish_queue
        or args.enable_browser_publish_assistant
        or args.enable_browser_form_fill
    )
    browser_publish_assistant_enabled = args.enable_browser_publish_assistant or args.enable_browser_form_fill
    job: dict[str, Any] = {
        "id": args.job_id,
        "enabled": True,
        "schedule": {"intervalDays": args.interval_days},
        "input": input_from_args(args),
        "platforms": split_csv(args.platforms),
        "goal": "leads",
        "topN": 10,
        "liveOfficialCompetitors": False,
        "collectorPlatforms": ["youtube", "github"],
        "autoSearchCompetitors": args.auto_search_competitors,
        "searchHtmlSnapshotDir": args.search_html_snapshot_dir,
        "followUpCapture": {
            "enabled": args.run_follow_up_captures,
            "limit": 20,
            "dryRun": False,
            "captureBrowserAssisted": args.capture_browser_assisted_follow_ups,
            "sampleVideoFrames": args.sample_video_frames,
            "videoSampleCount": args.video_sample_count,
        },
        "skipCreatorLeaderboard": args.skip_creator_leaderboard,
        "creatorFollowUp": {"enabled": args.run_creator_follow_up, "limit": 20, "topN": 5, "dryRun": args.creator_follow_up_dry_run},
        "multiQueryViralDiscovery": {
            "enabled": args.enable_multi_query_viral_discovery,
            "dryRun": args.multi_query_dry_run,
            "queryCount": 5,
            "queries": [],
            "runFollowUpCaptures": args.run_follow_up_captures,
            "captureBrowserAssistedFollowUps": args.capture_browser_assisted_follow_ups,
            "sampleVideoFrames": args.sample_video_frames,
            "videoSampleCount": args.video_sample_count,
        },
        "competitorInformedContent": {"enabled": not args.skip_competitor_informed_content},
        "skipVideo": args.skip_video,
        "installBrowserIfMissing": args.install_browser_if_missing,
        "metrics": {},
        "postPublishMetricsCapture": {
            "enabled": args.enable_post_publish_metrics_capture,
            "limit": 20,
            "captureBrowserAssisted": args.capture_browser_assisted_follow_ups,
            "publishedItemsJson": [],
            "publishedUrls": [],
        },
        "commentEvidenceCapture": {
            "enabled": args.enable_comment_evidence_capture,
            "limit": 20,
            "platform": "auto",
            "structuredJson": "",
            "htmlFile": "",
            "textFile": "",
            "captureBrowserAssisted": False,
            "installBrowserIfMissing": False,
            "allowLocalhost": False,
            "publishedItemsJson": [],
            "publishedUrls": [],
        },
        "businessAttribution": {
            "enabled": args.enable_business_attribution,
            "businessCsv": [],
            "businessXlsx": [],
            "businessJson": [],
            "businessText": [],
            "publishedItemsJson": [],
            "publishedUrls": [],
        },
        "metricsRecovery": {
            "enabled": args.enable_metrics_recovery,
            "metricsCsv": [],
            "metricsXlsx": [],
            "metricsJson": [],
            "metricsText": [],
            "metricsStructuredJson": [],
            "businessCsv": [],
            "businessXlsx": [],
            "businessJson": [],
            "businessText": [],
            "publishedItemsJson": [],
            "publishedUrls": [],
            "githubRepos": [],
            "youtubeVideoIds": [],
        },
        "nextRoundOptimization": {"enabled": args.enable_next_round_optimization},
        "publish": {"enabled": publish_enabled, "mode": "queue_only", "execute": False, "approval": "", "douyin": {"videoFile": ""}},
        "browserPublishAssistant": {"enabled": browser_publish_assistant_enabled, "openBrowser": False, "platformPublishUrls": {}, "publishedUrls": [], "evidence": []},
        "browserFormFill": {
            "enabled": args.enable_browser_form_fill,
            "headed": False,
            "allowLocalhost": False,
            "installBrowserIfMissing": False,
            "timeoutMs": 30000,
            "waitUntil": "domcontentloaded",
        },
    }
    config = {
        "version": 1,
        "defaultOutputRoot": args.output_root,
        "jobs": [job],
        "guardrails": [
            "Runs local workflow generation on schedule.",
            "Official publishing is limited to verified API platforms and still requires explicit credentials and approval.",
            "Douyin publishing is browser-assisted/manual in the current setup; publish.douyin.videoFile only attaches an MP4 asset.",
            "No cookies, passwords, hidden browser tokens, or fabricated metrics are stored.",
        ],
    }
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Automation config written to: {path.resolve()}")


def run_due_jobs(args: argparse.Namespace) -> None:
    config_path = Path(args.config).resolve()
    base_dir = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    now = parse_now(args.now)
    state_path = Path(args.state_file).resolve() if args.state_file else base_dir / "promotion-automation-state.json"
    state = load_state(state_path)
    root = resolve_path(base_dir, config.get("defaultOutputRoot", "./promotion-output/automation"))
    root.mkdir(parents=True, exist_ok=True)

    run_records = []
    for job in config.get("jobs", []):
        record = evaluate_job(job, state, root, base_dir, now, args.force, args.dry_run)
        run_records.append(record)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updatedAt"] = now.isoformat()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "generatedAt": now.isoformat(),
        "config": str(config_path),
        "stateFile": str(state_path),
        "dryRun": args.dry_run,
        "force": args.force,
        "records": run_records,
        "guardrails": config.get("guardrails", []),
    }
    report_dir = root / "scheduler"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "automation-run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report_dir / "automation-run.md").write_text(render_run_report(report) + "\n", encoding="utf-8")
    print(f"Automation run report written to: {(report_dir / 'automation-run.json').resolve()}")


def evaluate_job(
    job: dict[str, Any],
    state: dict[str, Any],
    root: Path,
    base_dir: Path,
    now: datetime,
    force: bool,
    dry_run: bool,
) -> dict[str, Any]:
    job_id = str(job.get("id") or "unnamed-job")
    job_state = state.setdefault("jobs", {}).setdefault(job_id, {})
    if not job.get("enabled", True):
        return {"jobId": job_id, "status": "skipped", "reason": "job disabled"}
    due, reason = is_due(job, job_state, now, force)
    if not due:
        return {"jobId": job_id, "status": "not_due", "reason": reason, "lastRunAt": job_state.get("lastRunAt", "")}

    out_dir = root / safe_slug(job_id) / timestamp_slug(now)
    command = build_workflow_command(job, out_dir, base_dir)
    record: dict[str, Any] = {
        "jobId": job_id,
        "status": "planned" if dry_run else "running",
        "reason": reason,
        "outDir": str(out_dir),
        "command": display_command(command),
        "publish": job.get("publish", {"enabled": False}),
    }
    if dry_run:
        return record
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    manifest_path = out_dir / "reports/promotion-manager/agent-run/workflow-manifest.json"
    record.update(
        {
            "status": "ready" if result.returncode == 0 else "error",
            "exitCode": result.returncode,
            "stdoutTail": tail(result.stdout),
            "stderrTail": tail(result.stderr),
            "manifest": str(manifest_path) if manifest_path.exists() else "",
        }
    )
    publish_result: dict[str, Any] = {}
    browser_publish_result: dict[str, Any] = {}
    if result.returncode == 0 and manifest_path.exists() and publish_enabled(job):
        publish_result = run_publish_queue(job, out_dir, base_dir, manifest_path)
        record["publishQueue"] = publish_result
        if publish_result.get("report") and browser_publish_assistant_enabled(job):
            browser_publish_result = run_browser_publish_assistant(job, out_dir, base_dir, publish_result["report"])
            record["browserPublishAssistant"] = browser_publish_result
    if result.returncode == 0 and manifest_path.exists() and browser_form_fill_enabled(job):
        if browser_publish_result.get("report"):
            record["browserFormFill"] = run_browser_form_fill(job, out_dir, base_dir, browser_publish_result["report"])
        else:
            record["browserFormFill"] = browser_form_fill_blocked_result(
                "browserPublishAssistant.enabled must be true and produce a payload report before browserFormFill can run."
            )
    if result.returncode == 0 and manifest_path.exists() and multi_query_viral_discovery_enabled(job):
        multi_query_result = run_multi_query_viral_discovery(job, out_dir, base_dir, manifest_path)
        record["multiQueryViralDiscovery"] = multi_query_result
    post_publish_capture_result: dict[str, Any] = {}
    if result.returncode == 0 and manifest_path.exists() and post_publish_metrics_capture_enabled(job):
        post_publish_capture_result = run_post_publish_metrics_capture(job, out_dir, base_dir)
        record["postPublishMetricsCapture"] = post_publish_capture_result
    comment_evidence_result: dict[str, Any] = {}
    if result.returncode == 0 and manifest_path.exists() and comment_evidence_capture_enabled(job):
        comment_evidence_result = run_comment_evidence_capture(job, out_dir, base_dir)
        record["commentEvidenceCapture"] = comment_evidence_result
    business_attribution_result: dict[str, Any] = {}
    if result.returncode == 0 and manifest_path.exists() and business_attribution_enabled(job):
        business_attribution_result = run_business_attribution(job, out_dir, base_dir)
        record["businessAttribution"] = business_attribution_result
    if result.returncode == 0 and manifest_path.exists() and metrics_recovery_enabled(job):
        recovery_result = run_metrics_recovery(
            job,
            out_dir,
            base_dir,
            manifest_path,
            publish_result.get("report", ""),
            post_publish_capture_result,
            business_attribution_result,
        )
        record["metricsRecovery"] = recovery_result
    if result.returncode == 0 and manifest_path.exists() and next_round_optimization_enabled(job):
        optimization_result = run_next_round_optimization(
            job,
            out_dir,
            base_dir,
            manifest_path,
            publish_result.get("report", ""),
            record.get("metricsRecovery", {}),
            comment_evidence_result,
            business_attribution_result,
        )
        record["nextRoundOptimization"] = optimization_result
    job_state["lastRunAt"] = now.isoformat()
    job_state["lastStatus"] = record["status"]
    job_state["lastOutDir"] = str(out_dir)
    job_state["lastManifest"] = str(manifest_path) if manifest_path.exists() else ""
    if record.get("publishQueue", {}).get("report"):
        job_state["lastPublishQueue"] = record["publishQueue"]["report"]
    if record.get("browserPublishAssistant", {}).get("report"):
        job_state["lastBrowserPublishAssistant"] = record["browserPublishAssistant"]["report"]
    if record.get("browserFormFill", {}).get("reports"):
        job_state["lastBrowserFormFill"] = record["browserFormFill"]["reports"]
    if record.get("multiQueryViralDiscovery", {}).get("report"):
        job_state["lastMultiQueryViralDiscovery"] = record["multiQueryViralDiscovery"]["report"]
    if record.get("postPublishMetricsCapture", {}).get("report"):
        job_state["lastPostPublishMetricsCapture"] = record["postPublishMetricsCapture"]["report"]
    if record.get("commentEvidenceCapture", {}).get("report"):
        job_state["lastCommentEvidenceCapture"] = record["commentEvidenceCapture"]["report"]
    if record.get("businessAttribution", {}).get("report"):
        job_state["lastBusinessAttribution"] = record["businessAttribution"]["report"]
    if record.get("metricsRecovery", {}).get("report"):
        job_state["lastMetricsRecovery"] = record["metricsRecovery"]["report"]
    if record.get("nextRoundOptimization", {}).get("report"):
        job_state["lastNextRoundOptimization"] = record["nextRoundOptimization"]["report"]
    job_state["nextRunAfter"] = next_run_after(job, now).isoformat()
    return record


def publish_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("publish") or {}).get("enabled"))


def metrics_recovery_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("metricsRecovery") or {}).get("enabled"))


def browser_publish_assistant_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("browserPublishAssistant") or {}).get("enabled"))


def browser_form_fill_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("browserFormFill") or {}).get("enabled"))


def post_publish_metrics_capture_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("postPublishMetricsCapture") or {}).get("enabled"))


def comment_evidence_capture_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("commentEvidenceCapture") or {}).get("enabled"))


def business_attribution_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("businessAttribution") or {}).get("enabled"))


def multi_query_viral_discovery_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("multiQueryViralDiscovery") or {}).get("enabled"))


def next_round_optimization_enabled(job: dict[str, Any]) -> bool:
    return bool((job.get("nextRoundOptimization") or {}).get("enabled"))


def run_publish_queue(job: dict[str, Any], out_dir: Path, base_dir: Path, manifest_path: Path) -> dict[str, Any]:
    command = build_publish_queue_command(job, out_dir, base_dir, manifest_path)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"
    summary: dict[str, Any] = {}
    if report_path.exists():
        try:
            summary = json.loads(report_path.read_text(encoding="utf-8-sig")).get("summary", {})
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": "ready" if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "summary": summary,
    }


def run_browser_publish_assistant(job: dict[str, Any], out_dir: Path, base_dir: Path, publish_queue_path: str) -> dict[str, Any]:
    command = build_browser_publish_assistant_command(job, out_dir, base_dir, publish_queue_path)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/browser-publish/browser-publish-assistant.json"
    summary: dict[str, Any] = {}
    if report_path.exists():
        try:
            summary = json.loads(report_path.read_text(encoding="utf-8-sig")).get("summary", {})
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": "ready" if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "summary": summary,
    }


def run_browser_form_fill(job: dict[str, Any], out_dir: Path, base_dir: Path, browser_publish_report_path: str) -> dict[str, Any]:
    report_path = Path(browser_publish_report_path)
    try:
        browser_publish_report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return browser_form_fill_blocked_result(f"Browser publish assistant report could not be read: {browser_publish_report_path}")

    records = []
    for item in browser_publish_report.get("records", []):
        platform = str(item.get("platform") or "platform")
        payload_json = str(((item.get("payloadFiles") or {}).get("json") or "")).strip()
        payload_path = resolve_path(base_dir, payload_json) if payload_json else None
        if not payload_path or not payload_path.exists():
            records.append(
                {
                    "platform": platform,
                    "status": "blocked",
                    "reason": "Prepared browser publish payload JSON was missing.",
                    "payloadJson": payload_json,
                    "report": "",
                    "exitCode": None,
                }
            )
            continue

        form_out_dir = out_dir / "browser-form-fill-runs" / safe_slug(platform)
        command = build_browser_form_fill_command(job, form_out_dir, base_dir, payload_path)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        form_report_path = form_out_dir / "reports/promotion-manager/browser-publish/browser-form-fill.json"
        form_report: dict[str, Any] = {}
        if form_report_path.exists():
            try:
                form_report = json.loads(form_report_path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                form_report = {}
        filled_fields = form_report.get("filledFields", [])
        records.append(
            {
                "platform": platform,
                "status": form_report.get("status", "error") if result.returncode == 0 and form_report_path.exists() else "error",
                "command": display_command(command),
                "payloadJson": str(payload_path),
                "report": str(form_report_path) if form_report_path.exists() else "",
                "screenshot": str(((form_report.get("artifacts") or {}).get("screenshot") or "")),
                "filledFields": len(filled_fields) if isinstance(filled_fields, list) else 0,
                "missingFields": form_report.get("missingFields", []),
                "submitted": bool(form_report.get("submitted", False)),
                "finalPublishUserActionRequired": bool(form_report.get("finalPublishUserActionRequired", True)),
                "exitCode": result.returncode,
                "stdoutTail": tail(result.stdout),
                "stderrTail": tail(result.stderr),
            }
        )
    statuses = [str(item.get("status", "")) for item in records]
    summary = {
        "runs": len(records),
        "ready": sum(1 for status in statuses if status == "ready"),
        "blocked": sum(1 for status in statuses if status == "blocked"),
        "errors": sum(1 for status in statuses if status == "error"),
        "submitted": sum(1 for item in records if item.get("submitted")),
        "finalPublishUserActionRequired": sum(1 for item in records if item.get("finalPublishUserActionRequired")),
        "filledFields": sum(int(item.get("filledFields") or 0) for item in records),
    }
    if not records:
        status = "no_browser_publish_payloads"
    elif any(status == "error" for status in statuses):
        status = "error"
    elif any(status == "blocked" for status in statuses):
        status = "blocked"
    elif all(status == "ready" for status in statuses):
        status = "ready"
    else:
        status = "partial_ready"
    return {
        "status": status,
        "sourceReport": browser_publish_report_path,
        "records": records,
        "reports": [str(item.get("report")) for item in records if item.get("report")],
        "summary": summary,
        "guardrails": [
            "Visible fields only; no login, captcha, risk-control bypass, secret extraction, or hidden field reads.",
            "The helper stops before final publish and records finalPublishUserActionRequired.",
        ],
    }


def browser_form_fill_blocked_result(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "records": [],
        "reports": [],
        "summary": {"runs": 0, "ready": 0, "blocked": 1, "errors": 0, "submitted": 0, "finalPublishUserActionRequired": 0, "filledFields": 0},
        "guardrails": [
            "Browser form fill requires prepared browser-publish payload JSON.",
            "It never performs final publish without user action.",
        ],
    }


def run_multi_query_viral_discovery(job: dict[str, Any], out_dir: Path, base_dir: Path, manifest_path: Path) -> dict[str, Any]:
    command = build_multi_query_viral_discovery_command(job, out_dir, base_dir, manifest_path)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/competitors/multi-query-viral-discovery.json"
    summary: dict[str, Any] = {}
    status = "error"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            summary = report.get("summary", {})
            status = str(report.get("status") or "ready")
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": status if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "summary": summary,
    }


def run_post_publish_metrics_capture(job: dict[str, Any], out_dir: Path, base_dir: Path) -> dict[str, Any]:
    command = build_post_publish_metrics_capture_command(job, out_dir, base_dir)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json"
    metric_export_path = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json"
    summary: dict[str, Any] = {}
    status = "error"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            summary = report.get("summary", {})
            status = report.get("status", "ready")
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": status if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "metricExport": str(metric_export_path) if metric_export_path.exists() else "",
        "summary": summary,
    }


def run_comment_evidence_capture(job: dict[str, Any], out_dir: Path, base_dir: Path) -> dict[str, Any]:
    command = build_comment_evidence_capture_command(job, out_dir, base_dir)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"
    export_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json"
    summary: dict[str, Any] = {}
    status = "error"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            summary = report.get("summary", {})
            status = report.get("status", "ready")
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": status if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "commentEvidenceExport": str(export_path) if export_path.exists() else "",
        "summary": summary,
    }


def run_business_attribution(job: dict[str, Any], out_dir: Path, base_dir: Path) -> dict[str, Any]:
    command = build_business_attribution_command(job, out_dir, base_dir)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"
    export_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json"
    summary: dict[str, Any] = {}
    status = "error"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            summary = report.get("summary", {})
            status = report.get("status", "ready")
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": status if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "businessAttributionExport": str(export_path) if export_path.exists() else "",
        "summary": summary,
    }


def run_metrics_recovery(
    job: dict[str, Any],
    out_dir: Path,
    base_dir: Path,
    manifest_path: Path,
    publish_queue_path: str,
    post_publish_capture_result: dict[str, Any] | None = None,
    business_attribution_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = build_metrics_recovery_command(
        job,
        out_dir,
        base_dir,
        manifest_path,
        publish_queue_path,
        post_publish_capture_result or {},
        business_attribution_result or {},
    )
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"
    summary: dict[str, Any] = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            summary = {
                "recoveryStatus": report.get("recoveryStatus", ""),
                "retrospectiveStatus": (report.get("retrospective") or {}).get("status", ""),
                "recordsWithMetrics": (report.get("coverage") or {}).get("recordsWithMetrics", 0),
                "manualOrPendingRequirements": (report.get("coverage") or {}).get("manualOrPendingRequirements", 0),
            }
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": "ready" if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "summary": summary,
    }


def run_next_round_optimization(
    job: dict[str, Any],
    out_dir: Path,
    base_dir: Path,
    manifest_path: Path,
    publish_queue_path: str,
    metrics_recovery_result: dict[str, Any] | None = None,
    comment_evidence_result: dict[str, Any] | None = None,
    business_attribution_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = build_next_round_optimization_command(
        job,
        out_dir,
        base_dir,
        manifest_path,
        publish_queue_path,
        metrics_recovery_result or {},
        comment_evidence_result or {},
        business_attribution_result or {},
    )
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = out_dir / "reports/promotion-manager/optimization/next-round-optimization.json"
    summary: dict[str, Any] = {}
    status = "error"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            coverage = report.get("evidenceCoverage") or {}
            summary = {
                "status": report.get("status", ""),
                "metricRecords": coverage.get("metricRecords", 0),
                "commentCount": coverage.get("commentCount", 0),
                "businessAttributions": coverage.get("businessAttributions", 0),
                "nextRoundContent": len(report.get("nextRoundContent", [])),
            }
            status = report.get("status", "ready")
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": status if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
        "report": str(report_path) if report_path.exists() else "",
        "summary": summary,
    }


def build_metrics_recovery_command(
    job: dict[str, Any],
    out_dir: Path,
    base_dir: Path,
    manifest_path: Path,
    publish_queue_path: str,
    post_publish_capture_result: dict[str, Any] | None = None,
    business_attribution_result: dict[str, Any] | None = None,
) -> list[str]:
    recovery = job.get("metricsRecovery") or {}
    command = [
        sys.executable,
        str(METRICS_RECOVERY),
        "--workflow-manifest",
        str(manifest_path),
        "--out-dir",
        str(out_dir),
    ]
    if publish_queue_path:
        command.extend(["--publish-queue", publish_queue_path])
    append_many(command, "--published-items-json", recovery.get("publishedItemsJson"), base_dir)
    append_many(command, "--published-url", recovery.get("publishedUrls"))
    append_many(command, "--github-repo", recovery.get("githubRepos"))
    append_many(command, "--youtube-video-id", recovery.get("youtubeVideoIds"))
    append_many(command, "--metrics-csv", recovery.get("metricsCsv"), base_dir)
    append_many(command, "--business-csv", recovery.get("businessCsv"), base_dir)
    append_many(command, "--business-xlsx", recovery.get("businessXlsx"), base_dir)
    append_many(command, "--metrics-xlsx", recovery.get("metricsXlsx"), base_dir)
    append_many(command, "--metrics-json", recovery.get("metricsJson"), base_dir)
    append_many(command, "--metrics-text", recovery.get("metricsText"), base_dir)
    append_many(command, "--metrics-structured-json", recovery.get("metricsStructuredJson"), base_dir)
    append_many(command, "--business-json", recovery.get("businessJson"), base_dir)
    append_many(command, "--business-text", recovery.get("businessText"), base_dir)
    metric_export = (post_publish_capture_result or {}).get("metricExport")
    if metric_export:
        command.extend(["--metrics-json", metric_export])
    attribution_export = (business_attribution_result or {}).get("businessAttributionExport")
    if attribution_export:
        command.extend(["--business-json", attribution_export])
    return command


def build_next_round_optimization_command(
    job: dict[str, Any],
    out_dir: Path,
    base_dir: Path,
    manifest_path: Path,
    publish_queue_path: str,
    metrics_recovery_result: dict[str, Any] | None = None,
    comment_evidence_result: dict[str, Any] | None = None,
    business_attribution_result: dict[str, Any] | None = None,
) -> list[str]:
    optimization = job.get("nextRoundOptimization") or {}
    command = [
        sys.executable,
        str(NEXT_ROUND_OPTIMIZER),
        "--workflow-manifest",
        str(manifest_path),
        "--out-dir",
        str(out_dir),
    ]
    if publish_queue_path:
        command.extend(["--publish-queue", publish_queue_path])
    recovery_report = (metrics_recovery_result or {}).get("report") or optimization.get("metricsRecoveryJson")
    if recovery_report:
        command.extend(["--metrics-recovery-json", str(resolve_path(base_dir, recovery_report) if optimization.get("metricsRecoveryJson") else recovery_report)])
    comment_report = (comment_evidence_result or {}).get("commentEvidenceExport") or (comment_evidence_result or {}).get("report") or optimization.get("commentEvidenceJson")
    if comment_report:
        command.extend(["--comment-evidence-json", str(resolve_path(base_dir, comment_report) if optimization.get("commentEvidenceJson") else comment_report)])
    business_report = (business_attribution_result or {}).get("report") or optimization.get("businessAttributionJson")
    if business_report:
        command.extend(["--business-attribution-json", str(resolve_path(base_dir, business_report) if optimization.get("businessAttributionJson") else business_report)])
    return command


def build_post_publish_metrics_capture_command(job: dict[str, Any], out_dir: Path, base_dir: Path) -> list[str]:
    capture = job.get("postPublishMetricsCapture") or {}
    command = [
        sys.executable,
        str(POST_PUBLISH_METRICS_CAPTURE),
        "--out-dir",
        str(out_dir),
    ]
    command.extend(["--limit", str(capture.get("limit") or 20)])
    append_many(command, "--published-items-json", capture.get("publishedItemsJson"), base_dir)
    append_many(command, "--published-url", capture.get("publishedUrls"))
    if capture.get("captureBrowserAssisted"):
        command.append("--capture-browser-assisted")
    if capture.get("installBrowserIfMissing"):
        command.append("--install-browser-if-missing")
    if capture.get("allowLocalhost"):
        command.append("--allow-localhost")
    return command


def build_comment_evidence_capture_command(job: dict[str, Any], out_dir: Path, base_dir: Path) -> list[str]:
    capture = job.get("commentEvidenceCapture") or {}
    command = [
        sys.executable,
        str(COMMENT_EVIDENCE_CAPTURE),
        "--out-dir",
        str(out_dir),
    ]
    command.extend(["--limit", str(capture.get("limit") or 20)])
    append_many(command, "--published-items-json", capture.get("publishedItemsJson"), base_dir)
    append_many(command, "--published-url", capture.get("publishedUrls"))
    append_if_present(command, "--platform", capture.get("platform"))
    if capture.get("structuredJson"):
        command.extend(["--structured-json", str(resolve_path(base_dir, capture["structuredJson"]))])
    if capture.get("htmlFile"):
        command.extend(["--html-file", str(resolve_path(base_dir, capture["htmlFile"]))])
    if capture.get("textFile"):
        command.extend(["--text-file", str(resolve_path(base_dir, capture["textFile"]))])
    if capture.get("captureBrowserAssisted"):
        command.append("--capture-browser-assisted")
    if capture.get("installBrowserIfMissing"):
        command.append("--install-browser-if-missing")
    if capture.get("allowLocalhost"):
        command.append("--allow-localhost")
    return command


def build_business_attribution_command(job: dict[str, Any], out_dir: Path, base_dir: Path) -> list[str]:
    attribution = job.get("businessAttribution") or {}
    command = [
        sys.executable,
        str(BUSINESS_ATTRIBUTION),
        "--out-dir",
        str(out_dir),
    ]
    append_many(command, "--business-csv", attribution.get("businessCsv"), base_dir)
    append_many(command, "--business-xlsx", attribution.get("businessXlsx"), base_dir)
    append_many(command, "--business-json", attribution.get("businessJson"), base_dir)
    append_many(command, "--business-text", attribution.get("businessText"), base_dir)
    append_many(command, "--published-items-json", attribution.get("publishedItemsJson"), base_dir)
    append_many(command, "--published-url", attribution.get("publishedUrls"))
    return command


def build_publish_queue_command(job: dict[str, Any], out_dir: Path, base_dir: Path, manifest_path: Path) -> list[str]:
    publish = job.get("publish") or {}
    command = [
        sys.executable,
        str(PUBLISH_QUEUE),
        "--workflow-manifest",
        str(manifest_path),
        "--promotion-out-dir",
        str(out_dir),
        "--out-dir",
        str(out_dir),
    ]
    append_if_present(command, "--platforms", comma_value(publish.get("platforms")))
    if publish.get("execute"):
        command.append("--execute")
        append_if_present(command, "--approval", publish.get("approval"))

    github = publish.get("github") or {}
    append_if_present(command, "--github-repo", github.get("repo"))
    append_if_present(command, "--github-action", github.get("action"))
    append_if_present(command, "--github-path", github.get("path"))
    append_if_present(command, "--github-branch", github.get("branch"))
    append_if_present(command, "--github-tag-name", github.get("tagName"))

    youtube = publish.get("youtube") or {}
    if youtube.get("videoFile"):
        command.extend(["--youtube-video-file", str(resolve_path(base_dir, youtube["videoFile"]))])
    append_if_present(command, "--youtube-privacy-status", youtube.get("privacyStatus"))
    append_if_present(command, "--youtube-category-id", youtube.get("categoryId"))

    douyin = publish.get("douyin") or {}
    if douyin.get("videoFile"):
        command.extend(["--douyin-video-file", str(resolve_path(base_dir, douyin["videoFile"]))])
    return command


def build_browser_publish_assistant_command(job: dict[str, Any], out_dir: Path, base_dir: Path, publish_queue_path: str) -> list[str]:
    assistant = job.get("browserPublishAssistant") or {}
    command = [
        sys.executable,
        str(BROWSER_PUBLISH_ASSISTANT),
        "--publish-queue",
        publish_queue_path,
        "--out-dir",
        str(out_dir),
    ]
    append_if_present(command, "--platforms", comma_value(assistant.get("platforms")))
    if assistant.get("openBrowser"):
        command.append("--open-browser")
    for item in key_value_options(assistant.get("platformPublishUrls"), base_dir=base_dir):
        command.extend(["--platform-publish-url", item])
    for item in key_value_options(assistant.get("publishedUrls")):
        command.extend(["--published-url", item])
    append_many(command, "--evidence", assistant.get("evidence"))
    return command


def build_browser_form_fill_command(job: dict[str, Any], out_dir: Path, base_dir: Path, payload_path: Path) -> list[str]:
    fill = job.get("browserFormFill") or {}
    command = [
        sys.executable,
        str(BROWSER_PUBLISH_FORM_FILL),
        "--payload-json",
        str(payload_path),
        "--out-dir",
        str(out_dir),
        "--timeout-ms",
        str(fill.get("timeoutMs") or 30000),
        "--wait-until",
        str(fill.get("waitUntil") or "domcontentloaded"),
    ]
    if fill.get("headed"):
        command.append("--headed")
    if fill.get("allowLocalhost"):
        command.append("--allow-localhost")
    if fill.get("installBrowserIfMissing"):
        command.append("--install-browser-if-missing")
    return command


def build_multi_query_viral_discovery_command(job: dict[str, Any], out_dir: Path, base_dir: Path, manifest_path: Path) -> list[str]:
    discovery = job.get("multiQueryViralDiscovery") or {}
    command = [
        sys.executable,
        str(MULTI_QUERY_VIRAL_DISCOVERY),
        "--workflow-manifest",
        str(manifest_path),
        "--out-dir",
        str(out_dir),
    ]
    command.extend(["--platforms", comma_value(discovery.get("platforms")) or comma_value(job.get("platforms")) or ",".join(DEFAULT_PLATFORMS)])
    command.extend(["--top-n", str(discovery.get("topN") or job.get("topN") or 20)])
    if discovery.get("queryCount") is not None:
        command.extend(["--query-count", str(discovery.get("queryCount"))])
    append_many(command, "--query", discovery.get("queries") or discovery.get("query"))
    html_root = discovery.get("htmlSnapshotRoot") or discovery.get("htmlSnapshotDir") or ""
    if html_root:
        command.extend(["--html-snapshot-root", str(resolve_path(base_dir, html_root))])
    if discovery.get("dryRun"):
        command.append("--dry-run")
    if discovery.get("installBrowserIfMissing"):
        command.append("--install-browser-if-missing")
    if discovery.get("liveOfficial"):
        command.append("--live-official")
    if discovery.get("runCreatorFollowUp"):
        command.append("--run-creator-follow-up")
    if discovery.get("creatorFollowUpDryRun"):
        command.append("--creator-follow-up-dry-run")
    if discovery.get("runFollowUpCaptures"):
        command.append("--run-follow-up-captures")
    if discovery.get("followUpDryRun"):
        command.append("--follow-up-dry-run")
    if discovery.get("captureBrowserAssistedFollowUps"):
        command.append("--capture-browser-assisted-follow-ups")
    if discovery.get("sampleVideoFrames"):
        command.append("--sample-video-frames")
        command.extend(["--video-sample-count", str(discovery.get("videoSampleCount") or 5)])
    return command


def build_workflow_command(job: dict[str, Any], out_dir: Path, base_dir: Path) -> list[str]:
    command = [sys.executable, str(SCRIPTS / "run_promotion_workflow.py")]
    source = job.get("input") or {}
    if source.get("browserUrl"):
        command.extend(["--browser-url", str(source["browserUrl"])])
    elif source.get("productUrl"):
        command.extend(["--product-url", str(source["productUrl"])])
    elif source.get("htmlFile"):
        command.extend(["--html-file", str(resolve_path(base_dir, source["htmlFile"]))])
    elif source.get("textFile"):
        command.extend(["--text-file", str(resolve_path(base_dir, source["textFile"]))])
    elif source.get("structuredJson"):
        command.extend(["--structured-json", str(resolve_path(base_dir, source["structuredJson"]))])
    else:
        raise SystemExit(f"Job {job.get('id')} is missing an input source.")

    append_if_present(command, "--product-name", job.get("productName"))
    append_if_present(command, "--audience", comma_value(job.get("audience")))
    append_if_present(command, "--pain-points", comma_value(job.get("painPoints")))
    append_if_present(command, "--value-proposition", job.get("valueProposition"))
    append_if_present(command, "--pricing", job.get("pricing"))
    append_if_present(command, "--competitor-query", job.get("competitorQuery"))
    command.extend(["--goal", str(job.get("goal") or "leads")])
    command.extend(["--platforms", comma_value(job.get("platforms")) or ",".join(DEFAULT_PLATFORMS)])
    command.extend(["--top-n", str(job.get("topN") or 10)])
    if job.get("liveOfficialCompetitors"):
        command.append("--live-official-competitors")
    if job.get("collectorPlatforms"):
        command.extend(["--collector-platforms", comma_value(job.get("collectorPlatforms"))])
    if job.get("autoSearchCompetitors"):
        command.append("--auto-search-competitors")
    if job.get("searchHtmlSnapshotDir"):
        command.extend(["--search-html-snapshot-dir", str(resolve_path(base_dir, job["searchHtmlSnapshotDir"]))])
    if job.get("searchSnapshotDir"):
        command.extend(["--search-snapshot-dir", str(resolve_path(base_dir, job["searchSnapshotDir"]))])
    follow_up = job.get("followUpCapture") or {}
    if follow_up.get("enabled"):
        command.append("--run-follow-up-captures")
        command.extend(["--follow-up-capture-limit", str(follow_up.get("limit") or 20)])
        if follow_up.get("dryRun"):
            command.append("--follow-up-dry-run")
        if follow_up.get("allowLocalhost"):
            command.append("--allow-localhost-follow-up")
        if follow_up.get("captureBrowserAssisted"):
            command.append("--capture-browser-assisted-follow-ups")
        if follow_up.get("sampleVideoFrames"):
            command.append("--sample-video-frames")
            command.extend(["--video-sample-count", str(follow_up.get("videoSampleCount") or 5)])
    if job.get("skipCreatorLeaderboard"):
        command.append("--skip-creator-leaderboard")
    creator_follow_up = job.get("creatorFollowUp") or {}
    if creator_follow_up.get("enabled"):
        command.append("--run-creator-follow-up")
        command.extend(["--creator-follow-up-limit", str(creator_follow_up.get("limit") or 20)])
        command.extend(["--creator-follow-up-top-n", str(creator_follow_up.get("topN") or 5)])
        if creator_follow_up.get("dryRun"):
            command.append("--creator-follow-up-dry-run")
    competitor_informed = job.get("competitorInformedContent")
    if isinstance(competitor_informed, dict):
        if competitor_informed.get("enabled") is False:
            command.append("--skip-competitor-informed-content")
        elif competitor_informed.get("enabled"):
            command.append("--use-competitor-informed-content")
    if job.get("skipCompetitorDiscovery"):
        command.append("--skip-competitor-discovery")
    if job.get("installBrowserIfMissing"):
        command.append("--install-browser-if-missing")
    if job.get("skipVideo"):
        command.append("--skip-video")
    append_if_present(command, "--video-platforms", comma_value(job.get("videoPlatforms")))
    if job.get("generateVoiceover"):
        command.append("--generate-voiceover")
    metrics = job.get("metrics") or {}
    for key, flag in [
        ("csvFile", "--metrics-csv"),
        ("xlsxFile", "--metrics-xlsx"),
        ("jsonFile", "--metrics-json"),
        ("textFile", "--metrics-text"),
        ("publishedUrl", "--published-url"),
        ("githubRepo", "--github-repo"),
        ("youtubeVideoId", "--youtube-video-id"),
    ]:
        if metrics.get(key):
            value = metrics[key]
            if key.endswith("File"):
                value = str(resolve_path(base_dir, value))
            command.extend([flag, str(value)])
            break
    append_if_present(command, "--metrics-platform", metrics.get("platform"))
    command.extend(["--out-dir", str(out_dir)])
    return command


def write_windows_task_script(args: argparse.Namespace) -> None:
    config_path = Path(args.config).resolve()
    state_path = Path(args.state_file).resolve() if args.state_file else config_path.parent / "promotion-automation-state.json"
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    argument = (
        f'"{SCRIPTS / "automation_scheduler.py"}" run '
        f'--config "{config_path}" '
        f'--state-file "{state_path}"'
    )
    script = f"""$Action = New-ScheduledTaskAction -Execute "python" -Argument {ps_quote(argument)} -WorkingDirectory {ps_quote(str(ROOT))}
$Trigger = New-ScheduledTaskTrigger -Daily -At {ps_quote(args.time)}
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName {ps_quote(args.task_name)} -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs the ENHE Product Promo Maker scheduler." -Force
"""
    out_path.write_text(script, encoding="utf-8")
    print(f"Windows scheduled task script written to: {out_path.resolve()}")


def is_due(job: dict[str, Any], job_state: dict[str, Any], now: datetime, force: bool) -> tuple[bool, str]:
    if force:
        return True, "forced"
    last_run = parse_optional_datetime(job_state.get("lastRunAt"))
    if not last_run:
        return True, "never_run"
    interval = int((job.get("schedule") or {}).get("intervalDays") or 7)
    due_at = last_run + timedelta(days=interval)
    if now >= due_at:
        return True, f"due_at_{due_at.isoformat()}"
    return False, f"next_run_after_{due_at.isoformat()}"


def next_run_after(job: dict[str, Any], now: datetime) -> datetime:
    interval = int((job.get("schedule") or {}).get("intervalDays") or 7)
    return now + timedelta(days=interval)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "jobs": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def input_from_args(args: argparse.Namespace) -> dict[str, str]:
    if args.browser_url:
        return {"browserUrl": args.browser_url}
    if args.product_url:
        return {"productUrl": args.product_url}
    if args.html_file:
        return {"htmlFile": args.html_file}
    if args.text_file:
        return {"textFile": args.text_file}
    return {"structuredJson": args.structured_json}


def render_run_report(report: dict[str, Any]) -> str:
    lines = [
        "# Promotion Automation Run",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Dry run: {report['dryRun']}",
        f"- Force: {report['force']}",
        "",
        "## Jobs",
    ]
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['jobId']}",
                f"- Status: `{record['status']}`",
                f"- Reason: {record.get('reason', '')}",
                f"- Output: {record.get('outDir', '')}",
                f"- Manifest: {record.get('manifest', '')}",
            ]
        )
        if record.get("publishQueue"):
            lines.append(f"- Publish queue: {record['publishQueue'].get('report', '')}")
        if record.get("browserPublishAssistant"):
            lines.append(f"- Browser publish assistant: {record['browserPublishAssistant'].get('report', '')}")
        if record.get("browserFormFill"):
            lines.append(f"- Browser form fill: {record['browserFormFill'].get('status', '')} ({record['browserFormFill'].get('summary', {}).get('runs', 0)} run(s))")
        if record.get("multiQueryViralDiscovery"):
            lines.append(f"- Multi-query viral discovery: {record['multiQueryViralDiscovery'].get('report', '')}")
        if record.get("postPublishMetricsCapture"):
            lines.append(f"- Post-publish metrics capture: {record['postPublishMetricsCapture'].get('report', '')}")
        if record.get("commentEvidenceCapture"):
            lines.append(f"- Comment evidence capture: {record['commentEvidenceCapture'].get('report', '')}")
        if record.get("businessAttribution"):
            lines.append(f"- Business attribution: {record['businessAttribution'].get('report', '')}")
        if record.get("metricsRecovery"):
            lines.append(f"- Metrics recovery: {record['metricsRecovery'].get('report', '')}")
        if record.get("nextRoundOptimization"):
            lines.append(f"- Next-round optimization: {record['nextRoundOptimization'].get('report', '')}")
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report.get("guardrails", [])])
    return "\n".join(lines)


def resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def parse_now(value: str) -> datetime:
    if value:
        return normalize_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
    return datetime.now(timezone.utc)


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return normalize_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def append_if_present(command: list[str], flag: str, value: Any) -> None:
    text = "" if value is None else str(value).strip()
    if text:
        command.extend([flag, text])


def append_many(command: list[str], flag: str, value: Any, base_dir: Path | None = None) -> None:
    values = value if isinstance(value, list) else [value]
    for item in values:
        text = "" if item is None else str(item).strip()
        if not text:
            continue
        if base_dir is not None:
            text = str(resolve_path(base_dir, text))
        command.extend([flag, text])


def key_value_options(value: Any, base_dir: Path | None = None) -> list[str]:
    if isinstance(value, dict):
        items = [f"{key}={val}" for key, val in value.items()]
    elif isinstance(value, list):
        items = [str(item) for item in value if str(item).strip()]
    elif value:
        items = [str(value)]
    else:
        items = []
    if base_dir is None:
        return items
    result = []
    for item in items:
        if "=" not in item:
            result.append(item)
            continue
        key, val = item.split("=", 1)
        result.append(f"{key}={resolve_path(base_dir, val) if looks_like_local_path(val) else val}")
    return result


def looks_like_local_path(value: str) -> bool:
    return bool(value) and not value.startswith(("http://", "https://"))


def comma_value(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    return "" if value is None else str(value).strip()


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def safe_slug(value: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-") or "job"


def timestamp_slug(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


if __name__ == "__main__":
    main()
