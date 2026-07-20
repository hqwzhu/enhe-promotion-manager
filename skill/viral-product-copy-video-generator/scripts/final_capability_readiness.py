#!/usr/bin/env python3
"""Build an operator-facing final capability readiness matrix."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
DEFAULT_PRODUCT_URL = "https://example.com/product"
VIDEO_RESEARCH_PLATFORMS = {"youtube", "douyin", "tiktok", "xiaohongshu"}
FRESH_PLATFORM_LEARNING_STATUSES = {"fresh_live_checked", "fresh_live_checked_with_warnings"}
OBJECTIVE_REQUIREMENTS = [
    {
        "id": "product_url_codex_structured_intake",
        "label": "Codex reads every product URL and passes structured page evidence into product intake.",
    },
    {
        "id": "viral_creator_video_research",
        "label": "Search and capture viral creators, posts, repos, and video evidence across target platforms.",
    },
    {
        "id": "copy_and_real_video_generation",
        "label": "Generate platform-native viral titles, copy, tags, first-batch comments, MP4 videos, covers, and detail images.",
    },
    {
        "id": "official_or_browser_assisted_publish",
        "label": "manual publish packages are the primary path; auto-publish ports are reserved for official API-only upgrades.",
    },
    {
        "id": "real_metrics_comments_orders_revenue",
        "label": "Recover real views, likes, comments, orders, revenue, and evidence-backed demand signals.",
    },
    {
        "id": "next_round_optimization",
        "label": "Use real evidence for retrospective, next-round hooks, scripts, and platform actions.",
    },
    {
        "id": "controlled_self_evolution",
        "label": "Audit tools, learn from official/public sources, install allowlisted runtimes, and sync the installed Skill only with approval.",
    },
    {
        "id": "github_documentation_and_install_tutorial",
        "label": "Keep GitHub-facing project intro, usage guide, install tutorial, and final capability map ready for open-source users.",
    },
    {
        "id": "browser_extension_operator_ui_subscription",
        "label": "Provide a Chrome extension operator UI with subscription hooks, production license-service reference, store package, developer info, and ENHE website traffic links.",
    },
    {
        "id": "phase_progress_reporting",
        "label": "Report progress after each stage with completed goals, unfinished goals, next plan, and estimated remaining time.",
    },
]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    sources = load_sources(args, out_dir)
    matrix = build_matrix(args, out_dir, sources)
    write_report(out_dir, matrix)
    print(f"Final capability readiness written to: {(report_dir(out_dir) / 'final-capability-readiness.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize final capability readiness from generated promotion manager reports.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--final-run", default="", help="Path to final-capability-run.json.")
    parser.add_argument("--final-audit", default="", help="Path to final-capability-audit.json.")
    parser.add_argument("--platform-access-audit", default="", help="Path to platform-access-audit.json.")
    parser.add_argument("--self-evolution-audit", default="", help="Path to self-evolution-audit.json.")
    parser.add_argument("--publish-readiness", action="append", default=[], help="Path to a publish-readiness.json file. Can repeat.")
    parser.add_argument("--publish-setup", action="append", default=[], help="Path to a publish-setup.json file. Can repeat.")
    parser.add_argument("--real-evidence-setup", action="append", default=[], help="Path to a real-evidence-setup.json file. Can repeat.")
    parser.add_argument("--real-evidence-inbox-setup", action="append", default=[], help="Path to a real-evidence-inbox-setup.json file. Can repeat.")
    parser.add_argument("--viral-evidence-inbox-setup", action="append", default=[], help="Path to a viral-evidence-inbox-setup.json file. Can repeat.")
    parser.add_argument("--viral-evidence-inbox", action="append", default=[], help="Path to a viral-evidence-inbox.json file. Can repeat.")
    parser.add_argument("--synthetic-evidence", action="append", default=[], help="Path to a synthetic-evidence.json file. Can repeat.")
    return parser.parse_args()


def load_sources(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    final_run_path = first_existing(
        [args.final_run, out_dir / "reports/promotion-manager/final-run/final-capability-run.json"]
    )
    final_audit_path = first_existing(
        [args.final_audit, out_dir / "reports/promotion-manager/capability/final-capability-audit.json"]
    )
    platform_access_path = first_existing(
        [args.platform_access_audit, out_dir / "reports/promotion-manager/platform-access/platform-access-audit.json"]
    )
    self_evolution_path = first_existing(
        [args.self_evolution_audit, out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.json"]
    )
    publish_readiness_paths = explicit_or_discovered(
        args.publish_readiness,
        out_dir,
        "reports/promotion-manager/publish-readiness/publish-readiness.json",
        "product-batch-runs/*/reports/promotion-manager/publish-readiness/publish-readiness.json",
    )
    publish_setup_paths = explicit_or_discovered(
        args.publish_setup,
        out_dir,
        "reports/promotion-manager/publish-setup/publish-setup.json",
        "product-batch-runs/*/reports/promotion-manager/publish-setup/publish-setup.json",
    )
    real_evidence_setup_paths = explicit_or_discovered(
        args.real_evidence_setup,
        out_dir,
        "reports/promotion-manager/real-evidence-setup/real-evidence-setup.json",
        "product-batch-runs/*/reports/promotion-manager/real-evidence-setup/real-evidence-setup.json",
    )
    real_evidence_inbox_setup_paths = explicit_or_discovered(
        args.real_evidence_inbox_setup,
        out_dir,
        "reports/promotion-manager/real-evidence-inbox-setup/real-evidence-inbox-setup.json",
        "product-batch-runs/*/reports/promotion-manager/real-evidence-inbox-setup/real-evidence-inbox-setup.json",
    )
    viral_evidence_inbox_setup_paths = explicit_or_discovered(
        args.viral_evidence_inbox_setup,
        out_dir,
        "reports/promotion-manager/competitors/viral-evidence-inbox-setup/viral-evidence-inbox-setup.json",
        "product-batch-runs/*/reports/promotion-manager/competitors/viral-evidence-inbox-setup/viral-evidence-inbox-setup.json",
    )
    viral_evidence_inbox_paths = explicit_or_discovered(
        args.viral_evidence_inbox,
        out_dir,
        "reports/promotion-manager/competitors/viral-evidence-inbox/viral-evidence-inbox.json",
        "product-batch-runs/*/reports/promotion-manager/competitors/viral-evidence-inbox/viral-evidence-inbox.json",
    )
    launch_unlock_paths = unique_paths(
        glob_existing(out_dir, "reports/promotion-manager/launch-unlock/launch-unlock.json")
        + glob_existing(out_dir, "product-batch-runs/*/reports/promotion-manager/launch-unlock/launch-unlock.json")
    )
    synthetic_evidence_paths = explicit_or_discovered(
        args.synthetic_evidence,
        out_dir,
        "reports/promotion-manager/synthetic-evidence/synthetic-evidence.json",
        "*/reports/promotion-manager/synthetic-evidence/synthetic-evidence.json",
        "*/*/reports/promotion-manager/synthetic-evidence/synthetic-evidence.json",
    )
    return {
        "finalRunPath": final_run_path,
        "finalAuditPath": final_audit_path,
        "platformAccessPath": platform_access_path,
        "selfEvolutionPath": self_evolution_path,
        "publishReadinessPaths": publish_readiness_paths,
        "publishSetupPaths": publish_setup_paths,
        "realEvidenceSetupPaths": real_evidence_setup_paths,
        "realEvidenceInboxSetupPaths": real_evidence_inbox_setup_paths,
        "viralEvidenceInboxSetupPaths": viral_evidence_inbox_setup_paths,
        "viralEvidenceInboxPaths": viral_evidence_inbox_paths,
        "launchUnlockPaths": launch_unlock_paths,
        "syntheticEvidencePaths": synthetic_evidence_paths,
        "finalRun": read_json(final_run_path),
        "finalAudit": read_json(final_audit_path),
        "platformAccess": read_json(platform_access_path),
        "selfEvolution": read_json(self_evolution_path),
        "publishReadiness": [read_json(path) for path in publish_readiness_paths],
        "publishSetup": [read_json(path) for path in publish_setup_paths],
        "realEvidenceSetup": [read_json(path) for path in real_evidence_setup_paths],
        "realEvidenceInboxSetup": [read_json(path) for path in real_evidence_inbox_setup_paths],
        "viralEvidenceInboxSetup": [read_json(path) for path in viral_evidence_inbox_setup_paths],
        "viralEvidenceInbox": [read_json(path) for path in viral_evidence_inbox_paths],
        "launchUnlock": [read_json(path) for path in launch_unlock_paths],
        "syntheticEvidence": [read_json_with_source(path) for path in synthetic_evidence_paths],
    }


def build_matrix(args: argparse.Namespace, out_dir: Path, sources: dict[str, Any]) -> dict[str, Any]:
    final_run = sources["finalRun"]
    final_audit = sources["finalAudit"]
    platform_access = sources["platformAccess"]
    self_evolution = sources["selfEvolution"]
    readiness = sources["publishReadiness"]
    setup = sources["publishSetup"]
    real_evidence_setup = [*sources["realEvidenceSetup"], *sources["realEvidenceInboxSetup"]]
    synthetic_evidence = sources["syntheticEvidence"]
    rows = [
        product_intake_row(final_run, final_audit),
        viral_research_row(
            final_run,
            final_audit,
            sources["viralEvidenceInboxSetup"],
            sources["viralEvidenceInbox"],
            [*sources["viralEvidenceInboxSetupPaths"], *sources["viralEvidenceInboxPaths"]],
        ),
        copy_video_row(final_run, final_audit),
        publish_row(final_run, final_audit, readiness, setup),
        metrics_row(final_run, final_audit, real_evidence_setup, synthetic_evidence),
        optimization_row(final_run, final_audit, synthetic_evidence),
        self_evolution_row(self_evolution, final_audit, platform_access),
        github_docs_row(final_audit),
        browser_extension_row(final_audit),
        phase_progress_reporting_row(final_audit),
    ]
    product_url = product_url_from_final_run(final_run)
    action_queue = build_action_queue(
        out_dir,
        rows,
        final_run,
        final_audit,
        readiness,
        setup,
        real_evidence_setup,
        self_evolution,
        platform_access,
        product_url,
    )
    summary = summarize(rows, action_queue)
    return {
        "generatedAt": TODAY,
        "status": final_status(rows),
        "outDir": str(out_dir),
        "sourceReports": source_report_summary(sources),
        "summary": summary,
        "requirements": rows,
        "platformMatrix": platform_matrix(final_audit, readiness),
        "externalGates": external_gates(rows),
        "actionQueue": action_queue,
        "operatingSequence": operating_sequence(out_dir, product_url),
        "guardrails": [
            "This matrix uses report status and evidence paths only; it never writes credential values.",
            "Official publishing still requires platform credentials, account authorization, and exact approval.",
            "Browser-assisted publishing must stop for login, captcha, risk checks, account verification, and final publish.",
            "Metrics, comments, orders, and revenue must come from public pages, official APIs, screenshots, structured snapshots, or business exports.",
            "Installed Skill sync and dependency changes remain reviewed actions; no silent self-replacement from network code.",
        ],
    }


def product_intake_row(final_run: dict[str, Any], final_audit: dict[str, Any]) -> dict[str, Any]:
    audit_item = requirement(final_audit, "product_url_structured_intake")
    summary = final_run.get("summary") if isinstance(final_run.get("summary"), dict) else {}
    product_batch = final_run.get("productBatch") if isinstance(final_run.get("productBatch"), dict) else {}
    codex_read = bool((final_run.get("input") or {}).get("codexReadFirst")) if isinstance(final_run.get("input"), dict) else False
    runs = int_value(summary.get("promotionRuns"))
    status = "ready"
    missing: list[str] = []
    if audit_item.get("status") not in {"ready"}:
        status = "partial_ready"
        missing.extend(audit_item.get("missing") or ["verified browser structured intake"])
    if final_run and (not codex_read or runs == 0):
        status = "needs_real_run_evidence"
        if not codex_read:
            missing.append("final run did not record codexReadFirst=true")
        if runs == 0:
            missing.append("no product promotion run evidence")
    evidence = audit_item.get("evidence") or []
    if product_batch.get("report"):
        evidence = list(evidence) + [product_batch["report"]]
    return row("product_url_codex_structured_intake", status, evidence, missing, [])


def viral_research_row(
    final_run: dict[str, Any],
    final_audit: dict[str, Any],
    viral_inbox_setup_reports: list[dict[str, Any]],
    viral_inbox_reports: list[dict[str, Any]],
    viral_inbox_paths: list[Path],
) -> dict[str, Any]:
    audit_item = requirement(final_audit, "viral_creator_content_research")
    summary = final_run.get("summary") if isinstance(final_run.get("summary"), dict) else {}
    runs = int_value(summary.get("multiQueryDiscoveryRuns"))
    status = audit_item.get("status") or "unknown"
    missing: list[str] = []
    inbox = viral_inbox_metrics(viral_inbox_setup_reports, viral_inbox_reports)
    requested = requested_platforms(final_run)
    requested_video_platforms = sorted(platform for platform in requested if platform in VIDEO_RESEARCH_PLATFORMS)
    observed_platforms = sorted(observed_multi_query_platforms(final_run))
    observed_video_platforms = sorted(platform for platform in observed_platforms if platform in VIDEO_RESEARCH_PLATFORMS)
    missing_video_platforms = [
        platform for platform in requested_video_platforms if platform not in observed_video_platforms
    ]
    metrics = {
        "multiQueryDiscoveryRuns": runs,
        "searchCapturesReady": int_value(summary.get("multiQuerySearchCapturesReady")),
        "viralMaterialsObserved": int_value(summary.get("multiQueryViralMaterialsObserved")),
        "mergedMaterials": int_value(summary.get("multiQueryMergedMaterials")),
        "mergedCreators": int_value(summary.get("multiQueryMergedCreators")),
        "deepEvidenceRuns": int_value(summary.get("multiQueryDeepEvidenceRuns")),
        "followUpCaptureRuns": int_value(summary.get("multiQueryFollowUpCaptureRuns")),
        "followUpImportedRecords": int_value(summary.get("multiQueryFollowUpImportedRecords")),
        "browserVisibleCaptureReady": int_value(summary.get("multiQueryBrowserVisibleCaptureReady")),
        "videoSampleRuns": int_value(summary.get("multiQueryVideoSampleRuns")),
        "videoSampleReady": int_value(summary.get("multiQueryVideoSampleReady")),
        "videoSampleFrames": int_value(summary.get("multiQueryVideoSampleFrames")),
        "requestedPlatforms": requested,
        "requestedVideoPlatforms": requested_video_platforms,
        "observedResearchPlatforms": observed_platforms,
        "observedVideoPlatforms": observed_video_platforms,
        "missingVideoPlatformEvidence": missing_video_platforms,
        **inbox,
    }
    if final_run and runs == 0:
        status = "needs_real_run_evidence"
        missing.append("no multi-query viral discovery run evidence in the final run")
    elif (
        final_run
        and metrics["mergedMaterials"] > 0
        and metrics["mergedCreators"] > 0
        and metrics["videoSampleFrames"] > 0
        and not missing_video_platforms
    ):
        status = "ready_with_video_evidence"
    elif final_run and missing_video_platforms and (
        metrics["mergedMaterials"] > 0
        or metrics["searchCapturesReady"] > 0
        or metrics["deepEvidenceRuns"] > 0
    ):
        status = "partial_ready_non_video_platform_evidence"
        missing.append(
            "no viral material evidence was captured for requested video platforms: "
            + ", ".join(missing_video_platforms)
        )
        if requested_video_platforms:
            missing.append(
                "no browser-visible video frame samples were captured for requested video platforms: "
                + ", ".join(missing_video_platforms)
            )
    elif final_run and (
        metrics["followUpImportedRecords"] > 0
        or metrics["browserVisibleCaptureReady"] > 0
        or metrics["deepEvidenceRuns"] > 0
    ):
        status = "partial_ready_deep_content_evidence"
        missing.append("no browser-visible video frame samples were captured in the final run")
    elif final_run and (metrics["mergedMaterials"] > 0 or metrics["searchCapturesReady"] > 0):
        status = "partial_ready_search_capture_only"
        missing.append("no deep competitor records or video frame samples were captured in the final run")
    if metrics["viralInboxImportedRecords"] > 0 and status not in {"ready_with_video_evidence"}:
        status = "partial_ready_user_inbox_evidence"
        missing.append("viral evidence was imported from a user-filled inbox; run browser/official capture when platform access allows")
    elif not final_run and metrics["viralInboxSetupReports"] > 0 and metrics["viralInboxImportedRecords"] == 0:
        status = "partial_ready_viral_inbox_available"
        missing.append("viral evidence inbox templates are ready but no real competitor evidence has been imported")
    evidence = list(audit_item.get("evidence") or [])
    evidence.extend(str(path) for path in viral_inbox_paths if path)
    return row(
        "viral_creator_video_research",
        status,
        evidence,
        missing or audit_item.get("missing") or [],
        audit_item.get("limits") or [],
        metrics,
    )


def copy_video_row(final_run: dict[str, Any], final_audit: dict[str, Any]) -> dict[str, Any]:
    audit_item = requirement(final_audit, "copy_and_real_video_generation")
    summary = final_run.get("summary") if isinstance(final_run.get("summary"), dict) else {}
    content_count = int_value(summary.get("contentArtifacts"))
    video_count = int_value(summary.get("videoFilesGenerated"))
    cover_count = int_value(summary.get("mediaAssetCoversReady"))
    detail_count = int_value(summary.get("mediaAssetDetailImagesReady"))
    status = audit_item.get("status") or "unknown"
    missing: list[str] = []
    if final_run and content_count == 0:
        status = "needs_real_run_evidence"
        missing.append("no generated content artifact in the final run")
    if final_run and video_count == 0:
        status = "partial_ready"
        missing.append("no MP4 generated in the final run")
    if final_run and cover_count == 0:
        status = "partial_ready"
        missing.append("no cover images generated in the final run")
    if final_run and detail_count == 0:
        status = "partial_ready"
        missing.append("no detail images generated in the final run")
    metrics = {
        "contentArtifacts": content_count,
        "videoFilesGenerated": video_count,
        "coverImagesGenerated": cover_count,
        "detailImagesGenerated": detail_count,
    }
    return row("copy_and_real_video_generation", status, audit_item.get("evidence") or [], missing or audit_item.get("missing") or [], [], metrics)


def publish_row(
    final_run: dict[str, Any],
    final_audit: dict[str, Any],
    readiness_reports: list[dict[str, Any]],
    setup_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    audit_item = requirement(final_audit, "all_platform_auto_publish")
    readiness_records = [record for report in readiness_reports for record in list_records(report, "records")]
    setup_records = [record for report in setup_reports for record in list_records(report, "records")]
    ready_to_execute = sum(1 for item in readiness_records if item.get("readiness") == "ready_to_execute")
    dry_run_ready = sum(1 for item in readiness_records if item.get("readiness") == "dry_run_ready")
    manual_required = sum(
        1
        for item in readiness_records
        if item.get("readiness")
        in {"manual_publish_required", "browser_assisted_or_official_app_required", "browser_assisted_publish_ready"}
    )
    missing: list[str] = publish_missing_from_readiness(readiness_records)
    if not readiness_records:
        missing.extend(audit_item.get("missing") or [])
    if not readiness_records and final_run:
        missing.append("no publish readiness records generated")
    if not setup_records and final_run:
        missing.append("no publish setup kit generated")
    status = audit_item.get("status") or "unknown"
    if ready_to_execute or dry_run_ready:
        status = "partial_ready_external_approval_required"
    if manual_required:
        status = "partial_ready_browser_or_manual_required"
    if readiness_records:
        status = "manual_package_ready_auto_ports_reserved"
    return row(
        "official_or_browser_assisted_publish",
        status,
        audit_item.get("evidence") or [],
        ordered_unique(missing),
        audit_item.get("limits") or [],
        {
            "readinessRecords": len(readiness_records),
            "setupRecords": len(setup_records),
            "readyToExecute": ready_to_execute,
            "dryRunReady": dry_run_ready,
            "manualOrBrowserRequired": manual_required,
            "manualPublishPackagesPrimary": True,
            "autoPublishPortsReserved": True,
            "officialApiOnly": True,
        },
    )


def publish_missing_from_readiness(readiness_records: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for item in readiness_records:
        platform = str(item.get("platform") or "").strip().lower()
        readiness = str(item.get("readiness") or "")
        if readiness == "missing_credentials":
            missing.append(platform_credential_missing_message(platform, item.get("credentialStatus")))
        target = item.get("targetStatus") if isinstance(item.get("targetStatus"), dict) else {}
        if target and not target.get("ready", False):
            detail = str(target.get("missing") or target.get("field") or "publish target").strip()
            missing.append(f"{platform or 'platform'} target missing: {detail}")
    return ordered_unique(missing)


def platform_credential_missing_message(platform: str, credential_status: Any) -> str:
    if platform == "github":
        return "GITHUB_TOKEN or GH_TOKEN for GitHub writes"
    if platform == "youtube":
        return "YouTube OAuth access token or OAuth client credentials"
    if platform == "douyin":
        return "Douyin is currently configured for browser-assisted publishing; no DOUYIN_* credential is required unless the future official port is re-enabled"
    if platform == "tiktok":
        return "TikTok open-platform app credentials and user authorization"
    missing_env: list[str] = []
    if isinstance(credential_status, dict):
        missing_env = [str(item) for item in credential_status.get("missingEnv", []) if str(item).strip()]
    if missing_env:
        return f"{platform or 'platform'} credentials missing: {', '.join(missing_env)}"
    return f"{platform or 'platform'} credentials missing"


def metrics_row(
    final_run: dict[str, Any],
    final_audit: dict[str, Any],
    evidence_setup_reports: list[dict[str, Any]],
    synthetic_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    audit_item = requirement(final_audit, "real_metrics_orders_revenue_recovery")
    summary = final_run.get("summary") if isinstance(final_run.get("summary"), dict) else {}
    metrics = real_evidence_metrics(summary)
    synthetic_metrics = synthetic_validation_metrics(synthetic_reports)
    metrics.update(synthetic_metrics)
    setup_targets = max(
        int_value(summary.get("realEvidenceSetupTargets")),
        sum(evidence_setup_target_count(report) for report in evidence_setup_reports if isinstance(report, dict)),
    )
    metrics["realEvidenceSetupTargets"] = setup_targets
    status = audit_item.get("status") or "unknown"
    missing = list(audit_item.get("missing") or [])
    if final_run and metrics["evidenceCount"] == 0:
        status = "waiting_real_data_with_evidence_templates" if setup_targets else "waiting_real_data"
        missing.append("real evidence templates are ready but no filled real data has been imported" if setup_targets else "no real metrics, comments, business rows, or recovered metric records in final run")
    elif final_run and metrics["hasFullFunnelEvidence"]:
        status = "ready_with_full_funnel_evidence"
        missing = []
    elif final_run and metrics["hasAnySocialOrCommentEvidence"] and not metrics["hasAnyBusinessEvidence"]:
        status = "partial_ready_social_metrics_only"
        missing.extend(["no real order evidence in final run", "no real revenue evidence in final run"])
    elif final_run and metrics["hasAnyBusinessEvidence"] and not metrics["hasAnySocialOrCommentEvidence"]:
        status = "partial_ready_business_attribution_only"
        missing.extend(["no real view evidence in final run", "no real like evidence in final run", "no real comment evidence in final run"])
    elif final_run:
        status = "partial_ready_evidence_incomplete"
        for label, key in [
            ("view", "hasViewsEvidence"),
            ("like", "hasLikesEvidence"),
            ("comment", "hasCommentsEvidence"),
            ("order", "hasOrdersEvidence"),
            ("revenue", "hasRevenueEvidence"),
        ]:
            if not metrics[key]:
                missing.append(f"no real {label} evidence in final run")
    limits = list(audit_item.get("limits") or [])
    if synthetic_metrics["syntheticValidationReports"]:
        limits.extend(
            [
                "Synthetic/demo evidence validates the recovery loop only and does not count as real platform, order, or revenue performance.",
                "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT",
            ]
        )
    evidence = list(audit_item.get("evidence") or [])
    evidence.extend(synthetic_metrics["syntheticValidationReportPaths"])
    return row(
        "real_metrics_comments_orders_revenue",
        status,
        evidence,
        ordered_unique(missing),
        ordered_unique(limits),
        metrics,
    )


def optimization_row(
    final_run: dict[str, Any],
    final_audit: dict[str, Any],
    synthetic_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    audit_item = requirement(final_audit, "retrospective_next_round_optimization")
    summary = final_run.get("summary") if isinstance(final_run.get("summary"), dict) else {}
    next_count = int_value(summary.get("nextRoundContent"))
    metrics = synthetic_validation_metrics(synthetic_reports)
    status = audit_item.get("status") or "unknown"
    missing: list[str] = []
    if final_run and next_count == 0:
        status = "waiting_real_data"
        missing.append("no next-round content was generated from real evidence")
        if metrics["syntheticNextRoundValidated"]:
            missing.append("synthetic/demo next-round validation exists but real evidence is still required")
    evidence = list(audit_item.get("evidence") or [])
    evidence.extend(metrics["syntheticValidationReportPaths"])
    limits = list(audit_item.get("limits") or [])
    if metrics["syntheticValidationReports"]:
        limits.extend(
            [
                "Synthetic/demo next-round recommendations are validation evidence only.",
                "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT",
            ]
        )
    return row(
        "next_round_optimization",
        status,
        evidence,
        missing or audit_item.get("missing") or [],
        ordered_unique(limits),
        metrics,
    )


def self_evolution_row(
    self_evolution: dict[str, Any],
    final_audit: dict[str, Any],
    platform_access: dict[str, Any],
) -> dict[str, Any]:
    audit_item = requirement(final_audit, "fully_autonomous_self_evolution")
    installed = self_evolution.get("installedSkill") if isinstance(self_evolution.get("installedSkill"), dict) else {}
    learning = platform_learning_metrics(self_evolution, platform_access)
    missing = list(audit_item.get("missing") or [])
    if installed.get("status") == "drift_detected":
        missing.append("installed Codex Skill is drifted from the reviewed repository")
    if learning["status"] not in FRESH_PLATFORM_LEARNING_STATUSES:
        missing.append(platform_learning_missing_message(learning["status"]))
    if learning["officialDocGapResearchStatus"] == "missing_official_doc_gap_research":
        missing.append("official platform doc gap research artifact is missing")
    elif learning["officialDocGapResearchMissingCapabilities"] > 0:
        missing.append("official platform doc gap research still has unresolved missing capabilities")
    status = audit_item.get("status") or self_evolution.get("status") or "unknown"
    if status == "blocked_by_safety_boundary":
        status = "partial_ready_review_gated_autonomy"
    elif status == "ready_review_gated_autonomy" and missing:
        status = "partial_ready_review_gated_autonomy"
    return row(
        "controlled_self_evolution",
        status,
        audit_item.get("evidence") or [],
        ordered_unique(missing),
        audit_item.get("limits") or [],
        {
            "installedSkillStatus": installed.get("status", ""),
            "syncCommand": installed.get("syncCommand", ""),
            "repositoryClean": bool((self_evolution.get("repository") or {}).get("clean")),
            "platformLearningStatus": learning["status"],
            "platformLearningLiveChecked": learning["checkLive"],
            "platformLearningReachableDocs": learning["reachableDocs"],
            "platformLearningMissingDocCapabilities": learning["missingDocCapabilities"],
            "platformLearningFailedDocs": learning["failedDocs"],
            "platformLearningCriticalFailedDocs": learning["criticalFailedDocs"],
            "platformLearningFallbackFailedDocs": learning["fallbackFailedDocs"],
            "platformLearningWarning": learning["warning"],
            "platformLearningRefreshCommand": learning["refreshCommand"],
            "officialDocGapResearchStatus": learning["officialDocGapResearchStatus"],
            "officialDocGapResearchRecords": learning["officialDocGapResearchRecords"],
            "officialDocGapResearchMissingCapabilities": learning["officialDocGapResearchMissingCapabilities"],
            "officialDocGapResearchManualFallbacks": learning["officialDocGapResearchManualFallbacks"],
            "reviewQueueTotal": int_value((self_evolution.get("reviewQueueSummary") or {}).get("total")),
            "reviewQueueRequiresApprovalOrManualReview": int_value(
                (self_evolution.get("reviewQueueSummary") or {}).get("requiresApprovalOrManualReview")
            ),
            "reviewQueueAgentExecutableNow": int_value(
                (self_evolution.get("reviewQueueSummary") or {}).get("agentExecutableNow")
            ),
        },
    )


def github_docs_row(final_audit: dict[str, Any]) -> dict[str, Any]:
    audit_item = requirement(final_audit, "github_documentation_and_install_tutorial")
    status = audit_item.get("status") or "unknown"
    return row(
        "github_documentation_and_install_tutorial",
        status,
        audit_item.get("evidence") or [],
        audit_item.get("missing") or [],
        audit_item.get("limits") or [],
    )


def browser_extension_row(final_audit: dict[str, Any]) -> dict[str, Any]:
    audit_item = requirement(final_audit, "browser_extension_operator_ui_subscription")
    status = audit_item.get("status") or "unknown"
    return row(
        "browser_extension_operator_ui_subscription",
        status,
        audit_item.get("evidence") or [],
        audit_item.get("missing") or [],
        audit_item.get("limits") or [],
    )


def phase_progress_reporting_row(final_audit: dict[str, Any]) -> dict[str, Any]:
    audit_item = requirement(final_audit, "phase_progress_reporting")
    status = audit_item.get("status") or "ready"
    if status == "unknown":
        status = "ready"
    evidence = audit_item.get("evidence") or [
        str(Path("scripts/real_run_playbook.py")),
        str(Path("scripts/skill_entry.py")),
        str(Path("scripts/final_capability_runner.py")),
        str(Path("scripts/final_capability_readiness.py")),
    ]
    metrics = {
        "requiredFields": [
            "currentStage",
            "completedGoals",
            "unfinishedGoals",
            "nextPlan",
            "estimatedRemainingTime",
        ],
        "reportArtifacts": [
            "real-run-playbook.md",
            "skill-entry.md",
            "final-capability-run.md",
            "final-capability-readiness.md",
        ],
    }
    return row(
        "phase_progress_reporting",
        status,
        evidence,
        audit_item.get("missing") or [],
        audit_item.get("limits")
        or [
            "Progress reports are generated from completed local stages and evidence paths.",
            "Estimates can change when platform authorization, app review, publishing, or real metric exports are delayed.",
        ],
        metrics,
    )


def row(
    requirement_id: str,
    status: str,
    evidence: list[Any],
    missing: list[Any],
    limits: list[Any],
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition = next(item for item in OBJECTIVE_REQUIREMENTS if item["id"] == requirement_id)
    blocked = status.startswith("blocked") or status.startswith("waiting_") or status in {"needs_real_run_evidence"}
    return {
        "id": requirement_id,
        "label": definition["label"],
        "status": status or "unknown",
        "satisfied": status
        in {
            "ready",
            "full_ready",
            "ready_with_video_evidence",
            "ready_with_full_funnel_evidence",
            "ready_review_gated_autonomy",
            "manual_package_ready_auto_ports_reserved",
        },
        "blocked": blocked,
        "evidence": [str(item) for item in evidence if item],
        "missing": [str(item) for item in missing if item],
        "limits": [str(item) for item in limits if item],
        "metrics": metrics or {},
    }


def build_action_queue(
    out_dir: Path,
    rows: list[dict[str, Any]],
    final_run: dict[str, Any],
    final_audit: dict[str, Any],
    readiness_reports: list[dict[str, Any]],
    setup_reports: list[dict[str, Any]],
    evidence_setup_reports: list[dict[str, Any]],
    self_evolution: dict[str, Any],
    platform_access: dict[str, Any],
    product_url: str,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    by_id = {item["id"]: item for item in rows}
    if by_id["product_url_codex_structured_intake"]["status"] == "needs_real_run_evidence":
        actions.append(action(10, "run_product_url_reading", "Run final capability runner on a real product URL.", final_runner_command(out_dir, product_url)))
    if by_id["viral_creator_video_research"]["status"] == "needs_real_run_evidence":
        actions.append(
            action(
                20,
                "run_multi_query_viral_discovery",
                "Run product-driven viral discovery and follow-up captures.",
                final_runner_command(out_dir, product_url) + " --run-follow-up-captures --sample-video-frames",
            )
        )
    if by_id["viral_creator_video_research"]["status"] in {
        "partial_ready_search_capture_only",
        "partial_ready_deep_content_evidence",
        "partial_ready_non_video_platform_evidence",
        "partial_ready_user_inbox_evidence",
        "partial_ready_viral_inbox_available",
    }:
        actions.append(
            action(
                21,
                "run_video_evidence_capture",
                "Run multi-query viral discovery with follow-up captures and browser-visible video frame sampling.",
                final_runner_command(out_dir, product_url) + " --multi-query-run-follow-up-captures --multi-query-sample-video-frames",
            )
        )
    if by_id["viral_creator_video_research"]["status"] in {
        "needs_real_run_evidence",
        "partial_ready_search_capture_only",
        "partial_ready_deep_content_evidence",
        "partial_ready_non_video_platform_evidence",
        "partial_ready_user_inbox_evidence",
        "partial_ready_viral_inbox_available",
    }:
        viral_metrics = by_id["viral_creator_video_research"]["metrics"]
        if int_value(viral_metrics.get("viralInboxSetupReports")) == 0:
            actions.append(
                action(
                    23,
                    "setup_viral_evidence_inbox",
                    "Create a fillable inbox for real competitor/viral material evidence when public platform automation is incomplete.",
                    f"python scripts/viral_evidence_inbox_setup.py --product-url \"{product_url}\" --platforms youtube,zhihu,xiaohongshu,douyin,github --inbox-dir \"./viral-evidence-inbox\" --out-dir \"{out_dir}\"",
                )
            )
        actions.append(
            action(
                24,
                "import_viral_evidence_inbox",
                "Import user-provided competitor URLs, visible text, transcripts, exports, or OCR text into the viral library.",
                f"python scripts/viral_evidence_inbox.py --inbox-dir \"./viral-evidence-inbox\" --out-dir \"{out_dir}\"",
            )
        )
    missing_video_platforms = by_id["viral_creator_video_research"]["metrics"].get("missingVideoPlatformEvidence") or []
    if missing_video_platforms:
        actions.append(
            action(
                22,
                "capture_missing_video_platform_evidence",
                "Rerun viral discovery scoped to requested video platforms that produced no captured material or video samples.",
                video_platform_runner_command(out_dir, missing_video_platforms, product_url),
            )
        )
    if "no MP4 generated" in " ".join(by_id["copy_and_real_video_generation"]["missing"]):
        actions.append(action(30, "render_video", "Run without --skip-video or provide a voiceover file for MP4 rendering.", final_runner_command(out_dir, product_url)))
    publish_status = by_id["official_or_browser_assisted_publish"]["status"]
    if publish_status.startswith("partial_ready") or publish_status == "manual_package_ready_auto_ports_reserved":
        actions.extend(publish_actions(out_dir, readiness_reports, setup_reports))
        actions.append(
            action(
                41,
                "build_launch_unlock_pack",
                "Build one setup pack for platform access, publish setup, browser-assisted publishing, and real evidence collection.",
                launch_unlock_command(out_dir),
            )
        )
    if publish_status.startswith("blocked") and not readiness_reports:
        actions.append(
            action(
                40,
                "build_publish_readiness_after_workflow",
                "After a real workflow manifest exists, build the guarded publish queue and setup kit.",
                (
                    f"python scripts/publish_readiness_runner.py --workflow-manifest "
                    f"\"{out_dir}/reports/promotion-manager/agent-run/workflow-manifest.json\" "
                    f"--build-queue --github-repo owner/repo --youtube-video-file \"{out_dir}/videos/product-youtube.mp4\" "
                    f"--douyin-video-file \"{out_dir}/videos/product-douyin.mp4\" --out-dir \"{out_dir}\""
                ),
            )
        )
        actions.append(
            action(
                41,
                "build_launch_unlock_pack",
                "After the publish queue exists, build one setup pack for platform access, publishing gates, and real evidence collection.",
                launch_unlock_command(out_dir),
            )
        )
    metrics_status = by_id["real_metrics_comments_orders_revenue"]["status"]
    if metrics_status.startswith("waiting_real_data"):
        evidence_setup_targets = sum(
            evidence_setup_target_count(report) for report in evidence_setup_reports if isinstance(report, dict)
        )
        if not evidence_setup_targets:
            actions.append(
                action(
                    57,
                    "setup_real_evidence_inbox",
                    "Create a fillable local evidence inbox before or immediately after publishing.",
                    f"python scripts/real_evidence_inbox_setup.py --product-url \"{product_url}\" --platforms youtube,zhihu,xiaohongshu,douyin,github --inbox-dir \"./promotion-evidence-inbox\" --out-dir \"{out_dir}\"",
                )
            )
            actions.append(
                action(
                    59,
                    "build_real_evidence_setup",
                    "Generate platform metrics, comment, published URL, and business attribution templates before collecting real data.",
                    f"python scripts/real_evidence_setup.py --publish-queue \"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" --out-dir \"{out_dir}\"",
                )
            )
            actions.append(
                action(
                    58,
                    "build_launch_unlock_pack",
                    "Build the launch unlock pack before collecting real published URL, metric, comment, order, and revenue evidence.",
                    launch_unlock_command(out_dir),
                )
            )
        metrics = by_id["real_metrics_comments_orders_revenue"]["metrics"]
        if not metrics.get("syntheticValidationReady"):
            actions.append(
                action(
                    63,
                    "run_synthetic_evidence_validation",
                    "Generate clearly marked synthetic/demo evidence to validate the retrospective loop without treating it as real performance.",
                    f"python scripts/synthetic_evidence_generator.py --product-url \"{product_url}\" --platforms youtube,zhihu,xiaohongshu,douyin,github --run-recovery --out-dir \"{out_dir}/synthetic-validation\"",
                )
            )
        actions.append(
            action(
                60,
                "monitor_post_publish_performance",
                "Run the post-publish monitor to capture public metrics, comments, business attribution, recovery, and next-round recommendations.",
                f"python scripts/performance_monitor.py --out-dir \"{out_dir}\"",
            )
        )
        actions.append(
            action(
                61,
                "import_real_evidence_inbox",
                "Import a local folder of published URLs, platform metrics, comments, orders, and revenue evidence.",
                f"python scripts/real_evidence_inbox.py --inbox-dir \"./promotion-evidence-inbox\" --out-dir \"{out_dir}\"",
            )
        )
        actions.append(
            action(
                62,
                "register_real_published_urls",
                "Register real published URLs or evidence before metrics recovery.",
                f"python scripts/published_items.py --platform xiaohongshu --published-url \"https://...\" --evidence \"./screenshots/published.png\" --out-dir \"{out_dir}\"",
            )
        )
        actions.append(
            action(
                63,
                "import_business_exports",
                "Provide business exports with URL, UTM, content id, orders, revenue, clicks, or leads.",
                f"python scripts/business_attribution.py --business-csv \"./orders-and-revenue.csv\" --out-dir \"{out_dir}\"",
            )
        )
    elif metrics_status.startswith("partial_ready"):
        missing_text = " ".join(by_id["real_metrics_comments_orders_revenue"]["missing"])
        if any(word in missing_text for word in ["view", "like", "comment"]):
            actions.append(
                action(
                    60,
                    "monitor_post_publish_performance",
                    "Run the post-publish monitor to capture public metrics/comments, merge exports, and generate next-round recommendations.",
                    f"python scripts/performance_monitor.py --out-dir \"{out_dir}\"",
                )
            )
            actions.append(
                action(
                    61,
                    "import_real_evidence_inbox",
                    "Import a local evidence folder when several metric, comment, and business files already exist.",
                    f"python scripts/real_evidence_inbox.py --inbox-dir \"./promotion-evidence-inbox\" --out-dir \"{out_dir}\"",
                )
            )
            actions.append(
                action(
                    62,
                    "capture_missing_social_evidence",
                    "Capture public/browser-visible published page metrics and comments for the missing social evidence fields.",
                    f"python scripts/post_publish_metrics_capture.py --out-dir \"{out_dir}\"",
                )
            )
            actions.append(
                action(
                    63,
                    "capture_missing_comment_evidence",
                    "Capture public/browser-visible comments or queue manual comment evidence.",
                    f"python scripts/comment_evidence_capture.py --out-dir \"{out_dir}\"",
                )
            )
        if any(word in missing_text for word in ["order", "revenue"]):
            actions.append(
                action(
                    62,
                    "import_missing_business_evidence",
                    "Import business exports with orders and revenue matched to published URLs, UTM content, or campaign/title evidence.",
                    f"python scripts/business_attribution.py --business-csv \"./orders-and-revenue.csv\" --out-dir \"{out_dir}\"",
                )
            )
    if by_id["next_round_optimization"]["status"] == "waiting_real_data":
        actions.append(
            action(
                70,
                "optimize_after_real_evidence",
                "Run next-round optimization after metrics, comments, or business attribution exist.",
                f"python scripts/next_round_optimizer.py --metrics-recovery-json \"{out_dir}/reports/promotion-manager/metrics-recovery/metrics-recovery.json\" --out-dir \"{out_dir}\"",
            )
        )
    installed = self_evolution.get("installedSkill") if isinstance(self_evolution.get("installedSkill"), dict) else {}
    learning = platform_learning_metrics(self_evolution, platform_access)
    if learning["status"] not in FRESH_PLATFORM_LEARNING_STATUSES:
        action_id = "refresh_platform_access_docs"
        description = "Refresh official platform publishing and metrics documentation before changing direct publishing executors."
        if learning["status"] == "partial_missing_official_doc_sources":
            action_id = "resolve_missing_official_doc_sources"
            description = "Add verified official doc sources for missing platform capabilities, or keep those capabilities manual/browser-assisted."
        actions.append(
            action(
                79,
                action_id,
                description,
                learning["refreshCommand"],
            )
        )
    if installed.get("status") == "drift_detected":
        actions.append(
            action(
                80,
                "sync_installed_skill_when_approved",
                "Sync reviewed repository files into the installed Codex Skill after explicit approval.",
                installed.get("syncCommand") or "python scripts/self_evolution_audit.py --sync-installed-skill --approval I_APPROVE_SKILL_SYNC --out-dir \"./promotion-output\"",
                approval="I_APPROVE_SKILL_SYNC",
            )
        )
    if by_id["github_documentation_and_install_tutorial"]["status"] != "ready":
        actions.append(
            action(
                82,
                "complete_github_docs",
                "Update README and docs so GitHub users can install, run, price, and understand the final capability boundaries.",
                "review README.md docs/installation.md docs/usage.md docs/browser-extension.md docs/extension-store-submission.md docs/subscription-pricing.md docs/final-capability-map.md",
            )
        )
    if by_id["browser_extension_operator_ui_subscription"]["status"] != "ready":
        actions.append(
            action(
                83,
                "complete_browser_extension",
                "Complete the Chrome MV3 extension files, packaged icons, submission zip, subscription/license UI evidence, and listing guide.",
                "python scripts/package_browser_extension.py --out-dir \"./dist\"",
            )
        )
    elif not (out_dir / "reports/promotion-manager/billing-simulator/billing-simulator.json").exists():
        actions.append(
            action(
                84,
                "validate_billing_contract_simulator",
                "Run the local billing contract simulator to verify license, quota, usage, and webhook behavior before deploying a paid backend.",
                f"python scripts/billing_contract_simulator.py demo --plan growth --workflow-type research_run --out-dir \"{out_dir}\"",
            )
        )
    for item in final_audit.get("nextActions", []) if isinstance(final_audit.get("nextActions"), list) else []:
        if isinstance(item, dict) and item.get("command"):
            actions.append(action(90 + int_value(item.get("priority")), str(item.get("area", "audit_next_action")), str(item.get("action", "")), str(item.get("command", ""))))
    return dedupe_actions(sorted(actions, key=lambda item: item["priority"]))


def publish_actions(out_dir: Path, readiness_reports: list[dict[str, Any]], setup_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for report in setup_reports:
        for record in list_records(report, "records"):
            commands = record.get("commands") if isinstance(record.get("commands"), dict) else {}
            category = record.get("setupCategory", "")
            platform = record.get("platform", "")
            if commands.get("rerunReadiness"):
                actions.append(action(40, f"rerun_{platform}_publish_readiness", f"Rerun {platform} publish readiness after setup changes.", commands["rerunReadiness"]))
            if commands.get("executeWhenReady") and category in {"execution_approval_required", "ready_to_execute", "credential_setup_required"}:
                actions.append(action(50, f"execute_{platform}_when_approved", f"Execute {platform} only after credentials, target, and approval are ready.", commands["executeWhenReady"], approval="I_APPROVE_PUBLISH"))
            if commands.get("prepareBrowserPublish"):
                actions.append(action(51, f"prepare_{platform}_browser_publish", f"Prepare browser/manual publish payloads for {platform}.", commands["prepareBrowserPublish"]))
                actions.append(
                    action(
                        52,
                        f"run_{platform}_browser_publish_session",
                        f"Run a browser-assisted publish session for {platform}, fill visible fields where possible, and stop before final publish.",
                        browser_publish_session_command(commands["prepareBrowserPublish"]),
                    )
                )
    if not actions and readiness_reports:
        actions.append(action(40, "build_publish_setup_kit", "Build publish setup kit from readiness reports.", f"python scripts/publish_setup_assistant.py --out-dir \"{out_dir}\""))
    return actions


def browser_publish_session_command(prepare_command: str) -> str:
    command = prepare_command.replace("browser_publish_assistant.py", "browser_publish_session.py")
    if "--run-form-fill" not in command:
        command = f"{command} --run-form-fill"
    return command


def launch_unlock_command(out_dir: Path) -> str:
    return (
        f"python scripts/launch_unlock_pack.py --publish-queue "
        f"\"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" "
        f"--publish-readiness \"{out_dir}/reports/promotion-manager/publish-readiness/publish-readiness.json\" "
        f"--out-dir \"{out_dir}\""
    )


def action(priority: int, action_id: str, description: str, command: str, approval: str = "") -> dict[str, Any]:
    return {
        "priority": priority,
        "id": action_id,
        "description": description,
        "command": command,
        "approvalRequired": approval,
    }


def summarize(rows: list[dict[str, Any]], actions: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "requirements": len(rows),
        "satisfied": sum(1 for item in rows if item["satisfied"]),
        "blockedOrWaiting": sum(1 for item in rows if item["blocked"]),
        "partial": sum(1 for item in rows if item["status"].startswith("partial")),
        "actions": len(actions),
        "approvalActions": sum(1 for item in actions if item.get("approvalRequired")),
    }
    return summary


def final_status(rows: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in rows}
    if all(item["satisfied"] for item in rows):
        return "full_ready"
    if any(status.startswith("blocked") for status in statuses):
        return "partial_ready_blocked_by_platform_or_safety_limits"
    if any(status.startswith("waiting_") or status == "needs_real_run_evidence" for status in statuses):
        return "partial_ready_waiting_external_evidence"
    return "partial_ready"


def platform_matrix(final_audit: dict[str, Any], readiness_reports: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = {}
    platforms = final_audit.get("platforms") if isinstance(final_audit.get("platforms"), dict) else {}
    for platform, info in platforms.items():
        matrix[platform] = dict(info) if isinstance(info, dict) else {"status": info}
    for report in readiness_reports:
        for record in list_records(report, "records"):
            platform = str(record.get("platform") or "")
            if not platform:
                continue
            matrix.setdefault(platform, {})
            matrix[platform]["publishReadiness"] = record.get("readiness", "")
            matrix[platform]["publishMode"] = record.get("publishMode", "")
    return matrix


def external_gates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for item in rows:
        if item["missing"] or item["limits"]:
            gates.append(
                {
                    "requirement": item["id"],
                    "status": item["status"],
                    "missing": item["missing"],
                    "limits": item["limits"],
                }
            )
    return gates


def operating_sequence(out_dir: Path, product_url: str) -> list[dict[str, str]]:
    return [
        {
            "step": "prepare_real_run_playbook",
            "command": f"python scripts/real_run_playbook.py --url \"{product_url}\" --platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\"",
        },
        {
            "step": "run_final_capability",
            "command": final_runner_command(out_dir, product_url),
        },
        {
            "step": "setup_viral_evidence_inbox_if_needed",
            "command": f"python scripts/viral_evidence_inbox_setup.py --product-url \"{product_url}\" --platforms youtube,zhihu,xiaohongshu,douyin,github --inbox-dir \"./viral-evidence-inbox\" --out-dir \"{out_dir}\"",
        },
        {
            "step": "import_viral_evidence_inbox",
            "command": f"python scripts/viral_evidence_inbox.py --inbox-dir \"./viral-evidence-inbox\" --out-dir \"{out_dir}\"",
        },
        {
            "step": "review_readiness_matrix",
            "command": f"python scripts/final_capability_readiness.py --out-dir \"{out_dir}\"",
        },
        {
            "step": "prepare_publish_setup",
            "command": f"python scripts/publish_setup_assistant.py --out-dir \"{out_dir}\"",
        },
        {
            "step": "build_launch_unlock_pack",
            "command": launch_unlock_command(out_dir),
        },
        {
            "step": "prepare_browser_publish",
            "command": f"python scripts/browser_publish_assistant.py --publish-queue \"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" --out-dir \"{out_dir}\"",
        },
        {
            "step": "run_browser_publish_session",
            "command": f"python scripts/browser_publish_session.py --publish-queue \"{out_dir}/reports/promotion-manager/publish-queue/publish-queue.json\" --run-form-fill --out-dir \"{out_dir}\"",
        },
        {
            "step": "recover_real_metrics",
            "command": f"python scripts/performance_monitor.py --out-dir \"{out_dir}\"",
        },
        {
            "step": "optimize_next_round",
            "command": f"python scripts/next_round_optimizer.py --metrics-recovery-json \"{out_dir}/reports/promotion-manager/metrics-recovery/metrics-recovery.json\" --out-dir \"{out_dir}\"",
        },
    ]


def final_runner_command(out_dir: Path, product_url: str = DEFAULT_PRODUCT_URL) -> str:
    return (
        f"python scripts/final_capability_runner.py --url \"{product_url}\" "
        "--platforms youtube,zhihu,xiaohongshu,douyin,github --run-follow-up-captures "
        "--sample-video-frames --business-csv \"./orders-and-revenue.csv\" "
        f"--out-dir \"{out_dir}\""
    )


def video_platform_runner_command(out_dir: Path, platforms: list[str], product_url: str = DEFAULT_PRODUCT_URL) -> str:
    platform_arg = ",".join(platforms)
    return (
        f"python scripts/final_capability_runner.py --url \"{product_url}\" "
        f"--platforms {platform_arg} --run-follow-up-captures --capture-browser-assisted-follow-ups "
        "--sample-video-frames --video-sample-count 2 --top-n 5 "
        "--timeout-ms 15000 --wait-until domcontentloaded "
        "--multi-query-query-count 1 --multi-query-top-n 5 --multi-query-run-follow-up-captures "
        "--multi-query-browser-search-timeout-ms 15000 --multi-query-browser-search-wait-until domcontentloaded "
        "--multi-query-capture-browser-assisted-follow-ups --multi-query-sample-video-frames "
        f"--multi-query-video-sample-count 2 --video-platforms {platform_arg} --out-dir \"{out_dir}\""
    )


def source_report_summary(sources: dict[str, Any]) -> dict[str, Any]:
    return {
        "finalRun": report_source(sources.get("finalRunPath")),
        "finalAudit": report_source(sources.get("finalAuditPath")),
        "platformAccess": report_source(sources.get("platformAccessPath")),
        "selfEvolution": report_source(sources.get("selfEvolutionPath")),
        "publishReadiness": [report_source(path) for path in sources.get("publishReadinessPaths", [])],
        "publishSetup": [report_source(path) for path in sources.get("publishSetupPaths", [])],
        "realEvidenceSetup": [report_source(path) for path in sources.get("realEvidenceSetupPaths", [])],
        "realEvidenceInboxSetup": [report_source(path) for path in sources.get("realEvidenceInboxSetupPaths", [])],
        "viralEvidenceInboxSetup": [report_source(path) for path in sources.get("viralEvidenceInboxSetupPaths", [])],
        "viralEvidenceInbox": [report_source(path) for path in sources.get("viralEvidenceInboxPaths", [])],
        "launchUnlock": [report_source(path) for path in sources.get("launchUnlockPaths", [])],
        "syntheticEvidence": [report_source(path) for path in sources.get("syntheticEvidencePaths", [])],
    }


def report_source(path: Path | None) -> dict[str, Any]:
    return {"path": str(path) if path else "", "exists": bool(path and path.exists())}


def product_url_from_final_run(final_run: dict[str, Any]) -> str:
    input_payload = final_run.get("input") if isinstance(final_run.get("input"), dict) else {}
    for value in [
        first_text(input_payload.get("urls")),
        input_payload.get("url"),
        input_payload.get("link"),
        input_payload.get("browserUrl"),
        input_payload.get("discoverFromUrl"),
    ]:
        text = first_text(value)
        if text:
            return text

    product_batch = final_run.get("productBatch") if isinstance(final_run.get("productBatch"), dict) else {}
    for run in list_records(product_batch, "promotionRuns"):
        text = first_text(run.get("url"))
        if text:
            return text

    for item in list_records(final_run, "cycleEvidence"):
        text = first_text(item.get("url"))
        if text:
            return text
        product = item.get("product") if isinstance(item.get("product"), dict) else {}
        text = first_text(product.get("canonicalUrl"))
        if text:
            return text

    return DEFAULT_PRODUCT_URL


def first_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            text = first_text(item)
            if text:
                return text
    return ""


def requirement(final_audit: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for item in final_audit.get("requirements", []) if isinstance(final_audit.get("requirements"), list) else []:
        if isinstance(item, dict) and item.get("id") == requirement_id:
            return item
    return {"id": requirement_id, "status": "unknown", "missing": ["final capability audit requirement missing"]}


def list_records(report: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [item for item in report.get(key, []) if isinstance(item, dict)] if isinstance(report, dict) else []


def real_evidence_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    counts = {
        "capturedMetricRecords": int_value(summary.get("capturedMetricRecords")),
        "recordsWithMetrics": int_value(summary.get("recordsWithMetrics")),
        "commentCount": int_value(summary.get("commentCount")),
        "matchedBusinessRows": int_value(summary.get("matchedBusinessRows")),
        "viewsEvidenceRecords": int_value(summary.get("viewsEvidenceRecords")),
        "likesEvidenceRecords": int_value(summary.get("likesEvidenceRecords")),
        "favoritesEvidenceRecords": int_value(summary.get("favoritesEvidenceRecords")),
        "commentsEvidenceRecords": max(
            int_value(summary.get("commentsEvidenceRecords")),
            int_value(summary.get("commentCount")),
        ),
        "sharesEvidenceRecords": int_value(summary.get("sharesEvidenceRecords")),
        "clicksEvidenceRecords": int_value(summary.get("clicksEvidenceRecords")),
        "messagesEvidenceRecords": int_value(summary.get("messagesEvidenceRecords")),
        "leadsEvidenceRecords": int_value(summary.get("leadsEvidenceRecords")),
        "ordersEvidenceRecords": int_value(summary.get("ordersEvidenceRecords")),
        "revenueEvidenceRecords": int_value(summary.get("revenueEvidenceRecords")),
    }
    has_views = counts["viewsEvidenceRecords"] > 0
    has_likes = counts["likesEvidenceRecords"] > 0
    has_comments = counts["commentsEvidenceRecords"] > 0
    has_orders = counts["ordersEvidenceRecords"] > 0
    has_revenue = counts["revenueEvidenceRecords"] > 0
    evidence_count = (
        counts["capturedMetricRecords"]
        + counts["recordsWithMetrics"]
        + counts["commentCount"]
        + counts["matchedBusinessRows"]
        + counts["viewsEvidenceRecords"]
        + counts["likesEvidenceRecords"]
        + counts["commentsEvidenceRecords"]
        + counts["ordersEvidenceRecords"]
        + counts["revenueEvidenceRecords"]
    )
    return {
        **counts,
        "evidenceCount": evidence_count,
        "hasViewsEvidence": has_views,
        "hasLikesEvidence": has_likes,
        "hasCommentsEvidence": has_comments,
        "hasOrdersEvidence": has_orders,
        "hasRevenueEvidence": has_revenue,
        "hasAnySocialOrCommentEvidence": has_views or has_likes or has_comments or counts["favoritesEvidenceRecords"] > 0 or counts["sharesEvidenceRecords"] > 0,
        "hasAnyBusinessEvidence": has_orders or has_revenue,
        "hasFullFunnelEvidence": has_views and has_likes and has_comments and has_orders and has_revenue,
    }


def synthetic_validation_metrics(reports: list[dict[str, Any]]) -> dict[str, Any]:
    valid_reports = [
        report
        for report in reports
        if isinstance(report, dict)
        and report.get("synthetic") is True
        and report.get("warning") == "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT"
    ]
    ready_reports = 0
    recovery_validated = 0
    next_round_validated = 0
    metric_rows = 0
    comment_lines = 0
    business_rows = 0
    platforms: list[str] = []
    report_paths: list[str] = []
    for report in valid_reports:
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        recovery = report.get("recovery") if isinstance(report.get("recovery"), dict) else {}
        recovery_reports = recovery.get("reports") if isinstance(recovery.get("reports"), dict) else {}
        ready = report.get("status") == "synthetic_validation_ready"
        recovery_ok = int_value(summary.get("recoveryExitCode") if "recoveryExitCode" in summary else recovery.get("exitCode")) == 0
        next_round_ok = bool(recovery_reports.get("nextRoundOptimization"))
        ready_reports += int(ready)
        recovery_validated += int(ready and recovery_ok)
        next_round_validated += int(ready and recovery_ok and next_round_ok)
        metric_rows += int_value(summary.get("metricRows"))
        comment_lines += int_value(summary.get("commentLines"))
        business_rows += int_value(summary.get("businessRows"))
        input_payload = report.get("input") if isinstance(report.get("input"), dict) else {}
        platforms.extend(split_platform_values(input_payload.get("platforms")))
        if report.get("_sourcePath"):
            report_paths.append(str(report["_sourcePath"]))
    return {
        "syntheticValidationReports": len(valid_reports),
        "syntheticValidationReadyReports": ready_reports,
        "syntheticValidationReady": ready_reports > 0,
        "syntheticRecoveryValidated": recovery_validated > 0,
        "syntheticNextRoundValidated": next_round_validated > 0,
        "syntheticValidationMetricRows": metric_rows,
        "syntheticValidationCommentLines": comment_lines,
        "syntheticValidationBusinessRows": business_rows,
        "syntheticValidationPlatforms": sorted(set(platforms)),
        "syntheticValidationWarning": "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT" if valid_reports else "",
        "syntheticValidationReportPaths": ordered_unique(report_paths),
    }


def viral_inbox_metrics(setup_reports: list[dict[str, Any]], inbox_reports: list[dict[str, Any]]) -> dict[str, Any]:
    imported_records = 0
    capture_reports = 0
    imported_sources = 0
    screenshot_needing_text = 0
    setup_files = 0
    setup_platforms = 0
    platforms: list[str] = []
    library_ready = False
    creator_leaderboard_ready = False
    for report in setup_reports:
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        setup_files += int_value(summary.get("filesPrepared"))
        setup_platforms += int_value(summary.get("platforms"))
    for report in inbox_reports:
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        imported_records += int_value(summary.get("records"))
        capture_reports += int_value(summary.get("captureReports"))
        imported_sources += int_value(summary.get("importedSources"))
        screenshot_needing_text += int_value(summary.get("screenshotEvidenceNeedingText"))
        platforms.extend(split_platform_values(summary.get("platforms")))
        library_ready = library_ready or bool(summary.get("libraryReady"))
        creator_leaderboard_ready = creator_leaderboard_ready or bool(summary.get("creatorLeaderboardReady"))
    return {
        "viralInboxSetupReports": len(setup_reports),
        "viralInboxImportReports": len(inbox_reports),
        "viralInboxSetupFiles": setup_files,
        "viralInboxSetupPlatforms": setup_platforms,
        "viralInboxImportedSources": imported_sources,
        "viralInboxImportedRecords": imported_records,
        "viralInboxCaptureReports": capture_reports,
        "viralInboxScreenshotEvidenceNeedingText": screenshot_needing_text,
        "viralInboxPlatforms": sorted(set(platforms)),
        "viralInboxLibraryReady": library_ready,
        "viralInboxCreatorLeaderboardReady": creator_leaderboard_ready,
    }


def platform_learning_metrics(self_evolution: dict[str, Any], platform_access: dict[str, Any]) -> dict[str, Any]:
    learning = self_evolution.get("platformLearning") if isinstance(self_evolution.get("platformLearning"), dict) else {}
    freshness = platform_access.get("learningFreshness") if isinstance(platform_access.get("learningFreshness"), dict) else {}
    doc_summary = platform_access.get("officialDocSummary") if isinstance(platform_access.get("officialDocSummary"), dict) else {}
    gap_research = platform_access.get("officialDocGapResearch") if isinstance(platform_access.get("officialDocGapResearch"), dict) else {}
    gap_summary = gap_research.get("summary") if isinstance(gap_research.get("summary"), dict) else {}
    check_live = bool(learning.get("checkLive") or freshness.get("checkLive") or platform_access.get("checkLive"))
    status = str(freshness.get("status") or learning.get("status") or "")
    if not status:
        status = "fresh_live_checked" if platform_access.get("checkLive") else "missing_platform_access_audit"
    return {
        "status": status,
        "checkLive": check_live,
        "reachableDocs": int_value(learning.get("reachableDocs") or freshness.get("reachableDocs") or doc_summary.get("reachableDocs")),
        "missingDocCapabilities": int_value(
            learning.get("missingDocCapabilities")
            or freshness.get("missingDocCapabilities")
            or doc_summary.get("missingDocCapabilities")
        ),
        "failedDocs": int_value(learning.get("failedDocs") or freshness.get("failedDocs")),
        "criticalFailedDocs": int_value(
            learning.get("criticalFailedDocs")
            or freshness.get("criticalFailedDocs")
            or doc_summary.get("criticalFailedDocs")
        ),
        "fallbackFailedDocs": int_value(
            learning.get("fallbackFailedDocs")
            or freshness.get("fallbackFailedDocs")
            or doc_summary.get("fallbackFailedDocs")
        ),
        "warning": str(learning.get("warning") or freshness.get("warning") or ""),
        "refreshCommand": str(
            learning.get("refreshCommand")
            or freshness.get("refreshCommand")
            or "python scripts/platform_access_audit.py --check-live --out-dir \"./promotion-output\""
        ),
        "officialDocGapResearchStatus": str(gap_research.get("status") or "missing_official_doc_gap_research"),
        "officialDocGapResearchRecords": int_value(gap_summary.get("records")),
        "officialDocGapResearchMissingCapabilities": int_value(gap_summary.get("missingOfficialDocCapabilities")),
        "officialDocGapResearchManualFallbacks": int_value(gap_summary.get("manualOrBrowserFallbacks")),
    }


def platform_learning_missing_message(status: str) -> str:
    if status == "partial_missing_official_doc_sources":
        return "some platform capabilities have no verified official doc source"
    if status == "partial_live_check_failed":
        return "some official platform documentation live checks failed"
    if status == "fresh_live_checked_with_warnings":
        return "official platform access docs are freshly live-checked with non-critical fallback warnings"
    if status in {"stale_not_live_checked", "missing_platform_access_audit", "invalid_platform_access_audit"}:
        return "official platform access docs are not freshly live-checked"
    return "official platform access learning evidence is incomplete"


def first_existing(values: list[Any]) -> Path | None:
    for value in values:
        if not value:
            continue
        path = Path(value)
        if path.exists():
            return path
    return None


def explicit_existing(values: list[str]) -> list[Path]:
    return [Path(value) for value in values if value and Path(value).exists()]


def explicit_or_discovered(values: list[str], base: Path, *patterns: str) -> list[Path]:
    explicit = explicit_existing(values)
    if explicit:
        return unique_paths(explicit)
    discovered: list[Path] = []
    for pattern in patterns:
        discovered.extend(glob_existing(base, pattern))
    return unique_paths(discovered)


def glob_existing(base: Path, pattern: str) -> list[Path]:
    return sorted(path for path in base.glob(pattern) if path.exists())


def unique_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve())
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_json_with_source(path: Path | None) -> dict[str, Any]:
    payload = read_json(path)
    if payload and path:
        payload["_sourcePath"] = str(path)
    return payload


def ordered_unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in actions:
        key = (str(item.get("id", "")), str(item.get("command", "")))
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def requested_platforms(final_run: dict[str, Any]) -> list[str]:
    input_payload = final_run.get("input") if isinstance(final_run.get("input"), dict) else {}
    platforms = split_platform_values(input_payload.get("platforms"))
    if platforms:
        return platforms
    product_batch = final_run.get("productBatch") if isinstance(final_run.get("productBatch"), dict) else {}
    return split_platform_values(product_batch.get("platforms"))


def observed_multi_query_platforms(final_run: dict[str, Any]) -> set[str]:
    platforms: set[str] = set()
    product_batch = final_run.get("productBatch") if isinstance(final_run.get("productBatch"), dict) else {}
    for run in list_records(product_batch, "promotionRuns"):
        discovery = run.get("multiQueryViralDiscovery") if isinstance(run, dict) else {}
        if isinstance(discovery, dict):
            summary = discovery.get("summary") if isinstance(discovery.get("summary"), dict) else {}
            platforms.update(split_platform_values(summary.get("platforms")))
    for item in list_records(final_run, "cycleEvidence"):
        research = item.get("competitorResearch") if isinstance(item, dict) else {}
        discovery = research.get("multiQueryViralDiscovery") if isinstance(research, dict) else {}
        if isinstance(discovery, dict):
            summary = discovery.get("summary") if isinstance(discovery.get("summary"), dict) else {}
            platforms.update(split_platform_values(summary.get("platforms")))
    return platforms


def split_platform_values(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, list):
        raw_values = value
    else:
        raw_values = []
    return ordered_unique([str(item).strip().lower() for item in raw_values if str(item).strip()])


def evidence_setup_target_count(report: dict[str, Any]) -> int:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return max(int_value(summary.get("targets")), int_value(summary.get("platforms")))


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "final-capability-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / "final-capability-readiness.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final Capability Readiness",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Output: {report['outDir']}",
        "",
        "## Requirements",
    ]
    for item in report["requirements"]:
        lines.append(f"- `{item['id']}`: `{item['status']}` - {item['label']}")
        if item.get("missing"):
            lines.append(f"  Missing: {', '.join(item['missing'])}")
        if item["id"] == "real_metrics_comments_orders_revenue" and item.get("metrics"):
            metrics = item["metrics"]
            lines.append(
                "  Evidence fields: "
                f"views={metrics.get('viewsEvidenceRecords', 0)}, "
                f"likes={metrics.get('likesEvidenceRecords', 0)}, "
                f"comments={metrics.get('commentsEvidenceRecords', 0)}, "
                f"orders={metrics.get('ordersEvidenceRecords', 0)}, "
                f"revenue={metrics.get('revenueEvidenceRecords', 0)}, "
                f"evidenceTemplates={metrics.get('realEvidenceSetupTargets', 0)}"
            )
            if metrics.get("syntheticValidationReports"):
                lines.append(
                    "  Synthetic validation: "
                    f"ready={metrics.get('syntheticValidationReady', False)}, "
                    f"recovery={metrics.get('syntheticRecoveryValidated', False)}, "
                    f"nextRound={metrics.get('syntheticNextRoundValidated', False)}, "
                    f"metricRows={metrics.get('syntheticValidationMetricRows', 0)}, "
                    f"commentLines={metrics.get('syntheticValidationCommentLines', 0)}, "
                    f"businessRows={metrics.get('syntheticValidationBusinessRows', 0)}, "
                    f"warning={metrics.get('syntheticValidationWarning', '')}"
                )
        if item["id"] == "next_round_optimization" and item.get("metrics"):
            metrics = item["metrics"]
            if metrics.get("syntheticValidationReports"):
                lines.append(
                    "  Synthetic next-round validation: "
                    f"ready={metrics.get('syntheticValidationReady', False)}, "
                    f"nextRound={metrics.get('syntheticNextRoundValidated', False)}, "
                    f"warning={metrics.get('syntheticValidationWarning', '')}"
                )
        if item["id"] == "controlled_self_evolution" and item.get("metrics"):
            metrics = item["metrics"]
            lines.append(
                "  Platform learning: "
                f"status={metrics.get('platformLearningStatus', '')}, "
                f"liveChecked={metrics.get('platformLearningLiveChecked', False)}, "
                f"reachableDocs={metrics.get('platformLearningReachableDocs', 0)}, "
                f"gapResearch={metrics.get('officialDocGapResearchStatus', '')}, "
                f"gapRecords={metrics.get('officialDocGapResearchRecords', 0)}"
            )
        if item["id"] == "phase_progress_reporting" and item.get("metrics"):
            metrics = item["metrics"]
            lines.append(f"  Required fields: {', '.join(metrics.get('requiredFields', []))}")
    lines.extend(["", "## Action Queue"])
    for item in report["actionQueue"]:
        approval = f" approval=`{item['approvalRequired']}`" if item.get("approvalRequired") else ""
        lines.append(f"- P{item['priority']} `{item['id']}`{approval}: {item['description']}")
        lines.append(f"  Command: `{item['command']}`")
    lines.extend(["", "## Platform Matrix"])
    for platform, info in report["platformMatrix"].items():
        lines.append(f"- {platform}: {json.dumps(info, ensure_ascii=False, sort_keys=True)}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/final-readiness"


if __name__ == "__main__":
    main()
