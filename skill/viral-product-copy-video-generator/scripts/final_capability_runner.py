#!/usr/bin/env python3
"""One command runner for the highest-automation promotion manager flow."""

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
PRODUCT_BATCH_RUNNER = SCRIPTS / "product_batch_runner.py"
PUBLISH_READINESS = SCRIPTS / "publish_readiness_runner.py"
PUBLISH_SETUP_ASSISTANT = SCRIPTS / "publish_setup_assistant.py"
REAL_EVIDENCE_SETUP = SCRIPTS / "real_evidence_setup.py"
LAUNCH_UNLOCK_PACK = SCRIPTS / "launch_unlock_pack.py"
BROWSER_PUBLISH_ASSISTANT = SCRIPTS / "browser_publish_assistant.py"
BROWSER_PUBLISH_FORM_FILL = SCRIPTS / "browser_publish_form_fill.py"
PLATFORM_ACCESS_AUDIT = SCRIPTS / "platform_access_audit.py"
FINAL_CAPABILITY_AUDIT = SCRIPTS / "final_capability_audit.py"
FINAL_CAPABILITY_READINESS = SCRIPTS / "final_capability_readiness.py"
SELF_EVOLUTION_AUDIT = SCRIPTS / "self_evolution_audit.py"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    batch = run_product_batch(args, out_dir, steps)
    publish_readiness = run_publish_readiness(args, batch, steps)
    publish_setup = run_publish_setup_assistant(args, publish_readiness, steps)
    real_evidence_setup = run_real_evidence_setup(args, batch, publish_readiness, steps)
    browser_publish = run_browser_publish_assistant(args, batch, steps)
    browser_form_fill = run_browser_form_fill(args, browser_publish, steps)
    launch_unlock = run_launch_unlock_pack(args, batch, publish_readiness, steps)
    audits = run_audits(args, out_dir, steps)
    cycle_evidence = collect_cycle_evidence(batch)
    report = build_report(
        args,
        out_dir,
        batch,
        publish_readiness,
        publish_setup,
        real_evidence_setup,
        browser_publish,
        browser_form_fill,
        launch_unlock,
        cycle_evidence,
        audits,
        steps,
    )
    write_report(out_dir, report)
    readiness_matrix = run_final_readiness_matrix(args, out_dir, steps)
    report["finalReadinessMatrix"] = readiness_matrix
    report["summary"]["finalReadinessStatus"] = readiness_matrix.get("status", "")
    write_report(out_dir, report)
    print(f"Final capability run written to: {(report_dir(out_dir) / 'final-capability-run.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full safe promotion manager flow from product URL to next-round optimization.")
    parser.add_argument("--url", action="append", default=[], help="Product URL. Can be repeated.")
    parser.add_argument("--urls-file", default="", help="Text file with one product URL per line.")
    parser.add_argument("--out-dir", default="./promotion-output")

    product_discovery = parser.add_argument_group("Product URL discovery")
    product_discovery.add_argument("--discover-from-url", default="", help="Public website or landing page URL to discover product URLs from before reading products.")
    product_discovery.add_argument("--discovery-html-file", default="", help="Saved public website HTML to discover product URLs from.")
    product_discovery.add_argument("--discovery-sitemap-url", default="", help="Public sitemap.xml or sitemap index URL to discover product URLs from.")
    product_discovery.add_argument("--discovery-sitemap-file", default="", help="Saved sitemap.xml, sitemap index, or .xml.gz file to discover product URLs from.")
    product_discovery.add_argument("--discovery-base-url", default="", help="Base URL for resolving links in --discovery-html-file.")
    product_discovery.add_argument("--discovery-top-n", type=int, default=50)
    product_discovery.add_argument("--discovery-min-score", type=float, default=3.0)
    product_discovery.add_argument("--discovery-max-pages", type=int, default=20)
    product_discovery.add_argument("--discovery-max-depth", type=int, default=1)
    product_discovery.add_argument("--discovery-max-sitemap-urls", type=int, default=1000)
    product_discovery.add_argument("--discovery-timeout", type=float, default=20.0)
    product_discovery.add_argument("--discovery-include-external", action="store_true")
    product_discovery.add_argument("--discovery-skip-sitemaps", action="store_true")
    product_discovery.add_argument("--discovery-allow-localhost", action="store_true")

    product = parser.add_argument_group("Product reading")
    product.add_argument("--skip-browser", action="store_true")
    product.add_argument("--no-static-fallback", action="store_true")
    product.add_argument("--install-browser-if-missing", action="store_true")
    product.add_argument("--timeout-ms", type=int, default=30000)
    product.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])

    workflow = parser.add_argument_group("Promotion workflow")
    workflow.add_argument("--platforms", default=DEFAULT_PLATFORMS)
    workflow.add_argument("--goal", default="leads", choices=["traffic", "leads", "sales", "seo", "brand", "github_stars"])
    workflow.add_argument("--language", default="zh-CN")
    workflow.add_argument("--top-n", type=int, default=10)
    workflow.add_argument("--competitor-query", default="")
    workflow.add_argument("--auto-search-competitors", action="store_true")
    workflow.add_argument("--live-official-competitors", action="store_true")
    workflow.add_argument("--run-creator-follow-up", action="store_true")
    workflow.add_argument("--creator-follow-up-dry-run", action="store_true")
    workflow.add_argument("--run-follow-up-captures", action="store_true")
    workflow.add_argument("--follow-up-dry-run", action="store_true")
    workflow.add_argument("--capture-browser-assisted-follow-ups", action="store_true", help="Attempt browser-visible snapshots for queued browser-assisted platform follow-up tasks in product cycles.")
    workflow.add_argument("--sample-video-frames", action="store_true", help="Sample browser-visible video evidence during product-cycle follow-up captures.")
    workflow.add_argument("--video-sample-count", type=int, default=5)
    workflow.add_argument("--skip-video", action="store_true")
    workflow.add_argument("--video-platforms", default="auto")
    workflow.add_argument("--generate-voiceover", action="store_true")

    discovery = parser.add_argument_group("Viral discovery")
    discovery.add_argument("--skip-multi-query-viral-discovery", action="store_true")
    discovery.add_argument("--multi-query-dry-run", action="store_true")
    discovery.add_argument("--multi-query-query", action="append", default=[])
    discovery.add_argument("--multi-query-query-count", type=int, default=5)
    discovery.add_argument("--multi-query-platforms", default="")
    discovery.add_argument("--multi-query-top-n", type=int, default=20)
    discovery.add_argument("--multi-query-html-snapshot-root", default="", help="Directory of Codex/browser-rendered platform search HTML snapshots for multi-query discovery.")
    discovery.add_argument("--multi-query-browser-search-timeout-ms", type=int, default=0, help="Defaults to --timeout-ms when omitted.")
    discovery.add_argument(
        "--multi-query-browser-search-wait-until",
        default="",
        choices=["", "load", "domcontentloaded", "networkidle"],
        help="Defaults to --wait-until when omitted.",
    )
    discovery.add_argument("--multi-query-live-official", action="store_true")
    discovery.add_argument("--multi-query-run-creator-follow-up", action="store_true")
    discovery.add_argument("--multi-query-run-follow-up-captures", action="store_true")
    discovery.add_argument("--multi-query-capture-browser-assisted-follow-ups", action="store_true")
    discovery.add_argument("--multi-query-sample-video-frames", action="store_true")
    discovery.add_argument("--multi-query-video-sample-count", type=int, default=5)

    publish = parser.add_argument_group("Publishing")
    publish.add_argument("--skip-publish-queue", action="store_true")
    publish.add_argument("--publish-platforms", default="")
    publish.add_argument("--execute-publish", action="store_true", help="Request approved official publishing through publish readiness/queue. Still requires credentials and exact approval.")
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
    publish.add_argument("--skip-publish-readiness", action="store_true")
    publish.add_argument("--skip-publish-setup-assistant", action="store_true")
    publish.add_argument("--skip-browser-publish-assistant", action="store_true")
    publish.add_argument("--skip-launch-unlock-pack", action="store_true")
    publish.add_argument("--browser-publish-open-browser", action="store_true")
    publish.add_argument("--platform-publish-url", action="append", default=[], help="Override browser-assisted publisher entry as platform=url.")
    publish.add_argument("--run-browser-form-fill", action="store_true", help="Fill visible publisher fields from prepared payloads and stop before final publish.")
    publish.add_argument("--browser-form-fill-headed", action="store_true")
    publish.add_argument("--browser-form-fill-allow-localhost", action="store_true")
    publish.add_argument("--browser-form-fill-install-browser-if-missing", action="store_true")
    publish.add_argument("--browser-form-fill-timeout-ms", type=int, default=30000)
    publish.add_argument("--browser-form-fill-wait-until", default="domcontentloaded", choices=["load", "domcontentloaded", "networkidle"])

    metrics = parser.add_argument_group("Real evidence recovery")
    metrics.add_argument("--skip-metrics-recovery", action="store_true")
    metrics.add_argument("--published-url", action="append", default=[])
    metrics.add_argument("--metrics-github-repo", action="append", default=[])
    metrics.add_argument("--metrics-youtube-video-id", action="append", default=[])
    metrics.add_argument("--metrics-csv", action="append", default=[])
    metrics.add_argument("--metrics-xlsx", action="append", default=[])
    metrics.add_argument("--metrics-json", action="append", default=[])
    metrics.add_argument("--metrics-text", action="append", default=[])
    metrics.add_argument("--metrics-structured-json", action="append", default=[])
    metrics.add_argument("--business-csv", action="append", default=[])
    metrics.add_argument("--business-xlsx", action="append", default=[])
    metrics.add_argument("--business-json", action="append", default=[])
    metrics.add_argument("--business-text", action="append", default=[])
    metrics.add_argument("--skip-post-publish-metrics-capture", action="store_true")
    metrics.add_argument("--post-publish-metrics-allow-localhost", action="store_true")
    metrics.add_argument("--post-publish-metrics-capture-browser-assisted", action="store_true")
    metrics.add_argument("--skip-comment-evidence-capture", action="store_true")
    metrics.add_argument("--comment-evidence-limit", type=int, default=20)
    metrics.add_argument("--comment-evidence-platform", default="")
    metrics.add_argument("--comment-evidence-structured-json", default="")
    metrics.add_argument("--comment-evidence-html-file", default="")
    metrics.add_argument("--comment-evidence-text-file", default="")
    metrics.add_argument("--comment-evidence-allow-localhost", action="store_true")
    metrics.add_argument("--comment-evidence-capture-browser-assisted", action="store_true")
    metrics.add_argument("--comment-evidence-install-browser-if-missing", action="store_true")
    metrics.add_argument("--skip-business-attribution", action="store_true")
    metrics.add_argument("--skip-next-round-optimization", action="store_true")
    metrics.add_argument("--skip-real-evidence-setup", action="store_true")

    audits = parser.add_argument_group("Audits")
    audits.add_argument("--skip-platform-access-audit", action="store_true")
    audits.add_argument("--skip-final-capability-audit", action="store_true")
    audits.add_argument("--skip-final-readiness-matrix", action="store_true")
    audits.add_argument("--skip-self-evolution-audit", action="store_true")
    return parser.parse_args()


