#!/usr/bin/env python3
"""Audit final-agent readiness for the viral product promotion skill."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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
    grouped_env_ready,
    load_project_env,
    preparse_env_file,
    present_env_names,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
SAFE_INSTALLS = {"playwright_chromium"}


SCRIPT_REQUIREMENTS = {
    "browser_snapshot": "browser_snapshot.py",
    "browser_video_sampler": "browser_video_sampler.py",
    "web_data_provider": "web_data_provider.py",
    "product_url_discovery": "product_url_discovery.py",
    "product_url_reader": "product_url_reader.py",
    "product_batch_runner": "product_batch_runner.py",
    "product_intake": "product_intake.py",
    "run_workflow": "run_promotion_workflow.py",
    "platform_search_browser": "platform_search_browser.py",
    "platform_search_capture": "platform_search_capture.py",
    "competitor_collector": "competitor_collector.py",
    "viral_discovery_runner": "viral_discovery_runner.py",
    "multi_query_viral_discovery": "multi_query_viral_discovery.py",
    "viral_evidence_inbox_setup": "viral_evidence_inbox_setup.py",
    "viral_evidence_inbox": "viral_evidence_inbox.py",
    "viral_content_library": "viral_content_library.py",
    "creator_leaderboard": "creator_leaderboard.py",
    "creator_follow_up_runner": "creator_follow_up_runner.py",
    "follow_up_capture_runner": "follow_up_capture_runner.py",
    "competitor_content_enhancer": "competitor_content_enhancer.py",
    "render_video": "render_video.py",
    "media_asset_pack": "media_asset_pack.py",
    "publish_queue": "publish_queue.py",
    "publish_readiness": "publish_readiness_runner.py",
    "publish_setup_assistant": "publish_setup_assistant.py",
    "launch_unlock_pack": "launch_unlock_pack.py",
    "browser_publish_assistant": "browser_publish_assistant.py",
    "browser_publish_form_fill": "browser_publish_form_fill.py",
    "browser_publish_session": "browser_publish_session.py",
    "platform_access_audit": "platform_access_audit.py",
    "platform_capabilities": "platform_capabilities.py",
    "publish_executor": "publish_executor.py",
    "youtube_oauth_publish": "youtube_oauth_publish.py",
    "youtube_credential_check": "youtube_credential_check.py",
    "published_items": "published_items.py",
    "publish_url_capture": "publish_url_capture.py",
    "post_publish_metrics_capture": "post_publish_metrics_capture.py",
    "comment_evidence_capture": "comment_evidence_capture.py",
    "business_attribution": "business_attribution.py",
    "real_evidence_inbox_setup": "real_evidence_inbox_setup.py",
    "real_evidence_inbox": "real_evidence_inbox.py",
    "performance_monitor": "performance_monitor.py",
    "metrics_intake": "metrics_intake.py",
    "metric_parsing": "metric_parsing.py",
    "metrics_recovery": "metrics_recovery.py",
    "next_round_optimizer": "next_round_optimizer.py",
    "automation_scheduler": "automation_scheduler.py",
    "promotion_cycle_runner": "promotion_cycle_runner.py",
    "real_run_playbook": "real_run_playbook.py",
    "skill_entry": "skill_entry.py",
    "final_capability_audit": "final_capability_audit.py",
    "final_capability_runner": "final_capability_runner.py",
    "final_capability_readiness": "final_capability_readiness.py",
    "self_evolution_audit": "self_evolution_audit.py",
    "billing_contract_simulator": "billing_contract_simulator.py",
    "package_browser_extension": "package_browser_extension.py",
    "completion_roadmap": "completion_roadmap.py",
    "operator_action_checklist": "operator_action_checklist.py",
}


CREDENTIALS = {
    "youtube_search_metrics": ["YOUTUBE_API_KEY"],
    "youtube_oauth_upload": list(YOUTUBE_ACCESS_TOKEN_ENVS),
    "youtube_oauth_flow": list(YOUTUBE_CLIENT_ID_ENVS + YOUTUBE_CLIENT_SECRET_ENVS),
    "github_write": ["GITHUB_TOKEN", "GH_TOKEN"],
    "tiktok_direct_post": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
    "firecrawl_web_data": ["FIRECRAWL_API_KEY"],
}

CREDENTIAL_ANY_CAPABILITIES = {"youtube_search_metrics", "youtube_oauth_upload", "github_write", "firecrawl_web_data"}
CREDENTIAL_GROUP_CAPABILITIES = {
    "youtube_oauth_flow": [YOUTUBE_CLIENT_ID_ENVS, YOUTUBE_CLIENT_SECRET_ENVS],
}


OFFICIAL_SOURCES = [
    {
        "platform": "youtube",
        "capability": "upload",
        "url": "https://developers.google.com/youtube/v3/docs/videos/insert",
        "notes": "Official videos.insert upload endpoint; OAuth scope, quota, and audit restrictions apply.",
    },
    {
        "platform": "github",
        "capability": "repository_content_write",
        "url": "https://docs.github.com/en/rest/repos/contents",
        "notes": "Official create/update file contents endpoint; write permissions are required.",
    },
    {
        "platform": "tiktok",
        "capability": "direct_post",
        "url": "https://developers.tiktok.com/doc/content-posting-api-get-started/",
        "notes": "Direct Post requires app product setup, video.publish approval, creator authorization, and audit for public visibility.",
    },
    {
        "platform": "douyin",
        "capability": "reserved_upload_create_publish",
        "url": "https://open.douyin.com/platform/resource/docs/ability/content-management/douyin-publish-solution",
        "notes": "Official open-platform upload/create is kept as a reserved future port. Current operator flow uses browser-assisted/manual publishing because Douyin authorization is unavailable.",
    },
    {
        "platform": "xiaohongshu",
        "capability": "open_platform_docs",
        "url": "https://open.xiaohongshu.com/document/api",
        "notes": "Treat general note publishing as manual/browser-assisted unless official creator publishing access is verified.",
    },
]


GITHUB_DOC_FILES = [
    "README.md",
    "README.zh-CN.md",
    "README.en.md",
    "docs/installation.md",
    "docs/zh-CN/installation.md",
    "docs/usage.md",
    "docs/zh-CN/usage.md",
    "docs/browser-extension.md",
    "docs/zh-CN/browser-extension.md",
    "docs/extension-store-submission.md",
    "docs/zh-CN/extension-store-submission.md",
    "docs/subscription-pricing.md",
    "docs/billing-backend-contract.md",
    "docs/final-capability-map.md",
    "docs/100-percent-completion-roadmap.md",
    "docs/zh-CN/100-percent-completion-guide.md",
    "docs/open-source-integration.md",
    "docs/legal/privacy-policy.md",
    "docs/legal/terms-of-service.md",
    "docs/legal/refund-policy.md",
    "docs/legal/support.md",
    "docs/store/chrome-listing.md",
    "docs/store/edge-listing.md",
    "docs/store/reviewer-notes.md",
    "docs/store/screenshot-plan.md",
    "deploy/promotion-manager/README.md",
    "deploy/promotion-manager/.env.production.example",
    "deploy/promotion-manager/nginx-promotion-manager.conf",
    "deploy/promotion-manager/enhe-promotion-manager-api.service",
    "deploy/promotion-manager/enhe-promotion-manager-worker.service",
]


BROWSER_EXTENSION_FILES = [
    "browser-extension/manifest.json",
    "browser-extension/billing-contract.json",
    "browser-extension/popup.html",
    "browser-extension/popup.css",
    "browser-extension/popup.js",
    "browser-extension/icons/icon16.png",
    "browser-extension/icons/icon48.png",
    "browser-extension/icons/icon128.png",
]


BACKEND_DEPLOY_FILES = [
    "backend/license-service/package.json",
    "backend/license-service/.env.example",
    "backend/license-service/README.md",
    "backend/license-service/src/server.js",
    "backend/license-service/src/state-store.js",
    "backend/license-service/src/hosted-worker.js",
    "backend/license-service/src/migrate.js",
    "backend/license-service/src/worker.js",
    "backend/license-service/migrations/001_state_store.sql",
    "deploy/promotion-manager/README.md",
    "deploy/promotion-manager/.env.production.example",
    "deploy/promotion-manager/nginx-promotion-manager.conf",
    "deploy/promotion-manager/enhe-promotion-manager-api.service",
    "deploy/promotion-manager/enhe-promotion-manager-worker.service",
]


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.install_safe_missing_tools:
        install_safe_missing_tools(args)
    report = build_report(args, out_dir, env_load)
    write_report(out_dir, report)
    print(f"Final capability audit written to: {(audit_dir(out_dir) / 'final-capability-audit.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit final capability readiness for the product promotion Skill.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before auditing credential presence. Values are never written to reports.")
    parser.add_argument(
        "--skip-runtime-checks",
        action="store_true",
        help="Skip slower runtime launch checks such as Playwright Chromium launch.",
    )
    parser.add_argument(
        "--install-safe-missing-tools",
        action="store_true",
        help="Install only allowlisted official runtime tools that are missing.",
    )
    parser.add_argument(
        "--safe-install",
        action="append",
        default=[],
        choices=sorted(SAFE_INSTALLS),
        help="Allowlisted runtime install to attempt when --install-safe-missing-tools is supplied.",
    )
    return parser.parse_args()


def install_safe_missing_tools(args: argparse.Namespace) -> None:
    installs = set(args.safe_install or [])
    if not installs:
        installs = {"playwright_chromium"}
    unsupported = installs - SAFE_INSTALLS
    if unsupported:
        raise SystemExit(f"Unsupported safe installs: {', '.join(sorted(unsupported))}")
    if "playwright_chromium" in installs and not playwright_chromium_available(skip_runtime_checks=False):
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], cwd=ROOT, check=False)


def build_report(args: argparse.Namespace, out_dir: Path, env_load: dict[str, object]) -> dict[str, Any]:
    scripts = script_status()
    tools = tool_status(skip_runtime_checks=args.skip_runtime_checks)
    credentials = credential_status()
    platforms = platform_status(scripts, tools, credentials)
    self_evolution_audit = run_self_evolution_audit(args, out_dir, scripts)
    requirements = requirement_status(scripts, tools, credentials, platforms, self_evolution_audit)
    actions = next_actions(requirements, tools, credentials, out_dir)
    return {
        "generatedAt": TODAY,
        "root": str(ROOT),
        "outDir": str(out_dir),
        "envLoad": env_load,
        "finalStatus": final_status(requirements),
        "requirements": requirements,
        "platforms": platforms,
        "localTools": tools,
        "credentials": credentials,
        "scripts": scripts,
        "platformAccessAudit": platform_access_audit_status(scripts, out_dir),
        "selfEvolutionAudit": self_evolution_audit,
        "selfEvolution": self_evolution_status(tools, self_evolution_audit),
        "recommendedCommands": recommended_commands(out_dir),
        "nextActions": actions,
        "officialSources": OFFICIAL_SOURCES,
        "guardrails": [
            "Do not auto-login, bypass captcha, use private endpoints, or extract browser cookies/tokens.",
            "Do not print or write credential values; only credential presence is recorded.",
            "Do not claim published content until a real official execution report or published URL exists.",
            "Do not claim platform metrics, orders, or revenue unless official APIs, exports, screenshots, or business data prove them.",
            "Self-evolution may audit, learn, and install explicit allowlisted runtime dependencies, but it must not silently replace itself from unreviewed network code.",
        ],
    }


def script_status() -> dict[str, dict[str, Any]]:
    status = {}
    for key, filename in SCRIPT_REQUIREMENTS.items():
        path = SCRIPTS / filename
        status[key] = {"file": str(path), "exists": path.exists()}
    return status


def tool_status(skip_runtime_checks: bool) -> dict[str, dict[str, Any]]:
    return {
        "python": {
            "available": True,
            "version": sys.version.split()[0],
            "path": sys.executable,
        },
        "git": command_status("git"),
        "ffmpeg": command_status("ffmpeg"),
        "playwright": python_module_status("playwright"),
        "googleApiPythonClient": python_module_status("googleapiclient"),
        "googleAuthOauthlib": python_module_status("google_auth_oauthlib"),
        "googleAuthHttplib2": python_module_status("google_auth_httplib2"),
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
    if skip_runtime_checks:
        return False
    code = (
        "from playwright.sync_api import sync_playwright\n"
        "p=sync_playwright().start()\n"
        "b=p.chromium.launch(headless=True)\n"
        "b.close()\n"
        "p.stop()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def credential_status() -> dict[str, dict[str, Any]]:
    status = {}
    for capability, names in CREDENTIALS.items():
        present = present_env_names(names)
        if capability in CREDENTIAL_GROUP_CAPABILITIES:
            ready = grouped_env_ready(CREDENTIAL_GROUP_CAPABILITIES[capability])
        elif capability in CREDENTIAL_ANY_CAPABILITIES:
            ready = bool(present)
        else:
            ready = all(name in present for name in names)
        status[capability] = {
            "requiredEnv": names,
            "presentEnv": present,
            "blankEnv": blank_env_names(names),
            "ready": ready,
            "valuesStored": False,
        }
    status["business_exports"] = {
        "requiredEvidence": ["business CSV/JSON/text export or structured browser snapshot with orders, revenue, clicks, leads, or platform metrics"],
        "ready": False,
        "valuesStored": False,
    }
    return status


def platform_status(
    scripts: dict[str, dict[str, Any]],
    tools: dict[str, dict[str, Any]],
    credentials: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    browser_ready = bool(tools["playwright"]["available"]) and (
        bool(tools["playwrightChromium"]["available"]) or not tools["playwrightChromium"]["checked"]
    )
    shared_browser_search = scripts_ready(scripts, ["platform_search_browser", "platform_search_capture", "viral_content_library", "browser_video_sampler"])
    return {
        "youtube": {
            "viralSearch": status_value(scripts_ready(scripts, ["competitor_collector"]) or (shared_browser_search and browser_ready)),
            "webData": "optional_firecrawl_ready" if credentials["firecrawl_web_data"]["ready"] else "local_browser_static_fallback",
            "directPublish": "ready" if credentials["youtube_oauth_upload"]["ready"] else "needs_oauth_or_access_token",
            "metricsRecovery": "ready" if credentials["youtube_search_metrics"]["ready"] else "needs_youtube_api_key",
            "ordersRevenue": "business_export_required",
        },
        "github": {
            "viralSearch": status_value(scripts_ready(scripts, ["competitor_collector"])),
            "webData": "optional_firecrawl_ready" if credentials["firecrawl_web_data"]["ready"] else "local_public_api_fallback",
            "directPublish": "ready" if credentials["github_write"]["ready"] else "needs_github_token",
            "metricsRecovery": "ready_public_repo_metrics",
            "ordersRevenue": "business_export_required",
        },
        "zhihu": {
            "viralSearch": "browser_visible_ready" if shared_browser_search and browser_ready else "browser_runtime_required",
            "webData": "optional_firecrawl_ready" if credentials["firecrawl_web_data"]["ready"] else "browser_or_user_evidence_fallback",
            "directPublish": "manual_or_browser_assisted_only",
            "metricsRecovery": "manual_export_or_structured_snapshot_required",
            "ordersRevenue": "business_export_required",
        },
        "xiaohongshu": {
            "viralSearch": "browser_visible_ready" if shared_browser_search and browser_ready else "browser_runtime_required",
            "webData": "optional_firecrawl_ready" if credentials["firecrawl_web_data"]["ready"] else "browser_or_user_evidence_fallback",
            "directPublish": "manual_or_browser_assisted_only",
            "metricsRecovery": "manual_export_or_structured_snapshot_required",
            "ordersRevenue": "business_export_required",
        },
        "douyin": {
            "viralSearch": "browser_visible_ready" if shared_browser_search and browser_ready else "browser_runtime_required",
            "webData": "optional_firecrawl_ready" if credentials["firecrawl_web_data"]["ready"] else "browser_or_user_evidence_fallback",
            "directPublish": "browser_assisted_publish_selected",
            "metricsRecovery": "manual_structured_snapshot_or_official_export_required",
            "ordersRevenue": "business_export_required",
        },
        "tiktok": {
            "viralSearch": "browser_visible_ready" if shared_browser_search and browser_ready else "browser_runtime_required",
            "webData": "optional_firecrawl_ready" if credentials["firecrawl_web_data"]["ready"] else "browser_or_user_evidence_fallback",
            "directPublish": "official_app_authorization_required"
            if credentials["tiktok_direct_post"]["ready"]
            else "developer_app_scope_and_creator_auth_required",
            "metricsRecovery": "manual_structured_snapshot_or_official_export_required",
            "ordersRevenue": "business_export_required",
        },
    }


def requirement_status(
    scripts: dict[str, dict[str, Any]],
    tools: dict[str, dict[str, Any]],
    credentials: dict[str, dict[str, Any]],
    platforms: dict[str, dict[str, Any]],
    self_evolution_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    browser_intake_ready = scripts_ready(
        scripts,
        ["browser_snapshot", "product_url_discovery", "product_url_reader", "product_batch_runner", "product_intake", "run_workflow"],
    )
    browser_runtime_ready = bool(tools["playwright"]["available"]) and (
        bool(tools["playwrightChromium"]["available"]) or not tools["playwrightChromium"]["checked"]
    )
    web_data_ready = scripts_ready(scripts, ["web_data_provider"])
    platform_capabilities_ready = scripts_ready(scripts, ["platform_capabilities"])
    completion_roadmap_ready = scripts_ready(scripts, ["completion_roadmap"]) and (ROOT / "docs/100-percent-completion-roadmap.md").exists()
    operator_action_checklist_ready = scripts_ready(scripts, ["operator_action_checklist"]) and (
        ROOT / "docs/zh-CN/100-percent-completion-guide.md"
    ).exists()
    video_scripts_ready = scripts_ready(scripts, ["render_video", "media_asset_pack"])
    video_ready = video_scripts_ready and bool(tools["ffmpeg"]["available"])
    search_ready = scripts_ready(
        scripts,
        [
            "viral_discovery_runner",
            "multi_query_viral_discovery",
            "platform_search_browser",
            "platform_search_capture",
            "viral_evidence_inbox_setup",
            "viral_evidence_inbox",
            "viral_content_library",
            "creator_leaderboard",
            "creator_follow_up_runner",
            "follow_up_capture_runner",
            "browser_video_sampler",
        ],
    )
    publish_ready = scripts_ready(
        scripts,
        [
            "publish_queue",
            "publish_readiness",
            "browser_publish_assistant",
            "browser_publish_form_fill",
            "browser_publish_session",
            "publish_executor",
            "youtube_oauth_publish",
        ],
    )
    youtube_google_client_ready = all(
        bool(tools[name]["available"]) for name in ["googleApiPythonClient", "googleAuthOauthlib", "googleAuthHttplib2"]
    ) and (ROOT / "requirements-youtube.txt").exists()
    metrics_ready = scripts_ready(
        scripts,
        [
            "published_items",
            "publish_url_capture",
            "post_publish_metrics_capture",
            "comment_evidence_capture",
            "business_attribution",
            "real_evidence_inbox_setup",
            "real_evidence_inbox",
            "performance_monitor",
            "metrics_intake",
            "metric_parsing",
            "metrics_recovery",
            "next_round_optimizer",
        ],
    )
    optimization_ready = scripts_ready(scripts, ["next_round_optimizer"])
    cycle_ready = scripts_ready(
        scripts,
        ["promotion_cycle_runner", "automation_scheduler", "real_run_playbook", "skill_entry", "final_capability_runner", "next_round_optimizer"],
    )
    phase_reporting_ready = scripts_ready(
        scripts,
        ["real_run_playbook", "skill_entry", "final_capability_runner", "final_capability_readiness"],
    )
    docs = github_docs_status()
    extension = browser_extension_status()
    extension_limits = [
        "The extension can generate Skill, browser publish session, viral/real evidence inbox, readiness audit, and periodic automation commands, validate a license endpoint, and build a Chrome/Edge submission zip.",
        "The repository includes a Stripe-backed license service, PostgreSQL JSONB state backend, isolated hosted worker, same-host HTTPS deployment files, legal pages, listing drafts, screenshot plan, and reviewer notes.",
        "External account setup, live Stripe prices/webhooks, deployed HTTPS server configuration, hosted-worker capacity, and Chrome/Edge store approval remain operator-controlled launch gates.",
        "Remote code is not allowed in the extension package; hosted services may return data only.",
    ]
    if extension["hostedWorkerEnabled"] is True:
        extension_limits.insert(
            1,
            "Hosted usage reservation and hosted-run submission are enabled and remain subject to backend quota and authorization checks.",
        )
    elif extension["hostedWorkerEnabled"] is False:
        extension_limits.insert(
            1,
            "Hosted Worker is disabled; hosted usage reservation, hosted payload copying, and hosted-run submission are fail-closed. Local Skill runs remain available.",
        )
    else:
        extension_limits.insert(1, "Hosted Worker state could not be confirmed from the extension source.")
    full_platform_publish_ready = all(
        platforms[p]["directPublish"] == "ready" for p in ["youtube", "github", "zhihu", "xiaohongshu", "douyin"]
    )
    real_metrics_ready = metrics_ready and (
        credentials["youtube_search_metrics"]["ready"] or credentials["github_write"]["ready"]
    )
    self_evolution_report = read_report_reference(str(self_evolution_audit.get("report", ""))) if self_evolution_audit.get("reportExists") else {}
    self_evolution_operational = (
        scripts_ready(scripts, ["final_capability_audit", "self_evolution_audit"])
        and bool(self_evolution_audit.get("ready"))
        and str(self_evolution_report.get("status", "")).startswith(("ready_", "partial_ready_"))
    )

    return [
        {
            "id": "product_url_structured_intake",
            "label": "Automatically parse product URLs through Codex/browser structured snapshots",
            "status": "ready" if browser_intake_ready and browser_runtime_ready else "partial_ready",
            "evidence": scripts_present(
                scripts,
                ["browser_snapshot", "product_url_discovery", "product_url_reader", "product_batch_runner", "product_intake", "run_workflow"],
            ),
            "missing": missing_for_scripts(
                scripts,
                ["browser_snapshot", "product_url_discovery", "product_url_reader", "product_batch_runner", "product_intake", "run_workflow"],
            )
            + ([] if browser_runtime_ready else ["Playwright Chromium runtime not verified"]),
        },
        {
            "id": "viral_creator_content_research",
            "label": "Search and capture viral creators/content across YouTube, Zhihu, Xiaohongshu, Douyin, and GitHub",
            "status": "partial_ready" if search_ready else "not_ready",
            "evidence": scripts_present(
                scripts,
                [
                    "viral_discovery_runner",
                    "multi_query_viral_discovery",
                    "platform_search_browser",
                    "platform_search_capture",
                    "viral_evidence_inbox_setup",
                    "viral_evidence_inbox",
                    "viral_content_library",
                    "creator_leaderboard",
                    "creator_follow_up_runner",
                    "follow_up_capture_runner",
                    "browser_video_sampler",
                ],
            ),
            "missing": [] if search_ready else ["search/capture/ranking scripts"],
            "limits": [
                "YouTube and GitHub can use official/public connectors.",
                "Zhihu, Xiaohongshu, Douyin, and TikTok require browser-visible evidence or official access; no private endpoint or anti-bot bypass is allowed.",
                "Video sampling captures browser-visible video metadata and frame screenshots only; it does not download private media streams or extract hidden media tokens.",
                "When platform search is blocked or unstable, viral_evidence_inbox_setup.py and viral_evidence_inbox.py provide a user-filled evidence fallback without fabricating metrics.",
            ],
        },
        {
            "id": "optional_firecrawl_web_data_backend",
            "label": "Optionally use Firecrawl-style Search, Scrape, Map, Crawl, and Batch Scrape for public web evidence",
            "status": "ready" if web_data_ready else "not_ready",
            "evidence": scripts_present(scripts, ["web_data_provider", "product_url_reader", "product_url_discovery", "platform_search_browser"]),
            "missing": [] if web_data_ready else ["web_data_provider.py"],
            "limits": [
                "The provider is optional; local browser/static/user-evidence fallbacks remain available when FIRECRAWL_API_KEY is absent.",
                "Only public URLs and public search results may be sent to Firecrawl or a self-hosted compatible provider.",
                "Self-hosting Firecrawl should be isolated from the lightweight license service and may require a larger server.",
            ],
        },
        {
            "id": "copy_and_real_video_generation",
            "label": "Generate real copy, scripts, storyboards, MP4 video files, cover images, and detail images",
            "status": "ready" if video_ready else "partial_ready",
            "evidence": scripts_present(scripts, ["competitor_content_enhancer", "render_video", "media_asset_pack"]),
            "missing": [] if video_ready else ["ffmpeg runtime"] if video_scripts_ready else ["render_video.py", "media_asset_pack.py"],
        },
        {
            "id": "all_platform_auto_publish",
            "label": "Publish through official APIs where available and browser-assisted/manual flows where required",
            "status": "ready" if publish_ready and full_platform_publish_ready else "blocked_by_authorization_or_platform_limits",
            "evidence": scripts_present(
                scripts,
                [
                    "platform_access_audit",
                    "publish_queue",
                    "publish_readiness",
                    "publish_setup_assistant",
                    "launch_unlock_pack",
                    "browser_publish_assistant",
                    "browser_publish_form_fill",
                    "browser_publish_session",
                    "publish_executor",
                    "youtube_oauth_publish",
                ],
            ),
            "missing": missing_publish_credentials(credentials),
            "limits": [
                "GitHub and YouTube writes require official credentials plus explicit publish approval.",
                "Zhihu, Xiaohongshu, and Douyin remain manual/browser-assisted unless official creator publishing access is verified.",
                "Douyin official upload/create code is a reserved future port only; current operation does not require DOUYIN_* credentials.",
                "TikTok requires approved open-platform app scopes and user authorization.",
            ],
        },
        {
            "id": "youtube_google_api_python_client_dependency",
            "label": "Install and record the official Google API Python client dependency for YouTube Data API publishing",
            "status": "ready" if youtube_google_client_ready else "partial_ready",
            "evidence": [
                str(ROOT / "requirements-youtube.txt"),
                f"googleapiclient={tools['googleApiPythonClient']['available']}",
                f"google_auth_oauthlib={tools['googleAuthOauthlib']['available']}",
                f"google_auth_httplib2={tools['googleAuthHttplib2']['available']}",
            ],
            "missing": []
            if youtube_google_client_ready
            else [
                "Install YouTube dependencies with: python -m pip install -r requirements-youtube.txt",
                "requirements-youtube.txt",
            ],
            "limits": [
                "The client library enables official YouTube Data API calls, but real uploads still require OAuth consent, approved scopes, quota, target video files, and explicit publish approval.",
            ],
        },
        {
            "id": "real_metrics_orders_revenue_recovery",
            "label": "Recover real views, likes, comments, orders, revenue, and business outcomes",
            "status": "partial_ready" if metrics_ready else "not_ready",
            "evidence": scripts_present(
                scripts,
                [
                    "published_items",
                    "publish_url_capture",
                    "post_publish_metrics_capture",
                    "comment_evidence_capture",
                    "business_attribution",
                    "real_evidence_inbox_setup",
                    "real_evidence_inbox",
                    "launch_unlock_pack",
                    "performance_monitor",
                    "metrics_intake",
                    "metric_parsing",
                    "metrics_recovery",
                    "next_round_optimizer",
                ],
            ),
            "missing": [] if real_metrics_ready else ["published URLs, official metrics credentials, structured metric snapshots, or business exports"],
            "limits": [
                "Social metrics require official APIs, public pages, browser-visible structured snapshots, screenshots, or exports.",
                "Orders and revenue require business-system exports; public platform pages cannot prove revenue.",
            ],
        },
        {
            "id": "retrospective_next_round_optimization",
            "label": "Turn real metrics, comments, orders, and revenue into next-round content and publish actions",
            "status": "ready" if optimization_ready else "not_ready",
            "evidence": scripts_present(
                scripts,
                ["next_round_optimizer", "metrics_recovery", "comment_evidence_capture", "business_attribution", "performance_monitor", "launch_unlock_pack"],
            ),
            "missing": [] if optimization_ready else ["next_round_optimizer.py"],
            "limits": [
                "The optimizer uses recovered evidence only and outputs waiting_real_data when metrics, comments, and business attribution are absent.",
                "It prepares next-round recommendations and commands; platform publishing still follows the approval and credential gates.",
            ],
        },
        {
            "id": "platform_registry_and_monetization_blueprint",
            "label": "Expose platform capability registry and creator-task monetization blueprint inspired by AiToEarn",
            "status": "ready" if platform_capabilities_ready else "not_ready",
            "evidence": scripts_present(scripts, ["platform_capabilities"]),
            "missing": [] if platform_capabilities_ready else ["platform_capabilities.py"],
            "limits": [
                "The current implementation is a machine-readable registry and safe MVP blueprint, not a live creator marketplace.",
                "CPS/CPE/CPM settlement remains manual-review-first until real platform, business, payment, and legal gates are connected.",
                "Store-safe engagement supports monitoring and AI reply drafts; final likes, follows, comments, and DMs require human confirmation.",
            ],
        },
        {
            "id": "completion_roadmap_to_100_percent",
            "label": "Document every module gap to 100%, what Codex can do, open-source references, operator actions, and acceptance evidence",
            "status": "ready" if completion_roadmap_ready else "partial_ready",
            "evidence": scripts_present(scripts, ["completion_roadmap"])
            + ([str(ROOT / "docs/100-percent-completion-roadmap.md")] if (ROOT / "docs/100-percent-completion-roadmap.md").exists() else []),
            "missing": [] if completion_roadmap_ready else ["scripts/completion_roadmap.py or docs/100-percent-completion-roadmap.md"],
            "limits": [
                "The roadmap can make external gates explicit, but it cannot complete operator-owned platform approvals, store approvals, live Stripe setup, server deployment, or real creator payouts.",
                "A module reaches production 100% only when its acceptance evidence exists for a current real run.",
            ],
        },
        {
            "id": "zh_cn_operator_action_checklist_to_100_percent",
            "label": "Provide a Chinese beginner-friendly action checklist for reaching 100% module readiness",
            "status": "ready" if operator_action_checklist_ready else "partial_ready",
            "evidence": scripts_present(scripts, ["operator_action_checklist"])
            + (
                [str(ROOT / "docs/zh-CN/100-percent-completion-guide.md")]
                if (ROOT / "docs/zh-CN/100-percent-completion-guide.md").exists()
                else []
            ),
            "missing": []
            if operator_action_checklist_ready
            else ["scripts/operator_action_checklist.py or docs/zh-CN/100-percent-completion-guide.md"],
            "limits": [
                "The checklist gives beginner execution steps and acceptance evidence, but operator-owned accounts, approvals, server deployment, live payments, and real publication evidence still have to be completed outside Codex.",
            ],
        },
        {
            "id": "periodic_codex_operation",
            "label": "Run the whole promotion loop periodically in Codex/local automation",
            "status": "ready" if cycle_ready else "not_ready",
            "evidence": scripts_present(
                scripts,
                ["promotion_cycle_runner", "automation_scheduler", "real_run_playbook", "skill_entry", "final_capability_runner", "next_round_optimizer"],
            ),
            "missing": []
            if cycle_ready
            else missing_for_scripts(
                scripts,
                ["promotion_cycle_runner", "automation_scheduler", "real_run_playbook", "skill_entry", "final_capability_runner", "next_round_optimizer"],
            ),
        },
        {
            "id": "github_documentation_and_install_tutorial",
            "label": "Publish GitHub-facing project introduction, usage guide, installation tutorial, and final capability map",
            "status": "ready" if docs["ready"] else "partial_ready",
            "evidence": docs["evidence"],
            "missing": docs["missing"],
            "limits": [
                "Documentation must be updated when platform access, pricing, or extension behavior changes.",
                "Pricing assumptions must be recalculated from real token and infrastructure logs before public launch.",
            ],
        },
        {
            "id": "browser_extension_operator_ui_subscription",
            "label": "Provide a Chrome MV3 browser extension with operator UI, subscription hooks, hosted-run submission, deployable license backend, store materials, legal pages, and ENHE website links",
            "status": "ready" if extension["ready"] else "partial_ready",
            "evidence": extension["evidence"],
            "missing": extension["missing"],
            "limits": extension_limits,
        },
        {
            "id": "phase_progress_reporting",
            "label": "Report progress after each stage with completed goals, unfinished goals, next plan, and estimated remaining time",
            "status": "ready" if phase_reporting_ready else "partial_ready",
            "evidence": scripts_present(
                scripts,
                ["real_run_playbook", "skill_entry", "final_capability_runner", "final_capability_readiness"],
            ),
            "missing": []
            if phase_reporting_ready
            else missing_for_scripts(
                scripts,
                ["real_run_playbook", "skill_entry", "final_capability_runner", "final_capability_readiness"],
            ),
            "limits": [
                "Progress reports are generated from completed local stages and evidence paths.",
                "Time estimates are planning estimates; platform review, account authorization, and real metrics arrival can change them.",
            ],
        },
        {
            "id": "fully_autonomous_self_evolution",
            "label": "Research, install tools, keep learning, and upgrade the Skill itself",
            "status": "ready_review_gated_autonomy" if self_evolution_operational else "partial_ready_review_gated_autonomy",
            "evidence": scripts_present(scripts, ["final_capability_audit", "self_evolution_audit"])
            + ([str(self_evolution_audit.get("report"))] if self_evolution_audit.get("reportExists") else []),
            "missing": [] if self_evolution_operational else ["self_evolution_audit.py did not produce a ready controlled-autonomy report"],
            "limits": [
                "The Skill can audit runtime tools, repository state, installed Skill drift, and safe upgrade actions.",
                "The Skill can install explicit allowlisted runtime dependencies and sync reviewed local Skill files when commanded with approval.",
                "It emits a reviewRequiredUpgradeRequests queue for tool installs, Skill sync, and platform-learning refreshes.",
                "It must not silently download unreviewed network code, store secrets, or replace itself without a clear source/risk note.",
            ],
        },
    ]


def github_docs_status() -> dict[str, Any]:
    missing = [path for path in GITHUB_DOC_FILES if not (ROOT / path).exists()]
    evidence = [str(ROOT / path) for path in GITHUB_DOC_FILES if (ROOT / path).exists()]
    required_markers = {
        "README.md": [
            "ENHE Product Promo Maker",
            "Quick Start",
            "Browser Extension",
            "Subscription Model",
            "Safety Gates",
            "Installation",
        ],
        "docs/installation.md": ["Installation", "Install As A Codex Skill", "Verify"],
        "docs/usage.md": ["One Product URL", "Publishing", "Metrics And Next Round"],
        "docs/browser-extension.md": [
            "Browser Extension",
            "Command types",
            "Subscription Flow",
            "Build Store Submission Package",
            "Reference Simulator",
            "Developer Info",
        ],
        "docs/zh-CN/browser-extension.md": ["浏览器插件", "收费订阅", "打包成上架包", "开发者信息"],
        "docs/extension-store-submission.md": [
            "Extension Store Submission",
            "Chrome Web Store Steps",
            "Microsoft Edge Add-ons Steps",
            "privacy policy",
            "remote code",
        ],
        "docs/zh-CN/extension-store-submission.md": [
            "ENHE 产品推广素材生成器浏览器扩展上架指南",
            "Chrome Web Store 上架步骤",
            "Microsoft Edge Add-ons 上架步骤",
            "隐私政策",
            "remote code",
        ],
        "docs/subscription-pricing.md": ["Subscription Pricing", "Credit Model", "Browser publish session", "Plans"],
        "docs/billing-backend-contract.md": [
            "Billing Backend Contract",
            "Usage Authorization",
            "Webhooks",
            "Loss-Control Rules",
            "Reference Simulator",
        ],
        "docs/final-capability-map.md": ["Final Capability Map", "Acceptance Command"],
        "docs/100-percent-completion-roadmap.md": ["100% Completion Roadmap", "Detailed user steps", "Acceptance evidence"],
        "docs/zh-CN/100-percent-completion-guide.md": ["100% 完成指南", "新手步骤", "验收证据"],
        "docs/legal/privacy-policy.md": ["Privacy Policy", "Data We Do Not Collect"],
        "docs/legal/terms-of-service.md": ["Terms Of Service", "Publishing Boundary"],
        "docs/legal/refund-policy.md": ["Refund Policy", "Credit Usage"],
        "docs/legal/support.md": ["Support", "Hosted run ID"],
        "docs/store/chrome-listing.md": ["Chrome Web Store Listing Draft", "Permission Justification"],
        "docs/store/edge-listing.md": ["Microsoft Edge Add-ons Listing Draft", "Certification Notes"],
        "docs/store/reviewer-notes.md": ["Store Reviewer Notes", "Manifest V3"],
        "docs/store/screenshot-plan.md": ["Store Screenshot Plan", "Hosted run"],
        "deploy/promotion-manager/README.md": ["same HTTPS host", "Server Requirement", "systemd"],
        "deploy/promotion-manager/.env.production.example": ["DATABASE_URL=", "HOSTED_RUN_OUTPUT_ROOT="],
        "deploy/promotion-manager/nginx-promotion-manager.conf": ["/api/promotion-manager/", "/promotion-manager/privacy"],
        "deploy/promotion-manager/enhe-promotion-manager-api.service": ["ExecStart", "api.env"],
        "deploy/promotion-manager/enhe-promotion-manager-worker.service": ["ExecStart", "api.env"],
    }
    for path, markers in required_markers.items():
        if not (ROOT / path).exists():
            continue
        text = safe_read(ROOT / path)
        for marker in markers:
            if marker not in text:
                missing.append(f"{path} missing marker: {marker}")
    return {
        "ready": not missing,
        "evidence": evidence,
        "missing": missing,
    }


def browser_extension_status() -> dict[str, Any]:
    missing = [path for path in BROWSER_EXTENSION_FILES if not (ROOT / path).exists()]
    evidence = [str(ROOT / path) for path in BROWSER_EXTENSION_FILES if (ROOT / path).exists()]
    hosted_worker_enabled: bool | None = None
    for path in BACKEND_DEPLOY_FILES:
        full_path = ROOT / path
        if full_path.exists():
            evidence.append(str(full_path))
        else:
            missing.append(path)
    simulator_path = ROOT / "scripts/billing_contract_simulator.py"
    if simulator_path.exists():
        evidence.append(str(simulator_path))
        simulator_text = safe_read(simulator_path)
        for marker in ["demo-hosted-run", "hosted-run", "accept_hosted_run", "complete_hosted_run", "hostedRuns"]:
            if marker not in simulator_text:
                missing.append(f"scripts/billing_contract_simulator.py missing marker: {marker}")
    else:
        missing.append("scripts/billing_contract_simulator.py")
    package_script_path = ROOT / "scripts/package_browser_extension.py"
    if package_script_path.exists():
        evidence.append(str(package_script_path))
        package_script_text = safe_read(package_script_path)
        for marker in ["browser-extension-package-report.json", "noRemoteExecutableCode", "icons/icon128.png"]:
            if marker not in package_script_text:
                missing.append(f"scripts/package_browser_extension.py missing marker: {marker}")
    else:
        missing.append("scripts/package_browser_extension.py")
    manifest_path = ROOT / "browser-extension/manifest.json"
    contract_path = ROOT / "browser-extension/billing-contract.json"
    popup_path = ROOT / "browser-extension/popup.html"
    script_path = ROOT / "browser-extension/popup.js"
    style_path = ROOT / "browser-extension/popup.css"
    manifest = read_json_file(manifest_path)
    if manifest:
        if manifest.get("manifest_version") != 3:
            missing.append("browser-extension/manifest.json must use manifest_version 3")
        action = manifest.get("action") if isinstance(manifest.get("action"), dict) else {}
        if action.get("default_popup") != "popup.html":
            missing.append("browser-extension/manifest.json must declare popup.html as default_popup")
        icons = manifest.get("icons") if isinstance(manifest.get("icons"), dict) else {}
        action_icons = action.get("default_icon") if isinstance(action.get("default_icon"), dict) else {}
        for size in ["16", "48", "128"]:
            icon = str(icons.get(size) or "")
            action_icon = str(action_icons.get(size) or "")
            if not icon or not (ROOT / "browser-extension" / icon).exists():
                missing.append(f"browser-extension/manifest.json missing packaged icon {size}")
            if not action_icon or not (ROOT / "browser-extension" / action_icon).exists():
                missing.append(f"browser-extension/manifest.json missing action icon {size}")
        csp = manifest.get("content_security_policy") if isinstance(manifest.get("content_security_policy"), dict) else {}
        if "script-src 'self'" not in str(csp.get("extension_pages", "")):
            missing.append("browser-extension/manifest.json must keep extension scripts local")
    elif manifest_path.exists():
        missing.append("browser-extension/manifest.json is invalid JSON")
    contract = read_json_file(contract_path)
    if contract:
        for key in [
            "checkoutUrl",
            "customerPortalUrl",
            "licenseEndpoint",
            "usageAuthorizeEndpoint",
            "usageCommitEndpoint",
            "hostedRunEndpoint",
            "hostedRunStatusEndpointTemplate",
            "legalUrls",
        ]:
            if not contract.get(key):
                missing.append(f"browser-extension/billing-contract.json missing key: {key}")
        legal_urls = contract.get("legalUrls") if isinstance(contract.get("legalUrls"), dict) else {}
        for key in ["privacyPolicy", "termsOfService", "refundPolicy", "support"]:
            if not legal_urls.get(key):
                missing.append(f"browser-extension/billing-contract.json missing legal URL: {key}")
        credit_costs = contract.get("creditCosts") if isinstance(contract.get("creditCosts"), dict) else {}
        for workflow in [
            "browser_publish_session",
            "viral_evidence_inbox_setup",
            "viral_evidence_inbox",
            "real_evidence_inbox_setup",
            "real_evidence_inbox",
            "performance_monitor",
            "launch_unlock_pack",
            "final_readiness_audit",
            "automation_config_init",
            "automation_due_run",
            "automation_windows_task",
        ]:
            if workflow not in credit_costs:
                missing.append(f"browser-extension/billing-contract.json missing credit cost: {workflow}")
        license_body = (contract.get("licenseRequest") or {}).get("body") if isinstance(contract.get("licenseRequest"), dict) else {}
        if not isinstance(license_body, dict) or "commandType" not in license_body:
            missing.append("browser-extension/billing-contract.json license request must include commandType")
        usage_body = (contract.get("usageAuthorizeRequest") or {}).get("body") if isinstance(contract.get("usageAuthorizeRequest"), dict) else {}
        if not isinstance(usage_body, dict):
            missing.append("browser-extension/billing-contract.json must include usageAuthorizeRequest.body")
        else:
            for key in ["licenseKey", "workflowType", "estimatedCredits", "idempotencyKey", "commandType"]:
                if key not in usage_body:
                    missing.append(f"browser-extension/billing-contract.json usageAuthorizeRequest missing key: {key}")
        hosted_run_body = (contract.get("hostedRunRequest") or {}).get("body") if isinstance(contract.get("hostedRunRequest"), dict) else {}
        if not isinstance(hosted_run_body, dict):
            missing.append("browser-extension/billing-contract.json must include hostedRunRequest.body")
        else:
            for key in ["licenseKey", "usageId", "workflowType", "estimatedCredits", "commandType", "productUrl", "platforms", "localCommand", "safety"]:
                if key not in hosted_run_body:
                    missing.append(f"browser-extension/billing-contract.json hostedRunRequest missing key: {key}")
        hosted_run_response = (contract.get("hostedRunResponse") or {}) if isinstance(contract.get("hostedRunResponse"), dict) else {}
        for key in ["accepted", "runId", "status", "dashboardUrl", "statusUrl"]:
            if key not in hosted_run_response:
                missing.append(f"browser-extension/billing-contract.json hostedRunResponse missing key: {key}")
        events = contract.get("requiredWebhookEvents") if isinstance(contract.get("requiredWebhookEvents"), list) else []
        for event in ["checkout.session.completed", "customer.subscription.updated", "invoice.payment_failed"]:
            if event not in events:
                missing.append(f"browser-extension/billing-contract.json missing webhook event: {event}")
    elif contract_path.exists():
        missing.append("browser-extension/billing-contract.json is invalid JSON")
    if popup_path.exists():
        popup_text = safe_read(popup_path)
        for marker in [
            "ENHE AI",
            "Subscription estimate",
            "Command type",
            "Browser publish session",
            "Evidence inbox setup",
            "Real evidence inbox",
            "Performance monitor",
            "Final readiness audit",
            "Schedule init",
            "Run scheduled jobs",
            "Windows task script",
            "Publish queue JSON",
            "Evidence inbox folder",
            "Automation config",
            "License key",
            "Usage authorization endpoint",
            "Reserve credits",
            "Hosted run endpoint",
            "Copy hosted payload",
            "Hosted Worker off",
            "Open checkout",
            "Billing portal",
            "www.enhe-tech.com.cn",
            "popup.js",
        ]:
            if marker not in popup_text:
                missing.append(f"browser-extension/popup.html missing marker: {marker}")
        if 'src="https://' in popup_text or "src='https://" in popup_text:
            missing.append("browser-extension/popup.html must not load remote scripts")
    if script_path.exists():
        script_text = safe_read(script_path)
        if "const HOSTED_WORKER_ENABLED = true;" in script_text:
            hosted_worker_enabled = True
        elif "const HOSTED_WORKER_ENABLED = false;" in script_text:
            hosted_worker_enabled = False
            missing.append(
                "browser-extension/popup.js declares HOSTED_WORKER_ENABLED = false; hosted usage reservation and run submission are disabled"
            )
            hosted_button = re.search(
                r'<button(?=[^>]*\bid="startHostedRun")(?=[^>]*\bdisabled\b)(?=[^>]*\baria-disabled="true")[^>]*>',
                safe_read(popup_path),
            )
            if not hosted_button:
                missing.append("browser-extension/popup.html must disable startHostedRun while Hosted Worker is off")
        else:
            missing.append("browser-extension/popup.js must declare HOSTED_WORKER_ENABLED explicitly")
        for marker in [
            "chrome.storage.local",
            "validateLicense",
            "openCheckout",
            "openPortal",
            "authorizeUsage",
            "buildHostedRunPayload",
            "startHostedRun",
            "applyHostedWorkerState",
            "requireHostedWorker",
            "usageAuthorizeEndpoint",
            "hostedRunEndpoint",
            "idempotencyKey",
            "estimatedMonthlyCredits",
            "COST_PER_CREDIT",
            "skill_entry.py",
            "browser_publish_session.py",
            "viral_evidence_inbox_setup.py",
            "viral_evidence_inbox.py",
            "real_evidence_inbox_setup.py",
            "real_evidence_inbox.py",
            "performance_monitor.py",
            "launch_unlock_pack.py",
            "final_capability_readiness.py",
            "automation_scheduler.py",
            "browser_publish_session",
            "viral_evidence_inbox_setup",
            "viral_evidence_inbox",
            "real_evidence_inbox_setup",
            "real_evidence_inbox",
            "performance_monitor",
            "launch_unlock_pack",
            "final_readiness_audit",
            "automation_config_init",
            "automation_due_run",
            "automation_windows_task",
        ]:
            if marker not in script_text:
                missing.append(f"browser-extension/popup.js missing marker: {marker}")
    if style_path.exists():
        style_text = safe_read(style_path)
        if "--accent" not in style_text or "grid-template-columns" not in style_text:
            missing.append("browser-extension/popup.css missing operator UI tokens or stable layout rules")
    backend_package = read_json_file(ROOT / "backend/license-service/package.json")
    if backend_package:
        dependencies = backend_package.get("dependencies") if isinstance(backend_package.get("dependencies"), dict) else {}
        scripts = backend_package.get("scripts") if isinstance(backend_package.get("scripts"), dict) else {}
        for dependency in ["express", "stripe", "pg"]:
            if dependency not in dependencies:
                missing.append(f"backend/license-service/package.json missing dependency: {dependency}")
        for script in ["start", "migrate", "worker", "test"]:
            if script not in scripts:
                missing.append(f"backend/license-service/package.json missing script: {script}")
    server_text = safe_read(ROOT / "backend/license-service/src/server.js")
    for marker in [
        "/promotion-manager/:page(privacy|terms|refund|support)",
        "/api/promotion-manager/run/:runId",
        "createStateStore",
        "startHostedWorker",
        "renderLegalPage",
    ]:
        if marker not in server_text:
            missing.append(f"backend/license-service/src/server.js missing marker: {marker}")
    worker_text = safe_read(ROOT / "backend/license-service/src/hosted-worker.js")
    for marker in ["buildHostedCommand", "safeWorkerEnv", "I_APPROVE_PUBLISH", "PUBLISH_DRY_RUN", "unsupported_hosted_command_type"]:
        if marker not in worker_text:
            missing.append(f"backend/license-service/src/hosted-worker.js missing marker: {marker}")
    return {
        "ready": not missing,
        "evidence": evidence,
        "missing": missing,
        "hostedWorkerEnabled": hosted_worker_enabled,
    }


def scripts_ready(scripts: dict[str, dict[str, Any]], keys: list[str]) -> bool:
    return all(bool(scripts.get(key, {}).get("exists")) for key in keys)


def scripts_present(scripts: dict[str, dict[str, Any]], keys: list[str]) -> list[str]:
    return [str(scripts[key]["file"]) for key in keys if bool(scripts.get(key, {}).get("exists"))]


def missing_for_scripts(scripts: dict[str, dict[str, Any]], keys: list[str]) -> list[str]:
    return [SCRIPT_REQUIREMENTS[key] for key in keys if not bool(scripts.get(key, {}).get("exists"))]


def status_value(value: bool) -> str:
    return "ready" if value else "not_ready"


def missing_publish_credentials(credentials: dict[str, dict[str, Any]]) -> list[str]:
    missing = []
    if not credentials["github_write"]["ready"]:
        missing.append("GITHUB_TOKEN or GH_TOKEN for GitHub writes")
    if not (credentials["youtube_oauth_upload"]["ready"] or credentials["youtube_oauth_flow"]["ready"]):
        missing.append("YouTube OAuth access token or OAuth client credentials")
    return missing


def self_evolution_status(tools: dict[str, dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    audit_report = read_report_reference(str(audit.get("report", ""))) if audit.get("reportExists") else {}
    return {
        "mode": "controlled_autonomy",
        "audit": audit,
        "reviewRequiredUpgradeRequests": audit_report.get("reviewRequiredUpgradeRequests", []),
        "reviewQueueSummary": audit_report.get(
            "reviewQueueSummary",
            {"total": 0, "agentExecutableNow": 0, "requiresApprovalOrManualReview": 0},
        ),
        "canDoNow": [
            "audit local scripts, tools, and credential presence",
            "audit installed Skill drift against the reviewed local repository",
            "write capability reports and next-action plans",
            "sync reviewed local Skill files into the installed Skill directory when explicitly approved",
            "install Playwright Chromium when explicitly requested through --install-safe-missing-tools",
            "use official docs and public repos as research inputs for reviewed upgrades",
        ],
        "notAllowed": [
            "silent dependency upgrades",
            "self-replacement from unreviewed network code",
            "credential, cookie, or hidden-token extraction",
            "captcha/risk-control bypass",
        ],
        "safeInstallCandidates": [
            {
                "id": "playwright_chromium",
                "status": "ready" if tools["playwrightChromium"]["available"] else "missing_or_unchecked",
                "command": "python scripts/final_capability_audit.py --install-safe-missing-tools --safe-install playwright_chromium",
            }
        ],
        "safeSkillSync": [
            {
                "id": "sync_installed_skill",
                "approvalRequired": "I_APPROVE_SKILL_SYNC",
                "command": "python scripts/self_evolution_audit.py --sync-installed-skill --approval I_APPROVE_SKILL_SYNC",
            }
        ],
    }


def run_self_evolution_audit(
    args: argparse.Namespace,
    out_dir: Path,
    scripts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    script = Path(str(scripts.get("self_evolution_audit", {}).get("file", "")))
    report_path = out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.json"
    command = [sys.executable, str(script), "--out-dir", str(out_dir)]
    if args.skip_runtime_checks:
        command.append("--skip-runtime-checks")
    if not script.exists():
        return {
            "ready": False,
            "status": "script_missing",
            "script": str(script),
            "command": " ".join(command),
            "report": str(report_path),
            "reportExists": False,
        }
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired:
        return {
            "ready": False,
            "status": "timeout",
            "script": str(script),
            "command": " ".join(command),
            "report": str(report_path),
            "reportExists": report_path.exists(),
        }
    status = "error"
    if report_path.exists():
        try:
            status = str(json.loads(report_path.read_text(encoding="utf-8")).get("status", "unknown"))
        except json.JSONDecodeError:
            status = "invalid_report"
    return {
        "ready": result.returncode == 0 and report_path.exists(),
        "status": status,
        "script": str(script),
        "command": " ".join(command),
        "exitCode": result.returncode,
        "report": str(report_path),
        "reportExists": report_path.exists(),
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }


def platform_access_audit_status(scripts: dict[str, dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    return {
        "ready": bool(scripts.get("platform_access_audit", {}).get("exists")),
        "script": str(scripts.get("platform_access_audit", {}).get("file", "")),
        "command": f"python scripts/platform_access_audit.py --out-dir \"{out_dir}\"",
        "purpose": "machine-readable official API, manual publishing, and metrics access boundary audit",
    }


def recommended_commands(out_dir: Path) -> list[dict[str, str]]:
    return [
        {
            "purpose": "one_command_cycle",
            "command": (
                f"python scripts/promotion_cycle_runner.py --browser-url \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "one_link_skill_entry",
            "command": (
                f"python scripts/skill_entry.py --link \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --github-repo owner/repo "
                f"--business-csv \"./orders-and-revenue.csv\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "build_real_run_playbook",
            "command": (
                f"python scripts/real_run_playbook.py --url \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --github-repo owner/repo "
                f"--business-csv \"./orders-and-revenue.csv\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "final_capability_runner",
            "command": (
                f"python scripts/final_capability_runner.py --url \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --business-csv \"./orders-and-revenue.csv\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "final_capability_runner_from_website_discovery",
            "command": (
                f"python scripts/final_capability_runner.py --discover-from-url \"https://example.com\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --business-csv \"./orders-and-revenue.csv\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "build_final_readiness_matrix",
            "command": f"python scripts/final_capability_readiness.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "review_github_docs",
            "command": "review README.md docs/installation.md docs/usage.md docs/browser-extension.md docs/extension-store-submission.md docs/legal docs/store deploy/promotion-manager docs/subscription-pricing.md docs/final-capability-map.md docs/100-percent-completion-roadmap.md docs/zh-CN/100-percent-completion-guide.md",
        },
        {
            "purpose": "build_completion_roadmap",
            "command": f"python scripts/completion_roadmap.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "install_youtube_google_api_python_client",
            "command": "python -m pip install -r requirements-youtube.txt",
        },
        {
            "purpose": "check_youtube_credentials_without_upload",
            "command": f"python scripts/youtube_credential_check.py --env-file \"C:/path/to/.env\" --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "build_zh_cn_operator_action_checklist",
            "command": f"python scripts/operator_action_checklist.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "package_browser_extension",
            "command": "python scripts/package_browser_extension.py --out-dir \"./dist\"",
        },
        {
            "purpose": "load_browser_extension",
            "command": "open chrome://extensions, enable Developer mode, click Load unpacked, select ./browser-extension",
        },
        {
            "purpose": "billing_contract_simulator_demo",
            "command": f"python scripts/billing_contract_simulator.py demo --plan growth --workflow-type research_run --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "batch_product_url_cycles",
            "command": (
                f"python scripts/product_batch_runner.py --urls-file \"./product-urls.txt\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "discover_product_urls_then_run_batch_cycles",
            "command": (
                f"python scripts/product_batch_runner.py --discover-from-url \"https://example.com\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "batch_product_url_cycles_with_multi_query_viral_discovery",
            "command": (
                f"python scripts/product_batch_runner.py --urls-file \"./product-urls.txt\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --run-multi-query-viral-discovery "
                f"--multi-query-query-count 5 --multi-query-top-n 20 --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "batch_product_url_closed_loop_with_next_round_optimization",
            "command": (
                f"python scripts/product_batch_runner.py --urls-file \"./product-urls.txt\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --run-post-publish-metrics-capture "
                f"--run-comment-evidence-capture --run-business-attribution --run-next-round-optimization "
                f"--business-csv \"./orders-and-revenue.csv\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "multi_query_viral_discovery",
            "command": (
                f"python scripts/multi_query_viral_discovery.py --workflow-manifest "
                f"\"{out_dir}/reports/promotion-manager/agent-run/workflow-manifest.json\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --top-n 20 --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "setup_viral_evidence_inbox",
            "command": (
                "python scripts/viral_evidence_inbox_setup.py --product-url \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --inbox-dir \"./viral-evidence-inbox\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "import_viral_evidence_inbox",
            "command": (
                f"python scripts/viral_evidence_inbox.py --inbox-dir \"./viral-evidence-inbox\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "capture_browser_visible_video_evidence",
            "command": (
                f"python scripts/browser_video_sampler.py --url \"https://example.com/video-page\" "
                f"--platform youtube --sample-count 5 --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "audit_platform_official_access",
            "command": f"python scripts/platform_access_audit.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "audit_platform_official_access_with_live_docs",
            "command": f"python scripts/platform_access_audit.py --check-live --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "audit_self_evolution",
            "command": f"python scripts/self_evolution_audit.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "audit_publish_readiness",
            "command": (
                f"python scripts/publish_readiness_runner.py --workflow-manifest \"{out_dir}/reports/promotion-manager/agent-run/workflow-manifest.json\" "
                f"--build-queue --github-repo owner/repo --youtube-video-file \"{out_dir}/videos/product-youtube.mp4\" "
                f"--douyin-video-file \"{out_dir}/videos/product-douyin.mp4\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "build_publish_setup_kit",
            "command": (
                f"python scripts/publish_setup_assistant.py --publish-readiness "
                f"\"{out_dir}/reports/promotion-manager/publish-readiness/publish-readiness.json\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "build_launch_unlock_pack",
            "command": (
                f"python scripts/launch_unlock_pack.py --publish-queue "
                f"\"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" "
                f"--publish-readiness \"{out_dir}/reports/promotion-manager/publish-readiness/publish-readiness.json\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "prepare_browser_assisted_publish",
            "command": (
                f"python scripts/browser_publish_assistant.py --publish-queue "
                f"\"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "run_browser_publish_session",
            "command": (
                f"python scripts/browser_publish_session.py --publish-queue "
                f"\"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" "
                f"--run-form-fill --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "recover_metrics_from_structured_snapshot",
            "command": (
                f"python scripts/metrics_recovery.py --metrics-structured-json \"{out_dir}/published-metrics-snapshot.json\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "monitor_post_publish_performance",
            "command": f"python scripts/performance_monitor.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "capture_public_post_publish_metrics",
            "command": f"python scripts/post_publish_metrics_capture.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "recover_captured_post_publish_metrics",
            "command": (
                f"python scripts/metrics_recovery.py --metrics-json "
                f"\"{out_dir}/reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json\" --out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "setup_real_evidence_inbox",
            "command": (
                f"python scripts/real_evidence_inbox_setup.py --product-url \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --inbox-dir \"./promotion-evidence-inbox\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "import_real_evidence_inbox",
            "command": (
                f"python scripts/real_evidence_inbox.py --inbox-dir \"./promotion-evidence-inbox\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "capture_public_comment_evidence",
            "command": f"python scripts/comment_evidence_capture.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "attribute_business_results",
            "command": (
                f"python scripts/business_attribution.py --business-csv \"./orders-and-revenue.csv\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "optimize_next_round_from_recovered_evidence",
            "command": (
                f"python scripts/next_round_optimizer.py --metrics-recovery-json "
                f"\"{out_dir}/reports/promotion-manager/metrics-recovery/metrics-recovery.json\" "
                f"--comment-evidence-json \"{out_dir}/reports/promotion-manager/comment-evidence/comment-evidence-export.json\" "
                f"--business-attribution-json \"{out_dir}/reports/promotion-manager/business-attribution/business-attribution.json\" "
                f"--out-dir \"{out_dir}\""
            ),
        },
        {
            "purpose": "install_browser_runtime_when_explicitly_allowed",
            "command": "python scripts/final_capability_audit.py --install-safe-missing-tools --safe-install playwright_chromium",
        },
        {
            "purpose": "sync_installed_skill_when_approved",
            "command": "python scripts/self_evolution_audit.py --sync-installed-skill --approval I_APPROVE_SKILL_SYNC --out-dir \"./promotion-output\"",
        },
        {
            "purpose": "run_periodic_jobs",
            "command": "python scripts/automation_scheduler.py run --config ./promotion-automation.json",
        },
    ]


def next_actions(
    requirements: list[dict[str, Any]],
    tools: dict[str, dict[str, Any]],
    credentials: dict[str, dict[str, Any]],
    out_dir: Path,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not tools["playwrightChromium"]["available"]:
        actions.append(
            {
                "priority": 1,
                "area": "product_intake_and_platform_search",
                "action": "Install or verify Playwright Chromium for rendered product and platform search snapshots.",
                "command": "python scripts/final_capability_audit.py --install-safe-missing-tools --safe-install playwright_chromium",
            }
        )
    if not credentials["github_write"]["ready"]:
        actions.append(
            {
                "priority": 2,
                "area": "github_publish",
                "action": "Provide GITHUB_TOKEN or GH_TOKEN only in the environment when approved GitHub publishing is needed.",
            }
        )
    if not (credentials["youtube_oauth_upload"]["ready"] or credentials["youtube_oauth_flow"]["ready"]):
        actions.append(
            {
                "priority": 3,
                "area": "youtube_publish",
                "action": "Provide Google OAuth client credentials or a temporary YouTube OAuth access token for approved uploads.",
            }
        )
    actions.append(
        {
            "priority": 4,
            "area": "full_cycle",
            "action": "Run a real product through the cycle and register real published URLs or exports before claiming performance.",
            "command": (
                f"python scripts/promotion_cycle_runner.py --browser-url \"https://example.com/product\" "
                f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
            ),
        }
    )
    if any(item["status"] == "blocked_by_safety_boundary" for item in requirements):
        actions.append(
            {
                "priority": 5,
                "area": "self_evolution",
                "action": "Keep self-upgrades reviewable: generate a proposal, cite official docs/public repos, then apply reviewed changes.",
            }
        )
    return actions


def final_status(requirements: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in requirements}
    if statuses == {"ready"}:
        return "full_ready"
    if "blocked_by_authorization_or_platform_limits" in statuses or "blocked_by_safety_boundary" in statuses:
        return "partial_ready_blocked_by_platform_or_safety_limits"
    if "partial_ready" in statuses:
        return "partial_ready"
    return "not_ready"


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = audit_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "final-capability-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / "final-capability-audit.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final Capability Audit",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['finalStatus']}`",
        f"- Output: {report['outDir']}",
        "",
        "## Requirements",
    ]
    for item in report["requirements"]:
        lines.append(f"- `{item['id']}`: `{item['status']}` - {item['label']}")
        missing = item.get("missing") or []
        if missing:
            lines.append(f"  Missing: {', '.join(missing)}")
        limits = item.get("limits") or []
        if limits:
            lines.append(f"  Limits: {'; '.join(limits)}")
    lines.extend(["", "## Platforms"])
    for platform, info in report["platforms"].items():
        lines.append(
            f"- {platform}: search=`{info['viralSearch']}`, publish=`{info['directPublish']}`, metrics=`{info['metricsRecovery']}`"
        )
    access = report.get("platformAccessAudit") or {}
    if access:
        lines.extend(
            [
                "",
                "## Platform Access Audit",
                f"- Ready: {access.get('ready')}",
                f"- Command: `{access.get('command')}`",
            ]
        )
    self_audit = report.get("selfEvolutionAudit") or {}
    if self_audit:
        lines.extend(
            [
                "",
                "## Self-Evolution Audit",
                f"- Ready: {self_audit.get('ready')}",
                f"- Status: `{self_audit.get('status')}`",
                f"- Report: {self_audit.get('report')}",
                f"- Command: `{self_audit.get('command')}`",
            ]
        )
    lines.extend(["", "## Next Actions"])
    for action in report["nextActions"]:
        lines.append(f"- P{action['priority']} {action['area']}: {action['action']}")
        if action.get("command"):
            lines.append(f"  Command: `{action['command']}`")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def audit_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/capability"


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_report_reference(path_value: str) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.is_absolute() and not path.exists():
        path = ROOT / path
    return read_json_file(path)


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def tail(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


if __name__ == "__main__":
    main()
