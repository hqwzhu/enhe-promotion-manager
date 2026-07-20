#!/usr/bin/env python3
"""Run multiple product URLs through Codex-first intake and promotion cycles."""

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
PRODUCT_URL_DISCOVERY = SCRIPTS / "product_url_discovery.py"
PRODUCT_URL_READER = SCRIPTS / "product_url_reader.py"
PROMOTION_CYCLE_RUNNER = SCRIPTS / "promotion_cycle_runner.py"
MULTI_QUERY_VIRAL_DISCOVERY = SCRIPTS / "multi_query_viral_discovery.py"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    discovery = run_product_url_discovery(args, out_dir, steps)
    reader = run_product_url_reader(args, out_dir, steps, discovery)
    runs = run_promotion_cycles(args, out_dir, reader, steps)
    attach_multi_query_viral_discovery(args, runs, steps)
    report = build_report(args, out_dir, discovery, reader, runs, steps)
    write_report(out_dir, report)
    print(f"Product batch runner report written to: {(batch_dir(out_dir) / 'product-batch-runner.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read product URLs first, then run one promotion cycle per ready product.")
    parser.add_argument("--url", action="append", default=[], help="Product URL. Can be repeated.")
    parser.add_argument("--urls-file", default="", help="Text file with one product URL per line.")
    parser.add_argument("--out-dir", default="./promotion-output")

    discovery = parser.add_argument_group("Product URL discovery")
    discovery.add_argument("--discover-from-url", default="", help="Public website or landing page URL to discover product URLs from before reading products.")
    discovery.add_argument("--discovery-html-file", default="", help="Saved public website HTML to discover product URLs from.")
    discovery.add_argument("--discovery-sitemap-url", default="", help="Public sitemap.xml or sitemap index URL to discover product URLs from.")
    discovery.add_argument("--discovery-sitemap-file", default="", help="Saved sitemap.xml, sitemap index, or .xml.gz file to discover product URLs from.")
    discovery.add_argument("--discovery-base-url", default="", help="Base URL for resolving links in --discovery-html-file.")
    discovery.add_argument("--discovery-top-n", type=int, default=50)
    discovery.add_argument("--discovery-min-score", type=float, default=3.0)
    discovery.add_argument("--discovery-max-pages", type=int, default=20)
    discovery.add_argument("--discovery-max-depth", type=int, default=1)
    discovery.add_argument("--discovery-max-sitemap-urls", type=int, default=1000)
    discovery.add_argument("--discovery-timeout", type=float, default=20.0)
    discovery.add_argument("--discovery-include-external", action="store_true")
    discovery.add_argument("--discovery-skip-sitemaps", action="store_true")
    discovery.add_argument("--discovery-allow-localhost", action="store_true")

    reader = parser.add_argument_group("Codex/browser URL reading")
    reader.add_argument("--skip-browser", action="store_true")
    reader.add_argument("--no-static-fallback", action="store_true")
    reader.add_argument("--install-browser-if-missing", action="store_true")
    reader.add_argument("--timeout-ms", type=int, default=30000)
    reader.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    reader.add_argument("--screenshot", action="store_true")
    reader.add_argument("--disable-web-text-fallback", action="store_true")
    reader.add_argument("--web-text-fallback-url-template", default="")
    reader.add_argument("--web-text-fallback-file", default="")

    workflow = parser.add_argument_group("Promotion cycle")
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
    workflow.add_argument("--capture-browser-assisted-follow-ups", action="store_true", help="Attempt browser-visible snapshots for queued browser-assisted platform follow-up tasks in each product cycle.")
    workflow.add_argument("--sample-video-frames", action="store_true", help="Sample browser-visible video evidence during each product cycle follow-up capture.")
    workflow.add_argument("--video-sample-count", type=int, default=5)
    workflow.add_argument("--skip-video", action="store_true")
    workflow.add_argument("--video-platforms", default="auto")
    workflow.add_argument("--generate-voiceover", action="store_true")

    discovery = parser.add_argument_group("Multi-query viral discovery")
    discovery.add_argument("--run-multi-query-viral-discovery", action="store_true")
    discovery.add_argument("--multi-query-dry-run", action="store_true")
    discovery.add_argument("--multi-query-query", action="append", default=[])
    discovery.add_argument("--multi-query-query-count", type=int, default=5)
    discovery.add_argument("--multi-query-platforms", default="", help="Defaults to --platforms.")
    discovery.add_argument("--multi-query-top-n", type=int, default=20)
    discovery.add_argument("--multi-query-html-snapshot-root", default="")
    discovery.add_argument("--multi-query-browser-search-timeout-ms", type=int, default=30000)
    discovery.add_argument(
        "--multi-query-browser-search-wait-until",
        default="networkidle",
        choices=["load", "domcontentloaded", "networkidle"],
    )
    discovery.add_argument("--multi-query-live-official", action="store_true")
    discovery.add_argument("--multi-query-run-creator-follow-up", action="store_true")
    discovery.add_argument("--multi-query-creator-follow-up-dry-run", action="store_true")
    discovery.add_argument("--multi-query-run-follow-up-captures", action="store_true")
    discovery.add_argument("--multi-query-follow-up-dry-run", action="store_true")
    discovery.add_argument("--multi-query-capture-browser-assisted-follow-ups", action="store_true")
    discovery.add_argument("--multi-query-sample-video-frames", action="store_true")
    discovery.add_argument("--multi-query-video-sample-count", type=int, default=5)

    publish = parser.add_argument_group("Publish queue")
    publish.add_argument("--skip-publish-queue", action="store_true")
    publish.add_argument("--publish-platforms", default="")
    publish.add_argument("--github-repo", default="")
    publish.add_argument("--github-path", default="PROMOTION.md")
    publish.add_argument("--youtube-video-file", default="")
    publish.add_argument("--douyin-video-file", default="")

    metrics = parser.add_argument_group("Metrics recovery")
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
    return parser.parse_args()


