#!/usr/bin/env python3
"""Run a safe browser-assisted publish session from a guarded publish queue."""

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
BROWSER_PUBLISH_ASSISTANT = SCRIPTS / "browser_publish_assistant.py"
BROWSER_PUBLISH_FORM_FILL = SCRIPTS / "browser_publish_form_fill.py"
TODAY = date.today().isoformat()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    queue_path = resolve_queue_path(args, out_dir)
    assistant_result = run_assistant(args, out_dir, queue_path)
    assistant_report_path = out_dir / "reports/promotion-manager/browser-publish/browser-publish-assistant.json"
    assistant_report = read_json(assistant_report_path)
    form_fill_runs = run_form_fill_runs(args, out_dir, assistant_report)
    report = build_report(args, out_dir, queue_path, assistant_result, assistant_report_path, assistant_report, form_fill_runs)
    write_report(out_dir, report)
    print(f"Browser publish session written to: {(report_dir(out_dir) / 'browser-publish-session.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and optionally fill browser-assisted publish forms from publish-queue.json.")
    parser.add_argument(
        "--publish-queue",
        default="",
        help="Path to publish-queue.json. Defaults to <out-dir>/reports/promotion-manager/publish-queue/publish-queue.json.",
    )
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument(
        "--platform-publish-url",
        action="append",
        default=[],
        help="Publisher entry override as platform=url. Can repeat.",
    )
    parser.add_argument("--open-browser", action="store_true", help="Open publisher entry URLs in the default browser.")
    parser.add_argument("--run-form-fill", action="store_true", help="Fill visible form fields from generated payloads and stop before final publish.")
    parser.add_argument("--headed", action="store_true", help="Show the browser during form fill.")
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost publisher URLs for local fixtures and tests.")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Allow browser_publish_form_fill.py to install official Playwright Chromium if missing.")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-until", default="domcontentloaded", choices=["load", "domcontentloaded", "networkidle"])
    return parser.parse_args()


def resolve_queue_path(args: argparse.Namespace, out_dir: Path) -> Path:
    if args.publish_queue:
        return Path(args.publish_queue)
    return out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"


def run_assistant(args: argparse.Namespace, out_dir: Path, queue_path: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(BROWSER_PUBLISH_ASSISTANT),
        "--publish-queue",
        str(queue_path),
        "--out-dir",
        str(out_dir),
    ]
    if args.platforms:
        command.extend(["--platforms", args.platforms])
    for value in args.platform_publish_url:
        command.extend(["--platform-publish-url", value])
    if args.open_browser:
        command.append("--open-browser")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "command": display_command(command),
        "exitCode": result.returncode,
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }


