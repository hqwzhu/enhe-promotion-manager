#!/usr/bin/env python3
"""Enhance generated promotion content with observed competitor patterns."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
GENERATED_DIR = Path("reports/promotion-manager/generated-content")


def main() -> None:
    args = parse_args()
    content_path = Path(args.content_json)
    content = json.loads(content_path.read_text(encoding="utf-8-sig"))
    materials = load_materials(Path(args.viral_library) if args.viral_library else None)
    deep_records = load_deep_records(Path(args.deep_library) if args.deep_library else None)
    enhanced, strategy = enhance_content(content, materials, deep_records)
    out_dir = Path(args.out_dir)
    report_paths = write_reports(out_dir, content_path, enhanced, strategy)
    if args.write_back:
        backup_path = content_path.with_suffix(".base.json")
        if not backup_path.exists():
            shutil.copyfile(content_path, backup_path)
        content_path.write_text(json.dumps(enhanced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report_paths["writeBack"] = str(content_path)
        report_paths["backup"] = str(backup_path)
    if args.publish_pack:
        update_publish_pack(Path(args.publish_pack), enhanced)
    print(f"Competitor-informed content written to: {Path(report_paths['json']).resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Use viral/deep competitor libraries to enhance generated platform content.")
    parser.add_argument("--content-json", required=True)
    parser.add_argument("--viral-library", default="")
    parser.add_argument("--deep-library", default="")
    parser.add_argument("--publish-pack", default="", help="Optional publish pack to update with enhanced content.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--write-back", action="store_true", help="Overwrite --content-json after writing a .base.json backup.")
    return parser.parse_args()


def load_materials(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    return [item for item in data.get("materials", []) if isinstance(item, dict)]


def load_deep_records(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    return [item for item in data.get("records", []) if isinstance(item, dict)]


def enhance_content(
    content: dict[str, Any],
    materials: list[dict[str, Any]],
    deep_records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    enhanced = deepcopy(content)
    strategy: dict[str, Any] = {
        "generatedAt": TODAY,
        "status": "ready" if materials or deep_records else "skipped",
        "sourceCounts": {"viralMaterials": len(materials), "deepRecords": len(deep_records)},
        "platforms": {},
        "guardrails": guardrails(),
    }
    for platform, item in enhanced.items():
        if not isinstance(item, dict):
            continue
        platform_records = records_for_platform(platform, materials, deep_records)
        insights = build_insights(platform, platform_records)
        strategy["platforms"][platform] = insights
        if not platform_records:
            item["competitorInformed"] = {"status": "skipped", "reason": "No competitor records for this platform.", "generatedAt": TODAY}
            continue
        apply_insights(platform, item, insights)
    return enhanced, strategy


def records_for_platform(platform: str, materials: list[dict[str, Any]], deep_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = [normalize_source_record(record, "viral_material") for record in materials if record.get("platform") == platform]
    records.extend(normalize_source_record(record, "deep_record") for record in deep_records if record.get("platform") == platform)
    if records:
        return sorted(records, key=lambda item: item.get("score", 0), reverse=True)
    fallback = [normalize_source_record(record, "viral_material") for record in materials[:3]]
    fallback.extend(normalize_source_record(record, "deep_record") for record in deep_records[:3])
    return sorted(fallback, key=lambda item: item.get("score", 0), reverse=True)[:3]


def normalize_source_record(record: dict[str, Any], source_type: str) -> dict[str, Any]:
    signals = record.get("viralSignals") if isinstance(record.get("viralSignals"), dict) else {}
    return {
        "sourceType": source_type,
        "platform": record.get("platform", "unknown"),
        "title": normalize_space(record.get("title", "")),
        "creatorName": normalize_space(record.get("creatorName", "")),
        "url": normalize_space(record.get("url", "")),
        "hook": normalize_space(record.get("hook", "")),
        "cta": normalize_space(record.get("cta", "")),
        "contentExcerpt": normalize_space(record.get("contentExcerpt", "")),
        "reusablePatterns": record.get("reusablePatterns") if isinstance(record.get("reusablePatterns"), list) else [],
        "contentStructure": record.get("contentStructure") if isinstance(record.get("contentStructure"), list) else [],
        "contentDeconstruction": record.get("contentDeconstruction") if isinstance(record.get("contentDeconstruction"), dict) else {},
        "videoSampleEvidence": record.get("videoSampleEvidence") if isinstance(record.get("videoSampleEvidence"), dict) else {},
        "visibleMetrics": record.get("visibleMetrics") if isinstance(record.get("visibleMetrics"), dict) else {},
        "score": numeric(signals.get("score"), 0.0),
    }


def build_insights(platform: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    hooks = unique_non_empty([record.get("hook") for record in records])
    titles = unique_non_empty([record.get("title") for record in records])
    ctas = unique_non_empty([record.get("cta") for record in records])
    deconstruction_summaries = unique_non_empty(
        [
            (record.get("contentDeconstruction") or {}).get("summary")
            for record in records
            if isinstance(record.get("contentDeconstruction"), dict)
        ]
    )
    patterns: dict[str, int] = {}
    structures: dict[str, int] = {}
    beat_functions: dict[str, int] = {}
    video_backed_records = 0
    video_sample_frames = 0
    for record in records:
        for pattern in record.get("reusablePatterns", []):
            patterns[str(pattern)] = patterns.get(str(pattern), 0) + 1
        for item in record.get("contentStructure", []):
            role = str(item.get("role", "")).strip()
            if role:
                structures[role] = structures.get(role, 0) + 1
        deconstruction = record.get("contentDeconstruction") if isinstance(record.get("contentDeconstruction"), dict) else {}
        beats = deconstruction.get("beats", [])
        if not isinstance(beats, list):
            beats = []
        for beat in beats:
            function = str(beat.get("function", "")).strip()
            if function:
                beat_functions[function] = beat_functions.get(function, 0) + 1
        video_sample = record.get("videoSampleEvidence") if isinstance(record.get("videoSampleEvidence"), dict) else {}
        if video_sample:
            video_backed_records += 1
            video_sample_frames += int(video_sample.get("frameCount") or 0)
    return {
        "platform": platform,
        "recordCount": len(records),
        "sourceTitles": titles[:5],
        "sourceHooks": hooks[:5],
        "sourceCtas": ctas[:5],
        "deconstructionSummaries": deconstruction_summaries[:5],
        "dominantPatterns": [name for name, _ in sorted(patterns.items(), key=lambda item: item[1], reverse=True)[:5]],
        "structureRoles": [name for name, _ in sorted(structures.items(), key=lambda item: item[1], reverse=True)[:5]],
        "beatFunctions": [name for name, _ in sorted(beat_functions.items(), key=lambda item: item[1], reverse=True)[:5]],
        "metricBackedRecords": sum(1 for record in records if record.get("visibleMetrics")),
        "videoBackedRecords": video_backed_records,
        "videoSampleFrames": video_sample_frames,
        "safePatternSummary": summarize_patterns(patterns, hooks, titles),
        "sourceRecords": [
            {
                "sourceType": record["sourceType"],
                "platform": record["platform"],
                "title": record["title"],
                "url": record["url"],
                "score": record["score"],
                "videoSampleFrames": (record.get("videoSampleEvidence") or {}).get("frameCount", 0),
            }
            for record in records[:5]
        ],
    }


def apply_insights(platform: str, item: dict[str, Any], insights: dict[str, Any]) -> None:
    original_title = str(item.get("title") or "")
    source_hook = first_non_empty(*(insights.get("sourceHooks") or []), original_title)
    source_title = first_non_empty(*(insights.get("sourceTitles") or []), original_title)
    pattern_summary = insights.get("safePatternSummary") or "hook -> problem -> proof -> CTA"
    product = item.get("sourceProduct") if isinstance(item.get("sourceProduct"), dict) else {}
    product_name = product.get("name") or original_title or "this product"
    product_url = product.get("url") or ""
    cta = item.get("cta") or (f"Open {product_url}" if product_url else "Try the product")

    item["title"] = enhanced_title(platform, product_name, source_title, original_title)
    item["description"] = enhanced_description(product_name, item.get("description", ""), pattern_summary, source_hook)
    if platform in {"youtube", "douyin", "tiktok"}:
        item["shortVideoScript"] = enhanced_video_script(product_name, source_hook, pattern_summary, cta)
        item["voiceover"] = enhanced_voiceover(product_name, source_hook, cta)
        item["storyboard"] = enhanced_storyboard(product_name, source_hook, pattern_summary, cta)
    if platform == "zhihu":
        item["article"] = enhanced_article(product_name, source_hook, pattern_summary, cta)
    if platform == "xiaohongshu":
        item["description"] = enhanced_xhs_note(product_name, source_hook, pattern_summary, cta)
    update_formats(platform, item, product_name, source_hook, pattern_summary, cta)
    item["competitorInformed"] = {
        "status": "ready",
        "generatedAt": TODAY,
        "sourceTitles": insights.get("sourceTitles", [])[:5],
        "sourceHooks": insights.get("sourceHooks", [])[:5],
        "deconstructionSummaries": insights.get("deconstructionSummaries", [])[:5],
        "structureRoles": insights.get("structureRoles", [])[:5],
        "beatFunctions": insights.get("beatFunctions", [])[:5],
        "dominantPatterns": insights.get("dominantPatterns", []),
        "metricBackedRecords": insights.get("metricBackedRecords", 0),
        "videoBackedRecords": insights.get("videoBackedRecords", 0),
        "videoSampleFrames": insights.get("videoSampleFrames", 0),
        "safeUseRule": "Use observed structures and patterns, not copied competitor wording or fabricated metrics.",
    }


def enhanced_title(platform: str, product_name: str, source_title: str, original_title: str) -> str:
    if platform == "youtube":
        return f"I tested the viral launch pattern behind '{trim(source_title, 54)}' with {product_name}"
    if platform == "zhihu":
        return f"After deconstructing viral promotion content, use {product_name} to build a publishable launch plan"
    if platform == "xiaohongshu":
        return f"Viral note structure teardown for {product_name}"
    if platform in {"douyin", "tiktok"}:
        return f"Viral short video structure for {product_name} in 4 steps"
    if platform == "github":
        return f"{product_name}: viral launch patterns turned into reusable repo copy"
    return original_title


def enhanced_description(product_name: str, original: str, pattern_summary: str, source_hook: str) -> str:
    return (
        f"{original}\n\n"
        f"Competitor-informed angle: reuse the observed structure `{pattern_summary}`. "
        f"Opening hook to test: {trim(source_hook, 160)}. "
        f"Keep claims factual for {product_name}; do not copy competitor wording or metrics."
    ).strip()


def enhanced_video_script(product_name: str, source_hook: str, pattern_summary: str, cta: str) -> str:
    return (
        f"Hook: {trim(source_hook, 120)}\n"
        f"Problem: Most product promotion fails because the message starts from features, not audience pain.\n"
        f"Pattern: Use the observed structure {pattern_summary}.\n"
        f"Demo: Put {product_name} into that structure and generate titles, copy, voiceover, and a publish pack.\n"
        f"CTA: {cta}"
    )


def enhanced_voiceover(product_name: str, source_hook: str, cta: str) -> str:
    return (
        f"{trim(source_hook, 100)} "
        f"Observed viral pattern: start with the pain, show the method, then give one clear action. "
        f"Apply that structure to {product_name}: identify the audience, name the pain, generate platform-native copy and a short video script. "
        f"{cta}"
    )


def enhanced_storyboard(product_name: str, source_hook: str, pattern_summary: str, cta: str) -> list[dict[str, str]]:
    return [
        {"time": "0-3s", "visual": "show the strongest observed hook", "voiceover": trim(source_hook, 80)},
        {"time": "3-10s", "visual": "show pattern labels", "voiceover": f"Break it into this structure: {pattern_summary}."},
        {
            "time": "10-22s",
            "visual": "show product URL turning into platform drafts",
            "voiceover": f"Put {product_name} into the structure and generate titles, voiceover, and a publish pack.",
        },
        {"time": "22-30s", "visual": "show CTA and publish checklist", "voiceover": str(cta)},
    ]


def enhanced_article(product_name: str, source_hook: str, pattern_summary: str, cta: str) -> str:
    return (
        f"# How to turn viral structure into product promotion for {product_name}\n\n"
        f"Observed opening hook: {trim(source_hook, 160)}\n\n"
        f"The reusable asset is the sequence, not the competitor's wording: {pattern_summary}.\n\n"
        f"For {product_name}, write in four steps: target user, real pain, how the product helps, and the next action.\n\n"
        f"CTA: {cta}"
    )


def enhanced_xhs_note(product_name: str, source_hook: str, pattern_summary: str, cta: str) -> str:
    return (
        f"{trim(source_hook, 120)}\n\n"
        f"Observed viral pattern: {pattern_summary}.\n\n"
        f"For {product_name}, start with the user pain, show the solution path, then leave one action.\n\n"
        f"{cta}\n\n"
        "Note: reuse the structure only. Do not copy competitor wording or invent views, likes, orders, or revenue."
    )


def update_formats(platform: str, item: dict[str, Any], product_name: str, source_hook: str, pattern_summary: str, cta: str) -> None:
    formats = item.get("formats")
    if not isinstance(formats, dict):
        formats = {}
        item["formats"] = formats
    if platform == "youtube":
        formats["longVideoTitles"] = prepend_unique(
            formats.get("longVideoTitles", []),
            [
                f"1. I rebuilt a viral launch structure for {product_name}",
                f"2. The {pattern_summary} content system for product launches",
            ],
            10,
        )
        formats["shortsTitles"] = prepend_unique(
            formats.get("shortsTitles", []),
            [f"1. Viral hook teardown: {trim(source_hook, 55)}", f"2. One product URL, one viral structure"],
            10,
        )
        formats["videoScripts"] = prepend_unique(formats.get("videoScripts", []), [item["shortVideoScript"]], 5)
    elif platform in {"douyin", "tiktok"}:
        formats["voiceoverTitles"] = prepend_unique(
            formats.get("voiceoverTitles", []),
            [f"1. Viral structure teardown: {product_name}", f"2. {trim(source_hook, 40)}"],
            20,
        )
        formats["thirtySecondScripts"] = prepend_unique(formats.get("thirtySecondScripts", []), [item["shortVideoScript"]], 5)
    elif platform == "xiaohongshu":
        formats["noteTitles"] = prepend_unique(
            formats.get("noteTitles", []),
            [f"1. Viral note structure: {product_name}", f"2. {trim(source_hook, 40)}"],
            20,
        )
        formats["notes"] = prepend_unique(formats.get("notes", []), [item["description"]], 5)
    elif platform == "zhihu":
        formats["articleTitles"] = prepend_unique(formats.get("articleTitles", []), [item["title"]], 10)
        formats["articleOutlines"] = prepend_unique(formats.get("articleOutlines", []), [f"{pattern_summary} -> product application -> risk boundary -> CTA"], 5)
    elif platform == "github":
        formats["readmePromotion"] = (
            f"## {product_name}\n\n"
            f"Competitor-informed launch angle: `{pattern_summary}`.\n\n"
            f"Hook to adapt: {trim(source_hook, 160)}\n\n"
            f"CTA: {cta}\n"
        )


def write_reports(out_dir: Path, content_path: Path, enhanced: dict[str, Any], strategy: dict[str, Any]) -> dict[str, str]:
    directory = out_dir / GENERATED_DIR
    directory.mkdir(parents=True, exist_ok=True)
    slug = content_path.stem.replace("-platform-content", "") or "product"
    json_path = directory / f"{slug}-competitor-informed-content.json"
    md_path = directory / f"{slug}-competitor-informed-content.md"
    strategy_path = directory / f"{slug}-competitor-informed-strategy.json"
    json_path.write_text(json.dumps(enhanced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(enhanced, strategy) + "\n", encoding="utf-8")
    strategy_path.write_text(json.dumps(strategy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "strategy": str(strategy_path)}


def update_publish_pack(path: Path, enhanced: dict[str, Any]) -> None:
    if not path.exists():
        return
    try:
        pack = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return
    if not isinstance(pack, list):
        return
    backup_path = path.with_suffix(".base.json")
    if not backup_path.exists():
        shutil.copyfile(path, backup_path)
    for item in pack:
        if not isinstance(item, dict):
            continue
        platform = item.get("platform")
        if platform in enhanced:
            item["content"] = enhanced[platform]
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(enhanced: dict[str, Any], strategy: dict[str, Any]) -> str:
    lines = [
        "# Competitor-Informed Content",
        "",
        f"- Generated: {strategy['generatedAt']}",
        f"- Status: `{strategy['status']}`",
        f"- Viral materials: {strategy['sourceCounts']['viralMaterials']}",
        f"- Deep records: {strategy['sourceCounts']['deepRecords']}",
        "",
        "## Platforms",
    ]
    for platform, item in enhanced.items():
        if not isinstance(item, dict):
            continue
        info = item.get("competitorInformed", {})
        lines.extend(
            [
                "",
                f"### {platform}",
                f"- Status: `{info.get('status', 'unknown')}`",
                f"- Title: {item.get('title', '')}",
                f"- Source hooks: {len(info.get('sourceHooks', [])) if isinstance(info.get('sourceHooks'), list) else 0}",
                f"- Dominant patterns: {', '.join(info.get('dominantPatterns', [])) if isinstance(info.get('dominantPatterns'), list) else ''}",
                f"- Video sample frames: {info.get('videoSampleFrames', 0)}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in strategy["guardrails"])
    return "\n".join(lines)


def summarize_patterns(patterns: dict[str, int], hooks: list[str], titles: list[str]) -> str:
    names = [name for name, _ in sorted(patterns.items(), key=lambda item: item[1], reverse=True)]
    if names:
        labels = []
        if "question_hook" in names:
            labels.append("question hook")
        if "numbered_title_or_claim" in names:
            labels.append("numbered claim")
        if "visible_social_proof" in names:
            labels.append("visible proof")
        if "explicit_call_to_action" in names:
            labels.append("explicit CTA")
        if labels:
            return " -> ".join(labels)
    if hooks or titles:
        return "strong hook -> concrete problem -> practical method -> CTA"
    return "hook -> problem -> solution -> CTA"


def prepend_unique(existing: Any, additions: list[str], limit: int) -> list[str]:
    values = [str(item) for item in additions if str(item).strip()]
    if isinstance(existing, list):
        values.extend(str(item) for item in existing if str(item).strip())
    seen = set()
    result = []
    for value in values:
        key = normalize_space(value).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def unique_non_empty(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = normalize_space(value or "")
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        result.append(text)
    return result


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = normalize_space(value or "")
        if text:
            return text
    return ""


def trim(value: str, limit: int) -> str:
    value = normalize_space(value)
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def numeric(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def guardrails() -> list[str]:
    return [
        "Reuse competitor structures and patterns only; do not copy competitor wording.",
        "Use visible/public metrics only as evidence metadata; do not invent or transfer competitor metrics to the product.",
        "Keep product claims factual and tied to the product page or user-provided evidence.",
        "Preserve platform publish safety boundaries and human approval gates.",
    ]


if __name__ == "__main__":
    main()
