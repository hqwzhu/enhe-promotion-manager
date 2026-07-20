#!/usr/bin/env python3
"""Turn real retrospective evidence into next-round promotion actions."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    metrics_reports = load_many(args.metrics_recovery_json, default_metrics_recovery(out_dir))
    comment_reports = load_many(args.comment_evidence_json, default_comment_evidence(out_dir))
    business_reports = load_many(args.business_attribution_json, default_business_attribution(out_dir))
    workflow = load_optional_json(args.workflow_manifest, default_workflow_manifest(out_dir))
    publish_queue = load_optional_json(args.publish_queue, default_publish_queue(out_dir))
    report = build_report(out_dir, metrics_reports, comment_reports, business_reports, workflow, publish_queue)
    write_report(out_dir, report)
    print(f"Next-round optimization written to: {(optimization_dir(out_dir) / 'next-round-optimization.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create evidence-backed next-round promotion recommendations.")
    parser.add_argument("--metrics-recovery-json", action="append", default=[], help="metrics-recovery.json report.")
    parser.add_argument("--comment-evidence-json", action="append", default=[], help="comment-evidence-capture/export JSON.")
    parser.add_argument("--business-attribution-json", action="append", default=[], help="business-attribution.json report.")
    parser.add_argument("--workflow-manifest", default="", help="workflow-manifest.json for product/platform context.")
    parser.add_argument("--publish-queue", default="", help="publish-queue.json for queued/manual platform context.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def build_report(
    out_dir: Path,
    metrics_reports: list[dict[str, Any]],
    comment_reports: list[dict[str, Any]],
    business_reports: list[dict[str, Any]],
    workflow: dict[str, Any],
    publish_queue: dict[str, Any],
) -> dict[str, Any]:
    metric_records = normalize_metric_records(metrics_reports)
    comments, demand_signals = normalize_comment_evidence(comment_reports)
    business_attributions = normalize_business_attributions(business_reports)
    manual_required = normalize_manual_requirements(metrics_reports)
    context = product_context(workflow)
    platforms = target_platforms(workflow, publish_queue, metric_records, comments, business_attributions)
    coverage = evidence_coverage(metric_records, comments, demand_signals, business_attributions, manual_required)
    winners = {
        "byViews": best_record(metric_records, "views"),
        "byRevenue": best_record(metric_records + business_attributions, "revenue"),
        "byOrders": best_record(metric_records + business_attributions, "orders"),
        "byEngagement": best_engagement_record(metric_records),
    }
    comment_demand = summarize_comment_demand(comments, demand_signals)
    status = optimization_status(coverage, manual_required)
    next_content = next_round_content(status, context, platforms, winners, comment_demand)
    platform_actions = platform_actions_for(status, platforms, winners, comment_demand, manual_required)
    recommended_commands = recommended_commands_for(out_dir, context, platforms)
    next_actions = next_actions_for(status, next_content, manual_required)
    return {
        "generatedAt": TODAY,
        "status": status,
        "outDir": str(out_dir),
        "product": context,
        "targetPlatforms": platforms,
        "evidenceCoverage": coverage,
        "winners": winners,
        "commentDemand": comment_demand,
        "businessSummary": business_summary(business_reports, business_attributions),
        "manualOrPendingRequirements": manual_required,
        "nextRoundContent": next_content,
        "platformActions": platform_actions,
        "recommendedCommands": recommended_commands,
        "nextActions": next_actions,
        "guardrails": guardrails(),
    }


def normalize_metric_records(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for report in reports:
        for record in report.get("records", []):
            if not isinstance(record, dict) or not record.get("metrics"):
                continue
            records.append(normalize_record(record, "metrics_recovery"))
    return dedupe_records(records)


def normalize_business_attributions(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for report in reports:
        for record in report.get("attributions", []):
            if isinstance(record, dict) and record.get("metrics"):
                records.append(normalize_record(record, "business_attribution"))
        for record in (report.get("export") or {}).get("records", []):
            if isinstance(record, dict):
                converted = business_export_to_record(record)
                if converted.get("metrics"):
                    records.append(normalize_record(converted, "business_attribution_export"))
    return dedupe_records(records)


def business_export_to_record(record: dict[str, Any]) -> dict[str, Any]:
    metrics = {}
    for key in ("orders", "revenue", "clicks", "leads"):
        value = record.get(key)
        if value not in (None, ""):
            number = numeric(value)
            metrics[key] = {"raw": str(value), "normalized": number if number is not None else value}
    return {
        "platform": record.get("platform", ""),
        "publishedUrl": record.get("publishedUrl", ""),
        "contentId": record.get("contentId", ""),
        "title": record.get("title", ""),
        "metrics": metrics,
        "evidence": split_evidence(record.get("evidence", "")),
    }


def normalize_record(record: dict[str, Any], source_type: str) -> dict[str, Any]:
    metrics = {}
    for name, value in (record.get("metrics") or {}).items():
        if not isinstance(value, dict):
            continue
        normalized = value.get("normalized")
        metrics[name] = {
            "raw": str(value.get("raw", normalized if normalized is not None else "")),
            "normalized": float(normalized) if isinstance(normalized, (int, float)) else numeric(value.get("raw")),
        }
    return {
        "id": record.get("id", ""),
        "platform": clean(record.get("platform")) or "unknown",
        "title": clean(record.get("title")) or clean(record.get("contentId")) or clean(record.get("publishedUrl")),
        "publishedUrl": clean(record.get("publishedUrl")),
        "contentId": clean(record.get("contentId")),
        "metrics": {key: value for key, value in metrics.items() if value.get("normalized") is not None},
        "evidence": list(record.get("evidence", [])),
        "sourceType": source_type,
    }


def normalize_comment_evidence(reports: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    comments: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    for report in reports:
        for comment in report.get("comments", []):
            if isinstance(comment, dict) and clean(comment.get("text")):
                comments.append(
                    {
                        "author": clean(comment.get("author")) or "unknown",
                        "text": clean(comment.get("text")),
                        "likes": int_value(comment.get("likes")),
                        "replies": int_value(comment.get("replies")),
                        "platform": clean(comment.get("platform")) or "unknown",
                        "publishedUrl": clean(comment.get("publishedUrl")),
                        "sourceEvidence": clean(comment.get("sourceEvidence")),
                    }
                )
        for signal in report.get("demandSignals", []):
            if isinstance(signal, dict) and clean(signal.get("type")):
                signals.append(
                    {
                        "type": clean(signal.get("type")),
                        "platform": clean(signal.get("platform")) or "unknown",
                        "excerpt": clean(signal.get("excerpt")),
                        "publishedUrl": clean(signal.get("publishedUrl")),
                    }
                )
    return dedupe_comments(comments), signals


def normalize_manual_requirements(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for report in reports:
        for item in report.get("manualExportRequired", []):
            if isinstance(item, dict):
                requirements.append(
                    {
                        "platform": clean(item.get("platform")) or "unknown",
                        "status": clean(item.get("status")),
                        "reason": clean(item.get("reason")),
                        "publishedUrl": clean(item.get("publishedUrl")),
                    }
                )
    return requirements


def evidence_coverage(
    metric_records: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    demand_signals: list[dict[str, Any]],
    business_attributions: list[dict[str, Any]],
    manual_required: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "metricRecords": len(metric_records),
        "recordsWithRevenue": sum(1 for record in metric_records + business_attributions if metric_value(record, "revenue") is not None),
        "recordsWithOrders": sum(1 for record in metric_records + business_attributions if metric_value(record, "orders") is not None),
        "commentCount": len(comments),
        "demandSignalCount": len(demand_signals),
        "businessAttributions": len(business_attributions),
        "manualOrPendingRequirements": len(manual_required),
    }


def optimization_status(coverage: dict[str, Any], manual_required: list[dict[str, Any]]) -> str:
    has_real_evidence = any(
        int(coverage.get(key) or 0) > 0
        for key in ("metricRecords", "commentCount", "businessAttributions")
    )
    if not has_real_evidence:
        return "waiting_real_data"
    if manual_required:
        return "partial_ready"
    return "ready"


def best_record(records: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    candidates = [record for record in records if metric_value(record, metric) is not None]
    if not candidates:
        return None
    record = max(candidates, key=lambda item: metric_value(item, metric) or 0.0)
    return public_record_summary(record, metric)


def best_engagement_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = []
    for record in records:
        views = metric_value(record, "views")
        if not views:
            continue
        engagement = sum(metric_value(record, name) or 0.0 for name in ("likes", "comments", "favorites", "shares")) / views
        item = dict(record)
        item["metrics"] = {**record.get("metrics", {}), "engagementRate": {"raw": f"{engagement:.6f}", "normalized": engagement}}
        candidates.append(item)
    if not candidates:
        return None
    record = max(candidates, key=lambda item: metric_value(item, "engagementRate") or 0.0)
    return public_record_summary(record, "engagementRate")


def public_record_summary(record: dict[str, Any], metric: str) -> dict[str, Any]:
    return {
        "platform": record.get("platform", ""),
        "title": record.get("title", ""),
        "publishedUrl": record.get("publishedUrl", ""),
        "metric": metric,
        "value": metric_value(record, metric),
        "sourceType": record.get("sourceType", ""),
        "evidence": record.get("evidence", []),
    }


def summarize_comment_demand(comments: list[dict[str, Any]], demand_signals: list[dict[str, Any]]) -> dict[str, Any]:
    signal_counts = Counter(signal["type"] for signal in demand_signals if signal.get("type"))
    examples: dict[str, list[str]] = defaultdict(list)
    platforms: dict[str, set[str]] = defaultdict(set)
    for signal in demand_signals:
        signal_type = signal.get("type", "")
        excerpt = signal.get("excerpt", "")
        if signal_type and excerpt and len(examples[signal_type]) < 3:
            examples[signal_type].append(excerpt)
        if signal_type and signal.get("platform"):
            platforms[signal_type].add(signal["platform"])
    top_signals = [
        {
            "type": signal_type,
            "count": count,
            "platforms": sorted(platforms.get(signal_type, set())),
            "examples": examples.get(signal_type, []),
        }
        for signal_type, count in signal_counts.most_common()
    ]
    top_comments = sorted(comments, key=lambda item: (item.get("likes") or 0) + (item.get("replies") or 0), reverse=True)[:5]
    return {
        "topSignals": top_signals,
        "topComments": top_comments,
    }


def next_round_content(
    status: str,
    context: dict[str, Any],
    platforms: list[str],
    winners: dict[str, Any],
    comment_demand: dict[str, Any],
) -> list[dict[str, Any]]:
    if status == "waiting_real_data":
        return []
    product_name = context.get("name") or "the product"
    best_reach = winners.get("byViews") or winners.get("byEngagement") or {}
    commercial = winners.get("byRevenue") or winners.get("byOrders") or {}
    signals = comment_demand.get("topSignals") or []
    primary_signals = signals[:3] if signals else [{"type": "proof", "examples": []}]
    preferred_platforms = unique([commercial.get("platform"), best_reach.get("platform"), *platforms])[:5]
    content: list[dict[str, Any]] = []
    for index, signal in enumerate(primary_signals, start=1):
        signal_type = signal.get("type", "proof")
        platform = preferred_platforms[(index - 1) % len(preferred_platforms)] if preferred_platforms else "youtube"
        example = first(signal.get("examples", []))
        angle = angle_for_signal(signal_type, product_name)
        content.append(
            {
                "id": f"next-{index:03d}",
                "platform": platform,
                "angle": angle,
                "title": title_for_signal(signal_type, product_name),
                "hook": hook_for_signal(signal_type, product_name, example),
                "scriptBrief": script_brief_for_signal(signal_type, best_reach, commercial),
                "sourceEvidence": evidence_for_signal(signal, best_reach, commercial),
            }
        )
    return content


def angle_for_signal(signal_type: str, product_name: str) -> str:
    mapping = {
        "pricing": f"Answer pricing hesitation before pitching {product_name}",
        "integration": f"Show the most requested integration path for {product_name}",
        "feature_request": f"Turn feature requests into a product-roadmap proof post for {product_name}",
        "question": f"Use audience questions as the opening FAQ hook for {product_name}",
        "pain_point": f"Lead with the painful workflow before introducing {product_name}",
        "objection": f"Handle the main objection with proof and a low-friction CTA for {product_name}",
        "cta_intent": f"Convert buying intent into a direct demo/download CTA for {product_name}",
    }
    return mapping.get(signal_type, f"Reuse proven reach and commercial proof for {product_name}")


def title_for_signal(signal_type: str, product_name: str) -> str:
    mapping = {
        "pricing": f"{product_name} pricing explained: when it is worth it",
        "integration": f"How {product_name} fits into your existing workflow",
        "feature_request": f"What users asked us to add next to {product_name}",
        "question": f"Top questions about {product_name}, answered with real launch data",
        "pain_point": f"Stop doing launch content manually: {product_name} workflow demo",
        "objection": f"Before you try {product_name}, watch this honest limitation breakdown",
        "cta_intent": f"Try {product_name}: a 60-second setup and result demo",
    }
    return mapping.get(signal_type, f"{product_name}: what worked in the last launch and what changes next")


def hook_for_signal(signal_type: str, product_name: str, example: str) -> str:
    if example:
        return f"User comment to answer first: {example}"
    mapping = {
        "pricing": f"If you are unsure whether {product_name} is worth paying for, start here.",
        "integration": f"The real question is not what {product_name} does, but where it fits into your stack.",
        "pain_point": f"Most launch content fails before publishing because the workflow is too slow.",
    }
    return mapping.get(signal_type, f"Here is what the last round taught us about promoting {product_name}.")


def script_brief_for_signal(signal_type: str, best_reach: dict[str, Any], commercial: dict[str, Any]) -> str:
    parts = [f"Open with the {signal_type} demand signal."]
    if best_reach:
        parts.append(f"Reference the strongest reach pattern from {best_reach.get('platform')} without copying wording.")
    if commercial:
        parts.append(f"Use the commercial winner from {commercial.get('platform')} as the CTA direction.")
    parts.append("End with one measurable CTA and register the published URL for metrics recovery.")
    return " ".join(parts)


def evidence_for_signal(signal: dict[str, Any], best_reach: dict[str, Any], commercial: dict[str, Any]) -> list[str]:
    evidence = []
    evidence.extend(signal.get("examples", []))
    for item in (best_reach, commercial):
        if item:
            evidence.extend(item.get("evidence", []))
            if item.get("publishedUrl"):
                evidence.append(item["publishedUrl"])
    return unique(evidence)


def platform_actions_for(
    status: str,
    platforms: list[str],
    winners: dict[str, Any],
    comment_demand: dict[str, Any],
    manual_required: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if status == "waiting_real_data":
        return [
            {
                "platform": platform,
                "action": "collect_real_evidence",
                "reason": "No proven metrics, comments, orders, or revenue were available.",
            }
            for platform in platforms or DEFAULT_PLATFORMS
        ]
    actions = []
    revenue_platform = (winners.get("byRevenue") or {}).get("platform")
    reach_platform = (winners.get("byViews") or {}).get("platform")
    for platform in platforms or DEFAULT_PLATFORMS:
        if platform == revenue_platform:
            action = "scale_commercial_winner"
            reason = "This platform has the strongest proven revenue/order evidence."
        elif platform == reach_platform:
            action = "turn_reach_into_conversion_test"
            reason = "This platform has the strongest observed reach; add a sharper CTA and tracking."
        elif any(item.get("platform") == platform for item in manual_required):
            action = "import_missing_real_evidence"
            reason = "Optimization is incomplete until this platform has a real export, screenshot, or visible snapshot."
        elif comment_demand.get("topSignals"):
            action = "adapt_top_comment_signal"
            reason = f"Use top audience signal: {comment_demand['topSignals'][0]['type']}."
        else:
            action = "reuse_best_proven_structure"
            reason = "Reuse the best proven structure while keeping platform-native format."
        actions.append({"platform": platform, "action": action, "reason": reason})
    return actions


def recommended_commands_for(out_dir: Path, context: dict[str, Any], platforms: list[str]) -> list[dict[str, str]]:
    platforms_arg = ",".join(platforms or DEFAULT_PLATFORMS)
    product_url = context.get("url") or "https://example.com/product"
    return [
        {
            "purpose": "run_next_cycle",
            "command": f"python scripts/promotion_cycle_runner.py --browser-url \"{product_url}\" --platforms {platforms_arg} --run-next-round-optimization --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "refresh_viral_discovery",
            "command": f"python scripts/multi_query_viral_discovery.py --workflow-manifest \"{out_dir / 'reports/promotion-manager/agent-run/workflow-manifest.json'}\" --platforms {platforms_arg} --top-n 20 --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "recover_next_round_metrics",
            "command": f"python scripts/metrics_recovery.py --out-dir \"{out_dir}\"",
        },
        {
            "purpose": "prepare_publish_queue",
            "command": f"python scripts/publish_readiness_runner.py --workflow-manifest \"{out_dir / 'reports/promotion-manager/agent-run/workflow-manifest.json'}\" --build-queue --out-dir \"{out_dir}\"",
        },
    ]


def next_actions_for(status: str, next_content: list[dict[str, Any]], manual_required: list[dict[str, Any]]) -> list[str]:
    if status == "waiting_real_data":
        return [
            "Import real metrics, public/browser-visible comments, or business exports before optimizing.",
            "Register published URLs with published_items.py or publish_url_capture.py, then rerun metrics_recovery.py.",
        ]
    actions = [
        "Generate the next draft/video from nextRoundContent and keep the sourceEvidence attached.",
        "Create a guarded publish queue; official writes still require credentials and explicit approval.",
        "After publishing, register the real URL and rerun metrics/comment/business recovery.",
    ]
    if manual_required:
        actions.append("Resolve manualOrPendingRequirements before treating the optimization as complete.")
    if next_content:
        actions.append(f"Start with {next_content[0]['platform']} angle: {next_content[0]['angle']}")
    return actions


def product_context(workflow: dict[str, Any]) -> dict[str, Any]:
    product = workflow.get("product") or workflow.get("productProfile") or workflow.get("input") or {}
    if not isinstance(product, dict):
        product = {}
    return {
        "name": clean(first_non_empty(product, "name", "productName", "title")) or "Product",
        "url": clean(first_non_empty(product, "url", "productUrl", "browserUrl", "sourceUrl")),
        "audience": clean(first_non_empty(product, "audience", "targetAudience")),
        "valueProposition": clean(first_non_empty(product, "valueProposition", "description", "tagline")),
    }


def target_platforms(
    workflow: dict[str, Any],
    publish_queue: dict[str, Any],
    metric_records: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    business_attributions: list[dict[str, Any]],
) -> list[str]:
    candidates: list[str] = []
    for value in workflow.get("platforms", []):
        candidates.append(clean(value))
    for item in workflow.get("publishAutomation", []):
        if isinstance(item, dict):
            candidates.append(clean(item.get("platform")))
    for item in publish_queue.get("records", []):
        if isinstance(item, dict):
            candidates.append(clean(item.get("platform")))
    for record in [*metric_records, *comments, *business_attributions]:
        candidates.append(clean(record.get("platform")))
    result = [value for value in unique(candidates) if value]
    return result or DEFAULT_PLATFORMS


def business_summary(reports: list[dict[str, Any]], attributions: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {"matchedRows": 0, "attributedOrders": 0.0, "attributedRevenue": 0.0}
    for report in reports:
        summary = report.get("summary") or {}
        totals["matchedRows"] += int(summary.get("matchedRows") or 0)
        totals["attributedOrders"] += float(summary.get("attributedOrders") or 0.0)
        totals["attributedRevenue"] += float(summary.get("attributedRevenue") or 0.0)
    if not reports:
        totals["attributedOrders"] = sum(metric_value(record, "orders") or 0.0 for record in attributions)
        totals["attributedRevenue"] = sum(metric_value(record, "revenue") or 0.0 for record in attributions)
    totals["attributionRecords"] = len(attributions)
    return totals


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = optimization_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "next-round-optimization.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "next-round-optimization.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Next-Round Optimization",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Product: {report['product'].get('name', '')}",
        "",
        "## Evidence Coverage",
    ]
    for key, value in report["evidenceCoverage"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Winners"])
    for key, value in report["winners"].items():
        if value:
            lines.append(f"- {key}: {value.get('platform')} / {value.get('title')} / {value.get('metric')}={value.get('value')}")
        else:
            lines.append(f"- {key}: none")
    lines.extend(["", "## Comment Demand"])
    if report["commentDemand"]["topSignals"]:
        for signal in report["commentDemand"]["topSignals"]:
            lines.append(f"- {signal['type']}: {signal['count']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Next-Round Content"])
    if report["nextRoundContent"]:
        for item in report["nextRoundContent"]:
            lines.extend(
                [
                    "",
                    f"### {item['id']} - {item['platform']}",
                    f"- Angle: {item['angle']}",
                    f"- Title: {item['title']}",
                    f"- Hook: {item['hook']}",
                    f"- Script brief: {item['scriptBrief']}",
                ]
            )
    else:
        lines.append("- waiting for real evidence")
    lines.extend(["", "## Platform Actions"])
    lines.extend([f"- {item['platform']}: `{item['action']}` {item['reason']}" for item in report["platformActions"]])
    lines.extend(["", "## Commands"])
    lines.extend([f"- {item['purpose']}: `{item['command']}`" for item in report["recommendedCommands"]])
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {item}" for item in report["nextActions"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


def default_metrics_recovery(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"


def default_comment_evidence(out_dir: Path) -> Path:
    export_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json"
    return export_path if export_path.exists() else out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"


def default_business_attribution(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"


def default_workflow_manifest(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/agent-run/workflow-manifest.json"


def default_publish_queue(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"


def optimization_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/optimization"


def load_many(values: list[str], default_path: Path) -> list[dict[str, Any]]:
    paths = [Path(value) for value in values if value]
    if default_path.exists() and default_path not in paths:
        paths.append(default_path)
    reports = []
    for path in paths:
        data = load_json(path)
        if isinstance(data, dict):
            reports.append(data)
    return reports


def load_optional_json(value: str, default_path: Path) -> dict[str, Any]:
    path = Path(value) if value else default_path
    data = load_json(path) if path.exists() else {}
    return data if isinstance(data, dict) else {}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def metric_value(record: dict[str, Any], name: str) -> float | None:
    metric = (record.get("metrics") or {}).get(name) or {}
    value = metric.get("normalized")
    if isinstance(value, (int, float)):
        return float(value)
    return numeric(metric.get("raw"))


def numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "").replace("$", "").replace("￥", "")
    multiplier = 1.0
    lowered = text.lower()
    if lowered.endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    elif lowered.endswith("m"):
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10_000.0
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def int_value(value: Any) -> int | None:
    number = numeric(value)
    return int(number) if number is not None else None


def first_non_empty(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if item)
        if value not in (None, ""):
            return value
    return ""


def first(values: list[Any]) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def split_evidence(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean(item) for item in value if clean(item)]
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for record in records:
        key = f"{record.get('platform')}:{record.get('publishedUrl') or record.get('contentId') or record.get('title')}".lower()
        if key not in seen:
            result.append(record)
            seen.add(key)
    return result


def dedupe_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for comment in comments:
        key = f"{comment.get('platform')}:{comment.get('author')}:{comment.get('text')}".lower()
        if key not in seen:
            result.append(comment)
            seen.add(key)
    return result


def unique(values: list[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        if value in (None, ""):
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def guardrails() -> list[str]:
    return [
        "Use only real metrics, public/browser-visible comments, official API output, screenshots, or business exports.",
        "Do not treat missing metrics as zero and do not fabricate views, likes, comments, orders, revenue, or published URLs.",
        "Do not auto-publish; platform writes still require official credentials, platform access, and explicit approval.",
        "Do not save cookies, passwords, OAuth tokens, browser tokens, or private analytics endpoints.",
        "Treat manual evidence requests as missing evidence, not as negative performance.",
    ]


if __name__ == "__main__":
    main()
