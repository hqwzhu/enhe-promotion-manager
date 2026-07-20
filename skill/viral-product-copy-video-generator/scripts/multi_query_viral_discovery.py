#!/usr/bin/env python3
"""Run and merge multi-query viral discovery for a product."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

from env_loader import load_project_env, preparse_env_file


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
COMPETITOR_DIR = Path("reports/promotion-manager/competitors")
DEFAULT_PLATFORMS = "youtube,zhihu,xiaohongshu,douyin,github"
NON_CONTENT_PATH_PARTS = {
    "about",
    "aboutus",
    "agreement",
    "agreements",
    "contact",
    "help",
    "privacy",
    "recovery_account",
    "terms",
}
NON_CONTENT_TITLE_TERMS = {
    "about us",
    "contact us",
    "privacy policy",
    "terms of service",
    "user agreement",
    "用户协议",
    "隐私政策",
    "关于我们",
    "联系我们",
    "账号找回",
}


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    product = load_product(args)
    query_plan = build_query_plan(args, product)
    runs = run_or_plan_discovery(args, out_dir, query_plan)
    materials = merge_materials(runs, args.top_n)
    creators = build_creator_leaderboard(materials, args.top_n)
    report = build_report(args, out_dir, product, query_plan, runs, materials, creators, env_load)
    write_outputs(out_dir, report, materials, creators)
    print(f"Multi-query viral discovery written to: {(report_dir(out_dir) / 'multi-query-viral-discovery.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate multiple product promotion search queries, run viral discovery, and merge results.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--product-profile", help="product-profile.json from product_intake.py.")
    source.add_argument("--workflow-manifest", help="workflow-manifest.json from run_promotion_workflow.py.")
    parser.add_argument("--product-name", default="")
    parser.add_argument("--product-url", default="")
    parser.add_argument("--value-proposition", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--pain-points", default="")
    parser.add_argument("--keywords", default="")
    parser.add_argument("--query", action="append", default=[], help="Seed query. Can be repeated.")
    parser.add_argument("--query-count", type=int, default=5)
    parser.add_argument("--platforms", default=DEFAULT_PLATFORMS)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before running discovery. Values are never written to reports.")
    parser.add_argument("--dry-run", action="store_true", help="Write query plan and commands without running platform search.")
    parser.add_argument("--existing-run-dir", action="append", default=[], help="Existing viral_discovery_runner output directory to merge. Can be repeated.")
    parser.add_argument("--html-snapshot-root", default="", help="Optional root containing saved search HTML fixtures. Uses <root>/<query-slug> when present, otherwise <root>.")
    parser.add_argument("--browser-search-timeout-ms", type=int, default=30000)
    parser.add_argument("--browser-search-wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--install-browser-if-missing", action="store_true")
    parser.add_argument("--live-official", action="store_true")
    parser.add_argument("--run-creator-follow-up", action="store_true")
    parser.add_argument("--creator-follow-up-dry-run", action="store_true")
    parser.add_argument("--run-follow-up-captures", action="store_true")
    parser.add_argument("--follow-up-dry-run", action="store_true")
    parser.add_argument("--capture-browser-assisted-follow-ups", action="store_true")
    parser.add_argument("--sample-video-frames", action="store_true", help="Pass video sampling to viral_discovery_runner follow-up captures.")
    parser.add_argument("--video-sample-count", type=int, default=5)
    return parser.parse_args()


def load_product(args: argparse.Namespace) -> dict[str, Any]:
    if args.workflow_manifest:
        path = Path(args.workflow_manifest)
        manifest = read_json(path)
        product = manifest.get("product") if isinstance(manifest, dict) else {}
        if isinstance(product, dict):
            return normalize_product(product, str(path))
    if args.product_profile:
        path = Path(args.product_profile)
        profile = read_json(path)
        return normalize_product(
            {
                "name": profile.get("productName") or profile.get("title"),
                "url": profile.get("canonicalUrl") or profile.get("source"),
                "valueProposition": profile.get("valueProposition") or profile.get("description"),
                "audience": profile.get("targetAudienceAssumptions"),
                "painPoints": profile.get("painPointAssumptions"),
                "keywords": profile.get("keywords"),
            },
            str(path),
        )
    return normalize_product(
        {
            "name": args.product_name,
            "url": args.product_url,
            "valueProposition": args.value_proposition,
            "audience": split_any(args.audience),
            "painPoints": split_any(args.pain_points),
            "keywords": split_any(args.keywords),
        },
        "cli",
    )


def normalize_product(raw: dict[str, Any], source: str) -> dict[str, Any]:
    name = first_non_empty(raw.get("name"), raw.get("productName"), "Unknown product")
    value = first_non_empty(raw.get("valueProposition"), raw.get("description"))
    return {
        "source": source,
        "name": name,
        "url": first_non_empty(raw.get("url"), raw.get("canonicalUrl")),
        "valueProposition": value,
        "audience": list_from_any(raw.get("audience") or raw.get("targetAudience") or raw.get("targetAudienceAssumptions")),
        "painPoints": list_from_any(raw.get("painPoints") or raw.get("painPointAssumptions")),
        "keywords": list_from_any(raw.get("keywords")),
    }


def build_query_plan(args: argparse.Namespace, product: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[str] = []
    candidates.extend(args.query)
    candidates.append(product["name"])
    if product.get("valueProposition"):
        candidates.append(product["valueProposition"])
    for keyword in product.get("keywords", [])[:8]:
        candidates.extend([keyword, f"{keyword} 工具", f"{keyword} 教程", f"{keyword} 测评"])
    for pain in product.get("painPoints", [])[:4]:
        candidates.extend([pain, f"{pain} 解决方案", f"{pain} 案例"])
    for audience in product.get("audience", [])[:3]:
        candidates.append(f"{audience} 工具")
    candidates.extend(
        [
            f"{product['name']} alternatives",
            f"{product['name']} tutorial",
            f"{product['name']} launch",
        ]
    )

    deduped = []
    seen = set()
    for candidate in candidates:
        query = clean_query(candidate)
        key = query.lower()
        if len(query) < 2 or key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    planned = deduped[: max(args.query_count, 0)]
    platforms = split_csv(args.platforms)
    plan = []
    used_slugs: set[str] = set()
    for index, query in enumerate(planned, start=1):
        base_slug = safe_slug(query)[:80] or f"query-{index:03d}"
        plan.append(
            {
                "id": f"query-{index:03d}",
                "query": query,
                "slug": dedupe_slug(base_slug, used_slugs),
                "platforms": platforms,
                "intent": infer_intent(query, product),
            }
        )
    return plan


def run_or_plan_discovery(args: argparse.Namespace, out_dir: Path, query_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs = []
    for value in args.existing_run_dir:
        run_dir = Path(value)
        runs.append(run_record_from_existing(run_dir))
    for query in query_plan:
        run_dir = out_dir / "reports/promotion-manager/competitors/multi-query-runs" / query["slug"]
        command = build_discovery_command(args, query, run_dir)
        if args.dry_run:
            runs.append(
                {
                    "queryId": query["id"],
                    "query": query["query"],
                    "status": "planned",
                    "outDir": str(run_dir),
                    "command": display_command(command),
                    "viralLibrary": str(viral_library_path(run_dir)),
                    "creatorLeaderboard": str(creator_leaderboard_path(run_dir)),
                }
            )
            continue
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        run_report_path = viral_discovery_run_path(run_dir)
        run_report = read_json(run_report_path)
        runs.append(
            {
                "queryId": query["id"],
                "query": query["query"],
                "status": "ready" if result.returncode == 0 and viral_library_path(run_dir).exists() else "error",
                "outDir": str(run_dir),
                "command": display_command(command),
                "exitCode": result.returncode,
                "stdoutTail": tail(result.stdout),
                "stderrTail": tail(result.stderr),
                "viralLibrary": str(viral_library_path(run_dir)),
                "creatorLeaderboard": str(creator_leaderboard_path(run_dir)),
                "viralDiscoveryRun": str(run_report_path) if run_report_path.exists() else "",
                "coverage": run_report.get("coverage", {}) if isinstance(run_report.get("coverage"), dict) else {},
            }
        )
    return runs


def build_discovery_command(args: argparse.Namespace, query: dict[str, Any], run_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPTS / "viral_discovery_runner.py"),
        "--query",
        query["query"],
        "--platforms",
        ",".join(query["platforms"]),
        "--top-n",
        str(args.top_n),
        "--out-dir",
        str(run_dir),
        "--browser-search-timeout-ms",
        str(args.browser_search_timeout_ms),
        "--browser-search-wait-until",
        args.browser_search_wait_until,
    ]
    html_dir = html_snapshot_dir_for(args.html_snapshot_root, query["slug"])
    if html_dir:
        command.extend(["--html-snapshot-dir", str(html_dir)])
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    if args.live_official:
        command.append("--live-official")
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
    return command


def run_record_from_existing(run_dir: Path) -> dict[str, Any]:
    library = viral_library_path(run_dir)
    if not library.exists() and (run_dir / "viral-content-library.json").exists():
        library = run_dir / "viral-content-library.json"
    leaderboard = creator_leaderboard_path(run_dir)
    if not leaderboard.exists() and (run_dir / "creator-leaderboard.json").exists():
        leaderboard = run_dir / "creator-leaderboard.json"
    query = ""
    if library.exists():
        payload = read_json(library)
        materials = payload.get("materials", [])
        if materials and isinstance(materials[0], dict):
            query = first_non_empty(materials[0].get("query"), "")
    run_report_path = viral_discovery_run_path(run_dir)
    run_report = read_json(run_report_path)
    return {
        "queryId": "existing",
        "query": query,
        "status": "ready" if library.exists() else "missing_library",
        "outDir": str(run_dir),
        "command": [],
        "viralLibrary": str(library),
        "creatorLeaderboard": str(leaderboard),
        "viralDiscoveryRun": str(run_report_path) if run_report_path.exists() else "",
        "coverage": run_report.get("coverage", {}) if isinstance(run_report.get("coverage"), dict) else {},
    }


def merge_materials(runs: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for run in runs:
        path = Path(str(run.get("viralLibrary") or ""))
        if not path.exists():
            continue
        payload = read_json(path)
        for material in payload.get("materials", []):
            if not isinstance(material, dict):
                continue
            item = dict(material)
            if not is_mergeable_material(item):
                continue
            item["sourceRun"] = run.get("outDir", "")
            item["sourceQuery"] = first_non_empty(run.get("query"), item.get("query"))
            key = material_key(item)
            current = merged.get(key)
            if current is None or material_score(item) > material_score(current):
                existing_queries = current.get("sourceQueries", []) if current else []
                item["sourceQueries"] = unique([*existing_queries, item["sourceQuery"]])
                merged[key] = item
            else:
                current["sourceQueries"] = unique([*current.get("sourceQueries", []), item.get("sourceQuery", "")])
    materials = list(merged.values())
    materials.sort(key=lambda item: (material_score(item), has_metrics(item), -int(item.get("libraryRank") or 9999)), reverse=True)
    limited = materials[: max(top_n, 0)]
    for index, material in enumerate(limited, start=1):
        material["id"] = f"multi-query-viral-material-{index:03d}"
        material["libraryRank"] = index
    return limited


def build_creator_leaderboard(materials: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for material in materials:
        platform = clean_text(material.get("platform") or "unknown")
        creator = clean_text(material.get("creatorName") or "") or inferred_creator(material)
        key = f"{platform}:{creator.lower()}"
        record = grouped.setdefault(
            key,
            {
                "id": "",
                "rank": 0,
                "creatorName": creator,
                "platform": platform,
                "materialCount": 0,
                "metricBackedMaterials": 0,
                "totalViralScore": 0.0,
                "sourceQueries": [],
                "topMaterials": [],
            },
        )
        score = material_score(material)
        record["materialCount"] += 1
        record["totalViralScore"] += score
        if has_metrics(material):
            record["metricBackedMaterials"] += 1
        record["sourceQueries"] = unique([*record["sourceQueries"], *(material.get("sourceQueries") or [material.get("sourceQuery", "")])])
        record["topMaterials"].append(
            {
                "materialId": material.get("id", ""),
                "title": material.get("title", ""),
                "url": material.get("url", ""),
                "viralScore": score,
                "sourceQueries": material.get("sourceQueries", []),
            }
        )
    creators = list(grouped.values())
    for creator in creators:
        creator["topMaterials"].sort(key=lambda item: item["viralScore"], reverse=True)
        creator["topMaterials"] = creator["topMaterials"][:5]
    creators.sort(key=lambda item: (item["totalViralScore"], item["metricBackedMaterials"], item["materialCount"]), reverse=True)
    limited = creators[: max(top_n, 0)]
    for index, creator in enumerate(limited, start=1):
        creator["id"] = f"multi-query-creator-{index:03d}"
        creator["rank"] = index
    return limited


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    product: dict[str, Any],
    query_plan: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    materials: list[dict[str, Any]],
    creators: list[dict[str, Any]],
    env_load: dict[str, object],
) -> dict[str, Any]:
    coverage = aggregate_run_coverage(runs)
    return {
        "generatedAt": TODAY,
        "status": run_status(runs, materials, args.dry_run),
        "product": product,
        "queryPlan": query_plan,
        "runs": runs,
        "envLoad": env_load,
        "summary": {
            "queries": len(query_plan),
            "runs": len(runs),
            "readyRuns": sum(1 for run in runs if run.get("status") == "ready"),
            "plannedRuns": sum(1 for run in runs if run.get("status") == "planned"),
            "mergedMaterials": len(materials),
            "mergedCreators": len(creators),
            "platforms": sorted({material.get("platform", "unknown") for material in materials}),
            **coverage,
        },
        "artifacts": {
            "mergedViralLibrary": str(report_dir(out_dir) / "multi-query-viral-content-library.json"),
            "mergedCreatorLeaderboard": str(report_dir(out_dir) / "multi-query-creator-leaderboard.json"),
        },
        "guardrails": guardrails(),
    }


def run_status(runs: list[dict[str, Any]], materials: list[dict[str, Any]], dry_run: bool) -> str:
    if materials:
        return "ready"
    if dry_run:
        return "planned"
    if any(run.get("status") == "ready" for run in runs):
        return "partial_ready_no_mergeable_materials"
    return "blocked"


def aggregate_run_coverage(runs: list[dict[str, Any]]) -> dict[str, int]:
    coverage_records = [run.get("coverage", {}) for run in runs if isinstance(run.get("coverage"), dict)]
    return {
        "searchCapturesReady": sum_coverage(coverage_records, "searchCapturesReady"),
        "viralMaterialsObserved": sum_coverage(coverage_records, "viralMaterials"),
        "creatorsObserved": sum_coverage(coverage_records, "creators"),
        "fullyCapturedRuns": sum(1 for item in coverage_records if item.get("fullyCapturedAcrossRequestedPlatforms")),
        "followUpCaptureRuns": sum_coverage(coverage_records, "followUpCaptureRuns"),
        "followUpImportedRecords": sum_coverage(coverage_records, "followUpImportedRecords"),
        "followUpPublicCaptureReady": sum_coverage(coverage_records, "followUpPublicCaptureReady"),
        "followUpBrowserVisibleAttempts": sum_coverage(coverage_records, "followUpBrowserVisibleAttempts"),
        "followUpBrowserVisibleReady": sum_coverage(coverage_records, "followUpBrowserVisibleReady"),
        "followUpManualEvidenceQueued": sum_coverage(coverage_records, "followUpManualEvidenceQueued"),
        "videoSampleRuns": sum_coverage(coverage_records, "videoSampleRuns"),
        "videoSampleReady": sum_coverage(coverage_records, "videoSampleReady"),
        "videoSampleFrames": sum_coverage(coverage_records, "videoSampleFrames"),
        "deepEvidenceRuns": sum(
            1
            for item in coverage_records
            if int_value(item.get("followUpImportedRecords"))
            or int_value(item.get("followUpBrowserVisibleReady"))
            or int_value(item.get("videoSampleFrames"))
        ),
    }


def sum_coverage(records: list[dict[str, Any]], key: str) -> int:
    return sum(int_value(item.get(key)) for item in records)


def write_outputs(out_dir: Path, report: dict[str, Any], materials: list[dict[str, Any]], creators: list[dict[str, Any]]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    merged_library = {
        "generatedAt": TODAY,
        "recordCount": len(materials),
        "materials": materials,
        "aggregatePatterns": aggregate_materials(materials),
        "guardrails": guardrails(),
    }
    creator_leaderboard = {
        "generatedAt": TODAY,
        "creatorCount": len(creators),
        "creators": creators,
        "summary": aggregate_creators(creators),
        "guardrails": guardrails(),
    }
    (directory / "multi-query-viral-discovery.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "multi-query-viral-discovery.md").write_text(render_report_markdown(report) + "\n", encoding="utf-8")
    (directory / "multi-query-viral-content-library.json").write_text(json.dumps(merged_library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "multi-query-viral-content-library.md").write_text(render_materials_markdown(merged_library) + "\n", encoding="utf-8")
    (directory / "multi-query-creator-leaderboard.json").write_text(json.dumps(creator_leaderboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "multi-query-creator-leaderboard.md").write_text(render_creators_markdown(creator_leaderboard) + "\n", encoding="utf-8")


def viral_library_path(run_dir: Path) -> Path:
    return run_dir / COMPETITOR_DIR / "viral-content-library.json"


def creator_leaderboard_path(run_dir: Path) -> Path:
    return run_dir / COMPETITOR_DIR / "creator-leaderboard.json"


def viral_discovery_run_path(run_dir: Path) -> Path:
    return run_dir / COMPETITOR_DIR / "viral-discovery-run.json"


def html_snapshot_dir_for(root: str, slug: str) -> Path | None:
    if not root:
        return None
    base = Path(root)
    nested = base / slug
    if nested.exists():
        return nested
    return base if base.exists() else None


def material_key(material: dict[str, Any]) -> str:
    platform = clean_text(material.get("platform") or "unknown").lower()
    url = clean_text(material.get("url") or "").lower().rstrip("/")
    if url:
        return f"{platform}:url:{url}"
    return f"{platform}:title:{clean_text(material.get('title')).lower()}:{clean_text(material.get('creatorName')).lower()}"


def material_score(material: dict[str, Any]) -> float:
    signals = material.get("viralSignals") if isinstance(material.get("viralSignals"), dict) else {}
    try:
        return float(signals.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def has_metrics(material: dict[str, Any]) -> int:
    metrics = material.get("visibleMetrics") if isinstance(material.get("visibleMetrics"), dict) else {}
    return 1 if metrics else 0


def inferred_creator(material: dict[str, Any]) -> str:
    url = clean_text(material.get("url") or "")
    if url:
        return f"unknown creator on {url_host(url)}"
    return f"unknown creator on {clean_text(material.get('platform') or 'unknown')}"


def url_host(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc.lower() or "unknown"


def is_mergeable_material(material: dict[str, Any]) -> bool:
    title = clean_text(material.get("title") or "")
    url = clean_text(material.get("url") or "")
    parsed = urllib.parse.urlparse(url)
    path_parts = {part.lower() for part in parsed.path.split("/") if part}
    lowered_title = title.lower()
    if path_parts & NON_CONTENT_PATH_PARTS:
        return False
    if any(term in lowered_title for term in NON_CONTENT_TITLE_TERMS):
        return False
    return bool(title or url)


def aggregate_materials(materials: list[dict[str, Any]]) -> dict[str, Any]:
    patterns: dict[str, int] = {}
    for material in materials:
        for pattern in material.get("reusablePatterns", []) if isinstance(material.get("reusablePatterns"), list) else []:
            patterns[str(pattern)] = patterns.get(str(pattern), 0) + 1
    return {
        "recordsWithObservedMetrics": sum(has_metrics(material) for material in materials),
        "topTitles": [material.get("title", "") for material in materials[:5]],
        "sourceQueries": sorted({query for material in materials for query in material.get("sourceQueries", []) if query}),
        "patternCounts": dict(sorted(patterns.items())),
    }


def aggregate_creators(creators: list[dict[str, Any]]) -> dict[str, Any]:
    platforms: dict[str, int] = {}
    for creator in creators:
        platform = creator.get("platform", "unknown")
        platforms[platform] = platforms.get(platform, 0) + 1
    return {"platforms": dict(sorted(platforms.items()))}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in str(value).split(",") if item.strip()]


def split_any(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]
    return [item.strip() for item in re.split(r"[,;\n]+", str(value or "")) if item.strip()]


def list_from_any(value: Any) -> list[str]:
    return split_any(value)


def clean_query(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"https?://\S+", "", text).strip()
    return text[:120]


def infer_intent(query: str, product: dict[str, Any]) -> str:
    lower = query.lower()
    if any(term in lower for term in ["教程", "tutorial", "how to"]):
        return "tutorial_or_how_to"
    if any(term in lower for term in ["测评", "review", "alternative"]):
        return "review_or_alternative"
    if query == product.get("name"):
        return "brand_or_product_name"
    if any(query == keyword for keyword in product.get("keywords", [])):
        return "category_keyword"
    return "problem_or_value_search"


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def safe_slug(value: str) -> str:
    ascii_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-")
    if ascii_slug:
        return ascii_slug
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"query-{digest}"


def dedupe_slug(base: str, used: set[str]) -> str:
    slug = base or "query"
    index = 2
    while slug in used:
        suffix = f"-{index:02d}"
        slug = f"{base[: max(1, 80 - len(suffix))]}{suffix}"
        index += 1
    used.add(slug)
    return slug


def unique(values: list[Any]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = clean_text(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = (value or "").strip()
    return value if len(value) <= limit else value[-limit:]


def report_dir(out_dir: Path) -> Path:
    return out_dir / COMPETITOR_DIR


def guardrails() -> list[str]:
    return [
        "Use official APIs, public pages, browser-visible snapshots, or user exports only.",
        "Do not bypass captcha, login prompts, rate limits, or platform risk controls.",
        "Do not store cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
        "Do not fabricate views, likes, comments, orders, revenue, creator income, or published URLs.",
    ]


def render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-Query Viral Discovery",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Product: {report['product']['name']}",
        f"- Queries: {report['summary']['queries']}",
        f"- Ready runs: {report['summary']['readyRuns']}",
        f"- Merged materials: {report['summary']['mergedMaterials']}",
        f"- Merged creators: {report['summary']['mergedCreators']}",
        f"- Deep evidence runs: {report['summary'].get('deepEvidenceRuns', 0)}",
        f"- Video sample frames: {report['summary'].get('videoSampleFrames', 0)}",
        "",
        "## Query Plan",
    ]
    for query in report["queryPlan"]:
        lines.append(f"- `{query['id']}` {query['query']} ({query['intent']})")
    lines.extend(["", "## Runs"])
    for run in report["runs"]:
        lines.append(f"- `{run.get('status')}` {run.get('query') or run.get('outDir')}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_materials_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-Query Viral Content Library",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Records: {report['recordCount']}",
        "",
        "## Materials",
    ]
    for material in report["materials"]:
        lines.extend(
            [
                "",
                f"### {material['libraryRank']}. {material.get('title', '')}",
                f"- Platform: {material.get('platform', '')}",
                f"- Creator: {material.get('creatorName') or 'unknown'}",
                f"- Score: {material_score(material)}",
                f"- Source queries: {', '.join(material.get('sourceQueries', []))}",
                f"- URL: {material.get('url') or 'unknown'}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_creators_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-Query Creator Leaderboard",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Creators: {report['creatorCount']}",
        "",
        "## Creators",
    ]
    for creator in report["creators"]:
        lines.extend(
            [
                "",
                f"### {creator['rank']}. {creator['creatorName']}",
                f"- Platform: {creator['platform']}",
                f"- Materials: {creator['materialCount']}",
                f"- Total viral score: {creator['totalViralScore']}",
                f"- Source queries: {', '.join(creator.get('sourceQueries', []))}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