def run_product_url_discovery(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not args.discover_from_url and not args.discovery_html_file and not args.discovery_sitemap_url and not args.discovery_sitemap_file:
        return {"status": "skipped", "reason": "No product URL discovery source was supplied."}
    command = [sys.executable, str(PRODUCT_URL_DISCOVERY), "--out-dir", str(out_dir)]
    append_if_present(command, "--site-url", args.discover_from_url)
    append_if_present(command, "--html-file", args.discovery_html_file)
    append_if_present(command, "--sitemap-url", args.discovery_sitemap_url)
    append_if_present(command, "--sitemap-file", args.discovery_sitemap_file)
    append_if_present(command, "--base-url", args.discovery_base_url)
    command.extend(
        [
            "--top-n",
            str(args.discovery_top_n),
            "--min-score",
            str(args.discovery_min_score),
            "--max-pages",
            str(args.discovery_max_pages),
            "--max-depth",
            str(args.discovery_max_depth),
            "--max-sitemap-urls",
            str(args.discovery_max_sitemap_urls),
            "--timeout",
            str(args.discovery_timeout),
        ]
    )
    if args.discovery_include_external:
        command.append("--include-external")
    if args.discovery_skip_sitemaps:
        command.append("--skip-sitemaps")
    if args.discovery_allow_localhost:
        command.append("--allow-localhost")
    step = run_command("product_url_discovery", command, check=False)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/intake/product-url-discovery.json"
    report = read_json(report_path)
    report["_path"] = str(report_path) if report_path.exists() else ""
    report["_step"] = step
    return report if report else {"status": "error", "reason": "Product URL discovery did not create a report.", "_step": step}


def run_product_url_reader(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    command = [sys.executable, str(PRODUCT_URL_READER), "--out-dir", str(out_dir)]
    for url in args.url:
        command.extend(["--url", url])
    for url in discovery.get("selectedUrls", []) if isinstance(discovery.get("selectedUrls"), list) else []:
        command.extend(["--url", str(url)])
    append_if_present(command, "--urls-file", args.urls_file)
    if args.skip_browser:
        command.append("--skip-browser")
    if args.no_static_fallback:
        command.append("--no-static-fallback")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    command.extend(["--timeout-ms", str(args.timeout_ms), "--wait-until", args.wait_until])
    if args.screenshot:
        command.append("--screenshot")
    if args.disable_web_text_fallback:
        command.append("--disable-web-text-fallback")
    append_if_present(command, "--web-text-fallback-url-template", args.web_text_fallback_url_template)
    append_if_present(command, "--web-text-fallback-file", args.web_text_fallback_file)

    step = run_command("product_url_reader", command)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/intake/product-url-reader.json"
    if not report_path.exists():
        raise SystemExit(f"Product URL reader did not create {report_path}")
    report = read_json(report_path)
    report["_path"] = str(report_path)
    return report


def run_promotion_cycles(
    args: argparse.Namespace,
    out_dir: Path,
    reader: dict[str, Any],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    runs = []
    for index, record in enumerate(reader.get("records", []), start=1):
        source = workflow_source(record)
        run_dir = out_dir / "product-batch-runs" / f"{index:03d}-{safe_id(record.get('id', 'product'))}"
        if not source:
            runs.append(blocked_run(record, run_dir, "No ready product profile or usable workflow source was available."))
            continue

        command = build_cycle_command(args, record, source, run_dir)
        step = run_command(f"promotion_cycle_{record.get('id', index)}", command, check=False)
        steps.append(step)
        runs.append(summarize_cycle_run(record, run_dir, source, step))
    return runs


def workflow_source(record: dict[str, Any]) -> dict[str, Any] | None:
    if (record.get("intake") or {}).get("status") not in {"ready", "partial_ready"}:
        return None
    snapshot = Path(str((record.get("browser") or {}).get("snapshot", "")))
    if record.get("sourceMode") == "browser_structured_snapshot" and snapshot.exists():
        return {"flag": "--structured-json", "value": str(snapshot), "sourceMode": "browser_structured_snapshot"}
    text_file = Path(str((record.get("webText") or {}).get("textFile", "")))
    if record.get("sourceMode") == "web_text_fallback" and text_file.exists():
        return {"flag": "--text-file", "value": str(text_file), "sourceMode": "web_text_fallback"}
    if record.get("sourceMode") == "cached_profile_fallback" and text_file.exists():
        return {"flag": "--text-file", "value": str(text_file), "sourceMode": "cached_profile_fallback"}
    url = str(record.get("url", "")).strip()
    if url:
        return {"flag": "--product-url", "value": url, "sourceMode": "static_url_fallback"}
    return None


def build_cycle_command(args: argparse.Namespace, record: dict[str, Any], source: dict[str, Any], run_dir: Path) -> list[str]:
    product = record.get("product") or {}
    command = [
        sys.executable,
        str(PROMOTION_CYCLE_RUNNER),
        source["flag"],
        source["value"],
        "--platforms",
        args.platforms,
        "--goal",
        args.goal,
        "--language",
        args.language,
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(run_dir),
    ]
    append_if_present(command, "--product-name", product.get("productName", ""))
    append_if_present(command, "--value-proposition", product.get("valueProposition", ""))
    append_if_present(command, "--pricing", product.get("pricing", ""))
    append_if_present(command, "--audience", join_list(product.get("targetAudienceAssumptions")))
    append_if_present(command, "--pain-points", join_list(product.get("painPointAssumptions")))
    append_if_present(command, "--competitor-query", args.competitor_query)
    if args.auto_search_competitors:
        command.append("--auto-search-competitors")
    if args.live_official_competitors:
        command.append("--live-official-competitors")
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

    if args.skip_publish_queue:
        command.append("--skip-publish-queue")
    append_if_present(command, "--publish-platforms", args.publish_platforms)
    append_if_present(command, "--github-repo", args.github_repo)
    append_if_present(command, "--github-path", args.github_path)
    append_if_present(command, "--youtube-video-file", args.youtube_video_file)
    append_if_present(command, "--douyin-video-file", args.douyin_video_file)

    if args.skip_metrics_recovery:
        command.append("--skip-metrics-recovery")
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
    if args.run_post_publish_metrics_capture:
        command.append("--run-post-publish-metrics-capture")
    command.extend(["--post-publish-metrics-limit", str(args.post_publish_metrics_limit)])
    if args.post_publish_metrics_allow_localhost:
        command.append("--post-publish-metrics-allow-localhost")
    if args.post_publish_metrics_capture_browser_assisted:
        command.append("--post-publish-metrics-capture-browser-assisted")
    if args.post_publish_metrics_install_browser_if_missing:
        command.append("--post-publish-metrics-install-browser-if-missing")
    if args.run_comment_evidence_capture:
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
    if args.run_business_attribution:
        command.append("--run-business-attribution")
    if args.run_next_round_optimization:
        command.append("--run-next-round-optimization")
    return command


def summarize_cycle_run(record: dict[str, Any], run_dir: Path, source: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    cycle_path = run_dir / "reports/promotion-manager/cycle/promotion-cycle.json"
    cycle = read_json(cycle_path)
    workflow_manifest = str((cycle.get("workflow") or {}).get("manifest") or run_dir / "reports/promotion-manager/agent-run/workflow-manifest.json")
    publish_queue = str((cycle.get("publishQueue") or {}).get("queue") or "")
    metrics_recovery = str((cycle.get("metricsRecovery") or {}).get("metricsRecovery") or "")
    next_round_optimization = summarize_next_round_optimization(cycle, run_dir)
    return {
        "id": record.get("id", ""),
        "url": record.get("url", ""),
        "status": cycle_run_status(step, cycle_path, cycle),
        "sourceMode": source["sourceMode"],
        "outputDir": str(run_dir),
        "cycleReport": str(cycle_path) if cycle_path.exists() else "",
        "workflowManifest": workflow_manifest if Path(workflow_manifest).exists() else "",
        "publishQueue": publish_queue if publish_queue and Path(publish_queue).exists() else "",
        "metricsRecovery": metrics_recovery if metrics_recovery and Path(metrics_recovery).exists() else "",
        "nextRoundOptimization": next_round_optimization,
        "automationStatus": cycle.get("automationStatus", ""),
        "product": record.get("product", {}),
        "command": step["command"],
        "exitCode": step["exitCode"],
        "stdoutTail": step["stdoutTail"],
        "stderrTail": step["stderrTail"],
        "multiQueryViralDiscovery": {"status": "skipped", "reason": "--run-multi-query-viral-discovery was not supplied."},
    }


def blocked_run(record: dict[str, Any], run_dir: Path, reason: str) -> dict[str, Any]:
    return {
        "id": record.get("id", ""),
        "url": record.get("url", ""),
        "status": "blocked",
        "sourceMode": record.get("sourceMode", "unavailable"),
        "outputDir": str(run_dir),
        "cycleReport": "",
        "workflowManifest": "",
        "publishQueue": "",
        "metricsRecovery": "",
        "automationStatus": "",
        "product": record.get("product", {}),
        "reason": reason,
        "command": [],
        "exitCode": None,
        "nextRoundOptimization": {"status": "skipped", "reason": "Promotion cycle was blocked."},
        "multiQueryViralDiscovery": {"status": "skipped", "reason": "Promotion cycle was blocked."},
    }


def cycle_run_status(step: dict[str, Any], cycle_path: Path, cycle: dict[str, Any]) -> str:
    if step["exitCode"] != 0 or not cycle_path.exists():
        return "error"
    automation_status = str(cycle.get("automationStatus", ""))
    if automation_status.endswith("_failed"):
        return "error"
    return "ready"


def summarize_next_round_optimization(cycle: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    item = cycle.get("nextRoundOptimization") if isinstance(cycle.get("nextRoundOptimization"), dict) else {}
    status = item.get("status", "skipped") if item else "skipped"
    report = str(item.get("report") or run_dir / "reports/promotion-manager/optimization/next-round-optimization.json")
    return {
        "status": status,
        "report": report if Path(report).exists() else "",
        "summary": item.get("summary", {}) if isinstance(item.get("summary"), dict) else {},
        "exitCode": item.get("exitCode"),
        "reason": item.get("reason", ""),
    }


def attach_multi_query_viral_discovery(args: argparse.Namespace, runs: list[dict[str, Any]], steps: list[dict[str, Any]]) -> None:
    if not args.run_multi_query_viral_discovery:
        return
    for run in runs:
        run["multiQueryViralDiscovery"] = run_multi_query_for_run(args, run, steps)


def run_multi_query_for_run(args: argparse.Namespace, run: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    manifest_path = Path(str(run.get("workflowManifest") or ""))
    run_dir = Path(str(run.get("outputDir") or ""))
    if run.get("status") != "ready" or not manifest_path.exists() or not run_dir:
        return {
            "status": "blocked",
            "reason": "A ready promotion cycle and workflow manifest are required before multi-query viral discovery.",
            "report": "",
            "mergedViralLibrary": "",
            "mergedCreatorLeaderboard": "",
            "command": [],
        }
    command = build_multi_query_command(args, manifest_path, run_dir)
    step = run_command(f"multi_query_viral_discovery_{run.get('id', 'product')}", command, check=False)
    steps.append(step)
    report_path = run_dir / "reports/promotion-manager/competitors/multi-query-viral-discovery.json"
    report = read_json(report_path)
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    return {
        "status": report.get("status", "error") if step["exitCode"] == 0 and report_path.exists() else "error",
        "report": str(report_path) if report_path.exists() else "",
        "mergedViralLibrary": str(artifacts.get("mergedViralLibrary", "")),
        "mergedCreatorLeaderboard": str(artifacts.get("mergedCreatorLeaderboard", "")),
        "summary": report.get("summary", {}),
        "command": step["command"],
        "exitCode": step["exitCode"],
        "stdoutTail": step["stdoutTail"],
        "stderrTail": step["stderrTail"],
    }


def build_multi_query_command(args: argparse.Namespace, manifest_path: Path, run_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(MULTI_QUERY_VIRAL_DISCOVERY),
        "--workflow-manifest",
        str(manifest_path),
        "--platforms",
        args.multi_query_platforms or args.platforms,
        "--top-n",
        str(args.multi_query_top_n),
        "--query-count",
        str(args.multi_query_query_count),
        "--out-dir",
        str(run_dir),
        "--browser-search-timeout-ms",
        str(args.multi_query_browser_search_timeout_ms),
        "--browser-search-wait-until",
        args.multi_query_browser_search_wait_until,
    ]
    append_many(command, "--query", args.multi_query_query)
    append_if_present(command, "--html-snapshot-root", args.multi_query_html_snapshot_root)
    if args.multi_query_dry_run:
        command.append("--dry-run")
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    if args.multi_query_live_official:
        command.append("--live-official")
    if args.multi_query_run_creator_follow_up:
        command.append("--run-creator-follow-up")
    if args.multi_query_creator_follow_up_dry_run:
        command.append("--creator-follow-up-dry-run")
    if args.multi_query_run_follow_up_captures:
        command.append("--run-follow-up-captures")
    if args.multi_query_follow_up_dry_run:
        command.append("--follow-up-dry-run")
    if args.multi_query_capture_browser_assisted_follow_ups:
        command.append("--capture-browser-assisted-follow-ups")
    if args.multi_query_sample_video_frames:
        command.append("--sample-video-frames")
        command.extend(["--video-sample-count", str(args.multi_query_video_sample_count)])
    return command


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    discovery: dict[str, Any],
    reader: dict[str, Any],
    runs: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    discovered_urls = discovery.get("selectedUrls", []) if isinstance(discovery.get("selectedUrls"), list) else []
    multi_query_totals = aggregate_multi_query_summaries(runs)
    summary = {
        "requestedUrls": (reader.get("summary") or {}).get("requestedUrls", len(reader.get("records", []))),
        "discoveredUrls": len(discovered_urls),
        "readyProductProfiles": sum(
            1 for item in reader.get("records", []) if (item.get("intake") or {}).get("status") in {"ready", "partial_ready"}
        ),
        "blockedProductProfiles": sum(
            1 for item in reader.get("records", []) if (item.get("intake") or {}).get("status") not in {"ready", "partial_ready"}
        ),
        "readyPromotionRuns": sum(1 for item in runs if item.get("status") == "ready"),
        "failedPromotionRuns": sum(1 for item in runs if item.get("status") == "error"),
        "blockedPromotionRuns": sum(1 for item in runs if item.get("status") == "blocked"),
        "browserStructuredRuns": sum(1 for item in runs if item.get("sourceMode") == "browser_structured_snapshot"),
        "staticFallbackRuns": sum(1 for item in runs if item.get("sourceMode") == "static_url_fallback"),
        "webTextFallbackRuns": sum(1 for item in runs if item.get("sourceMode") == "web_text_fallback"),
        "multiQueryDiscoveryRuns": sum(1 for item in runs if item.get("multiQueryViralDiscovery", {}).get("status") not in {"", "skipped", None}),
        "readyMultiQueryDiscoveryRuns": sum(1 for item in runs if item.get("multiQueryViralDiscovery", {}).get("status") == "ready"),
        "plannedMultiQueryDiscoveryRuns": sum(1 for item in runs if item.get("multiQueryViralDiscovery", {}).get("status") == "planned"),
        "failedMultiQueryDiscoveryRuns": sum(1 for item in runs if item.get("multiQueryViralDiscovery", {}).get("status") == "error"),
        "nextRoundOptimizationRuns": sum(1 for item in runs if item.get("nextRoundOptimization", {}).get("status") not in {"", "skipped", None}),
        "readyNextRoundOptimizationRuns": sum(1 for item in runs if item.get("nextRoundOptimization", {}).get("status") == "ready"),
        "partialReadyNextRoundOptimizationRuns": sum(1 for item in runs if item.get("nextRoundOptimization", {}).get("status") == "partial_ready"),
        "waitingRealDataNextRoundOptimizationRuns": sum(1 for item in runs if item.get("nextRoundOptimization", {}).get("status") == "waiting_real_data"),
        "failedNextRoundOptimizationRuns": sum(1 for item in runs if item.get("nextRoundOptimization", {}).get("status") in {"blocked", "error"}),
        **multi_query_totals,
    }
    return {
        "generatedAt": TODAY,
        "status": batch_status(runs),
        "outDir": str(out_dir),
        "readerReport": reader.get("_path", ""),
        "discoveryReport": discovery.get("_path", ""),
        "input": {
            "urls": args.url,
            "urlsFile": args.urls_file,
            "discoverFromUrl": args.discover_from_url,
            "discoveryHtmlFile": args.discovery_html_file,
            "discoverySitemapUrl": args.discovery_sitemap_url,
            "discoverySitemapFile": args.discovery_sitemap_file,
            "platforms": args.platforms,
            "codexReadFirst": True,
        },
        "summary": summary,
        "discoverySummary": discovery.get("summary", {}) if isinstance(discovery.get("summary"), dict) else {},
        "discoveredUrls": discovered_urls,
        "readerSummary": reader.get("summary", {}),
        "promotionRuns": runs,
        "guardrails": [
            "Each product URL is read by product_url_reader.py before a promotion cycle starts.",
            "Product URL discovery uses public HTML links only and produces candidates that still require product_url_reader.py evidence.",
            "Browser structured snapshots are passed to promotion_cycle_runner.py with --structured-json when available.",
            "Static URL intake is used only when browser capture is skipped or unavailable and fallback is allowed.",
            "Public web-reader text fallback is passed to promotion_cycle_runner.py with --text-file after browser/static intake failures.",
            "Multi-query viral discovery uses public/browser-visible platform evidence, official APIs, or dry-run query plans.",
            "Official publishing still requires explicit approval, credentials, and platform authorization.",
            "No login, captcha bypass, cookie extraction, hidden token storage, or fabricated metrics.",
        ],
        "steps": steps,
    }


def batch_status(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return "blocked"
    cycle_statuses = [item.get("status") for item in runs]
    multi_statuses = [item.get("multiQueryViralDiscovery", {}).get("status") for item in runs]
    next_statuses = [item.get("nextRoundOptimization", {}).get("status") for item in runs]
    failed_multi = any(status in {"blocked", "error"} for status in multi_statuses)
    failed_next = any(status in {"blocked", "error"} for status in next_statuses)
    partial_next = any(status in {"partial_ready", "waiting_real_data"} for status in next_statuses)
    if all(status == "ready" for status in cycle_statuses) and not failed_multi and not failed_next and not partial_next:
        return "ready"
    if any(status == "ready" for status in cycle_statuses):
        return "partial_ready"
    return "blocked"


def aggregate_multi_query_summaries(runs: list[dict[str, Any]]) -> dict[str, int]:
    summaries = [
        item.get("multiQueryViralDiscovery", {}).get("summary", {})
        for item in runs
        if isinstance(item.get("multiQueryViralDiscovery", {}).get("summary"), dict)
    ]
    return {
        "multiQuerySearchCapturesReady": sum_summary(summaries, "searchCapturesReady"),
        "multiQueryViralMaterialsObserved": sum_summary(summaries, "viralMaterialsObserved"),
        "multiQueryMergedMaterials": sum_summary(summaries, "mergedMaterials"),
        "multiQueryMergedCreators": sum_summary(summaries, "mergedCreators"),
        "multiQueryDeepEvidenceRuns": sum_summary(summaries, "deepEvidenceRuns"),
        "multiQueryFollowUpCaptureRuns": sum_summary(summaries, "followUpCaptureRuns"),
        "multiQueryFollowUpImportedRecords": sum_summary(summaries, "followUpImportedRecords"),
        "multiQueryBrowserVisibleCaptureReady": sum_summary(summaries, "followUpBrowserVisibleReady"),
        "multiQueryVideoSampleRuns": sum_summary(summaries, "videoSampleRuns"),
        "multiQueryVideoSampleReady": sum_summary(summaries, "videoSampleReady"),
        "multiQueryVideoSampleFrames": sum_summary(summaries, "videoSampleFrames"),
    }


def sum_summary(summaries: list[dict[str, Any]], key: str) -> int:
    return sum(int_value(item.get(key)) for item in summaries)


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = batch_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "product-batch-runner.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "product-batch-runner.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Product Batch Runner",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Requested URLs: {report['summary']['requestedUrls']}",
        f"- Ready product profiles: {report['summary']['readyProductProfiles']}",
        f"- Discovered URLs: {report['summary'].get('discoveredUrls', 0)}",
        f"- Ready promotion runs: {report['summary']['readyPromotionRuns']}",
        f"- Discovery report: {report.get('discoveryReport', '')}",
        f"- Reader report: {report['readerReport']}",
        "",
        "## Promotion Runs",
    ]
    for run in report["promotionRuns"]:
        product = run.get("product") or {}
        lines.extend(
            [
                "",
                f"### {run.get('id', '')}",
                f"- Product: {product.get('productName', 'unknown')}",
                f"- URL: {run.get('url', '')}",
                f"- Status: `{run.get('status', '')}`",
                f"- Source mode: `{run.get('sourceMode', '')}`",
                f"- Cycle: {run.get('cycleReport', '')}",
                f"- Workflow manifest: {run.get('workflowManifest', '')}",
                f"- Automation status: `{run.get('automationStatus', '')}`",
                f"- Next-round optimization: `{run.get('nextRoundOptimization', {}).get('status', 'skipped')}` {run.get('nextRoundOptimization', {}).get('report', '')}",
                f"- Multi-query discovery: `{run.get('multiQueryViralDiscovery', {}).get('status', 'skipped')}` {run.get('multiQueryViralDiscovery', {}).get('report', '')}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


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


def batch_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/batch"


def append_if_present(command: list[str], flag: str, value: Any) -> None:
    text = "" if value is None else str(value).strip()
    if text:
        command.extend([flag, text])


def append_many(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        append_if_present(command, flag, value)


def join_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value else ""


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.lower()).strip("-") or "product"


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
