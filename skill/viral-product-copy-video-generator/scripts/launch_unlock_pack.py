#!/usr/bin/env python3
"""Build one safe unlock pack for external publishing and evidence gates."""

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
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
REPORT_DIR = Path("reports/promotion-manager/launch-unlock")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    platform_access_path = run_platform_access(args, out_dir, steps)
    publish_readiness_path = resolve_publish_readiness(args, out_dir)
    publish_queue_path = resolve_publish_queue(args, out_dir)

    if not publish_readiness_path and (publish_queue_path or args.workflow_manifest):
        publish_readiness_path = run_publish_readiness(args, out_dir, publish_queue_path, steps)
        readiness = read_json(publish_readiness_path)
        publish_queue_path = first_existing(
            [
                publish_queue_path,
                readiness.get("inputs", {}).get("publishQueue") if isinstance(readiness.get("inputs"), dict) else "",
                out_dir / "reports/promotion-manager/publish-queue/publish-queue.json",
            ]
        )

    publish_setup_path = run_publish_setup(args, out_dir, publish_readiness_path, steps)
    real_evidence_setup_path = run_real_evidence_setup(args, out_dir, publish_queue_path, publish_readiness_path, steps)
    browser_publish_path = run_browser_publish(args, out_dir, publish_queue_path, steps)

    report = build_report(
        args=args,
        out_dir=out_dir,
        platform_access_path=platform_access_path,
        publish_readiness_path=publish_readiness_path,
        publish_queue_path=publish_queue_path,
        publish_setup_path=publish_setup_path,
        real_evidence_setup_path=real_evidence_setup_path,
        browser_publish_path=browser_publish_path,
        steps=steps,
    )
    artifacts = write_artifacts(out_dir, report)
    report["artifacts"] = artifacts
    write_report(out_dir, report)
    print(f"Launch unlock pack written to: {(report_dir(out_dir) / 'launch-unlock.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine platform access, publish setup, browser-assisted publishing, and real evidence setup."
    )
    parser.add_argument("--workflow-manifest", default="", help="Workflow manifest used to build publish readiness/queue.")
    parser.add_argument("--publish-queue", default="", help="Existing publish-queue.json.")
    parser.add_argument("--publish-readiness", default="", help="Existing publish-readiness.json.")
    parser.add_argument("--platforms", default="youtube,zhihu,xiaohongshu,douyin,github")
    parser.add_argument("--github-repo", default="")
    parser.add_argument("--youtube-video-file", default="")
    parser.add_argument("--douyin-video-file", default="")
    parser.add_argument("--business-csv", default="")
    parser.add_argument("--business-xlsx", default="")
    parser.add_argument("--business-json", default="")
    parser.add_argument("--business-text", default="")
    parser.add_argument("--platform-publish-url", action="append", default=[], help="Override browser-assisted publisher entry as platform=url.")
    parser.add_argument("--check-live", action="store_true", help="Refresh official platform doc reachability.")
    parser.add_argument("--skip-browser-publish-assistant", action="store_true")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def run_platform_access(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> Path:
    command = [
        sys.executable,
        str(SCRIPTS / "platform_access_audit.py"),
        "--platforms",
        args.platforms,
        "--out-dir",
        str(out_dir),
    ]
    if args.check_live:
        command.append("--check-live")
    run_step("platform_access_audit", command, steps)
    return out_dir / "reports/promotion-manager/platform-access/platform-access-audit.json"


def run_publish_readiness(
    args: argparse.Namespace,
    out_dir: Path,
    publish_queue_path: Path | None,
    steps: list[dict[str, Any]],
) -> Path | None:
    command = [
        sys.executable,
        str(SCRIPTS / "publish_readiness_runner.py"),
        "--platforms",
        args.platforms,
        "--out-dir",
        str(out_dir),
    ]
    if publish_queue_path:
        command.extend(["--publish-queue", str(publish_queue_path)])
    elif args.workflow_manifest:
        command.extend(["--workflow-manifest", args.workflow_manifest, "--build-queue"])
    else:
        return None
    append_arg(command, "--github-repo", args.github_repo)
    append_arg(command, "--youtube-video-file", args.youtube_video_file)
    append_arg(command, "--douyin-video-file", args.douyin_video_file)
    run_step("publish_readiness", command, steps)
    return out_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json"


def run_publish_setup(
    args: argparse.Namespace,
    out_dir: Path,
    publish_readiness_path: Path | None,
    steps: list[dict[str, Any]],
) -> Path | None:
    if not publish_readiness_path:
        return None
    command = [
        sys.executable,
        str(SCRIPTS / "publish_setup_assistant.py"),
        "--publish-readiness",
        str(publish_readiness_path),
        "--platforms",
        args.platforms,
        "--out-dir",
        str(out_dir),
    ]
    run_step("publish_setup_assistant", command, steps)
    return out_dir / "reports/promotion-manager/publish-setup/publish-setup.json"


def run_real_evidence_setup(
    args: argparse.Namespace,
    out_dir: Path,
    publish_queue_path: Path | None,
    publish_readiness_path: Path | None,
    steps: list[dict[str, Any]],
) -> Path | None:
    if not publish_queue_path:
        return None
    command = [
        sys.executable,
        str(SCRIPTS / "real_evidence_setup.py"),
        "--publish-queue",
        str(publish_queue_path),
        "--platforms",
        args.platforms,
        "--out-dir",
        str(out_dir),
    ]
    if publish_readiness_path:
        command.extend(["--publish-readiness", str(publish_readiness_path)])
    run_step("real_evidence_setup", command, steps)
    return out_dir / "reports/promotion-manager/real-evidence-setup/real-evidence-setup.json"


def run_browser_publish(
    args: argparse.Namespace,
    out_dir: Path,
    publish_queue_path: Path | None,
    steps: list[dict[str, Any]],
) -> Path | None:
    if args.skip_browser_publish_assistant or not publish_queue_path:
        return None
    command = [
        sys.executable,
        str(SCRIPTS / "browser_publish_assistant.py"),
        "--publish-queue",
        str(publish_queue_path),
        "--platforms",
        args.platforms,
        "--out-dir",
        str(out_dir),
    ]
    append_many(command, "--platform-publish-url", args.platform_publish_url)
    run_step("browser_publish_assistant", command, steps)
    return out_dir / "reports/promotion-manager/browser-publish/browser-publish-assistant.json"


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    platform_access_path: Path,
    publish_readiness_path: Path | None,
    publish_queue_path: Path | None,
    publish_setup_path: Path | None,
    real_evidence_setup_path: Path | None,
    browser_publish_path: Path | None,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    platform_access = read_json(platform_access_path)
    readiness = read_json(publish_readiness_path)
    publish_setup = read_json(publish_setup_path)
    evidence_setup = read_json(real_evidence_setup_path)
    browser_publish = read_json(browser_publish_path)
    gates = gate_records(platform_access, readiness, publish_setup, evidence_setup, browser_publish)
    return {
        "generatedAt": TODAY,
        "status": "ready_unlock_pack" if publish_readiness_path or publish_queue_path else "waiting_workflow_or_publish_queue",
        "inputs": {
            "workflowManifest": args.workflow_manifest,
            "publishQueue": str(publish_queue_path or ""),
            "publishReadiness": str(publish_readiness_path or ""),
            "platforms": args.platforms,
            "checkLive": bool(args.check_live),
            "githubRepoProvided": bool(args.github_repo),
            "youtubeVideoFileProvided": bool(args.youtube_video_file),
            "douyinVideoFileProvided": bool(args.douyin_video_file),
            "businessEvidenceProvided": bool(args.business_csv or args.business_xlsx or args.business_json or args.business_text),
        },
        "sourceReports": {
            "platformAccess": report_ref(platform_access_path),
            "publishReadiness": report_ref(publish_readiness_path),
            "publishSetup": report_ref(publish_setup_path),
            "realEvidenceSetup": report_ref(real_evidence_setup_path),
            "browserPublishAssistant": report_ref(browser_publish_path),
        },
        "summary": summarize_gates(gates, steps),
        "gates": gates,
        "nextCommands": next_commands(out_dir, publish_queue_path, publish_readiness_path, args),
        "steps": steps,
        "guardrails": [
            "This pack unlocks reviewable setup steps; it does not bypass platform authorization, login, captcha, account verification, or final publish.",
            "No credential values are read from environment variables, printed, or written; only variable names and presence status may appear in child reports.",
            "Browser-assisted platforms still require user-visible review and a real final publish action by the account owner.",
            "Published URLs, views, likes, comments, orders, and revenue must come from official APIs, public/browser-visible evidence, screenshots/OCR, or business exports.",
            "Use this pack before claiming a real launch is ready; use final_capability_readiness.py after evidence is imported.",
        ],
    }


def gate_records(
    platform_access: dict[str, Any],
    readiness: dict[str, Any],
    publish_setup: dict[str, Any],
    evidence_setup: dict[str, Any],
    browser_publish: dict[str, Any],
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    gates.append(
        {
            "id": "platform_access_boundaries",
            "status": platform_access.get("status", "missing"),
            "ready": bool(platform_access),
            "nextAction": "Use official executors only where platform access is mapped; keep unverified platforms browser-assisted.",
        }
    )
    gates.append(
        {
            "id": "publish_authorization",
            "status": readiness.get("status", "waiting_publish_readiness"),
            "ready": bool(readiness) and readiness.get("status") in {"ready", "partial_ready"},
            "nextAction": "Set required environment variables outside the repository and rerun publish readiness before any official write.",
        }
    )
    gates.append(
        {
            "id": "publish_setup_kit",
            "status": publish_setup.get("status", "waiting_publish_readiness"),
            "ready": bool(publish_setup) and publish_setup.get("status") == "ready",
            "nextAction": "Use generated env template, platform setup guide, and checklist; do not fill real secrets into repo files.",
        }
    )
    gates.append(
        {
            "id": "browser_assisted_publish",
            "status": browser_publish.get("status", "waiting_publish_queue"),
            "ready": bool(browser_publish) and browser_publish.get("status") in {"ready", "no_browser_publish_tasks"},
            "nextAction": "Use browser payloads for Zhihu, Xiaohongshu, Douyin, TikTok, or other manual/browser-assisted platforms.",
        }
    )
    gates.append(
        {
            "id": "real_evidence_collection",
            "status": evidence_setup.get("status", "waiting_publish_queue_or_published_items"),
            "ready": bool(evidence_setup) and evidence_setup.get("status") == "ready",
            "nextAction": "Register final published URLs, fill metric/comment/business templates, then run the performance monitor.",
        }
    )
    return gates


def summarize_gates(gates: list[dict[str, Any]], steps: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "gates": len(gates),
        "readyGates": sum(1 for gate in gates if gate.get("ready")),
        "waitingGates": sum(1 for gate in gates if not gate.get("ready")),
        "steps": len(steps),
        "failedSteps": sum(1 for step in steps if step.get("exitCode") not in {0, None}),
    }


def next_commands(
    out_dir: Path,
    publish_queue_path: Path | None,
    publish_readiness_path: Path | None,
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    queue = str(publish_queue_path or out_dir / "reports/promotion-manager/publish-queue/publish-queue.json")
    readiness = str(publish_readiness_path or out_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json")
    commands = [
        {
            "purpose": "refresh_platform_access",
            "command": f"python scripts/platform_access_audit.py --check-live --platforms {quote(args.platforms)} --out-dir {quote(str(out_dir))}",
        },
        {
            "purpose": "rerun_publish_readiness",
            "command": f"python scripts/publish_readiness_runner.py --publish-queue {quote(queue)} --platforms {quote(args.platforms)} --out-dir {quote(str(out_dir))}",
        },
        {
            "purpose": "build_publish_setup",
            "command": f"python scripts/publish_setup_assistant.py --publish-readiness {quote(readiness)} --platforms {quote(args.platforms)} --out-dir {quote(str(out_dir))}",
        },
        {
            "purpose": "browser_publish_session",
            "command": f"python scripts/browser_publish_session.py --publish-queue {quote(queue)} --out-dir {quote(str(out_dir))}",
        },
        {
            "purpose": "real_evidence_setup",
            "command": f"python scripts/real_evidence_setup.py --publish-queue {quote(queue)} --publish-readiness {quote(readiness)} --out-dir {quote(str(out_dir))}",
        },
        {
            "purpose": "performance_monitor",
            "command": f"python scripts/performance_monitor.py --out-dir {quote(str(out_dir))}",
        },
        {
            "purpose": "final_readiness",
            "command": f"python scripts/final_capability_readiness.py --out-dir {quote(str(out_dir))}",
        },
    ]
    return commands


def write_artifacts(out_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    directory = report_dir(out_dir)
    commands_dir = directory / "commands"
    directory.mkdir(parents=True, exist_ok=True)
    commands_dir.mkdir(parents=True, exist_ok=True)
    checklist = directory / "launch-unlock-checklist.md"
    command_file = commands_dir / "launch-unlock-next-actions.ps1"
    checklist.write_text(render_checklist(report) + "\n", encoding="utf-8")
    command_file.write_text(render_commands(report) + "\n", encoding="utf-8")
    return {
        "checklist": str(checklist),
        "nextActionCommands": str(command_file),
    }


def render_checklist(report: dict[str, Any]) -> str:
    lines = [
        "# Launch Unlock Checklist",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        "",
        "## Gates",
    ]
    for gate in report["gates"]:
        mark = "x" if gate.get("ready") else " "
        lines.append(f"- [{mark}] `{gate['id']}` status `{gate['status']}`")
        lines.append(f"  - Next: {gate['nextAction']}")
    lines.extend(["", "## Next Commands"])
    for command in report["nextCommands"]:
        lines.append(f"- `{command['command']}`")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_commands(report: dict[str, Any]) -> str:
    lines = [
        "# Generated by scripts/launch_unlock_pack.py",
        "# Review each command before execution. Do not paste real secrets into this file.",
        "",
    ]
    for item in report["nextCommands"]:
        lines.append(f"# {item['purpose']}")
        lines.append(item["command"])
        lines.append("")
    return "\n".join(lines).rstrip()


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "launch-unlock.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "launch-unlock.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Launch Unlock Pack",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Ready gates: {report['summary']['readyGates']}/{report['summary']['gates']}",
        "",
        "## Source Reports",
    ]
    for name, ref in report["sourceReports"].items():
        lines.append(f"- {name}: {ref.get('path') or 'missing'}")
    lines.extend(["", "## Gates"])
    for gate in report["gates"]:
        lines.extend(
            [
                "",
                f"### {gate['id']}",
                f"- Status: `{gate['status']}`",
                f"- Ready: {gate['ready']}",
                f"- Next action: {gate['nextAction']}",
            ]
        )
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- {item['purpose']}: `{item['command']}`" for item in report["nextCommands"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def run_step(name: str, command: list[str], steps: list[dict[str, Any]]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    steps.append(
        {
            "name": name,
            "command": display_command(command),
            "exitCode": result.returncode,
            "stdoutTail": tail(result.stdout),
            "stderrTail": tail(result.stderr),
        }
    )
    if result.returncode != 0:
        raise SystemExit(f"{name} failed with exit code {result.returncode}: {tail(result.stderr) or tail(result.stdout)}")


def resolve_publish_readiness(args: argparse.Namespace, out_dir: Path) -> Path | None:
    return first_existing([args.publish_readiness, out_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json"])


def resolve_publish_queue(args: argparse.Namespace, out_dir: Path) -> Path | None:
    return first_existing([args.publish_queue, out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"])


def first_existing(values: list[Any]) -> Path | None:
    for value in values:
        if not value:
            continue
        path = Path(value)
        if path.exists():
            return path
    return None


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def report_ref(path: Path | None) -> dict[str, Any]:
    return {"path": str(path or ""), "exists": bool(path and path.exists())}


def append_arg(command: list[str], flag: str, value: str) -> None:
    if value:
        command.extend([flag, value])


def append_many(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        append_arg(command, flag, value)


def tail(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    return text[-limit:] if len(text) > limit else text


def display_command(command: list[str]) -> str:
    return " ".join(quote(item) for item in command)


def quote(value: str) -> str:
    text = str(value)
    if not text or any(ch.isspace() for ch in text) or any(ch in text for ch in ['"', "'"]):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def report_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


if __name__ == "__main__":
    main()
