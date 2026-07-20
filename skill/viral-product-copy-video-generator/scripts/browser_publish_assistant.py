#!/usr/bin/env python3
"""Prepare browser-assisted publish tasks from a guarded publish queue."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import webbrowser
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PUBLISHED_ITEMS = SCRIPTS / "published_items.py"
BROWSER_FORM_FILL = SCRIPTS / "browser_publish_form_fill.py"
TODAY = date.today().isoformat()
ASSISTED_STATUSES = {"queued_manual", "queued_browser_assisted"}
ASSISTED_MODES = {"manual_publish_required", "browser_assisted_publish"}


DEFAULT_PUBLISH_URLS = {
    "zhihu": "https://www.zhihu.com/creator",
    "xiaohongshu": "https://creator.xiaohongshu.com/",
    "douyin": "https://creator.douyin.com/creator-micro/content/upload",
    "tiktok": "https://www.tiktok.com/creator-center",
}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    queue_path = resolve_queue_path(args, out_dir)
    queue = read_json(queue_path) if queue_path.exists() else {}
    overrides = parse_key_values(args.platform_publish_url)
    published_urls = parse_key_values(args.published_url)
    records = build_records(args, out_dir, queue_path, queue, overrides)
    registered = register_published_urls(args, out_dir, records, published_urls)
    report = {
        "generatedAt": TODAY,
        "status": "ready" if records or registered["records"] else "no_browser_publish_tasks",
        "input": {"publishQueue": str(queue_path), "openBrowser": bool(args.open_browser)},
        "records": records,
        "registeredPublishedItems": registered,
        "summary": summarize(records, registered),
        "guardrails": [
            "This assistant prepares user-visible publishing materials only; it does not auto-login or click final publish.",
            "Do not paste generated form-fill scripts into untrusted pages.",
            "Stop when login, captcha, risk control, account verification, or platform review appears.",
            "Register a post only after a real published URL or user-visible post-publish evidence exists.",
            "No cookies, passwords, API keys, OAuth tokens, or hidden browser tokens are read or written.",
        ],
    }
    write_report(out_dir, report)
    print(f"Browser publish assistant written to: {(report_dir(out_dir) / 'browser-publish-assistant.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare browser-assisted/manual publish tasks from publish-queue.json.")
    parser.add_argument(
        "--publish-queue",
        default="",
        help="Path to publish-queue.json. Defaults to <out-dir>/reports/promotion-manager/publish-queue/publish-queue.json.",
    )
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument(
        "--platform-publish-url",
        action="append",
        default=[],
        help="Override publisher entry as platform=url. Useful when a platform moves its creator page.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open publisher entry URLs in the user's default browser. This does not automate login or click publish.",
    )
    parser.add_argument(
        "--published-url",
        action="append",
        default=[],
        help="Register a real post-publish URL as platform=url after the user publishes.",
    )
    parser.add_argument("--evidence", action="append", default=[], help="Evidence path/URL to attach to registered published URLs.")
    return parser.parse_args()


def resolve_queue_path(args: argparse.Namespace, out_dir: Path) -> Path:
    if args.publish_queue:
        return Path(args.publish_queue)
    return out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"


def build_records(
    args: argparse.Namespace,
    out_dir: Path,
    queue_path: Path,
    queue: dict[str, Any],
    overrides: dict[str, str],
) -> list[dict[str, Any]]:
    selected = set(split_csv(args.platforms))
    records = []
    for item in queue.get("records", []):
        platform = clean_text(item.get("platform")).lower()
        if not platform or (selected and platform not in selected):
            continue
        status = clean_text(item.get("status"))
        mode = clean_text(item.get("publishMode"))
        if status not in ASSISTED_STATUSES and mode not in ASSISTED_MODES:
            continue
        draft_value = clean_text(item.get("contentDraft"))
        draft_path = Path(draft_value) if draft_value else None
        draft = read_text_if_exists(draft_path)
        payload = payload_from_draft(platform, draft, item)
        publisher_url = overrides.get(platform) or DEFAULT_PUBLISH_URLS.get(platform, "")
        payload_files = write_payload_files(out_dir, platform, payload, item, publisher_url)
        browser_form_fill = browser_form_fill_info(out_dir, payload_files["json"])
        opened = False
        if args.open_browser and publisher_url:
            opened = webbrowser.open(publisher_url)
        records.append(
            {
                "id": f"{TODAY}-{platform}",
                "platform": platform,
                "queueStatus": status,
                "publishMode": mode,
                "sourceQueue": str(queue_path),
                "contentDraft": str(draft_path) if draft_path else "",
                "publisherUrl": publisher_url,
                "publisherUrlSource": "override" if platform in overrides else "default_entry_point",
                "browserOpened": bool(opened),
                "payload": payload,
                "payloadFiles": payload_files,
                "browserFormFill": browser_form_fill,
                "finalPublishUserActionRequired": True,
                "postPublish": {
                    "registerUrlCommand": (
                        f"python scripts/published_items.py --platform {platform} --published-url \"<REAL_PUBLISHED_URL>\" "
                        f"--title \"{shell_safe(payload['title'])}\" --out-dir \"{out_dir}\""
                    ),
                    "captureSnapshotCommand": (
                        f"python scripts/publish_url_capture.py --structured-json \"<PUBLISHED_PAGE_SNAPSHOT.json>\" "
                        f"--platform {platform} --out-dir \"{out_dir}\""
                    ),
                    "metricsRecoveryCommand": f"python scripts/metrics_recovery.py --out-dir \"{out_dir}\"",
                },
                "nextAction": next_action(platform, publisher_url),
            }
        )
    return records


def browser_form_fill_info(out_dir: Path, payload_json: str) -> dict[str, Any]:
    report = report_dir(out_dir) / "browser-form-fill.json"
    screenshot = report_dir(out_dir) / "browser-form-fill.png"
    return {
        "command": f"python scripts/{BROWSER_FORM_FILL.name} --payload-json \"{payload_json}\" --out-dir \"{out_dir}\"",
        "payloadJson": payload_json,
        "report": str(report),
        "screenshot": str(screenshot),
        "finalPublishUserActionRequired": True,
        "guardrail": "Fills visible fields only; the user must review and click final publish.",
    }


def payload_from_draft(platform: str, draft: str, item: dict[str, Any]) -> dict[str, Any]:
    title = first_labeled_value(draft, "Viral title") or first_labeled_value(draft, "Title") or clean_text(item.get("viralTitle")) or clean_text(item.get("title")) or f"{platform} promotion draft"
    tags = split_tags(first_labeled_value(draft, "Tags")) or clean_list(item.get("tags"))
    body = body_from_draft(draft)
    cover_text = first_labeled_value(draft, "Cover text")
    cta = first_labeled_value(draft, "CTA")
    tracking = item.get("trackingPlan") if isinstance(item.get("trackingPlan"), dict) else {}
    return {
        "title": title,
        "body": clean_text(item.get("copy")) or body,
        "tags": tags,
        "coverText": cover_text,
        "firstBatch": item.get("firstBatch", {}),
        "video": item.get("video", {}),
        "cover": item.get("cover", {}),
        "detailImages": item.get("detailImages", []),
        "assets": item.get("assets", []),
        "cta": cta,
        "trackedUrl": tracking.get("trackedUrl", ""),
        "trackingPlan": tracking,
        "preparedAt": TODAY,
    }


def body_from_draft(draft: str) -> str:
    if not draft:
        return ""
    markers = ["## Description", "## article", "## shortVideoScript", "## voiceover", "## Formats"]
    sections = []
    for index, marker in enumerate(markers):
        start = draft.find(marker)
        if start < 0:
            continue
        end_candidates = [draft.find(next_marker, start + len(marker)) for next_marker in markers[index + 1 :]]
        end_candidates = [value for value in end_candidates if value >= 0]
        end = min(end_candidates) if end_candidates else len(draft)
        text = draft[start + len(marker) : end].strip()
        if text and text not in sections:
            sections.append(text)
    if sections:
        return "\n\n".join(sections).strip()
    return draft.strip()


def write_payload_files(
    out_dir: Path,
    platform: str,
    payload: dict[str, Any],
    queue_item: dict[str, Any],
    publisher_url: str,
) -> dict[str, str]:
    directory = report_dir(out_dir) / "payloads"
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / platform
    json_path = base.with_suffix(".payload.json")
    clipboard_path = base.with_suffix(".clipboard.txt")
    script_path = base.with_suffix(".form-fill.js")
    checklist_path = base.with_suffix(".checklist.md")
    json_path.write_text(
        json.dumps({"platform": platform, "publisherUrl": publisher_url, "payload": payload, "queueItem": queue_item}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    clipboard_path.write_text(render_clipboard(payload) + "\n", encoding="utf-8")
    script_path.write_text(render_form_fill_script(payload) + "\n", encoding="utf-8")
    checklist_path.write_text(render_checklist(platform, payload, queue_item, publisher_url) + "\n", encoding="utf-8")
    return {
        "json": str(json_path),
        "clipboard": str(clipboard_path),
        "formFillScript": str(script_path),
        "checklist": str(checklist_path),
    }


def render_clipboard(payload: dict[str, Any]) -> str:
    lines = [
        f"Title: {payload['title']}",
        "",
        payload["body"],
    ]
    if payload["tags"]:
        lines.extend(["", "Tags: " + " ".join(payload["tags"])])
    if payload["coverText"]:
        lines.extend(["", "Cover: " + payload["coverText"]])
    lines.extend(["", "First batch:", render_first_batch(payload.get("firstBatch", {}))])
    lines.extend(["", "Media assets:", render_payload_assets(payload)])
    if payload.get("trackedUrl"):
        lines.extend(["", "Tracked URL: " + payload["trackedUrl"]])
    return "\n".join(lines).strip()


def render_form_fill_script(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return f"""(() => {{
  const payload = {data};
  const setValue = (el, value) => {{
    if (!el || !value) return false;
    el.focus();
    if ('value' in el) {{
      el.value = value;
      el.dispatchEvent(new Event('input', {{ bubbles: true }}));
      el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }} else {{
      el.textContent = value;
      el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: value }}));
    }}
    return true;
  }};
  const find = (selectors) => selectors.map((selector) => document.querySelector(selector)).find(Boolean);
  setValue(find(['input[placeholder*=标题]', 'input[aria-label*=标题]', 'input[name*=title]', 'textarea[placeholder*=标题]']), payload.title);
  setValue(find(['textarea', '[contenteditable=true]', 'div[role=textbox]']), payload.body);
  console.warn('Review every field manually. This helper does not click Publish/Submit.');
}})();"""


def render_checklist(platform: str, payload: dict[str, Any], queue_item: dict[str, Any], publisher_url: str) -> str:
    lines = [
        f"# {platform} Browser Publish Checklist",
        "",
        f"- Publisher entry: {publisher_url or 'configure with --platform-publish-url platform=url'}",
        f"- Title: {payload['title']}",
        f"- Tracked URL: {payload.get('trackedUrl') or 'not generated'}",
        f"- Draft status: `{queue_item.get('status', '')}`",
        f"- Publish mode: `{queue_item.get('publishMode', '')}`",
        "",
        "## Before Publish",
        "",
        "- Confirm the logged-in account is the intended account.",
        "- Paste or fill the prepared viral title, body, tags, first-batch comments, cover text, and media.",
        "- Upload or attach the video, cover, and detail images from the media asset paths below.",
        "",
        "## Media Assets",
        "",
        render_payload_assets(payload),
        "",
        "## First Batch",
        "",
        render_first_batch(payload.get("firstBatch", {})),
        "",
        "## Final Review",
        "",
        "- Review platform warnings, commercial disclosure requirements, and visibility settings.",
        "- Let the user perform the final publish action.",
        "",
        "## After Publish",
        "",
        "- Copy the real published URL.",
        "- Register it with `published_items.py` or `publish_url_capture.py`.",
        "- Run metrics recovery only after real public/analytics evidence exists.",
    ]
    return "\n".join(lines)


def render_payload_assets(payload: dict[str, Any]) -> str:
    assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
    if not assets:
        return "- Media assets: missing or pending media asset pack."
    lines = []
    for asset in assets:
        if isinstance(asset, dict):
            lines.append(f"- {asset.get('type', 'asset')}: `{asset.get('status', '')}` {asset.get('path', '')}")
    return "\n".join(lines) if lines else "- Media assets: missing or pending media asset pack."


def render_first_batch(first_batch: Any) -> str:
    if not isinstance(first_batch, dict) or not first_batch:
        return "- First batch: pending."
    lines = []
    if first_batch.get("pinnedComment"):
        lines.append(f"- Pinned comment: {first_batch['pinnedComment']}")
    for key, label in [
        ("firstComments", "First comments"),
        ("replyPrompts", "Reply prompts"),
        ("launchActions", "Launch actions"),
    ]:
        values = first_batch.get(key)
        if isinstance(values, list) and values:
            lines.append(f"- {label}:")
            lines.extend(f"  - {value}" for value in values)
    return "\n".join(lines) if lines else "- First batch: pending."


def register_published_urls(
    args: argparse.Namespace,
    out_dir: Path,
    records: list[dict[str, Any]],
    published_urls: dict[str, str],
) -> dict[str, Any]:
    results = []
    by_platform = {record["platform"]: record for record in records}
    for platform, url in published_urls.items():
        title = ((by_platform.get(platform) or {}).get("payload") or {}).get("title", "")
        command = [
            sys.executable,
            str(PUBLISHED_ITEMS),
            "--platform",
            platform,
            "--published-url",
            url,
            "--title",
            title or f"{platform} published item",
            "--out-dir",
            str(out_dir),
        ]
        for evidence in args.evidence:
            command.extend(["--evidence", evidence])
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        report_path = out_dir / "reports/promotion-manager/published-items/published-items.json"
        results.append(
            {
                "platform": platform,
                "publishedUrl": url,
                "status": "registered" if result.returncode == 0 else "error",
                "command": display_command(command),
                "exitCode": result.returncode,
                "report": str(report_path) if report_path.exists() else "",
                "stdoutTail": tail(result.stdout),
                "stderrTail": tail(result.stderr),
            }
        )
    return {"records": results, "count": len(results)}


def next_action(platform: str, publisher_url: str) -> str:
    if not publisher_url:
        return f"Provide --platform-publish-url {platform}=<creator_publish_url>, then open the publisher manually."
    return "Open the publisher entry, use the payload files to prepare the post, let the user click final publish, then register the real URL."


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "browser-publish-assistant.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "browser-publish-assistant.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Browser Publish Assistant",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Publish queue: {report['input']['publishQueue']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Records"])
    if not report["records"]:
        lines.append("- none")
    for record in report["records"]:
        lines.extend(
            [
                "",
                f"### {record['platform']}",
                f"- Queue status: `{record['queueStatus']}`",
                f"- Publisher URL: {record['publisherUrl'] or 'missing'}",
                f"- Clipboard: {record['payloadFiles']['clipboard']}",
                f"- Form fill script: {record['payloadFiles']['formFillScript']}",
                f"- Browser form-fill command: `{record['browserFormFill']['command']}`",
                f"- Checklist: {record['payloadFiles']['checklist']}",
                f"- Final publish user action required: {record['finalPublishUserActionRequired']}",
                f"- Next action: {record['nextAction']}",
            ]
        )
    if report["registeredPublishedItems"]["records"]:
        lines.extend(["", "## Registered Published URLs"])
        for item in report["registeredPublishedItems"]["records"]:
            lines.append(f"- {item['platform']}: `{item['status']}` {item['publishedUrl']}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def summarize(records: list[dict[str, Any]], registered: dict[str, Any]) -> dict[str, int]:
    return {
        "prepared": len(records),
        "browserOpened": sum(1 for item in records if item.get("browserOpened")),
        "registeredPublishedUrls": int(registered.get("count", 0)),
        "finalPublishUserActionRequired": sum(1 for item in records if item.get("finalPublishUserActionRequired")),
    }


def parse_key_values(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Expected platform=url, got: {value}")
        key, item = value.split("=", 1)
        key = clean_text(key).lower()
        item = clean_text(item)
        if key and item:
            result[key] = item
    return result


def first_labeled_value(text: str, label: str) -> str:
    pattern = re.compile(rf"^-+\s*{re.escape(label)}:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text or "")
    return clean_text(match.group(1)) if match else ""


def split_tags(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，\s]+", value) if item.strip()]


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def read_text_if_exists(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/browser-publish"


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def shell_safe(value: str) -> str:
    return value.replace('"', "'")[:100]


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
