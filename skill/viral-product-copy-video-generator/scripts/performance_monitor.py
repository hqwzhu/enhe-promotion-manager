#!/usr/bin/env python3
"""Run post-publish performance monitoring from proven evidence sources."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
REPORT_DIR = Path("reports/promotion-manager/performance-monitor")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    steps = run_monitor(args, out_dir)
    report = build_report(args, out_dir, steps)
    write_report(out_dir, report)
    append_history(out_dir, report)
    print(f"Performance monitor written to: {(monitor_dir(out_dir) / 'performance-monitor.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture public metrics/comments, merge real exports, and produce next-round recommendations."
    )
    parser.add_argument("--published-items-json", action="append", default=[], help="Published items JSON evidence.")
    parser.add_argument("--published-url", action="append", default=[], help="Published URL, or platform=url.")
    parser.add_argument("--metrics-csv", action="append", default=[], help="Platform metrics CSV export.")
    parser.add_argument("--metrics-xlsx", action="append", default=[], help="Platform metrics .xlsx export.")
    parser.add_argument("--metrics-json", action="append", default=[], help="Platform metrics JSON export.")
    parser.add_argument("--metrics-text", action="append", default=[], help="Copied metrics text evidence.")
    parser.add_argument("--metrics-structured-json", action="append", default=[], help="Codex/browser metrics snapshot.")
    parser.add_argument("--business-csv", action="append", default=[], help="Order/revenue CSV export.")
    parser.add_argument("--business-xlsx", action="append", default=[], help="Order/revenue .xlsx export.")
    parser.add_argument("--business-json", action="append", default=[], help="Order/revenue JSON export.")
    parser.add_argument("--business-text", action="append", default=[], help="Copied order/revenue text evidence.")
    parser.add_argument("--workflow-manifest", default="", help="Optional workflow-manifest.json context.")
    parser.add_argument("--publish-queue", default="", help="Optional publish-queue.json context.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--capture-browser-assisted", action="store_true")
    parser.add_argument("--install-browser-if-missing", action="store_true")
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost URLs for local fixtures/tests only.")
    parser.add_argument("--skip-post-publish-metrics", action="store_true")
    parser.add_argument("--skip-comment-evidence", action="store_true")
    parser.add_argument("--skip-business-attribution", action="store_true")
    parser.add_argument("--skip-metrics-recovery", action="store_true")
    parser.add_argument("--skip-next-round-optimization", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run_monitor(args: argparse.Namespace, out_dir: Path) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not args.skip_post_publish_metrics:
        steps.append(run_post_publish_metrics(args, out_dir))
    if not args.skip_comment_evidence:
        steps.append(run_comment_evidence(args, out_dir))
    if has_business_sources(args) and not args.skip_business_attribution:
        steps.append(run_business_attribution(args, out_dir))
    if not args.skip_metrics_recovery:
        steps.append(run_metrics_recovery(args, out_dir))
    if not args.skip_next_round_optimization:
        steps.append(run_next_round_optimizer(args, out_dir))
    if not steps:
        steps.append({"id": "monitor", "status": "skipped", "reason": "All monitor stages were skipped."})
    return steps


def run_post_publish_metrics(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPTS / "post_publish_metrics_capture.py"),
        "--out-dir",
        str(out_dir),
        "--limit",
        str(args.limit),
        "--timeout-ms",
        str(args.timeout_ms),
    ]
    add_published_sources(command, args)
    if args.capture_browser_assisted:
        command.append("--capture-browser-assisted")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    if args.allow_localhost:
        command.append("--allow-localhost")
    report_path = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json"
    return run_step(args, "post_publish_metrics_capture", command, report_path)


def run_comment_evidence(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
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
    add_published_sources(command, args)
    if args.capture_browser_assisted:
        command.append("--capture-browser-assisted")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    if args.allow_localhost:
        command.append("--allow-localhost")
    report_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"
    return run_step(args, "comment_evidence_capture", command, report_path)


def run_business_attribution(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    command = [sys.executable, str(SCRIPTS / "business_attribution.py"), "--out-dir", str(out_dir)]
    add_published_sources(command, args)
    add_repeated(command, "--business-csv", args.business_csv)
    add_repeated(command, "--business-xlsx", args.business_xlsx)
    add_repeated(command, "--business-json", args.business_json)
    add_repeated(command, "--business-text", args.business_text)
    report_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"
    return run_step(args, "business_attribution", command, report_path)


def run_metrics_recovery(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    command = [sys.executable, str(SCRIPTS / "metrics_recovery.py"), "--out-dir", str(out_dir)]
    add_optional(command, "--workflow-manifest", args.workflow_manifest)
    add_optional(command, "--publish-queue", args.publish_queue)
    add_published_sources(command, args)
    add_repeated(command, "--metrics-csv", args.metrics_csv)
    add_repeated(command, "--metrics-xlsx", args.metrics_xlsx)
    add_repeated(command, "--metrics-json", args.metrics_json)
    add_repeated(command, "--metrics-text", args.metrics_text)
    add_repeated(command, "--metrics-structured-json", args.metrics_structured_json)

    post_publish_export = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json"
    if post_publish_export.exists():
        command.extend(["--metrics-json", str(post_publish_export)])

    business_export = out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json"
    if business_export.exists():
        command.extend(["--business-json", str(business_export)])
    else:
        add_repeated(command, "--business-csv", args.business_csv)
        add_repeated(command, "--business-xlsx", args.business_xlsx)
        add_repeated(command, "--business-json", args.business_json)
        add_repeated(command, "--business-text", args.business_text)

    report_path = out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"
    return run_step(args, "metrics_recovery", command, report_path)


def run_next_round_optimizer(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    command = [sys.executable, str(SCRIPTS / "next_round_optimizer.py"), "--out-dir", str(out_dir)]
    metrics_recovery = out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"
    comment_export = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json"
    business_report = out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"
    add_optional(command, "--workflow-manifest", args.workflow_manifest)
    add_optional(command, "--publish-queue", args.publish_queue)
    if metrics_recovery.exists():
        command.extend(["--metrics-recovery-json", str(metrics_recovery)])
    if comment_export.exists():
        command.extend(["--comment-evidence-json", str(comment_export)])
    if business_report.exists():
        command.extend(["--business-attribution-json", str(business_report)])
    report_path = out_dir / "reports/promotion-manager/optimization/next-round-optimization.json"
    return run_step(args, "next_round_optimizer", command, report_path)


def run_step(args: argparse.Namespace, step_id: str, command: list[str], report_path: Path) -> dict[str, Any]:
    step = {
        "id": step_id,
        "command": display_command(command),
        "report": str(report_path),
    }
    if args.dry_run:
        step.update({"status": "dry_run", "exitCode": None})
        return step
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report = read_json(report_path)
    step.update(
        {
            "status": step_status(result.returncode, report),
            "exitCode": result.returncode,
            "stdoutTail": tail(result.stdout),
            "stderrTail": tail(result.stderr),
            "reportExists": report_path.exists(),
            "reportStatus": report_status(report),
            "summary": step_summary(step_id, report),
        }
    )
    return step


def build_report(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = artifacts_for(out_dir)
    reports = {name: read_json(path) for name, path in artifacts.items()}
    summary = monitor_summary(steps, reports)
    return {
        "generatedAt": TODAY,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "status": monitor_status(summary, steps),
        "outDir": str(out_dir),
        "input": {
            "publishedItemsJson": args.published_items_json,
            "publishedUrls": args.published_url,
            "metricsSources": source_summary(args, "metrics"),
            "businessSources": source_summary(args, "business"),
            "captureBrowserAssisted": args.capture_browser_assisted,
            "dryRun": args.dry_run,
        },
        "summary": summary,
        "steps": steps,
        "artifacts": {name: str(path) for name, path in artifacts.items()},
        "nextCommands": next_commands(out_dir),
        "guardrails": guardrails(),
    }


def monitor_summary(steps: list[dict[str, Any]], reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    post_summary = (reports.get("postPublishMetrics") or {}).get("summary") or {}
    comment_report = reports.get("commentEvidence") or {}
    business_summary = (reports.get("businessAttribution") or {}).get("summary") or {}
    metrics_recovery = reports.get("metricsRecovery") or {}
    next_round = reports.get("nextRoundOptimization") or {}
    coverage = next_round.get("evidenceCoverage") or {}
    return {
        "steps": len(steps),
        "failedSteps": sum(1 for step in steps if step.get("status") == "error"),
        "readySteps": sum(1 for step in steps if step.get("status") in {"ready", "partial_ready"}),
        "capturedMetricRecords": int(post_summary.get("capturedMetricRecords") or 0),
        "commentCount": int(comment_report.get("summary", {}).get("commentCount") or len(comment_report.get("comments", [])) or 0),
        "demandSignalCount": int(comment_report.get("summary", {}).get("demandSignalCount") or len(comment_report.get("demandSignals", [])) or 0),
        "matchedBusinessRows": int(business_summary.get("matchedRows") or business_summary.get("attributions") or 0),
        "metricsRecoveryStatus": metrics_recovery.get("recoveryStatus", ""),
        "nextRoundStatus": next_round.get("status", ""),
        "nextRoundMetricRecords": int(coverage.get("metricRecords") or 0),
        "nextRoundBusinessAttributions": int(coverage.get("businessAttributions") or 0),
        "manualOrPendingRequirements": int(coverage.get("manualOrPendingRequirements") or 0),
    }


def monitor_status(summary: dict[str, Any], steps: list[dict[str, Any]]) -> str:
    if any(step.get("status") == "dry_run" for step in steps):
        return "dry_run"
    if summary["failedSteps"]:
        return "partial_ready"
    has_evidence = any(
        int(summary.get(key) or 0) > 0
        for key in ("capturedMetricRecords", "commentCount", "matchedBusinessRows", "nextRoundMetricRecords", "nextRoundBusinessAttributions")
    )
    if not has_evidence:
        return "waiting_real_data"
    if summary.get("nextRoundStatus") == "ready":
        return "ready"
    return "partial_ready"


def step_summary(step_id: str, report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return {}
    if step_id == "post_publish_metrics_capture":
        return report.get("summary") or {}
    if step_id == "comment_evidence_capture":
        return report.get("summary") or {"commentCount": len(report.get("comments", []))}
    if step_id == "business_attribution":
        return report.get("summary") or {}
    if step_id == "metrics_recovery":
        retrospective = report.get("retrospective") or {}
        return {
            "recoveryStatus": report.get("recoveryStatus", ""),
            "records": len(report.get("records", [])),
            "retrospectiveStatus": retrospective.get("status", ""),
        }
    if step_id == "next_round_optimizer":
        return {"status": report.get("status", ""), "evidenceCoverage": report.get("evidenceCoverage", {})}
    return {}


def artifacts_for(out_dir: Path) -> dict[str, Path]:
    return {
        "postPublishMetrics": out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json",
        "postPublishMetricExport": out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json",
        "commentEvidence": out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json",
        "commentEvidenceExport": out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json",
        "businessAttribution": out_dir / "reports/promotion-manager/business-attribution/business-attribution.json",
        "businessAttributionExport": out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json",
        "metricsRecovery": out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json",
        "nextRoundOptimization": out_dir / "reports/promotion-manager/optimization/next-round-optimization.json",
        "performanceMonitor": monitor_dir(out_dir) / "performance-monitor.json",
        "history": monitor_dir(out_dir) / "performance-monitor-history.jsonl",
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = monitor_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "performance-monitor.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "performance-monitor.md").write_text(render_markdown(report), encoding="utf-8")


def append_history(out_dir: Path, report: dict[str, Any]) -> None:
    history_path = monitor_dir(out_dir) / "performance-monitor-history.jsonl"
    snapshot = {
        "generatedAtUtc": report["generatedAtUtc"],
        "status": report["status"],
        "summary": report["summary"],
        "artifacts": {
            "performanceMonitor": report["artifacts"]["performanceMonitor"],
            "nextRoundOptimization": report["artifacts"]["nextRoundOptimization"],
        },
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Performance Monitor",
        "",
        f"- Status: `{report['status']}`",
        f"- Captured metric records: {summary['capturedMetricRecords']}",
        f"- Comments: {summary['commentCount']}",
        f"- Demand signals: {summary['demandSignalCount']}",
        f"- Matched business rows: {summary['matchedBusinessRows']}",
        f"- Metrics recovery: `{summary.get('metricsRecoveryStatus', '')}`",
        f"- Next round: `{summary.get('nextRoundStatus', '')}`",
        "",
        "## Steps",
    ]
    for step in report["steps"]:
        lines.append(f"- {step['id']}: `{step.get('status')}` report={step.get('report', '')}")
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    lines.append("")
    return "\n".join(lines)


def next_commands(out_dir: Path) -> list[str]:
    return [
        f"python scripts/performance_monitor.py --out-dir \"{out_dir}\"",
        (
            f"python scripts/next_round_optimizer.py --metrics-recovery-json "
            f"\"{out_dir}/reports/promotion-manager/metrics-recovery/metrics-recovery.json\" "
            f"--comment-evidence-json \"{out_dir}/reports/promotion-manager/comment-evidence/comment-evidence-export.json\" "
            f"--business-attribution-json \"{out_dir}/reports/promotion-manager/business-attribution/business-attribution.json\" "
            f"--out-dir \"{out_dir}\""
        ),
    ]


def guardrails() -> list[str]:
    return [
        "Use only proven published URLs, public/browser-visible pages, official exports, screenshots/OCR text, or business exports.",
        "Do not infer hidden analytics, orders, or revenue from social engagement.",
        "Do not auto-login, solve captcha, bypass risk checks, or save cookies/tokens/passwords.",
        "Manual evidence requests are missing evidence, not recovered data.",
    ]


def add_published_sources(command: list[str], args: argparse.Namespace) -> None:
    add_repeated(command, "--published-items-json", args.published_items_json)
    add_repeated(command, "--published-url", args.published_url)


def add_repeated(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        if value:
            command.extend([flag, value])


def add_optional(command: list[str], flag: str, value: str) -> None:
    if value:
        command.extend([flag, value])


def has_business_sources(args: argparse.Namespace) -> bool:
    return any([args.business_csv, args.business_xlsx, args.business_json, args.business_text])


def source_summary(args: argparse.Namespace, kind: str) -> dict[str, int]:
    if kind == "metrics":
        return {
            "csv": len(args.metrics_csv),
            "xlsx": len(args.metrics_xlsx),
            "json": len(args.metrics_json),
            "text": len(args.metrics_text),
            "structuredJson": len(args.metrics_structured_json),
        }
    return {
        "csv": len(args.business_csv),
        "xlsx": len(args.business_xlsx),
        "json": len(args.business_json),
        "text": len(args.business_text),
    }


def step_status(exit_code: int, report: dict[str, Any]) -> str:
    if exit_code != 0:
        return "error"
    status = report_status(report)
    if status:
        return status
    return "ready" if report else "completed"


def report_status(report: dict[str, Any]) -> str:
    if not report:
        return ""
    return str(report.get("status") or report.get("recoveryStatus") or "")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def display_command(command: list[str]) -> list[str]:
    return [str(part) for part in command]


def tail(text: str, limit: int = 1200) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[-limit:]


def monitor_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


if __name__ == "__main__":
    main()
