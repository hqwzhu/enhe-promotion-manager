#!/usr/bin/env python3
"""Create a safe real-evidence inbox before a live promotion run."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]
REPORT_DIR = Path("reports/promotion-manager/real-evidence-inbox-setup")
METRIC_FIELDS = [
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
]


def main() -> None:
    args = parse_args()
    inbox_dir = Path(args.inbox_dir)
    out_dir = Path(args.out_dir)
    platforms = split_csv(args.platforms) or DEFAULT_PLATFORMS
    published_urls = parse_published_urls(args.published_url)
    artifacts = write_inbox(args, inbox_dir, out_dir, platforms, published_urls)
    report = build_report(args, inbox_dir, out_dir, platforms, published_urls, artifacts)
    write_report(out_dir, report)
    print(f"Real evidence inbox setup written to: {(report_dir(out_dir) / 'real-evidence-inbox-setup.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a fillable real-evidence inbox for published URLs, metrics, comments, orders, and revenue.")
    parser.add_argument("--product-url", default="", help="Product or website URL being promoted.")
    parser.add_argument("--product-name", default="", help="Optional product name for checklist context.")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated platforms to prepare.")
    parser.add_argument("--published-url", action="append", default=[], help="Optional published URL, or platform=url. Can repeat.")
    parser.add_argument("--inbox-dir", default="./promotion-evidence-inbox", help="Folder to create for real evidence files.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing inbox template files. Existing files are preserved by default.")
    return parser.parse_args()


def write_inbox(
    args: argparse.Namespace,
    inbox_dir: Path,
    out_dir: Path,
    platforms: list[str],
    published_urls: list[dict[str, str]],
) -> dict[str, Any]:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    commands_dir = inbox_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, Any] = {}
    files = {
        "manifest": inbox_dir / "inbox-manifest.json",
        "publishedUrlsCsv": inbox_dir / "published-urls.csv",
        "metricsCsv": inbox_dir / "metrics.csv",
        "commentsText": inbox_dir / "comments.txt",
        "ordersCsv": inbox_dir / "orders.csv",
        "structuredMetricsExample": inbox_dir / "structured-metrics-snapshot.example.json",
        "readme": inbox_dir / "README.md",
        "importCommands": commands_dir / "import-real-evidence.ps1",
    }

    artifacts["publishedUrlsCsv"] = write_csv(
        files["publishedUrlsCsv"],
        ["platform", "publishedUrl", "contentId", "title", "publishedAt", "evidence", "notes"],
        published_url_rows(published_urls),
        args.overwrite,
    )
    artifacts["metricsCsv"] = write_csv(
        files["metricsCsv"],
        ["platform", "publishedUrl", "contentId", "title", *METRIC_FIELDS, "evidence", "notes"],
        [],
        args.overwrite,
    )
    artifacts["ordersCsv"] = write_csv(
        files["ordersCsv"],
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
        [],
        args.overwrite,
    )
    artifacts["commentsText"] = write_text(files["commentsText"], "", args.overwrite)
    artifacts["structuredMetricsExample"] = write_text(
        files["structuredMetricsExample"],
        json.dumps(structured_metrics_example(args, platforms), ensure_ascii=True, indent=2) + "\n",
        args.overwrite,
    )
    artifacts["manifest"] = write_text(
        files["manifest"],
        json.dumps(manifest_payload(args, platforms, files), ensure_ascii=True, indent=2) + "\n",
        args.overwrite,
    )
    artifacts["readme"] = write_text(files["readme"], render_readme(args, platforms) + "\n", args.overwrite)
    artifacts["importCommands"] = write_text(files["importCommands"], render_commands(inbox_dir, out_dir) + "\n", args.overwrite)
    return artifacts


def manifest_payload(args: argparse.Namespace, platforms: list[str], files: dict[str, Path]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "source": "real_evidence_inbox_setup",
        "product": {
            "name": args.product_name,
            "url": args.product_url,
        },
        "expectedPlatforms": platforms,
        "evidence": {
            "publishedUrlFiles": [files["publishedUrlsCsv"].name],
            "metricsCsv": [files["metricsCsv"].name],
            "commentText": [files["commentsText"].name],
            "businessCsv": [files["ordersCsv"].name],
        },
        "referenceFiles": {
            "structuredMetricsExample": files["structuredMetricsExample"].name,
            "readme": files["readme"].name,
            "importCommands": str(Path("commands") / files["importCommands"].name),
        },
        "guardrails": guardrails(),
    }


def published_url_rows(records: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for record in records:
        rows.append(
            {
                "platform": record.get("platform", ""),
                "publishedUrl": record.get("publishedUrl", ""),
                "contentId": record.get("contentId", ""),
                "title": record.get("title", ""),
                "publishedAt": "",
                "evidence": "",
                "notes": "Final public URL only; do not use draft, preview, editor, or login URLs.",
            }
        )
    return rows


def structured_metrics_example(args: argparse.Namespace, platforms: list[str]) -> dict[str, Any]:
    platform = platforms[0] if platforms else "youtube"
    return {
        "exampleOnly": True,
        "doNotImportAsEvidence": True,
        "product": {
            "name": args.product_name or "Product name",
            "url": args.product_url or "https://example.com/product",
        },
        "platform": platform,
        "publishedUrl": "https://platform.example/final-public-post",
        "title": "Published promotion title",
        "metrics": {field: "replace-with-real-exported-value" for field in METRIC_FIELDS},
        "comments": [{"author": "real-visible-author", "text": "real visible/exported comment", "likes": "0", "replies": "0"}],
        "evidence": "public page, official export, screenshot OCR text, or business export path",
    }


def build_report(
    args: argparse.Namespace,
    inbox_dir: Path,
    out_dir: Path,
    platforms: list[str],
    published_urls: list[dict[str, str]],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "status": "ready",
        "input": {
            "productUrl": args.product_url,
            "productName": args.product_name,
            "platforms": platforms,
            "publishedUrlCount": len(published_urls),
            "inboxDir": str(inbox_dir),
            "outDir": str(out_dir),
            "overwrite": bool(args.overwrite),
        },
        "summary": {
            "platforms": len(platforms),
            "publishedUrlsSeeded": len(published_urls),
            "filesPrepared": len(artifacts),
            "realMetricsSeeded": 0,
            "realCommentsSeeded": 0,
            "realOrdersSeeded": 0,
            "realRevenueSeeded": 0,
        },
        "artifacts": artifacts,
        "nextCommands": [
            f"python scripts/real_evidence_inbox.py --inbox-dir \"{inbox_dir}\" --out-dir \"{out_dir}\"",
            f"python scripts/performance_monitor.py --out-dir \"{out_dir}\"",
        ],
        "guardrails": guardrails(),
    }


def render_readme(args: argparse.Namespace, platforms: list[str]) -> str:
    product = args.product_name or args.product_url or "this product"
    lines = [
        "# Real Evidence Inbox",
        "",
        f"Product: {product}",
        f"Platforms: {', '.join(platforms)}",
        "",
        "Fill these files after real publishing:",
        "",
        "- `published-urls.csv`: final public platform URLs only.",
        "- `metrics.csv`: real platform/API/export/screenshot-derived metrics.",
        "- `comments.txt`: copied public or exported comments, one comment per line.",
        "- `orders.csv`: real order, lead, click, and revenue export rows.",
        "- `structured-metrics-snapshot.example.json`: reference shape only; do not import it as evidence.",
        "",
        "Run the import command after the files contain real evidence:",
        "",
        "```powershell",
        ".\\commands\\import-real-evidence.ps1",
        "```",
        "",
        "Rules:",
    ]
    lines.extend(f"- {item}" for item in guardrails())
    return "\n".join(lines)


def render_commands(inbox_dir: Path, out_dir: Path) -> str:
    return "\n".join(
        [
            "# Generated by scripts/real_evidence_inbox_setup.py",
            "# Run from the repository root after adding real evidence files.",
            "",
            f"python scripts\\real_evidence_inbox.py --inbox-dir \"{inbox_dir}\" --out-dir \"{out_dir}\"",
            f"python scripts\\final_capability_readiness.py --out-dir \"{out_dir}\"",
        ]
    )


def write_csv(path: Path, header: list[str], rows: list[dict[str, Any]], overwrite: bool) -> dict[str, str]:
    if path.exists() and not overwrite:
        return artifact_status(path, "preserved_existing")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})
    return artifact_status(path, "written")


def write_text(path: Path, text: str, overwrite: bool) -> dict[str, str]:
    if path.exists() and not overwrite:
        return artifact_status(path, "preserved_existing")
    path.write_text(text, encoding="utf-8")
    return artifact_status(path, "written")


def artifact_status(path: Path, status: str) -> dict[str, str]:
    return {
        "path": str(path),
        "status": status,
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "real-evidence-inbox-setup.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (directory / "real-evidence-inbox-setup.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Evidence Inbox Setup",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Inbox: {report['input']['inboxDir']}",
        f"- Platforms: {report['summary']['platforms']}",
        f"- Seeded published URLs: {report['summary']['publishedUrlsSeeded']}",
        "",
        "## Artifacts",
    ]
    for key, item in report["artifacts"].items():
        lines.append(f"- {key}: `{item['status']}` {item['path']}")
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in report["nextCommands"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def parse_published_urls(values: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for value in values:
        text = value.strip()
        if not text:
            continue
        platform = ""
        url = text
        if "=" in text and not text.lower().startswith(("http://", "https://")):
            platform, url = [part.strip() for part in text.split("=", 1)]
        records.append({"platform": platform, "publishedUrl": url, "contentId": "", "title": ""})
    return records


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def guardrails() -> list[str]:
    return [
        "Do not fabricate views, likes, comments, orders, revenue, or published URLs.",
        "Do not treat blanks as zero.",
        "Use only public pages, official APIs/exports, screenshot OCR text, structured browser snapshots, or business exports.",
        "Do not store cookies, passwords, API keys, OAuth tokens, payment tokens, or hidden browser tokens.",
        "Do not use draft, preview, editor, login, or captcha pages as published URL evidence.",
    ]


def report_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


if __name__ == "__main__":
    main()
