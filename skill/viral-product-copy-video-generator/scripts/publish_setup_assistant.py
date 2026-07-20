#!/usr/bin/env python3
"""Create a publish setup kit from a publish-readiness report."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
OFFICIAL_READINESS = {"missing_credentials", "missing_target", "missing_approval", "dry_run_ready", "ready_to_execute"}
BROWSER_OR_MANUAL_READINESS = {
    "manual_publish_required",
    "browser_assisted_or_official_app_required",
    "browser_assisted_publish_ready",
}
PLATFORM_SETUP_GUIDES = {
    "github": {
        "automationStatus": "official_executor_integrated",
        "developerConsole": "https://github.com/settings/tokens?type=beta",
        "officialDocs": [
            {"label": "GitHub REST Contents API", "url": "https://docs.github.com/en/rest/repos/contents"},
            {"label": "GitHub REST Releases API", "url": "https://docs.github.com/en/rest/releases/releases"},
        ],
        "requiredCapabilities": [
            "Fine-grained personal access token or GitHub App token scoped to the target repository.",
            "Contents repository permission set to write for file publishing.",
            "Issues or Releases permissions only when using those GitHub actions.",
        ],
        "targetInputs": ["--github-repo owner/repo", "--github-path PROMOTION.md"],
        "credentialEnvNames": ["GITHUB_TOKEN", "GH_TOKEN"],
        "constraints": [
            "Do not store token values in this repository.",
            "Workflow files require additional workflow permission when editing .github/workflows.",
        ],
    },
    "youtube": {
        "automationStatus": "official_executor_integrated",
        "developerConsole": "https://console.cloud.google.com/apis/credentials",
        "officialDocs": [
            {"label": "YouTube videos.insert", "url": "https://developers.google.com/youtube/v3/docs/videos/insert"},
            {"label": "Google OAuth native apps", "url": "https://developers.google.com/identity/protocols/oauth2/native-app"},
        ],
        "requiredCapabilities": [
            "Google Cloud project with YouTube Data API enabled.",
            "OAuth consent and a user-authorized channel with youtube.upload scope.",
            "A real MP4 video file and reviewed title, description, tags, and privacy status.",
        ],
        "targetInputs": ["--youtube-video-file ./promotion-output/videos/product-youtube.mp4"],
        "credentialEnvNames": [
            "YOUTUBE_ACCESS_TOKEN",
            "YOUTUBE_OAUTH_ACCESS_TOKEN",
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN",
        ],
        "constraints": [
            "Unverified API projects may be restricted to private visibility until audit requirements are satisfied.",
            "Uploads consume YouTube quota and require the channel owner's authorization.",
        ],
    },
    "douyin": {
        "automationStatus": "browser_or_manual_current_official_port_reserved",
        "developerConsole": "https://open.douyin.com/",
        "officialDocs": [
            {"label": "Douyin publish solution", "url": "https://open.douyin.com/platform/resource/docs/ability/content-management/douyin-publish-solution"},
            {"label": "Douyin upload video", "url": "https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/upload/"},
            {"label": "Douyin create video", "url": "https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/create-video"},
        ],
        "requiredCapabilities": [
            "Use the generated title, copy, hashtags, cover/detail images, and MP4 in a user-visible Douyin creator workflow.",
            "Stop before the final publish action; the account owner completes login, captcha, account verification, and final submit.",
            "A real MP4/WebM video file should satisfy Douyin size, duration, review, and watermark constraints.",
        ],
        "targetInputs": ["--douyin-video-file ./promotion-output/videos/product-douyin.mp4"],
        "credentialEnvNames": [],
        "constraints": [
            "Official API publishing is reserved for a future verified open-platform authorization path.",
            "Do not use cookies, simulated login, private endpoints, captcha bypass, or scripted final publish clicks.",
            "Published status requires the real Douyin URL or user-provided evidence after manual/browser-assisted publishing.",
        ],
    },
    "tiktok": {
        "automationStatus": "official_candidate_executor_not_integrated",
        "developerConsole": "https://developers.tiktok.com/",
        "officialDocs": [
            {"label": "TikTok Content Posting API", "url": "https://developers.tiktok.com/doc/content-posting-api-get-started/"},
        ],
        "requiredCapabilities": [
            "Registered TikTok developer app with Content Posting API product enabled.",
            "Approved video.publish scope and target creator authorization.",
            "Access token and open ID for the authorized creator.",
        ],
        "targetInputs": ["approved TikTok app integration"],
        "credentialEnvNames": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
        "constraints": [
            "Direct executor is not integrated in this Skill yet.",
            "Unaudited clients may have visibility restrictions until platform audit is complete.",
        ],
    },
    "zhihu": {
        "automationStatus": "browser_or_manual_until_official_publish_access_verified",
        "developerConsole": "",
        "officialDocs": [],
        "requiredCapabilities": [
            "Use the generated article draft in a user-visible Zhihu creator/editor workflow.",
            "Register the real published URL and evidence after manual/browser-assisted publishing.",
        ],
        "targetInputs": ["browser/manual editor URL", "published URL evidence after publish"],
        "credentialEnvNames": [],
        "constraints": [
            "No stable official article publishing API is integrated.",
            "Do not use private endpoints, stored cookies, captcha bypass, or hidden browser tokens.",
        ],
    },
    "xiaohongshu": {
        "automationStatus": "browser_or_manual_until_official_publish_access_verified",
        "developerConsole": "https://open.xiaohongshu.com/",
        "officialDocs": [
            {"label": "Xiaohongshu open platform docs", "url": "https://open.xiaohongshu.com/document/api"},
        ],
        "requiredCapabilities": [
            "Use the generated note, tags, and cover text in a user-visible Xiaohongshu creator workflow.",
            "Register the real published URL and evidence after manual/browser-assisted publishing.",
        ],
        "targetInputs": ["browser/manual creator URL", "published URL evidence after publish"],
        "credentialEnvNames": [],
        "constraints": [
            "No stable official note publishing API is integrated.",
            "Do not use private endpoints, stored cookies, captcha bypass, or hidden browser tokens.",
        ],
    },
}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    readiness_path = resolve_readiness_path(args, out_dir)
    readiness = read_json(readiness_path) if readiness_path else {}
    records = selected_records(readiness, args.platforms)
    setup_records = [build_setup_record(record, readiness) for record in records]
    env_names = collect_env_names(setup_records)
    artifacts = write_artifacts(out_dir, readiness_path, setup_records, env_names)
    report = build_report(args, readiness_path, readiness, setup_records, env_names, artifacts)
    write_report(out_dir, report)
    print(f"Publish setup assistant written to: {(report_dir(out_dir) / 'publish-setup.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate credential, target, and approval setup artifacts for publishing.")
    parser.add_argument("--publish-readiness", default="", help="Path to publish-readiness.json. Defaults to <out-dir>/reports/promotion-manager/publish-readiness/publish-readiness.json.")
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def resolve_readiness_path(args: argparse.Namespace, out_dir: Path) -> Path | None:
    if args.publish_readiness:
        path = Path(args.publish_readiness)
        return path if path.exists() else None
    candidate = out_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json"
    return candidate if candidate.exists() else None


def selected_records(readiness: dict[str, Any], platforms: str) -> list[dict[str, Any]]:
    records = [item for item in readiness.get("records", []) if isinstance(item, dict)]
    selected = split_csv(platforms)
    if selected:
        records = [item for item in records if str(item.get("platform", "")).lower() in selected]
    return records


def build_setup_record(record: dict[str, Any], readiness_report: dict[str, Any]) -> dict[str, Any]:
    platform = str(record.get("platform", "")).strip()
    readiness = str(record.get("readiness", "")).strip()
    credential = record.get("credentialStatus") if isinstance(record.get("credentialStatus"), dict) else {}
    target = record.get("targetStatus") if isinstance(record.get("targetStatus"), dict) else {}
    approval = record.get("approvalStatus") if isinstance(record.get("approvalStatus"), dict) else {}
    category = setup_category(readiness)
    env_names = ordered_unique(
        list(credential.get("requiredAny") or [])
        + list(credential.get("requiredAll") or [])
        + list(credential.get("alternativeAll") or [])
        + flatten_groups(credential.get("alternativeGroups") or [])
    )
    missing_env = ordered_unique(list(credential.get("missingEnv") or []))
    commands = setup_commands(platform, readiness, readiness_report)
    return {
        "platform": platform,
        "publishMode": record.get("publishMode", ""),
        "readiness": readiness,
        "setupCategory": category,
        "credentialEnvNames": env_names,
        "missingEnv": missing_env,
        "target": {
            "ready": bool(target.get("ready", True)),
            "field": target.get("field", ""),
            "missing": target.get("missing", ""),
        },
        "approval": {
            "required": bool(approval.get("required", False)),
            "approvalPhrase": APPROVAL_PHRASE if approval.get("required", False) else "",
            "provided": bool(approval.get("approvalProvided", False)),
        },
        "setupSteps": setup_steps(platform, category, missing_env, target, approval, record),
        "commands": commands,
        "sourceNextAction": record.get("nextAction", ""),
        "guardrail": platform_guardrail(platform, readiness),
    }


def setup_category(readiness: str) -> str:
    if readiness == "missing_credentials":
        return "credential_setup_required"
    if readiness == "missing_target":
        return "target_setup_required"
    if readiness == "missing_approval":
        return "approval_required"
    if readiness == "dry_run_ready":
        return "execution_approval_required"
    if readiness == "ready_to_execute":
        return "ready_to_execute"
    if readiness in BROWSER_OR_MANUAL_READINESS:
        return "browser_or_manual_publish"
    if readiness == "already_published":
        return "published_metrics_recovery"
    if readiness == "official_app_integration_required":
        return "platform_app_integration_required"
    return "manual_review_required"


def setup_steps(
    platform: str,
    category: str,
    missing_env: list[str],
    target: dict[str, Any],
    approval: dict[str, Any],
    record: dict[str, Any],
) -> list[str]:
    if category == "credential_setup_required":
        return [
            "Set required environment variables in the shell or OS scheduler; do not write real secret values into repo files.",
            "Rerun publish readiness to verify credentials are present by name.",
            f"Use --execute-publish --approval {APPROVAL_PHRASE} only after reviewing the dry-run output.",
        ]
    if category == "target_setup_required":
        missing = target.get("missing") or "the required platform target"
        return [f"Provide {missing}.", "Rerun publish readiness before attempting official execution."]
    if category == "approval_required":
        return [f"Add the exact approval phrase {APPROVAL_PHRASE} when executing official writes."]
    if category == "execution_approval_required":
        return [
            "Review generated drafts, targets, and dry-run execution reports.",
            f"Execute only with --execute-publish --approval {APPROVAL_PHRASE}.",
        ]
    if category == "ready_to_execute":
        return ["The readiness report says execution gates are satisfied; run the guarded executor and keep the official execution report."]
    if category == "browser_or_manual_publish":
        return [
            "Use the browser-assisted payload or manual draft in a user-visible creator/editor page.",
            "Do not auto-login, bypass challenges, or click final publish by script.",
            "After publishing, register the real published URL and evidence for metrics recovery.",
        ]
    if category == "published_metrics_recovery":
        return ["Use the registered published URL for public metrics, comments, and business attribution recovery."]
    if category == "platform_app_integration_required":
        return [f"Complete official {platform} app approval and add a reviewed executor before claiming direct publishing."]
    next_action = str(record.get("nextAction") or "Review platform readiness manually.")
    return [next_action]


def setup_commands(platform: str, readiness: str, readiness_report: dict[str, Any]) -> dict[str, str]:
    inputs = readiness_report.get("inputs") if isinstance(readiness_report.get("inputs"), dict) else {}
    queue = str(inputs.get("publishQueue") or "").strip()
    manifest = str(inputs.get("workflowManifest") or "").strip()
    out_dir = infer_out_dir(queue, manifest)
    readiness_base = ["python", "scripts/publish_readiness_runner.py"]
    if queue:
        readiness_base.extend(["--publish-queue", queue])
    elif manifest:
        readiness_base.extend(["--workflow-manifest", manifest, "--build-queue"])
    readiness_base.extend(["--platforms", platform])
    append_input(readiness_base, "--github-repo", inputs.get("githubRepo", ""))
    append_input(readiness_base, "--youtube-video-file", inputs.get("youtubeVideoFile", ""))
    append_input(readiness_base, "--douyin-video-file", inputs.get("douyinVideoFile", ""))
    if out_dir:
        readiness_base.extend(["--out-dir", out_dir])

    execute = list(readiness_base)
    execute.extend(["--execute-publish", "--approval", APPROVAL_PHRASE])
    commands = {"rerunReadiness": display_command(readiness_base)}
    if readiness in OFFICIAL_READINESS:
        commands["executeWhenReady"] = display_command(execute)
    if readiness in BROWSER_OR_MANUAL_READINESS and queue:
        browser = [
            "python",
            "scripts/browser_publish_assistant.py",
            "--publish-queue",
            queue,
            "--platforms",
            platform,
        ]
        if out_dir:
            browser.extend(["--out-dir", out_dir])
        commands["prepareBrowserPublish"] = display_command(browser)
    commands["registerPublishedUrl"] = (
        f"python scripts/published_items.py --platform {platform} --published-url \"https://...\" "
        f"--title \"Published {platform} content\" --evidence \"./screenshots/{platform}-published.png\""
        + (f" --out-dir \"{out_dir}\"" if out_dir else "")
    )
    return commands


def infer_out_dir(queue: str, manifest: str) -> str:
    for value in [queue, manifest]:
        if not value:
            continue
        path = Path(value)
        parts = path.parts
        if len(parts) >= 4 and parts[-4:-1] == ("reports", "promotion-manager", "publish-queue"):
            return str(path.parents[3])
        if len(parts) >= 4 and parts[-4:-1] == ("reports", "promotion-manager", "agent-run"):
            return str(path.parents[3])
    return ""


def platform_guardrail(platform: str, readiness: str) -> str:
    if readiness in BROWSER_OR_MANUAL_READINESS:
        return f"{platform} remains browser-assisted/manual until verified official publishing access exists."
    if readiness in OFFICIAL_READINESS:
        return "Official writes still require credentials, target readiness, and exact approval; no credential values are stored."
    return "Use only official APIs, public/browser-visible evidence, or user-provided exports."


def collect_env_names(records: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for record in records:
        names.extend(record.get("credentialEnvNames") or [])
    return ordered_unique(names)


def write_artifacts(out_dir: Path, readiness_path: Path | None, records: list[dict[str, Any]], env_names: list[str]) -> dict[str, str]:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    env_file = directory / "publish-credentials.example.env"
    checklist_file = directory / "publish-setup-checklist.md"
    platform_guide_json = directory / "platform-setup-guide.json"
    platform_guide_md = directory / "platform-setup-guide.md"
    platform_guides = build_platform_setup_guides(records)
    env_file.write_text(render_env_template(env_names), encoding="utf-8")
    checklist_file.write_text(render_checklist(readiness_path, records) + "\n", encoding="utf-8")
    platform_guide_json.write_text(json.dumps(platform_guides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    platform_guide_md.write_text(render_platform_setup_guide(platform_guides) + "\n", encoding="utf-8")
    return {
        "envTemplate": str(env_file),
        "checklist": str(checklist_file),
        "platformSetupGuide": str(platform_guide_md),
        "platformSetupGuideJson": str(platform_guide_json),
    }


def build_report(
    args: argparse.Namespace,
    readiness_path: Path | None,
    readiness: dict[str, Any],
    records: list[dict[str, Any]],
    env_names: list[str],
    artifacts: dict[str, str],
) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "status": "ready" if records else "blocked_missing_readiness",
        "input": {
            "publishReadiness": str(readiness_path) if readiness_path else "",
            "platforms": args.platforms,
            "sourceStatus": readiness.get("status", ""),
        },
        "summary": summarize(records, env_names),
        "records": records,
        "artifacts": artifacts,
        "guardrails": [
            "This setup kit writes environment variable names only, never credential values.",
            "The .env file is an example template; do not commit real secrets.",
            "Official writes require reviewed dry-runs, target information, environment credentials, and exact approval.",
            "Browser-assisted/manual platforms must stop for login, captcha, account verification, and final publish actions.",
            "Published URLs, metrics, orders, and revenue require real evidence before retrospective or optimization.",
        ],
    }


def summarize(records: list[dict[str, Any]], env_names: list[str]) -> dict[str, int]:
    summary: dict[str, int] = {
        "total": len(records),
        "credentialEnvNames": len(env_names),
    }
    for record in records:
        category = str(record.get("setupCategory") or "unknown")
        summary[category] = summary.get(category, 0) + 1
    return dict(sorted(summary.items()))


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "publish-setup.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "publish-setup.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Publish Setup Assistant",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Readiness source: {report['input'].get('publishReadiness', '')}",
        f"- Env template: {report['artifacts'].get('envTemplate', '')}",
        f"- Checklist: {report['artifacts'].get('checklist', '')}",
        f"- Platform setup guide: {report['artifacts'].get('platformSetupGuide', '')}",
        "",
        "## Platforms",
    ]
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['platform']}",
                f"- Setup category: `{record['setupCategory']}`",
                f"- Readiness: `{record['readiness']}`",
                f"- Missing env: {', '.join(record.get('missingEnv') or []) or 'none'}",
                f"- Target missing: {record.get('target', {}).get('missing') or 'none'}",
                f"- Approval required: {record.get('approval', {}).get('required', False)}",
                "- Steps:",
            ]
        )
        lines.extend(f"  - {step}" for step in record.get("setupSteps", []))
        if record.get("commands"):
            lines.append("- Commands:")
            for name, command in record["commands"].items():
                lines.append(f"  - {name}: `{command}`")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_env_template(env_names: list[str]) -> str:
    lines = [
        "# Publish credential template generated by publish_setup_assistant.py",
        "# Do not commit real secrets. Set real values in your shell, OS scheduler, or secret manager.",
    ]
    if not env_names:
        lines.append("# No official publishing credential variables were required by the selected readiness records.")
    for name in env_names:
        lines.append(f"{name}=")
    return "\n".join(lines) + "\n"


def render_checklist(readiness_path: Path | None, records: list[dict[str, Any]]) -> str:
    lines = [
        "# Publish Setup Checklist",
        "",
        f"- Source readiness report: {readiness_path or ''}",
        "- Review dry-run outputs before execution.",
        "- Keep all real credentials outside the repository.",
        "- Register real published URLs before metrics recovery.",
        "",
    ]
    for record in records:
        lines.append(f"## {record['platform']}")
        for step in record.get("setupSteps", []):
            lines.append(f"- [ ] {step}")
        lines.append("")
    return "\n".join(lines)


def build_platform_setup_guides(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    guides: list[dict[str, Any]] = []
    for record in records:
        platform = str(record.get("platform") or "").lower()
        base = PLATFORM_SETUP_GUIDES.get(platform, {})
        commands = record.get("commands") if isinstance(record.get("commands"), dict) else {}
        env_names = ordered_unique(
            list(record.get("credentialEnvNames") or [])
            + list(base.get("credentialEnvNames") or [])
        )
        guides.append(
            {
                "platform": platform,
                "automationStatus": base.get("automationStatus", "manual_review_required"),
                "developerConsole": base.get("developerConsole", ""),
                "officialDocs": base.get("officialDocs", []),
                "requiredCapabilities": base.get("requiredCapabilities", []),
                "credentialEnvNames": env_names,
                "missingEnv": record.get("missingEnv") or [],
                "targetInputs": base.get("targetInputs", []),
                "targetStatus": record.get("target", {}),
                "approval": record.get("approval", {}),
                "setupCategory": record.get("setupCategory", ""),
                "readiness": record.get("readiness", ""),
                "verificationCommands": {
                    "rerunReadiness": commands.get("rerunReadiness", ""),
                    "dryRunOrExecuteWhenApproved": commands.get("executeWhenReady", ""),
                    "prepareBrowserPublish": commands.get("prepareBrowserPublish", ""),
                    "registerPublishedUrl": commands.get("registerPublishedUrl", ""),
                },
                "setupSteps": platform_setup_steps(platform, record, base),
                "constraints": base.get("constraints", []) + [record.get("guardrail", "")],
                "secretHandling": [
                    "Set real credential values only in the shell, OS scheduler, or secret manager.",
                    "Do not paste, print, or commit API keys, OAuth tokens, passwords, cookies, or hidden browser tokens.",
                    "This guide records variable names and commands only; it must not contain credential values.",
                ],
            }
        )
    return guides


def platform_setup_steps(platform: str, record: dict[str, Any], base: dict[str, Any]) -> list[str]:
    category = str(record.get("setupCategory") or "")
    steps = [
        f"Review the official documentation and platform account requirements for {platform}.",
        "Create or select the correct developer app/account and request the required publishing permissions.",
    ]
    env_names = ordered_unique(list(record.get("credentialEnvNames") or []) + list(base.get("credentialEnvNames") or []))
    if env_names:
        steps.append("Set these environment variable names outside the repository: " + ", ".join(env_names) + ".")
    target_inputs = list(base.get("targetInputs") or [])
    if target_inputs:
        steps.append("Prepare target inputs: " + ", ".join(target_inputs) + ".")
    if category == "browser_or_manual_publish":
        steps.append("Use generated browser/manual payloads, stop before final publish, and let the user complete any login, captcha, or final publish action.")
    elif category in {"credential_setup_required", "target_setup_required", "approval_required", "execution_approval_required", "ready_to_execute"}:
        steps.append("Rerun publish readiness until the platform is dry_run_ready or ready_to_execute.")
        steps.append(f"Execute official writes only with --execute-publish --approval {APPROVAL_PHRASE}.")
    else:
        steps.extend(record.get("setupSteps") or [])
    steps.append("After publishing, register the real published URL and evidence before metrics recovery.")
    return ordered_unique(steps)


def render_platform_setup_guide(guides: list[dict[str, Any]]) -> str:
    lines = [
        "# Platform Setup Guide",
        "",
        "This guide contains setup instructions and environment variable names only. It must not contain real secrets.",
    ]
    if not guides:
        lines.append("")
        lines.append("No platform readiness records were available. Run publish readiness first.")
        return "\n".join(lines)
    for guide in guides:
        lines.extend(
            [
                "",
                f"## {guide['platform']}",
                f"- Automation status: `{guide.get('automationStatus', '')}`",
                f"- Readiness: `{guide.get('readiness', '')}`",
                f"- Setup category: `{guide.get('setupCategory', '')}`",
                f"- Developer console: {guide.get('developerConsole') or 'manual/browser workflow'}",
                f"- Credential env names: {', '.join(guide.get('credentialEnvNames') or []) or 'none'}",
                f"- Missing env: {', '.join(guide.get('missingEnv') or []) or 'none'}",
                "",
                "### Official Docs",
            ]
        )
        docs = guide.get("officialDocs") or []
        if docs:
            for doc in docs:
                lines.append(f"- [{doc.get('label', doc.get('url', 'doc'))}]({doc.get('url', '')})")
        else:
            lines.append("- No verified official direct-publish API is integrated for this platform.")
        lines.extend(["", "### Required Capabilities"])
        lines.extend(f"- {item}" for item in guide.get("requiredCapabilities", []))
        lines.extend(["", "### Setup Steps"])
        lines.extend(f"- [ ] {item}" for item in guide.get("setupSteps", []))
        lines.extend(["", "### Verification Commands"])
        for name, command in (guide.get("verificationCommands") or {}).items():
            if command:
                lines.append(f"- {name}: `{command}`")
        lines.extend(["", "### Constraints"])
        lines.extend(f"- {item}" for item in guide.get("constraints", []) if item)
    return "\n".join(lines)


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def ordered_unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def flatten_groups(groups: Any) -> list[str]:
    result: list[str] = []
    if not isinstance(groups, list):
        return result
    for group in groups:
        if isinstance(group, list):
            result.extend(str(item) for item in group)
    return result


def append_input(command: list[str], flag: str, value: Any) -> None:
    text = "" if value is None else str(value).strip()
    if text:
        command.extend([flag, text])


def display_command(command: list[str]) -> str:
    return " ".join(quote_arg(item) for item in command)


def quote_arg(value: str) -> str:
    if not value or any(ch.isspace() for ch in value) or any(ch in value for ch in ['"', "'"]):
        return '"' + value.replace('"', '\\"') + '"'
    return value


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/publish-setup"


if __name__ == "__main__":
    main()
