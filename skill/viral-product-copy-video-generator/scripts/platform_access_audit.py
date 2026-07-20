#!/usr/bin/env python3
"""Audit official platform access paths for publishing and metrics recovery."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from env_loader import (
    YOUTUBE_ACCESS_TOKEN_ENVS,
    YOUTUBE_CLIENT_ID_ENVS,
    YOUTUBE_CLIENT_SECRET_ENVS,
    blank_env_names,
    load_project_env,
    preparse_env_file,
    present_env_names,
)


TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github", "tiktok"]
AUTOMATION_CRITICAL_ACCESS = {
    "implemented_official_api",
    "implemented_public_api",
    "official_candidate_not_integrated",
}


PLATFORM_ACCESS: dict[str, dict[str, Any]] = {
    "youtube": {
        "label": "YouTube",
        "publish": {
            "access": "implemented_official_api",
            "mode": "official_api_publish",
            "implementedBy": ["publish_executor.py", "youtube_oauth_publish.py"],
            "requiredEnvAny": list(YOUTUBE_ACCESS_TOKEN_ENVS),
            "alternativeEnvAll": ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"],
            "alternativeEnvGroups": [list(YOUTUBE_CLIENT_ID_ENVS), list(YOUTUBE_CLIENT_SECRET_ENVS)],
            "approvalRequired": True,
            "notes": "Uploads use the official YouTube Data API videos.insert endpoint and require channel OAuth authorization.",
            "officialDocs": [
                {
                    "title": "YouTube Data API videos.insert",
                    "url": "https://developers.google.com/youtube/v3/docs/videos/insert",
                }
            ],
        },
        "metrics": {
            "access": "implemented_official_api",
            "mode": "official_api_metrics",
            "implementedBy": ["metrics_intake.py", "metrics_recovery.py"],
            "requiredEnvAny": ["YOUTUBE_API_KEY"],
            "notes": "Video statistics are read from the official videos.list endpoint when an API key is present.",
            "officialDocs": [
                {
                    "title": "YouTube Data API videos.list",
                    "url": "https://developers.google.com/youtube/v3/docs/videos/list",
                }
            ],
        },
    },
    "github": {
        "label": "GitHub",
        "publish": {
            "access": "implemented_official_api",
            "mode": "official_api_publish",
            "implementedBy": ["publish_executor.py"],
            "requiredEnvAny": ["GITHUB_TOKEN", "GH_TOKEN"],
            "approvalRequired": True,
            "notes": "Repository files, issues, and releases use official GitHub REST API paths with write permissions.",
            "officialDocs": [
                {
                    "title": "GitHub REST API repository contents",
                    "url": "https://docs.github.com/en/rest/repos/contents",
                },
                {
                    "title": "GitHub REST API issues",
                    "url": "https://docs.github.com/en/rest/issues/issues",
                },
                {
                    "title": "GitHub REST API releases",
                    "url": "https://docs.github.com/en/rest/releases/releases",
                },
            ],
        },
        "metrics": {
            "access": "implemented_public_api",
            "mode": "public_api_metrics",
            "implementedBy": ["metrics_intake.py", "metrics_recovery.py"],
            "requiredEnvAny": [],
            "notes": "Public repository stars, forks, and watchers can be read without storing credentials.",
            "officialDocs": [
                {
                    "title": "GitHub REST API repositories",
                    "url": "https://docs.github.com/en/rest/repos/repos",
                }
            ],
        },
    },
    "douyin": {
        "label": "Douyin",
        "publish": {
            "access": "manual_or_browser_assisted_required",
            "mode": "browser_assisted_publish",
            "implementedBy": ["browser_publish_session.py", "browser_publish_assistant.py"],
            "requiredEnvAll": [],
            "approvalRequired": True,
            "notes": "Douyin official authorization is not available in the current operator setup. Publish through user-visible browser-assisted/manual payloads; publish_executor.py remains a reserved future official port only.",
            "officialDocs": [
                {
                    "title": "Douyin Open Platform publishing solution",
                    "url": "https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/ability-introduction",
                },
                {
                    "title": "Douyin upload/create video APIs",
                    "url": "https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/upload-video",
                },
                {
                    "title": "Douyin create video API",
                    "url": "https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create",
                }
            ],
        },
        "metrics": {
            "access": "official_or_manual_export_required",
            "mode": "manual_structured_snapshot_or_official_export",
            "implementedBy": ["metrics_intake.py", "metrics_recovery.py"],
            "requiredEnvAll": [],
            "notes": "Use official exports/API access when approved, or browser-visible structured snapshots supplied by the user.",
            "officialDocs": [
                {
                    "title": "Douyin Open Platform docs",
                    "url": "https://open.douyin.com/platform/doc",
                }
            ],
        },
    },
    "tiktok": {
        "label": "TikTok",
        "publish": {
            "access": "official_candidate_not_integrated",
            "mode": "official_app_integration_required",
            "implementedBy": [],
            "requiredEnvAll": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
            "approvalRequired": True,
            "notes": "Direct Post requires app product setup, creator authorization, and approved video.publish scope; no direct executor is bundled yet.",
            "officialDocs": [
                {
                    "title": "TikTok Content Posting API",
                    "url": "https://developers.tiktok.com/doc/content-posting-api-get-started/",
                }
            ],
        },
        "metrics": {
            "access": "official_or_manual_export_required",
            "mode": "manual_structured_snapshot_or_official_export",
            "implementedBy": ["metrics_intake.py", "metrics_recovery.py"],
            "requiredEnvAll": [],
            "notes": "Recover only from official analytics access, exports, or user-visible structured snapshots.",
            "officialDocs": [
                {
                    "title": "TikTok Research API overview",
                    "url": "https://developers.tiktok.com/doc/research-api-specs-query-videos/",
                }
            ],
        },
    },
    "xiaohongshu": {
        "label": "Xiaohongshu",
        "publish": {
            "access": "no_verified_public_creator_publish_endpoint",
            "mode": "manual_or_browser_assisted_until_verified",
            "implementedBy": [],
            "requiredEnvAll": [],
            "approvalRequired": True,
            "notes": "No stable public creator note publishing endpoint is integrated; publish packs remain manual/browser-assisted until official access is verified.",
            "officialDocs": [
                {
                    "title": "Xiaohongshu Open Platform API index",
                    "url": "https://open.xiaohongshu.com/document/api",
                }
            ],
        },
        "metrics": {
            "access": "manual_export_or_structured_snapshot_required",
            "mode": "manual_structured_snapshot_or_export",
            "implementedBy": ["metrics_intake.py", "metrics_recovery.py"],
            "requiredEnvAll": [],
            "notes": "Use exported analytics, screenshots, or browser-visible structured snapshots; do not use private endpoints.",
            "officialDocs": [
                {
                    "title": "Xiaohongshu Open Platform API index",
                    "url": "https://open.xiaohongshu.com/document/api",
                }
            ],
        },
    },
    "zhihu": {
        "label": "Zhihu",
        "publish": {
            "access": "no_verified_public_creator_publish_endpoint",
            "mode": "manual_or_browser_assisted_until_verified",
            "implementedBy": [],
            "requiredEnvAll": [],
            "approvalRequired": True,
            "notes": "Official Zhihu entry points are documented, but no stable public creator article publishing API is integrated; publish packs remain manual/browser-assisted until official access is verified.",
            "officialDocs": [
                {
                    "title": "Zhihu developer portal",
                    "url": "https://developer.zhihu.com/",
                },
                {
                    "title": "Zhihu creator entry",
                    "url": "https://www.zhihu.com/creator",
                },
            ],
        },
        "metrics": {
            "access": "manual_export_or_structured_snapshot_required",
            "mode": "manual_structured_snapshot_or_export",
            "implementedBy": ["metrics_intake.py", "metrics_recovery.py"],
            "requiredEnvAll": [],
            "notes": "Use public page evidence, exported analytics, screenshots, or browser-visible structured snapshots; no public creator analytics API is integrated.",
            "officialDocs": [
                {
                    "title": "Zhihu developer portal",
                    "url": "https://developer.zhihu.com/",
                },
                {
                    "title": "Zhihu creator entry",
                    "url": "https://www.zhihu.com/creator",
                },
            ],
        },
    },
}


OFFICIAL_GAP_RESEARCH: dict[str, dict[str, dict[str, Any]]] = {
    "zhihu": {
        "publish": {
            "searchedOfficialSources": [
                {
                    "title": "Zhihu developer portal",
                    "url": "https://developer.zhihu.com/",
                    "purpose": "Official developer entry; no verified creator article publishing API is integrated.",
                },
                {
                    "title": "Zhihu creator entry",
                    "url": "https://www.zhihu.com/creator",
                    "purpose": "User-visible creator entry for manual/browser-assisted publishing, not an automation API.",
                },
            ],
            "searchedTerms": [
                "Zhihu developer API article publish",
                "Zhihu creator publishing API",
                "Zhihu Open Platform article API",
            ],
            "finding": "No verified official public creator article publishing endpoint is configured for automated writes.",
            "safeFallback": "manual_or_browser_assisted_publish",
        },
        "metrics": {
            "searchedOfficialSources": [
                {
                    "title": "Zhihu developer portal",
                    "url": "https://developer.zhihu.com/",
                    "purpose": "Official developer entry; no verified creator analytics API is integrated.",
                },
                {
                    "title": "Zhihu creator entry",
                    "url": "https://www.zhihu.com/creator",
                    "purpose": "User-visible creator entry for manual analytics export or browser-visible evidence.",
                },
            ],
            "searchedTerms": [
                "Zhihu creator analytics API",
                "Zhihu answer article statistics API",
                "Zhihu Open Platform metrics API",
            ],
            "finding": "No verified official public creator analytics endpoint is configured for automated recovery.",
            "safeFallback": "manual_export_or_structured_snapshot",
        },
    },
    "xiaohongshu": {
        "publish": {
            "searchedOfficialSources": [
                {
                    "title": "Xiaohongshu Open Platform API index",
                    "url": "https://open.xiaohongshu.com/document/api",
                    "purpose": "Configured official API index; no creator note publishing executor is verified in this Skill.",
                }
            ],
            "searchedTerms": [
                "Xiaohongshu creator note publishing API",
                "Xiaohongshu Open Platform note publish",
            ],
            "finding": "Open-platform documentation is reachable, but a stable public creator note publishing executor is not verified.",
            "safeFallback": "manual_or_browser_assisted_publish",
        },
        "metrics": {
            "searchedOfficialSources": [
                {
                    "title": "Xiaohongshu Open Platform API index",
                    "url": "https://open.xiaohongshu.com/document/api",
                    "purpose": "Configured official API index; account analytics still require approved access, export, or visible evidence.",
                }
            ],
            "searchedTerms": [
                "Xiaohongshu creator analytics API",
                "Xiaohongshu note metrics export",
            ],
            "finding": "Metric recovery stays limited to exports, screenshots, public pages, or structured browser snapshots.",
            "safeFallback": "manual_export_or_structured_snapshot",
        },
    },
    "douyin": {
        "publish": {
            "searchedOfficialSources": [
                {
                    "title": "Douyin Open Platform publishing solution",
                    "url": "https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/ability-introduction",
                    "purpose": "Official publishing documentation; current operator authorization is unavailable, so this remains a future reserved port.",
                },
                {
                    "title": "Douyin creator entry",
                    "url": "https://creator.douyin.com/",
                    "purpose": "User-visible creator entry for browser-assisted/manual publishing.",
                },
            ],
            "searchedTerms": [
                "Douyin Open Platform video.create authorization",
                "Douyin creator publishing workflow",
            ],
            "finding": "The current operator cannot obtain Douyin publishing authorization, so direct API publishing is disabled and browser-assisted/manual publishing is selected.",
            "safeFallback": "manual_or_browser_assisted_publish",
        },
        "metrics": {
            "searchedOfficialSources": [
                {
                    "title": "Douyin Open Platform docs",
                    "url": "https://open.douyin.com/platform/doc",
                    "purpose": "Configured official documentation entry; analytics require approved access or export evidence.",
                }
            ],
            "searchedTerms": [
                "Douyin Open Platform video data API",
                "Douyin creator analytics export",
            ],
            "finding": "Publishing is browser-assisted/manual in the current operator setup; metrics recovery still requires approved official access, export, or visible evidence.",
            "safeFallback": "official_export_or_structured_snapshot",
        }
    },
    "tiktok": {
        "publish": {
            "searchedOfficialSources": [
                {
                    "title": "TikTok Content Posting API",
                    "url": "https://developers.tiktok.com/doc/content-posting-api-get-started/",
                    "purpose": "Configured official direct-post documentation; executor integration is not bundled.",
                }
            ],
            "searchedTerms": [
                "TikTok Content Posting API direct post",
                "TikTok video.publish scope",
            ],
            "finding": "Official app path exists, but no reviewed direct-post executor is integrated in this Skill.",
            "safeFallback": "official_app_integration_or_browser_assisted_publish",
        },
        "metrics": {
            "searchedOfficialSources": [
                {
                    "title": "TikTok Research API overview",
                    "url": "https://developers.tiktok.com/doc/research-api-specs-query-videos/",
                    "purpose": "Configured official documentation entry; creator analytics require approved access or export evidence.",
                }
            ],
            "searchedTerms": [
                "TikTok creator analytics API",
                "TikTok video metrics export",
            ],
            "finding": "Metric recovery stays limited to approved official access, exports, screenshots, or structured browser snapshots.",
            "safeFallback": "official_export_or_structured_snapshot",
        },
    },
}


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    platforms = select_platforms(args.platforms)
    records = [platform_record(platform, args.check_live) for platform in platforms]
    doc_summary = official_doc_summary(records)
    report = {
        "generatedAt": TODAY,
        "envLoad": env_load,
        "status": overall_status(records),
        "checkLive": bool(args.check_live),
        "platforms": records,
        "summary": summary(records),
        "officialDocSummary": doc_summary,
        "learningFreshness": learning_freshness(args.check_live, doc_summary),
        "officialDocGapResearch": official_doc_gap_research(records, args.check_live),
        "implementationGaps": implementation_gaps(records),
        "guardrails": [
            "Use official APIs only for automated writes.",
            "Never store, print, or infer credential values; record environment variable names only.",
            "Stop for user action when login, captcha, account verification, or platform review is required.",
            "Treat platforms without verified public creator-publishing access as manual/browser-assisted.",
            "Recover metrics only from official APIs, public pages, user exports, screenshots, or browser-visible structured snapshots.",
        ],
    }
    write_report(out_dir, report)
    print(f"Platform access audit written to: {(report_dir(out_dir) / 'platform-access-audit.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit official platform publishing and metrics access paths.")
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter. Defaults to all supported platforms.")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before auditing credential presence. Values are never written to reports.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument(
        "--check-live",
        action="store_true",
        help="Fetch official doc URLs and record reachability status. This never sends credentials.",
    )
    return parser.parse_args()


def select_platforms(value: str) -> list[str]:
    if not value:
        return DEFAULT_PLATFORMS
    selected = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in selected if item not in PLATFORM_ACCESS]
    if unknown:
        raise SystemExit(f"Unsupported platform(s): {', '.join(unknown)}")
    return selected


def platform_record(platform: str, check_live: bool) -> dict[str, Any]:
    config = PLATFORM_ACCESS[platform]
    publish = capability_record(config["publish"], check_live)
    metrics = capability_record(config["metrics"], check_live)
    return {
        "platform": platform,
        "label": config["label"],
        "publish": publish,
        "metrics": metrics,
        "automationLevel": automation_level(publish, metrics),
        "nextActions": next_actions(platform, publish, metrics),
    }


def capability_record(config: dict[str, Any], check_live: bool) -> dict[str, Any]:
    docs = [dict(item) for item in config.get("officialDocs", [])]
    if check_live:
        for doc in docs:
            doc["liveCheck"] = check_url(str(doc["url"]))
    env = env_status(config)
    doc_status = official_doc_status(docs, check_live)
    return {
        "access": config["access"],
        "mode": config["mode"],
        "implementedBy": config.get("implementedBy", []),
        "credentialStatus": env,
        "approvalRequired": bool(config.get("approvalRequired", False)),
        "officialDocs": docs,
        "officialDocEvidenceStatus": doc_status,
        "notes": config["notes"],
        "readyForAutomation": ready_for_automation(config, env),
    }


def official_doc_status(docs: list[dict[str, Any]], check_live: bool) -> str:
    if not docs:
        return "missing_official_docs"
    if not check_live:
        return "configured_not_live_checked"
    statuses = [str((doc.get("liveCheck") or {}).get("status", "not_checked")) for doc in docs]
    if all(status == "reachable" for status in statuses):
        return "all_reachable"
    if any(status == "reachable" for status in statuses):
        return "partially_reachable"
    return "unreachable"


def env_status(config: dict[str, Any]) -> dict[str, Any]:
    any_names = list(config.get("requiredEnvAny") or [])
    all_names = list(config.get("requiredEnvAll") or [])
    alternative_all = list(config.get("alternativeEnvAll") or [])
    alternative_groups = [list(group) for group in config.get("alternativeEnvGroups") or []]
    grouped_names = [name for group in alternative_groups for name in group]
    present_any = present_env_names(any_names)
    present_all = present_env_names(all_names)
    present_alternative = present_env_names(alternative_all + grouped_names)
    alternative_all_ready = bool(alternative_all) and len(present_env_names(alternative_all)) == len(alternative_all)
    alternative_group_ready = bool(alternative_groups) and all(any(os.environ.get(name) for name in group) for group in alternative_groups)
    if any_names:
        ready = bool(present_any) or alternative_all_ready or alternative_group_ready
    elif all_names:
        ready = len(present_all) == len(all_names)
    else:
        ready = True
    all_known_names = any_names + all_names + alternative_all + grouped_names
    return {
        "requiredAny": any_names,
        "requiredAll": all_names,
        "alternativeAll": alternative_all,
        "alternativeGroups": alternative_groups,
        "presentEnv": sorted(set(present_any + present_all + present_alternative)),
        "missingEnv": missing_env_names(any_names, all_names, alternative_all, alternative_groups),
        "blankEnv": blank_env_names(all_known_names),
        "ready": ready,
        "valuesStored": False,
    }


def missing_env_names(
    any_names: list[str],
    all_names: list[str],
    alternative_all: list[str],
    alternative_groups: list[list[str]],
) -> list[str]:
    missing: list[str] = []
    if any_names and not any(os.environ.get(name) for name in any_names):
        missing.extend(any_names)
    missing.extend(name for name in all_names if not os.environ.get(name))
    if alternative_groups:
        for group in alternative_groups:
            if not any(os.environ.get(name) for name in group):
                missing.append(" or ".join(group))
    elif alternative_all and not all(os.environ.get(name) for name in alternative_all):
        missing.extend(name for name in alternative_all if not os.environ.get(name))
    return missing


def ready_for_automation(config: dict[str, Any], env: dict[str, Any]) -> bool:
    return config["access"] in {"implemented_official_api", "implemented_public_api"} and bool(env["ready"])


def automation_level(publish: dict[str, Any], metrics: dict[str, Any]) -> str:
    if publish["readyForAutomation"] and metrics["readyForAutomation"]:
        return "official_publish_and_metrics_ready"
    if publish["access"] == "implemented_official_api":
        return "official_publish_ready_when_credentials_present"
    if publish["access"] == "official_candidate_not_integrated":
        return "official_app_integration_required"
    if publish["access"] == "manual_or_browser_assisted_required":
        return "manual_or_browser_assisted_required"
    return "manual_or_browser_assisted_required"


def next_actions(platform: str, publish: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if publish["access"] == "implemented_official_api" and not publish["credentialStatus"]["ready"]:
        actions.append("Set the required publish environment variables only when execution is approved.")
    if publish["access"] == "official_candidate_not_integrated":
        actions.append("Complete official developer-app approval and implement a reviewed executor before direct publishing.")
    if publish["access"] in {"no_verified_public_creator_publish_endpoint", "manual_or_browser_assisted_required"}:
        actions.append("Keep publishing manual/browser-assisted until official creator publishing access is verified.")
    if metrics["access"] in {"manual_export_or_structured_snapshot_required", "official_or_manual_export_required"}:
        actions.append("Recover metrics from official exports, screenshots, public pages, or structured browser snapshots.")
    if platform == "douyin":
        actions.append("Use Douyin browser-assisted publishing now; keep the official API executor as a future reserved port only.")
    if platform == "tiktok":
        actions.append("Do not treat app credentials alone as publish readiness; user authorization and platform review are still required.")
    return actions


def overall_status(records: list[dict[str, Any]]) -> str:
    doc_statuses = {
        record[area]["officialDocEvidenceStatus"]
        for record in records
        for area in ["publish", "metrics"]
        if record[area]["access"] in {"implemented_official_api", "official_candidate_not_integrated"}
    }
    if "unreachable" in doc_statuses:
        return "partial_ready_official_doc_verification_failed"
    levels = {record["automationLevel"] for record in records}
    if levels == {"official_publish_and_metrics_ready"}:
        return "full_official_access_ready"
    if "manual_or_browser_assisted_required" in levels or "official_app_integration_required" in levels:
        return "partial_ready_official_paths_mapped"
    return "partial_ready_credentials_required"


def summary(records: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {"total": len(records)}
    for record in records:
        level = str(record["automationLevel"])
        result[level] = result.get(level, 0) + 1
    return dict(sorted(result.items()))


def official_doc_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {
        "totalDocs": 0,
        "missingDocCapabilities": 0,
        "reachableDocs": 0,
        "unreachableDocs": 0,
        "httpErrorDocs": 0,
        "uncheckedDocs": 0,
        "criticalFailedDocs": 0,
        "fallbackFailedDocs": 0,
    }
    checked_at: list[str] = []
    by_status: dict[str, int] = {}
    failed_doc_capabilities: list[dict[str, str]] = []
    for record in records:
        for area in ["publish", "metrics"]:
            capability = record[area]
            status = str(capability.get("officialDocEvidenceStatus", "unknown"))
            by_status[status] = by_status.get(status, 0) + 1
            access = str(capability.get("access") or "")
            critical = access in AUTOMATION_CRITICAL_ACCESS
            docs = capability.get("officialDocs") or []
            if not docs:
                counts["missingDocCapabilities"] += 1
                continue
            for doc in docs:
                counts["totalDocs"] += 1
                live = doc.get("liveCheck") or {}
                live_status = str(live.get("status") or "unchecked")
                if live.get("checkedAt"):
                    checked_at.append(str(live["checkedAt"]))
                if live_status == "reachable":
                    counts["reachableDocs"] += 1
                elif live_status == "http_error":
                    counts["httpErrorDocs"] += 1
                elif live_status == "unchecked":
                    counts["uncheckedDocs"] += 1
                else:
                    counts["unreachableDocs"] += 1
                if live_status not in {"reachable", "unchecked"}:
                    if critical:
                        counts["criticalFailedDocs"] += 1
                    else:
                        counts["fallbackFailedDocs"] += 1
                    failed_doc_capabilities.append(
                        {
                            "platform": str(record.get("platform") or ""),
                            "area": area,
                            "access": access,
                            "title": str(doc.get("title") or ""),
                            "url": str(doc.get("url") or ""),
                            "status": live_status,
                        }
                    )
    return {
        **counts,
        "capabilityEvidenceStatus": dict(sorted(by_status.items())),
        "failedDocCapabilities": failed_doc_capabilities,
        "checkedAt": sorted(set(checked_at)),
    }


def learning_freshness(check_live: bool, doc_summary: dict[str, Any]) -> dict[str, Any]:
    missing = int(doc_summary.get("missingDocCapabilities") or 0)
    total = int(doc_summary.get("totalDocs") or 0)
    reachable = int(doc_summary.get("reachableDocs") or 0)
    failed = int(doc_summary.get("unreachableDocs") or 0) + int(doc_summary.get("httpErrorDocs") or 0)
    critical_failed = int(doc_summary.get("criticalFailedDocs") or 0)
    if not check_live:
        status = "stale_not_live_checked"
    elif critical_failed:
        status = "partial_live_check_failed"
    elif missing:
        status = "partial_missing_official_doc_sources"
    elif failed:
        status = "fresh_live_checked_with_warnings"
    elif total and reachable == total:
        status = "fresh_live_checked"
    else:
        status = "partial_no_reachable_docs"
    return {
        "status": status,
        "checkLive": bool(check_live),
        "checkedAt": doc_summary.get("checkedAt", []),
        "totalDocs": total,
        "reachableDocs": reachable,
        "missingDocCapabilities": missing,
        "failedDocs": failed,
        "criticalFailedDocs": critical_failed,
        "fallbackFailedDocs": int(doc_summary.get("fallbackFailedDocs") or 0),
        "warning": (
            "Some official documentation endpoints for manual/browser-assisted fallback platforms were not reachable "
            "during this live check; no automated executor is enabled from those sources."
            if status == "fresh_live_checked_with_warnings"
            else ""
        ),
        "refreshCommand": "python scripts/platform_access_audit.py --check-live --out-dir \"./promotion-output\"",
    }


def implementation_gaps(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for record in records:
        publish = record["publish"]
        metrics = record["metrics"]
        if publish["access"] == "official_candidate_not_integrated":
            gaps.append({"platform": record["platform"], "area": "publish", "gap": "official_app_executor_not_integrated"})
        if publish["access"] == "no_verified_public_creator_publish_endpoint":
            gaps.append({"platform": record["platform"], "area": "publish", "gap": "verified_official_creator_publish_api_missing"})
        if publish["access"] == "manual_or_browser_assisted_required":
            gaps.append({"platform": record["platform"], "area": "publish", "gap": "manual_browser_assisted_publish_required"})
        if metrics["access"] in {"manual_export_or_structured_snapshot_required", "official_or_manual_export_required"}:
            gaps.append({"platform": record["platform"], "area": "metrics", "gap": "official_or_user_export_evidence_required"})
        for area in ["publish", "metrics"]:
            capability = record[area]
            doc_status = capability.get("officialDocEvidenceStatus")
            if doc_status == "missing_official_docs":
                gaps.append({"platform": record["platform"], "area": area, "gap": "official_doc_evidence_missing"})
            elif doc_status == "unreachable":
                gaps.append({"platform": record["platform"], "area": area, "gap": "official_doc_live_check_failed"})
            elif doc_status == "partially_reachable":
                gaps.append({"platform": record["platform"], "area": area, "gap": "official_doc_live_check_partial"})
    return gaps


def official_doc_gap_research(records: list[dict[str, Any]], check_live: bool) -> dict[str, Any]:
    live_cache: dict[str, dict[str, Any]] = {}
    items: list[dict[str, Any]] = []
    for record in records:
        for area in ["publish", "metrics"]:
            capability = record[area]
            if not needs_gap_research(capability):
                continue
            items.append(gap_research_record(record, area, capability, check_live, live_cache))
    missing_docs = sum(1 for item in items if item["docEvidenceStatus"] == "missing_official_docs")
    manual_fallbacks = sum(
        1
        for item in items
        if item["safeFallback"] in {"manual_or_browser_assisted_publish", "manual_export_or_structured_snapshot"}
    )
    official_app_gaps = sum(1 for item in items if item["access"] == "official_candidate_not_integrated")
    if missing_docs:
        status = "unresolved_missing_official_docs"
    elif official_app_gaps:
        status = "official_app_or_executor_gaps_documented"
    elif items:
        status = "manual_or_evidence_fallbacks_documented"
    else:
        status = "no_gap_research_required"
    return {
        "status": status,
        "checkLive": bool(check_live),
        "summary": {
            "records": len(items),
            "missingOfficialDocCapabilities": missing_docs,
            "manualOrBrowserFallbacks": manual_fallbacks,
            "officialAppOrExecutorGaps": official_app_gaps,
        },
        "records": items,
        "guardrails": [
            "A candidate source is not treated as a verified official API unless the capability officialDocs entry names a specific documented path.",
            "Missing official documentation keeps the capability manual/browser-assisted or export/snapshot based.",
            "Do not use private endpoints, hidden browser tokens, cookies, or captcha/login bypass as a substitute for official access.",
        ],
    }


def needs_gap_research(capability: dict[str, Any]) -> bool:
    access = str(capability.get("access") or "")
    return (
        capability.get("officialDocEvidenceStatus") == "missing_official_docs"
        or access
        in {
            "no_verified_public_creator_publish_endpoint",
            "manual_or_browser_assisted_required",
            "official_candidate_not_integrated",
            "manual_export_or_structured_snapshot_required",
            "official_or_manual_export_required",
        }
    )


def gap_research_record(
    platform_record_value: dict[str, Any],
    area: str,
    capability: dict[str, Any],
    check_live: bool,
    live_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    platform = str(platform_record_value["platform"])
    configured = OFFICIAL_GAP_RESEARCH.get(platform, {}).get(area, {})
    sources = [dict(item) for item in configured.get("searchedOfficialSources", [])]
    if check_live:
        for source in sources:
            url = str(source.get("url") or "")
            if not url:
                continue
            if url not in live_cache:
                live_cache[url] = check_url(url)
            source["liveCheck"] = dict(live_cache[url])
    doc_status = str(capability.get("officialDocEvidenceStatus") or "")
    access = str(capability.get("access") or "")
    return {
        "platform": platform,
        "label": platform_record_value.get("label", platform),
        "area": area,
        "access": access,
        "mode": capability.get("mode", ""),
        "docEvidenceStatus": doc_status,
        "finding": configured.get("finding") or default_gap_finding(access, doc_status),
        "safeFallback": configured.get("safeFallback") or default_gap_fallback(area, access),
        "searchedTerms": configured.get("searchedTerms", []),
        "searchedOfficialSources": sources,
        "nextAction": gap_research_next_action(area, access, doc_status),
        "prohibitedWorkarounds": [
            "private endpoints",
            "cookie or hidden-token extraction",
            "automatic login",
            "captcha or risk-control bypass",
            "claiming full automation without real official execution evidence",
        ],
    }


def default_gap_finding(access: str, doc_status: str) -> str:
    if doc_status == "missing_official_docs":
        return "No verified official documentation source is configured for this capability."
    if access == "official_candidate_not_integrated":
        return "Official app documentation is configured, but no reviewed executor is integrated."
    if access == "no_verified_public_creator_publish_endpoint":
        return "No verified public creator publishing endpoint is integrated."
    return "Capability requires official export, user export, public page evidence, or structured browser-visible evidence."


def default_gap_fallback(area: str, access: str) -> str:
    if access == "official_candidate_not_integrated":
        return "official_app_integration_required"
    if area == "publish":
        return "manual_or_browser_assisted_publish"
    return "manual_export_or_structured_snapshot"


def gap_research_next_action(area: str, access: str, doc_status: str) -> str:
    if doc_status == "missing_official_docs":
        return "Add a specific verified official documentation URL for this capability, or keep the capability on the safe fallback path."
    if access == "official_candidate_not_integrated":
        return "Implement and review an official executor only after app approval, scopes, and authorization are available."
    if area == "publish":
        return "Prepare browser-assisted/manual publish payloads and register the real URL after the user publishes."
    return "Recover only from official exports, screenshots, public pages, business exports, or structured browser-visible snapshots."


def check_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "CodexSkillPlatformAccessAudit/1.0"})
    checked_at = live_timestamp()
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return {
                "status": "reachable",
                "httpStatus": response.status,
                "finalUrl": response.geturl(),
                "contentType": response.headers.get("Content-Type", ""),
                "checkedAt": checked_at,
            }
    except urllib.error.HTTPError as exc:
        return {"status": "http_error", "httpStatus": exc.code, "checkedAt": checked_at}
    except urllib.error.URLError as exc:
        return {"status": "unreachable", "reason": str(exc.reason)[:160], "checkedAt": checked_at}
    except TimeoutError:
        return {"status": "timeout", "checkedAt": checked_at}
    except (http.client.RemoteDisconnected, ConnectionResetError, OSError) as exc:
        return {"status": "unreachable", "reason": str(exc)[:160], "checkedAt": checked_at}


def live_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "platform-access-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "platform-access-audit.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Platform Access Audit",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Live doc check: {report['checkLive']}",
        f"- Learning freshness: `{report.get('learningFreshness', {}).get('status', '')}`",
        "",
        "## Platforms",
    ]
    for record in report["platforms"]:
        lines.extend(
            [
                "",
                f"### {record['label']}",
                f"- Automation level: `{record['automationLevel']}`",
                f"- Publish access: `{record['publish']['access']}`",
                f"- Publish env present: {', '.join(record['publish']['credentialStatus']['presentEnv']) or 'none'}",
                f"- Metrics access: `{record['metrics']['access']}`",
                f"- Metrics env present: {', '.join(record['metrics']['credentialStatus']['presentEnv']) or 'none'}",
            ]
        )
        for action in record["nextActions"]:
            lines.append(f"- Next action: {action}")
        lines.append(f"- Publish doc evidence: `{record['publish']['officialDocEvidenceStatus']}`")
        lines.append(f"- Metrics doc evidence: `{record['metrics']['officialDocEvidenceStatus']}`")
        docs = record["publish"]["officialDocs"] + record["metrics"]["officialDocs"]
        if docs:
            lines.append("- Official docs:")
            seen = set()
            for doc in docs:
                if doc["url"] in seen:
                    continue
                seen.add(doc["url"])
                suffix = ""
                if doc.get("liveCheck"):
                    suffix = f" ({doc['liveCheck']['status']})"
                lines.append(f"  - {doc['title']}: {doc['url']}{suffix}")
    if report["implementationGaps"]:
        lines.extend(["", "## Implementation Gaps"])
        for gap in report["implementationGaps"]:
            lines.append(f"- {gap['platform']} {gap['area']}: `{gap['gap']}`")
    gap_research = report.get("officialDocGapResearch") if isinstance(report.get("officialDocGapResearch"), dict) else {}
    if gap_research:
        summary = gap_research.get("summary") if isinstance(gap_research.get("summary"), dict) else {}
        lines.extend(
            [
                "",
                "## Official Doc Gap Research",
                f"- Status: `{gap_research.get('status', '')}`",
                f"- Records: {summary.get('records', 0)}",
                f"- Missing official-doc capabilities: {summary.get('missingOfficialDocCapabilities', 0)}",
                f"- Manual/browser fallbacks: {summary.get('manualOrBrowserFallbacks', 0)}",
            ]
        )
        for item in gap_research.get("records", []):
            lines.append(
                f"- {item['platform']} {item['area']}: `{item['finding']}` "
                f"-> fallback `{item['safeFallback']}`"
            )
            for source in item.get("searchedOfficialSources", []):
                suffix = ""
                if source.get("liveCheck"):
                    suffix = f" ({source['liveCheck']['status']})"
                lines.append(f"  - Candidate source: {source['title']}: {source['url']}{suffix}")
            lines.append(f"  - Next action: {item['nextAction']}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/platform-access"


if __name__ == "__main__":
    main()
