#!/usr/bin/env python3
"""Build a creator leaderboard from ranked viral materials."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
COMPETITOR_DIR = Path("reports/promotion-manager/competitors")
PUBLIC_RESEARCH_PLATFORMS = {"youtube", "github"}
BROWSER_ASSISTED_PLATFORMS = {"zhihu", "xiaohongshu", "douyin", "tiktok"}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    materials = load_materials(args, out_dir)
    creators = build_creators(materials, args.top_n)
    tasks = build_creator_tasks(creators)
    write_outputs(out_dir, creators, tasks, materials)
    print(f"Creator leaderboard written to: {(report_dir(out_dir) / 'creator-leaderboard.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Group viral materials by creator/account and create follow-up tracking tasks.")
    parser.add_argument("--viral-library", default="", help="Path to viral-content-library.json.")
    parser.add_argument("--workflow-manifest", default="", help="Workflow manifest whose viralContentLibrary path should be used.")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_materials(args: argparse.Namespace, out_dir: Path) -> list[dict[str, Any]]:
    candidates = []
    if args.viral_library:
        candidates.append(Path(args.viral_library))
    if args.workflow_manifest:
        manifest_path = Path(args.workflow_manifest)
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                library_path = manifest.get("competitorDiscovery", {}).get("viralContentLibrary", {}).get("library")
                if library_path:
                    candidates.append(Path(library_path))
            except json.JSONDecodeError:
                pass
    candidates.append(report_dir(out_dir) / "viral-content-library.json")

    seen: set[Path] = set()
    materials = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("materials"), list):
            for item in payload["materials"]:
                if isinstance(item, dict):
                    material = dict(item)
                    material["_sourceLibrary"] = str(path)
                    materials.append(material)
    return materials


def build_creators(materials: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for material in materials:
        creator_name = normalize_space(material.get("creatorName") or "")
        platform = normalize_space(material.get("platform") or "unknown")
        if not creator_name:
            creator_name = inferred_creator_name(material)
        key = f"{platform}:{creator_name.lower()}"
        creator = grouped.setdefault(
            key,
            {
                "id": "",
                "rank": 0,
                "creatorName": creator_name,
                "platform": platform,
                "platforms": set(),
                "materialCount": 0,
                "metricBackedMaterials": 0,
                "totalViralScore": 0.0,
                "maxViralScore": 0.0,
                "averageViralScore": 0.0,
                "metricTotals": {},
                "reusablePatterns": {},
                "sampleUrls": [],
                "topMaterials": [],
                "sourceLibraries": set(),
                "trackingMode": tracking_mode_for(platform),
                "trackingStatus": tracking_status_for(platform, creator_name),
            },
        )
        update_creator(creator, material)

    creators = list(grouped.values())
    for creator in creators:
        finalize_creator(creator)
    creators.sort(key=lambda item: (item["totalViralScore"], item["metricBackedMaterials"], item["materialCount"]), reverse=True)
    limited = creators[: max(top_n, 0)]
    for index, creator in enumerate(limited, start=1):
        creator["rank"] = index
        creator["id"] = f"creator-{index:03d}"
    return limited


def update_creator(creator: dict[str, Any], material: dict[str, Any]) -> None:
    platform = normalize_space(material.get("platform") or creator["platform"])
    score = numeric((material.get("viralSignals") or {}).get("score"), 0.0)
    metrics = material.get("visibleMetrics") if isinstance(material.get("visibleMetrics"), dict) else {}
    creator["platforms"].add(platform)
    creator["materialCount"] += 1
    creator["totalViralScore"] += score
    creator["maxViralScore"] = max(creator["maxViralScore"], score)
    if metrics:
        creator["metricBackedMaterials"] += 1
    for name, value in metrics.items():
        normalized = metric_value(value)
        if normalized is not None:
            creator["metricTotals"][name] = creator["metricTotals"].get(name, 0.0) + normalized
    for pattern in material.get("reusablePatterns", []) if isinstance(material.get("reusablePatterns"), list) else []:
        pattern = str(pattern)
        creator["reusablePatterns"][pattern] = creator["reusablePatterns"].get(pattern, 0) + 1
    url = normalize_space(material.get("url") or "")
    if url and url not in creator["sampleUrls"]:
        creator["sampleUrls"].append(url)
    source_library = normalize_space(material.get("_sourceLibrary") or "")
    if source_library:
        creator["sourceLibraries"].add(source_library)
    creator["topMaterials"].append(
        {
            "materialId": material.get("id", ""),
            "libraryRank": material.get("libraryRank", 0),
            "platform": platform,
            "title": material.get("title", ""),
            "url": url,
            "hook": material.get("hook", ""),
            "viralScore": score,
            "metricFields": sorted(metrics),
        }
    )


def finalize_creator(creator: dict[str, Any]) -> None:
    count = max(creator["materialCount"], 1)
    creator["averageViralScore"] = round(creator["totalViralScore"] / count, 4)
    creator["metricTotals"] = dict(sorted(creator["metricTotals"].items()))
    creator["reusablePatterns"] = dict(sorted(creator["reusablePatterns"].items(), key=lambda item: (-item[1], item[0])))
    creator["platforms"] = sorted(creator["platforms"])
    creator["sourceLibraries"] = sorted(creator["sourceLibraries"])
    creator["topMaterials"].sort(key=lambda item: item["viralScore"], reverse=True)
    creator["topMaterials"] = creator["topMaterials"][:5]
    creator["sampleUrls"] = creator["sampleUrls"][:5]


def build_creator_tasks(creators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    for creator in creators:
        tasks.append(
            {
                "id": f"creator-follow-up-{creator['rank']:03d}",
                "creatorId": creator["id"],
                "priority": creator["rank"],
                "creatorName": creator["creatorName"],
                "platform": creator["platform"],
                "trackingMode": creator["trackingMode"],
                "status": creator["trackingStatus"],
                "sampleUrls": creator["sampleUrls"],
                "requiredEvidence": required_evidence_for(creator["trackingMode"]),
                "recommendedActions": recommended_actions_for(creator),
            }
        )
    return tasks


def required_evidence_for(mode: str) -> list[str]:
    if mode == "public_or_official_research_candidate":
        return ["official/public profile or channel URL", "recent top posts/videos", "visible metrics or official API evidence"]
    if mode == "browser_assisted_or_user_export_required":
        return ["browser-visible creator profile or user export", "screenshots/transcripts for metrics used", "real public material URLs"]
    return ["manual access-rule review", "public creator identity evidence"]


def recommended_actions_for(creator: dict[str, Any]) -> list[str]:
    if creator["trackingMode"] == "public_or_official_research_candidate":
        return [
            "Open public profile/channel pages or official APIs where available.",
            "Capture the creator's newest high-performing materials before the next content generation run.",
        ]
    if creator["trackingMode"] == "browser_assisted_or_user_export_required":
        return [
            "Use browser-visible review or account export; stop at login, captcha, or risk-control prompts.",
            "Provide copied visible text/screenshots before using metrics in analysis.",
        ]
    return ["Review platform access rules before any automated fetch."]


def write_outputs(out_dir: Path, creators: list[dict[str, Any]], tasks: list[dict[str, Any]], materials: list[dict[str, Any]]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    leaderboard = {
        "generatedAt": TODAY,
        "creatorCount": len(creators),
        "sourceMaterialCount": len(materials),
        "creators": creators,
        "summary": summarize_creators(creators),
        "guardrails": guardrails(),
    }
    task_report = {
        "generatedAt": TODAY,
        "taskCount": len(tasks),
        "tasks": tasks,
        "summary": summarize_tasks(tasks),
        "guardrails": guardrails(),
    }
    (directory / "creator-leaderboard.json").write_text(json.dumps(leaderboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "creator-leaderboard.md").write_text(render_leaderboard_markdown(leaderboard) + "\n", encoding="utf-8")
    (directory / "creator-follow-up-tasks.json").write_text(json.dumps(task_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "creator-follow-up-tasks.md").write_text(render_tasks_markdown(task_report) + "\n", encoding="utf-8")


def summarize_creators(creators: list[dict[str, Any]]) -> dict[str, Any]:
    platforms: dict[str, int] = {}
    tracking_modes: dict[str, int] = {}
    for creator in creators:
        platforms[creator["platform"]] = platforms.get(creator["platform"], 0) + 1
        tracking_modes[creator["trackingMode"]] = tracking_modes.get(creator["trackingMode"], 0) + 1
    return {"platforms": dict(sorted(platforms.items())), "trackingModes": dict(sorted(tracking_modes.items()))}


def summarize_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    modes: dict[str, int] = {}
    for task in tasks:
        statuses[task["status"]] = statuses.get(task["status"], 0) + 1
        modes[task["trackingMode"]] = modes.get(task["trackingMode"], 0) + 1
    return {"statuses": dict(sorted(statuses.items())), "trackingModes": dict(sorted(modes.items()))}


def tracking_mode_for(platform: str) -> str:
    if platform in PUBLIC_RESEARCH_PLATFORMS:
        return "public_or_official_research_candidate"
    if platform in BROWSER_ASSISTED_PLATFORMS:
        return "browser_assisted_or_user_export_required"
    return "manual_access_rule_review_required"


def tracking_status_for(platform: str, creator_name: str) -> str:
    if not creator_name or creator_name.startswith("unknown"):
        return "manual_identity_required"
    if platform in PUBLIC_RESEARCH_PLATFORMS:
        return "ready"
    if platform in BROWSER_ASSISTED_PLATFORMS:
        return "queued_browser_assisted"
    return "queued_manual_review"


def inferred_creator_name(material: dict[str, Any]) -> str:
    url = normalize_space(material.get("url") or "")
    host = urllib.parse.urlparse(url).netloc.lower()
    return f"unknown creator on {host or normalize_space(material.get('platform') or 'unknown')}"


def metric_value(value: Any) -> float | None:
    if isinstance(value, dict):
        return numeric(value.get("normalized"), None)
    return numeric(value, None)


def numeric(value: Any, default: float | None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def report_dir(out_dir: Path) -> Path:
    return out_dir / COMPETITOR_DIR


def guardrails() -> list[str]:
    return [
        "Use official APIs, public pages, browser-visible snapshots, or user exports only.",
        "Do not bypass captcha, login prompts, rate limits, or platform risk controls.",
        "Do not store cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
        "Do not fabricate creator metrics, platform metrics, published URLs, orders, or revenue.",
    ]


def render_leaderboard_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Creator Leaderboard",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Creators: {report['creatorCount']}",
        f"- Source materials: {report['sourceMaterialCount']}",
        "",
        "## Top Creators",
    ]
    for creator in report["creators"]:
        lines.extend(
            [
                "",
                f"### {creator['rank']}. {creator['creatorName']}",
                f"- Platform: {creator['platform']}",
                f"- Materials: {creator['materialCount']}",
                f"- Total viral score: {creator['totalViralScore']}",
                f"- Tracking mode: `{creator['trackingMode']}`",
                f"- Sample URLs: {', '.join(creator['sampleUrls']) if creator['sampleUrls'] else 'manual evidence required'}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_tasks_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Creator Follow-Up Tasks",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Tasks: {report['taskCount']}",
        "",
        "## Tasks",
    ]
    for task in report["tasks"]:
        lines.extend(
            [
                "",
                f"### {task['id']} - {task['creatorName']}",
                f"- Platform: {task['platform']}",
                f"- Mode: `{task['trackingMode']}`",
                f"- Status: `{task['status']}`",
                f"- Required evidence: {', '.join(task['requiredEvidence'])}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
