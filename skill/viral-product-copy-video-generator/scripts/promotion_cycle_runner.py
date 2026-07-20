#!/usr/bin/env python3
"""Run a promotion workflow through publish queue, published-item registration, and metrics recovery."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import metrics_intake


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUN_WORKFLOW = SCRIPTS / "run_promotion_workflow.py"
PUBLISH_QUEUE = SCRIPTS / "publish_queue.py"
PUBLISHED_ITEMS = SCRIPTS / "published_items.py"
METRICS_RECOVERY = SCRIPTS / "metrics_recovery.py"
POST_PUBLISH_METRICS_CAPTURE = SCRIPTS / "post_publish_metrics_capture.py"
COMMENT_EVIDENCE_CAPTURE = SCRIPTS / "comment_evidence_capture.py"
BUSINESS_ATTRIBUTION = SCRIPTS / "business_attribution.py"
NEXT_ROUND_OPTIMIZER = SCRIPTS / "next_round_optimizer.py"
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    workflow = prepare_workflow(args, out_dir, steps)
    publish = run_publish_queue(args, out_dir, workflow, steps)
    published = run_published_items(args, out_dir, publish, steps)
    post_publish_metrics = run_post_publish_metrics_capture(args, out_dir, published, steps)
    comment_evidence = run_comment_evidence_capture(args, out_dir, published, steps)
    business_attribution = run_business_attribution(args, out_dir, published, steps)
    metrics = run_metrics_recovery(args, out_dir, workflow, publish, published, post_publish_metrics, business_attribution, steps)
    next_round_optimization = run_next_round_optimization(args, out_dir, workflow, publish, comment_evidence, business_attribution, metrics, steps)
    report = build_cycle_report(
        args,
        out_dir,
        workflow,
        publish,
        published,
        post_publish_metrics,
        comment_evidence,
        business_attribution,
        metrics,
        next_round_optimization,
        steps,
    )
    write_cycle_report(out_dir, report)
    print(f"Promotion cycle report written to: {(cycle_dir(out_dir) / 'promotion-cycle.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run product promotion generation, guarded publishing, published URL registration, and metrics recovery.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--workflow-manifest", default="", help="Use an existing workflow-manifest.json instead of running product intake/content generation.")
    source.add_argument("--browser-url", default="")
    source.add_argument("--product-url", default="")
    source.add_argument("--html-file", default="")
    source.add_argument("--text-file", default="")
    source.add_argument("--structured-json", default="")

    workflow = parser.add_argument_group("Workflow")
    workflow.add_argument("--product-name", default="")
    workflow.add_argument("--audience", default="")
    workflow.add_argument("--pain-points", default="")
    workflow.add_argument("--value-proposition", default="")
    workflow.add_argument("--pricing", default="")
    workflow.add_argument("--goal", default="leads", choices=["traffic", "leads", "sales", "seo", "brand", "github_stars"])
    workflow.add_argument("--language", default="zh-CN")
    workflow.add_argument("--platforms", default=DEFAULT_PLATFORMS)
    workflow.add_argument("--competitor-query", default="")
    workflow.add_argument("--top-n", type=int, default=10)
    workflow.add_argument("--live-official-competitors", action="store_true")
    workflow.add_argument("--collector-platforms", default="youtube,github")
    workflow.add_argument("--auto-search-competitors", action="store_true")
    workflow.add_argument("--search-snapshot-dir", default="")
    workflow.add_argument("--search-html-snapshot-dir", default="")
    workflow.add_argument("--run-creator-follow-up", action="store_true")
    workflow.add_argument("--creator-follow-up-dry-run", action="store_true")
    workflow.add_argument("--run-follow-up-captures", action="store_true")
    workflow.add_argument("--follow-up-dry-run", action="store_true")
    workflow.add_argument("--capture-browser-assisted-follow-ups", action="store_true", help="Attempt browser-visible snapshots for queued Zhihu/Xiaohongshu/Douyin/TikTok follow-up capture tasks.")
    workflow.add_argument("--sample-video-frames", action="store_true", help="Sample browser-visible video evidence during follow-up captures.")
    workflow.add_argument("--video-sample-count", type=int, default=5)
    workflow.add_argument("--skip-video", action="store_true")
    workflow.add_argument("--video-platforms", default="auto")
    workflow.add_argument("--generate-voiceover", action="store_true")
    workflow.add_argument("--install-browser-if-missing", action="store_true")

    publish = parser.add_argument_group("Publish")
    publish.add_argument("--skip-publish-queue", action="store_true")
    publish.add_argument("--publish-platforms", default="", help="Comma-separated platform filter for publish_queue.py.")
    publish.add_argument("--execute-publish", action="store_true", help="Pass --execute to publish_queue.py. Official writes still require approval and credentials.")
    publish.add_argument("--approval", default="", help=f"Must equal {APPROVAL_PHRASE} when --execute-publish is used.")
    publish.add_argument("--github-repo", default="", help="owner/repo target for GitHub publishing.")
    publish.add_argument("--github-action", default="file", choices=["file", "issue", "release"])
    publish.add_argument("--github-path", default="PROMOTION.md")
    publish.add_argument("--github-branch", default="")
    publish.add_argument("--github-tag-name", default="")
    publish.add_argument("--youtube-video-file", default="")
    publish.add_argument("--youtube-privacy-status", default="private", choices=["private", "public", "unlisted"])
    publish.add_argument("--youtube-category-id", default="22")
    publish.add_argument("--douyin-video-file", default="")

    metrics = parser.add_argument_group("Metrics")
    metrics.add_argument("--skip-metrics-recovery", action="store_true")
    metrics.add_argument("--published-url", action="append", default=[], help="Real published URL, optionally as platform=url.")
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
    metrics.add_argument("--run-post-publish-metrics-capture", action="store_true")
    metrics.add_argument("--post-publish-metrics-limit", type=int, default=20)
    metrics.add_argument("--post-publish-metrics-allow-localhost", action="store_true")
    metrics.add_argument("--post-publish-metrics-capture-browser-assisted", action="store_true")
    metrics.add_argument("--post-publish-metrics-install-browser-if-missing", action="store_true")
    metrics.add_argument("--run-comment-evidence-capture", action="store_true")
    metrics.add_argument("--comment-evidence-limit", type=int, default=20)
    metrics.add_argument("--comment-evidence-platform", default="")
    metrics.add_argument("--comment-evidence-structured-json", default="")
    metrics.add_argument("--comment-evidence-html-file", default="")
    metrics.add_argument("--comment-evidence-text-file", default="")
    metrics.add_argument("--comment-evidence-allow-localhost", action="store_true")
    metrics.add_argument("--comment-evidence-capture-browser-assisted", action="store_true")
    metrics.add_argument("--comment-evidence-install-browser-if-missing", action="store_true")
    metrics.add_argument("--run-business-attribution", action="store_true")
    metrics.add_argument("--run-next-round-optimization", action="store_true")

    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def prepare_workflow(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    if args.workflow_manifest:
        manifest_path = Path(args.workflow_manifest)
        status = "ready" if manifest_path.exists() else "missing"
        workflow_out_dir = infer_workflow_out_dir(manifest_path, out_dir)
        return {"status": status, "manifest": str(manifest_path), "outDir": str(workflow_out_dir), "source": "existing_manifest"}

    command = build_workflow_command(args, out_dir)
    step = run_command("run_promotion_workflow", command)
    steps.append(step)
    manifest_path = out_dir / "reports/promotion-manager/agent-run/workflow-manifest.json"
    status = "ready" if step["exitCode"] == 0 and manifest_path.exists() else "error"
    return {"status": status, "manifest": str(manifest_path), "outDir": str(out_dir), "source": "generated_workflow", "exitCode": step["exitCode"]}


def build_workflow_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    command = [sys.executable, str(RUN_WORKFLOW)]
    for flag, value in [
        ("--browser-url", args.browser_url),
        ("--product-url", args.product_url),
        ("--html-file", args.html_file),
        ("--text-file", args.text_file),
        ("--structured-json", args.structured_json),
    ]:
        if value:
            command.extend([flag, value])
            break
    append_if_present(command, "--product-name", args.product_name)
    append_if_present(command, "--audience", args.audience)
    append_if_present(command, "--pain-points", args.pain_points)
    append_if_present(command, "--value-proposition", args.value_proposition)
    append_if_present(command, "--pricing", args.pricing)
    append_if_present(command, "--competitor-query", args.competitor_query)
    command.extend(["--goal", args.goal, "--language", args.language, "--platforms", args.platforms, "--top-n", str(args.top_n)])
    if args.live_official_competitors:
        command.append("--live-official-competitors")
    append_if_present(command, "--collector-platforms", args.collector_platforms)
    if args.auto_search_competitors:
        command.append("--auto-search-competitors")
    append_if_present(command, "--search-snapshot-dir", args.search_snapshot_dir)
    append_if_present(command, "--search-html-snapshot-dir", args.search_html_snapshot_dir)
    if args.run_creator_follow_up:
        command.append("--run-creator-follow-up")
    if args.creator_follow_up_dry_run:
        command.append("--creator-follow-up-dry-run")
    if args.run_follow_up_captures:
        command.append("--run-follow-up-captures")
    if args.follow_up_dry_run:
        command.append("--follow-up-dry-run")
    if args.capture_browser_assisted_follow_ups:
        command.append("--capture-browser-assisted-follow-ups")
    if args.sample_video_frames:
        command.append("--sample-video-frames")
        command.extend(["--video-sample-count", str(args.video_sample_count)])
    if args.skip_video:
        command.append("--skip-video")
    append_if_present(command, "--video-platforms", args.video_platforms)
    if args.generate_voiceover:
        command.append("--generate-voiceover")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    command.extend(["--out-dir", str(out_dir)])
    return command


def run_publish_queue(args: argparse.Namespace, out_dir: Path, workflow: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    if args.skip_publish_queue:
        return {"status": "skipped", "reason": "--skip-publish-queue was supplied."}
    manifest_path = Path(str(workflow.get("manifest", "")))
    if workflow.get("status") != "ready" or not manifest_path.exists():
        return {"status": "blocked", "reason": "Workflow manifest is required before building a publish queue."}
    workflow_out_dir = Path(str(workflow.get("outDir") or out_dir))
    command = [
        sys.executable,
        str(PUBLISH_QUEUE),
        "--workflow-manifest",
        str(manifest_path),
        "--promotion-out-dir",
        str(workflow_out_dir),
        "--out-dir",
        str(out_dir),
    ]
    append_if_present(command, "--platforms", args.publish_platforms)
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
    summary = read_summary(queue_path)
    return {
        "status": "ready" if step["exitCode"] == 0 and queue_path.exists() else "error",
        "queue": str(queue_path),
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def run_published_items(args: argparse.Namespace, out_dir: Path, publish: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    manual_items_path = write_manual_published_items(out_dir, args.published_url)
    queue_path = existing_path(publish.get("queue", ""))
    if not queue_path and not manual_items_path:
        return {"status": "skipped", "reason": "No publish queue or real published URLs were available."}
    command = [sys.executable, str(PUBLISHED_ITEMS), "--out-dir", str(out_dir)]
    if queue_path:
        command.extend(["--publish-queue", str(queue_path)])
    if manual_items_path:
        command.extend(["--published-items-json", str(manual_items_path)])
    step = run_command("published_items", command)
    steps.append(step)
    items_path = out_dir / "reports/promotion-manager/published-items/published-items.json"
    summary = read_summary(items_path)
    return {
        "status": "ready" if step["exitCode"] == 0 and items_path.exists() else "error",
        "publishedItems": str(items_path),
        "manualInput": str(manual_items_path) if manual_items_path else "",
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def run_post_publish_metrics_capture(args: argparse.Namespace, out_dir: Path, published: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not args.run_post_publish_metrics_capture:
        return {"status": "skipped", "reason": "--run-post-publish-metrics-capture was not supplied."}
    command = [
        sys.executable,
        str(POST_PUBLISH_METRICS_CAPTURE),
        "--out-dir",
        str(out_dir),
        "--limit",
        str(args.post_publish_metrics_limit),
    ]
    items_path = existing_path(published.get("publishedItems", ""))
    if items_path:
        command.extend(["--published-items-json", str(items_path)])
    append_published_urls(command, args.published_url)
    if args.post_publish_metrics_allow_localhost:
        command.append("--allow-localhost")
    if args.post_publish_metrics_capture_browser_assisted:
        command.append("--capture-browser-assisted")
    if args.post_publish_metrics_install_browser_if_missing:
        command.append("--install-browser-if-missing")
    step = run_command("post_publish_metrics_capture", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json"
    export_path = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json"
    summary = read_summary(report_path)
    return {
        "status": "ready" if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path),
        "metricExport": str(export_path) if export_path.exists() else "",
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def run_comment_evidence_capture(args: argparse.Namespace, out_dir: Path, published: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not args.run_comment_evidence_capture:
        return {"status": "skipped", "reason": "--run-comment-evidence-capture was not supplied."}
    command = [
        sys.executable,
        str(COMMENT_EVIDENCE_CAPTURE),
        "--out-dir",
        str(out_dir),
        "--limit",
        str(args.comment_evidence_limit),
    ]
    items_path = existing_path(published.get("publishedItems", ""))
    if items_path:
        command.extend(["--published-items-json", str(items_path)])
    append_published_urls(command, args.published_url)
    append_if_present(command, "--platform", args.comment_evidence_platform)
    append_if_present(command, "--structured-json", args.comment_evidence_structured_json)
    append_if_present(command, "--html-file", args.comment_evidence_html_file)
    append_if_present(command, "--text-file", args.comment_evidence_text_file)
    if args.comment_evidence_allow_localhost:
        command.append("--allow-localhost")
    if args.comment_evidence_capture_browser_assisted:
        command.append("--capture-browser-assisted")
    if args.comment_evidence_install_browser_if_missing:
        command.append("--install-browser-if-missing")
    step = run_command("comment_evidence_capture", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"
    export_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json"
    summary = read_summary(report_path)
    return {
        "status": "ready" if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path),
        "commentEvidenceExport": str(export_path) if export_path.exists() else "",
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def run_business_attribution(args: argparse.Namespace, out_dir: Path, published: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not args.run_business_attribution:
        return {"status": "skipped", "reason": "--run-business-attribution was not supplied."}
    command = [sys.executable, str(BUSINESS_ATTRIBUTION), "--out-dir", str(out_dir)]
    append_many(command, "--business-csv", args.business_csv)
    append_many(command, "--business-xlsx", args.business_xlsx)
    append_many(command, "--business-json", args.business_json)
    items_path = existing_path(published.get("publishedItems", ""))
    if items_path:
        command.extend(["--published-items-json", str(items_path)])
    append_published_urls(command, args.published_url)
    step = run_command("business_attribution", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"
    export_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json"
    summary = read_summary(report_path)
    return {
        "status": "ready" if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path),
        "businessAttributionExport": str(export_path) if export_path.exists() else "",
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def run_metrics_recovery(
    args: argparse.Namespace,
    out_dir: Path,
    workflow: dict[str, Any],
    publish: dict[str, Any],
    published: dict[str, Any],
    post_publish_metrics: dict[str, Any],
    business_attribution: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    if args.skip_metrics_recovery:
        return {"status": "skipped", "reason": "--skip-metrics-recovery was supplied."}
    manifest_path = Path(str(workflow.get("manifest", "")))
    command = [sys.executable, str(METRICS_RECOVERY), "--out-dir", str(out_dir)]
    if manifest_path.exists():
        command.extend(["--workflow-manifest", str(manifest_path)])
    queue_path = existing_path(publish.get("queue", ""))
    if queue_path:
        command.extend(["--publish-queue", str(queue_path)])
    items_path = existing_path(published.get("publishedItems", ""))
    if items_path:
        command.extend(["--published-items-json", str(items_path)])
    for value in args.published_url:
        _, url = parse_published_url(value)
        command.extend(["--published-url", url])
    append_many(command, "--github-repo", args.metrics_github_repo)
    append_many(command, "--youtube-video-id", args.metrics_youtube_video_id)
    append_many(command, "--metrics-csv", args.metrics_csv)
    append_many(command, "--metrics-xlsx", args.metrics_xlsx)
    append_many(command, "--metrics-json", args.metrics_json)
    append_many(command, "--metrics-text", args.metrics_text)
    append_many(command, "--metrics-structured-json", args.metrics_structured_json)
    metric_export = post_publish_metrics.get("metricExport", "")
    if metric_export:
        command.extend(["--metrics-json", str(metric_export)])
    attribution_export = business_attribution.get("businessAttributionExport", "")
    if attribution_export:
        command.extend(["--business-json", str(attribution_export)])
    else:
        append_many(command, "--business-csv", args.business_csv)
        append_many(command, "--business-xlsx", args.business_xlsx)
        append_many(command, "--business-json", args.business_json)
    append_many(command, "--business-text", args.business_text)
    step = run_command("metrics_recovery", command)
    steps.append(step)
    recovery_path = out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"
    summary = metrics_summary(recovery_path)
    return {
        "status": "ready" if step["exitCode"] == 0 and recovery_path.exists() else "error",
        "metricsRecovery": str(recovery_path),
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def run_next_round_optimization(
    args: argparse.Namespace,
    out_dir: Path,
    workflow: dict[str, Any],
    publish: dict[str, Any],
    comment_evidence: dict[str, Any],
    business_attribution: dict[str, Any],
    metrics: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    if not args.run_next_round_optimization:
        return {"status": "skipped", "reason": "--run-next-round-optimization was not supplied."}
    command = [sys.executable, str(NEXT_ROUND_OPTIMIZER), "--out-dir", str(out_dir)]
    manifest_path = existing_path(workflow.get("manifest", ""))
    if manifest_path:
        command.extend(["--workflow-manifest", str(manifest_path)])
    queue_path = existing_path(publish.get("queue", ""))
    if queue_path:
        command.extend(["--publish-queue", str(queue_path)])
    metrics_path = existing_path(metrics.get("metricsRecovery", ""))
    if metrics_path:
        command.extend(["--metrics-recovery-json", str(metrics_path)])
    comment_export = existing_path(comment_evidence.get("commentEvidenceExport", ""))
    if comment_export:
        command.extend(["--comment-evidence-json", str(comment_export)])
    elif existing_path(comment_evidence.get("report", "")):
        command.extend(["--comment-evidence-json", str(comment_evidence["report"])])
    business_report = existing_path(business_attribution.get("report", ""))
    if business_report:
        command.extend(["--business-attribution-json", str(business_report)])
    step = run_command("next_round_optimizer", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/optimization/next-round-optimization.json"
    summary = optimization_summary(report_path)
    return {
        "status": summary.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path),
        "exitCode": step["exitCode"],
        "summary": summary,
    }


def build_cycle_report(
    args: argparse.Namespace,
    out_dir: Path,
    workflow: dict[str, Any],
    publish: dict[str, Any],
    published: dict[str, Any],
    post_publish_metrics: dict[str, Any],
    comment_evidence: dict[str, Any],
    business_attribution: dict[str, Any],
    metrics: dict[str, Any],
    next_round_optimization: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "outDir": str(out_dir),
        "workflow": workflow,
        "publishQueue": publish,
        "publishedItems": published,
        "postPublishMetricsCapture": post_publish_metrics,
        "commentEvidenceCapture": comment_evidence,
        "businessAttribution": business_attribution,
        "metricsRecovery": metrics,
        "nextRoundOptimization": next_round_optimization,
        "automationStatus": cycle_status(workflow, publish, published, post_publish_metrics, comment_evidence, business_attribution, metrics, next_round_optimization),
        "approval": {
            "approvalPhrase": APPROVAL_PHRASE,
            "publishExecutionRequested": args.execute_publish,
            "approvalProvided": args.approval == APPROVAL_PHRASE,
        },
        "guardrails": [
            "Official API writes require --execute-publish, the exact approval phrase, and environment credentials.",
            "Dry-runs, blocked writes, queued manual tasks, and browser-assisted tasks are not treated as published.",
            "Metrics recovery uses official/public connectors and user-provided exports only.",
            "Next-round optimization uses recovered evidence only and waits when real data is missing.",
            "Do not bypass login, captcha, risk controls, platform review, or account verification.",
            "Do not fabricate views, likes, comments, orders, revenue, published URLs, or platform IDs.",
        ],
        "steps": steps,
    }


def cycle_status(
    workflow: dict[str, Any],
    publish: dict[str, Any],
    published: dict[str, Any],
    post_publish_metrics: dict[str, Any],
    comment_evidence: dict[str, Any],
    business_attribution: dict[str, Any],
    metrics: dict[str, Any],
    next_round_optimization: dict[str, Any],
) -> str:
    if workflow.get("status") != "ready":
        return "workflow_failed"
    if publish.get("status") not in {"ready", "skipped"}:
        return "publish_queue_failed"
    if published.get("status") not in {"ready", "skipped"}:
        return "published_items_failed"
    if post_publish_metrics.get("status") not in {"ready", "skipped"}:
        return "post_publish_metrics_capture_failed"
    if comment_evidence.get("status") not in {"ready", "skipped"}:
        return "comment_evidence_capture_failed"
    if business_attribution.get("status") not in {"ready", "skipped"}:
        return "business_attribution_failed"
    if metrics.get("status") not in {"ready", "skipped"}:
        return "metrics_recovery_failed"
    if next_round_optimization.get("status") not in {"ready", "partial_ready", "waiting_real_data", "skipped"}:
        return "next_round_optimization_failed"
    if metrics.get("status") == "skipped":
        return "ready_waiting_real_data"
    recovery_status = (metrics.get("summary") or {}).get("recoveryStatus", "")
    if recovery_status == "ready":
        return "ready_with_real_metrics"
    if recovery_status == "partial_ready":
        return "partial_ready_with_real_metrics"
    return "ready_waiting_real_data"


def write_cycle_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = cycle_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "promotion-cycle.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "promotion-cycle.md").write_text(render_cycle_markdown(report) + "\n", encoding="utf-8")


def render_cycle_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Promotion Cycle",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['automationStatus']}`",
        f"- Output: {report['outDir']}",
        "",
        "## Workflow",
        f"- Status: `{report['workflow'].get('status', '')}`",
        f"- Manifest: {report['workflow'].get('manifest', '')}",
        "",
        "## Publish Queue",
        f"- Status: `{report['publishQueue'].get('status', '')}`",
        f"- Queue: {report['publishQueue'].get('queue', '')}",
        f"- Summary: {report['publishQueue'].get('summary', {})}",
        "",
        "## Published Items",
        f"- Status: `{report['publishedItems'].get('status', '')}`",
        f"- Report: {report['publishedItems'].get('publishedItems', '')}",
        f"- Summary: {report['publishedItems'].get('summary', {})}",
        "",
        "## Post-Publish Metrics Capture",
        f"- Status: `{report['postPublishMetricsCapture'].get('status', '')}`",
        f"- Report: {report['postPublishMetricsCapture'].get('report', '')}",
        f"- Summary: {report['postPublishMetricsCapture'].get('summary', {})}",
        "",
        "## Comment Evidence Capture",
        f"- Status: `{report['commentEvidenceCapture'].get('status', '')}`",
        f"- Report: {report['commentEvidenceCapture'].get('report', '')}",
        f"- Summary: {report['commentEvidenceCapture'].get('summary', {})}",
        "",
        "## Business Attribution",
        f"- Status: `{report['businessAttribution'].get('status', '')}`",
        f"- Report: {report['businessAttribution'].get('report', '')}",
        f"- Summary: {report['businessAttribution'].get('summary', {})}",
        "",
        "## Metrics Recovery",
        f"- Status: `{report['metricsRecovery'].get('status', '')}`",
        f"- Report: {report['metricsRecovery'].get('metricsRecovery', '')}",
        f"- Summary: {report['metricsRecovery'].get('summary', {})}",
        "",
        "## Next-Round Optimization",
        f"- Status: `{report['nextRoundOptimization'].get('status', '')}`",
        f"- Report: {report['nextRoundOptimization'].get('report', '')}",
        f"- Summary: {report['nextRoundOptimization'].get('summary', {})}",
        "",
        "## Guardrails",
    ]
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def write_manual_published_items(out_dir: Path, values: list[str]) -> Path | None:
    records = []
    for value in values:
        platform, url = parse_published_url(value)
        records.append({"platform": platform, "publishedUrl": url, "title": "", "evidence": [url]})
    if not records:
        return None
    path = cycle_dir(out_dir) / "manual-published-items-input.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_published_url(value: str) -> tuple[str, str]:
    if "=" in value:
        platform, url = value.split("=", 1)
        return platform.strip(), url.strip()
    url = value.strip()
    return metrics_intake.choose_platform("auto", url), url


def infer_workflow_out_dir(manifest_path: Path, fallback: Path) -> Path:
    parts = manifest_path.parts
    if len(parts) >= 4 and parts[-4:] == ("reports", "promotion-manager", "agent-run", "workflow-manifest.json"):
        return manifest_path.parents[3]
    return fallback


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "name": name,
        "command": display_command(command),
        "exitCode": result.returncode,
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }


def read_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return data.get("summary", {}) if isinstance(data, dict) else {}


def metrics_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    coverage = report.get("coverage") or {}
    return {
        "recoveryStatus": report.get("recoveryStatus", ""),
        "retrospectiveStatus": (report.get("retrospective") or {}).get("status", ""),
        "recordsWithMetrics": coverage.get("recordsWithMetrics", 0),
        "manualOrPendingRequirements": coverage.get("manualOrPendingRequirements", 0),
        "metricFields": coverage.get("metricFields", []),
        "metricFieldCounts": coverage.get("metricFieldCounts", {}),
        "totals": coverage.get("totals", {}),
    }


def optimization_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    coverage = report.get("evidenceCoverage") or {}
    return {
        "status": report.get("status", ""),
        "metricRecords": coverage.get("metricRecords", 0),
        "commentCount": coverage.get("commentCount", 0),
        "businessAttributions": coverage.get("businessAttributions", 0),
        "nextRoundContent": len(report.get("nextRoundContent", [])),
        "manualOrPendingRequirements": coverage.get("manualOrPendingRequirements", 0),
    }


def cycle_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/cycle"


def append_if_present(command: list[str], flag: str, value: str) -> None:
    if value:
        command.extend([flag, value])


def append_many(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        if value:
            command.extend([flag, value])


def existing_path(value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.exists() else None


def append_published_urls(command: list[str], values: list[str]) -> None:
    for value in values:
        if value:
            command.extend(["--published-url", value])


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
