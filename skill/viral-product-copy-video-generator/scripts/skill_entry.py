#!/usr/bin/env python3
"""Codex-facing one-link entry point for the promotion manager Skill."""

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
REAL_RUN_PLAYBOOK = SCRIPTS / "real_run_playbook.py"
FINAL_CAPABILITY_RUNNER = SCRIPTS / "final_capability_runner.py"
FINAL_CAPABILITY_READINESS = SCRIPTS / "final_capability_readiness.py"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    playbook = run_playbook(args, out_dir, steps)
    final_run = run_final_capability(args, out_dir, steps)
    readiness = run_readiness(args, out_dir, steps)
    report = build_report(args, out_dir, playbook, final_run, readiness, steps)
    write_report(out_dir, report)
    print(f"Skill entry report written to: {(report_dir(out_dir) / 'skill-entry.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Skill from one product or website link with safe high-automation defaults.")
    parser.add_argument("--link", action="append", default=[], help="Product URL or website URL. Can be repeated.")
    parser.add_argument("--links-file", default="", help="Text file with one product URL per line.")
    parser.add_argument("--link-mode", choices=["auto", "product", "site"], default="auto", help="auto passes links as products and uses the first link for product discovery.")
    parser.add_argument("--platforms", default=DEFAULT_PLATFORMS)
    parser.add_argument("--goal", default="leads", choices=["traffic", "leads", "sales", "seo", "brand", "github_stars"])
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--out-dir", default="./promotion-output")

    product = parser.add_argument_group("Product reading")
    product.add_argument("--skip-browser", action="store_true")
    product.add_argument("--install-browser-if-missing", action="store_true")
    product.add_argument("--timeout-ms", type=int, default=30000)
    product.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    product.add_argument("--discovery-html-file", default="", help="Saved public website HTML to discover product URLs from.")
    product.add_argument("--discovery-sitemap-url", default="", help="Public sitemap.xml or sitemap index URL to discover product URLs from.")
    product.add_argument("--discovery-sitemap-file", default="", help="Saved sitemap.xml, sitemap index, or .xml.gz file to discover product URLs from.")
    product.add_argument("--discovery-base-url", default="", help="Base URL for resolving links in --discovery-html-file.")
    product.add_argument("--discovery-top-n", type=int, default=50)
    product.add_argument("--discovery-min-score", type=float, default=3.0)
    product.add_argument("--discovery-max-pages", type=int, default=20)
    product.add_argument("--discovery-max-depth", type=int, default=1)
    product.add_argument("--discovery-max-sitemap-urls", type=int, default=1000)
    product.add_argument("--discovery-timeout", type=float, default=20.0)
    product.add_argument("--discovery-include-external", action="store_true")
    product.add_argument("--discovery-skip-sitemaps", action="store_true")
    product.add_argument("--discovery-allow-localhost", action="store_true")

    research = parser.add_argument_group("Viral research")
    research.add_argument("--skip-auto-search-competitors", action="store_true")
    research.add_argument("--live-official-competitors", action="store_true")
    research.add_argument("--skip-creator-follow-up", action="store_true")
    research.add_argument("--creator-follow-up-dry-run", action="store_true")
    research.add_argument("--skip-follow-up-captures", action="store_true")
    research.add_argument("--follow-up-dry-run", action="store_true")
    research.add_argument("--skip-browser-assisted-follow-ups", action="store_true")
    research.add_argument("--skip-video-sampling", action="store_true")
    research.add_argument("--video-sample-count", type=int, default=5)
    research.add_argument("--multi-query-dry-run", action="store_true")
    research.add_argument("--multi-query-query-count", type=int, default=5)

    content = parser.add_argument_group("Content and videos")
    content.add_argument("--skip-video", action="store_true")
    content.add_argument("--video-platforms", default="auto")
    content.add_argument("--generate-voiceover", action="store_true")

    publish = parser.add_argument_group("Publishing")
    publish.add_argument("--skip-publish-queue", action="store_true")
    publish.add_argument("--publish-platforms", default="")
    publish.add_argument("--execute-publish", action="store_true", help="Request approved official publishing through the final runner. Still requires credentials and exact approval.")
    publish.add_argument("--approval", default="", help=f"Must equal {APPROVAL_PHRASE} when --execute-publish is supplied.")
    publish.add_argument("--github-repo", default="")
    publish.add_argument("--github-action", default="file", choices=["file", "issue", "release"])
    publish.add_argument("--github-path", default="PROMOTION.md")
    publish.add_argument("--github-branch", default="")
    publish.add_argument("--github-tag-name", default="")
    publish.add_argument("--youtube-video-file", default="")
    publish.add_argument("--youtube-privacy-status", default="private", choices=["private", "public", "unlisted"])
    publish.add_argument("--youtube-category-id", default="22")
    publish.add_argument("--douyin-video-file", default="")
    publish.add_argument("--platform-publish-url", action="append", default=[], help="Override browser-assisted publisher entry as platform=url.")
    publish.add_argument("--run-browser-form-fill", action="store_true", help="Fill visible publisher fields and stop before final publish.")
    publish.add_argument("--browser-form-fill-headed", action="store_true")
    publish.add_argument("--browser-form-fill-allow-localhost", action="store_true")
    publish.add_argument("--browser-form-fill-install-browser-if-missing", action="store_true")
    publish.add_argument("--browser-form-fill-timeout-ms", type=int, default=30000)
    publish.add_argument("--browser-form-fill-wait-until", default="domcontentloaded", choices=["load", "domcontentloaded", "networkidle"])

    evidence = parser.add_argument_group("Real evidence recovery")
    evidence.add_argument("--published-url", action="append", default=[], help="Known real published URL as platform=url.")
    evidence.add_argument("--metrics-csv", action="append", default=[])
    evidence.add_argument("--metrics-xlsx", action="append", default=[])
    evidence.add_argument("--metrics-json", action="append", default=[])
    evidence.add_argument("--metrics-text", action="append", default=[])
    evidence.add_argument("--metrics-structured-json", action="append", default=[])
    evidence.add_argument("--business-csv", action="append", default=[])
    evidence.add_argument("--business-xlsx", action="append", default=[])
    evidence.add_argument("--business-json", action="append", default=[])
    evidence.add_argument("--business-text", action="append", default=[])
    evidence.add_argument("--post-publish-metrics-allow-localhost", action="store_true")
    evidence.add_argument("--post-publish-metrics-capture-browser-assisted", action="store_true")
    evidence.add_argument("--comment-evidence-limit", type=int, default=20)
    evidence.add_argument("--comment-evidence-platform", default="")
    evidence.add_argument("--comment-evidence-structured-json", default="")
    evidence.add_argument("--comment-evidence-html-file", default="")
    evidence.add_argument("--comment-evidence-text-file", default="")
    evidence.add_argument("--comment-evidence-allow-localhost", action="store_true")
    evidence.add_argument("--comment-evidence-capture-browser-assisted", action="store_true")
    evidence.add_argument("--comment-evidence-install-browser-if-missing", action="store_true")

    audits = parser.add_argument_group("Audits")
    audits.add_argument("--skip-platform-access-audit", action="store_true")
    audits.add_argument("--skip-final-capability-audit", action="store_true")
    audits.add_argument("--skip-self-evolution-audit", action="store_true")
    return parser.parse_args()


