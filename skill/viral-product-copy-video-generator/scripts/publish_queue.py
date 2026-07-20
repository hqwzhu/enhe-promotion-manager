#!/usr/bin/env python3
"""Build and optionally execute a guarded publish queue from workflow outputs."""

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
PUBLISHED_ITEMS = SCRIPTS / "published_items.py"
TODAY = date.today().isoformat()
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
OFFICIAL_PLATFORMS = {"github", "youtube"}
MANUAL_MODES = {"manual_publish_required", "browser_assisted_publish"}


def main() -> None:
    args = parse_args()
    promotion_dir = Path(args.promotion_out_dir)
    manifest_path = workflow_manifest_path(args, promotion_dir)
    manifest = read_json(manifest_path) if manifest_path and manifest_path.exists() else {}
    publish_pack_path = resolve_artifact_path(args.publish_pack, manifest, "publishPack", promotion_dir)
    content_path = resolve_artifact_path(args.content_json, manifest, "contentJson", promotion_dir)

    if not publish_pack_path.exists():
        raise SystemExit(f"Publish pack not found: {publish_pack_path}")
    if not content_path.exists():
        raise SystemExit(f"Generated content JSON not found: {content_path}")

    publish_pack = read_json(publish_pack_path)
    content = read_json(content_path)
    selected_platforms = split_csv(args.platforms)
    out_dir = Path(args.out_dir)
    queue = build_queue(args, out_dir, promotion_dir, manifest, publish_pack, content, selected_platforms)
    write_queue(out_dir, queue)
    write_published_items(out_dir)
    print(f"Publish queue written to: {(queue_dir(out_dir) / 'publish-queue.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a guarded publish queue from generated promotion outputs.")
    parser.add_argument("--workflow-manifest", default="", help="Path to workflow-manifest.json. Defaults to <promotion-out-dir>/reports/promotion-manager/agent-run/workflow-manifest.json.")
    parser.add_argument("--promotion-out-dir", default="./promotion-output", help="Output directory produced by run_promotion_workflow.py.")
    parser.add_argument("--publish-pack", default="", help="Override path to <product>-publish-pack.json.")
    parser.add_argument("--content-json", default="", help="Override path to <product>-platform-content.json.")
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter. Defaults to all platforms in the publish pack.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--execute", action="store_true", help="Pass --execute to official publish executor. Default is dry run.")
    parser.add_argument("--approval", default="", help=f"Must equal {APPROVAL_PHRASE} when --execute is used.")

    github = parser.add_argument_group("GitHub")
    github.add_argument("--github-repo", default="", help="owner/repo target for GitHub official publishing.")
    github.add_argument("--github-action", default="file", choices=["file", "issue", "release"])
    github.add_argument("--github-path", default="PROMOTION.md", help="Repository path for GitHub file publishing.")
    github.add_argument("--github-branch", default="")
    github.add_argument("--github-tag-name", default="")

    youtube = parser.add_argument_group("YouTube")
    youtube.add_argument("--youtube-video-file", default="", help="MP4 to upload. Defaults to the workflow manifest YouTube video when available.")
    youtube.add_argument("--youtube-privacy-status", default="private", choices=["private", "public", "unlisted"])
    youtube.add_argument("--youtube-category-id", default="22")

    douyin = parser.add_argument_group("Douyin")
    douyin.add_argument(
        "--douyin-video-file",
        default="",
        help="MP4 asset for Douyin browser-assisted publishing. This does not enable official API publishing.",
    )
    return parser.parse_args()


def workflow_manifest_path(args: argparse.Namespace, promotion_dir: Path) -> Path | None:
    if args.workflow_manifest:
        return Path(args.workflow_manifest)
    candidate = promotion_dir / "reports/promotion-manager/agent-run/workflow-manifest.json"
    return candidate if candidate.exists() else None


def resolve_artifact_path(override: str, manifest: dict[str, Any], key: str, promotion_dir: Path) -> Path:
    if override:
        return Path(override)
    value = (manifest.get("artifacts") or {}).get(key, "")
    if value:
        path = Path(value)
        if path.is_absolute() or path.exists():
            return path
        if (promotion_dir / path).exists():
            return promotion_dir / path
        return path
    if key == "publishPack":
        matches = sorted((promotion_dir / "reports/promotion-manager/publish-packs").glob("*-publish-pack.json"))
        if matches:
            return matches[0]
    if key == "contentJson":
        matches = sorted((promotion_dir / "reports/promotion-manager/generated-content").glob("*-platform-content.json"))
        if matches:
            return matches[0]
    return promotion_dir / "__missing__"