def run_product_batch(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [sys.executable, str(PRODUCT_BATCH_RUNNER), "--out-dir", str(out_dir)]
    append_many(command, "--url", args.url)
    append_if_present(command, "--urls-file", args.urls_file)
    append_if_present(command, "--discover-from-url", args.discover_from_url)
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
    append_common_batch_args(command, args)
    step = run_command("product_batch_runner", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/batch/product-batch-runner.json"
    report = read_json(report_path)
    return {
        "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path) if report_path.exists() else "",
        "summary": report.get("summary", {}),
        "discoveryReport": report.get("discoveryReport", ""),
        "discoveredUrls": report.get("discoveredUrls", []),
        "promotionRuns": report.get("promotionRuns", []),
        "exitCode": step["exitCode"],
    }


def append_common_batch_args(command: list[str], args: argparse.Namespace) -> None:
    for flag, enabled in [
        ("--skip-browser", args.skip_browser),
        ("--no-static-fallback", args.no_static_fallback),
        ("--install-browser-if-missing", args.install_browser_if_missing),
        ("--auto-search-competitors", args.auto_search_competitors),
        ("--live-official-competitors", args.live_official_competitors),
        ("--run-creator-follow-up", args.run_creator_follow_up),
        ("--creator-follow-up-dry-run", args.creator_follow_up_dry_run),
        ("--run-follow-up-captures", args.run_follow_up_captures),
        ("--follow-up-dry-run", args.follow_up_dry_run),
        ("--capture-browser-assisted-follow-ups", args.capture_browser_assisted_follow_ups),
        ("--sample-video-frames", args.sample_video_frames),
        ("--skip-video", args.skip_video),
        ("--generate-voiceover", args.generate_voiceover),
        ("--skip-publish-queue", args.skip_publish_queue),
        ("--skip-metrics-recovery", args.skip_metrics_recovery),
    ]:
        if enabled:
            command.append(flag)
    command.extend(["--timeout-ms", str(args.timeout_ms), "--wait-until", args.wait_until])
    command.extend(["--platforms", args.platforms, "--goal", args.goal, "--language", args.language, "--top-n", str(args.top_n)])
    append_if_present(command, "--competitor-query", args.competitor_query)
    if args.sample_video_frames:
        command.extend(["--video-sample-count", str(args.video_sample_count)])
    append_if_present(command, "--video-platforms", args.video_platforms)
    append_if_present(command, "--publish-platforms", args.publish_platforms)
    append_if_present(command, "--github-repo", args.github_repo)
    append_if_present(command, "--github-path", args.github_path)
    append_if_present(command, "--youtube-video-file", args.youtube_video_file)
    append_if_present(command, "--douyin-video-file", args.douyin_video_file)
    if not args.skip_multi_query_viral_discovery:
        command.append("--run-multi-query-viral-discovery")
        command.extend(["--multi-query-query-count", str(args.multi_query_query_count), "--multi-query-top-n", str(args.multi_query_top_n)])
        multi_query_browser_timeout_ms = args.multi_query_browser_search_timeout_ms or args.timeout_ms
        multi_query_browser_wait_until = args.multi_query_browser_search_wait_until or args.wait_until
        command.extend(
            [
                "--multi-query-browser-search-timeout-ms",
                str(multi_query_browser_timeout_ms),
                "--multi-query-browser-search-wait-until",
                multi_query_browser_wait_until,
            ]
        )
        append_many(command, "--multi-query-query", args.multi_query_query)
        append_if_present(command, "--multi-query-platforms", args.multi_query_platforms)
        append_if_present(command, "--multi-query-html-snapshot-root", args.multi_query_html_snapshot_root)
        if args.multi_query_dry_run:
            command.append("--multi-query-dry-run")
        if args.multi_query_live_official:
            command.append("--multi-query-live-official")
        if args.multi_query_run_creator_follow_up:
            command.append("--multi-query-run-creator-follow-up")
        if args.multi_query_run_follow_up_captures or args.run_follow_up_captures:
            command.append("--multi-query-run-follow-up-captures")
        if args.multi_query_capture_browser_assisted_follow_ups or args.capture_browser_assisted_follow_ups:
            command.append("--multi-query-capture-browser-assisted-follow-ups")
        if args.multi_query_sample_video_frames or args.sample_video_frames:
            command.append("--multi-query-sample-video-frames")
            video_sample_count = args.multi_query_video_sample_count if args.multi_query_sample_video_frames else args.video_sample_count
            command.extend(["--multi-query-video-sample-count", str(video_sample_count)])
    append_many(command, "--published-url", args.published_url)
    append_many(command, "--metrics-github-repo", args.metrics_github_repo)
    append_many(command, "--metrics-youtube-video-id", args.metrics_youtube_video_id)
    append_many(command, "--metrics-csv", args.metrics_csv)
    append_many(command, "--metrics-xlsx", args.metrics_xlsx)
    append_many(command, "--metrics-json", args.metrics_json)
    append_many(command, "--metrics-text", args.metrics_text)
    append_many(command, "--metrics-structured-json", args.metrics_structured_json)
    append_many(command, "--business-csv", args.business_csv)
    append_many(command, "--business-xlsx", args.business_xlsx)
    append_many(command, "--business-json", args.business_json)
    append_many(command, "--business-text", args.business_text)
    if not args.skip_post_publish_metrics_capture:
        command.append("--run-post-publish-metrics-capture")
    if args.post_publish_metrics_allow_localhost:
        command.append("--post-publish-metrics-allow-localhost")
    if args.post_publish_metrics_capture_browser_assisted:
        command.append("--post-publish-metrics-capture-browser-assisted")
    if not args.skip_comment_evidence_capture:
        command.append("--run-comment-evidence-capture")
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
    if not args.skip_business_attribution:
        command.append("--run-business-attribution")
    if not args.skip_next_round_optimization:
        command.append("--run-next-round-optimization")


def run_publish_readiness(args: argparse.Namespace, batch: dict[str, Any], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if args.skip_publish_readiness:
        return []
    results = []
    for run in batch.get("promotionRuns", []):
        manifest = existing_path(run.get("workflowManifest", ""))
        run_dir = existing_dir(run.get("outputDir", ""))
        if not manifest or not run_dir:
            continue
        command = [
            sys.executable,
            str(PUBLISH_READINESS),
            "--workflow-manifest",
            str(manifest),
            "--build-queue",
            "--out-dir",
            str(run_dir),
        ]
        append_publish_args(command, args)
        step = run_command(f"publish_readiness_{run.get('id', 'product')}", command, check=False)
        steps.append(step)
        report_path = run_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json"
        report = read_json(report_path)
        results.append(
            {
                "productRunId": run.get("id", ""),
                "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
                "report": str(report_path) if report_path.exists() else "",
                "summary": report.get("summary", {}),
                "exitCode": step["exitCode"],
            }
        )
    return results


def run_publish_setup_assistant(args: argparse.Namespace, publish_readiness: list[dict[str, Any]], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if args.skip_publish_setup_assistant:
        return []
    results = []
    for readiness in publish_readiness:
        readiness_path = existing_path(readiness.get("report", ""))
        if not readiness_path:
            continue
        run_dir = report_out_dir(readiness_path)
        command = [
            sys.executable,
            str(PUBLISH_SETUP_ASSISTANT),
            "--publish-readiness",
            str(readiness_path),
            "--platforms",
            args.publish_platforms or args.platforms,
            "--out-dir",
            str(run_dir),
        ]
        step = run_command(f"publish_setup_{readiness.get('productRunId', 'product')}", command, check=False)
        steps.append(step)
        report_path = run_dir / "reports/promotion-manager/publish-setup/publish-setup.json"
        report = read_json(report_path)
        artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
        results.append(
            {
                "productRunId": readiness.get("productRunId", ""),
                "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
                "report": str(report_path) if report_path.exists() else "",
                "envTemplate": str(artifacts.get("envTemplate", "")),
                "checklist": str(artifacts.get("checklist", "")),
                "platformSetupGuide": str(artifacts.get("platformSetupGuide", "")),
                "platformSetupGuideJson": str(artifacts.get("platformSetupGuideJson", "")),
                "summary": report.get("summary", {}) if isinstance(report.get("summary"), dict) else {},
                "exitCode": step["exitCode"],
            }
        )
    return results


def run_real_evidence_setup(
    args: argparse.Namespace,
    batch: dict[str, Any],
    publish_readiness: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if args.skip_real_evidence_setup:
        return []
    readiness_by_run = {item.get("productRunId", ""): item for item in publish_readiness}
    results = []
    for run in batch.get("promotionRuns", []):
        run_dir = existing_dir(run.get("outputDir", ""))
        queue_path = existing_path(run.get("publishQueue", "")) or (
            run_dir / "reports/promotion-manager/publish-queue/publish-queue.json" if run_dir else None
        )
        if not run_dir or not queue_path or not queue_path.exists():
            continue
        readiness_path = existing_path((readiness_by_run.get(run.get("id", "")) or {}).get("report", ""))
        published_items_path = run_dir / "reports/promotion-manager/published-items/published-items.json"
        command = [
            sys.executable,
            str(REAL_EVIDENCE_SETUP),
            "--publish-queue",
            str(queue_path),
            "--platforms",
            args.publish_platforms or args.platforms,
            "--out-dir",
            str(run_dir),
        ]
        if readiness_path:
            command.extend(["--publish-readiness", str(readiness_path)])
        if published_items_path.exists():
            command.extend(["--published-items-json", str(published_items_path)])
        step = run_command(f"real_evidence_setup_{run.get('id', 'product')}", command, check=False)
        steps.append(step)
        report_path = run_dir / "reports/promotion-manager/real-evidence-setup/real-evidence-setup.json"
        report = read_json(report_path)
        artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
        results.append(
            {
                "productRunId": run.get("id", ""),
                "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
                "report": str(report_path) if report_path.exists() else "",
                "checklist": str(artifacts.get("checklist", "")),
                "platformMetricsTemplate": str(artifacts.get("platformMetricsTemplate", "")),
                "commentEvidenceTemplate": str(artifacts.get("commentEvidenceTemplate", "")),
                "businessAttributionTemplate": str(artifacts.get("businessAttributionTemplate", "")),
                "publishedUrlTemplate": str(artifacts.get("publishedUrlTemplate", "")),
                "summary": report.get("summary", {}) if isinstance(report.get("summary"), dict) else {},
                "exitCode": step["exitCode"],
            }
        )
    return results


def run_browser_publish_assistant(args: argparse.Namespace, batch: dict[str, Any], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if args.skip_browser_publish_assistant:
        return []
    results = []
    for run in batch.get("promotionRuns", []):
        run_dir = existing_dir(run.get("outputDir", ""))
        queue_path = existing_path(run.get("publishQueue", "")) or (run_dir / "reports/promotion-manager/publish-queue/publish-queue.json" if run_dir else None)
        if not run_dir or not queue_path or not queue_path.exists():
            continue
        command = [
            sys.executable,
            str(BROWSER_PUBLISH_ASSISTANT),
            "--publish-queue",
            str(queue_path),
            "--platforms",
            args.publish_platforms or args.platforms,
            "--out-dir",
            str(run_dir),
        ]
        if args.browser_publish_open_browser:
            command.append("--open-browser")
        append_many(command, "--platform-publish-url", args.platform_publish_url)
        step = run_command(f"browser_publish_assistant_{run.get('id', 'product')}", command, check=False)
        steps.append(step)
        report_path = run_dir / "reports/promotion-manager/browser-publish/browser-publish-assistant.json"
        report = read_json(report_path)
        results.append(
            {
                "productRunId": run.get("id", ""),
                "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
                "report": str(report_path) if report_path.exists() else "",
                "summary": report.get("summary", {}),
                "exitCode": step["exitCode"],
            }
        )
    return results


def run_browser_form_fill(args: argparse.Namespace, browser_publish: list[dict[str, Any]], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not args.run_browser_form_fill:
        return []
    results = []
    for publish in browser_publish:
        publish_report_path = existing_path(publish.get("report", ""))
        if not publish_report_path:
            continue
        publish_report = read_json(publish_report_path)
        run_dir = report_out_dir(publish_report_path)
        for record in publish_report.get("records", []):
            payload_json = str(((record.get("payloadFiles") or {}).get("json") or "")).strip()
            payload_path = existing_path(payload_json)
            platform = str(record.get("platform", ""))
            if not payload_path:
                results.append(
                    {
                        "productRunId": publish.get("productRunId", ""),
                        "platform": platform,
                        "status": "blocked",
                        "reason": "Prepared browser publish payload JSON was missing.",
                        "payloadJson": payload_json,
                        "report": "",
                        "exitCode": None,
                    }
                )
                continue
            fill_out_dir = run_dir / "browser-form-fill-runs" / safe_path_part(platform or "platform")
            command = [
                sys.executable,
                str(BROWSER_PUBLISH_FORM_FILL),
                "--payload-json",
                str(payload_path),
                "--out-dir",
                str(fill_out_dir),
                "--timeout-ms",
                str(args.browser_form_fill_timeout_ms),
                "--wait-until",
                args.browser_form_fill_wait_until,
            ]
            if args.browser_form_fill_headed:
                command.append("--headed")
            if args.browser_form_fill_allow_localhost:
                command.append("--allow-localhost")
            if args.browser_form_fill_install_browser_if_missing:
                command.append("--install-browser-if-missing")
            step = run_command(f"browser_form_fill_{publish.get('productRunId', 'product')}_{platform or 'platform'}", command, check=False)
            steps.append(step)
            report_path = fill_out_dir / "reports/promotion-manager/browser-publish/browser-form-fill.json"
            report = read_json(report_path)
            results.append(
                {
                    "productRunId": publish.get("productRunId", ""),
                    "platform": platform,
                    "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
                    "report": str(report_path) if report_path.exists() else "",
                    "screenshot": str(((report.get("artifacts") or {}).get("screenshot") or "")),
                    "payloadJson": str(payload_path),
                    "filledFields": len(report.get("filledFields", [])) if isinstance(report.get("filledFields"), list) else 0,
                    "missingFields": report.get("missingFields", []),
                    "submitted": bool(report.get("submitted", False)),
                    "finalPublishUserActionRequired": bool(report.get("finalPublishUserActionRequired", True)),
                    "exitCode": step["exitCode"],
                    "stdoutTail": step["stdoutTail"],
                    "stderrTail": step["stderrTail"],
                }
            )
    return results


def run_launch_unlock_pack(
    args: argparse.Namespace,
    batch: dict[str, Any],
    publish_readiness: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if args.skip_launch_unlock_pack:
        return []
    readiness_by_run = {item.get("productRunId", ""): item for item in publish_readiness}
    results = []
    for run in batch.get("promotionRuns", []):
        run_dir = existing_dir(run.get("outputDir", ""))
        queue_path = existing_path(run.get("publishQueue", "")) or (
            run_dir / "reports/promotion-manager/publish-queue/publish-queue.json" if run_dir else None
        )
        if not run_dir or not queue_path or not queue_path.exists():
            continue
        readiness_path = existing_path((readiness_by_run.get(run.get("id", "")) or {}).get("report", ""))
        command = [
            sys.executable,
            str(LAUNCH_UNLOCK_PACK),
            "--publish-queue",
            str(queue_path),
            "--platforms",
            args.publish_platforms or args.platforms,
            "--out-dir",
            str(run_dir),
        ]
        if readiness_path:
            command.extend(["--publish-readiness", str(readiness_path)])
        append_if_present(command, "--github-repo", args.github_repo)
        append_if_present(command, "--youtube-video-file", args.youtube_video_file)
        append_if_present(command, "--douyin-video-file", args.douyin_video_file)
        append_first(command, "--business-csv", args.business_csv)
        append_first(command, "--business-xlsx", args.business_xlsx)
        append_first(command, "--business-json", args.business_json)
        append_first(command, "--business-text", args.business_text)
        append_many(command, "--platform-publish-url", args.platform_publish_url)
        step = run_command(f"launch_unlock_pack_{run.get('id', 'product')}", command, check=False)
        steps.append(step)
        report_path = run_dir / "reports/promotion-manager/launch-unlock/launch-unlock.json"
        report = read_json(report_path)
        artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
        results.append(
            {
                "productRunId": run.get("id", ""),
                "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
                "report": str(report_path) if report_path.exists() else "",
                "checklist": str(artifacts.get("checklist", "")),
                "nextActionCommands": str(artifacts.get("nextActionCommands", "")),
                "summary": report.get("summary", {}) if isinstance(report.get("summary"), dict) else {},
                "exitCode": step["exitCode"],
            }
        )
    return results


def run_audits(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    audits: dict[str, Any] = {}
    if not args.skip_platform_access_audit:
        audits["platformAccess"] = run_audit("platform_access_audit", PLATFORM_ACCESS_AUDIT, out_dir, steps)
    if not args.skip_final_capability_audit:
        audits["finalCapability"] = run_audit("final_capability_audit", FINAL_CAPABILITY_AUDIT, out_dir, steps)
    if not args.skip_self_evolution_audit:
        audits["selfEvolution"] = run_audit("self_evolution_audit", SELF_EVOLUTION_AUDIT, out_dir, steps)
    return audits


def run_audit(name: str, script: Path, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    command = [sys.executable, str(script), "--out-dir", str(out_dir)]
    step = run_command(name, command, check=False)
    steps.append(step)
    path = audit_report_path(name, out_dir)
    report = read_json(path)
    return {
        "status": report.get("finalStatus") or report.get("status") or ("ready" if step["exitCode"] == 0 else "error"),
        "report": str(path) if path.exists() else "",
        "exitCode": step["exitCode"],
    }


def run_final_readiness_matrix(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    if args.skip_final_readiness_matrix:
        return {}
    final_run_path = report_dir(out_dir) / "final-capability-run.json"
    command = [
        sys.executable,
        str(FINAL_CAPABILITY_READINESS),
        "--out-dir",
        str(out_dir),
        "--final-run",
        str(final_run_path),
    ]
    step = run_command("final_capability_readiness", command, check=False)
    steps.append(step)
    path = out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json"
    report = read_json(path)
    return {
        "status": report.get("status") or ("ready" if step["exitCode"] == 0 else "error"),
        "report": str(path) if path.exists() else "",
        "summary": report.get("summary", {}) if isinstance(report.get("summary"), dict) else {},
        "exitCode": step["exitCode"],
    }


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    batch: dict[str, Any],
    publish_readiness: list[dict[str, Any]],
    publish_setup: list[dict[str, Any]],
    real_evidence_setup: list[dict[str, Any]],
    browser_publish: list[dict[str, Any]],
    browser_form_fill: list[dict[str, Any]],
    launch_unlock: list[dict[str, Any]],
    cycle_evidence: list[dict[str, Any]],
    audits: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = {
        "productBatchStatus": batch.get("status", ""),
        "promotionRuns": len(batch.get("promotionRuns", [])),
        "publishExecutionRequested": bool(args.execute_publish),
        "publishApprovalProvided": args.approval == APPROVAL_PHRASE,
        "publishReadinessRuns": len(publish_readiness),
        "publishSetupRuns": len(publish_setup),
        "publishSetupEnvVars": sum(int_value((item.get("summary") or {}).get("credentialEnvNames")) for item in publish_setup),
        "realEvidenceSetupRuns": len(real_evidence_setup),
        "realEvidenceSetupTargets": sum(int_value((item.get("summary") or {}).get("targets")) for item in real_evidence_setup),
        "browserPublishAssistantRuns": len(browser_publish),
        "browserFormFillRuns": len(browser_form_fill),
        "launchUnlockPackRuns": len(launch_unlock),
        "launchUnlockReadyGates": sum(int_value((item.get("summary") or {}).get("readyGates")) for item in launch_unlock),
        "launchUnlockWaitingGates": sum(int_value((item.get("summary") or {}).get("waitingGates")) for item in launch_unlock),
        "browserFormFillReady": sum(1 for item in browser_form_fill if item.get("status") == "ready"),
        "browserFormFillBlocked": sum(1 for item in browser_form_fill if item.get("status") == "blocked"),
        "browserFormFillErrors": sum(1 for item in browser_form_fill if item.get("status") == "error"),
        "browserFormFillFilledFields": sum(int_value(item.get("filledFields")) for item in browser_form_fill),
        "nextRoundOptimizationRuns": int((batch.get("summary") or {}).get("nextRoundOptimizationRuns") or 0),
        "multiQueryDiscoveryRuns": int((batch.get("summary") or {}).get("multiQueryDiscoveryRuns") or 0),
    }
    summary.update(cycle_evidence_summary(cycle_evidence))
    return {
        "generatedAt": TODAY,
        "status": final_status(batch, publish_readiness, publish_setup, real_evidence_setup, browser_publish, browser_form_fill, launch_unlock, audits),
        "outDir": str(out_dir),
        "input": {
            "urls": args.url,
            "urlsFile": args.urls_file,
            "discoverFromUrl": args.discover_from_url,
            "discoveryHtmlFile": args.discovery_html_file,
            "discoverySitemapUrl": args.discovery_sitemap_url,
            "discoverySitemapFile": args.discovery_sitemap_file,
            "discoveryBaseUrl": args.discovery_base_url,
            "discoveryTopN": args.discovery_top_n,
            "discoveryMinScore": args.discovery_min_score,
            "discoveryMaxPages": args.discovery_max_pages,
            "discoveryMaxDepth": args.discovery_max_depth,
            "discoveryMaxSitemapUrls": args.discovery_max_sitemap_urls,
            "discoveryTimeout": args.discovery_timeout,
            "discoveryIncludeExternal": bool(args.discovery_include_external),
            "discoverySkipSitemaps": bool(args.discovery_skip_sitemaps),
            "discoveryAllowLocalhost": bool(args.discovery_allow_localhost),
            "platforms": args.platforms,
            "codexReadFirst": True,
            "publishExecutionRequested": bool(args.execute_publish),
            "publishApprovalProvided": args.approval == APPROVAL_PHRASE,
        },
        "summary": summary,
        "productBatch": batch,
        "cycleEvidence": cycle_evidence,
        "publishReadiness": publish_readiness,
        "publishSetup": publish_setup,
        "realEvidenceSetup": real_evidence_setup,
        "browserPublishAssistant": browser_publish,
        "browserFormFill": browser_form_fill,
        "launchUnlockPack": launch_unlock,
        "audits": audits,
        "externalGates": external_gates(),
        "recommendedNextCommands": recommended_next_commands(out_dir),
        "guardrails": guardrails(),
        "steps": steps,
    }


def collect_cycle_evidence(batch: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for run in batch.get("promotionRuns", []):
        run_dir = existing_dir(run.get("outputDir", ""))
        cycle_path = existing_path(run.get("cycleReport", "")) or (
            run_dir / "reports/promotion-manager/cycle/promotion-cycle.json" if run_dir else None
        )
        manifest_path = existing_path(run.get("workflowManifest", ""))
        cycle = read_json(cycle_path) if cycle_path else {}
        manifest = read_json(manifest_path) if manifest_path else {}
        artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
        videos = manifest.get("videoGeneration") if isinstance(manifest.get("videoGeneration"), list) else []
        media_asset_pack_path = existing_path(artifacts.get("mediaAssetPack", ""))
        media_asset_pack = read_json(media_asset_pack_path) if media_asset_pack_path else {}
        item = {
            "productRunId": run.get("id", ""),
            "url": run.get("url", ""),
            "status": run.get("status", ""),
            "automationStatus": cycle.get("automationStatus") or run.get("automationStatus", ""),
            "outputDir": str(run_dir) if run_dir else str(run.get("outputDir", "")),
            "cycleReport": str(cycle_path) if cycle_path and cycle_path.exists() else "",
            "workflowManifest": str(manifest_path) if manifest_path and manifest_path.exists() else "",
            "product": run.get("product") or manifest.get("product") or {},
            "content": {
                "contentJson": artifact_path(artifacts.get("contentJson", "")),
                "publishPack": artifact_path(artifacts.get("publishPack", "")),
                "competitorInformedContent": artifact_path(artifacts.get("competitorInformedContent", "")),
                "competitorInformedStrategy": artifact_path(artifacts.get("competitorInformedStrategy", "")),
            },
            "competitorResearch": {
                "viralContentLibrary": artifact_path(artifacts.get("viralContentLibrary", "")),
                "creatorLeaderboard": artifact_path(artifacts.get("creatorLeaderboard", "")),
                "creatorFollowUpResults": artifact_path(artifacts.get("creatorFollowUpResults", "")),
                "deepCompetitorLibrary": artifact_path(artifacts.get("deepCompetitorLibrary", "")),
                "multiQueryViralDiscovery": run.get("multiQueryViralDiscovery", {}),
            },
            "videoGeneration": summarize_videos(videos),
            "mediaAssets": summarize_media_assets(media_asset_pack_path, media_asset_pack),
            "publishQueue": summarize_section(cycle.get("publishQueue"), "queue"),
            "publishedItems": summarize_section(cycle.get("publishedItems"), "publishedItems"),
            "postPublishMetricsCapture": summarize_section(cycle.get("postPublishMetricsCapture"), "report", ["metricExport"]),
            "commentEvidenceCapture": summarize_section(cycle.get("commentEvidenceCapture"), "report", ["commentEvidenceExport"]),
            "businessAttribution": summarize_section(cycle.get("businessAttribution"), "report", ["businessAttributionExport"]),
            "metricsRecovery": summarize_section(cycle.get("metricsRecovery"), "metricsRecovery"),
            "nextRoundOptimization": summarize_section(cycle.get("nextRoundOptimization"), "report"),
        }
        item["evidenceCounts"] = evidence_counts(item)
        evidence.append(item)
    return evidence


def summarize_videos(videos: list[dict[str, Any]]) -> dict[str, Any]:
    generated = []
    for item in videos:
        video = str(item.get("video") or "").strip()
        if video and Path(video).exists():
            generated.append(video)
    return {
        "items": videos,
        "generatedFiles": generated,
        "generatedCount": len(generated),
        "statusCounts": count_statuses(videos),
    }


def summarize_media_assets(path: Path | None, report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "status": report.get("status", "missing" if not report else ""),
        "report": str(path) if path and path.exists() else "",
        "exists": bool(path and path.exists()),
        "summary": summary,
        "platforms": len(report.get("platforms", [])) if isinstance(report.get("platforms"), list) else 0,
    }


def summarize_section(value: Any, path_key: str, extra_path_keys: list[str] | None = None) -> dict[str, Any]:
    section = value if isinstance(value, dict) else {}
    report_path = artifact_path(section.get(path_key, ""))
    result = {
        "status": section.get("status", "missing" if not section else ""),
        "report": report_path,
        "exists": bool(report_path and Path(report_path).exists()),
        "summary": section.get("summary", {}) if isinstance(section.get("summary"), dict) else {},
    }
    for key in extra_path_keys or []:
        result[key] = artifact_path(section.get(key, ""))
    if section.get("reason"):
        result["reason"] = section.get("reason")
    return result


def evidence_counts(item: dict[str, Any]) -> dict[str, int]:
    post_metrics = item.get("postPublishMetricsCapture", {}).get("summary", {})
    comments = item.get("commentEvidenceCapture", {}).get("summary", {})
    business = item.get("businessAttribution", {}).get("summary", {})
    metrics = item.get("metricsRecovery", {}).get("summary", {})
    optimization = item.get("nextRoundOptimization", {}).get("summary", {})
    field_counts = metric_field_counts(post_metrics, metrics)
    comment_count = int_value(comments.get("commentCount") or optimization.get("commentCount"))
    matched_business_rows = int_value(business.get("matchedRows") or optimization.get("businessAttributions"))
    if comment_count:
        field_counts["comments"] = max(int_value(field_counts.get("comments")), comment_count)
    if has_positive_number(business.get("attributedOrders")) or has_positive_number(business.get("totalOrders")):
        field_counts["orders"] = max(int_value(field_counts.get("orders")), matched_business_rows or 1)
    if has_positive_number(business.get("attributedRevenue")) or has_positive_number(business.get("totalRevenue")):
        field_counts["revenue"] = max(int_value(field_counts.get("revenue")), matched_business_rows or 1)
    multi_query = (
        item.get("competitorResearch", {})
        .get("multiQueryViralDiscovery", {})
        .get("summary", {})
    )
    media_summary = item.get("mediaAssets", {}).get("summary", {})
    recovered_metric_records = max(
        int_value(post_metrics.get("capturedMetricRecords")),
        int_value(metrics.get("recordsWithMetrics")),
    )
    return {
        "capturedMetricRecords": recovered_metric_records,
        "commentCount": comment_count,
        "matchedBusinessRows": matched_business_rows,
        "recordsWithMetrics": int_value(metrics.get("recordsWithMetrics")),
        "viewsEvidenceRecords": int_value(field_counts.get("views")),
        "likesEvidenceRecords": int_value(field_counts.get("likes")),
        "favoritesEvidenceRecords": int_value(field_counts.get("favorites")),
        "commentsEvidenceRecords": int_value(field_counts.get("comments")),
        "sharesEvidenceRecords": int_value(field_counts.get("shares")),
        "clicksEvidenceRecords": int_value(field_counts.get("clicks")),
        "messagesEvidenceRecords": int_value(field_counts.get("messages")),
        "leadsEvidenceRecords": int_value(field_counts.get("leads")),
        "ordersEvidenceRecords": int_value(field_counts.get("orders")),
        "revenueEvidenceRecords": int_value(field_counts.get("revenue")),
        "socialMetricEvidenceFields": sum(1 for field in ("views", "likes", "comments", "favorites", "shares") if int_value(field_counts.get(field)) > 0),
        "fullFunnelEvidenceFields": sum(1 for field in ("views", "likes", "comments", "orders", "revenue") if int_value(field_counts.get(field)) > 0),
        "manualOrPendingRequirements": int_value(metrics.get("manualOrPendingRequirements"))
        + int_value(optimization.get("manualOrPendingRequirements")),
        "nextRoundContent": int_value(optimization.get("nextRoundContent")),
        "multiQuerySearchCapturesReady": int_value(multi_query.get("searchCapturesReady")),
        "multiQueryViralMaterialsObserved": int_value(multi_query.get("viralMaterialsObserved")),
        "multiQueryMergedMaterials": int_value(multi_query.get("mergedMaterials")),
        "multiQueryMergedCreators": int_value(multi_query.get("mergedCreators")),
        "multiQueryDeepEvidenceRuns": int_value(multi_query.get("deepEvidenceRuns")),
        "multiQueryFollowUpCaptureRuns": int_value(multi_query.get("followUpCaptureRuns")),
        "multiQueryFollowUpImportedRecords": int_value(multi_query.get("followUpImportedRecords")),
        "multiQueryBrowserVisibleCaptureReady": int_value(multi_query.get("followUpBrowserVisibleReady")),
        "multiQueryVideoSampleRuns": int_value(multi_query.get("videoSampleRuns")),
        "multiQueryVideoSampleReady": int_value(multi_query.get("videoSampleReady")),
        "multiQueryVideoSampleFrames": int_value(multi_query.get("videoSampleFrames")),
        "mediaAssetPlatforms": int_value(media_summary.get("platforms")),
        "mediaAssetVideosReady": int_value(media_summary.get("videosReady")),
        "mediaAssetCoversReady": int_value(media_summary.get("coversReady")),
        "mediaAssetDetailImagesReady": int_value(media_summary.get("detailImagesReady")),
    }


def cycle_evidence_summary(cycle_evidence: list[dict[str, Any]]) -> dict[str, int]:
    counts = [item.get("evidenceCounts", {}) for item in cycle_evidence]
    return {
        "contentArtifacts": sum(1 for item in cycle_evidence if item.get("content", {}).get("contentJson")),
        "videoFilesGenerated": sum(int_value(item.get("videoGeneration", {}).get("generatedCount")) for item in cycle_evidence),
        "mediaAssetPacks": sum(1 for item in cycle_evidence if item.get("mediaAssets", {}).get("exists")),
        "mediaAssetVideosReady": sum(int_value(item.get("mediaAssetVideosReady")) for item in counts),
        "mediaAssetCoversReady": sum(int_value(item.get("mediaAssetCoversReady")) for item in counts),
        "mediaAssetDetailImagesReady": sum(int_value(item.get("mediaAssetDetailImagesReady")) for item in counts),
        "publishQueues": sum(1 for item in cycle_evidence if item.get("publishQueue", {}).get("exists")),
        "publishedItemsReports": sum(1 for item in cycle_evidence if item.get("publishedItems", {}).get("exists")),
        "postPublishMetricsCaptureRuns": sum(1 for item in cycle_evidence if item.get("postPublishMetricsCapture", {}).get("status") == "ready"),
        "commentEvidenceCaptureRuns": sum(1 for item in cycle_evidence if item.get("commentEvidenceCapture", {}).get("status") == "ready"),
        "businessAttributionRuns": sum(1 for item in cycle_evidence if item.get("businessAttribution", {}).get("status") == "ready"),
        "metricsRecoveryRuns": sum(1 for item in cycle_evidence if item.get("metricsRecovery", {}).get("status") == "ready"),
        "capturedMetricRecords": sum(int_value(item.get("capturedMetricRecords")) for item in counts),
        "commentCount": sum(int_value(item.get("commentCount")) for item in counts),
        "matchedBusinessRows": sum(int_value(item.get("matchedBusinessRows")) for item in counts),
        "recordsWithMetrics": sum(int_value(item.get("recordsWithMetrics")) for item in counts),
        "viewsEvidenceRecords": sum(int_value(item.get("viewsEvidenceRecords")) for item in counts),
        "likesEvidenceRecords": sum(int_value(item.get("likesEvidenceRecords")) for item in counts),
        "favoritesEvidenceRecords": sum(int_value(item.get("favoritesEvidenceRecords")) for item in counts),
        "commentsEvidenceRecords": sum(int_value(item.get("commentsEvidenceRecords")) for item in counts),
        "sharesEvidenceRecords": sum(int_value(item.get("sharesEvidenceRecords")) for item in counts),
        "clicksEvidenceRecords": sum(int_value(item.get("clicksEvidenceRecords")) for item in counts),
        "messagesEvidenceRecords": sum(int_value(item.get("messagesEvidenceRecords")) for item in counts),
        "leadsEvidenceRecords": sum(int_value(item.get("leadsEvidenceRecords")) for item in counts),
        "ordersEvidenceRecords": sum(int_value(item.get("ordersEvidenceRecords")) for item in counts),
        "revenueEvidenceRecords": sum(int_value(item.get("revenueEvidenceRecords")) for item in counts),
        "socialMetricEvidenceFields": sum(int_value(item.get("socialMetricEvidenceFields")) for item in counts),
        "fullFunnelEvidenceFields": sum(int_value(item.get("fullFunnelEvidenceFields")) for item in counts),
        "manualOrPendingRequirements": sum(int_value(item.get("manualOrPendingRequirements")) for item in counts),
        "nextRoundContent": sum(int_value(item.get("nextRoundContent")) for item in counts),
        "multiQuerySearchCapturesReady": sum(int_value(item.get("multiQuerySearchCapturesReady")) for item in counts),
        "multiQueryViralMaterialsObserved": sum(int_value(item.get("multiQueryViralMaterialsObserved")) for item in counts),
        "multiQueryMergedMaterials": sum(int_value(item.get("multiQueryMergedMaterials")) for item in counts),
        "multiQueryMergedCreators": sum(int_value(item.get("multiQueryMergedCreators")) for item in counts),
        "multiQueryDeepEvidenceRuns": sum(int_value(item.get("multiQueryDeepEvidenceRuns")) for item in counts),
        "multiQueryFollowUpCaptureRuns": sum(int_value(item.get("multiQueryFollowUpCaptureRuns")) for item in counts),
        "multiQueryFollowUpImportedRecords": sum(int_value(item.get("multiQueryFollowUpImportedRecords")) for item in counts),
        "multiQueryBrowserVisibleCaptureReady": sum(int_value(item.get("multiQueryBrowserVisibleCaptureReady")) for item in counts),
        "multiQueryVideoSampleRuns": sum(int_value(item.get("multiQueryVideoSampleRuns")) for item in counts),
        "multiQueryVideoSampleReady": sum(int_value(item.get("multiQueryVideoSampleReady")) for item in counts),
        "multiQueryVideoSampleFrames": sum(int_value(item.get("multiQueryVideoSampleFrames")) for item in counts),
    }


def count_statuses(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def metric_field_counts(*summaries: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        raw_counts = summary.get("metricFieldCounts")
        if isinstance(raw_counts, dict):
            for field, value in raw_counts.items():
                counts[str(field)] = counts.get(str(field), 0) + int_value(value)
        fields = summary.get("metricFields")
        if isinstance(fields, list):
            for field in fields:
                text = str(field)
                counts[text] = max(counts.get(text, 0), 1)
        totals = summary.get("totals")
        if isinstance(totals, dict):
            for field, value in totals.items():
                if has_positive_number(value):
                    counts[str(field)] = max(counts.get(str(field), 0), 1)
    return counts


def artifact_path(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return text if text and Path(text).exists() else ""


def has_positive_number(value: Any) -> bool:
    try:
        return float(value or 0) > 0
    except (TypeError, ValueError):
        return False


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def final_status(
    batch: dict[str, Any],
    publish_readiness: list[dict[str, Any]],
    publish_setup: list[dict[str, Any]],
    real_evidence_setup: list[dict[str, Any]],
    browser_publish: list[dict[str, Any]],
    browser_form_fill: list[dict[str, Any]],
    launch_unlock: list[dict[str, Any]],
    audits: dict[str, Any],
) -> str:
    if batch.get("status") in {"blocked", "error", ""}:
        return "blocked"
    failed_readiness = any(item.get("status") == "error" for item in publish_readiness)
    failed_setup = any(item.get("status") == "error" for item in publish_setup)
    failed_real_evidence = any(item.get("status") == "error" for item in real_evidence_setup)
    failed_browser = any(item.get("status") == "error" for item in browser_publish)
    failed_form_fill = any(item.get("status") == "error" for item in browser_form_fill)
    failed_launch_unlock = any(item.get("status") == "error" for item in launch_unlock)
    failed_audit = any(item.get("exitCode") not in {0, None} for item in audits.values())
    if failed_readiness or failed_setup or failed_real_evidence or failed_browser or failed_form_fill or failed_launch_unlock or failed_audit:
        return "partial_ready_with_errors"
    if batch.get("status") == "ready" and publish_readiness:
        return "partial_ready"
    return "partial_ready"


def external_gates() -> list[dict[str, str]]:
    return [
        {"area": "official_publish", "gate": "I_APPROVE_PUBLISH plus platform credentials are required for writes."},
        {"area": "youtube", "gate": "OAuth client credentials or a temporary OAuth access token are required for upload."},
        {"area": "github", "gate": "GITHUB_TOKEN or GH_TOKEN is required for repository writes."},
        {"area": "douyin", "gate": "Current Douyin publishing is browser-assisted/manual; the official API port is reserved until verified authorization is available."},
        {"area": "zhihu_xiaohongshu", "gate": "Manual/browser-assisted publishing remains required unless official creator publishing access is verified."},
        {"area": "metrics_revenue", "gate": "Private analytics, orders, and revenue require official APIs, screenshots, or business exports."},
        {"area": "self_evolution", "gate": "Installed Skill sync and dependency changes require explicit reviewed approval."},
    ]


def recommended_next_commands(out_dir: Path) -> list[dict[str, str]]:
    return [
        {
            "purpose": "review_batch_report",
            "command": f"open \"{out_dir / 'reports/promotion-manager/batch/product-batch-runner.md'}\"",
        },
        {
            "purpose": "build_publish_setup_kit",
            "command": f"python scripts/publish_setup_assistant.py --publish-readiness \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/publish-readiness/publish-readiness.json\" --out-dir \"{out_dir}/product-batch-runs/<id>\"",
        },
        {
            "purpose": "prepare_browser_assisted_publish",
            "command": f"python scripts/browser_publish_assistant.py --publish-queue \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/publish-queue/publish-queue.json\" --out-dir \"{out_dir}/product-batch-runs/<id>\"",
        },
        {
            "purpose": "run_browser_publish_session",
            "command": f"python scripts/browser_publish_session.py --publish-queue \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/publish-queue/publish-queue.json\" --run-form-fill --out-dir \"{out_dir}/product-batch-runs/<id>\"",
        },
        {
            "purpose": "build_launch_unlock_pack",
            "command": f"python scripts/launch_unlock_pack.py --publish-queue \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/publish-queue/publish-queue.json\" --publish-readiness \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/publish-readiness/publish-readiness.json\" --out-dir \"{out_dir}/product-batch-runs/<id>\"",
        },
        {
            "purpose": "prepare_real_evidence_templates",
            "command": f"python scripts/real_evidence_setup.py --publish-queue \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/publish-queue/publish-queue.json\" --out-dir \"{out_dir}/product-batch-runs/<id>\"",
        },
        {
            "purpose": "fill_browser_publish_fields_without_submit",
            "command": f"python scripts/browser_publish_form_fill.py --payload-json \"{out_dir}/product-batch-runs/<id>/reports/promotion-manager/browser-publish/payloads/<platform>.payload.json\" --out-dir \"{out_dir}/product-batch-runs/<id>\"",
        },
        {
            "purpose": "sync_installed_skill_when_approved",
            "command": "python scripts/self_evolution_audit.py --sync-installed-skill --approval I_APPROVE_SKILL_SYNC --out-dir \"./promotion-output\"",
        },
        {
            "purpose": "build_final_readiness_matrix",
            "command": f"python scripts/final_capability_readiness.py --out-dir \"{out_dir}\"",
        },
    ]


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "final-capability-run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "final-capability-run.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final Capability Run",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Output: {report['outDir']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## External Gates"])
    lines.extend(f"- {item['area']}: {item['gate']}" for item in report["externalGates"])
    lines.extend(["", "## Reports"])
    lines.append(f"- Product batch: {report['productBatch'].get('report', '')}")
    lines.extend(["", "## Cycle Evidence"])
    for item in report["cycleEvidence"]:
        counts = item.get("evidenceCounts", {})
        product = item.get("product") or {}
        lines.append(f"- {item.get('productRunId', '')}: {product.get('productName') or product.get('name') or 'unknown'}")
        lines.append(f"  Content: {item.get('content', {}).get('contentJson', '')}")
        lines.append(f"  Videos: {item.get('videoGeneration', {}).get('generatedCount', 0)} generated")
        lines.append(f"  Media assets: `{item.get('mediaAssets', {}).get('status', '')}` {item.get('mediaAssets', {}).get('report', '')}")
        lines.append(f"  Publish queue: `{item.get('publishQueue', {}).get('status', '')}` {item.get('publishQueue', {}).get('report', '')}")
        lines.append(
            "  Evidence: "
            f"metrics={counts.get('capturedMetricRecords', 0)}, "
            f"comments={counts.get('commentCount', 0)}, "
            f"businessRows={counts.get('matchedBusinessRows', 0)}, "
            f"nextRound={counts.get('nextRoundContent', 0)}"
        )
    for item in report["publishReadiness"]:
        lines.append(f"- Publish readiness ({item['productRunId']}): `{item['status']}` {item['report']}")
    for item in report["publishSetup"]:
        lines.append(f"- Publish setup ({item['productRunId']}): `{item['status']}` {item['report']}")
    for item in report["realEvidenceSetup"]:
        lines.append(f"- Real evidence setup ({item['productRunId']}): `{item['status']}` {item['report']}")
    for item in report["browserPublishAssistant"]:
        lines.append(f"- Browser publish ({item['productRunId']}): `{item['status']}` {item['report']}")
    for item in report["browserFormFill"]:
        lines.append(
            f"- Browser form fill ({item.get('productRunId', '')}/{item.get('platform', '')}): "
            f"`{item.get('status', '')}` fields={item.get('filledFields', 0)} {item.get('report', '')}"
        )
    for item in report["launchUnlockPack"]:
        lines.append(f"- Launch unlock pack ({item['productRunId']}): `{item['status']}` {item['report']}")
    for name, item in report["audits"].items():
        lines.append(f"- {name}: `{item['status']}` {item['report']}")
    readiness = report.get("finalReadinessMatrix") or {}
    if readiness:
        lines.append(f"- final readiness matrix: `{readiness.get('status', '')}` {readiness.get('report', '')}")
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- {item['purpose']}: `{item['command']}`" for item in report["recommendedNextCommands"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def append_publish_args(command: list[str], args: argparse.Namespace) -> None:
    append_if_present(command, "--platforms", args.publish_platforms or args.platforms)
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


def run_command(name: str, command: list[str], check: bool = True) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    step = {
        "name": name,
        "command": display_command(command),
        "exitCode": result.returncode,
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
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def audit_report_path(name: str, out_dir: Path) -> Path:
    if name == "platform_access_audit":
        return out_dir / "reports/promotion-manager/platform-access/platform-access-audit.json"
    if name == "final_capability_audit":
        return out_dir / "reports/promotion-manager/capability/final-capability-audit.json"
    return out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.json"


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/final-run"


def existing_path(value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.exists() else None


def existing_dir(value: Any) -> Path | None:
    path = existing_path(value)
    return path if path and path.is_dir() else None


def report_out_dir(report_path: Path) -> Path:
    parts = report_path.parts
    if len(parts) >= 4 and parts[-4:-1] == ("reports", "promotion-manager", "browser-publish"):
        return report_path.parents[3]
    if len(parts) >= 4 and parts[-4:-1] == ("reports", "promotion-manager", "publish-readiness"):
        return report_path.parents[3]
    return report_path.parent


def safe_path_part(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.lower()).strip("-")
    return text or "item"


def append_if_present(command: list[str], flag: str, value: Any) -> None:
    text = "" if value is None else str(value).strip()
    if text:
        command.extend([flag, text])


def append_many(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        append_if_present(command, flag, value)


def append_first(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        if str(value or "").strip():
            append_if_present(command, flag, value)
            return


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


def guardrails() -> list[str]:
    return [
        "Read product URLs before content generation and prefer browser-visible structured snapshots when available.",
        "Use public or official evidence for competitor research; do not bypass login, captcha, risk controls, or private endpoints.",
        "Prepare publish queues and browser-assisted payloads, but do not click final publish without explicit user action.",
        "Official writes require credentials and explicit I_APPROVE_PUBLISH approval.",
        "Use only real public/official/platform/business evidence for metrics, comments, orders, and revenue.",
        "Do not store cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
    ]


if __name__ == "__main__":
    main()
