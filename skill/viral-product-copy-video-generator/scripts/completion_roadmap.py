#!/usr/bin/env python3
"""Generate the 100% completion roadmap for ENHE Product Promo Maker."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()


def main() -> None:
    args = parse_args()
    report = build_report()
    if args.out_dir:
        write_report(Path(args.out_dir), report)
        print(f"Completion roadmap written to: {(report_dir(Path(args.out_dir)) / 'completion-roadmap.json').resolve()}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a module-by-module 100% completion roadmap.")
    parser.add_argument("--out-dir", default="", help="Write roadmap reports under promotion-output.")
    return parser.parse_args()


def build_report() -> dict[str, Any]:
    modules = module_roadmap()
    return {
        "generatedAt": TODAY,
        "status": "roadmap_ready",
        "rule": "A module reaches 100% only when current evidence proves code, docs, runtime, account gates, and real-world outputs as applicable.",
        "modules": modules,
        "summary": {
            "moduleCount": len(modules),
            "codexCanCompleteLocally": [item["id"] for item in modules if item["codexCompletionScope"] in {"full_local", "majority_local"}],
            "requiresOperatorExternalGates": [item["id"] for item in modules if item["operatorExternalGates"]],
            "unsafeShortcutsRejected": [
                "cookie capture",
                "simulated login",
                "hidden token reuse",
                "private platform endpoints",
                "captcha or risk-control bypass",
                "auto-like/follow/comment/DM",
                "final browser publish click",
                "fabricated metrics, orders, revenue, or published URLs",
            ],
        },
        "openSourceReferences": open_source_references(),
        "priorityOrder": [
            "Prove one real Codex Skill run end to end.",
            "Verify media runtimes and publish-pack assets.",
            "Configure Firecrawl or import real viral evidence inbox data.",
            "Deploy the license backend and hosted worker behind HTTPS.",
            "Submit the browser extension to Chrome and Edge stores.",
            "Enable official publishing only for approved API platforms.",
            "Build the Monetize marketplace MVP after real promotion and billing loops are stable.",
        ],
        "verificationCommands": [
            "python scripts\\completion_roadmap.py --out-dir \".\\promotion-output\"",
            "python scripts\\platform_capabilities.py --out-dir \".\\promotion-output\"",
            "python scripts\\final_capability_audit.py --skip-runtime-checks --out-dir \".\\promotion-output\\verification\"",
            "python -m compileall -q scripts",
            "python scripts\\test_promotion_manager.py",
        ],
    }


def module_roadmap() -> list[dict[str, Any]]:
    return [
        {
            "id": "codex_skill_local_promotion_loop",
            "name": "Codex Skill local promotion loop",
            "currentEstimate": 85,
            "codexCompletionScope": "majority_local",
            "missingTo100": [
                "real product URL run evidence",
                "Playwright runtime verified when browser capture is needed",
                "final readiness matrix generated from current run",
                "installed Skill synced after explicit review",
                "regression and compile checks after latest changes",
            ],
            "codexCanDo": [
                "run audits and tests",
                "generate playbooks and readiness matrices",
                "create launch unlock packs and evidence inboxes",
                "sync reviewed Skill files after explicit approval",
            ],
            "operatorMustDo": [
                "provide real product or website URL",
                "approve Skill sync only after review",
                "provide real published evidence after manual publishing",
            ],
            "operatorSteps": [
                "cd \"C:\\Users\\HU\\Documents\\Viral-Product-Copy-Video-Generator\"",
                "python scripts\\final_capability_audit.py --install-safe-missing-tools --safe-install playwright_chromium --out-dir \".\\promotion-output\"",
                "python scripts\\skill_entry.py --link \"https://your-real-product-url.example\" --platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \".\\promotion-output\"",
                "notepad \".\\promotion-output\\reports\\promotion-manager\\final-readiness\\final-capability-readiness.md\"",
            ],
            "acceptanceEvidence": [
                "reports/promotion-manager/skill-entry/skill-entry.json",
                "reports/promotion-manager/final-run/final-capability-run.json",
                "reports/promotion-manager/final-readiness/final-capability-readiness.json",
                "reports/promotion-manager/capability/final-capability-audit.json",
            ],
            "operatorExternalGates": ["real product URL", "optional Skill sync approval", "real post-publish evidence"],
        },
        {
            "id": "copy_video_cover_detail_publish_pack",
            "name": "Copy, video, cover, detail image, publish pack",
            "currentEstimate": 85,
            "codexCompletionScope": "majority_local",
            "missingTo100": [
                "ffmpeg verified for MP4 rendering",
                "Pillow verified for PNG generation",
                "real product assets generated after latest workflow run",
                "video files attached for video-required platforms",
                "publish pack schema verified for every target platform",
                "production voiceover audio supplied if required",
            ],
            "codexCanDo": [
                "generate platform copy, scripts, tags, and first-batch comments",
                "render silent captioned MP4 drafts when ffmpeg exists",
                "attach provided voiceover audio",
                "generate cover and detail PNG assets",
                "write media paths back into the publish pack",
            ],
            "operatorMustDo": [
                "install ffmpeg and Pillow if missing",
                "provide production voiceover audio when silent or system TTS is not acceptable",
                "review generated assets before public publishing",
            ],
            "operatorSteps": [
                "winget install Gyan.FFmpeg",
                "python -m pip install pillow",
                "python scripts\\render_video.py --content-json \".\\promotion-output\\reports\\promotion-manager\\generated-content\\product-platform-content.json\" --platform douyin --out \".\\promotion-output\\videos\\product-douyin.mp4\"",
                "python scripts\\media_asset_pack.py --content-json \".\\promotion-output\\reports\\promotion-manager\\generated-content\\product-platform-content.json\" --publish-pack \".\\promotion-output\\reports\\promotion-manager\\publish-packs\\product-publish-pack.json\" --video-file \"douyin=.\\promotion-output\\videos\\product-douyin.mp4\" --out-dir \".\\promotion-output\"",
            ],
            "acceptanceEvidence": [
                "videos/*.mp4",
                "media-assets/*/*.png",
                "reports/promotion-manager/media-assets/media-asset-pack.json",
                "reports/promotion-manager/publish-packs/*-publish-pack.json",
            ],
            "operatorExternalGates": ["runtime installs", "optional production voiceover review"],
        },
        {
            "id": "competitor_research_and_web_data",
            "name": "Competitor research and web data",
            "currentEstimate": 80,
            "codexCompletionScope": "majority_local",
            "missingTo100": [
                "Playwright Chromium verified",
                "Firecrawl key or self-hosted compatible endpoint configured when desired",
                "real product-derived platform searches run",
                "risk-controlled platform gaps filled with real user evidence",
                "viral library and creator leaderboard populated with real evidence",
                "deep competitor records include source URLs and deconstruction",
            ],
            "codexCanDo": [
                "run public/browser-visible search",
                "call optional Firecrawl-style Search/Scrape/Map/Crawl/Batch Scrape provider",
                "create and import viral evidence inboxes",
                "rank materials and creator accounts",
                "keep blocked platforms explicit instead of inventing data",
            ],
            "operatorMustDo": [
                "provide FIRECRAWL_API_KEY when using Firecrawl Cloud",
                "provide enough server capacity if self-hosting Firecrawl",
                "provide real exports, URLs, transcripts, or OCR text for blocked platforms",
            ],
            "operatorSteps": [
                "Add WEB_DATA_PROVIDER=auto, FIRECRAWL_API_KEY, and FIRECRAWL_BASE_URL to .env if using Firecrawl.",
                "python scripts\\web_data_provider.py --provider firecrawl --out-dir \".\\promotion-output\" scrape --url \"https://your-real-product-url.example\"",
                "python scripts\\multi_query_viral_discovery.py --workflow-manifest \".\\promotion-output\\reports\\promotion-manager\\agent-run\\workflow-manifest.json\" --platforms youtube,zhihu,xiaohongshu,douyin,github --top-n 20 --out-dir \".\\promotion-output\"",
                "python scripts\\viral_evidence_inbox_setup.py --product-url \"https://your-real-product-url.example\" --platforms youtube,zhihu,xiaohongshu,douyin,github --inbox-dir \".\\viral-evidence-inbox\" --out-dir \".\\promotion-output\"",
                "python scripts\\viral_evidence_inbox.py --inbox-dir \".\\viral-evidence-inbox\" --out-dir \".\\promotion-output\"",
            ],
            "acceptanceEvidence": [
                "reports/promotion-manager/web-data/*.json",
                "reports/promotion-manager/competitors/viral-content-library.json",
                "reports/promotion-manager/competitors/creator-leaderboard.json",
                "reports/promotion-manager/competitors/deep-competitor-library.json",
            ],
            "operatorExternalGates": ["Firecrawl key or server", "real competitor evidence for blocked platforms"],
        },
        {
            "id": "browser_extension_and_commercial_infrastructure",
            "name": "Browser extension and commercialization infrastructure",
            "currentEstimate": 75,
            "codexCompletionScope": "majority_local",
            "missingTo100": [
                "production HTTPS backend deployed",
                "PostgreSQL database created and migrated",
                "Stripe live products, prices, and webhook secret configured",
                "license API and hosted worker running as isolated services",
                "extension endpoints configured for production",
                "legal pages published",
                "Chrome Web Store and Edge Add-ons approvals received",
                "production monitoring, backups, rate limits, and worker capacity verified",
            ],
            "codexCanDo": [
                "maintain extension code and package validation",
                "maintain license backend and migration files",
                "maintain legal/store drafts",
                "help debug deployment logs and reviewer feedback",
            ],
            "operatorMustDo": [
                "own the server, domain, Stripe account, and browser store accounts",
                "enter live secrets into server environment variables",
                "submit store listings",
                "upgrade server if CPU/RAM is insufficient",
            ],
            "operatorSteps": [
                "ssh root@your-server-ip",
                "sudo apt update && sudo apt install -y nodejs npm postgresql nginx git",
                "git clone https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator.git",
                "cd Viral-Product-Copy-Video-Generator/backend/license-service && npm install",
                "Create PostgreSQL database and user for enhe_promotion_manager.",
                "cp ../../deploy/promotion-manager/.env.production.example .env and fill live values on the server.",
                "npm run migrate",
                "Install and start the API and worker systemd services from deploy/promotion-manager.",
                "Configure Nginx and HTTPS for www.enhe-tech.com.cn.",
                "python scripts\\package_browser_extension.py --out-dir \".\\dist\"",
                "Submit the ZIP to Chrome Web Store and Edge Add-ons.",
            ],
            "acceptanceEvidence": [
                "HTTPS health check succeeds",
                "database migration completed",
                "Stripe webhook updates license state",
                "extension validates a license against production endpoint",
                "hosted run job completes through the worker",
                "Chrome/Edge listing status is approved",
            ],
            "operatorExternalGates": ["server", "domain HTTPS", "Stripe live account", "store approval", "production secrets"],
        },
        {
            "id": "true_all_platform_auto_publish",
            "name": "True all-platform automatic publishing",
            "currentEstimate": 40,
            "codexCompletionScope": "limited_by_platforms",
            "missingTo100": [
                "GitHub fine-grained token or GitHub App permissions",
                "YouTube OAuth app, approved scope, quota, and video target",
                "Douyin browser-assisted/manual publishing evidence; official Open Platform publishing is a reserved future port",
                "verified official publishing API for any platform claimed as automatic",
                "explicit I_APPROVE_PUBLISH and PUBLISH_DRY_RUN=false",
                "real execution report, published URL, and audit log",
            ],
            "codexCanDo": [
                "build dry-run queues and readiness reports",
                "execute official API calls only when all gates are present",
                "generate manual/browser-assisted payloads for unsupported platforms",
                "write audit logs and clear errors",
            ],
            "operatorMustDo": [
                "create developer apps",
                "complete OAuth consent and app review",
                "put tokens and secrets into environment variables",
                "approve each real publish",
                "accept manual/browser-assisted publishing for platforms without verified official API access",
            ],
            "operatorSteps": [
                "$env:GITHUB_TOKEN=\"github_pat_xxx\"",
                "$env:YOUTUBE_CLIENT_ID=\"your-client-id\"",
                "$env:YOUTUBE_CLIENT_SECRET=\"your-client-secret\"",
                "# GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET are also accepted aliases.",
                "python scripts\\publish_readiness_runner.py --workflow-manifest \".\\promotion-output\\reports\\promotion-manager\\agent-run\\workflow-manifest.json\" --build-queue --github-repo hqwzhu/Viral-Product-Copy-Video-Generator --youtube-video-file \".\\promotion-output\\videos\\product-youtube.mp4\" --douyin-video-file \".\\promotion-output\\videos\\product-douyin.mp4\" --out-dir \".\\promotion-output\"",
                "$env:I_APPROVE_PUBLISH=\"true\"",
                "$env:PUBLISH_DRY_RUN=\"false\"",
                "python scripts\\final_capability_runner.py --url \"https://your-real-product-url.example\" --platforms youtube,douyin,github --github-repo hqwzhu/Viral-Product-Copy-Video-Generator --youtube-video-file \".\\promotion-output\\videos\\product-youtube.mp4\" --douyin-video-file \".\\promotion-output\\videos\\product-douyin.mp4\" --run-browser-form-fill --out-dir \".\\promotion-output\"",
            ],
            "acceptanceEvidence": [
                "publish-readiness.json says ready for the platform",
                "official execution report status is success",
                "published URL is registered",
                "audit log contains platform, status, content ID, URL, time, and errors",
            ],
            "operatorExternalGates": ["developer accounts", "OAuth approval", "platform scopes", "valid tokens", "manual approval"],
        },
        {
            "id": "creator_tasks_settlement_monetize_marketplace",
            "name": "Creator tasks, settlement, and Monetize marketplace",
            "currentEstimate": 30,
            "codexCompletionScope": "needs_new_product_build",
            "missingTo100": [
                "campaign, task, submission, evidence, payout, creator, advertiser, and review data model",
                "operator UI or CLI for campaign creation",
                "creator task acceptance and submission flow",
                "evidence review and fraud checks",
                "CPS/CPE/CPM formulas backed by real evidence",
                "payout provider and compliance process",
                "support, dispute, refund, and tax processes",
            ],
            "codexCanDo": [
                "build MVP schema and API",
                "generate admin CLI or UI flows",
                "connect evidence inbox outputs to payout proposals",
                "add tests for settlement formulas",
                "keep payouts manual-review-first",
            ],
            "operatorMustDo": [
                "decide legal business entity",
                "open Stripe Connect or another payout provider",
                "define creator and advertiser terms",
                "recruit pilot creators and advertisers",
                "approve payouts manually until controls are proven",
            ],
            "operatorSteps": [
                "Start with manual settlement and one pilot campaign.",
                "Prepare product URL, target platforms, deliverables, payout model, budget cap, deadline, and evidence requirements.",
                "Ask Codex to create the Monetize MVP schema/API after confirming the scope.",
                "Run one creator pilot: publish manually, submit URL and evidence, import evidence, generate payout proposal, manually approve payout.",
            ],
            "acceptanceEvidence": [
                "real campaign exists",
                "real creator submission exists",
                "real published URL and evidence imported",
                "payout proposal generated from evidence",
                "manual payout decision recorded",
                "no payout made from fabricated or unverified metrics",
            ],
            "operatorExternalGates": ["legal entity", "payout provider", "creator onboarding", "tax/compliance", "real campaigns"],
        },
    ]


def open_source_references() -> list[dict[str, str]]:
    return [
        {
            "project": "firecrawl/firecrawl",
            "url": "https://github.com/firecrawl/firecrawl",
            "use": "Search, Scrape, Map, Crawl, Batch Scrape, Interact, and future MCP web evidence provider.",
            "boundary": "Use only for public URLs and public search evidence; do not send private or login-only pages.",
        },
        {
            "project": "yikart/AiToEarn",
            "url": "https://github.com/yikart/AiToEarn",
            "use": "Reference for Create, Publish, Engage, Monetize platform architecture and marketplace shape.",
            "boundary": "Do not adopt cookie, simulated-login, hidden-token, private endpoint, or store-risky auto-engagement paths.",
        },
        {
            "project": "stripe-samples",
            "url": "https://github.com/stripe-samples",
            "use": "Checkout, customer portal, webhook verification, and Connect marketplace samples.",
            "boundary": "Live billing still requires the operator's verified Stripe account and production secrets.",
        },
        {
            "project": "openmeterio/openmeter",
            "url": "https://github.com/openmeterio/openmeter",
            "use": "Usage metering and credit ledger architecture reference.",
            "boundary": "Reference only unless the project deliberately adopts its service model.",
        },
        {
            "project": "getlago/lago",
            "url": "https://github.com/getlago/lago",
            "use": "Open-source billing and invoice architecture reference.",
            "boundary": "Do not replace the current lightweight license service without migration work.",
        },
        {
            "project": "unkeyed/unkey",
            "url": "https://github.com/unkeyed/unkey",
            "use": "API key, quota, and rate-limit management reference.",
            "boundary": "Keep extension secrets out of the client and store only server-side secrets.",
        },
    ]


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "completion-roadmap.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "completion-roadmap.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Completion Roadmap",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Rule: {report['rule']}",
        "",
        "## Modules",
    ]
    for module in report["modules"]:
        lines.extend(
            [
                "",
                f"### {module['name']}",
                f"- Current estimate: {module['currentEstimate']}%",
                f"- Codex scope: `{module['codexCompletionScope']}`",
                "- Missing to 100%:",
            ]
        )
        lines.extend(f"  - {item}" for item in module["missingTo100"])
        lines.append("- Codex can do:")
        lines.extend(f"  - {item}" for item in module["codexCanDo"])
        lines.append("- Operator must do:")
        lines.extend(f"  - {item}" for item in module["operatorMustDo"])
        lines.append("- Operator steps:")
        lines.extend(f"  - `{item}`" for item in module["operatorSteps"])
        lines.append("- Acceptance evidence:")
        lines.extend(f"  - {item}" for item in module["acceptanceEvidence"])
    lines.extend(["", "## Open Source References"])
    for ref in report["openSourceReferences"]:
        lines.append(f"- [{ref['project']}]({ref['url']}): {ref['use']} Boundary: {ref['boundary']}")
    lines.extend(["", "## Priority Order"])
    lines.extend(f"{index}. {item}" for index, item in enumerate(report["priorityOrder"], start=1))
    lines.extend(["", "## Verification Commands"])
    lines.extend(f"- `{item}`" for item in report["verificationCommands"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/capability"


if __name__ == "__main__":
    main()