def run_form_fill_runs(args: argparse.Namespace, out_dir: Path, assistant_report: dict[str, Any]) -> list[dict[str, Any]]:
    if not args.run_form_fill:
        return []
    runs = []
    for record in list_records(assistant_report, "records"):
        platform = clean_text(record.get("platform"))
        payload_json = clean_text((record.get("payloadFiles") or {}).get("json"))
        if not payload_json:
            runs.append(
                {
                    "platform": platform,
                    "status": "skipped_missing_payload",
                    "command": [],
                    "report": "",
                    "screenshot": "",
                    "submitted": False,
                    "finalPublishUserActionRequired": True,
                }
            )
            continue
        run_out_dir = report_dir(out_dir) / "form-fill-runs" / (platform or "unknown")
        command = [
            sys.executable,
            str(BROWSER_PUBLISH_FORM_FILL),
            "--payload-json",
            payload_json,
            "--out-dir",
            str(run_out_dir),
            "--timeout-ms",
            str(args.timeout_ms),
            "--wait-until",
            args.wait_until,
        ]
        if args.headed:
            command.append("--headed")
        if args.allow_localhost:
            command.append("--allow-localhost")
        if args.install_browser_if_missing:
            command.append("--install-browser-if-missing")
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        report_path = run_out_dir / "reports/promotion-manager/browser-publish/browser-form-fill.json"
        form_report = read_json(report_path)
        artifacts = form_report.get("artifacts") if isinstance(form_report.get("artifacts"), dict) else {}
        runs.append(
            {
                "platform": platform,
                "status": clean_text(form_report.get("status")) or ("error" if result.returncode else "report_missing"),
                "command": display_command(command),
                "exitCode": result.returncode,
                "report": str(report_path) if report_path.exists() else "",
                "screenshot": clean_text(artifacts.get("screenshot")),
                "submitted": bool(form_report.get("submitted")),
                "finalPublishUserActionRequired": bool(form_report.get("finalPublishUserActionRequired", True)),
                "filledFields": form_report.get("filledFields") if isinstance(form_report.get("filledFields"), list) else [],
                "missingFields": form_report.get("missingFields") if isinstance(form_report.get("missingFields"), list) else [],
                "stdoutTail": tail(result.stdout),
                "stderrTail": tail(result.stderr),
            }
        )
    return runs


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    queue_path: Path,
    assistant_result: dict[str, Any],
    assistant_report_path: Path,
    assistant_report: dict[str, Any],
    form_fill_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    records = build_records(out_dir, assistant_report, form_fill_runs)
    status = session_status(assistant_result, assistant_report, records, args.run_form_fill)
    return {
        "generatedAt": TODAY,
        "status": status,
        "input": {
            "publishQueue": str(queue_path),
            "platforms": args.platforms,
            "runFormFill": bool(args.run_form_fill),
            "openBrowser": bool(args.open_browser),
        },
        "assistant": {
            **assistant_result,
            "report": str(assistant_report_path) if assistant_report_path.exists() else "",
            "status": clean_text(assistant_report.get("status")),
            "summary": assistant_report.get("summary") if isinstance(assistant_report.get("summary"), dict) else {},
        },
        "records": records,
        "summary": summarize(records, assistant_result, args.run_form_fill),
        "postPublish": {
            "realEvidenceInboxCommand": f"python scripts/real_evidence_inbox.py --inbox-dir \"./promotion-evidence-inbox\" --out-dir \"{out_dir}\"",
            "publishedUrlCaptureCommand": f"python scripts/publish_url_capture.py --structured-json \"<PUBLISHED_PAGE_SNAPSHOT.json>\" --out-dir \"{out_dir}\"",
            "metricsRecoveryCommand": f"python scripts/metrics_recovery.py --out-dir \"{out_dir}\"",
        },
        "guardrails": [
            "This session prepares browser-assisted publishing only; it does not auto-login or click final publish.",
            "Form fill writes only visible fields from generated payloads and stops before Publish/Submit/Post/Schedule actions.",
            "Stop for login, captcha, risk control, account verification, platform review, or unexpected account state.",
            "Register a post only after a real published URL or user-visible post-publish evidence exists.",
            "No cookies, passwords, API keys, OAuth tokens, browser storage, or hidden platform tokens are read or written.",
        ],
    }


