#!/usr/bin/env python3
"""Machine-readable platform capability registry for ENHE Product Promo Maker."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()


def main() -> None:
    args = parse_args()
    report = build_report(args.platform)
    if args.out_dir:
        write_report(Path(args.out_dir), report)
        print(f"Platform capabilities written to: {(report_dir(Path(args.out_dir)) / 'platform-capabilities.json').resolve()}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List safe platform capabilities inspired by provider-registry projects.")
    parser.add_argument("--platform", default="", help="Optional platform key: youtube, github, douyin, zhihu, xiaohongshu, tiktok.")
    parser.add_argument("--out-dir", default="", help="Write reports under promotion-output.")
    return parser.parse_args()


def build_report(platform: str = "") -> dict[str, Any]:
    registry = platform_registry()
    selected = [registry[platform]] if platform else list(registry.values())
    if platform and platform not in registry:
        raise SystemExit(f"Unsupported platform: {platform}")
    return {
        "generatedAt": TODAY,
        "status": "ready",
        "inspiredBy": {
            "AiToEarn": {
                "used": [
                    "platform integration registry shape",
                    "publish/auth/analytics/engagement/work/browse capability separation",
                    "publish records, scheduling, verification, and MCP-facing tool concepts",
                    "Relay-style optional connector boundary for early integrations",
                ],
                "rejected": [
                    "loginCookie storage",
                    "simulated login or hidden browser token reuse",
                    "store-version auto like/follow/comment/final publish side effects",
                    "unverified private platform endpoints",
                    "opaque third-party relay as the long-term core security promise",
                ],
            },
            "Firecrawl": {
                "used": [
                    "optional Search/Scrape/Map/Crawl/Batch Scrape public web data backend",
                    "Interact planning for public, user-visible evidence collection with stop conditions",
                    "future MCP/Agent web evidence provider",
                ],
                "rejected": [
                    "making a heavy crawler stack a hard dependency for local Skill runs",
                    "sending private, login-only, or risk-controlled pages to a third-party provider",
                    "using Interact to bypass login, captcha, risk control, or platform publishing permissions",
                ],
            },
        },
        "platforms": selected,
        "monetizationBlueprint": monetization_blueprint(),
        "relayBridgePolicy": relay_bridge_policy(),
        "guardrails": guardrails(),
    }


def platform_registry() -> dict[str, dict[str, Any]]:
    base_engage = {
        "allowed": [
            "brand monitoring from public/official evidence",
            "comment and demand-signal collection from public/official/user-exported evidence",
            "AI reply draft generation",
            "manual review before any reply, like, follow, or other side effect",
        ],
        "blockedInStoreVersion": [
            "auto-like",
            "auto-follow",
            "auto-comment",
            "auto-DM",
            "captcha/risk-control bypass",
            "final publish click",
        ],
    }
    return {
        "youtube": {
            "platform": "youtube",
            "displayName": "YouTube",
            "create": ["titles", "descriptions", "tags", "shorts scripts", "long-form scripts", "MP4 drafts", "cover images"],
            "search": {"mode": "official_or_public", "implementedBy": ["competitor_collector.py", "platform_search_browser.py", "web_data_provider.py"]},
            "publish": {
                "defaultMode": "manual_publish_pack",
                "officialApiPort": "YouTube Data API v3 videos.insert",
                "executor": "publish_executor.py / youtube_oauth_publish.py",
                "dryRunDefault": True,
                "scheduleSupport": "official publishAt requires private privacyStatus and approved OAuth",
                "requiredEnv": [
                    "GOOGLE_OAUTH_CLIENT_ID or YOUTUBE_CLIENT_ID",
                    "GOOGLE_OAUTH_CLIENT_SECRET or YOUTUBE_CLIENT_SECRET",
                    "YOUTUBE_ACCESS_TOKEN",
                    "YOUTUBE_OAUTH_ACCESS_TOKEN",
                    "YOUTUBE_REFRESH_TOKEN optional for future refresh-token support",
                ],
            },
            "engage": base_engage,
            "analytics": {"mode": "official_or_public", "requiredEnv": ["YOUTUBE_API_KEY"], "manualFallback": "analytics export or screenshot text"},
            "monetize": {"settlement": "manual_review_first", "evidence": ["published URL", "platform export", "business export"]},
        },
        "github": {
            "platform": "github",
            "displayName": "GitHub",
            "create": ["README promotion copy", "release notes", "issue drafts", "discussion drafts"],
            "search": {"mode": "public_api", "implementedBy": ["competitor_collector.py", "platform_search_browser.py", "web_data_provider.py"]},
            "publish": {
                "defaultMode": "official_api_dry_run_or_pr",
                "officialApiPort": "GitHub REST contents/issues/releases",
                "executor": "publish_executor.py",
                "dryRunDefault": True,
                "scheduleSupport": "external scheduler can create PR or content when approved",
                "requiredEnv": ["GITHUB_TOKEN"],
            },
            "engage": base_engage,
            "analytics": {"mode": "public_repo_metrics", "requiredEnv": [], "manualFallback": "repository insights export"},
            "monetize": {"settlement": "manual_review_first", "evidence": ["PR/release URL", "stars/forks/issues", "business export"]},
        },
        "douyin": {
            "platform": "douyin",
            "displayName": "Douyin",
            "create": ["viral titles", "hashtags", "30s scripts", "storyboards", "MP4 drafts", "cover images"],
            "search": {"mode": "browser_visible_or_web_data", "implementedBy": ["platform_search_browser.py", "viral_evidence_inbox.py", "web_data_provider.py"]},
            "publish": {
                "defaultMode": "browser_assisted_publish_pack",
                "officialApiPort": "reserved_future_only; disabled by current operator policy until verified Douyin authorization is available",
                "executor": "browser_publish_session.py / browser_publish_assistant.py",
                "dryRunDefault": True,
                "scheduleSupport": "manual scheduling or browser-assisted session only",
                "requiredEnv": [],
            },
            "engage": base_engage,
            "analytics": {"mode": "manual_export_or_public_snapshot", "requiredEnv": [], "manualFallback": "creator analytics export or screenshot text"},
            "monetize": {"settlement": "manual_review_first", "evidence": ["published URL", "creator export", "order/revenue export"]},
        },
        "zhihu": {
            "platform": "zhihu",
            "displayName": "Zhihu",
            "create": ["article titles", "article outlines", "answers/articles", "comment prompts"],
            "search": {"mode": "browser_visible_or_user_evidence", "implementedBy": ["platform_search_browser.py", "viral_evidence_inbox.py", "web_data_provider.py"]},
            "publish": {
                "defaultMode": "manual_or_browser_assisted_publish_pack",
                "officialApiPort": "not verified for general creator publishing",
                "executor": "browser_publish_session.py",
                "dryRunDefault": True,
                "scheduleSupport": "manual scheduling only until official API access is verified",
                "requiredEnv": [],
            },
            "engage": base_engage,
            "analytics": {"mode": "manual_export_or_public_snapshot", "requiredEnv": [], "manualFallback": "analytics export or screenshot text"},
            "monetize": {"settlement": "manual_review_first", "evidence": ["published URL", "platform export", "business export"]},
        },
        "xiaohongshu": {
            "platform": "xiaohongshu",
            "displayName": "Xiaohongshu",
            "create": ["note titles", "note body", "hashtags", "first-batch comments", "cover images", "detail images"],
            "search": {"mode": "browser_visible_or_user_evidence", "implementedBy": ["platform_search_browser.py", "viral_evidence_inbox.py", "web_data_provider.py"]},
            "publish": {
                "defaultMode": "manual_or_browser_assisted_publish_pack",
                "officialApiPort": "not verified for general creator publishing",
                "executor": "browser_publish_session.py",
                "dryRunDefault": True,
                "scheduleSupport": "manual scheduling only until official API access is verified",
                "requiredEnv": [],
            },
            "engage": base_engage,
            "analytics": {"mode": "manual_export_or_public_snapshot", "requiredEnv": [], "manualFallback": "creator center export or screenshot text"},
            "monetize": {"settlement": "manual_review_first", "evidence": ["published URL", "platform export", "order/revenue export"]},
        },
        "tiktok": {
            "platform": "tiktok",
            "displayName": "TikTok",
            "create": ["short video titles", "hashtags", "scripts", "MP4 drafts", "cover images"],
            "search": {"mode": "browser_visible_or_web_data", "implementedBy": ["platform_search_browser.py", "viral_evidence_inbox.py", "web_data_provider.py"]},
            "publish": {
                "defaultMode": "manual_or_official_api_candidate",
                "officialApiPort": "TikTok Content Posting API candidate",
                "executor": "reserved",
                "dryRunDefault": True,
                "scheduleSupport": "requires official app product access and creator authorization",
                "requiredEnv": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
            },
            "engage": base_engage,
            "analytics": {"mode": "manual_export_or_public_snapshot", "requiredEnv": [], "manualFallback": "analytics export or screenshot text"},
            "monetize": {"settlement": "manual_review_first", "evidence": ["published URL", "platform export", "business export"]},
        },
    }


def monetization_blueprint() -> dict[str, Any]:
    return {
        "status": "blueprint_ready",
        "mvpEntities": [
            {"name": "campaigns", "purpose": "brand/product promotion offers, target platforms, budget, payout model"},
            {"name": "creator_tasks", "purpose": "creator-facing tasks with deliverables, due dates, and approval rules"},
            {"name": "submissions", "purpose": "published URL, asset package, notes, and review status"},
            {"name": "evidence_items", "purpose": "platform exports, screenshots, public snapshots, order/revenue exports"},
            {"name": "payout_ledger", "purpose": "manual-review settlement records for CPS/CPE/CPM/flat-fee payouts"},
        ],
        "safeMvpFlow": [
            "operator creates campaign and publish package",
            "creator accepts a task and publishes manually or through approved official APIs",
            "creator submits real published URL and evidence",
            "system imports metrics/business evidence and proposes payout",
            "operator manually approves settlement before payment",
        ],
        "blockedUntilExternalGates": [
            "automatic payout from public metrics alone",
            "auto-engagement farming",
            "platform-private analytics without official/exported evidence",
            "live Stripe Connect or marketplace payout without account onboarding and legal review",
        ],
    }


def relay_bridge_policy() -> dict[str, Any]:
    return {
        "status": "temporary_optional_bridge",
        "allowedUse": [
            "early-stage connector relay for platforms where the operator explicitly accepts a third-party trust boundary",
            "manual approval workflow handoff and status tracking",
            "non-secret capability discovery and task orchestration",
        ],
        "notAllowedAsCorePromise": [
            "opaque credential custody for open-source default deployments",
            "hidden private endpoint publishing",
            "browser cookie/token relay",
            "automatic social engagement actions",
        ],
        "migrationPath": [
            "replace relay publishing with official platform APIs when available",
            "self-host relay-like workers with auditable code and least-privilege credentials",
            "keep manual publish package fallback for platforms without verified official APIs",
        ],
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "platform-capabilities.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "platform-capabilities.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Platform Capabilities",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        "",
        "## Platforms",
    ]
    for platform in report["platforms"]:
        lines.extend(
            [
                "",
                f"### {platform['displayName']}",
                f"- Create: {', '.join(platform['create'])}",
                f"- Search: `{platform['search']['mode']}`",
                f"- Publish default: `{platform['publish']['defaultMode']}`",
                f"- Official API port: {platform['publish']['officialApiPort']}",
                f"- Executor: `{platform['publish']['executor']}`",
                f"- Analytics: `{platform['analytics']['mode']}`",
                f"- Monetize: `{platform['monetize']['settlement']}`",
            ]
        )
    lines.extend(["", "## Monetization MVP"])
    lines.extend(f"- {item['name']}: {item['purpose']}" for item in report["monetizationBlueprint"]["mvpEntities"])
    relay = report.get("relayBridgePolicy") if isinstance(report.get("relayBridgePolicy"), dict) else {}
    if relay:
        lines.extend(["", "## Relay Bridge Policy", f"- Status: `{relay.get('status', '')}`"])
        lines.extend(f"- Allowed: {item}" for item in relay.get("allowedUse", []))
        lines.extend(f"- Not core promise: {item}" for item in relay.get("notAllowedAsCorePromise", []))
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/capability"


def guardrails() -> list[str]:
    return [
        "Manual publish packages remain the primary path; official auto-publish ports are dry-run-first.",
        "No cookie capture, simulated login, hidden token reuse, captcha bypass, or private endpoint calls.",
        "Store-safe engagement means monitoring and reply drafts first; final social actions require human confirmation.",
        "Chrome/Edge store builds do not implement automatic like, follow, comment, or DM actions.",
        "CPS/CPE/CPM settlement must be backed by real published URL, platform/export evidence, and business evidence.",
        "Firecrawl is an optional web data backend, not a required local runtime or proof of platform authorization.",
    ]


if __name__ == "__main__":
    main()