def build_queue(
    args: argparse.Namespace,
    out_dir: Path,
    promotion_dir: Path,
    manifest: dict[str, Any],
    publish_pack: list[dict[str, Any]],
    content: dict[str, Any],
    selected_platforms: list[str],
) -> dict[str, Any]:
    records = []
    for pack in publish_pack:
        platform = str(pack.get("platform") or "").strip()
        if not platform or (selected_platforms and platform not in selected_platforms):
            continue
        platform_content = pack.get("content") or content.get(platform) or {}
        mode = effective_publish_mode(platform, pack)
        effective_pack = with_douyin_video_payload(pack, args.douyin_video_file) if platform == "douyin" else dict(pack)
        effective_pack["publishMode"] = mode
        draft_path = write_platform_draft(out_dir, platform, platform_content, effective_pack)
        record: dict[str, Any] = {
            "id": f"{TODAY}-{platform}",
            "platform": platform,
            "publishMode": mode,
            "approvalRequired": bool(effective_pack.get("approvalRequired", True)),
            "viralTitle": effective_pack.get("viralTitle") or content_title(platform_content),
            "copy": effective_pack.get("copy", ""),
            "tags": effective_pack.get("tags") or platform_content.get("tags", []),
            "firstBatch": effective_pack.get("firstBatch", {}),
            "video": effective_pack.get("video", {}),
            "cover": effective_pack.get("cover", {}),
            "detailImages": effective_pack.get("detailImages", []),
            "assets": effective_pack.get("assets", []),
            "contentDraft": str(draft_path),
            "scheduleSuggestion": effective_pack.get("scheduleSuggestion", ""),
            "trackingFields": effective_pack.get("trackingFields", []),
            "trackingPlan": effective_pack.get("trackingPlan", {}),
            "warnings": effective_pack.get("warnings", []),
        }
        if platform in OFFICIAL_PLATFORMS and mode == "official_api_publish":
            record.update(run_official_queue_item(args, out_dir, promotion_dir, manifest, platform, platform_content, draft_path, effective_pack))
        elif mode in MANUAL_MODES:
            record.update(manual_queue_item(mode, platform))
        else:
            record.update({"status": "unsupported", "reason": f"Unsupported publish mode: {mode}"})
        records.append(record)

    return {
        "generatedAt": TODAY,
        "mode": "execute" if args.execute else "dry_run",
        "approvalRequired": True,
        "approvalPhrase": APPROVAL_PHRASE,
        "approvalProvided": args.approval == APPROVAL_PHRASE,
        "records": records,
        "summary": summarize(records),
        "guardrails": [
            "Official API writes require --execute and the exact approval phrase.",
            "Credentials are read from environment variables by publish_executor.py and are never written to queue reports.",
            "Zhihu, Xiaohongshu, Douyin, and unverified platforms remain browser-assisted or manual by default.",
            "Douyin official API publishing is reserved for a future verified open-platform authorization path; current queues only attach MP4 assets for browser-assisted publishing.",
            "Do not bypass login, captcha, risk control, platform review, or account verification.",
            "Record published URLs and metrics only after real evidence exists.",
        ],
    }


def effective_publish_mode(platform: str, pack: dict[str, Any]) -> str:
    if platform == "douyin":
        return "browser_assisted_publish"
    return str(pack.get("publishMode") or "manual_publish_required")


def with_douyin_video_payload(pack: dict[str, Any], video_file: str) -> dict[str, Any]:
    effective = dict(pack)
    path_text = str(video_file or "").strip()
    if not path_text:
        return effective
    status = "ready" if Path(path_text).exists() else "missing"
    video = dict(effective.get("video") or {})
    video.update(
        {
            "required": True,
            "status": status,
            "path": path_text,
            "source": "douyin_video_file_arg",
        }
    )
    effective["video"] = video
    assets = [item for item in (effective.get("assets") or []) if isinstance(item, dict)]
    if not any(str(item.get("path") or "") == path_text for item in assets):
        assets.append(
            {
                "type": "video",
                "platform": "douyin",
                "status": status,
                "path": path_text,
                "source": "douyin_video_file_arg",
            }
        )
    effective["assets"] = assets
    warnings = [str(item) for item in (effective.get("warnings") or []) if str(item).strip()]
    warning = (
        "Douyin is configured for browser-assisted publishing; --douyin-video-file attaches an MP4 asset "
        "but does not enable official API publishing."
    )
    if warning not in warnings:
        warnings.append(warning)
    effective["warnings"] = warnings
    return effective