def build_records(out_dir: Path, assistant_report: dict[str, Any], form_fill_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs_by_platform = {clean_text(item.get("platform")): item for item in form_fill_runs}
    records = []
    for record in list_records(assistant_report, "records"):
        platform = clean_text(record.get("platform"))
        payload_files = record.get("payloadFiles") if isinstance(record.get("payloadFiles"), dict) else {}
        post_publish = record.get("postPublish") if isinstance(record.get("postPublish"), dict) else {}
        form_fill = runs_by_platform.get(platform, {})
        records.append(
            {
                "platform": platform,
                "queueStatus": clean_text(record.get("queueStatus")),
                "publishMode": clean_text(record.get("publishMode")),
                "publisherUrl": clean_text(record.get("publisherUrl")),
                "payloadJson": clean_text(payload_files.get("json")),
                "clipboard": clean_text(payload_files.get("clipboard")),
                "checklist": clean_text(payload_files.get("checklist")),
                "formFill": form_fill or {"status": "not_requested", "submitted": False, "finalPublishUserActionRequired": True},
                "finalPublishUserActionRequired": True,
                "registerPublishedUrlCommand": clean_text(post_publish.get("registerUrlCommand"))
                or f"python scripts/published_items.py --platform {platform} --published-url \"<REAL_PUBLISHED_URL>\" --out-dir \"{out_dir}\"",
                "capturePublishedUrlCommand": clean_text(post_publish.get("captureSnapshotCommand"))
                or f"python scripts/publish_url_capture.py --structured-json \"<PUBLISHED_PAGE_SNAPSHOT.json>\" --platform {platform} --out-dir \"{out_dir}\"",
                "nextAction": "Review the prepared post, let the user perform final publish, then register the real URL and import real evidence.",
            }
        )
    return records


def session_status(
    assistant_result: dict[str, Any],
    assistant_report: dict[str, Any],
    records: list[dict[str, Any]],
    run_form_fill: bool,
) -> str:
    if assistant_result["exitCode"] != 0:
        return "error"
    if not records:
        return "no_browser_publish_tasks"
    if not run_form_fill:
        return "ready_payloads_prepared"
    statuses = {clean_text((record.get("formFill") or {}).get("status")) for record in records}
    if statuses <= {"ready"}:
        return "ready_form_fill_completed"
    if "error" in statuses:
        return "partial_ready_form_fill_errors"
    if "blocked" in statuses:
        return "partial_ready_user_action_required"
    return "partial_ready_review_required"


def summarize(records: list[dict[str, Any]], assistant_result: dict[str, Any], run_form_fill: bool) -> dict[str, int]:
    return {
        "platforms": len(records),
        "assistantExitCode": int(assistant_result["exitCode"]),
        "payloadsPrepared": sum(1 for item in records if item.get("payloadJson")),
        "formFillRequested": 1 if run_form_fill else 0,
        "formFillRuns": sum(1 for item in records if clean_text((item.get("formFill") or {}).get("status")) not in {"", "not_requested"}),
        "formFillReady": sum(1 for item in records if clean_text((item.get("formFill") or {}).get("status")) == "ready"),
        "submitted": sum(1 for item in records if bool((item.get("formFill") or {}).get("submitted"))),
        "finalPublishUserActionRequired": sum(1 for item in records if item.get("finalPublishUserActionRequired")),
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "browser-publish-session.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "browser-publish-session.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Browser Publish Session",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Publish queue: {report['input']['publishQueue']}",
        f"- Assistant report: {report['assistant'].get('report', '') or 'missing'}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Platform Sessions"])
    if not report["records"]:
        lines.append("- none")
    for record in report["records"]:
        form_fill = record.get("formFill") if isinstance(record.get("formFill"), dict) else {}
        lines.extend(
            [
                "",
                f"### {record['platform']}",
                f"- Publish mode: `{record['publishMode']}`",
                f"- Queue status: `{record['queueStatus']}`",
                f"- Publisher URL: {record['publisherUrl'] or 'missing'}",
                f"- Payload JSON: {record['payloadJson'] or 'missing'}",
                f"- Clipboard: {record['clipboard'] or 'missing'}",
                f"- Checklist: {record['checklist'] or 'missing'}",
                f"- Form fill status: `{form_fill.get('status', 'not_requested')}`",
                f"- Form fill report: {form_fill.get('report', '') or 'not requested'}",
                f"- Screenshot: {form_fill.get('screenshot', '') or 'not captured'}",
                f"- Submitted: `{form_fill.get('submitted', False)}`",
                f"- Final publish user action required: `{record['finalPublishUserActionRequired']}`",
                f"- Register URL: `{record['registerPublishedUrlCommand']}`",
                f"- Next action: {record['nextAction']}",
            ]
        )
    lines.extend(["", "## Post Publish"])
    for key, value in report["postPublish"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/browser-publish-session"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def list_records(report: dict[str, Any], key: str) -> list[dict[str, Any]]:
    if not isinstance(report, dict) or not isinstance(report.get(key), list):
        return []
    return [item for item in report[key] if isinstance(item, dict)]


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def tail(value: str, limit: int = 1200) -> str:
    value = (value or "").strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
