#!/usr/bin/env python3
"""Generate clearly marked synthetic evidence for validating the recovery loop."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import metric_parsing


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]
SYNTHETIC_EVIDENCE = "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    inbox_dir = Path(args.inbox_dir) if args.inbox_dir else out_dir / "synthetic-evidence-inbox"
    platforms = split_csv(args.platforms) or DEFAULT_PLATFORMS
    product_name = args.product_name or product_name_from_url(args.product_url)
    records = build_records(platforms, args.product_url, product_name)
    artifacts = write_inbox(inbox_dir, records, args.product_url, product_name)
    recovery = run_recovery(args, out_dir, inbox_dir) if args.run_recovery else {}
    report = build_report(args, out_dir, inbox_dir, records, artifacts, recovery)
    write_report(out_dir, report)
    print(f"Synthetic evidence report written to: {(report_dir(out_dir) / 'synthetic-evidence.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create synthetic/demo evidence to validate the retrospective pipeline.")
    parser.add_argument("--product-url", default="https://example.com/product")
    parser.add_argument("--product-name", default="")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS))
    parser.add_argument("--inbox-dir", default="", help="Defaults to <out-dir>/synthetic-evidence-inbox.")
    parser.add_argument("--out-dir", default="./promotion-output/synthetic-validation")
    parser.add_argument("--run-recovery", action="store_true", help="Run real_evidence_inbox.py against the synthetic inbox.")
    return parser.parse_args()


def build_records(platforms: list[str], product_url: str, product_name: str) -> list[dict[str, Any]]:
    records = []
    for index, platform in enumerate(platforms, start=1):
        content_id = f"synthetic-{platform}-{index:03d}"
        published_url = f"https://synthetic.example/{platform}/{content_id}"
        base = 1000 + index * 375
        metrics = synthetic_metrics(platform, base)
        records.append(
            {
                "platform": platform,
                "publishedUrl": published_url,
                "contentId": content_id,
                "title": f"Synthetic {product_name} promotion on {platform}",
                "publishedAt": TODAY,
                "metrics": metrics,
                "orders": max(1, index * 2),
                "revenue": round(max(1, index * 2) * 39.0, 2),
                "productUrl": product_url,
                "evidence": SYNTHETIC_EVIDENCE,
            }
        )
    return records


def synthetic_metrics(platform: str, base: int) -> dict[str, Any]:
    if platform == "github":
        return {
            "stars": base // 12,
            "forks": base // 48,
            "watchers": base // 24,
            "openIssues": 3,
            "clicks": base // 30,
            "leads": base // 90,
            "orders": 2,
            "revenue": 78.0,
        }
    return {
        "views": base,
        "likes": base // 18,
        "favorites": base // 35,
        "comments": base // 55,
        "shares": base // 70,
        "clicks": base // 28,
        "messages": base // 95,
        "leads": base // 120,
        "orders": max(1, base // 700),
        "revenue": round(max(1, base // 700) * 39.0, 2),
    }


def write_inbox(inbox_dir: Path, records: list[dict[str, Any]], product_url: str, product_name: str) -> dict[str, str]:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    published_urls = inbox_dir / "published-urls.csv"
    metrics = inbox_dir / "metrics.csv"
    comments = inbox_dir / "comments.txt"
    orders = inbox_dir / "orders.csv"
    manifest = inbox_dir / "inbox-manifest.json"
    readme = inbox_dir / "README.md"

    write_csv(
        published_urls,
        ["platform", "publishedUrl", "contentId", "title", "publishedAt", "evidence", "notes"],
        [
            {
                **record,
                "notes": "Synthetic published URL for local validation only.",
            }
            for record in records
        ],
    )
    write_csv(
        metrics,
        ["platform", "publishedUrl", "contentId", "title", *metric_parsing.METRIC_FIELDS, "evidence", "notes"],
        [
            {
                **record,
                **record["metrics"],
                "notes": "Synthetic metrics for pipeline validation only.",
            }
            for record in records
        ],
    )
    write_csv(
        orders,
        [
            "orderId",
            "platform",
            "publishedUrl",
            "referrer",
            "landingPage",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "contentId",
            "title",
            "clicks",
            "leads",
            "orders",
            "revenue",
            "status",
            "evidence",
        ],
        [business_row(record, product_url, product_name) for record in records],
    )
    comments.write_text(render_comments(records), encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "generatedAt": TODAY,
                "synthetic": True,
                "warning": SYNTHETIC_EVIDENCE,
                "evidence": {
                    "publishedUrlFiles": [published_urls.name],
                    "metricsCsv": [metrics.name],
                    "commentText": [comments.name],
                    "businessCsv": [orders.name],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    readme.write_text(render_readme(product_url, product_name), encoding="utf-8")
    return {
        "publishedUrlsCsv": str(published_urls),
        "metricsCsv": str(metrics),
        "commentsText": str(comments),
        "ordersCsv": str(orders),
        "manifest": str(manifest),
        "readme": str(readme),
    }


def business_row(record: dict[str, Any], product_url: str, product_name: str) -> dict[str, Any]:
    metrics = record["metrics"]
    return {
        "orderId": f"synthetic-order-{record['contentId']}",
        "platform": record["platform"],
        "publishedUrl": record["publishedUrl"],
        "referrer": record["publishedUrl"],
        "landingPage": product_url,
        "utm_source": record["platform"],
        "utm_medium": "synthetic_validation",
        "utm_campaign": clean_slug(product_name),
        "utm_content": record["contentId"],
        "contentId": record["contentId"],
        "title": record["title"],
        "clicks": metrics.get("clicks", ""),
        "leads": metrics.get("leads", ""),
        "orders": record["orders"],
        "revenue": record["revenue"],
        "status": "paid",
        "evidence": SYNTHETIC_EVIDENCE,
    }


def render_comments(records: list[dict[str, Any]]) -> str:
    lines = []
    for record in records:
        platform = record["platform"]
        lines.append(
            f"Comment by synthetic_{platform}_buyer: Can {record['title']} connect with our daily workflow? likes: 8 replies: 2"
        )
        lines.append(
            f"Comment by synthetic_{platform}_operator: Need pricing, Windows setup steps, and team license details. likes: 5 replies: 1"
        )
    return "\n".join(lines) + "\n"


def run_recovery(args: argparse.Namespace, out_dir: Path, inbox_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPTS / "real_evidence_inbox.py"),
        "--inbox-dir",
        str(inbox_dir),
        "--out-dir",
        str(out_dir),
        "--skip-post-publish-capture",
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "command": command,
        "exitCode": completed.returncode,
        "stdoutTail": completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "",
        "stderrTail": completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "",
        "reports": {
            "realEvidenceInbox": str(out_dir / "reports/promotion-manager/real-evidence-inbox/real-evidence-inbox.json"),
            "metricsRecovery": str(out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"),
            "commentEvidence": str(out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"),
            "businessAttribution": str(out_dir / "reports/promotion-manager/business-attribution/business-attribution.json"),
            "nextRoundOptimization": str(out_dir / "reports/promotion-manager/optimization/next-round-optimization.json"),
        },
    }


def build_report(
    args: argparse.Namespace,
    out_dir: Path,
    inbox_dir: Path,
    records: list[dict[str, Any]],
    artifacts: dict[str, str],
    recovery: dict[str, Any],
) -> dict[str, Any]:
    recovery_exit = recovery.get("exitCode")
    status = "synthetic_validation_ready"
    if recovery and recovery_exit != 0:
        status = "synthetic_validation_recovery_failed"
    return {
        "generatedAt": TODAY,
        "status": status,
        "synthetic": True,
        "warning": SYNTHETIC_EVIDENCE,
        "outDir": str(out_dir),
        "inboxDir": str(inbox_dir),
        "input": {
            "productUrl": args.product_url,
            "productName": args.product_name,
            "platforms": split_csv(args.platforms),
            "runRecovery": args.run_recovery,
        },
        "summary": {
            "platforms": len(records),
            "metricRows": len(records),
            "commentLines": len(records) * 2,
            "businessRows": len(records),
            "recoveryExitCode": recovery_exit,
        },
        "artifacts": artifacts,
        "recovery": recovery,
        "nextCommands": [
            f"python scripts/real_evidence_inbox.py --inbox-dir \"{inbox_dir}\" --out-dir \"{out_dir}\" --skip-post-publish-capture",
            f"python scripts/final_capability_readiness.py --out-dir \"{out_dir}\"",
        ],
        "guardrails": [
            "Synthetic evidence is for local validation only and must not be reported as real performance.",
            "Do not merge synthetic evidence into a live product run or investor/customer report.",
            "Real readiness still requires real published URLs, public or exported platform metrics, comments, orders, and revenue.",
        ],
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "synthetic-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "synthetic-evidence.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Synthetic Evidence Validation",
        "",
        f"- Status: `{report['status']}`",
        f"- Warning: `{report['warning']}`",
        f"- Inbox: {report['inboxDir']}",
        f"- Platforms: {report['summary']['platforms']}",
        f"- Recovery exit code: {report['summary']['recoveryExitCode']}",
        "",
        "## Artifacts",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in report["artifacts"].items())
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def render_readme(product_url: str, product_name: str) -> str:
    return "\n".join(
        [
            "# Synthetic Evidence Inbox",
            "",
            f"Product: {product_name}",
            f"Product URL: {product_url}",
            "",
            f"Warning: {SYNTHETIC_EVIDENCE}",
            "",
            "These files are generated only to validate the local recovery and optimization pipeline.",
            "Replace them with real published URLs, platform exports, screenshots, comments, and business exports before any live retrospective.",
            "",
        ]
    )


def write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/synthetic-evidence"


def product_name_from_url(url: str) -> str:
    slug = clean_slug(url.rstrip("/").split("/")[-1] or "product")
    return slug.replace("-", " ").title()


def clean_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-") or "product"


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    main()
