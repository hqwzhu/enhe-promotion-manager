#!/usr/bin/env python3
"""Audit publish readiness and authorization requirements before platform writes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from env_loader import (
    YOUTUBE_ACCESS_TOKEN_ENVS,
    YOUTUBE_CLIENT_ID_ENVS,
    YOUTUBE_CLIENT_SECRET_ENVS,
    blank_env_names,
    load_project_env,
    preparse_env_file,
    present_env_names,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PUBLISH_QUEUE = SCRIPTS / "publish_queue.py"
TODAY = date.today().isoformat()
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]


PLATFORM_RULES = {
    "github": {
        "mode": "official_api_publish",
        "requiredEnvAny": ["GITHUB_TOKEN", "GH_TOKEN"],
        "target": "githubRepo",
        "executor": "publish_executor.py",
        "notes": "Official GitHub REST writes are supported for files, issues, and releases.",
    },
    "youtube": {
        "mode": "official_api_publish",
        "requiredEnvAny": list(YOUTUBE_ACCESS_TOKEN_ENVS),
        "alternativeEnvAll": ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"],
        "alternativeEnvGroups": [list(YOUTUBE_CLIENT_ID_ENVS), list(YOUTUBE_CLIENT_SECRET_ENVS)],
        "target": "youtubeVideoFile",
        "executor": "publish_executor.py or youtube_oauth_publish.py",
        "notes": "YouTube upload requires OAuth channel authorization and quota.",
    },
    "zhihu": {
        "mode": "manual_publish_required",
        "requiredEnvAny": [],
        "target": "",
        "executor": "",
        "notes": "No verified stable public article publishing API is integrated.",
    },
    "xiaohongshu": {
        "mode": "manual_publish_required",
        "requiredEnvAny": [],
        "target": "",
        "executor": "",
        "notes": "No verified stable public note publishing API is integrated.",
    },
    "douyin": {
        "mode": "browser_assisted_publish",
        "requiredEnvAny": [],
        "target": "douyinVideoFile",
        "executor": "browser_publish_session.py / browser_publish_assistant.py",
        "notes": "Douyin official authorization is not available in the current operator setup, so Douyin publishes through browser-assisted/manual payloads and stops before the final publish action. The official executor remains a reserved future port.",
    },
    "tiktok": {
        "mode": "official_api_candidate",
        "requiredEnvAll": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
        "target": "tiktokDeveloperApp",
        "executor": "",
        "notes": "TikTok Direct Post requires approved app product, video.publish scope, and creator authorization; direct executor is not integrated.",
    },
}


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    queue_path = resolve_or_build_queue(args, out_dir, steps)
    queue = read_json(queue_path) if queue_path else {}
    manifest = read_json(Path(args.workflow_manifest)) if args.workflow_manifest else {}
    records = build_records(args, queue, manifest)
    report = {
        "generatedAt": TODAY,
        "envLoad": env_load,
        "status": readiness_status(records),
        "mode": "execute_requested" if args.execute_publish else "dry_run_or_planning",
        "approval": {
            "approvalPhrase": APPROVAL_PHRASE,
            "publishExecutionRequested": args.execute_publish,
            "approvalProvided": args.approval == APPROVAL_PHRASE,
        },
        "inputs": {
            "workflowManifest": args.workflow_manifest,
            "publishQueue": str(queue_path) if queue_path else "",
            "githubRepo": args.github_repo,
            "githubAction": args.github_action,
            "githubPath": args.github_path,
            "githubBranchProvided": bool(args.github_branch),
            "githubTagNameProvided": bool(args.github_tag_name),
            "youtubeVideoFile": args.youtube_video_file,
            "youtubePrivacyStatus": args.youtube_privacy_status,
            "youtubeCategoryId": args.youtube_category_id,
            "douyinVideoFile": args.douyin_video_file,
        },
        "records": records,
        "summary": summarize(records),
        "nextActions": next_actions(records),
        "guardrails": [
            "This report records credential presence only; it never writes secret values.",
            "Official writes require explicit execution request, platform credentials, target information, and exact approval phrase.",
            "Manual/browser-assisted platforms remain queued until a real published URL or user-visible evidence is registered.",
            "Do not auto-login, bypass captcha/risk controls, extract cookies, or use hidden/private endpoints.",
        ],
        "steps": steps,
    }
    write_report(out_dir, report)
    print(f"Publish readiness report written to: {(report_dir(out_dir) / 'publish-readiness.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit readiness for official, browser-assisted, and manual publishing.")
    parser.add_argument("--workflow-manifest", default="", help="Existing workflow manifest.")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before auditing credential presence. Values are never written to reports.")
    parser.add_argument("--publish-queue", default="", help="Existing publish-queue.json.")
    parser.add_argument("--build-queue", action="store_true", help="Build a dry-run/guarded publish queue from --workflow-manifest first.")
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter. Defaults to queue/workflow platforms or common defaults.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--promotion-out-dir", default="", help="Workflow output dir when building a queue. Inferred from manifest when omitted.")
    parser.add_argument("--execute-publish", action="store_true")
    parser.add_argument("--approval", default="")
    parser.add_argument("--github-repo", default="")
    parser.add_argument("--github-action", default="file", choices=["file", "issue", "release"])
    parser.add_argument("--github-path", default="PROMOTION.md")
    parser.add_argument("--github-branch", default="")
    parser.add_argument("--github-tag-name", default="")
    parser.add_argument("--youtube-video-file", default="")
    parser.add_argument("--youtube-privacy-status", default="private", choices=["private", "public", "unlisted"])
    parser.add_argument("--youtube-category-id", default="22")
    parser.add_argument("--douyin-video-file", default="")
    return parser.parse_args()


def resolve_or_build_queue(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> Path | None:
    if args.publish_queue:
        path = Path(args.publish_queue)
        return path if path.exists() else None
    if not args.build_queue:
        return None
    if not args.workflow_manifest:
        raise SystemExit("--build-queue requires --workflow-manifest.")
    manifest_path = Path(args.workflow_manifest)
    promotion_dir = Path(args.promotion_out_dir) if args.promotion_out_dir else infer_promotion_out_dir(manifest_path, out_dir)
    command = [
        sys.executable,
        str(PUBLISH_QUEUE),
        "--workflow-manifest",
        str(manifest_path),
        "--promotion-out-dir",
        str(promotion_dir),
        "--out-dir",
        str(out_dir),
    ]
    append_if_present(command, "--platforms", args.platforms)
    if args.execute_publish:
        command.append("--execute")
        append_if_present(command, "--approval", args.approval)
    append_if_present(command, "--github-repo", args.github_repo)
    append_if_present(command, "--github-action", args.github_action)
    append_if_present(command, "--github-path", args.github_path)
    append_if_present(command, "--github-branch", args.github_branch)
    append_if_present(command, "--github-tag-name", args.github_tag_name)
    append_if_present(command, "--youtube-video-file", args.youtube_video_file)
    append_if_present(command, "--youtube-privacy-status", args.youtube_privacy_status)
    append_if_present(command, "--youtube-category-id", args.youtube_category_id)
    append_if_present(command, "--douyin-video-file", args.douyin_video_file)
    step = run_command("publish_queue", command)
    steps.append(step)
    queue_path = out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"
    return queue_path if queue_path.exists() else None


def build_records(args: argparse.Namespace, queue: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    queue_by_platform = {str(item.get("platform")): item for item in queue.get("records", []) if item.get("platform")}
    platforms = requested_platforms(args, queue_by_platform, manifest)
    return [build_platform_record(args, platform, queue_by_platform.get(platform, {})) for platform in platforms]


def build_platform_record(args: argparse.Namespace, platform: str, queue_item: dict[str, Any]) -> dict[str, Any]:
    rule = PLATFORM_RULES.get(platform, {"mode": "unsupported", "requiredEnvAny": [], "notes": "Unsupported platform."})
    env = env_status(rule)
    target = target_status(args, platform, rule, queue_item)
    approval = approval_status(args, platform, rule)
    queue_status = str(queue_item.get("status") or "")
    readiness = platform_readiness(platform, rule, env, target, approval, queue_status)
    return {
        "platform": platform,
        "publishMode": queue_item.get("publishMode") or rule.get("mode", "unsupported"),
        "readiness": readiness,
        "queueStatus": queue_status,
        "credentialStatus": env,
        "targetStatus": target,
        "approvalStatus": approval,
        "executor": rule.get("executor", ""),
        "contentDraft": queue_item.get("contentDraft", ""),
        "publishedUrl": (queue_item.get("officialExecution") or {}).get("publishedUrl", ""),
        "notes": rule.get("notes", ""),
        "nextAction": platform_next_action(platform, readiness, env, target, approval),
    }


def env_status(rule: dict[str, Any]) -> dict[str, Any]:
    any_names = list(rule.get("requiredEnvAny") or [])
    all_names = list(rule.get("requiredEnvAll") or [])
    alternative_all = list(rule.get("alternativeEnvAll") or [])
    alternative_groups = [list(group) for group in rule.get("alternativeEnvGroups") or []]
    grouped_names = [name for group in alternative_groups for name in group]
    present_any = present_env_names(any_names)
    present_all = present_env_names(all_names)
    present_alternative = present_env_names(alternative_all + grouped_names)
    alternative_all_ready = bool(alternative_all) and len(present_env_names(alternative_all)) == len(alternative_all)
    alternative_group_ready = bool(alternative_groups) and all(any(os.environ.get(name) for name in group) for group in alternative_groups)
    if any_names:
        ready = bool(present_any) or alternative_all_ready or alternative_group_ready
    elif all_names:
        ready = len(present_all) == len(all_names)
    else:
        ready = True
    missing = missing_env_names(any_names, all_names, alternative_all, alternative_groups)
    all_known_names = any_names + all_names + alternative_all + grouped_names
    return {
        "ready": ready,
        "requiredAny": any_names,
        "requiredAll": all_names,
        "alternativeAll": alternative_all,
        "alternativeGroups": alternative_groups,
        "presentEnv": sorted(set(present_any + present_all + present_alternative)),
        "missingEnv": missing,
        "blankEnv": blank_env_names(all_known_names),
        "valuesStored": False,
    }


def missing_env_names(
    any_names: list[str],
    all_names: list[str],
    alternative_all: list[str],
    alternative_groups: list[list[str]],
) -> list[str]:
    missing: list[str] = []
    if any_names and not any(os.environ.get(name) for name in any_names):
        missing.extend(any_names)
    missing.extend(name for name in all_names if not os.environ.get(name))
    if alternative_groups:
        for group in alternative_groups:
            if not any(os.environ.get(name) for name in group):
                missing.append(" or ".join(group))
    elif alternative_all and not all(os.environ.get(name) for name in alternative_all):
        missing.extend(name for name in alternative_all if not os.environ.get(name))
    return missing


def target_status(args: argparse.Namespace, platform: str, rule: dict[str, Any], queue_item: dict[str, Any]) -> dict[str, Any]:
    if platform == "github":
        value = args.github_repo or github_repo_from_queue(queue_item)
        return {"ready": bool(value), "field": "githubRepo", "valuePresent": bool(value), "missing": "" if value else "--github-repo"}
    if platform == "youtube":
        value = args.youtube_video_file or youtube_file_from_queue(queue_item)
        return {"ready": bool(value), "field": "youtubeVideoFile", "valuePresent": bool(value), "missing": "" if value else "--youtube-video-file"}
    if platform == "douyin":
        value = args.douyin_video_file or douyin_file_from_queue(queue_item)
        return {
            "ready": True,
            "field": "douyinVideoFile",
            "valuePresent": bool(value),
            "missing": "" if value else "optional --douyin-video-file to attach an MP4 asset",
        }
    if platform == "tiktok":
        return {"ready": False, "field": rule.get("target", ""), "valuePresent": False, "missing": "approved developer/open-platform app integration"}
    return {"ready": True, "field": "", "valuePresent": False, "missing": ""}


def approval_status(args: argparse.Namespace, platform: str, rule: dict[str, Any]) -> dict[str, Any]:
    official_like = rule.get("mode") in {"official_api_publish", "official_api_candidate"}
    required = official_like or platform in {"tiktok"}
    return {
        "required": required,
        "executionRequested": args.execute_publish,
        "approvalProvided": args.approval == APPROVAL_PHRASE,
        "ready": (not args.execute_publish) or args.approval == APPROVAL_PHRASE,
    }


def platform_readiness(
    platform: str,
    rule: dict[str, Any],
    env: dict[str, Any],
    target: dict[str, Any],
    approval: dict[str, Any],
    queue_status: str,
) -> str:
    mode = rule.get("mode")
    if queue_status == "published":
        return "already_published"
    if platform in {"zhihu", "xiaohongshu"}:
        return "manual_publish_required"
    if platform == "douyin":
        return "browser_assisted_publish_ready"
    if platform == "tiktok":
        return "official_app_integration_required"
    if mode == "official_api_publish":
        if not target["ready"]:
            return "missing_target"
        if not env["ready"]:
            return "missing_credentials"
        if not approval["ready"]:
            return "missing_approval"
        if approval["executionRequested"] and approval["approvalProvided"]:
            return "ready_to_execute"
        return "dry_run_ready"
    return "unsupported"


def platform_next_action(
    platform: str,
    readiness: str,
    env: dict[str, Any],
    target: dict[str, Any],
    approval: dict[str, Any],
) -> str:
    if readiness == "ready_to_execute":
        return "Run the official executor or publish queue with execution enabled."
    if readiness == "dry_run_ready":
        return f"Review dry-run, then add --execute-publish --approval {APPROVAL_PHRASE} when ready."
    if readiness == "missing_target":
        return f"Provide {target['missing']}."
    if readiness == "missing_credentials":
        return "Set required environment variables: " + ", ".join(env["missingEnv"])
    if readiness == "missing_approval":
        return f"Add --approval {APPROVAL_PHRASE}."
    if readiness == "manual_publish_required":
        return "Use the generated draft in a user-visible browser/manual workflow, then register the real published URL."
    if readiness == "browser_assisted_publish_ready":
        return "Use browser-assisted Douyin publishing, review the prepared payload, and let the user complete the final publish action."
    if readiness == "official_app_integration_required":
        return "Integrate approved TikTok Direct Post app scopes and creator authorization."
    if readiness == "already_published":
        return "Register or recover metrics from the published URL."
    return f"Manual review required for {platform}."


def requested_platforms(args: argparse.Namespace, queue_by_platform: dict[str, dict[str, Any]], manifest: dict[str, Any]) -> list[str]:
    if args.platforms:
        return split_csv(args.platforms)
    if queue_by_platform:
        return sorted(queue_by_platform)
    platforms = manifest.get("product", {}).get("platforms")
    if isinstance(platforms, list) and platforms:
        return [str(item) for item in platforms]
    return DEFAULT_PLATFORMS


def summarize(records: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {"total": len(records)}
    for record in records:
        key = str(record["readiness"])
        summary[key] = summary.get(key, 0) + 1
    return dict(sorted(summary.items()))


def next_actions(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    actions = []
    for record in records:
        actions.append({"platform": record["platform"], "readiness": record["readiness"], "action": record["nextAction"]})
    return actions


def readiness_status(records: list[dict[str, Any]]) -> str:
    readiness = {record["readiness"] for record in records}
    if readiness and readiness <= {"ready_to_execute", "already_published"}:
        return "ready_to_execute"
    if readiness & {"ready_to_execute", "dry_run_ready", "manual_publish_required", "browser_assisted_publish_ready"}:
        return "partial_ready"
    return "blocked"


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "publish-readiness.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "publish-readiness.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Publish Readiness",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Mode: `{report['mode']}`",
        f"- Approval provided: {report['approval']['approvalProvided']}",
        "",
        "## Platforms",
    ]
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['platform']}",
                f"- Readiness: `{record['readiness']}`",
                f"- Queue status: `{record['queueStatus']}`",
                f"- Credential env present: {', '.join(record['credentialStatus']['presentEnv']) or 'none'}",
                f"- Target ready: {record['targetStatus']['ready']}",
                f"- Next action: {record['nextAction']}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "name": name,
        "command": display_command(command),
        "exitCode": result.returncode,
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def infer_promotion_out_dir(manifest_path: Path, fallback: Path) -> Path:
    if manifest_path.name == "workflow-manifest.json" and len(manifest_path.parents) >= 4:
        parent_parts = manifest_path.parts[-4:]
        if parent_parts == ("reports", "promotion-manager", "agent-run", "workflow-manifest.json"):
            return manifest_path.parents[3]
    return fallback


def youtube_file_from_queue(queue_item: dict[str, Any]) -> str:
    command = ((queue_item.get("officialExecution") or {}).get("command") or [])
    if "--video-file" in command:
        index = command.index("--video-file")
        if index + 1 < len(command):
            return str(command[index + 1])
    return ""


def douyin_file_from_queue(queue_item: dict[str, Any]) -> str:
    video = queue_item.get("video") if isinstance(queue_item.get("video"), dict) else {}
    path_value = str(video.get("path") or "").strip()
    if path_value:
        return path_value
    command = ((queue_item.get("officialExecution") or {}).get("command") or [])
    if "--douyin-video-file" in command:
        index = command.index("--douyin-video-file")
        if index + 1 < len(command):
            return str(command[index + 1])
    return ""


def github_repo_from_queue(queue_item: dict[str, Any]) -> str:
    command = ((queue_item.get("officialExecution") or {}).get("command") or [])
    if "--github-repo" in command:
        index = command.index("--github-repo")
        if index + 1 < len(command):
            return str(command[index + 1])
    return ""


def append_if_present(command: list[str], flag: str, value: str) -> None:
    if value:
        command.extend([flag, value])


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/publish-readiness"


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