def run_playbook(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [sys.executable, str(REAL_RUN_PLAYBOOK)]
    append_link_args(command, args)
    append_discovery_args(command, args)
    command.extend(["--platforms", args.platforms, "--goal", args.goal, "--language", args.language])
    append_if_present(command, "--github-repo", args.github_repo)
    append_if_present(command, "--github-action", args.github_action)
    append_if_present(command, "--github-path", args.github_path)
    append_if_present(command, "--github-branch", args.github_branch)
    append_if_present(command, "--github-tag-name", args.github_tag_name)
    append_if_present(command, "--youtube-video-file", args.youtube_video_file)
    append_if_present(command, "--youtube-privacy-status", args.youtube_privacy_status)
    append_if_present(command, "--youtube-category-id", args.youtube_category_id)
    append_if_present(command, "--douyin-video-file", args.douyin_video_file)
    append_many(command, "--metrics-csv", args.metrics_csv)
    append_many(command, "--metrics-xlsx", args.metrics_xlsx)
    append_many(command, "--metrics-json", args.metrics_json)
    append_many(command, "--metrics-text", args.metrics_text)
    append_many(command, "--metrics-structured-json", args.metrics_structured_json)
    append_many(command, "--business-csv", args.business_csv)
    append_many(command, "--business-xlsx", args.business_xlsx)
    append_many(command, "--business-json", args.business_json)
    append_many(command, "--business-text", args.business_text)
    append_many(command, "--published-url", args.published_url)
    if args.generate_voiceover:
        command.append("--generate-voiceover")
    command.extend(["--out-dir", str(out_dir)])
    step = run_command("real_run_playbook", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/real-run-playbook/real-run-playbook.json"
    report = read_json(report_path)
    return {
        "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path) if report_path.exists() else "",
        "artifacts": report.get("artifacts", {}) if isinstance(report.get("artifacts"), dict) else {},
    }


def run_final_capability(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [sys.executable, str(FINAL_CAPABILITY_RUNNER)]
    append_link_args(command, args)
    append_discovery_args(command, args)
    command.extend(
        [
            "--platforms",
            args.platforms,
            "--goal",
            args.goal,
            "--language",
            args.language,
            "--timeout-ms",
            str(args.timeout_ms),
            "--wait-until",
            args.wait_until,
        ]
    )
    if args.skip_browser:
        command.append("--skip-browser")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    if not args.skip_auto_search_competitors:
        command.append("--auto-search-competitors")
    if args.live_official_competitors:
        command.append("--live-official-competitors")
    if not args.skip_creator_follow_up:
        command.append("--run-creator-follow-up")
        if args.creator_follow_up_dry_run:
            command.append("--creator-follow-up-dry-run")
    if not args.skip_follow_up_captures:
        command.append("--run-follow-up-captures")
        if args.follow_up_dry_run:
            command.append("--follow-up-dry-run")
    if not args.skip_browser_assisted_follow_ups:
        command.append("--capture-browser-assisted-follow-ups")
    if not args.skip_video_sampling:
        command.append("--sample-video-frames")
        command.extend(["--video-sample-count", str(args.video_sample_count)])
    if args.skip_video:
        command.append("--skip-video")
    append_if_present(command, "--video-platforms", args.video_platforms)
    if args.generate_voiceover:
        command.append("--generate-voiceover")

    command.extend(["--multi-query-query-count", str(args.multi_query_query_count)])
    if args.multi_query_dry_run:
        command.append("--multi-query-dry-run")
    if not args.skip_creator_follow_up:
        command.append("--multi-query-run-creator-follow-up")
    if not args.skip_follow_up_captures:
        command.append("--multi-query-run-follow-up-captures")
    if not args.skip_browser_assisted_follow_ups:
        command.append("--multi-query-capture-browser-assisted-follow-ups")
    if not args.skip_video_sampling:
        command.append("--multi-query-sample-video-frames")
        command.extend(["--multi-query-video-sample-count", str(args.video_sample_count)])

    if args.skip_publish_queue:
        command.append("--skip-publish-queue")
    append_if_present(command, "--publish-platforms", args.publish_platforms)
    if args.execute_publish:
        command.append("--execute-publish")
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
    append_many(command, "--platform-publish-url", args.platform_publish_url)
    if args.run_browser_form_fill:
        command.append("--run-browser-form-fill")
        if args.browser_form_fill_headed:
            command.append("--browser-form-fill-headed")
        if args.browser_form_fill_allow_localhost:
            command.append("--browser-form-fill-allow-localhost")
        if args.browser_form_fill_install_browser_if_missing:
            command.append("--browser-form-fill-install-browser-if-missing")
        command.extend(["--browser-form-fill-timeout-ms", str(args.browser_form_fill_timeout_ms)])
        command.extend(["--browser-form-fill-wait-until", args.browser_form_fill_wait_until])

    append_many(command, "--published-url", args.published_url)
    append_many(command, "--metrics-csv", args.metrics_csv)
    append_many(command, "--metrics-xlsx", args.metrics_xlsx)
    append_many(command, "--metrics-json", args.metrics_json)
    append_many(command, "--metrics-text", args.metrics_text)
    append_many(command, "--metrics-structured-json", args.metrics_structured_json)
    append_many(command, "--business-csv", args.business_csv)
    append_many(command, "--business-xlsx", args.business_xlsx)
    append_many(command, "--business-json", args.business_json)
    append_many(command, "--business-text", args.business_text)
    if args.post_publish_metrics_allow_localhost:
        command.append("--post-publish-metrics-allow-localhost")
    if args.post_publish_metrics_capture_browser_assisted:
        command.append("--post-publish-metrics-capture-browser-assisted")
    command.extend(["--comment-evidence-limit", str(args.comment_evidence_limit)])
    append_if_present(command, "--comment-evidence-platform", args.comment_evidence_platform)
    append_if_present(command, "--comment-evidence-structured-json", args.comment_evidence_structured_json)
    append_if_present(command, "--comment-evidence-html-file", args.comment_evidence_html_file)
    append_if_present(command, "--comment-evidence-text-file", args.comment_evidence_text_file)
    if args.comment_evidence_allow_localhost:
        command.append("--comment-evidence-allow-localhost")
    if args.comment_evidence_capture_browser_assisted:
        command.append("--comment-evidence-capture-browser-assisted")
    if args.comment_evidence_install_browser_if_missing:
        command.append("--comment-evidence-install-browser-if-missing")

    if args.skip_platform_access_audit:
        command.append("--skip-platform-access-audit")
    if args.skip_final_capability_audit:
        command.append("--skip-final-capability-audit")
    if args.skip_self_evolution_audit:
        command.append("--skip-self-evolution-audit")
    command.extend(["--out-dir", str(out_dir)])

    step = run_command("final_capability_runner", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/final-run/final-capability-run.json"
    report = read_json(report_path)
    return {
        "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path) if report_path.exists() else "",
        "summary": report.get("summary", {}) if isinstance(report.get("summary"), dict) else {},
    }


def run_readiness(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [sys.executable, str(FINAL_CAPABILITY_READINESS), "--out-dir", str(out_dir)]
    step = run_command("final_capability_readiness", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json"
    report = read_json(report_path)
    return {
        "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path) if report_path.exists() else "",
        "requirements": report.get("requirements", []) if isinstance(report.get("requirements"), list) else [],
        "actionQueue": report.get("actionQueue", []) if isinstance(report.get("actionQueue"), list) else [],
    }


def append_link_args(command: list[str], args: argparse.Namespace) -> None:
    if args.link_mode in {"auto", "product"}:
        append_many(command, "--url", args.link)
        append_if_present(command, "--urls-file", args.links_file)
    if args.link_mode in {"auto", "site"} and args.link:
        command.extend(["--discover-from-url", args.link[0]])


def append_discovery_args(command: list[str], args: argparse.Namespace) -> None:
    append_if_present(command, "--discovery-html-file", args.discovery_html_file)
    append_if_present(command, "--discovery-sitemap-url", args.discovery_sitemap_url)
    append_if_present(command, "--discovery-sitemap-file", args.discovery_sitemap_file)
    append_if_present(command, "--discovery-base-url", args.discovery_base_url)
    command.extend(
        [
            "--discovery-top-n",
            str(args.discovery_top_n),
            "--discovery-min-score",
            str(args.discovery_min_score),
            "--discovery-max-pages",
            str(args.discovery_max_pages),
            "--discovery-max-depth",
            str(args.discovery_max_depth),
            "--discovery-max-sitemap-urls",
            str(args.discovery_max_sitemap_urls),
            "--discovery-timeout",
            str(args.discovery_timeout),
        ]
    )
    if args.discovery_include_external:
        command.append("--discovery-include-external")
    if args.discovery_skip_sitemaps:
        command.append("--discovery-skip-sitemaps")
    if args.discovery_allow_localhost:
        command.append("--discovery-allow-localhost")


def discovery_input(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "htmlFile": args.discovery_html_file,
        "sitemapUrl": args.discovery_sitemap_url,
        "sitemapFile": args.discovery_sitemap_file,
        "baseUrl": args.discovery_base_url,
        "topN": args.discovery_top_n,
        "minScore": args.discovery_min_score,
        "maxPages": args.discovery_max_pages,
        "maxDepth": args.discovery_max_depth,
        "maxSitemapUrls": args.discovery_max_sitemap_urls,
        "timeout": args.discovery_timeout,
        "includeExternal": bool(args.discovery_include_external),
        "skipSitemaps": bool(args.discovery_skip_sitemaps),
        "allowLocalhost": bool(args.discovery_allow_localhost),
    }


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    playbook: dict[str, Any],
    final_run: dict[str, Any],
    readiness: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "status": entry_status(playbook, final_run, readiness),
        "outDir": str(out_dir),
        "input": {
            "links": args.link,
            "linksFile": args.links_file,
            "linkMode": args.link_mode,
            "discovery": discovery_input(args),
            "platforms": args.platforms,
            "goal": args.goal,
            "language": args.language,
            "codexReadFirst": True,
            "publishExecutionRequested": bool(args.execute_publish),
            "publishApprovalProvided": args.approval == APPROVAL_PHRASE,
        },
        "summary": {
            "playbookStatus": playbook.get("status", ""),
            "finalRunStatus": final_run.get("status", ""),
            "readinessStatus": readiness.get("status", ""),
            "publishExecutionRequested": bool(args.execute_publish),
            "publishApprovalProvided": args.approval == APPROVAL_PHRASE,
            "promotionRuns": int_value((final_run.get("summary") or {}).get("promotionRuns")),
            "contentArtifacts": int_value((final_run.get("summary") or {}).get("contentArtifacts")),
            "videoFilesGenerated": int_value((final_run.get("summary") or {}).get("videoFilesGenerated")),
            "publishQueues": int_value((final_run.get("summary") or {}).get("publishQueues")),
            "launchUnlockPackRuns": int_value((final_run.get("summary") or {}).get("launchUnlockPackRuns")),
            "capturedMetricRecords": int_value((final_run.get("summary") or {}).get("capturedMetricRecords")),
            "commentCount": int_value((final_run.get("summary") or {}).get("commentCount")),
            "matchedBusinessRows": int_value((final_run.get("summary") or {}).get("matchedBusinessRows")),
        },
        "playbook": playbook,
        "finalRun": final_run,
        "readiness": readiness,
        "guardrails": [
            "One link can be treated as both a product candidate and a website discovery seed in auto mode.",
            "Product pages are read before generation, with browser-visible structured snapshots when available.",
            "Search, follow-up capture, video sampling, publish payloads, and metrics recovery use public, official, or user-provided evidence.",
            "Official publishing still requires credentials, account authorization, reviewed dry-runs, and I_APPROVE_PUBLISH.",
            "Browser-assisted publishing must stop for login, captcha, account verification, risk checks, and final publish.",
            "Metrics, comments, orders, and revenue must come from real URLs, public pages, official APIs, screenshots, structured snapshots, or business exports.",
        ],
        "steps": steps,
    }


def entry_status(playbook: dict[str, Any], final_run: dict[str, Any], readiness: dict[str, Any]) -> str:
    if playbook.get("status") == "error" or final_run.get("status") in {"", "error", "blocked"}:
        return "blocked"
    if readiness.get("status") == "partial_ready_blocked_by_platform_or_safety_limits":
        return "partial_ready_blocked_by_platform_or_safety_limits"
    return str(readiness.get("status") or final_run.get("status") or "partial_ready")


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "skill-entry.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "skill-entry.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Skill Entry Run",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Output: {report['outDir']}",
        f"- Links: {', '.join(report['input'].get('links') or [])}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Reports",
            f"- Real run playbook: {report['playbook'].get('report', '')}",
            f"- Final capability run: {report['finalRun'].get('report', '')}",
            f"- Final readiness: {report['readiness'].get('report', '')}",
            "",
            "## Guardrails",
        ]
    )
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    step = {
        "name": name,
        "command": display_command(command),
        "exitCode": result.returncode,
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }
    if result.returncode != 0:
        raise SystemExit(f"{name} failed: {step['stderrTail'] or step['stdoutTail']}")
    return step


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/skill-entry"


def append_if_present(command: list[str], flag: str, value: Any) -> None:
    text = "" if value is None else str(value).strip()
    if text:
        command.extend([flag, text])


def append_many(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        append_if_present(command, flag, value)


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