def run_official_queue_item(
    args: argparse.Namespace,
    out_dir: Path,
    promotion_dir: Path,
    manifest: dict[str, Any],
    platform: str,
    content: dict[str, Any],
    draft_path: Path,
    pack: dict[str, Any],
) -> dict[str, Any]:
    if platform == "github":
        return run_github_queue_item(args, out_dir, content, draft_path)
    if platform == "youtube":
        return run_youtube_queue_item(args, out_dir, promotion_dir, manifest, content, draft_path, pack)
    if platform == "douyin":
        return run_douyin_queue_item(args, out_dir, content)
    return {"status": "unsupported", "reason": f"No official queue runner for {platform}."}


def run_github_queue_item(args: argparse.Namespace, out_dir: Path, content: dict[str, Any], draft_path: Path) -> dict[str, Any]:
    if not args.github_repo:
        return {
            "status": "blocked",
            "reason": "Provide --github-repo owner/repo to prepare the official GitHub publish executor.",
            "executionReport": "",
        }
    command = [
        sys.executable,
        str(SCRIPTS / "publish_executor.py"),
        "--platform",
        "github",
        "--github-action",
        args.github_action,
        "--github-repo",
        args.github_repo,
        "--out-dir",
        str(execution_out_dir(out_dir, "github")),
    ]
    if args.execute:
        command.extend(["--execute", "--approval", args.approval])
    if args.github_action == "file":
        command.extend(["--path", args.github_path, "--content-file", str(draft_path), "--commit-message", github_commit_message(content)])
        if args.github_branch:
            command.extend(["--branch", args.github_branch])
    elif args.github_action == "issue":
        command.extend(["--title", content_title(content), "--body-file", str(draft_path)])
    else:
        command.extend(["--title", content_title(content), "--body-file", str(draft_path), "--tag-name", args.github_tag_name or TODAY])
    return execute_publish_command("github", command)


def run_youtube_queue_item(
    args: argparse.Namespace,
    out_dir: Path,
    promotion_dir: Path,
    manifest: dict[str, Any],
    content: dict[str, Any],
    draft_path: Path,
    pack: dict[str, Any],
) -> dict[str, Any]:
    video_file = Path(args.youtube_video_file) if args.youtube_video_file else video_from_pack(pack) or youtube_video_from_manifest(manifest, promotion_dir)
    if not video_file or not video_file.exists():
        return {
            "status": "blocked",
            "reason": "Provide --youtube-video-file or render a YouTube MP4 in the workflow before queue execution.",
            "executionReport": "",
        }
    command = [
        sys.executable,
        str(SCRIPTS / "publish_executor.py"),
        "--platform",
        "youtube",
        "--video-file",
        str(video_file),
        "--title",
        content_title(content),
        "--description-file",
        str(draft_path),
        "--tags",
        ",".join(str(tag) for tag in content.get("tags", []) if str(tag).strip()),
        "--category-id",
        args.youtube_category_id,
        "--privacy-status",
        args.youtube_privacy_status,
        "--out-dir",
        str(execution_out_dir(out_dir, "youtube")),
    ]
    if args.execute:
        command.extend(["--execute", "--approval", args.approval])
    return execute_publish_command("youtube", command)


def run_douyin_queue_item(args: argparse.Namespace, out_dir: Path, content: dict[str, Any]) -> dict[str, Any]:
    video_file = Path(args.douyin_video_file)
    if not video_file.exists():
        return {
            "status": "blocked",
            "reason": "Provide --douyin-video-file or render a Douyin MP4 before queue execution.",
            "executionReport": "",
        }
    command = [
        sys.executable,
        str(SCRIPTS / "publish_executor.py"),
        "--platform",
        "douyin",
        "--douyin-video-file",
        str(video_file),
        "--title",
        content_title(content),
        "--out-dir",
        str(execution_out_dir(out_dir, "douyin")),
    ]
    if args.execute:
        command.extend(["--execute", "--approval", args.approval])
    return execute_publish_command("douyin", command)


