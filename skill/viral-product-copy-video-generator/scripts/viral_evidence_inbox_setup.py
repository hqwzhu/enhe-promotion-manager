#!/usr/bin/env python3
"""Create a fillable viral competitor evidence inbox."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


TODAY = date.today().isoformat()
DEFAULT_PLATFORMS = ["youtube", "zhihu", "xiaohongshu", "douyin", "github"]
REPORT_DIR = Path("reports/promotion-manager/competitors/viral-evidence-inbox-setup")
METRIC_FIELDS = [
    "views",
    "likes",
    "favorites",
    "comments",
    "shares",
    "subscribers",
    "stars",
    "forks",
]


def main() -> None:
    args = parse_args()
    inbox_dir = Path(args.inbox_dir)
    out_dir = Path(args.out_dir)
    platforms = split_csv(args.platforms) or DEFAULT_PLATFORMS
    artifacts = write_inbox(args, inbox_dir, out_dir, platforms)
    report = build_report(args, inbox_dir, out_dir, platforms, artifacts)
    write_report(out_dir, report)
    print(f"Viral evidence inbox setup written to: {(report_dir(out_dir) / 'viral-evidence-inbox-setup.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a fillable inbox for real competitor/viral material evidence.")
    parser.add_argument("--product-url", default="", help="Product or website URL being promoted.")
    parser.add_argument("--product-name", default="", help="Optional product name for checklist context.")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated platforms to prepare.")
    parser.add_argument("--inbox-dir", default="./viral-evidence-inbox", help="Folder to create for competitor evidence files.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing inbox template files. Existing files are preserved by default.")
    return parser.parse_args()


def write_inbox(args: argparse.Namespace, inbox_dir: Path, out_dir: Path, platforms: list[str]) -> dict[str, Any]:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    commands_dir = inbox_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "manifest": inbox_dir / "inbox-manifest.json",
        "sourceCsv": inbox_dir / "viral-sources.csv",
        "copiedText": inbox_dir / "copied-visible-content.txt",
        "structuredExample": inbox_dir / "structured-viral-evidence.example.json",
        "readme": inbox_dir / "README.md",
        "importCommands": commands_dir / "import-viral-evidence.ps1",
    }
    artifacts: dict[str, Any] = {}
    artifacts["sourceCsv"] = write_csv(files["sourceCsv"], csv_fields(), [], args.overwrite)
    artifacts["copiedText"] = write_text(files["copiedText"], "", args.overwrite)
    artifacts["structuredExample"] = write_text(
        files["structuredExample"],
        json.dumps(structured_example(args, platforms), ensure_ascii=True, indent=2) + "\n",
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


def csv_fields() -> list[str]:
    return [
        "platform",
        "url",
        "title",
        "creatorName",
        "contentFormat",
        "hook",
        "description",
        "content",
        *METRIC_FIELDS,
        "evidence",
        "notes",
    ]


def manifest_payload(args: argparse.Namespace, platforms: list[str], files: dict[str, Path]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "source": "viral_evidence_inbox_setup",
        "product": {
            "name": args.product_name,
            "url": args.product_url,
        },
        "expectedPlatforms": platforms,
        "evidence": {
            "sourceCsv": [files["sourceCsv"].name],
            "textFiles": [files["copiedText"].name],
        },
        "referenceFiles": {
            "structuredExample": files["structuredExample"].name,
            "readme": files["readme"].name,
            "importCommands": str(Path("commands") / files["importCommands"].name),
        },
        "guardrails": guardrails(),
    }


def structured_example(args: argparse.Namespace, platforms: list[str]) -> dict[str, Any]:
    platform = platforms[0] if platforms else "youtube"
    return {
        "exampleOnly": True,
        "doNotImportAsEvidence": True,
        "product": {
            "name": args.product_name or "Product name",
            "url": args.product_url or "https://example.com/product",
        },
        "records": [
            {
                "platform": platform,
                "url": "https://platform.example/final-public-material",
                "title": "Replace with real competitor title",
                "creatorName": "Replace with real creator/account",
                "contentFormat": "video_or_note_or_article",
                "hook": "Replace with observed opening hook",
                "content": "Paste visible transcript, note body, article opening, or repository summary.",
                "visibleMetrics": {
                    "views": "replace-with-real-visible-or-exported-value",
                    "likes": "replace-with-real-visible-or-exported-value",
                },
                "evidence": "public page, browser-visible text, platform export, screenshot OCR text, or copied transcript",
            }
        ],
    }


def build_report(args: argparse.Namespace, inbox_dir: Path, out_dir: Path, platforms: list[str], artifacts: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "status": "ready",
        "input": {
            "productUrl": args.product_url,
            "productName": args.product_name,
            "platforms": platforms,
            "inboxDir": str(inbox_dir),
            "outDir": str(out_dir),
            "overwrite": bool(args.overwrite),
        },
        "summary": {
            "platforms": len(platforms),
            "filesPrepared": len(artifacts),
            "realCompetitorRecordsSeeded": 0,
            "realMetricsSeeded": 0,
        },
        "artifacts": artifacts,
        "nextCommands": [
            f"python scripts/viral_evidence_inbox.py --inbox-dir \"{inbox_dir}\" --out-dir \"{out_dir}\"",
            f"python scripts/viral_content_library.py --out-dir \"{out_dir}\"",
        ],
        "guardrails": guardrails(),
    }


def render_readme(args: argparse.Namespace, platforms: list[str]) -> str:
    product = args.product_name or args.product_url or "this product"
    lines = [
        "# Viral Evidence Inbox",
        "",
        f"Product: {product}",
        f"Platforms: {', '.join(platforms)}",
        "",
        "Add real competitor or viral material evidence here:",
        "",
        "- `viral-sources.csv`: one real competitor material per row.",
        "- `copied-visible-content.txt`: copied visible page text, transcript, or export text.",
        "- `structured-viral-evidence.example.json`: reference shape only; copy it to a non-example JSON file before using real records.",
        "- Extra `.html`, `.txt`, `.md`, `.json`, or `.csv` files can be added. File names containing platform names help classification.",
        "",
        "Run the import command after the files contain real evidence:",
        "",
        "```powershell",
        ".\\commands\\import-viral-evidence.ps1",
        "```",
        "",
        "Rules:",
    ]
    lines.extend(f"- {item}" for item in guardrails())
    return "\n".join(lines)


def render_commands(inbox_dir: Path, out_dir: Path) -> str:
    return "\n".join(
        [
            "# Generated by scripts/viral_evidence_inbox_setup.py",
            "# Run from the repository root after adding real competitor evidence files.",
            "",
            f"python scripts/viral_evidence_inbox.py --inbox-dir \"{inbox_dir}\" --out-dir \"{out_dir}\"",
        ]
    )


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]], overwrite: bool) -> dict[str, Any]:
    if path.exists() and not overwrite:
        return artifact(path, "preserved")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    return artifact(path, "written")


def write_text(path: Path, text: str, overwrite: bool) -> dict[str, Any]:
    if path.exists() and not overwrite:
        return artifact(path, "preserved")
    path.write_text(text, encoding="utf-8")
    return artifact(path, "written")


def artifact(path: Path, status: str) -> dict[str, Any]:
    return {"path": str(path), "status": status, "exists": path.exists()}


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def report_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "viral-evidence-inbox-setup.json"
    md_path = directory / "viral-evidence-inbox-setup.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_report_markdown(report) + "\n", encoding="utf-8")


def render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Viral Evidence Inbox Setup",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Inbox: `{report['input']['inboxDir']}`",
        f"- Files prepared: {report['summary']['filesPrepared']}",
        "",
        "## Next Commands",
    ]
    lines.extend(f"- `{command}`" for command in report["nextCommands"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def guardrails() -> list[str]:
    return [
        "Use public pages, browser-visible snapshots, official APIs, platform exports, screenshots/OCR text, or copied visible text only.",
        "Do not use private endpoints, hidden browser tokens, cookies, or captcha bypass.",
        "Do not treat missing metrics as zero.",
        "Do not fabricate views, likes, comments, orders, revenue, creator identity, or published URLs.",
        "Competitor wording is evidence for structure analysis only; do not copy it into final product content.",
    ]


if __name__ == "__main__":
    main()
