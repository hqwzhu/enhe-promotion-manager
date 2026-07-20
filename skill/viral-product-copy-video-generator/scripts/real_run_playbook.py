#!/usr/bin/env python3
"""Generate a copy-ready playbook for a real product promotion run."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"
PUBLISH_APPROVAL = "I_APPROVE_PUBLISH"
SKILL_SYNC_APPROVAL = "I_APPROVE_SKILL_SYNC"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    report = build_playbook(args, out_dir)
    write_report(out_dir, report)
    print(f"Real run playbook written to: {(report_dir(out_dir) / 'real-run-playbook.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an operator playbook for a real Codex promotion run.")
    parser.add_argument("--url", action="append", default=[], help="Product URL. Can be repeated.")
    parser.add_argument("--urls-file", default="", help="Text file with one product URL per line.")
    parser.add_argument("--discover-from-url", default="", help="Website URL to discover product URLs from.")
    parser.add_argument("--discovery-html-file", default="", help="Saved public website HTML to discover product URLs from.")
    parser.add_argument("--discovery-sitemap-url", default="", help="Public sitemap.xml or sitemap index URL to discover product URLs from.")
    parser.add_argument("--discovery-sitemap-file", default="", help="Saved sitemap.xml, sitemap index, or .xml.gz file to discover product URLs from.")
    parser.add_argument("--discovery-base-url", default="", help="Base URL for resolving links in --discovery-html-file.")
    parser.add_argument("--discovery-top-n", type=int, default=50)
    parser.add_argument("--discovery-min-score", type=float, default=3.0)
    parser.add_argument("--discovery-max-pages", type=int, default=20)
    parser.add_argument("--discovery-max-depth", type=int, default=1)
    parser.add_argument("--discovery-max-sitemap-urls", type=int, default=1000)
    parser.add_argument("--discovery-timeout", type=float, default=20.0)
    parser.add_argument("--discovery-include-external", action="store_true")
    parser.add_argument("--discovery-skip-sitemaps", action="store_true")
    parser.add_argument("--discovery-allow-localhost", action="store_true")
    parser.add_argument("--platforms", default=DEFAULT_PLATFORMS)
    parser.add_argument("--goal", default="leads")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--github-repo", default="owner/repo")
    parser.add_argument("--github-action", default="file", choices=["file", "issue", "release"])
    parser.add_argument("--github-path", default="PROMOTION.md")
    parser.add_argument("--github-branch", default="")
    parser.add_argument("--github-tag-name", default="")
    parser.add_argument("--youtube-video-file", default="")
    parser.add_argument("--youtube-privacy-status", default="private", choices=["private", "public", "unlisted"])
    parser.add_argument("--youtube-category-id", default="22")
    parser.add_argument("--douyin-video-file", default="")
    parser.add_argument("--platform-publish-url", action="append", default=[], help="Override browser-assisted publisher entry as platform=url.")
    parser.add_argument("--run-browser-form-fill", action="store_true", help="Include browser form-fill execution in final runner commands.")
    parser.add_argument("--browser-form-fill-headed", action="store_true")
    parser.add_argument("--browser-form-fill-allow-localhost", action="store_true")
    parser.add_argument("--browser-form-fill-install-browser-if-missing", action="store_true")
    parser.add_argument("--browser-form-fill-timeout-ms", type=int, default=30000)
    parser.add_argument("--browser-form-fill-wait-until", default="domcontentloaded", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--metrics-csv", action="append", default=[], help="Platform metrics CSV export. Can repeat.")
    parser.add_argument("--metrics-xlsx", action="append", default=[], help="Platform metrics Excel .xlsx export. Can repeat.")
    parser.add_argument("--metrics-json", action="append", default=[], help="Platform metrics JSON export. Can repeat.")
    parser.add_argument("--metrics-text", action="append", default=[], help="Platform metrics text evidence. Can repeat.")
    parser.add_argument("--business-csv", action="append", default=[], help="Business orders/revenue CSV export. Can repeat.")
    parser.add_argument("--business-xlsx", action="append", default=[], help="Business orders/revenue Excel .xlsx export. Can repeat.")
    parser.add_argument("--business-json", action="append", default=[], help="Business orders/revenue JSON export. Can repeat.")
    parser.add_argument("--business-text", action="append", default=[], help="Business orders/revenue text evidence. Can repeat.")
    parser.add_argument("--published-url", action="append", default=[], help="Known published URL as platform=url. Can repeat.")
    parser.add_argument("--metrics-structured-json", default="./published-metrics-snapshot.json")
    parser.add_argument("--automation-config", default="./promotion-automation.json")
    parser.add_argument("--automation-job-id", default="product-weekly")
    parser.add_argument("--interval-days", type=int, default=7)
    parser.add_argument("--generate-voiceover", action="store_true")
    return parser.parse_args()


def build_playbook(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    run_root = out_dir / "product-batch-runs/<product-id>"
    phases = build_phases(args, out_dir, run_root)
    artifacts = artifact_paths(out_dir)
    return {
        "generatedAt": TODAY,
        "status": "ready",
        "outDir": str(out_dir),
        "input": {
            "urls": args.url,
            "urlsFile": args.urls_file,
            "discoverFromUrl": args.discover_from_url,
            "discovery": discovery_input(args),
            "platforms": args.platforms,
            "goal": args.goal,
            "language": args.language,
            "githubRepo": args.github_repo,
            "githubAction": args.github_action,
            "githubPath": args.github_path,
            "githubBranchProvided": bool(args.github_branch),
            "githubTagNameProvided": bool(args.github_tag_name),
            "youtubeVideoFile": args.youtube_video_file,
            "youtubePrivacyStatus": args.youtube_privacy_status,
            "youtubeCategoryId": args.youtube_category_id,
            "douyinVideoFile": args.douyin_video_file,
            "platformPublishUrl": args.platform_publish_url,
            "runBrowserFormFill": bool(args.run_browser_form_fill),
            "metricsCsv": args.metrics_csv,
            "metricsXlsx": args.metrics_xlsx,
            "metricsJson": args.metrics_json,
            "metricsText": args.metrics_text,
            "businessCsv": args.business_csv,
            "businessXlsx": args.business_xlsx,
            "businessJson": args.business_json,
            "businessText": args.business_text,
            "publishedUrl": args.published_url,
            "metricsStructuredJson": args.metrics_structured_json,
        },
        "operatingRule": "Run phases in order, keep generated evidence paths, and do not mark performance recovered until real URLs/exports exist.",
        "phases": phases,
        "evidenceChecklist": evidence_checklist(out_dir, run_root),
        "platformGates": platform_gates(),
        "approvalGates": approval_gates(),
        "artifacts": artifacts,
        "guardrails": guardrails(),
    }


def build_phases(args: argparse.Namespace, out_dir: Path, run_root: Path) -> list[dict[str, Any]]:
    return [
        phase(
            "preflight",
            "Verify local tools, platform boundaries, and installed Skill drift.",
            [
                command(
                    "audit_final_capability",
                    ["python", "scripts/final_capability_audit.py", "--out-dir", str(out_dir)],
                    proves=["local scripts, ffmpeg, browser runtime, credential presence by name, and platform limits"],
                    outputs=[str(out_dir / "reports/promotion-manager/capability/final-capability-audit.json")],
                ),
                command(
                    "audit_self_evolution",
                    ["python", "scripts/self_evolution_audit.py", "--out-dir", str(out_dir)],
                    proves=["repository state, runtime gaps, installed Skill drift, and safe sync command"],
                    outputs=[str(out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.json")],
                ),
            ],
        ),
        phase(
            "real_full_run",
            "Read product URLs first, run viral discovery, generate copy/video, build publish packs, and collect available evidence.",
            [
                command(
                    "run_final_capability",
                    final_capability_command(args, out_dir),
                    proves=[
                        "Codex-first product URL reading",
                        "multi-platform viral discovery and follow-up queues",
                        "platform copy and MP4 generation when ffmpeg and targets are available",
                        "publish readiness, browser publish payloads, metrics recovery, and next-round optimizer reports",
                    ],
                    outputs=[
                        str(out_dir / "reports/promotion-manager/final-run/final-capability-run.json"),
                        str(out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json"),
                    ],
                )
            ],
        ),
        phase(
            "readiness_review",
            "Build the final requirement matrix and inspect what is ready versus externally gated.",
            [
                command(
                    "build_final_readiness_matrix",
                    ["python", "scripts/final_capability_readiness.py", "--out-dir", str(out_dir)],
                    proves=["requirement-by-requirement final state, missing evidence, external gates, and next actions"],
                    outputs=[str(out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json")],
                )
            ],
        ),
        phase(
            "publish_preparation",
            "Convert generated content into guarded publish queues and setup guides.",
            [
                command(
                    "audit_publish_readiness_for_one_product",
                    publish_readiness_command(args, run_root),
                    proves=["per-platform target, credential, approval, queue, and execution readiness"],
                    outputs=[str(run_root / "reports/promotion-manager/publish-readiness/publish-readiness.json")],
                ),
                command(
                    "build_publish_setup_kit",
                    [
                        "python",
                        "scripts/publish_setup_assistant.py",
                        "--publish-readiness",
                        str(run_root / "reports/promotion-manager/publish-readiness/publish-readiness.json"),
                        "--out-dir",
                        str(run_root),
                    ],
                    proves=["credential variable names, official setup references, target gaps, and approval commands"],
                    outputs=[
                        str(run_root / "reports/promotion-manager/publish-setup/publish-setup.json"),
                        str(run_root / "reports/promotion-manager/publish-setup/platform-setup-guide.md"),
                    ],
                ),
                command(
                    "prepare_browser_publish_payloads",
                    browser_publish_assistant_command(args, run_root),
                    proves=["copy-ready browser/manual payloads for Zhihu, Xiaohongshu, Douyin fallback, TikTok, and similar platforms"],
                    outputs=[str(run_root / "reports/promotion-manager/browser-publish/browser-publish-assistant.json")],
                ),
                command(
                    "run_browser_publish_session",
                    browser_publish_session_command(args, run_root),
                    proves=["payload preparation, visible-field fill where possible, screenshots, final user-action checklist, and post-publish evidence commands"],
                    outputs=[str(run_root / "reports/promotion-manager/browser-publish-session/browser-publish-session.json")],
                ),
                command(
                    "fill_prepared_browser_publish_payload",
                    browser_form_fill_command(args, run_root),
                    requires=["prepared browser-publish payload JSON", "user-visible publisher entry URL"],
                    proves=["visible publisher fields can be filled while stopping before final publish"],
                    outputs=[str(run_root / "browser-form-fill-runs/<platform>/reports/promotion-manager/browser-publish/browser-form-fill.json")],
                ),
                command(
                    "build_real_evidence_setup",
                    [
                        "python",
                        "scripts/real_evidence_setup.py",
                        "--publish-queue",
                        str(run_root / "reports/promotion-manager/publish-queue/publish-queue.json"),
                        "--publish-readiness",
                        str(run_root / "reports/promotion-manager/publish-readiness/publish-readiness.json"),
                        "--out-dir",
                        str(run_root),
                    ],
                    proves=["platform metric templates, comment templates, business attribution template, published URL template, and import commands for real evidence recovery"],
                    outputs=[
                        str(run_root / "reports/promotion-manager/real-evidence-setup/real-evidence-setup.json"),
                        str(run_root / "reports/promotion-manager/real-evidence-setup/real-evidence-checklist.md"),
                    ],
                ),
            ],
        ),
        phase(
            "authorized_publish",
            "Execute official publishing only where credentials, target, account authorization, and approval are ready; keep Douyin on browser-assisted/manual publishing in the current setup.",
            [
                command(
                    "execute_queue_when_approved",
                    publish_readiness_command(args, run_root)
                    + ["--execute-publish", "--approval", PUBLISH_APPROVAL],
                    approval=PUBLISH_APPROVAL,
                    requires=["official credentials in environment", "reviewed dry-run output", "real platform account authorization"],
                    proves=["official publish execution report or explicit platform block reason"],
                    outputs=[str(run_root / "reports/promotion-manager/publish-readiness/publish-readiness.json")],
                ),
                command(
                    "youtube_oauth_upload_when_approved",
                    youtube_oauth_command(args, run_root),
                    approval=PUBLISH_APPROVAL,
                    requires=["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "YouTube channel owner consent", "real MP4"],
                    proves=["YouTube upload result without saved OAuth token"],
                    outputs=[str(run_root / "reports/promotion-manager/publish-results/youtube-oauth-publish.json")],
                ),
            ],
        ),
        phase(
            "register_real_publication_evidence",
            "Register real published URLs from official or browser/manual publishing before metrics recovery.",
            [
                command(
                    f"register_{platform}_published_url",
                    [
                        "python",
                        "scripts/published_items.py",
                        "--platform",
                        platform,
                        "--published-url",
                        url,
                        "--title",
                        f"Published {platform} promotion",
                        "--evidence",
                        f"./screenshots/{platform}-published.png",
                        "--out-dir",
                        str(run_root),
                    ],
                    requires=["real published URL", "screenshot, official execution report, or platform evidence"],
                    proves=[f"registered {platform} published item for metrics recovery"],
                    outputs=[str(run_root / "reports/promotion-manager/published-items/published-items.json")],
                )
                for platform, url in published_url_pairs(args)
            ]
            or [
                command(
                    "register_first_real_published_url",
                    [
                        "python",
                        "scripts/published_items.py",
                        "--platform",
                        "xiaohongshu",
                        "--published-url",
                        "https://...",
                        "--title",
                        "Published promotion",
                        "--evidence",
                        "./screenshots/published.png",
                        "--out-dir",
                        str(run_root),
                    ],
                    requires=["replace placeholder with a real platform URL"],
                    proves=["registered published item for metrics recovery"],
                    outputs=[str(run_root / "reports/promotion-manager/published-items/published-items.json")],
                )
            ],
        ),
        phase(
            "real_metrics_recovery",
            "Recover real public metrics, comments, business attribution, and merged retrospective data.",
            [
                command(
                    "capture_public_post_publish_metrics",
                    ["python", "scripts/post_publish_metrics_capture.py", "--out-dir", str(run_root)],
                    requires=["registered real published URLs"],
                    proves=["public/browser-visible views, likes, saves, shares, comments, clicks, leads, orders, or revenue when visible"],
                    outputs=[str(run_root / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json")],
                ),
                command(
                    "capture_public_comment_evidence",
                    ["python", "scripts/comment_evidence_capture.py", "--out-dir", str(run_root)],
                    requires=["registered real published URLs or comment exports"],
                    proves=["real public/browser-visible comments and demand signals"],
                    outputs=[str(run_root / "reports/promotion-manager/comment-evidence/comment-evidence-export.json")],
                ),
                command(
                    "attribute_business_exports",
                    business_attribution_command(args, run_root),
                    requires=["business export with URL, UTM, content id, campaign, title, orders, revenue, clicks, or leads"],
                    proves=["matched orders/revenue/leads/clicks to specific published content when evidence matches"],
                    outputs=[str(run_root / "reports/promotion-manager/business-attribution/business-attribution.json")],
                ),
                command(
                    "merge_metrics_recovery",
                    metrics_recovery_command(args, run_root),
                    requires=["real published URLs, public metrics export, official metrics, structured snapshots, or business exports"],
                    proves=["merged real metrics and waiting/manual evidence gaps without fabrication"],
                    outputs=[str(run_root / "reports/promotion-manager/metrics-recovery/metrics-recovery.json")],
                ),
            ],
        ),
        phase(
            "next_round",
            "Turn recovered evidence into the next content round.",
            [
                command(
                    "optimize_next_round",
                    [
                        "python",
                        "scripts/next_round_optimizer.py",
                        "--metrics-recovery-json",
                        str(run_root / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"),
                        "--comment-evidence-json",
                        str(run_root / "reports/promotion-manager/comment-evidence/comment-evidence-export.json"),
                        "--business-attribution-json",
                        str(run_root / "reports/promotion-manager/business-attribution/business-attribution.json"),
                        "--out-dir",
                        str(run_root),
                    ],
                    requires=["real metrics, comments, or business attribution"],
                    proves=["next-round hooks, angles, scripts, commands, and platform actions backed by real evidence"],
                    outputs=[str(run_root / "reports/promotion-manager/optimization/next-round-optimization.json")],
                )
            ],
        ),
        phase(
            "periodic_operation",
            "Create and run a local schedule after the manual gates are understood.",
            [
                command(
                    "init_weekly_automation",
                    automation_init_command(args),
                    proves=["local scheduler config for periodic Codex/local operation"],
                    outputs=[args.automation_config],
                ),
                command(
                    "run_due_automation_jobs",
                    ["python", "scripts/automation_scheduler.py", "run", "--config", args.automation_config],
                    proves=["due scheduled promotion jobs executed through guarded local workflow"],
                    outputs=[str(out_dir / "automation/scheduler/automation-run.json")],
                ),
            ],
        ),
        phase(
            "controlled_self_evolution",
            "Apply reviewed local Skill sync or safe runtime installs only when explicitly approved.",
            [
                command(
                    "install_playwright_chromium_if_needed",
                    [
                        "python",
                        "scripts/final_capability_audit.py",
                        "--install-safe-missing-tools",
                        "--safe-install",
                        "playwright_chromium",
                        "--out-dir",
                        str(out_dir),
                    ],
                    requires=["explicit command to install allowlisted runtime"],
                    proves=["safe browser runtime install attempt recorded by audit"],
                    outputs=[str(out_dir / "reports/promotion-manager/capability/final-capability-audit.json")],
                ),
                command(
                    "sync_installed_skill_when_approved",
                    [
                        "python",
                        "scripts/self_evolution_audit.py",
                        "--sync-installed-skill",
                        "--approval",
                        SKILL_SYNC_APPROVAL,
                        "--out-dir",
                        str(out_dir),
                    ],
                    approval=SKILL_SYNC_APPROVAL,
                    requires=["reviewed source repository", "explicit approval phrase"],
                    proves=["installed Codex Skill synced to reviewed source without storing secrets"],
                    outputs=[str(out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.json")],
                ),
            ],
        ),
    ]


def final_capability_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    command = ["python", "scripts/final_capability_runner.py"]
    append_many(command, "--url", args.url)
    append_if(command, "--urls-file", args.urls_file)
    append_if(command, "--discover-from-url", args.discover_from_url)
    append_discovery_args(command, args)
    command.extend(
        [
            "--platforms",
            args.platforms,
            "--goal",
            args.goal,
            "--language",
            args.language,
            "--auto-search-competitors",
            "--run-creator-follow-up",
            "--run-follow-up-captures",
            "--capture-browser-assisted-follow-ups",
            "--sample-video-frames",
            "--multi-query-run-creator-follow-up",
            "--multi-query-run-follow-up-captures",
            "--multi-query-capture-browser-assisted-follow-ups",
            "--multi-query-sample-video-frames",
        ]
    )
    if args.generate_voiceover:
        command.append("--generate-voiceover")
    append_if(command, "--github-repo", args.github_repo)
    append_if(command, "--github-action", args.github_action)
    append_if(command, "--github-path", args.github_path)
    append_if(command, "--github-branch", args.github_branch)
    append_if(command, "--github-tag-name", args.github_tag_name)
    append_if(command, "--youtube-video-file", args.youtube_video_file)
    append_if(command, "--youtube-privacy-status", args.youtube_privacy_status)
    append_if(command, "--youtube-category-id", args.youtube_category_id)
    append_if(command, "--douyin-video-file", args.douyin_video_file)
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
    append_many(command, "--metrics-csv", args.metrics_csv)
    append_many(command, "--metrics-xlsx", args.metrics_xlsx)
    append_many(command, "--metrics-json", args.metrics_json)
    append_many(command, "--metrics-text", args.metrics_text)
    append_if(command, "--metrics-structured-json", args.metrics_structured_json)
    append_many(command, "--business-csv", args.business_csv)
    append_many(command, "--business-xlsx", args.business_xlsx)
    append_many(command, "--business-json", args.business_json)
    append_many(command, "--business-text", args.business_text)
    append_many(command, "--published-url", args.published_url)
    command.extend(["--out-dir", str(out_dir)])
    return command


def append_discovery_args(command: list[str], args: argparse.Namespace) -> None:
    append_if(command, "--discovery-html-file", args.discovery_html_file)
    append_if(command, "--discovery-sitemap-url", args.discovery_sitemap_url)
    append_if(command, "--discovery-sitemap-file", args.discovery_sitemap_file)
    append_if(command, "--discovery-base-url", args.discovery_base_url)
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


def publish_readiness_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    command = [
        "python",
        "scripts/publish_readiness_runner.py",
        "--workflow-manifest",
        str(run_root / "reports/promotion-manager/agent-run/workflow-manifest.json"),
        "--build-queue",
        "--platforms",
        args.platforms,
        "--github-repo",
        args.github_repo,
        "--out-dir",
        str(run_root),
    ]
    append_if(command, "--github-action", args.github_action)
    append_if(command, "--github-path", args.github_path)
    append_if(command, "--github-branch", args.github_branch)
    append_if(command, "--github-tag-name", args.github_tag_name)
    append_if(command, "--youtube-video-file", args.youtube_video_file or str(run_root / "videos/product-youtube.mp4"))
    append_if(command, "--youtube-privacy-status", args.youtube_privacy_status)
    append_if(command, "--youtube-category-id", args.youtube_category_id)
    append_if(command, "--douyin-video-file", args.douyin_video_file or str(run_root / "videos/product-douyin.mp4"))
    return command


def browser_publish_assistant_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    command = [
        "python",
        "scripts/browser_publish_assistant.py",
        "--publish-queue",
        str(run_root / "reports/promotion-manager/publish-queue/publish-queue.json"),
        "--out-dir",
        str(run_root),
    ]
    append_many(command, "--platform-publish-url", args.platform_publish_url)
    return command


def browser_publish_session_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    command = [
        "python",
        "scripts/browser_publish_session.py",
        "--publish-queue",
        str(run_root / "reports/promotion-manager/publish-queue/publish-queue.json"),
        "--out-dir",
        str(run_root),
    ]
    append_many(command, "--platform-publish-url", args.platform_publish_url)
    if args.run_browser_form_fill:
        command.append("--run-form-fill")
        if args.browser_form_fill_headed:
            command.append("--headed")
        if args.browser_form_fill_allow_localhost:
            command.append("--allow-localhost")
        if args.browser_form_fill_install_browser_if_missing:
            command.append("--install-browser-if-missing")
        command.extend(["--timeout-ms", str(args.browser_form_fill_timeout_ms)])
        command.extend(["--wait-until", args.browser_form_fill_wait_until])
    return command


def browser_form_fill_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    platform = first_browser_assisted_platform(args.platforms)
    command = [
        "python",
        "scripts/browser_publish_form_fill.py",
        "--payload-json",
        str(run_root / f"reports/promotion-manager/browser-publish/payloads/{platform}.payload.json"),
        "--out-dir",
        str(run_root / "browser-form-fill-runs" / platform),
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
    return command


def youtube_oauth_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    return [
        "python",
        "scripts/youtube_oauth_publish.py",
        "--execute",
        "--approval",
        PUBLISH_APPROVAL,
        "--video-file",
        args.youtube_video_file or str(run_root / "videos/product-youtube.mp4"),
        "--title",
        "Product promotion video",
        "--out-dir",
        str(run_root),
    ]


def business_attribution_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    command = ["python", "scripts/business_attribution.py", "--out-dir", str(run_root)]
    if args.business_csv:
        append_many(command, "--business-csv", args.business_csv)
    elif args.business_xlsx:
        append_many(command, "--business-xlsx", args.business_xlsx)
    elif args.business_json:
        append_many(command, "--business-json", args.business_json)
    elif args.business_text:
        append_many(command, "--business-text", args.business_text)
    else:
        command.extend(["--business-csv", "./orders-and-revenue.csv"])
    return command


def metrics_recovery_command(args: argparse.Namespace, run_root: Path) -> list[str]:
    command = [
        "python",
        "scripts/metrics_recovery.py",
        "--workflow-manifest",
        str(run_root / "reports/promotion-manager/agent-run/workflow-manifest.json"),
        "--publish-queue",
        str(run_root / "reports/promotion-manager/publish-queue/publish-queue.json"),
        "--metrics-json",
        str(run_root / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json"),
        "--out-dir",
        str(run_root),
    ]
    append_many(command, "--metrics-csv", args.metrics_csv)
    append_many(command, "--metrics-xlsx", args.metrics_xlsx)
    append_many(command, "--metrics-json", args.metrics_json)
    append_many(command, "--metrics-text", args.metrics_text)
    append_if(command, "--metrics-structured-json", args.metrics_structured_json)
    if args.business_csv:
        append_many(command, "--business-csv", args.business_csv)
    elif args.business_xlsx:
        append_many(command, "--business-xlsx", args.business_xlsx)
    elif args.business_json:
        append_many(command, "--business-json", args.business_json)
    elif args.business_text:
        append_many(command, "--business-text", args.business_text)
    else:
        command.extend(["--business-csv", "./orders-and-revenue.csv"])
    return command


def automation_init_command(args: argparse.Namespace) -> list[str]:
    command = [
        "python",
        "scripts/automation_scheduler.py",
        "init",
        "--config",
        args.automation_config,
        "--job-id",
        args.automation_job_id,
        "--platforms",
        args.platforms,
        "--interval-days",
        str(args.interval_days),
    ]
    if args.url:
        command.extend(["--browser-url", args.url[0]])
    elif args.discover_from_url:
        command.extend(["--browser-url", args.discover_from_url])
    else:
        command.extend(["--browser-url", "https://example.com/product"])
    return command


def first_browser_assisted_platform(platforms: str) -> str:
    candidates = [item.strip().lower() for item in platforms.split(",") if item.strip()]
    for platform in candidates:
        if platform in {"zhihu", "xiaohongshu", "douyin", "tiktok"}:
            return platform
    return candidates[0] if candidates else "<platform>"


def published_url_pairs(args: argparse.Namespace) -> list[tuple[str, str]]:
    pairs = []
    for item in args.published_url:
        if "=" not in item:
            continue
        platform, url = item.split("=", 1)
        platform = platform.strip().lower()
        url = url.strip()
        if platform and url:
            pairs.append((platform, url))
    return pairs


def phase(phase_id: str, label: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    return {"id": phase_id, "label": label, "commands": commands}


def command(
    command_id: str,
    parts: list[str],
    approval: str = "",
    requires: list[str] | None = None,
    proves: list[str] | None = None,
    outputs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": command_id,
        "command": display_command(parts),
        "approvalRequired": approval,
        "requires": requires or [],
        "proves": proves or [],
        "outputs": outputs or [],
    }


def evidence_checklist(out_dir: Path, run_root: Path) -> list[dict[str, Any]]:
    return [
        checklist("productStructuredSnapshots", "Codex/browser structured product snapshots exist before content generation.", [str(run_root / "product-url-reader/<id>/structured-product-page.json")]),
        checklist("viralMaterials", "Viral material library and creator leaderboard exist or show browser/manual evidence gaps.", [str(run_root / "reports/promotion-manager/competitors/viral-content-library.json"), str(run_root / "reports/promotion-manager/competitors/creator-leaderboard.json")]),
        checklist("generatedCopyAndVideo", "Platform copy and MP4 files exist for the selected platforms.", [str(run_root / "reports/promotion-manager/generated-content/<product>-platform-content.json"), str(run_root / "videos/*.mp4")]),
        checklist("publishReadiness", "Publish queue, setup guide, and readiness report exist before any platform write.", [str(run_root / "reports/promotion-manager/publish-readiness/publish-readiness.json"), str(run_root / "reports/promotion-manager/publish-setup/platform-setup-guide.md")]),
        checklist("realPublishedUrls", "Real published URLs or official execution reports are registered before metrics recovery.", [str(run_root / "reports/promotion-manager/published-items/published-items.json")]),
        checklist("realMetrics", "Views, likes, comments, shares, clicks, leads, orders, or revenue come from public pages, official APIs, structured snapshots, screenshots, or business exports.", [str(run_root / "reports/promotion-manager/metrics-recovery/metrics-recovery.json")]),
        checklist("nextRound", "Next-round recommendations are generated from real recovered evidence or explicitly remain waiting_real_data.", [str(run_root / "reports/promotion-manager/optimization/next-round-optimization.json")]),
        checklist("finalReadiness", "Final readiness matrix records remaining platform, credential, data, or Skill-sync gates.", [str(out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json")]),
    ]


def checklist(item_id: str, requirement: str, evidence_paths: list[str]) -> dict[str, Any]:
    return {"id": item_id, "requirement": requirement, "evidencePaths": evidence_paths}


def platform_gates() -> list[dict[str, str]]:
    return [
        {"platform": "youtube", "gate": "OAuth channel authorization, YouTube Data API quota, reviewed MP4/title/description, and approval are required for upload."},
        {"platform": "github", "gate": "GITHUB_TOKEN or GH_TOKEN with target repository write permission and approval are required for repository writes."},
        {"platform": "zhihu", "gate": "Manual/browser-assisted creator workflow remains required unless verified official publishing access exists."},
        {"platform": "xiaohongshu", "gate": "Manual/browser-assisted creator workflow remains required unless verified official publishing access exists."},
        {"platform": "douyin", "gate": "Current Douyin publishing uses browser-assisted/manual payloads; attach the video file as an asset and let the account owner complete final publish."},
        {"platform": "metrics_revenue", "gate": "Orders and revenue require business exports or analytics evidence matched to specific content."},
    ]


def approval_gates() -> list[dict[str, str]]:
    return [
        {"approval": PUBLISH_APPROVAL, "scope": "official platform writes only after dry-run review, credentials, target, and account authorization are ready"},
        {"approval": SKILL_SYNC_APPROVAL, "scope": "sync reviewed source files into the installed Codex Skill directory"},
    ]


def artifact_paths(out_dir: Path) -> dict[str, str]:
    directory = report_dir(out_dir)
    return {
        "json": str(directory / "real-run-playbook.json"),
        "markdown": str(directory / "real-run-playbook.md"),
        "powershell": str(directory / "real-run-commands.ps1"),
    }


def guardrails() -> list[str]:
    return [
        "Do not auto-login, bypass captcha/risk controls, extract cookies, or use private endpoints.",
        "Do not store or print API keys, OAuth tokens, passwords, cookies, or hidden browser tokens.",
        "Do not click final publish in browser-assisted flows; stop for user-visible account action.",
        "Do not fabricate published URLs, platform metrics, comments, orders, revenue, or conversion attribution.",
        "Treat placeholder commands as templates until real product URLs, targets, credentials, and evidence files exist.",
    ]


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "real-run-playbook.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "real-run-playbook.md").write_text(render_markdown(report) + "\n", encoding="utf-8")
    (directory / "real-run-commands.ps1").write_text(render_powershell(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Run Playbook",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Output: {report['outDir']}",
        "",
        report["operatingRule"],
        "",
        "## Phases",
    ]
    for phase_item in report["phases"]:
        lines.extend(["", f"### {phase_item['id']}", phase_item["label"]])
        for command_item in phase_item["commands"]:
            approval = f" approval=`{command_item['approvalRequired']}`" if command_item.get("approvalRequired") else ""
            lines.append(f"- `{command_item['id']}`{approval}: `{command_item['command']}`")
            if command_item.get("requires"):
                lines.append(f"  Requires: {', '.join(command_item['requires'])}")
            if command_item.get("proves"):
                lines.append(f"  Proves: {', '.join(command_item['proves'])}")
    lines.extend(["", "## Evidence Checklist"])
    for item in report["evidenceChecklist"]:
        lines.append(f"- `{item['id']}`: {item['requirement']}")
        lines.append(f"  Evidence: {', '.join(item['evidencePaths'])}")
    lines.extend(["", "## Platform Gates"])
    lines.extend(f"- {item['platform']}: {item['gate']}" for item in report["platformGates"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_powershell(report: dict[str, Any]) -> str:
    lines = [
        "# Generated by scripts/real_run_playbook.py",
        "# Review each command before running. Commands with approval gates must not run until the gate is intentionally satisfied.",
        "",
    ]
    for phase_item in report["phases"]:
        lines.append(f"# {phase_item['id']}: {phase_item['label']}")
        for command_item in phase_item["commands"]:
            approval = command_item.get("approvalRequired") or ""
            if approval:
                lines.append(f"# Requires approval phrase: {approval}")
            lines.append(command_item["command"])
            lines.append("")
    return "\n".join(lines).rstrip()


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/real-run-playbook"


def display_command(parts: list[str]) -> str:
    return " ".join(quote_arg(str(part)) for part in parts)


def quote_arg(value: str) -> str:
    if value == "":
        return '""'
    if any(ch.isspace() for ch in value) or any(ch in value for ch in ['"', "'", "<", ">", "*"]):
        return '"' + value.replace('"', '\\"') + '"'
    return value


def append_if(command: list[str], flag: str, value: str) -> None:
    if value:
        command.extend([flag, value])


def append_many(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        append_if(command, flag, value)


if __name__ == "__main__":
    main()