def execute_publish_command(platform: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    report_path = execution_out_dir_from_command(command) / "reports/promotion-manager/publish-results/publish-execution.json"
    execution_report = read_json(report_path) if report_path.exists() else {}
    status = str(execution_report.get("status") or ("ready" if result.returncode == 0 else "error"))
    return {
        "status": status,
        "officialExecution": {
            "command": display_command(command),
            "exitCode": result.returncode,
            "stdoutTail": tail(result.stdout),
            "stderrTail": tail(result.stderr),
            "report": str(report_path) if report_path.exists() else "",
            "publishedUrl": execution_report.get("publishedUrl", ""),
            "reason": execution_report.get("reason", ""),
        },
    }


def execution_out_dir_from_command(command: list[str]) -> Path:
    try:
        index = command.index("--out-dir")
    except ValueError:
        return Path("./promotion-output")
    return Path(command[index + 1])


def manual_queue_item(mode: str, platform: str) -> dict[str, Any]:
    if mode == "browser_assisted_publish":
        return {
            "status": "queued_browser_assisted",
            "reason": "Open the platform publisher with user-visible browser assistance, then let the user complete final publish.",
            "manualStepsRequired": True,
        }
    return {
        "status": "queued_manual",
        "reason": f"{platform} requires manual copy/paste or verified official access before automation.",
        "manualStepsRequired": True,
    }


def write_platform_draft(out_dir: Path, platform: str, content: dict[str, Any], pack: dict[str, Any]) -> Path:
    draft_dir = queue_dir(out_dir) / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    path = draft_dir / f"{platform}-draft.md"
    path.write_text(render_platform_draft(platform, content, pack) + "\n", encoding="utf-8")
    return path


def render_platform_draft(platform: str, content: dict[str, Any], pack: dict[str, Any]) -> str:
    lines = [
        f"# {platform} Publish Draft",
        "",
        f"- Viral title: {pack.get('viralTitle') or content_title(content)}",
        f"- Title: {content_title(content)}",
        f"- Content type: {content.get('contentType', '')}",
        f"- CTA: {content.get('cta', '')}",
        f"- Cover text: {content.get('coverText', '')}",
        f"- Tags: {', '.join(str(tag) for tag in (pack.get('tags') or content.get('tags', [])))}",
        f"- Publish mode: `{pack.get('publishMode', '')}`",
        f"- Approval required: {pack.get('approvalRequired', True)}",
        "",
        "## Required Publish Package",
        "",
        f"- Video: `{(pack.get('video') or {}).get('status', '')}` {(pack.get('video') or {}).get('path', '')}",
        f"- Cover: `{(pack.get('cover') or {}).get('status', '')}` {(pack.get('cover') or {}).get('path', '')}",
        f"- Detail images: {len(pack.get('detailImages', []))}",
        "",
        "## Media Assets",
        "",
        render_media_assets(pack),
        "",
        "## First Batch",
        "",
        render_first_batch(pack.get("firstBatch", {})),
        "",
        "## Tracking Plan",
        "",
        render_tracking_plan(pack.get("trackingPlan", {})),
        "",
        "## Description",
        "",
        str(content.get("description") or ""),
    ]
    for key in ["article", "shortVideoScript", "voiceover"]:
        if content.get(key):
            lines.extend(["", f"## {key}", "", str(content[key])])
    if content.get("storyboard"):
        lines.extend(["", "## Storyboard"])
        for item in content["storyboard"]:
            lines.append(f"- {item.get('time', '')}: {item.get('visual', '')} / {item.get('voiceover', '')}")
    if content.get("formats"):
        lines.extend(["", "## Formats", "", "```json", json.dumps(content["formats"], ensure_ascii=False, indent=2), "```"])
    lines.extend(["", "## Publish Steps"])
    lines.extend(f"- {step}" for step in pack.get("publishSteps", []))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in pack.get("warnings", []))
    return "\n".join(lines)


def render_media_assets(pack: dict[str, Any]) -> str:
    assets = pack.get("assets") if isinstance(pack.get("assets"), list) else []
    if not assets:
        return "- Media assets: pending media_asset_pack.py"
    lines = []
    for asset in assets:
        if isinstance(asset, dict):
            label = asset.get("type") or "asset"
            status = asset.get("status") or ""
            path = asset.get("path") or ""
            lines.append(f"- {label}: `{status}` {path}")
    return "\n".join(lines) if lines else "- Media assets: pending media_asset_pack.py"


def render_first_batch(first_batch: Any) -> str:
    if not isinstance(first_batch, dict) or not first_batch:
        return "- First batch: pending"
    lines = []
    if first_batch.get("pinnedComment"):
        lines.append(f"- Pinned comment: {first_batch['pinnedComment']}")
    for key, label in [
        ("firstComments", "First comments"),
        ("replyPrompts", "Reply prompts"),
        ("launchActions", "Launch actions"),
    ]:
        values = first_batch.get(key)
        if isinstance(values, list) and values:
            lines.append(f"- {label}:")
            lines.extend(f"  - {value}" for value in values)
    return "\n".join(lines) if lines else "- First batch: pending"


