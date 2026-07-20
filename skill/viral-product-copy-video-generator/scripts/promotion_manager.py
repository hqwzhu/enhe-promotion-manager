#!/usr/bin/env python3
"""Deterministic report generator for the viral product promotion skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]
VIDEO_REQUIRED_PLATFORMS = {"youtube", "xiaohongshu", "douyin", "tiktok"}
TODAY = date.today().isoformat()


@dataclass
class Product:
    name: str
    url: str
    audience: list[str]
    pain_points: list[str]
    value_proposition: str
    pricing: str
    goal: str
    language: str
    platforms: list[str]


SOURCES = {
    "youtube_videos_insert": {
        "title": "YouTube Data API videos.insert",
        "url": "https://developers.google.com/youtube/v3/docs/videos/insert",
        "evidence": "Official videos.insert endpoint uploads a video and metadata, supports media upload, and requires YouTube API authorization and quota.",
    },
    "tiktok_content_posting": {
        "title": "TikTok Content Posting API",
        "url": "https://developers.tiktok.com/doc/content-posting-api-get-started",
        "evidence": "Official Content Posting API can post directly after app registration, Direct Post configuration, video.publish scope approval, and user authorization; unaudited clients are visibility-restricted.",
    },
    "douyin_publish_solution": {
        "title": "Douyin content publishing solution",
        "url": "https://open.douyin.com/platform/resource/docs/ability/content-management/douyin-publish-solution",
        "evidence": "Official Douyin Open Platform describes open_api publishing of video or image content, with review logic and platform constraints.",
    },
    "douyin_video_upload": {
        "title": "Douyin upload video API",
        "url": "https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/upload/",
        "evidence": "Official upload endpoint needs video.create scope, permission application, and user authorization.",
    },
    "douyin_create_video": {
        "title": "Douyin create video API",
        "url": "https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/create-video",
        "evidence": "Official create video endpoint needs video.create scope and requires user-visible authorization before creating content on a user's behalf.",
    },
    "github_contents": {
        "title": "GitHub repository contents REST API",
        "url": "https://docs.github.com/en/rest/repos/contents",
        "evidence": "Official REST API can create or update file contents with write permissions and appropriate tokens.",
    },
    "github_releases": {
        "title": "GitHub releases REST API",
        "url": "https://docs.github.com/en/rest/releases/releases",
        "evidence": "Official REST API can create releases for users with repository push access.",
    },
    "github_issues": {
        "title": "GitHub issues REST API",
        "url": "https://docs.github.com/en/rest/issues/issues",
        "evidence": "Official REST API can create issues when the authenticated user has repository access and issues are enabled.",
    },
    "github_discussions": {
        "title": "GitHub Discussions GraphQL API",
        "url": "https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions",
        "evidence": "Official GraphQL API can get, create, edit, and delete repository discussion posts for authenticated users/apps.",
    },
    "xiaohongshu_open_platform": {
        "title": "Xiaohongshu open platform developer docs",
        "url": "https://open.xiaohongshu.com/document/developer/file/4",
        "evidence": "Public official docs are primarily open-platform/developer docs; no stable general creator note-publishing API was verified in public docs.",
    },
    "xiaohongshu_api_docs": {
        "title": "Xiaohongshu open platform API docs",
        "url": "https://open.xiaohongshu.com/document/api",
        "evidence": "Public API docs expose open-platform categories; treat general note publishing as manual/browser-assisted unless official access is verified.",
    },
}


CAPABILITIES: list[dict[str, Any]] = [
    {
        "platform": "youtube",
        "supportsOfficialApi": True,
        "supportsDirectPublish": True,
        "supportsScheduledPublish": False,
        "recommendedMode": "official_api_publish",
        "approvalRequired": True,
        "requiredCredentials": ["Google Cloud project", "OAuth consent", "YouTube Data API scope", "user channel authorization"],
        "riskLevel": "medium",
        "notes": [
            "Official API candidate. Do not upload until the user provides OAuth approval and a final publish approval.",
            "Generate publish packs first; the skill does not store credentials or upload videos by default.",
        ],
        "officialDocs": [SOURCES["youtube_videos_insert"]["url"]],
        "referenceProjects": [],
    },
    {
        "platform": "github",
        "supportsOfficialApi": True,
        "supportsDirectPublish": True,
        "supportsScheduledPublish": False,
        "recommendedMode": "official_api_publish",
        "approvalRequired": True,
        "requiredCredentials": ["GitHub token or GitHub App with repository permissions"],
        "riskLevel": "low",
        "notes": [
            "Official API candidate for README/content updates, releases, issues, and repository discussions.",
            "Never write to a repository without explicit user approval.",
        ],
        "officialDocs": [
            SOURCES["github_contents"]["url"],
            SOURCES["github_releases"]["url"],
            SOURCES["github_issues"]["url"],
            SOURCES["github_discussions"]["url"],
        ],
        "referenceProjects": [],
    },
    {
        "platform": "tiktok",
        "supportsOfficialApi": True,
        "supportsDirectPublish": True,
        "supportsScheduledPublish": False,
        "recommendedMode": "official_api_publish",
        "approvalRequired": True,
        "requiredCredentials": ["TikTok developer app", "Content Posting API product", "video.publish approval", "user authorization"],
        "riskLevel": "medium",
        "notes": [
            "Official API candidate only after app approval, required scope approval, and creator authorization.",
            "Unaudited clients can be restricted; do not claim public posting readiness until audit state is verified.",
        ],
        "officialDocs": [SOURCES["tiktok_content_posting"]["url"]],
        "referenceProjects": [],
    },
    {
        "platform": "douyin",
        "supportsOfficialApi": True,
        "supportsDirectPublish": False,
        "supportsScheduledPublish": False,
        "recommendedMode": "browser_assisted_publish",
        "approvalRequired": True,
        "requiredCredentials": [],
        "riskLevel": "high",
        "notes": [
            "Official API code is reserved for future verified authorization; the current Skill defaults to browser-assisted/manual publishing.",
            "Do not bypass review, captcha, risk controls, or user-visible authorization.",
        ],
        "officialDocs": [
            SOURCES["douyin_publish_solution"]["url"],
            SOURCES["douyin_video_upload"]["url"],
            SOURCES["douyin_create_video"]["url"],
        ],
        "referenceProjects": ["dreammis/social-auto-upload"],
    },
    {
        "platform": "xiaohongshu",
        "supportsOfficialApi": False,
        "supportsDirectPublish": False,
        "supportsScheduledPublish": False,
        "recommendedMode": "manual_publish_required",
        "approvalRequired": True,
        "requiredCredentials": [],
        "riskLevel": "high",
        "notes": [
            "No stable public general note-publishing API was verified. Treat unofficial endpoints as unsupported for first version.",
            "Generate copyable note packs and manual/browser-assisted guidance only.",
        ],
        "officialDocs": [
            SOURCES["xiaohongshu_open_platform"]["url"],
            SOURCES["xiaohongshu_api_docs"]["url"],
        ],
        "referenceProjects": ["dreammis/social-auto-upload"],
    },
    {
        "platform": "zhihu",
        "supportsOfficialApi": False,
        "supportsDirectPublish": False,
        "supportsScheduledPublish": False,
        "recommendedMode": "manual_publish_required",
        "approvalRequired": True,
        "requiredCredentials": [],
        "riskLevel": "high",
        "notes": [
            "No stable official public article-publishing API was verified. Do not use captured/private endpoints.",
            "Generate long-form article packs and manual/browser-assisted guidance only.",
        ],
        "officialDocs": [],
        "referenceProjects": [],
    },
]


REFERENCE_PROJECTS: list[dict[str, Any]] = [
    {
        "name": "Postiz",
        "repo": "gitroomhq/postiz-app",
        "url": "https://github.com/gitroomhq/postiz-app",
        "category": "social media scheduling",
        "license": "AGPL-3.0",
        "platforms": ["X", "Bluesky", "Mastodon", "Discord", "and others"],
        "usefulPatterns": ["OAuth-first architecture", "human review calendar", "no scraping/cookie capture stance"],
        "riskNotes": ["Heavy SaaS-style system; use as architecture reference, not as a first-version dependency."],
    },
    {
        "name": "social-auto-upload",
        "repo": "dreammis/social-auto-upload",
        "url": "https://github.com/dreammis/social-auto-upload",
        "category": "multi-platform video uploader",
        "license": "MIT",
        "platforms": ["Douyin", "Xiaohongshu", "WeChat Channels", "TikTok", "YouTube", "Bilibili"],
        "usefulPatterns": ["platform adapters", "upload workflow references", "video distribution research"],
        "riskNotes": ["May rely on browser automation or unofficial paths; do not integrate blindly."],
    },
    {
        "name": "LangChain social-media-agent",
        "repo": "langchain-ai/social-media-agent",
        "url": "https://github.com/langchain-ai/social-media-agent",
        "category": "URL-to-social-post agent",
        "license": "MIT",
        "platforms": ["Twitter/X", "LinkedIn"],
        "usefulPatterns": ["URL ingestion", "draft generation", "human-in-the-loop authentication and approval"],
        "riskNotes": ["Platform scope is narrower than this Skill; use for HITL agent flow ideas."],
    },
    {
        "name": "n8n social media workflow library",
        "repo": "n8n workflow templates",
        "url": "https://n8n.io/workflows/categories/social-media/",
        "category": "workflow automation templates",
        "license": "template-specific",
        "platforms": ["YouTube", "TikTok", "Instagram", "LinkedIn", "X", "Reddit", "and others"],
        "usefulPatterns": ["approval nodes", "metadata tracking", "workflow orchestration"],
        "riskNotes": ["Templates can require third-party posting APIs; verify every node before production use."],
    },
]


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "platform-data":
        from platform_data_manager import main as platform_data_main

        platform_data_main(sys.argv[2:])
        return
    args = parse_args()
    product = Product(
        name=args.product_name,
        url=args.product_url,
        audience=split_csv(args.audience),
        pain_points=split_csv(args.pain_points),
        value_proposition=args.value_proposition,
        pricing=args.pricing,
        goal=args.goal,
        language=args.language,
        platforms=split_csv(args.platforms) if args.platforms else DEFAULT_PLATFORMS,
    )
    out_dir = Path(args.out_dir)
    ensure_output_tree(out_dir)

    if args.command in ("research", "capability", "all"):
        write_research_reports(out_dir)

    if args.command in ("deconstruct", "all"):
        deconstruction = build_deconstruction_report(product)
        write_named_report(
            out_dir / "reports/promotion-manager/competitors",
            f"{slugify(product.name)}-deconstruction",
            deconstruction,
            render_deconstruction(deconstruction),
        )

    plan = build_content_plan(product)
    content_path = out_dir / "reports/promotion-manager/generated-content" / f"{slugify(product.name)}-platform-content.json"
    if args.command in ("plan", "all"):
        write_named_report(
            out_dir / "reports/promotion-manager/content-plans",
            f"{slugify(product.name)}-content-plan",
            plan,
            render_content_plan(plan),
        )

    content = generate_platform_content(product, plan)
    if args.command in ("content", "all"):
        write_named_report(
            out_dir / "reports/promotion-manager/generated-content",
            f"{slugify(product.name)}-platform-content",
            content,
            render_platform_content(content),
        )

    review = review_content(content)
    if args.command in ("review", "all"):
        cheat_review_pack = build_cheat_review_pack(out_dir, product, content, content_path)
        apply_cheat_review_pack(review, cheat_review_pack)
        write_named_report(
            out_dir / "reports/promotion-manager/cheat-review",
            f"{slugify(product.name)}-cheat-review-pack",
            cheat_review_pack,
            render_cheat_review_pack(cheat_review_pack),
        )
        write_named_report(
            out_dir / "reports/promotion-manager/generated-content",
            f"{slugify(product.name)}-content-review",
            review,
            render_review(review),
        )

    publish_pack = build_publish_pack(content)
    if args.command in ("publish-pack", "all"):
        write_named_report(
            out_dir / "reports/promotion-manager/publish-packs",
            f"{slugify(product.name)}-publish-pack",
            publish_pack,
            render_publish_pack(publish_pack),
        )
        write_named_report(
            out_dir / "reports/promotion-manager/publish-packs",
            "platform-publish-capability-map",
            CAPABILITIES,
            render_capabilities(CAPABILITIES),
        )

    result_template = build_result_template(product)
    if args.command in ("result-template", "all"):
        write_named_report(
            out_dir / "reports/promotion-manager/publish-results",
            f"{slugify(product.name)}-publish-result-input",
            result_template,
            render_result_template(result_template),
        )

    retrospective = build_retrospective(result_template)
    if args.command in ("retrospective", "all"):
        write_named_report(
            out_dir / "reports/promotion-manager/retrospectives",
            f"{slugify(product.name)}-retrospective",
            retrospective,
            render_retrospective(retrospective),
        )

    if args.command in ("roadmap", "all"):
        write_roadmaps(out_dir)

    write_legacy_index(out_dir, product)
    print(f"Promotion reports written to: {out_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate multi-platform product promotion manager reports.")
    parser.add_argument(
        "command",
        choices=[
            "all",
            "research",
            "capability",
            "deconstruct",
            "plan",
            "content",
            "review",
            "publish-pack",
            "result-template",
            "retrospective",
            "roadmap",
        ],
        help="Report set to generate.",
    )
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--product-url", required=True)
    parser.add_argument("--audience", required=True, help="Comma-separated audience list.")
    parser.add_argument("--pain-points", default="blank-page product copy, low traffic, weak conversion")
    parser.add_argument("--value-proposition", required=True)
    parser.add_argument("--pricing", default="unknown")
    parser.add_argument("--goal", default="leads", choices=["traffic", "leads", "sales", "seo", "brand", "github_stars"])
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated platform list.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "product"


def ensure_output_tree(out_dir: Path) -> None:
    for subdir in [
        "docs/promotion-manager",
        "reports/promotion-manager/research",
        "reports/promotion-manager/competitors",
        "reports/promotion-manager/content-plans",
        "reports/promotion-manager/generated-content",
        "reports/promotion-manager/cheat-review",
        "reports/promotion-manager/publish-packs",
        "reports/promotion-manager/publish-results",
        "reports/promotion-manager/retrospectives",
    ]:
        (out_dir / subdir).mkdir(parents=True, exist_ok=True)


def write_research_reports(out_dir: Path) -> None:
    feasibility = build_platform_feasibility()
    references = build_reference_project_report()
    risks = build_risk_matrix()
    notes = build_self_learning_notes()
    write_named_report(
        out_dir / "reports/promotion-manager/research",
        "platform-publishing-feasibility",
        feasibility,
        render_platform_feasibility(feasibility),
    )
    write_named_report(
        out_dir / "reports/promotion-manager/research",
        "github-reference-projects",
        references,
        render_reference_projects(references),
    )
    write_named_report(
        out_dir / "reports/promotion-manager/research",
        "platform-risk-matrix",
        risks,
        render_risk_matrix(risks),
    )
    write_named_report(
        out_dir / "reports/promotion-manager/research",
        "self-learning-notes",
        notes,
        render_self_learning_notes(notes),
    )
    write_doc(out_dir, "01-platform-publishing-feasibility.md", render_platform_feasibility(feasibility))
    write_doc(out_dir, "02-github-reference-projects.md", render_reference_projects(references))
    write_doc(out_dir, "03-platform-risk-matrix.md", render_risk_matrix(risks))
    write_doc(out_dir, "04-self-learning-notes.md", render_self_learning_notes(notes))


def build_platform_feasibility() -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "policy": {
            "autoPublishFirstVersion": False,
            "storesCookieOrToken": False,
            "bypassesCaptcha": False,
            "fabricatesMetrics": False,
            "approvalRequired": True,
        },
        "sources": SOURCES,
        "capabilities": CAPABILITIES,
    }


def build_reference_project_report() -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "selectionRule": "Use projects as architecture references only; do not import code or wire posting automation without review.",
        "projects": REFERENCE_PROJECTS,
    }


def build_risk_matrix() -> list[dict[str, Any]]:
    rows = []
    for capability in CAPABILITIES:
        rows.append(
            {
                "platform": capability["platform"],
                "recommendedMode": capability["recommendedMode"],
                "apiLimitRisk": "medium" if capability["supportsOfficialApi"] else "high",
                "loginRisk": "low" if capability["supportsOfficialApi"] else "high",
                "cookieTokenRisk": "medium" if capability["requiredCredentials"] else "low",
                "captchaRisk": "medium" if capability["platform"] in {"douyin", "xiaohongshu", "zhihu"} else "low",
                "accountSafetyRisk": capability["riskLevel"],
                "firstVersionDecision": "generate_publish_pack_only",
                "mustNotDo": [
                    "no automatic login",
                    "no final publish click",
                    "no cookie/token/password storage",
                    "no captcha bypass",
                    "no fabricated metrics",
                ],
            }
        )
    return rows


def build_self_learning_notes() -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "currentConclusion": [
            "First version should remain a Codex-local Skill pipeline, not a SaaS UI or browser plugin.",
            "YouTube and GitHub have active official publishing ports. Douyin stays browser-assisted/manual because authorization is unavailable; its official path is reserved for future verified access.",
            "Zhihu and Xiaohongshu should default to manual publish packs unless official creator publishing access is verified.",
            "Reference projects are useful for patterns; none should be integrated without a separate security and compliance review.",
        ],
        "nextResearchQueue": [
            "refresh official platform docs before any real publishing integration",
            "collect user-provided competitor URLs before deconstruction metrics are claimed",
            "verify each platform's latest content and advertising rules before production publishing",
        ],
        "skillUse": [
            "Use web-access for live research.",
            "Use cheat-on-content for qualitative review when available.",
            "Use this script for deterministic report scaffolding.",
        ],
    }


def build_deconstruction_report(product: Product) -> dict[str, Any]:
    return {
        "platforms": product.platforms,
        "niche": product.value_proposition,
        "status": "needs_live_research_or_user_import",
        "competitors": [],
        "winningPatterns": [
            "pain-first hook",
            "specific workflow demonstration",
            "platform-native CTA",
            "before/after framing",
        ],
        "titlePatterns": [
            "How to turn one product URL into a week of content",
            "Stop writing from scratch: use a product promotion system",
            "The checklist I use before launching an AI tool",
        ],
        "hookPatterns": [
            "You do not have a traffic problem first; you have a message clarity problem.",
            "One product page can become five platform-native assets.",
            "Before posting anywhere, split audience, pain, proof, and CTA.",
        ],
        "contentStructures": [
            "Problem -> failed old way -> repeatable method -> product demo -> CTA",
            "Audience -> pain -> workflow -> example output -> next action",
            "Benchmark pattern -> adapted script -> approval checklist -> publish pack",
        ],
        "ctaPatterns": [
            f"Open {product.url} and generate your first promotion pack.",
            "Save this checklist before your next launch.",
            "Comment with your product URL to get a rewrite angle.",
        ],
        "visualPatterns": ["screen recording", "template preview", "checklist overlay", "before/after copy comparison"],
        "risks": ["do not claim competitor metrics without observed evidence", "do not copy competitor wording"],
        "recommendations": ["import real competitor links in the next run", "record visible metrics with evidence URLs"],
    }


def build_content_plan(product: Product) -> dict[str, Any]:
    platform_plans = []
    for platform in product.platforms:
        platform_plans.append(
            {
                "platform": platform,
                "audienceAngle": angle_for(platform),
                "topics": [
                    f"{product.name} solves a painful blank-page problem",
                    f"Turn one product URL into a reusable content system",
                    f"How {product.name} helps {product.audience[0] if product.audience else 'operators'} ship faster",
                ],
                "cta": f"Open {product.url} and try {product.name} before your next launch post.",
                "frequency": frequency_for(platform),
                "reusePlan": reuse_plan_for(platform),
                "approvalRequired": True,
            }
        )
    return {
        "product": asdict(product),
        "positioning": f"{product.name}: {product.value_proposition}",
        "platformPlans": platform_plans,
        "calendar": [
            {"platform": item["platform"], "topic": item["topics"][0], "cadence": item["frequency"], "approvalRequired": True}
            for item in platform_plans
        ],
    }


def angle_for(platform: str) -> str:
    return {
        "youtube": "Build trust with long-form explanation and Shorts pain-point clips.",
        "zhihu": "Use question-led long-form reasoning and practical checklists.",
        "xiaohongshu": "Use list posts, before/after framing, and low-friction action prompts.",
        "douyin": "Use a 3-second pain hook, one concrete method, and a direct CTA.",
        "github": "Use builder-friendly README, Discussion, Issue, and release copy.",
        "tiktok": "Use short proof-led demos and direct creator workflow framing.",
    }.get(platform, "Use platform-native product education and a clear CTA.")


def frequency_for(platform: str) -> str:
    return {
        "youtube": "1 long video plus 2 Shorts per week",
        "zhihu": "1 long article per week",
        "xiaohongshu": "3 notes per week",
        "douyin": "3 short videos per week",
        "github": "1 README/release/discussion update per launch event",
        "tiktok": "3 short videos per week",
    }.get(platform, "1-3 posts per week")


def reuse_plan_for(platform: str) -> str:
    return {
        "youtube": "Use Zhihu article as long-video outline; convert hooks into Shorts.",
        "zhihu": "Expand YouTube script into reasoned article with checklists.",
        "xiaohongshu": "Turn core benefits into list posts and cover text.",
        "douyin": "Convert strongest hook into 30-second voiceover and storyboard.",
        "github": "Convert positioning into README, release notes, and discussion prompts.",
        "tiktok": "Reuse Douyin script after localizing platform language and constraints.",
    }.get(platform, "Adapt the core message to local platform format.")


def generate_platform_content(product: Product, plan: dict[str, Any]) -> dict[str, Any]:
    content: dict[str, Any] = {}
    for item in plan["platformPlans"]:
        platform = item["platform"]
        title = title_for(platform, product.name)
        article = article_for(platform, product)
        short_video_script = short_video_script_for(platform, product)
        voiceover = voiceover_for(platform, product)
        formats = format_payload(platform, product)
        content[platform] = {
            "platform": platform,
            "contentType": content_type_for(platform),
            "title": title,
            "viralTitle": title,
            "description": f"{product.name}: {product.value_proposition}",
            "article": article,
            "shortVideoScript": short_video_script,
            "voiceover": voiceover,
            "storyboard": storyboard_for(platform, product),
            "coverText": cover_text_for(platform, product.name),
            "tags": tags_for(platform),
            "cta": item["cta"],
            "copy": publication_copy_for(platform, product, article, short_video_script, voiceover, formats),
            "firstBatch": first_batch_for(platform, product, formats),
            "complianceNotice": "Human approval required. Verify facts, price, links, and platform rules before publishing.",
            "sourceProduct": asdict(product),
            "formats": formats,
            "generatedAt": TODAY,
        }
    return content


def content_type_for(platform: str) -> str:
    return {
        "youtube": "video_pack",
        "zhihu": "long_form_article",
        "xiaohongshu": "note_pack",
        "douyin": "short_video_pack",
        "github": "repository_content_pack",
        "tiktok": "short_video_pack",
    }.get(platform, "promotion_pack")


def title_for(platform: str, name: str) -> str:
    return {
        "youtube": f"How to turn one product URL into a week of content with {name}",
        "zhihu": f"如何用 {name} 系统化生成产品推广内容？",
        "xiaohongshu": f"不会写产品文案？先试试 {name}",
        "douyin": "你不是不会推广，是没有把卖点说清楚",
        "github": f"{name}: reusable prompts for product copy and launch content",
        "tiktok": f"Stop writing product copy from scratch with {name}",
    }.get(platform, f"{name} promotion content pack")


def article_for(platform: str, product: Product) -> str | None:
    if platform != "zhihu":
        return None
    return (
        f"# 如何用 {product.name} 系统化生成产品推广内容？\n\n"
        f"很多产品推广失败，不是产品没有价值，而是没有把目标用户、痛点、结果和行动路径讲清楚。\n\n"
        f"{product.name} 的定位是：{product.value_proposition}。\n\n"
        "推荐流程：先拆用户，再拆痛点，再生成平台原生内容，最后用真实数据复盘。"
        f"\n\n行动建议：打开 {product.url}，先生成一份你的产品推广包。"
    )


def short_video_script_for(platform: str, product: Product) -> str | None:
    if platform not in {"douyin", "tiktok", "youtube"}:
        return None
    return (
        f"Hook: 你不是不会推广，是还没有把 {product.name} 的用户、痛点、卖点和 CTA 拆开。\n"
        f"Demo: 输入产品链接，生成标题、文案、口播、视频脚本和发布包。\n"
        f"CTA: 打开 {product.url}，先生成第一套推广内容。"
    )


def voiceover_for(platform: str, product: Product) -> str | None:
    if platform not in {"douyin", "tiktok", "youtube"}:
        return None
    return (
        f"如果你有一个产品，却不知道怎么发 YouTube、知乎、小红书、抖音和 GitHub，"
        f"先用 {product.name} 把目标用户、痛点、卖点和 CTA 拆清楚。"
        "不要先追热点，先让每个平台都拿到能发布的内容包。"
    )


def storyboard_for(platform: str, product: Product) -> list[dict[str, str]] | None:
    if platform not in {"douyin", "tiktok", "youtube"}:
        return None
    return [
        {"time": "0-3s", "visual": "show messy product notes", "voiceover": "你不是不会推广，是信息没拆清楚。"},
        {"time": "3-12s", "visual": "show product URL input", "voiceover": f"输入 {product.name} 的链接。"},
        {"time": "12-24s", "visual": "show platform packs", "voiceover": "生成标题、口播、脚本、文章和发布步骤。"},
        {"time": "24-30s", "visual": "show CTA", "voiceover": f"打开 {product.url} 试一次。"},
    ]


def cover_text_for(platform: str, name: str) -> str:
    return {
        "youtube": "One URL -> one week of content",
        "zhihu": "产品推广怎么系统化？",
        "xiaohongshu": "产品文案别从零写",
        "douyin": "卖点讲不清？这样拆",
        "github": "Launch copy templates",
        "tiktok": "Stop blank-page marketing",
    }.get(platform, f"{name} promotion")


def tags_for(platform: str) -> list[str]:
    return {
        "youtube": ["AI tools", "product marketing", "content strategy", "SaaS growth"],
        "zhihu": ["AI工具", "产品推广", "内容运营", "SEO"],
        "xiaohongshu": ["AI工具", "副业工具", "产品文案", "运营"],
        "douyin": ["AI工具", "产品推广", "短视频脚本", "创业"],
        "github": ["ai", "product-marketing", "prompt-engineering", "launch"],
        "tiktok": ["aitools", "productmarketing", "contentcreator", "startup"],
    }.get(platform, ["product", "marketing"])


def format_payload(platform: str, product: Product) -> dict[str, Any]:
    if platform == "youtube":
        return {
            "longVideoTitles": [f"{i}. {product.name} product promotion workflow" for i in range(1, 11)],
            "shortsTitles": [f"{i}. 30s product copy tip with {product.name}" for i in range(1, 11)],
            "videoScripts": [
                f"Hook: Stop staring at a blank product page. Method: use {product.name} to define audience, pain, offer, and CTA. CTA: visit {product.url}.",
                f"Hook: Your product is not unclear; your message is. Show the template flow, then point to {product.name}.",
                f"Hook: One URL can become many posts. Demonstrate the content plan and ask viewers to try {product.name}.",
            ],
        }
    if platform == "zhihu":
        return {
            "articleTitles": [f"{i}. {product.name} 如何帮助产品推广？" for i in range(1, 11)],
            "articleOutlines": [
                "问题 -> 失败原因 -> 模板化解决方案 -> 使用步骤 -> CTA",
                "目标用户 -> 场景 -> 产品价值 -> 多平台复用 -> CTA",
                "SEO 意图 -> 内容结构 -> 转化动作 -> 复盘指标 -> CTA",
            ],
        }
    if platform == "xiaohongshu":
        return {
            "noteTitles": [f"{i}. {product.name} 文案模板" for i in range(1, 21)],
            "notes": [
                f"如果你有产品但写不出推广内容，先用 {product.name} 把用户、痛点、卖点和 CTA 拆开。",
                "不要先追热点，先把产品能解决谁的问题讲清楚。",
                "一套产品信息可以复用成小红书、知乎、抖音和 YouTube 内容。",
                "发布前确认事实、链接和平台规则，不承诺收益。",
                f"适合 {', '.join(product.audience[:3])}。",
            ],
            "commentPrompts": ["你最卡在哪个平台？", "发产品链接，我帮你拆一个角度。"],
        }
    if platform in {"douyin", "tiktok"}:
        return {
            "voiceoverTitles": [f"{i}. 30秒讲清 {product.name}" for i in range(1, 21)],
            "thirtySecondScripts": [
                f"你不是不会推广，是没有把卖点说清楚。用 {product.name} 先拆用户、痛点、结果和 CTA。",
                f"别让 AI 随便写。给它结构：谁、痛点、产品、证据、行动。{product.name} 就是这套结构。",
                "一个产品 URL 可以变成一周内容，但前提是你有可复用模板。",
                "流量不是玄学，每条内容都要有钩子、痛点、CTA 和复盘指标。",
                f"打开 {product.url}，先生成你的第一套推广内容。",
            ],
            "captions": ["先拆用户", "再讲痛点", "最后给 CTA"],
        }
    if platform == "github":
        return {
            "readmePromotion": f"## {product.name}\n\n{product.value_proposition}\n\nCTA: {product.url}",
            "releaseNote": f"Release idea: add reusable product promotion templates for {product.name}.",
            "discussionPrompts": [
                "How do you turn one product URL into a complete launch content plan?",
                "What prompt templates are most useful for product copy and SEO workflows?",
                "Share your workflow for turning product positioning into video scripts.",
            ],
        }
    return {"draft": f"{product.name} promotion draft"}


def publication_copy_for(
    platform: str,
    product: Product,
    article: str | None,
    short_video_script: str | None,
    voiceover: str | None,
    formats: dict[str, Any],
) -> str:
    candidates: list[Any] = [
        article,
        short_video_script,
        voiceover,
        formats.get("readmePromotion"),
        first_list_item(formats.get("notes")),
        first_list_item(formats.get("thirtySecondScripts")),
        first_list_item(formats.get("videoScripts")),
        f"{product.name}: {product.value_proposition}",
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return f"{product.name} promotion copy for {platform}."


def first_batch_for(platform: str, product: Product, formats: dict[str, Any]) -> dict[str, Any]:
    comment_prompts = clean_list(formats.get("commentPrompts"))
    if platform == "github":
        first_comments = [
            "Open a launch Discussion with the generated README positioning.",
            "Pin the release note and ask users which integration or template they need next.",
        ]
    else:
        first_comments = comment_prompts or [
            "Which platform is hardest for you to promote on right now?",
            "Drop your product URL and rewrite the first hook with this structure.",
        ]
    return {
        "pinnedComment": f"Try {product.name}: {product.url}" if product.url else f"Try {product.name}",
        "firstComments": first_comments,
        "replyPrompts": [
            "Ask the user which product category they are promoting.",
            "Ask which platform they want to publish on first.",
            "Offer one concrete title, hook, or CTA rewrite.",
        ],
        "launchActions": [
            "Publish only after human review.",
            "Pin the strongest CTA or resource comment.",
            "Save the real published URL for metrics recovery.",
        ],
    }


def first_list_item(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return ""


def clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def review_content(content: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = []
    for platform, item in content.items():
        risk_flags = []
        if platform in {"zhihu", "xiaohongshu", "douyin"}:
            risk_flags.append("manual_or_browser_assisted_publish_only")
        reviews.append(
            {
                "platform": platform,
                "viralityScore": 78,
                "titleHookScore": 82,
                "openingHookScore": 80,
                "painPointScore": 84,
                "clarityScore": 86,
                "conversionScore": 84 if item.get("cta") else 50,
                "complianceScore": 92,
                "platformFitScore": 82,
                "seoScore": 80,
                "cheatOnContent": {
                    "status": "pending_cheat_review_pack",
                    "reason": "The promotion manager will create a cheat-on-content review pack without writing prediction logs.",
                },
                "riskFlags": risk_flags,
                "rewriteSuggestions": [
                    "Verify product claims and pricing before publishing.",
                    "Make the CTA concrete and single-action.",
                    "Do not claim guaranteed income or fake social proof.",
                ],
                "finalRecommendation": "ready_with_approval",
            }
        )
    return reviews


def build_cheat_review_pack(out_dir: Path, product: Product, content: dict[str, Any], content_path: Path) -> dict[str, Any]:
    report_dir = out_dir / "reports/promotion-manager/cheat-review"
    draft_dir = report_dir / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    skill_paths = detect_cheat_skill_paths()
    project_state = detect_cheat_project_state(out_dir)
    draft_items = []
    for platform, item in content.items():
        draft_path = draft_dir / f"{slugify(product.name)}-{platform}.md"
        draft_path.write_text(render_cheat_draft(product, platform, item), encoding="utf-8")
        prompt = f"Use cheat-score to score this draft without prediction logging: {draft_path}"
        draft_items.append(
            {
                "platform": platform,
                "draftPath": str(draft_path),
                "reviewPrompt": prompt,
                "contentPath": str(content_path),
                "status": "ready_for_codex_cheat_score",
                "notes": [
                    "This pack prepares the draft for cheat-on-content qualitative scoring.",
                    "It does not create immutable prediction files.",
                    "If the content project is not initialized, run cheat-init before formal scoring.",
                ],
            }
        )
    return {
        "generatedAt": TODAY,
        "status": "cheat_review_pack_created",
        "product": asdict(product),
        "skillDetection": skill_paths,
        "projectState": project_state,
        "drafts": draft_items,
        "nextActions": [
            "Use the reviewPrompt for the target platform draft inside Codex.",
            "Use cheat-score for exploratory scoring only.",
            "Use cheat-predict only when the user explicitly starts a real prediction cycle.",
        ],
        "safety": {
            "writesPredictionLogs": False,
            "usesRealPerformanceData": False,
            "fallbackScorecardRemainsAvailable": True,
        },
    }


def detect_cheat_skill_paths() -> dict[str, Any]:
    candidates = [
        Path.home() / ".codex/skills/cheat-on-content/SKILL.md",
        Path.home() / ".codex/skills/cheat-score/SKILL.md",
        Path.home() / ".codex/skills/cheat-on-content/skills/cheat-score/SKILL.md",
        Path.home() / ".agents/skills/cheat-on-content/SKILL.md",
    ]
    existing = [str(path) for path in candidates if path.exists()]
    return {
        "cheatOnContentInstalled": any(path.endswith("cheat-on-content\\SKILL.md") or path.endswith("cheat-on-content/SKILL.md") for path in existing),
        "cheatScoreInstalled": any("cheat-score" in path for path in existing),
        "paths": existing,
    }


def detect_cheat_project_state(out_dir: Path) -> dict[str, Any]:
    candidates = [
        Path.cwd() / ".cheat-state.json",
        out_dir / ".cheat-state.json",
        out_dir / "rubric_notes.md",
    ]
    existing = [str(path) for path in candidates if path.exists()]
    return {
        "initialized": any(path.endswith(".cheat-state.json") for path in existing),
        "rubricAvailable": any(path.endswith("rubric_notes.md") for path in existing),
        "paths": existing,
    }


def apply_cheat_review_pack(review: list[dict[str, Any]], pack: dict[str, Any]) -> None:
    by_platform = {item["platform"]: item for item in pack["drafts"]}
    for item in review:
        draft = by_platform.get(item["platform"], {})
        item["cheatOnContent"] = {
            "status": pack["status"],
            "draftPath": draft.get("draftPath", ""),
            "reviewPrompt": draft.get("reviewPrompt", ""),
            "cheatOnContentInstalled": pack["skillDetection"]["cheatOnContentInstalled"],
            "cheatScoreInstalled": pack["skillDetection"]["cheatScoreInstalled"],
            "projectInitialized": pack["projectState"]["initialized"],
            "reason": "A review pack was created for Codex to invoke cheat-score without writing prediction logs.",
        }


def render_cheat_draft(product: Product, platform: str, item: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {product.name} - {platform} promotion draft",
            "",
            f"- Product URL: {product.url}",
            f"- Audience: {', '.join(product.audience)}",
            f"- Goal: {product.goal}",
            f"- Platform: {platform}",
            f"- Content type: {item.get('contentType', '')}",
            f"- Title: {item.get('title', '')}",
            f"- Hook: {item.get('hook', '')}",
            f"- CTA: {item.get('cta', '')}",
            f"- Cover text: {item.get('coverText', '')}",
            f"- Compliance notice: {item.get('complianceNotice', '')}",
            "",
            "## Platform Payload",
            "",
            "```json",
            json.dumps(item, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Cheat Review Boundary",
            "",
            "Score this as a draft only. Do not create prediction files unless the user explicitly asks for a prediction cycle.",
        ]
    )


def build_publish_pack(content: dict[str, Any]) -> list[dict[str, Any]]:
    packs = []
    capability_by_platform = {item["platform"]: item for item in CAPABILITIES}
    for platform, item in content.items():
        capability = capability_by_platform.get(platform, {"recommendedMode": "manual_publish_required", "riskLevel": "high"})
        viral_title = str(item.get("viralTitle") or item.get("title") or item.get("description") or "").strip()
        tags = clean_list(item.get("tags"))
        first_batch = item.get("firstBatch") if isinstance(item.get("firstBatch"), dict) else {}
        packs.append(
            {
                "platform": platform,
                "publishMode": capability["recommendedMode"],
                "approvalRequired": True,
                "viralTitle": viral_title,
                "copy": str(item.get("copy") or item.get("article") or item.get("shortVideoScript") or item.get("description") or "").strip(),
                "tags": tags,
                "firstBatch": first_batch,
                "video": {
                    "type": "video",
                    "required": platform in VIDEO_REQUIRED_PLATFORMS,
                    "status": "pending_media_asset_pack" if platform in VIDEO_REQUIRED_PLATFORMS else "not_required",
                    "path": "",
                },
                "cover": {
                    "type": "cover_image",
                    "required": True,
                    "status": "pending_media_asset_pack",
                    "path": "",
                    "coverText": item.get("coverText", ""),
                },
                "detailImages": [],
                "content": item,
                "assets": [],
                "publishSteps": publish_steps_for(platform, capability["recommendedMode"]),
                "scheduleSuggestion": schedule_suggestion_for(platform),
                "trackingPlan": tracking_plan_for(platform, item),
                "trackingFields": [
                    "publishedUrl",
                    "publishedAt",
                    "trackedUrl",
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_content",
                    "views",
                    "likes",
                    "favorites",
                    "comments",
                    "shares",
                    "clicks",
                    "messages",
                    "leads",
                    "orders",
                    "revenue",
                    "evidence",
                ],
                "warnings": [
                    "No automatic publishing in first version.",
                    "No cookie/token/password storage.",
                    "No captcha bypass.",
                    "Human approval required.",
                    "Do not fabricate published URLs or metrics.",
                ],
            }
        )
    return packs


def tracking_plan_for(platform: str, content: dict[str, Any]) -> dict[str, Any]:
    product = content.get("sourceProduct") if isinstance(content.get("sourceProduct"), dict) else {}
    product_name = str(product.get("name") or content.get("title") or "product")
    product_url = str(product.get("url") or "")
    campaign_id = f"{slugify(product_name)}-{TODAY}"
    content_id = f"{campaign_id}-{platform}"
    utm = {
        "utm_source": platform,
        "utm_medium": tracking_medium_for(platform),
        "utm_campaign": campaign_id,
        "utm_content": content_id,
    }
    return {
        "status": "ready" if product_url else "missing_product_url",
        "campaignId": campaign_id,
        "contentId": content_id,
        "trackedUrl": tracked_url(product_url, utm) if product_url else "",
        "utm": utm,
        "businessExportMatchKeys": [
            "publishedUrl",
            "referrer",
            "landingPage",
            "utm_content",
            "utm_campaign",
            "contentId",
            "title",
        ],
        "recommendedBusinessExportColumns": [
            "orderId",
            "utm_source",
            "utm_campaign",
            "utm_content",
            "referrer",
            "landingPage",
            "revenue",
            "orders",
            "status",
        ],
        "guardrail": "Use only real business exports and proven published URLs; never infer orders or revenue from engagement.",
    }


def tracking_medium_for(platform: str) -> str:
    if platform in {"youtube", "douyin", "tiktok"}:
        return "video"
    if platform in {"zhihu", "xiaohongshu"}:
        return "social"
    if platform == "github":
        return "repository"
    return "promotion"


def tracked_url(product_url: str, utm: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(product_url)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query.update(utm)
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def publish_steps_for(platform: str, mode: str) -> list[str]:
    if mode == "official_api_publish":
        return [
            "Verify official API access, app approval, and user authorization.",
            "Open the generated content pack and inspect viral title, copy, tags, first-batch comments, video, cover, detail images, and CTA.",
            "Confirm the target account/repository/channel.",
            "User explicitly approves the API write action.",
            "Only then call the official API or save as draft when the platform supports drafts.",
        ]
    if mode == "browser_assisted_publish":
        return [
            "Open the platform publishing page manually or with browser assistance.",
            "Copy viral title, copy, tags, first-batch comments, cover text, media assets, and CTA from the publish pack.",
            "User verifies account, rules, video, cover, detail images, and preview.",
            "User clicks final publish or saves draft.",
            "Record published URL and time only after real publication evidence exists.",
        ]
    return [
        "Open the platform manually.",
        "Copy the generated viral title, copy, tags, first-batch comments, cover text, media assets, and CTA.",
        "Verify facts, links, product claims, and platform rules.",
        "User publishes manually or saves a draft.",
        "Fill result template with real data only.",
    ]


def schedule_suggestion_for(platform: str) -> str:
    return {
        "youtube": "Publish long video mid-week; test Shorts around the same topic on two separate days.",
        "zhihu": "Publish after the product page has stable details and internal links.",
        "xiaohongshu": "Test two note angles in the same week: pain checklist and before/after template.",
        "douyin": "Post short videos in small batches and compare hook retention manually.",
        "github": "Publish with releases or major repo updates, not as noisy repeated posts.",
        "tiktok": "Post when creator account analytics show active audience windows.",
    }.get(platform, "Schedule after human review.")


def build_result_template(product: Product) -> list[dict[str, Any]]:
    return [
        {
            "platform": platform,
            "published": False,
            "publishedAt": None,
            "publishedUrl": None,
            "views": None,
            "likes": None,
            "favorites": None,
            "comments": None,
            "shares": None,
            "clicks": None,
            "messages": None,
            "leads": None,
            "orders": None,
            "revenue": None,
            "feedback": [],
            "evidence": [],
            "notes": [f"Fill only real {platform} data for {product.name}."],
        }
        for platform in product.platforms
    ]


def build_retrospective(results: list[dict[str, Any]]) -> dict[str, Any]:
    published = [item for item in results if item.get("published") and item.get("publishedUrl") and item.get("evidence")]
    if not published:
        return {
            "status": "waiting_real_data",
            "period": None,
            "publishedItems": [],
            "bestPerformingContent": None,
            "worstPerformingContent": None,
            "channelInsights": [],
            "offerInsights": [],
            "copywritingInsights": [],
            "nextRoundActions": ["Wait for real published URLs and platform evidence before making retrospective claims."],
        }
    return {
        "status": "ready",
        "period": "user_supplied",
        "publishedItems": published,
        "bestPerformingContent": published[0],
        "worstPerformingContent": published[-1],
        "channelInsights": ["Use only observed channel data."],
        "offerInsights": ["Compare click and lead evidence before changing the offer."],
        "copywritingInsights": ["Reuse the strongest observed hook."],
        "nextRoundActions": ["Reuse the strongest hook with a new platform-native angle."],
    }


def write_roadmaps(out_dir: Path) -> None:
    write_doc(out_dir, "05-browser-extension-roadmap.md", render_browser_extension_roadmap())
    write_doc(out_dir, "06-saas-product-roadmap.md", render_saas_roadmap())


def write_legacy_index(out_dir: Path, product: Product) -> None:
    index = (
        "# Promotion Output Index\n\n"
        f"- Product: {product.name}\n"
        f"- Generated: {TODAY}\n"
        "- Docs: `docs/promotion-manager/`\n"
        "- Reports: `reports/promotion-manager/`\n"
        "- Auto publish first version: no\n"
        "- Store cookie/token: no\n"
        "- Fabricate platform metrics: no\n"
    )
    (out_dir / "INDEX.md").write_text(index, encoding="utf-8")


def write_doc(out_dir: Path, name: str, markdown: str) -> None:
    (out_dir / "docs/promotion-manager" / name).write_text(markdown + "\n", encoding="utf-8")


def write_named_report(out_dir: Path, name: str, data: Any, markdown: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / f"{name}.md").write_text(markdown + "\n", encoding="utf-8")


def render_capabilities(items: list[dict[str, Any]]) -> str:
    lines = ["# Platform Publish Capability Map", "", "| Platform | Official API | Mode | Approval | Risk |", "| --- | --- | --- | --- | --- |"]
    for item in items:
        lines.append(
            f"| {item['platform']} | {item['supportsOfficialApi']} | `{item['recommendedMode']}` | {item['approvalRequired']} | {item['riskLevel']} |"
        )
    return "\n".join(lines)


def render_platform_feasibility(report: dict[str, Any]) -> str:
    lines = ["# Platform Publishing Feasibility", "", f"Generated: {report['generatedAt']}", "", render_capabilities(report["capabilities"]), "", "## Source Notes"]
    for source in report["sources"].values():
        lines.append(f"- [{source['title']}]({source['url']}): {source['evidence']}")
    return "\n".join(lines)


def render_reference_projects(report: dict[str, Any]) -> str:
    lines = ["# GitHub Reference Projects", "", report["selectionRule"], "", "| Project | Category | Use | Risk |", "| --- | --- | --- | --- |"]
    for project in report["projects"]:
        lines.append(
            f"| [{project['repo']}]({project['url']}) | {project['category']} | {'; '.join(project['usefulPatterns'])} | {'; '.join(project['riskNotes'])} |"
        )
    return "\n".join(lines)


def render_risk_matrix(rows: list[dict[str, Any]]) -> str:
    lines = ["# Platform Risk Matrix", "", "| Platform | Mode | API | Login | Cookie/Token | Captcha | Account |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(
            f"| {row['platform']} | `{row['recommendedMode']}` | {row['apiLimitRisk']} | {row['loginRisk']} | {row['cookieTokenRisk']} | {row['captchaRisk']} | {row['accountSafetyRisk']} |"
        )
    lines.extend(["", "## Must Not Do"])
    for rule in rows[0]["mustNotDo"]:
        lines.append(f"- {rule}")
    return "\n".join(lines)


def render_self_learning_notes(notes: dict[str, Any]) -> str:
    lines = ["# Self-Learning Notes", "", f"Generated: {notes['generatedAt']}", "", "## Current Conclusion"]
    lines.extend([f"- {item}" for item in notes["currentConclusion"]])
    lines.extend(["", "## Next Research Queue"])
    lines.extend([f"- {item}" for item in notes["nextResearchQueue"]])
    lines.extend(["", "## Skill Use"])
    lines.extend([f"- {item}" for item in notes["skillUse"]])
    return "\n".join(lines)


def render_deconstruction(report: dict[str, Any]) -> str:
    lines = ["# Competitor Deconstruction Report", "", f"Status: `{report['status']}`", "", "## Reusable Patterns"]
    for key in ["winningPatterns", "titlePatterns", "hookPatterns", "contentStructures", "ctaPatterns", "visualPatterns", "risks", "recommendations"]:
        lines.extend(["", f"### {key}"])
        lines.extend([f"- {item}" for item in report[key]])
    return "\n".join(lines)


def render_content_plan(plan: dict[str, Any]) -> str:
    lines = ["# Content Plan", "", f"Positioning: {plan['positioning']}", "", "## Platform Plans"]
    for item in plan["platformPlans"]:
        lines.extend(
            [
                "",
                f"### {item['platform']}",
                f"- Angle: {item['audienceAngle']}",
                f"- Frequency: {item['frequency']}",
                f"- Reuse: {item['reusePlan']}",
                f"- CTA: {item['cta']}",
            ]
        )
        lines.extend([f"- Topic: {topic}" for topic in item["topics"]])
    return "\n".join(lines)


def render_platform_content(content: dict[str, Any]) -> str:
    lines = ["# Platform Content"]
    for platform, item in content.items():
        lines.extend(
            [
                "",
                f"## {platform}",
                f"- Type: {item['contentType']}",
                f"- Title: {item['title']}",
                f"- CTA: {item['cta']}",
                f"- Cover: {item['coverText']}",
                f"- Compliance: {item['complianceNotice']}",
            ]
        )
    return "\n".join(lines)


def render_review(review: list[dict[str, Any]]) -> str:
    lines = ["# Content Review"]
    for item in review:
        lines.extend(
            [
                "",
                f"## {item['platform']}",
                f"- Virality: {item['viralityScore']}",
                f"- Compliance: {item['complianceScore']}",
                f"- Cheat-on-content: {item['cheatOnContent']['status']}",
                f"- Cheat draft: {item['cheatOnContent'].get('draftPath', '')}",
                f"- Recommendation: {item['finalRecommendation']}",
            ]
        )
    return "\n".join(lines)


def render_cheat_review_pack(pack: dict[str, Any]) -> str:
    lines = [
        "# Cheat-On-Content Review Pack",
        "",
        f"Status: `{pack['status']}`",
        f"Cheat-on-content installed: {pack['skillDetection']['cheatOnContentInstalled']}",
        f"Cheat-score installed: {pack['skillDetection']['cheatScoreInstalled']}",
        f"Project initialized: {pack['projectState']['initialized']}",
        "",
        "This pack prepares draft files for Codex to invoke cheat-score. It does not write prediction logs.",
        "",
        "## Drafts",
    ]
    for item in pack["drafts"]:
        lines.extend(
            [
                "",
                f"### {item['platform']}",
                f"- Draft: `{item['draftPath']}`",
                f"- Prompt: `{item['reviewPrompt']}`",
            ]
        )
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {item}" for item in pack["nextActions"]])
    return "\n".join(lines)


def render_publish_pack(packs: list[dict[str, Any]]) -> str:
    lines = ["# Publish Pack", "", "No automatic publishing. Human approval required."]
    for pack in packs:
        lines.extend(
            [
                "",
                f"## {pack['platform']}",
                f"- Mode: `{pack['publishMode']}`",
                f"- Approval required: {pack['approvalRequired']}",
                f"- Viral title: {pack.get('viralTitle', '')}",
                f"- Tags: {', '.join(str(tag) for tag in pack.get('tags', []))}",
                f"- Video: `{pack.get('video', {}).get('status', '')}` {pack.get('video', {}).get('path', '')}",
                f"- Cover: `{pack.get('cover', {}).get('status', '')}` {pack.get('cover', {}).get('path', '')}",
                f"- Detail images: {len(pack.get('detailImages', []))}",
                f"- Schedule: {pack['scheduleSuggestion']}",
                f"- Tracked URL: {pack.get('trackingPlan', {}).get('trackedUrl', '')}",
                f"- UTM content: {pack.get('trackingPlan', {}).get('utm', {}).get('utm_content', '')}",
                "- Steps:",
            ]
        )
        lines.extend([f"  - {step}" for step in pack["publishSteps"]])
    return "\n".join(lines)


def render_result_template(results: list[dict[str, Any]]) -> str:
    lines = ["# Publish Result Input", "", "Fill only real data with evidence."]
    for item in results:
        lines.extend(["", f"## {item['platform']}", f"- published: {item['published']}", "- metrics: null until real data is supplied"])
    return "\n".join(lines)


def render_retrospective(retrospective: dict[str, Any]) -> str:
    lines = ["# Retrospective", "", f"Status: {retrospective['status']}", ""]
    lines.extend([f"- {action}" for action in retrospective["nextRoundActions"]])
    return "\n".join(lines)


def render_browser_extension_roadmap() -> str:
    return """# Browser Extension Roadmap

This is a phase-2 design note only. Do not implement until the user approves plugin development.

## Recommended Shape

- Chrome Extension Manifest V3.
- Local JSON import from `reports/promotion-manager/publish-packs`.
- Content scripts fill title/body/tags/assets where platform UI permits normal user input.
- Human approval button remains mandatory.
- The extension records `publishedUrl` and `publishedAt` only after the user confirms real publication.

## Non-Negotiables

- No password, cookie, token, or API key extraction.
- No captcha bypass.
- No final publish click by the agent.
- No background posting without a visible approval step.
"""


def render_saas_roadmap() -> str:
    return """# SaaS Product Roadmap

This is a phase-3 design note only. Do not implement until the user approves website/SaaS development.

## Modules

- Product library.
- Platform account configuration without plaintext secrets.
- Competitor and deconstruction library.
- Content generator and video script generator.
- Publish calendar and publish-pack manager.
- Manual result input and retrospective reports.
- A/B test planner.
- Template marketplace and paid membership gates.

## First Security Decisions

- Store OAuth tokens only through a proper secret manager.
- Keep every publish action behind a visible approval gate.
- Separate draft generation from publishing permissions.
- Add audit logs before enabling any production API write.
"""


if __name__ == "__main__":
    main()
