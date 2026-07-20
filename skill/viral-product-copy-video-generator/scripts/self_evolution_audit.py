#!/usr/bin/env python3
"""Audit and run controlled self-evolution actions for the promotion Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "viral-product-copy-video-generator"
TODAY = date.today().isoformat()
SAFE_INSTALLS = {"playwright_chromium"}
SKILL_SYNC_APPROVAL = "I_APPROVE_SKILL_SYNC"
FRESH_PLATFORM_LEARNING_STATUSES = {"fresh_live_checked", "fresh_live_checked_with_warnings"}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    install_results = install_safe_missing_tools(args) if args.install_safe_missing_tools else []
    sync_result = sync_installed_skill(args) if args.sync_installed_skill else None
    report = build_report(args, out_dir, install_results, sync_result)
    write_report(out_dir, report)
    print(f"Self-evolution audit written to: {(report_dir(out_dir) / 'self-evolution-audit.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit controlled self-evolution readiness for the product promotion Skill.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument(
        "--skip-runtime-checks",
        action="store_true",
        help="Skip slower launch checks such as Playwright Chromium startup.",
    )
    parser.add_argument(
        "--install-safe-missing-tools",
        action="store_true",
        help="Install only explicit allowlisted runtime tools. This never installs arbitrary packages.",
    )
    parser.add_argument(
        "--safe-install",
        action="append",
        default=[],
        choices=sorted(SAFE_INSTALLS),
        help="Allowlisted runtime install to attempt when --install-safe-missing-tools is supplied.",
    )
    parser.add_argument(
        "--sync-installed-skill",
        action="store_true",
        help="Copy reviewed local Skill files into the installed Codex Skill directory.",
    )
    parser.add_argument(
        "--approval",
        default="",
        help=f"Required approval phrase for --sync-installed-skill: {SKILL_SYNC_APPROVAL}",
    )
    return parser.parse_args()


def install_safe_missing_tools(args: argparse.Namespace) -> list[dict[str, Any]]:
    installs = set(args.safe_install or []) or {"playwright_chromium"}
    unsupported = installs - SAFE_INSTALLS
    if unsupported:
        raise SystemExit(f"Unsupported safe installs: {', '.join(sorted(unsupported))}")
    results: list[dict[str, Any]] = []
    if "playwright_chromium" in installs:
        before = playwright_chromium_available(skip_runtime_checks=False)
        command = [sys.executable, "-m", "playwright", "install", "chromium"]
        if before:
            results.append(
                {
                    "id": "playwright_chromium",
                    "status": "already_available",
                    "command": sanitize_command(command),
                    "exitCode": None,
                }
            )
        elif not python_module_status("playwright")["available"]:
            results.append(
                {
                    "id": "playwright_chromium",
                    "status": "blocked_missing_playwright_module",
                    "command": sanitize_command(command),
                    "exitCode": None,
                    "nextAction": "Install the Python Playwright package through a reviewed dependency change before browser runtime install.",
                }
            )
        else:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            results.append(
                {
                    "id": "playwright_chromium",
                    "status": "installed" if result.returncode == 0 else "error",
                    "command": sanitize_command(command),
                    "exitCode": result.returncode,
                    "stdoutTail": tail(result.stdout),
                    "stderrTail": tail(result.stderr),
                }
            )
    return results


def sync_installed_skill(args: argparse.Namespace) -> dict[str, Any]:
    installed = installed_skill_dir()
    files = managed_skill_files(ROOT)
    result: dict[str, Any] = {
        "requested": True,
        "approvalRequired": SKILL_SYNC_APPROVAL,
        "approvalProvided": args.approval == SKILL_SYNC_APPROVAL,
        "installedSkillDir": str(installed),
        "copiedFiles": [],
        "status": "blocked_missing_approval",
    }
    if args.approval != SKILL_SYNC_APPROVAL:
        return result
    installed.mkdir(parents=True, exist_ok=True)
    for rel in files:
        source = ROOT / rel
        target = installed / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        result["copiedFiles"].append(str(rel).replace("\\", "/"))
    result["status"] = "synced"
    return result


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    install_results: list[dict[str, Any]],
    sync_result: dict[str, Any] | None,
) -> dict[str, Any]:
    tools = tool_status(skip_runtime_checks=args.skip_runtime_checks)
    installed = installed_skill_status()
    runtime_gaps = runtime_gap_list(tools)
    platform_learning = platform_learning_status(out_dir)
    review_queue = review_required_upgrade_requests(installed, runtime_gaps, platform_learning, tools, out_dir)
    report = {
        "generatedAt": TODAY,
        "status": audit_status(installed, runtime_gaps, args.skip_runtime_checks),
        "root": str(ROOT),
        "outDir": str(out_dir),
        "installedSkill": installed,
        "repository": repository_status(),
        "localTools": tools,
        "runtimeGaps": runtime_gaps,
        "safeInstallCandidates": safe_install_candidates(tools, out_dir),
        "installResults": install_results,
        "platformLearning": platform_learning,
        "reviewRequiredUpgradeRequests": review_queue,
        "reviewQueueSummary": review_queue_summary(review_queue),
        "syncInstalledSkill": sync_result
        or {
            "requested": False,
            "approvalRequired": SKILL_SYNC_APPROVAL,
            "approvalProvided": False,
            "status": "not_requested",
            "installedSkillDir": str(installed_skill_dir()),
        },
        "learningAndUpgradeLoop": learning_and_upgrade_loop(out_dir),
        "selfUpgradePolicy": {
            "mode": "controlled_autonomy",
            "canActWithoutFurtherInput": [
                "audit local tools and installed Skill drift",
                "write self-evolution reports and next-action plans",
                "run tests, compile checks, and secret scans when invoked by Codex",
                "install allowlisted browser runtime only when explicit install flags are supplied",
            ],
            "requiresExplicitApproval": [
                "copy reviewed local Skill files into the installed Codex Skill directory",
                "execute real platform publishing",
                "add or upgrade Python packages, binaries, or platform executors",
                "use OAuth, API tokens, cookies, or account sessions",
            ],
            "notAllowed": [
                "silent dependency upgrades",
                "self-replacement from unreviewed network code",
                "credential, cookie, password, or hidden-token extraction",
                "captcha, login, risk-control, or account-verification bypass",
            ],
        },
        "nextActions": next_actions(installed, runtime_gaps, platform_learning, out_dir),
        "guardrails": [
            "Record only credential environment variable names, never values.",
            "Do not install arbitrary network code or upgrade dependencies without a reviewed source and explicit command.",
            "Do not delete installed Skill files during sync; only overwrite managed reviewed files.",
            "Do not claim full autonomous self-evolution while safety approval gates remain required.",
        ],
    }
    return report


def tool_status(skip_runtime_checks: bool) -> dict[str, dict[str, Any]]:
    return {
        "python": {
            "available": True,
            "version": sys.version.split()[0],
            "path": sys.executable,
        },
        "git": command_status("git"),
        "ffmpeg": command_status("ffmpeg"),
        "winget": command_status("winget"),
        "playwright": python_module_status("playwright"),
        "playwrightChromium": {
            "available": playwright_chromium_available(skip_runtime_checks),
            "checked": not skip_runtime_checks,
            "installCommand": "python -m playwright install chromium",
        },
    }


def command_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": bool(path), "path": path or ""}


def python_module_status(name: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return {"available": result.returncode == 0, "module": name}


def playwright_chromium_available(skip_runtime_checks: bool) -> bool:
    if skip_runtime_checks or not python_module_status("playwright")["available"]:
        return False
    code = (
        "from playwright.sync_api import sync_playwright\n"
        "p=sync_playwright().start()\n"
        "b=p.chromium.launch(headless=True)\n"
        "b.close()\n"
        "p.stop()\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def installed_skill_status() -> dict[str, Any]:
    installed = installed_skill_dir()
    files = managed_skill_files(ROOT)
    missing: list[str] = []
    mismatched: list[str] = []
    compared = 0
    for rel in files:
        source = ROOT / rel
        target = installed / rel
        if not target.exists():
            missing.append(str(rel).replace("\\", "/"))
            continue
        compared += 1
        if file_hash(source) != file_hash(target):
            mismatched.append(str(rel).replace("\\", "/"))
    if not installed.exists():
        status = "missing"
    elif missing or mismatched:
        status = "drift_detected"
    else:
        status = "synced"
    return {
        "status": status,
        "path": str(installed),
        "exists": installed.exists(),
        "managedFiles": len(files),
        "comparedFiles": compared,
        "missingFiles": missing,
        "mismatchedFiles": mismatched,
        "syncCommand": (
            "python scripts/self_evolution_audit.py --sync-installed-skill "
            f"--approval {SKILL_SYNC_APPROVAL} --out-dir \"./promotion-output\""
        ),
    }


def installed_skill_dir() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    return codex_home / "skills" / SKILL_NAME


def managed_skill_files(root: Path) -> list[Path]:
    files = [Path("SKILL.md")]
    for standalone in ["README.md", "README.en.md", "README.zh-CN.md", "LICENSE", ".gitignore", "requirements-youtube.txt"]:
        if (root / standalone).exists():
            files.append(Path(standalone))
    directory_patterns = {
        "references": ["*.md"],
        "scripts": ["*.py"],
        "docs": ["*.md"],
        "deploy": ["*.md", "*.conf", "*.service", "*.example"],
        "browser-extension": ["*.json", "*.html", "*.css", "*.js", "*.md", "*.txt", "*.png"],
        "backend/license-service": ["*.json", "*.js", "*.md", "*.sql", "*.example", ".gitignore"],
    }
    for folder, patterns in directory_patterns.items():
        directory = root / folder
        if not directory.exists():
            continue
        for pattern in patterns:
            for item in sorted(directory.rglob(pattern)):
                relative = item.relative_to(directory)
                if generated_or_dependency_path(relative):
                    continue
                files.append(Path(folder) / relative)
    fixture_dir = root / "scripts" / "fixtures" / "mediacrawler"
    if fixture_dir.exists():
        for item in sorted(fixture_dir.glob("*.jsonl")):
            files.append(Path("scripts/fixtures/mediacrawler") / item.name)
    return sorted(dict.fromkeys(files), key=lambda item: item.as_posix())


def generated_or_dependency_path(relative: Path) -> bool:
    ignored_parts = {"node_modules", "var", "__pycache__", ".pytest_cache"}
    return any(part in ignored_parts for part in relative.parts)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_status() -> dict[str, Any]:
    git_available = bool(shutil.which("git"))
    if not git_available:
        return {"gitAvailable": False, "status": "git_missing"}
    status_short = run_git(["status", "--short"])
    status_branch = run_git(["status", "--short", "--branch"])
    return {
        "gitAvailable": True,
        "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"])["stdout"].strip(),
        "head": run_git(["rev-parse", "--short", "HEAD"])["stdout"].strip(),
        "remote": run_git(["remote", "get-url", "origin"])["stdout"].strip(),
        "statusShort": status_short["stdout"].splitlines(),
        "statusBranch": status_branch["stdout"].splitlines(),
        "clean": status_short["exitCode"] == 0 and not status_short["stdout"].strip(),
    }


def run_git(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "exitCode": result.returncode,
        "stdout": result.stdout,
        "stderrTail": tail(result.stderr),
    }


def runtime_gap_list(tools: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if not tools["git"]["available"]:
        gaps.append({"tool": "git", "impact": "cannot inspect repository state or push reviewed upgrades"})
    if not tools["ffmpeg"]["available"]:
        gaps.append({"tool": "ffmpeg", "impact": "cannot render real MP4 promotion videos"})
    if not tools["playwright"]["available"]:
        gaps.append({"tool": "playwright", "impact": "cannot capture rendered product pages or browser-visible platform search"})
    if tools["playwright"]["available"] and tools["playwrightChromium"]["checked"] and not tools["playwrightChromium"]["available"]:
        gaps.append({"tool": "playwright_chromium", "impact": "browser runtime missing for rendered page capture"})
    return gaps


def safe_install_candidates(tools: dict[str, dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    chromium_status = "available" if tools["playwrightChromium"]["available"] else "missing_or_unchecked"
    return [
        {
            "id": "playwright_chromium",
            "status": chromium_status,
            "autoInstallSupported": True,
            "command": (
                "python scripts/self_evolution_audit.py --install-safe-missing-tools "
                f"--safe-install playwright_chromium --out-dir \"{out_dir}\""
            ),
            "source": "official Playwright browser runtime installer",
        },
        {
            "id": "ffmpeg",
            "status": "available" if tools["ffmpeg"]["available"] else "missing",
            "autoInstallSupported": False,
            "command": "winget install Gyan.FFmpeg",
            "source": "review before installing system binary",
        },
        {
            "id": "python_playwright_package",
            "status": "available" if tools["playwright"]["available"] else "missing",
            "autoInstallSupported": False,
            "command": "python -m pip install playwright",
            "source": "review dependency change before installing Python package",
        },
    ]


def review_required_upgrade_requests(
    installed: dict[str, Any],
    runtime_gaps: list[dict[str, str]],
    platform_learning: dict[str, Any],
    tools: dict[str, dict[str, Any]],
    out_dir: Path,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for gap in runtime_gaps:
        tool = gap.get("tool", "")
        if tool == "playwright_chromium":
            requests.append(
                upgrade_request(
                    "install_playwright_chromium",
                    "runtime_tool",
                    "install_allowlisted_runtime",
                    "explicit_command",
                    (
                        "python scripts/self_evolution_audit.py --install-safe-missing-tools "
                        f"--safe-install playwright_chromium --out-dir \"{out_dir}\""
                    ),
                    gap.get("impact", ""),
                    "Official Playwright browser runtime installer; no arbitrary package install.",
                    agent_can_execute=False,
                )
            )
        elif tool == "playwright":
            requests.append(
                upgrade_request(
                    "review_python_playwright_package",
                    "python_dependency",
                    "manual_dependency_review",
                    "manual_review",
                    "python -m pip install playwright",
                    gap.get("impact", ""),
                    "Requires reviewed dependency change before installing a Python package.",
                    agent_can_execute=False,
                )
            )
        elif tool == "ffmpeg":
            requests.append(
                upgrade_request(
                    "review_ffmpeg_install",
                    "system_binary",
                    "manual_binary_review",
                    "manual_review",
                    "winget install Gyan.FFmpeg",
                    gap.get("impact", ""),
                    "Requires reviewed system binary installation outside the Skill repository.",
                    agent_can_execute=False,
                )
            )
    if installed.get("status") != "synced":
        requests.append(
            upgrade_request(
                "sync_installed_skill",
                "installed_skill",
                "sync_reviewed_skill_files",
                SKILL_SYNC_APPROVAL,
                installed.get("syncCommand", ""),
                "Installed Codex Skill does not match reviewed repository files.",
                "Copies managed local files only; does not delete unmanaged installed files.",
                agent_can_execute=False,
            )
        )
    if platform_learning.get("status") not in FRESH_PLATFORM_LEARNING_STATUSES:
        requests.append(
            upgrade_request(
                "refresh_platform_access_learning",
                "platform_learning",
                "refresh_official_docs",
                "",
                platform_learning.get("refreshCommand") or f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
                "Publishing and metrics executors should be changed only after fresh official/public source checks.",
                "Read-only official documentation reachability check; records gaps and keeps unsafe platforms on manual/browser fallback.",
                agent_can_execute=True,
            )
        )
    if not tools.get("git", {}).get("available"):
        requests.append(
            upgrade_request(
                "review_git_install",
                "system_binary",
                "manual_binary_review",
                "manual_review",
                "install Git from the official installer or winget after review",
                "Repository state and reviewed GitHub sync cannot be verified without Git.",
                "System binary install must be reviewed by the operator.",
                agent_can_execute=False,
            )
        )
    return requests


def upgrade_request(
    request_id: str,
    area: str,
    action: str,
    approval_required: str,
    command: str,
    reason: str,
    safety_note: str,
    agent_can_execute: bool,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "area": area,
        "action": action,
        "approvalRequired": approval_required,
        "agentCanExecuteWithoutFurtherApproval": agent_can_execute and not approval_required,
        "command": command,
        "reason": reason,
        "safetyNote": safety_note,
    }


def review_queue_summary(queue: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(queue),
        "agentExecutableNow": sum(1 for item in queue if item.get("agentCanExecuteWithoutFurtherApproval")),
        "requiresApprovalOrManualReview": sum(1 for item in queue if not item.get("agentCanExecuteWithoutFurtherApproval")),
    }


def learning_and_upgrade_loop(out_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "step": "capability_audit",
            "command": f"python scripts/final_capability_audit.py --out-dir \"{out_dir}\"",
            "purpose": "prove current readiness against the full requested Agent scope",
        },
        {
            "step": "platform_access_refresh",
            "command": f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
            "purpose": "refresh official publishing and metrics access boundaries from platform docs",
        },
        {
            "step": "self_evolution_audit",
            "command": f"python scripts/self_evolution_audit.py --out-dir \"{out_dir}\"",
            "purpose": "detect runtime gaps, Skill drift, and reviewed upgrade actions",
        },
        {
            "step": "one_link_skill_entry",
            "command": f"python scripts/skill_entry.py --link \"https://example.com/product\" --out-dir \"{out_dir}\"",
            "purpose": "run the Codex-facing one-link Skill entry through playbook, final runner, and readiness matrix",
        },
        {
            "step": "real_run_playbook",
            "command": f"python scripts/real_run_playbook.py --url \"https://example.com/product\" --out-dir \"{out_dir}\"",
            "purpose": "generate the live-run command pack and evidence checklist before a real product cycle",
        },
        {
            "step": "final_readiness_matrix",
            "command": f"python scripts/final_capability_readiness.py --out-dir \"{out_dir}\"",
            "purpose": "merge run, audit, publish, and self-evolution reports into the end-state acceptance matrix",
        },
        {
            "step": "verification",
            "command": "python scripts/test_promotion_manager.py && python -m compileall -q scripts",
            "purpose": "verify behavior before syncing the installed Skill or pushing changes",
        },
        {
            "step": "sensitive_scan",
            "command": "scan SKILL.md, references/*.md, and scripts/*.py for secret-like values before commit or sync",
            "purpose": "avoid leaking tokens, cookies, passwords, or private keys",
        },
    ]


def platform_learning_status(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "reports/promotion-manager/platform-access/platform-access-audit.json"
    if not path.exists():
        return {
            "status": "missing_platform_access_audit",
            "report": "",
            "checkLive": False,
            "refreshCommand": f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
        }
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "invalid_platform_access_audit",
            "report": str(path),
            "checkLive": False,
            "refreshCommand": f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
        }
    freshness = report.get("learningFreshness") if isinstance(report.get("learningFreshness"), dict) else {}
    doc_summary = report.get("officialDocSummary") if isinstance(report.get("officialDocSummary"), dict) else {}
    return {
        "status": freshness.get("status") or ("fresh_live_checked" if report.get("checkLive") else "stale_not_live_checked"),
        "report": str(path),
        "checkLive": bool(report.get("checkLive")),
        "checkedAt": freshness.get("checkedAt") or doc_summary.get("checkedAt", []),
        "totalDocs": int_value(freshness.get("totalDocs") or doc_summary.get("totalDocs")),
        "reachableDocs": int_value(freshness.get("reachableDocs") or doc_summary.get("reachableDocs")),
        "missingDocCapabilities": int_value(freshness.get("missingDocCapabilities") or doc_summary.get("missingDocCapabilities")),
        "failedDocs": (
            int_value(freshness.get("failedDocs"))
            if "failedDocs" in freshness
            else int_value(doc_summary.get("unreachableDocs")) + int_value(doc_summary.get("httpErrorDocs"))
        ),
        "criticalFailedDocs": int_value(freshness.get("criticalFailedDocs") or doc_summary.get("criticalFailedDocs")),
        "fallbackFailedDocs": int_value(freshness.get("fallbackFailedDocs") or doc_summary.get("fallbackFailedDocs")),
        "warning": str(freshness.get("warning") or ""),
        "refreshCommand": freshness.get("refreshCommand") or f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
    }


def next_actions(
    installed: dict[str, Any],
    runtime_gaps: list[dict[str, str]],
    platform_learning: dict[str, Any],
    out_dir: Path,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if runtime_gaps:
        actions.append(
            {
                "priority": 1,
                "area": "runtime_tools",
                "action": "Resolve missing runtime tools before claiming final autonomous operation.",
                "gaps": runtime_gaps,
            }
        )
    if installed["status"] != "synced":
        actions.append(
            {
                "priority": 2,
                "area": "installed_skill",
                "action": "Sync reviewed local Skill files into the Codex installed Skill directory.",
                "command": installed["syncCommand"],
            }
        )
    if platform_learning.get("status") not in FRESH_PLATFORM_LEARNING_STATUSES:
        action = "Refresh official platform access docs before adding or changing direct publishing executors."
        if platform_learning.get("status") == "partial_missing_official_doc_sources":
            action = "Add verified official doc sources for missing platform capabilities, or keep those capabilities manual/browser-assisted."
        actions.append(
            {
                "priority": 3,
                "area": "learning_loop",
                "action": action,
                "command": platform_learning.get("refreshCommand") or f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
            }
        )
    return actions


def audit_status(installed: dict[str, Any], runtime_gaps: list[dict[str, str]], skip_runtime_checks: bool) -> str:
    if installed["status"] == "missing":
        return "partial_ready_installed_skill_missing"
    if installed["status"] == "drift_detected":
        return "partial_ready_skill_drift_detected"
    if runtime_gaps and not skip_runtime_checks:
        return "partial_ready_runtime_gaps"
    return "ready_controlled_autonomy"


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "self-evolution-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / "self-evolution-audit.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Self-Evolution Audit",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Installed Skill: `{report['installedSkill']['status']}`",
        f"- Repository clean: {report['repository'].get('clean')}",
        "",
        "## Runtime Gaps",
    ]
    if report["runtimeGaps"]:
        for gap in report["runtimeGaps"]:
            lines.append(f"- `{gap['tool']}`: {gap['impact']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Safe Install Candidates"])
    for item in report["safeInstallCandidates"]:
        lines.append(f"- `{item['id']}`: `{item['status']}`; auto={item['autoInstallSupported']}")
        lines.append(f"  Command: `{item['command']}`")
    lines.extend(["", "## Skill Sync"])
    sync = report["syncInstalledSkill"]
    lines.append(f"- Requested: {sync['requested']}")
    lines.append(f"- Status: `{sync['status']}`")
    lines.append(f"- Approval required: `{sync['approvalRequired']}`")
    learning = report.get("platformLearning", {})
    lines.extend(["", "## Platform Learning"])
    lines.append(f"- Status: `{learning.get('status', '')}`")
    lines.append(f"- Live checked: {learning.get('checkLive', False)}")
    if learning.get("report"):
        lines.append(f"- Report: {learning['report']}")
    lines.append(f"- Refresh command: `{learning.get('refreshCommand', '')}`")
    lines.extend(["", "## Review Required Upgrade Requests"])
    queue = report.get("reviewRequiredUpgradeRequests", [])
    if queue:
        for item in queue:
            approval = item.get("approvalRequired") or "none"
            lines.append(f"- `{item['id']}` area=`{item['area']}` approval=`{approval}`")
            lines.append(f"  Command: `{item.get('command', '')}`")
            lines.append(f"  Reason: {item.get('reason', '')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions"])
    for action in report["nextActions"]:
        lines.append(f"- P{action['priority']} {action['area']}: {action['action']}")
        if action.get("command"):
            lines.append(f"  Command: `{action['command']}`")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/self-evolution"


def sanitize_command(command: list[str]) -> list[str]:
    sanitized: list[str] = []
    for part in command:
        value = str(part)
        if any(marker in value.upper() for marker in ["TOKEN", "SECRET", "PASSWORD", "COOKIE", "KEY="]):
            sanitized.append("[REDACTED]")
        else:
            sanitized.append(value)
    return sanitized


def tail(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    main()
