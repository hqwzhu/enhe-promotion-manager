#!/usr/bin/env python3
"""Capture public post-publish metrics from proven published URLs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import metric_parsing
import metrics_intake
import published_items


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
REPORT_DIR = Path("reports/promotion-manager/post-publish-capture")
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"


class VisibleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.headings: list[str] = []
        self.text_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._title_parts: list[str] = []
        self._heading_tag = ""
        self._heading_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        self._tag_stack.append(tag)
        if tag == "meta":
            key = attrs_map.get("property") or attrs_map.get("name")
            content = attrs_map.get("content")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)
        elif tag == "link":
            self.links.append(attrs_map)
        elif tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.title = normalize_space(" ".join(self._title_parts))
            self._title_parts = []
        elif tag == self._heading_tag and self._heading_parts:
            text = normalize_space(" ".join(self._heading_parts))
            if text:
                self.headings.append(text)
            self._heading_tag = ""
            self._heading_parts = []
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        current = self._tag_stack[-1] if self._tag_stack else ""
        if current == "title":
            self._title_parts.append(text)
        elif self._heading_tag:
            self._heading_parts.append(text)
        elif current not in {"script", "style", "noscript"}:
            self.text_parts.append(text)

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    items = load_published_items(args, out_dir)
    results, metric_records, structured_records = capture_items(args, out_dir, items)
    report = build_report(args, items, results, metric_records, structured_records)
    write_outputs(out_dir, report, metric_records, structured_records)
    print(f"Post-publish metrics capture written to: {(capture_dir(out_dir) / 'post-publish-metrics-capture.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture browser-visible/public post-publish metrics from proven published URLs.")
    parser.add_argument("--published-items-json", action="append", default=[], help="published-items.json or a JSON list of published URL records.")
    parser.add_argument("--published-url", action="append", default=[], help="Published URL, or platform=url.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost URLs for local fixtures/tests only.")
    parser.add_argument("--capture-browser-assisted", action="store_true", help="Use Playwright browser-visible capture before falling back to static HTML fetch.")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Allow browser_snapshot.py to install official Playwright Chromium when missing.")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_published_items(args: argparse.Namespace, out_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    default_path = out_dir / "reports/promotion-manager/published-items/published-items.json"
    paths = [Path(value) for value in args.published_items_json if value]
    if default_path.exists() and default_path not in paths:
        paths.append(default_path)
    for path in paths:
        items.extend(items_from_json(path))
    for value in args.published_url:
        items.append(item_from_published_url(value))
    return dedupe_items(items)[: max(args.limit, 0)]


def items_from_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        records = first_list(data, "records", "items", "publishedItems", "published_items")
        if not records and data.get("publishedUrl"):
            records = [data]
    elif isinstance(data, list):
        records = data
    else:
        records = []
    return [normalize_item(item, str(path)) for item in records if isinstance(item, dict)]


def item_from_published_url(value: str) -> dict[str, Any]:
    platform = ""
    url = value
    if "=" in value and not value.lower().startswith(("http://", "https://")):
        platform, url = value.split("=", 1)
    return normalize_item({"platform": platform, "publishedUrl": url, "source": "cli"}, "cli")


def normalize_item(item: dict[str, Any], source: str) -> dict[str, Any]:
    url = first_non_empty(item.get("publishedUrl"), item.get("url"), item.get("link"))
    platform = clean_text(item.get("platform")) or metrics_intake.choose_platform("auto", url or source)
    status = clean_text(item.get("publishStatus") or item.get("status") or "published")
    return {
        "platform": platform,
        "publishedUrl": url,
        "contentId": first_non_empty(item.get("contentId"), item.get("videoId"), item.get("repo"), published_items.content_id_from_url(platform, url)),
        "title": first_non_empty(item.get("title"), item.get("name"), item.get("headline")),
        "publishedAt": first_non_empty(item.get("publishedAt"), item.get("date"), item.get("createdAt")),
        "publishStatus": "published" if url and status in {"", "ready", "published"} else status,
        "source": source,
        "sourceType": clean_text(item.get("sourceType")) or "published_items_json",
    }


def capture_items(
    args: argparse.Namespace,
    out_dir: Path,
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    results = []
    metric_records = []
    structured_records = []
    for index, item in enumerate(items, start=1):
        result, metric_record, structured_record = capture_item(args, out_dir, item, index)
        results.append(result)
        if metric_record:
            metric_records.append(metric_record)
        if structured_record:
            structured_records.append(structured_record)
    return results, metric_records, structured_records


def capture_item(
    args: argparse.Namespace,
    out_dir: Path,
    item: dict[str, Any],
    index: int,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    url = clean_text(item.get("publishedUrl"))
    task_id = safe_slug(f"{index:03d}-{item.get('platform')}-{item.get('contentId') or url or 'item'}")
    result = {
        "id": task_id,
        "platform": item.get("platform", ""),
        "publishedUrl": url,
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "captureMode": "browser_visible" if args.capture_browser_assisted else "static_public_html",
        "status": "planned",
    }
    if item.get("publishStatus") != "published":
        return with_manual_request(out_dir, item, result, "publish_pending"), None, None
    validation_issue = validate_url(url, args.allow_localhost)
    if validation_issue:
        return with_manual_request(out_dir, item, result, validation_issue), None, None
    if args.dry_run:
        result.update({"status": "dry_run", "reason": "Capture planned but not executed because --dry-run was supplied."})
        return result, None, None

    capture, capture_result = run_capture(args, out_dir, item, task_id)
    result.update(capture_result)
    if not capture:
        return with_manual_request(out_dir, item, result, result.get("reason") or "capture_failed"), None, None

    unsafe_issue = unsafe_capture_issue(capture)
    if unsafe_issue:
        result.update({"snapshot": capture.get("snapshot", ""), "status": "queued_manual_evidence"})
        return with_manual_request(out_dir, item, result, unsafe_issue), None, None

    text = "\n".join(str(capture.get(key) or "") for key in ["title", "description", "text", "visibleText"])
    metrics = extract_visible_metrics(text)
    if not metrics:
        return with_manual_request(out_dir, item, result, "no_visible_metrics_found"), None, structured_snapshot(item, capture, metrics)

    structured_record = structured_snapshot(item, capture, metrics)
    metric_record = metric_export_record(structured_record)
    result.update(
        {
            "status": "ready",
            "reason": "",
            "metrics": metrics,
            "metricFields": sorted(metrics.keys()),
            "snapshot": capture.get("snapshot", ""),
        }
    )
    return result, metric_record, structured_record


def run_capture(args: argparse.Namespace, out_dir: Path, item: dict[str, Any], task_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if args.capture_browser_assisted:
        capture, result = browser_visible_capture(args, out_dir, item, task_id)
        if capture:
            return capture, result
    return static_public_capture(args, out_dir, item, task_id)


def browser_visible_capture(args: argparse.Namespace, out_dir: Path, item: dict[str, Any], task_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    snapshot_path = capture_dir(out_dir) / "snapshots" / task_id / "browser-visible-snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(SCRIPTS / "browser_snapshot.py"),
        "--url",
        str(item["publishedUrl"]),
        "--out-file",
        str(snapshot_path),
        "--out-dir",
        str(snapshot_path.parent),
        "--timeout-ms",
        str(args.timeout_ms),
    ]
    if args.install_browser_if_missing:
        command.append("--install-browser-if-missing")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    status = {
        "browserCommand": display_command(command),
        "browserExitCode": result.returncode,
        "browserStdoutTail": tail(result.stdout),
        "browserStderrTail": tail(result.stderr),
    }
    if result.returncode != 0 or not snapshot_path.exists():
        status.update({"status": "error", "reason": "browser_visible_capture_failed"})
        return None, status
    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        status.update({"status": "error", "reason": "browser_snapshot_invalid_json"})
        return None, status
    data["snapshot"] = str(snapshot_path)
    data["captureMode"] = "browser_visible"
    status.update({"snapshot": str(snapshot_path)})
    return data, status


def static_public_capture(args: argparse.Namespace, out_dir: Path, item: dict[str, Any], task_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    snapshot_path = capture_dir(out_dir) / "snapshots" / task_id / "static-page.json"
    try:
        html = fetch_public_html(str(item["publishedUrl"]), args.timeout_ms / 1000)
    except Exception as exc:  # noqa: BLE001 - CLI reports the safe fetch failure.
        return None, {"status": "error", "reason": f"static_public_fetch_failed: {exc}"}
    parser = VisibleHTMLParser()
    parser.feed(html)
    canonical = first_non_empty(meta_url(parser), canonical_link(parser.links), item.get("publishedUrl"))
    title = first_non_empty(parser.meta.get("og:title"), parser.meta.get("twitter:title"), parser.headings[0] if parser.headings else "", parser.title, item.get("title"))
    snapshot = {
        "url": canonical,
        "sourceUrl": item.get("publishedUrl"),
        "title": title,
        "description": first_non_empty(parser.meta.get("description"), parser.meta.get("og:description"), parser.meta.get("twitter:description")),
        "text": parser.text,
        "headings": parser.headings[:20],
        "captureMode": "static_public_html",
        "snapshot": str(snapshot_path),
        "capturedAt": TODAY,
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot, {"snapshot": str(snapshot_path)}


def structured_snapshot(item: dict[str, Any], capture: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    url = first_non_empty(capture.get("url"), capture.get("canonicalUrl"), item.get("publishedUrl"))
    platform = item.get("platform") or metrics_intake.choose_platform("auto", url)
    evidence = unique([item.get("publishedUrl"), capture.get("snapshot"), item.get("source")])
    return {
        "platform": platform,
        "publishedUrl": url,
        "url": url,
        "contentId": first_non_empty(item.get("contentId"), published_items.content_id_from_url(platform, url)),
        "title": first_non_empty(capture.get("title"), item.get("title"), "Untitled published item"),
        "publishedAt": item.get("publishedAt", ""),
        "capturedAt": TODAY,
        "text": capture.get("text", ""),
        "metrics": metrics,
        "evidence": "; ".join(evidence),
        "source": {"type": "public_page_capture", "value": capture.get("snapshot", ""), "capturedAt": TODAY},
    }


def metric_export_record(structured: dict[str, Any]) -> dict[str, Any]:
    record = {
        "platform": structured["platform"],
        "publishedUrl": structured["publishedUrl"],
        "contentId": structured["contentId"],
        "title": structured["title"],
        "publishedAt": structured.get("publishedAt", ""),
        "evidence": structured.get("evidence", ""),
        "notes": "Captured from browser-visible/public published page.",
    }
    for name, value in structured.get("metrics", {}).items():
        normalized = value.get("normalized")
        record[name] = str(normalized) if normalized is not None else value.get("raw", "")
    return record


def extract_visible_metrics(text: str) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    aliases = {
        "views": r"(?:views?|plays?|impressions?|播放量|播放|浏览量|浏览|观看|曝光)",
        "likes": r"(?:likes?|点赞|赞)",
        "favorites": r"(?:favorites?|saves?|收藏|保存)",
        "comments": r"(?:comments?|评论)",
        "shares": r"(?:shares?|转发|分享)",
        "clicks": r"(?:clicks?|点击|访问)",
        "messages": r"(?:messages?|私信|咨询|会话)",
        "leads": r"(?:leads?|线索|留资)",
        "orders": r"(?:orders?|订单)",
        "revenue": r"(?:revenue|gmv|sales|收入|销售额|成交额)",
        "stars": r"(?:stars?|星标)",
        "forks": r"(?:forks?)",
        "watchers": r"(?:watchers?|subscribers?|订阅)",
    }
    number = r"([$¥￥]?\s*\d+(?:,\d{3})*(?:\.\d+)?\s*(?:k|m|万|千)?)"
    for field, label in aliases.items():
        after = re.search(rf"{label}\s*[:：]?\s*{number}", text, flags=re.IGNORECASE)
        before = re.search(rf"{number}\s*{label}", text, flags=re.IGNORECASE)
        match = after or before
        if match:
            value = match.group(1)
            metrics[field] = metric_value(value)
    return metrics


def metric_value(value: Any) -> dict[str, Any]:
    raw = clean_text(value)
    return {"raw": raw, "normalized": parse_metric_number(raw)}


def parse_metric_number(value: str) -> float | None:
    text = (
        clean_text(value)
        .replace(",", "")
        .replace("$", "")
        .replace("¥", "")
        .replace("￥", "")
        .replace(" ", "")
    )
    if not text:
        return None
    multiplier = 1.0
    lower = text.lower()
    if lower.endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    elif lower.endswith("m"):
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10_000.0
        text = text[:-1]
    elif text.endswith("千"):
        multiplier = 1_000.0
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def extract_visible_metrics(text: str) -> dict[str, dict[str, Any]]:
    return metric_parsing.extract_metrics(text, metrics_intake.METRIC_FIELDS)


def metric_value(value: Any) -> dict[str, Any]:
    return metric_parsing.metric_value(value)


def parse_metric_number(value: str) -> float | None:
    return metric_parsing.parse_metric_number(value)


def fetch_public_html(url: str, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def validate_url(url: str, allow_localhost: bool) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "url_is_not_public_http"
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"} and not allow_localhost:
        return "localhost_blocked_without_allow_localhost"
    lowered = url.lower()
    if any(marker in lowered for marker in ["/login", "/signin", "/captcha", "/challenge", "/editor", "/draft", "/preview"]):
        return "url_looks_like_login_captcha_editor_draft_or_preview"
    return ""


def unsafe_capture_issue(capture: dict[str, Any]) -> str:
    text = " ".join(str(capture.get(key) or "") for key in ["url", "title", "description", "text"]).lower()
    blocked = [
        "captcha",
        "challenge",
        "verify you are human",
        "please sign in",
        "sign in to continue",
        "login required",
        "access denied",
        "请先登录",
        "登录后查看",
        "验证码",
        "安全验证",
        "访问受限",
        "请完成验证",
    ]
    if any(marker in text for marker in blocked):
        return "capture_looks_like_login_captcha_verification_or_access_denied"
    return ""


def with_manual_request(out_dir: Path, item: dict[str, Any], result: dict[str, Any], reason: str) -> dict[str, Any]:
    request_path = write_manual_evidence_request(out_dir, item, result, reason)
    result.update(
        {
            "status": "queued_manual_evidence" if reason != "publish_pending" else "publish_pending",
            "reason": reason,
            "evidenceRequest": str(request_path),
        }
    )
    return result


def write_manual_evidence_request(out_dir: Path, item: dict[str, Any], result: dict[str, Any], reason: str) -> Path:
    directory = capture_dir(out_dir) / "manual-evidence"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe_slug(result.get('id') or item.get('publishedUrl') or 'published-item')}.md"
    path.write_text(render_manual_request(item, reason) + "\n", encoding="utf-8")
    return path


def build_report(
    args: argparse.Namespace,
    items: list[dict[str, Any]],
    results: list[dict[str, Any]],
    metric_records: list[dict[str, Any]],
    structured_records: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = summarize(results, metric_records)
    return {
        "generatedAt": TODAY,
        "status": capture_status(items, summary),
        "input": {
            "publishedItemsJson": args.published_items_json,
            "publishedUrls": args.published_url,
            "captureBrowserAssisted": args.capture_browser_assisted,
            "dryRun": args.dry_run,
        },
        "summary": summary,
        "results": results,
        "metricRecords": metric_records,
        "structuredRecords": structured_records,
        "artifacts": {
            "metricExport": str(capture_dir(Path(args.out_dir)) / "post-publish-metrics-export.json"),
            "structuredSnapshot": str(capture_dir(Path(args.out_dir)) / "post-publish-metrics-snapshot.json"),
        },
        "nextCommands": [
            (
                f"python scripts/metrics_recovery.py --metrics-json "
                f"\"{capture_dir(Path(args.out_dir)) / 'post-publish-metrics-export.json'}\" --out-dir \"{args.out_dir}\""
            )
        ],
        "guardrails": guardrails(),
    }


def summarize(results: list[dict[str, Any]], metric_records: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    platforms: dict[str, int] = {}
    for result in results:
        statuses[str(result.get("status") or "unknown")] = statuses.get(str(result.get("status") or "unknown"), 0) + 1
        platform = str(result.get("platform") or "unknown")
        platforms[platform] = platforms.get(platform, 0) + 1
    metric_field_counts = {
        field: sum(1 for record in metric_records if field in record)
        for field in metrics_intake.METRIC_FIELDS
        if any(field in record for record in metric_records)
    }
    metric_fields = sorted(metric_field_counts)
    return {
        "publishedItems": len(results),
        "capturedMetricRecords": len(metric_records),
        "recordsWithMetrics": len(metric_records),
        "statuses": dict(sorted(statuses.items())),
        "platforms": dict(sorted(platforms.items())),
        "metricFields": metric_fields,
        "metricFieldCounts": metric_field_counts,
    }


def capture_status(items: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    if not items:
        return "waiting_published_urls"
    if summary["capturedMetricRecords"] and summary["capturedMetricRecords"] < len(items):
        return "partial_ready"
    if summary["capturedMetricRecords"]:
        return "ready"
    return "waiting_real_data"


def write_outputs(
    out_dir: Path,
    report: dict[str, Any],
    metric_records: list[dict[str, Any]],
    structured_records: list[dict[str, Any]],
) -> None:
    directory = capture_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    metric_export = {
        "generatedAt": TODAY,
        "source": "post_publish_metrics_capture",
        "records": metric_records,
        "guardrails": guardrails(),
    }
    structured_snapshot = {
        "generatedAt": TODAY,
        "source": "post_publish_metrics_capture",
        "items": structured_records,
        "guardrails": guardrails(),
    }
    (directory / "post-publish-metrics-capture.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "post-publish-metrics-capture.md").write_text(render_markdown(report) + "\n", encoding="utf-8")
    (directory / "post-publish-metrics-export.json").write_text(json.dumps(metric_export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "post-publish-metrics-snapshot.json").write_text(json.dumps(structured_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Post-Publish Metrics Capture",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Published items checked: {report['summary']['publishedItems']}",
        f"- Captured metric records: {report['summary']['capturedMetricRecords']}",
        f"- Metric export: {report['artifacts']['metricExport']}",
        "",
        "## Results",
    ]
    for result in report["results"]:
        lines.extend(
            [
                "",
                f"### {result.get('id', 'item')} - {result.get('platform', '')}",
                f"- Status: `{result.get('status', '')}`",
                f"- URL: {result.get('publishedUrl') or 'missing'}",
                f"- Title: {result.get('title') or 'unknown'}",
            ]
        )
        if result.get("metricFields"):
            lines.append(f"- Metric fields: {', '.join(result['metricFields'])}")
        if result.get("reason"):
            lines.append(f"- Reason: {result['reason']}")
        if result.get("evidenceRequest"):
            lines.append(f"- Evidence request: {result['evidenceRequest']}")
    lines.extend(["", "## Next Commands"])
    lines.extend([f"- `{command}`" for command in report["nextCommands"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


def render_manual_request(item: dict[str, Any], reason: str) -> str:
    return "\n".join(
        [
            "# Post-Publish Metrics Evidence Request",
            "",
            f"- Platform: {item.get('platform', '')}",
            f"- URL: {item.get('publishedUrl') or 'missing'}",
            f"- Title: {item.get('title') or 'unknown'}",
            f"- Reason: `{reason}`",
            "",
            "## Required Evidence",
            "- Browser-visible metrics text or screenshot OCR for views, likes, comments, shares, saves, clicks, leads, orders, or revenue.",
            "- Official platform export when public page metrics are hidden.",
            "- Business-system export for orders and revenue.",
            "",
            "## Safe Import",
            "",
            "```bash",
            "python scripts/metrics_recovery.py --metrics-text \"<visible-metrics.txt>\" --out-dir \"<promotion-output>\"",
            "```",
        ]
    )


def guardrails() -> list[str]:
    return [
        "Capture only public or browser-visible page text.",
        "Do not auto-login, solve captcha, bypass risk controls, or use private endpoints.",
        "Do not save cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
        "Do not treat missing metrics as zero and do not fabricate orders or revenue.",
        "Orders and revenue require business exports or visible analytics evidence.",
    ]


def capture_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


def meta_url(parser: VisibleHTMLParser) -> str:
    return first_non_empty(parser.meta.get("og:url"), parser.meta.get("twitter:url"))


def canonical_link(links: list[dict[str, str]]) -> str:
    for link in links:
        if "canonical" in link.get("rel", "").lower() and link.get("href"):
            return link["href"]
    return ""


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in items:
        key = f"{item.get('platform')}:{item.get('publishedUrl') or item.get('contentId')}".lower().rstrip("/")
        if key and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", clean_text(value)).strip()


def unique(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = clean_text(value)
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    return text if len(text) <= limit else text[-limit:]


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-") or "published-item"


if __name__ == "__main__":
    main()
