#!/usr/bin/env python3
"""Run the Codex-local product promotion manager workflow end to end."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]
VIDEO_PLATFORMS = {"youtube", "xiaohongshu", "douyin", "tiktok"}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    profile = run_product_intake(args, out_dir, steps)
    product = product_from_profile(args, profile)
    run_promotion_manager(args, product, out_dir, steps)
    discovery = run_competitor_discovery(args, product, out_dir, steps)
    collections = run_competitor_collectors(args, product, out_dir, steps)
    browser_search = run_browser_search_snapshots(args, product, out_dir, steps)
    search_captures = run_search_captures(args, product, out_dir, steps, browser_search)
    viral_library = run_viral_content_library(args, out_dir, steps, search_captures)
    creator_leaderboard = run_creator_leaderboard(args, out_dir, steps, viral_library)
    creator_follow_up = run_creator_follow_up(args, out_dir, steps, creator_leaderboard)
    follow_up_captures = run_follow_up_captures(args, out_dir, steps, viral_library)
    competitor_informed = run_competitor_content_enhancer(args, product, out_dir, steps, viral_library, follow_up_captures, creator_follow_up)
    videos = render_video_artifacts(args, product, out_dir, steps)
    media_assets = run_media_asset_pack(args, product, out_dir, steps, videos)
    metrics = run_metrics_import(args, out_dir, steps)

    manifest = build_manifest(args, product, profile, discovery, collections, browser_search, search_captures, viral_library, creator_leaderboard, creator_follow_up, follow_up_captures, competitor_informed, videos, media_assets, metrics, steps, out_dir)
    write_manifest(out_dir, manifest)
    print(f"Promotion workflow manifest written to: {(agent_dir(out_dir) / 'workflow-manifest.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run product intake, competitor discovery, content generation, video rendering, and review outputs.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--browser-url", help="Public product URL to render with Playwright before intake.")
    source.add_argument("--product-url", help="Public product URL to fetch with static HTML metadata.")
    source.add_argument("--html-file", help="Saved product HTML file.")
    source.add_argument("--text-file", help="Rendered page text captured by Codex/browser tooling.")
    source.add_argument("--structured-json", help="Structured page snapshot captured by Codex/browser tooling.")

    parser.add_argument("--product-name", default="", help="Override extracted product name.")
    parser.add_argument("--audience", default="", help="Override extracted audience assumptions, comma-separated.")
    parser.add_argument("--pain-points", default="", help="Override extracted pain points, comma-separated.")
    parser.add_argument("--value-proposition", default="", help="Override extracted value proposition.")
    parser.add_argument("--pricing", default="", help="Override extracted pricing.")
    parser.add_argument("--goal", default="leads", choices=["traffic", "leads", "sales", "seo", "brand", "github_stars"])
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated target platforms.")
    parser.add_argument("--competitor-query", default="", help="Override competitor discovery query.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--live-official-competitors", action="store_true", help="Call official/public competitor connectors where credentials allow.")
    parser.add_argument("--collector-platforms", default="youtube,github", help="Comma-separated platforms for official/public competitor collectors.")
    parser.add_argument("--auto-search-competitors", action="store_true", help="Open public platform search pages and write structured search snapshots before capture.")
    parser.add_argument("--search-snapshot-dir", default="", help="Directory of rendered search snapshots named <platform>.json/.txt/.html to capture.")
    parser.add_argument("--search-html-snapshot-dir", default="", help="Optional directory of saved <platform>.html search pages for auto search snapshots.")
    parser.add_argument("--skip-viral-library", action="store_true", help="Skip ranked viral material library generation after search captures.")
    parser.add_argument("--skip-creator-leaderboard", action="store_true", help="Skip creator/account leaderboard generation after the viral material library is built.")
    parser.add_argument("--run-creator-follow-up", action="store_true", help="Run safe public creator/account follow-up research after the creator leaderboard is built.")
    parser.add_argument("--creator-follow-up-limit", type=int, default=20)
    parser.add_argument("--creator-follow-up-top-n", type=int, default=5)
    parser.add_argument("--creator-follow-up-dry-run", action="store_true", help="Plan creator follow-up research without fetching public APIs.")
    parser.add_argument("--run-follow-up-captures", action="store_true", help="Run safe public follow-up captures after the viral material library is built.")
    parser.add_argument("--follow-up-capture-limit", type=int, default=20)
    parser.add_argument("--follow-up-dry-run", action="store_true", help="Plan follow-up captures without fetching public URLs.")
    parser.add_argument("--allow-localhost-follow-up", action="store_true", help="Allow localhost follow-up URLs for local fixtures/tests only.")
    parser.add_argument("--sample-video-frames", action="store_true", help="Sample browser-visible video metadata and frame screenshots during follow-up captures.")
    parser.add_argument("--video-sample-count", type=int, default=5)
    parser.add_argument(
        "--capture-browser-assisted-follow-ups",
        action="store_true",
        help="Attempt browser-visible snapshots for queued Zhihu/Xiaohongshu/Douyin/TikTok follow-up capture tasks.",
    )
    parser.add_argument("--use-competitor-informed-content", action="store_true", help="Explicitly use viral/deep competitor libraries to rewrite generated content before video and publish packs. This is enabled automatically when a library exists.")
    parser.add_argument("--skip-competitor-informed-content", action="store_true", help="Skip rewriting generated content with competitor-informed patterns.")
    parser.add_argument("--skip-competitor-discovery", action="store_true")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Allow browser_snapshot.py to run python -m playwright install chromium when Chromium is missing.")

    parser.add_argument("--skip-video", action="store_true", help="Skip MP4 rendering.")
    parser.add_argument("--video-platforms", default="auto", help="Comma-separated platforms to render, or auto.")
    parser.add_argument("--generate-voiceover", action="store_true", help="Use Windows SAPI review voiceover when rendering videos.")

    metrics = parser.add_mutually_exclusive_group()
    metrics.add_argument("--metrics-csv", help="CSV export for real post-publish metrics.")
    metrics.add_argument("--metrics-xlsx", help="Excel .xlsx export for real post-publish metrics.")
    metrics.add_argument("--metrics-json", help="JSON export for real post-publish metrics.")
    metrics.add_argument("--metrics-text", help="Text evidence for real post-publish metrics.")
    metrics.add_argument("--published-url", help="Published URL to resolve through supported official metrics connectors.")
    metrics.add_argument("--github-repo", help="GitHub repo owner/name for metrics collection.")
    metrics.add_argument("--youtube-video-id", help="YouTube video ID for metrics collection.")
    parser.add_argument("--metrics-platform", default="auto")

    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def run_product_intake(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    intake_dir = out_dir / "intake"
    command = [sys.executable, str(SCRIPTS / "product_intake.py"), "--out-dir", str(intake_dir)]
    if args.browser_url:
        snapshot_path = run_browser_snapshot(args, out_dir, steps)
        command.extend(["--structured-json", str(snapshot_path)])
    elif args.product_url:
        command.extend(["--url", args.product_url])
    elif args.html_file:
        command.extend(["--html-file", args.html_file])
    elif args.text_file:
        command.extend(["--text-file", args.text_file])
    else:
        command.extend(["--structured-json", args.structured_json])
    steps.append(run_command("product_intake", command))
    profile_path = intake_dir / "product-profile.json"
    if not profile_path.exists():
        raise SystemExit(f"Product intake did not create {profile_path}")
    return json.loads(profile_path.read_text(encoding="utf-8"))


def run_browser_snapshot(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> Path:
    snapshot_path = out_dir / "browser-snapshot/product-page-snapshot.json"
    command = [
        sys.executable,
        str(SCRIPTS / "browser_snapshot.py"),
        "--url",
        args.browser_url,
        "--out-file",
        str(snapshot_path),
        "--out-dir",
        str(out_dir),
    ]
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    steps.append(run_command("browser_snapshot", command))
    if not snapshot_path.exists():
        raise SystemExit(f"Browser snapshot did not create {snapshot_path}")
    return snapshot_path


def product_from_profile(args: argparse.Namespace, profile: dict[str, Any]) -> dict[str, Any]:
    name = first_non_empty(args.product_name, profile.get("productName"), profile.get("title"), "Unknown product")
    url = first_non_empty(args.browser_url, args.product_url, profile.get("canonicalUrl"), profile.get("source"))
    audience = split_csv(args.audience) or clean_list(profile.get("targetAudienceAssumptions")) or ["target audience needs manual verification"]
    pain_points = split_csv(args.pain_points) or clean_list(profile.get("painPointAssumptions")) or ["pain points need manual verification"]
    value = first_non_empty(args.value_proposition, profile.get("valueProposition"), profile.get("description"), f"{name} value proposition needs manual verification.")
    pricing = first_non_empty(args.pricing, profile.get("pricing"), "unknown")
    return {
        "name": name,
        "url": url,
        "audience": audience,
        "painPoints": pain_points,
        "valueProposition": value,
        "pricing": pricing,
        "goal": args.goal,
        "language": args.language,
        "platforms": split_csv(args.platforms) or DEFAULT_PLATFORMS,
        "keywords": clean_list(profile.get("keywords")),
    }


def run_promotion_manager(args: argparse.Namespace, product: dict[str, Any], out_dir: Path, steps: list[dict[str, Any]]) -> None:
    command = [
        sys.executable,
        str(SCRIPTS / "promotion_manager.py"),
        "all",
        "--product-name",
        product["name"],
        "--product-url",
        product["url"],
        "--audience",
        ", ".join(product["audience"]),
        "--pain-points",
        ", ".join(product["painPoints"]),
        "--value-proposition",
        product["valueProposition"],
        "--pricing",
        product["pricing"],
        "--goal",
        product["goal"],
        "--language",
        args.language,
        "--platforms",
        ",".join(product["platforms"]),
        "--out-dir",
        str(out_dir),
    ]
    steps.append(run_command("promotion_manager_all", command))


def run_competitor_discovery(args: argparse.Namespace, product: dict[str, Any], out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    if args.skip_competitor_discovery:
        return None
    query = competitor_query(args, product)
    command = [
        sys.executable,
        str(SCRIPTS / "competitor_discovery.py"),
        "--query",
        query,
        "--platforms",
        ",".join(product["platforms"]),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    if args.live_official_competitors:
        command.append("--live-official")
    steps.append(run_command("competitor_discovery", command))
    path = out_dir / "reports/promotion-manager/competitors/competitor-discovery.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def run_competitor_collectors(args: argparse.Namespace, product: dict[str, Any], out_dir: Path, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not args.live_official_competitors:
        return []
    query = competitor_query(args, product)
    reports = []
    for platform in split_csv(args.collector_platforms):
        collector_dir = agent_dir(out_dir) / "competitor-collections" / platform
        command = [
            sys.executable,
            str(SCRIPTS / "competitor_collector.py"),
            "--platform",
            platform,
            "--query",
            query,
            "--top-n",
            str(args.top_n),
            "--out-dir",
            str(collector_dir),
        ]
        steps.append(run_command(f"competitor_collector_{platform}", command, check=False))
        path = collector_dir / "reports/promotion-manager/competitors/auto-collected-competitors.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            reports.append({"platform": platform, "path": str(path), "recordCount": len(payload.get("records", [])), "connectorStatus": payload.get("connectorStatus", [])})
    return reports


def run_browser_search_snapshots(args: argparse.Namespace, product: dict[str, Any], out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not args.auto_search_competitors:
        return None
    snapshot_dir = out_dir / "search-snapshots/browser-search"
    command = [
        sys.executable,
        str(SCRIPTS / "platform_search_browser.py"),
        "--query",
        competitor_query(args, product),
        "--platforms",
        ",".join(product["platforms"]),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
        "--snapshot-dir",
        str(snapshot_dir),
    ]
    if args.search_html_snapshot_dir:
        command.extend(["--html-snapshot-dir", args.search_html_snapshot_dir])
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    step = run_command("platform_search_browser", command, check=False)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/competitors/browser-search-snapshots.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return {
            "status": "ready" if step["exitCode"] == 0 else "error",
            "path": str(report_path),
            "snapshotDir": report.get("snapshotDir", str(snapshot_dir)),
            "records": report.get("records", []),
        }
    return {"status": "error", "path": "", "snapshotDir": str(snapshot_dir), "records": []}


def run_search_captures(
    args: argparse.Namespace,
    product: dict[str, Any],
    out_dir: Path,
    steps: list[dict[str, Any]],
    browser_search: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    snapshot_dir_value = args.search_snapshot_dir or (browser_search or {}).get("snapshotDir", "")
    if not snapshot_dir_value:
        return []
    snapshot_dir = Path(snapshot_dir_value)
    query = competitor_query(args, product)
    captures = []
    for platform in product["platforms"]:
        source = search_snapshot_source(snapshot_dir, platform)
        if not source:
            captures.append({"platform": platform, "status": "missing_snapshot", "expected": str(snapshot_dir / f"{platform}.json")})
            continue
        command = [
            sys.executable,
            str(SCRIPTS / "platform_search_capture.py"),
            "--platform",
            platform,
            "--query",
            query,
            "--top-n",
            str(args.top_n),
            "--out-dir",
            str(out_dir),
            str(source["flag"]),
            str(source["path"]),
        ]
        step = run_command(f"platform_search_capture_{platform}", command, check=False)
        steps.append(step)
        path = out_dir / "reports/promotion-manager/competitors" / f"captured-search-results-{platform}.json"
        summary = {"platform": platform, "status": "ready" if path.exists() else "error", "path": str(path), "exitCode": step["exitCode"]}
        if path.exists():
            report = json.loads(path.read_text(encoding="utf-8"))
            summary["recordCount"] = len(report.get("records", []))
            summary["inputMode"] = report.get("inputMode")
        captures.append(summary)
    return captures


def run_viral_content_library(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
    search_captures: list[dict[str, Any]],
) -> dict[str, Any]:
    if args.skip_viral_library:
        return {"status": "skipped", "reason": "--skip-viral-library was supplied."}
    capture_paths = [item.get("path") for item in search_captures if item.get("status") == "ready" and item.get("path")]
    capture_paths = [path for path in capture_paths if Path(path).exists()]
    if not capture_paths:
        return {"status": "skipped", "reason": "No captured search result reports were available."}
    command = [
        sys.executable,
        str(SCRIPTS / "viral_content_library.py"),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    for path in capture_paths:
        command.extend(["--capture-report", path])
    step = run_command("viral_content_library", command, check=False)
    steps.append(step)
    library_path = out_dir / "reports/promotion-manager/competitors/viral-content-library.json"
    tasks_path = out_dir / "reports/promotion-manager/competitors/follow-up-capture-tasks.json"
    summary = {
        "status": "ready" if library_path.exists() else "error",
        "library": str(library_path),
        "followUpTasks": str(tasks_path),
        "exitCode": step["exitCode"],
    }
    if library_path.exists():
        report = json.loads(library_path.read_text(encoding="utf-8"))
        summary["recordCount"] = report.get("recordCount", 0)
        summary["platforms"] = report.get("platforms", [])
    if tasks_path.exists():
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        summary["taskSummary"] = tasks.get("summary", {})
    return summary


def run_creator_leaderboard(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
    viral_library: dict[str, Any],
) -> dict[str, Any]:
    if args.skip_creator_leaderboard:
        return {"status": "skipped", "reason": "--skip-creator-leaderboard was supplied."}
    library_path = existing_path(viral_library.get("library", ""))
    if not library_path:
        return {"status": "skipped", "reason": "No viral content library was available."}
    command = [
        sys.executable,
        str(SCRIPTS / "creator_leaderboard.py"),
        "--viral-library",
        str(library_path),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(out_dir),
    ]
    step = run_command("creator_leaderboard", command, check=False)
    steps.append(step)
    leaderboard_path = out_dir / "reports/promotion-manager/competitors/creator-leaderboard.json"
    tasks_path = out_dir / "reports/promotion-manager/competitors/creator-follow-up-tasks.json"
    summary: dict[str, Any] = {
        "status": "ready" if leaderboard_path.exists() and step["exitCode"] == 0 else "error",
        "leaderboard": str(leaderboard_path),
        "followUpTasks": str(tasks_path),
        "exitCode": step["exitCode"],
    }
    if leaderboard_path.exists():
        leaderboard = json.loads(leaderboard_path.read_text(encoding="utf-8"))
        summary["creatorCount"] = leaderboard.get("creatorCount", 0)
        summary["summary"] = leaderboard.get("summary", {})
    if tasks_path.exists():
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        summary["taskCount"] = tasks.get("taskCount", 0)
        summary["taskSummary"] = tasks.get("summary", {})
    return summary


def run_creator_follow_up(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
    creator_leaderboard: dict[str, Any],
) -> dict[str, Any]:
    if not args.run_creator_follow_up:
        return {"status": "skipped", "reason": "--run-creator-follow-up was not supplied."}
    tasks_path = creator_leaderboard.get("followUpTasks", "")
    if not tasks_path or not Path(tasks_path).exists():
        return {"status": "skipped", "reason": "No creator follow-up tasks were available."}
    command = [
        sys.executable,
        str(SCRIPTS / "creator_follow_up_runner.py"),
        "--tasks-json",
        tasks_path,
        "--limit",
        str(args.creator_follow_up_limit),
        "--top-n",
        str(args.creator_follow_up_top_n),
        "--out-dir",
        str(out_dir),
    ]
    if args.creator_follow_up_dry_run:
        command.append("--dry-run")
    step = run_command("creator_follow_up_runner", command, check=False)
    steps.append(step)
    results_path = out_dir / "reports/promotion-manager/competitors/creator-follow-up-results.json"
    deep_path = out_dir / "reports/promotion-manager/competitors/creator-deep-library.json"
    summary: dict[str, Any] = {
        "status": "ready" if results_path.exists() and step["exitCode"] == 0 else "error",
        "results": str(results_path),
        "creatorDeepLibrary": str(deep_path),
        "exitCode": step["exitCode"],
    }
    if results_path.exists():
        report = json.loads(results_path.read_text(encoding="utf-8"))
        summary["resultSummary"] = report.get("summary", {})
    if deep_path.exists():
        deep = json.loads(deep_path.read_text(encoding="utf-8"))
        summary["deepRecordCount"] = deep.get("recordCount", 0)
    return summary


def run_follow_up_captures(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
    viral_library: dict[str, Any],
) -> dict[str, Any]:
    if not args.run_follow_up_captures:
        return {"status": "skipped", "reason": "--run-follow-up-captures was not supplied."}
    tasks_path = viral_library.get("followUpTasks", "")
    if not tasks_path or not Path(tasks_path).exists():
        return {"status": "skipped", "reason": "No follow-up capture tasks were available."}
    command = [
        sys.executable,
        str(SCRIPTS / "follow_up_capture_runner.py"),
        "--tasks-json",
        tasks_path,
        "--limit",
        str(args.follow_up_capture_limit),
        "--out-dir",
        str(out_dir),
    ]
    if args.follow_up_dry_run:
        command.append("--dry-run")
    if args.allow_localhost_follow_up:
        command.append("--allow-localhost")
    if args.capture_browser_assisted_follow_ups:
        command.append("--capture-browser-assisted")
    if args.sample_video_frames:
        command.append("--sample-video-frames")
        command.extend(["--video-sample-count", str(args.video_sample_count)])
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    step = run_command("follow_up_capture_runner", command, check=False)
    steps.append(step)
    results_path = out_dir / "reports/promotion-manager/competitors/follow-up-capture-results.json"
    deep_path = out_dir / "reports/promotion-manager/competitors/deep-competitor-library.json"
    summary = {
        "status": "ready" if results_path.exists() and step["exitCode"] == 0 else "error",
        "results": str(results_path),
        "deepCompetitorLibrary": str(deep_path),
        "exitCode": step["exitCode"],
    }
    if results_path.exists():
        report = json.loads(results_path.read_text(encoding="utf-8"))
        summary["resultSummary"] = report.get("summary", {})
    if deep_path.exists():
        deep = json.loads(deep_path.read_text(encoding="utf-8"))
        summary["deepRecordCount"] = deep.get("recordCount", 0)
    return summary


def run_competitor_content_enhancer(
    args: argparse.Namespace,
    product: dict[str, Any],
    out_dir: Path,
    steps: list[dict[str, Any]],
    viral_library: dict[str, Any],
    follow_up_captures: dict[str, Any],
    creator_follow_up: dict[str, Any],
) -> dict[str, Any]:
    if args.skip_competitor_informed_content:
        return {"status": "skipped", "reason": "--skip-competitor-informed-content was supplied."}

    content_json = out_dir / "reports/promotion-manager/generated-content" / f"{slugify(product['name'])}-platform-content.json"
    if not content_json.exists():
        return {"status": "blocked", "reason": f"Generated content JSON not found: {content_json}"}

    viral_path = existing_path(viral_library.get("library", ""))
    deep_path = existing_path(follow_up_captures.get("deepCompetitorLibrary", ""))
    if not deep_path:
        deep_path = existing_path(creator_follow_up.get("creatorDeepLibrary", ""))
    if not viral_path and not deep_path:
        return {"status": "skipped", "reason": "No viral or deep competitor library was available."}

    publish_pack = out_dir / "reports/promotion-manager/publish-packs" / f"{slugify(product['name'])}-publish-pack.json"
    command = [
        sys.executable,
        str(SCRIPTS / "competitor_content_enhancer.py"),
        "--content-json",
        str(content_json),
        "--out-dir",
        str(out_dir),
        "--write-back",
    ]
    if viral_path:
        command.extend(["--viral-library", str(viral_path)])
    if deep_path:
        command.extend(["--deep-library", str(deep_path)])
    if publish_pack.exists():
        command.extend(["--publish-pack", str(publish_pack)])

    step = run_command("competitor_content_enhancer", command, check=False)
    steps.append(step)
    slug = content_json.stem.replace("-platform-content", "") or "product"
    content_report = out_dir / "reports/promotion-manager/generated-content" / f"{slug}-competitor-informed-content.json"
    markdown_report = out_dir / "reports/promotion-manager/generated-content" / f"{slug}-competitor-informed-content.md"
    strategy_report = out_dir / "reports/promotion-manager/generated-content" / f"{slug}-competitor-informed-strategy.json"
    backup_path = content_json.with_suffix(".base.json")
    status = "ready" if step["exitCode"] == 0 and content_report.exists() and strategy_report.exists() else "error"
    summary: dict[str, Any] = {
        "status": status,
        "content": str(content_report),
        "markdown": str(markdown_report) if markdown_report.exists() else "",
        "strategy": str(strategy_report),
        "writeBack": str(content_json),
        "backup": str(backup_path) if backup_path.exists() else "",
        "updatedPublishPack": str(publish_pack) if publish_pack.exists() else "",
        "sourceLibraries": {
            "viralContentLibrary": str(viral_path) if viral_path else "",
            "deepCompetitorLibrary": str(deep_path) if deep_path else "",
        },
        "exitCode": step["exitCode"],
    }
    if strategy_report.exists():
        strategy = json.loads(strategy_report.read_text(encoding="utf-8"))
        summary["sourceCounts"] = strategy.get("sourceCounts", {})
        summary["platforms"] = {
            platform: info.get("recordCount", 0)
            for platform, info in strategy.get("platforms", {}).items()
            if isinstance(info, dict)
        }
    return summary


def search_snapshot_source(snapshot_dir: Path, platform: str) -> dict[str, Path | str] | None:
    for suffix, flag in [(".json", "--structured-json"), (".txt", "--text-file"), (".html", "--html-file"), (".htm", "--html-file")]:
        path = snapshot_dir / f"{platform}{suffix}"
        if path.exists():
            return {"path": path, "flag": flag}
    return None


def render_video_artifacts(args: argparse.Namespace, product: dict[str, Any], out_dir: Path, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if args.skip_video:
        return [{"status": "skipped", "reason": "--skip-video was supplied."}]
    content_json = out_dir / "reports/promotion-manager/generated-content" / f"{slugify(product['name'])}-platform-content.json"
    if not content_json.exists():
        return [{"status": "blocked", "reason": f"Generated content JSON not found: {content_json}"}]
    if not shutil.which("ffmpeg"):
        return [{"status": "blocked", "reason": "ffmpeg is required to render MP4 files."}]
    platforms = video_platforms(args, product)
    results = []
    for platform in platforms:
        width, height = dimensions_for(platform)
        out_path = out_dir / "videos" / f"{slugify(product['name'])}-{platform}.mp4"
        command = [
            sys.executable,
            str(SCRIPTS / "render_video.py"),
            "--content-json",
            str(content_json),
            "--platform",
            platform,
            "--width",
            str(width),
            "--height",
            str(height),
            "--out",
            str(out_path),
        ]
        if args.generate_voiceover:
            command.append("--generate-voiceover")
        step = run_command(f"render_video_{platform}", command, check=False)
        steps.append(step)
        results.append(
            {
                "platform": platform,
                "status": "ready" if out_path.exists() and out_path.stat().st_size > 0 else "blocked",
                "video": str(out_path) if out_path.exists() else "",
                "metadata": str(out_path.with_suffix(".json")) if out_path.with_suffix(".json").exists() else "",
                "exitCode": step["exitCode"],
            }
        )
    return results


def run_media_asset_pack(
    args: argparse.Namespace,
    product: dict[str, Any],
    out_dir: Path,
    steps: list[dict[str, Any]],
    videos: list[dict[str, Any]],
) -> dict[str, Any]:
    content_json = out_dir / "reports/promotion-manager/generated-content" / f"{slugify(product['name'])}-platform-content.json"
    publish_pack = out_dir / "reports/promotion-manager/publish-packs" / f"{slugify(product['name'])}-publish-pack.json"
    if not content_json.exists() or not publish_pack.exists():
        return {
            "status": "blocked",
            "reason": "Generated content JSON or publish pack was missing before media asset generation.",
            "assetPack": "",
        }
    command = [
        sys.executable,
        str(SCRIPTS / "media_asset_pack.py"),
        "--content-json",
        str(content_json),
        "--publish-pack",
        str(publish_pack),
        "--platforms",
        ",".join(product["platforms"]),
        "--out-dir",
        str(out_dir),
    ]
    for item in videos:
        platform = str(item.get("platform") or "").strip()
        video = str(item.get("video") or "").strip()
        if platform and video:
            command.extend(["--video-file", f"{platform}={video}"])
    step = run_command("media_asset_pack", command, check=False)
    steps.append(step)
    report_path = out_dir / "reports/promotion-manager/media-assets/media-asset-pack.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return {
        "status": report.get("status") or ("ready" if step["exitCode"] == 0 else "error"),
        "assetPack": str(report_path) if report_path.exists() else "",
        "summary": report.get("summary", {}),
        "exitCode": step["exitCode"],
    }


def run_metrics_import(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    source_args = metrics_source_args(args)
    if not source_args:
        return None
    command = [sys.executable, str(SCRIPTS / "metrics_intake.py"), *source_args, "--platform", args.metrics_platform, "--out-dir", str(out_dir)]
    steps.append(run_command("metrics_intake", command, check=False))
    path = out_dir / "reports/promotion-manager/metrics/imported-metrics.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def build_manifest(
    args: argparse.Namespace,
    product: dict[str, Any],
    profile: dict[str, Any],
    discovery: dict[str, Any] | None,
    collections: list[dict[str, Any]],
    browser_search: dict[str, Any] | None,
    search_captures: list[dict[str, Any]],
    viral_library: dict[str, Any],
    creator_leaderboard: dict[str, Any],
    creator_follow_up: dict[str, Any],
    follow_up_captures: dict[str, Any],
    competitor_informed: dict[str, Any],
    videos: list[dict[str, Any]],
    media_assets: dict[str, Any],
    metrics: dict[str, Any] | None,
    steps: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    publish_packs = out_dir / "reports/promotion-manager/publish-packs" / f"{slugify(product['name'])}-publish-pack.json"
    publish_queue = []
    if publish_packs.exists():
        for item in json.loads(publish_packs.read_text(encoding="utf-8")):
            publish_queue.append(
                {
                    "platform": item.get("platform"),
                    "publishMode": item.get("publishMode"),
                    "approvalRequired": item.get("approvalRequired", True),
                    "automationStatus": automation_status(item.get("publishMode", "")),
                    "scheduleSuggestion": item.get("scheduleSuggestion"),
                }
            )
    return {
        "generatedAt": TODAY,
        "product": product,
        "input": {
            "sourceType": profile.get("sourceType"),
            "source": profile.get("source"),
            "confidence": profile.get("confidence"),
            "codexRenderedSnapshotSupported": True,
        },
        "artifacts": {
            "intakeProfile": str(out_dir / "intake/product-profile.json"),
            "browserSnapshot": str(out_dir / "browser-snapshot/product-page-snapshot.json") if args.browser_url else "",
            "contentJson": str(out_dir / "reports/promotion-manager/generated-content" / f"{slugify(product['name'])}-platform-content.json"),
            "publishPack": str(publish_packs),
            "competitorDiscovery": str(out_dir / "reports/promotion-manager/competitors/competitor-discovery.json"),
            "viralContentLibrary": viral_library.get("library", ""),
            "creatorLeaderboard": creator_leaderboard.get("leaderboard", ""),
            "creatorFollowUpTasks": creator_leaderboard.get("followUpTasks", ""),
            "creatorFollowUpResults": creator_follow_up.get("results", ""),
            "creatorDeepLibrary": creator_follow_up.get("creatorDeepLibrary", ""),
            "followUpCaptureTasks": viral_library.get("followUpTasks", ""),
            "followUpCaptureResults": follow_up_captures.get("results", ""),
            "deepCompetitorLibrary": follow_up_captures.get("deepCompetitorLibrary", ""),
            "competitorInformedContent": competitor_informed.get("content", ""),
            "competitorInformedStrategy": competitor_informed.get("strategy", ""),
            "mediaAssetPack": media_assets.get("assetPack", ""),
            "metricsReport": str(out_dir / "reports/promotion-manager/metrics/imported-metrics.json"),
        },
        "competitorDiscovery": {
            "status": "ready" if discovery else "skipped",
            "query": discovery.get("query") if discovery else "",
            "platforms": [task.get("platform") for task in discovery.get("tasks", [])] if discovery else [],
            "officialCollections": collections,
            "browserSearchSnapshots": browser_search or {},
            "searchCaptures": search_captures,
            "viralContentLibrary": viral_library,
            "creatorLeaderboard": creator_leaderboard,
            "creatorFollowUpRun": creator_follow_up,
            "followUpCaptureRun": follow_up_captures,
            "competitorInformedContent": competitor_informed,
        },
        "videoGeneration": videos,
        "mediaAssets": media_assets,
        "publishAutomation": publish_queue,
        "metricsRecovery": {
            "status": metrics.get("retrospective", {}).get("status") if metrics else "waiting_real_data",
            "inputMode": metrics.get("inputMode") if metrics else "",
            "records": len(metrics.get("records", [])) if metrics else 0,
            "rule": "Use official APIs, platform exports, screenshots, or user-provided business evidence only.",
        },
        "selfEvolution": {
            "status": "controlled",
            "canResearch": True,
            "canWriteUpgradePlans": True,
            "canInstallWithoutReview": False,
            "reason": "The Skill can learn and propose/install reviewed tools, but must not silently execute unreviewed network code or modify itself without an explicit command.",
        },
        "guardrails": [
            "No automatic login, captcha bypass, cookie extraction, token storage, or fabricated metrics.",
            "Official API writes require explicit approval and environment credentials.",
            "Zhihu, Xiaohongshu, and Douyin remain browser-assisted/manual unless official access is verified for the user's account.",
        ],
        "steps": steps,
    }


def run_command(name: str, command: list[str], check: bool = True) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    step = {
        "name": name,
        "status": "ready" if result.returncode == 0 else "error",
        "exitCode": result.returncode,
        "command": display_command(command),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }
    if check and result.returncode != 0:
        raise SystemExit(f"{name} failed: {step['stderrTail'] or step['stdoutTail']}")
    return step


def write_manifest(out_dir: Path, manifest: dict[str, Any]) -> None:
    directory = agent_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "workflow-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "workflow-manifest.md").write_text(render_manifest(manifest) + "\n", encoding="utf-8")


def render_manifest(manifest: dict[str, Any]) -> str:
    product = manifest["product"]
    lines = [
        "# Promotion Workflow Manifest",
        "",
        f"- Generated: {manifest['generatedAt']}",
        f"- Product: {product['name']}",
        f"- URL: {product['url']}",
        f"- Input source: `{manifest['input']['sourceType']}`",
        "",
        "## Competitor Discovery",
        f"- Status: `{manifest['competitorDiscovery']['status']}`",
        f"- Query: {manifest['competitorDiscovery']['query']}",
        f"- Viral content library: `{manifest['competitorDiscovery']['viralContentLibrary'].get('status', 'skipped')}`",
        f"- Creator leaderboard: `{manifest['competitorDiscovery']['creatorLeaderboard'].get('status', 'skipped')}`",
        f"- Creator follow-up: `{manifest['competitorDiscovery']['creatorFollowUpRun'].get('status', 'skipped')}`",
        f"- Follow-up captures: `{manifest['competitorDiscovery']['followUpCaptureRun'].get('status', 'skipped')}`",
        f"- Competitor-informed content: `{manifest['competitorDiscovery']['competitorInformedContent'].get('status', 'skipped')}`",
        "",
        "## Video Generation",
    ]
    for item in manifest["videoGeneration"]:
        lines.append(f"- {item.get('platform', 'workflow')}: `{item.get('status')}` {item.get('video') or item.get('reason', '')}")
    media_assets = manifest.get("mediaAssets") if isinstance(manifest.get("mediaAssets"), dict) else {}
    lines.extend(["", "## Media Assets"])
    lines.append(f"- Status: `{media_assets.get('status', 'missing')}`")
    lines.append(f"- Asset pack: {media_assets.get('assetPack', '')}")
    for key, value in (media_assets.get("summary") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Publish Automation"])
    for item in manifest["publishAutomation"]:
        lines.append(f"- {item['platform']}: `{item['publishMode']}` / `{item['automationStatus']}`")
    lines.extend(
        [
            "",
            "## Metrics Recovery",
            f"- Status: `{manifest['metricsRecovery']['status']}`",
            f"- Records: {manifest['metricsRecovery']['records']}",
            "",
            "## Self Evolution",
            f"- Status: `{manifest['selfEvolution']['status']}`",
            f"- Install without review: {manifest['selfEvolution']['canInstallWithoutReview']}",
            "",
            "## Guardrails",
        ]
    )
    lines.extend([f"- {item}" for item in manifest["guardrails"]])
    return "\n".join(lines)


def competitor_query(args: argparse.Namespace, product: dict[str, Any]) -> str:
    if args.competitor_query:
        return args.competitor_query
    parts = [product["name"], product["valueProposition"], *product.get("keywords", [])[:5]]
    return " ".join(part for part in parts if part).strip()[:180]


def video_platforms(args: argparse.Namespace, product: dict[str, Any]) -> list[str]:
    if args.video_platforms != "auto":
        return [platform for platform in split_csv(args.video_platforms) if platform in product["platforms"]]
    return [platform for platform in product["platforms"] if platform in VIDEO_PLATFORMS]


def dimensions_for(platform: str) -> tuple[int, int]:
    if platform in {"douyin", "tiktok"}:
        return 1080, 1920
    return 1280, 720


def metrics_source_args(args: argparse.Namespace) -> list[str]:
    if args.metrics_csv:
        return ["--csv-file", args.metrics_csv]
    if args.metrics_xlsx:
        return ["--xlsx-file", args.metrics_xlsx]
    if args.metrics_json:
        return ["--json-file", args.metrics_json]
    if args.metrics_text:
        return ["--text-file", args.metrics_text]
    if args.published_url:
        return ["--published-url", args.published_url]
    if args.github_repo:
        return ["--github-repo", args.github_repo]
    if args.youtube_video_id:
        return ["--youtube-video-id", args.youtube_video_id]
    return []


def automation_status(mode: str) -> str:
    if mode == "official_api_publish":
        return "dry_run_ready_requires_credentials_and_approval"
    if mode == "browser_assisted_publish":
        return "browser_assisted_requires_user_final_publish"
    if mode == "manual_publish_required":
        return "copy_pack_ready_manual_publish"
    return "unsupported"


def agent_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/agent-run"


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return split_csv(value)
    return []


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = "" if value is None else str(value).strip()
        if text:
            return text
    return ""


def existing_path(value: Any) -> Path | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    path = Path(text)
    return path if path.exists() else None


def slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "product"


def display_command(command: list[str]) -> list[str]:
    displayed = []
    for item in command:
        if item == sys.executable:
            displayed.append("python")
        else:
            displayed.append(item)
    return displayed


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


if __name__ == "__main__":
    main()