def render_tracking_plan(tracking: Any) -> str:
    if not isinstance(tracking, dict) or not tracking:
        return "- Tracking plan: not generated"
    utm = tracking.get("utm") if isinstance(tracking.get("utm"), dict) else {}
    lines = [
        f"- Campaign ID: {tracking.get('campaignId', '')}",
        f"- Content ID: {tracking.get('contentId', '')}",
        f"- Tracked URL: {tracking.get('trackedUrl', '')}",
    ]
    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_content"]:
        lines.append(f"- {key}: {utm.get(key, '')}")
    lines.append("- Business export match keys: " + ", ".join(str(item) for item in tracking.get("businessExportMatchKeys", [])))
    return "\n".join(lines)


def youtube_video_from_manifest(manifest: dict[str, Any], promotion_dir: Path) -> Path | None:
    for item in manifest.get("videoGeneration", []):
        if item.get("platform") == "youtube" and item.get("video"):
            path = Path(str(item["video"]))
            if path.is_absolute() or path.exists():
                return path
            return promotion_dir / path
    return None


def video_from_pack(pack: dict[str, Any]) -> Path | None:
    video = pack.get("video") if isinstance(pack.get("video"), dict) else {}
    path_value = str(video.get("path") or "").strip()
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.exists() else None


def write_queue(out_dir: Path, queue: dict[str, Any]) -> None:
    directory = queue_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "publish-queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "publish-queue.md").write_text(render_queue_markdown(queue) + "\n", encoding="utf-8")


def write_published_items(out_dir: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PUBLISHED_ITEMS),
            "--publish-queue",
            str(queue_dir(out_dir) / "publish-queue.json"),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"published_items failed: {tail(result.stderr) or tail(result.stdout)}")


def render_queue_markdown(queue: dict[str, Any]) -> str:
    lines = [
        "# Publish Queue",
        "",
        f"- Generated: {queue['generatedAt']}",
        f"- Mode: `{queue['mode']}`",
        f"- Approval provided: {queue['approvalProvided']}",
        "",
        "## Summary",
    ]
    for key, value in queue["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Records"])
    for record in queue["records"]:
        lines.extend(
            [
                "",
                f"### {record['platform']}",
                f"- Status: `{record['status']}`",
                f"- Mode: `{record['publishMode']}`",
                f"- Draft: {record['contentDraft']}",
                f"- Reason: {record.get('reason', '')}",
                f"- Viral title: {record.get('viralTitle', '')}",
                f"- Video: `{(record.get('video') or {}).get('status', '')}` {(record.get('video') or {}).get('path', '')}",
                f"- Cover: `{(record.get('cover') or {}).get('status', '')}` {(record.get('cover') or {}).get('path', '')}",
                f"- Detail images: {len(record.get('detailImages', []))}",
            ]
        )
        official = record.get("officialExecution") or {}
        if official:
            lines.extend(
                [
                    f"- Execution report: {official.get('report', '')}",
                    f"- Published URL: {official.get('publishedUrl', '') or 'not published'}",
                ]
            )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in queue["guardrails"])
    return "\n".join(lines)


def summarize(records: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "total": len(records),
        "officialDryRuns": 0,
        "published": 0,
        "blocked": 0,
        "manualQueued": 0,
        "browserQueued": 0,
        "errors": 0,
    }
    for record in records:
        status = str(record.get("status", ""))
        if status == "dry_run":
            summary["officialDryRuns"] += 1
        elif status == "published":
            summary["published"] += 1
        elif status == "blocked":
            summary["blocked"] += 1
        elif status == "queued_manual":
            summary["manualQueued"] += 1
        elif status == "queued_browser_assisted":
            summary["browserQueued"] += 1
        elif status == "error":
            summary["errors"] += 1
    return summary


def execution_out_dir(out_dir: Path, platform: str) -> Path:
    return queue_dir(out_dir) / "official-executions" / platform


def queue_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/publish-queue"


def github_commit_message(content: dict[str, Any]) -> str:
    return f"Publish promotion content for {content_title(content)}"


def content_title(content: dict[str, Any]) -> str:
    return str(content.get("title") or content.get("description") or "Promotion draft").strip()[:100]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def display_command(command: list[str]) -> list[str]:
    displayed = []
    for item in command:
        displayed.append("python" if item == sys.executable else item)
    return displayed


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
