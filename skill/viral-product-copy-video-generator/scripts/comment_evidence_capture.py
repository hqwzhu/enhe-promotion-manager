#!/usr/bin/env python3
"""Capture public/browser-visible comments and demand signals."""

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

import metrics_intake
import published_items


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TODAY = date.today().isoformat()
REPORT_DIR = Path("reports/promotion-manager/comment-evidence")
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"


class VisibleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self._parts: list[str] = []
        self._tag_stack: list[str] = []
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._tag_stack.append(tag)
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        if tag == "meta":
            key = attrs_map.get("property") or attrs_map.get("name")
            content = attrs_map.get("content")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.title = normalize_space(" ".join(self._title_parts))
            self._title_parts = []
        if tag in {"p", "li", "div", "section", "article", "blockquote", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        current = self._tag_stack[-1] if self._tag_stack else ""
        if current == "title":
            self._title_parts.append(text)
        elif current not in {"script", "style", "noscript"}:
            self._parts.append(text)

    @property
    def text(self) -> str:
        return normalize_lines(" ".join(self._parts))


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    items = load_items(args, out_dir)
    results = [capture_item(args, out_dir, item, index) for index, item in enumerate(items, start=1)]
    report = build_report(args, items, results)
    write_outputs(out_dir, report)
    print(f"Comment evidence capture written to: {(capture_dir(out_dir) / 'comment-evidence-capture.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture public/browser-visible comments and demand signals from published content.")
    parser.add_argument("--published-items-json", action="append", default=[], help="published-items.json or a JSON list of published URL records.")
    parser.add_argument("--published-url", action="append", default=[], help="Published URL, or platform=url.")
    parser.add_argument("--structured-json", help="Codex/browser structured snapshot containing comments or visible page text.")
    parser.add_argument("--html-file", help="Saved public HTML page.")
    parser.add_argument("--text-file", help="Copied public page text or comment export.")
    parser.add_argument("--platform", default="auto")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost URLs for local fixtures/tests only.")
    parser.add_argument("--capture-browser-assisted", action="store_true", help="Use Playwright browser-visible capture before static HTML fetch.")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Allow browser_snapshot.py to install official Playwright Chromium when missing.")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_items(args: argparse.Namespace, out_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    default_path = out_dir / "reports/promotion-manager/published-items/published-items.json"
    paths = [Path(value) for value in args.published_items_json if value]
    if default_path.exists() and default_path not in paths:
        paths.append(default_path)
    for path in paths:
        items.extend(items_from_json(path, args.platform))
    for value in args.published_url:
        items.append(item_from_published_url(value, args.platform))
    if not items and any([args.structured_json, args.html_file, args.text_file]):
        items.append(
            normalize_item(
                {
                    "platform": args.platform,
                    "publishedUrl": "",
                    "title": source_title(args),
                    "publishStatus": "published",
                    "sourceType": "direct_file",
                },
                "cli",
                args.platform,
            )
        )
    return dedupe_items(items)[: max(args.limit, 0)]


def items_from_json(path: Path, platform: str) -> list[dict[str, Any]]:
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
    return [normalize_item(item, str(path), platform) for item in records if isinstance(item, dict)]


def item_from_published_url(value: str, platform: str) -> dict[str, Any]:
    item_platform = platform
    url = value
    if "=" in value and not value.lower().startswith(("http://", "https://")):
        item_platform, url = value.split("=", 1)
    return normalize_item({"platform": item_platform, "publishedUrl": url, "source": "cli"}, "cli", platform)


def normalize_item(item: dict[str, Any], source: str, fallback_platform: str) -> dict[str, Any]:
    url = first_non_empty(item.get("publishedUrl"), item.get("url"), item.get("link"))
    platform = clean_text(item.get("platform")) or metrics_intake.choose_platform(fallback_platform, url or source)
    status = clean_text(item.get("publishStatus") or item.get("status") or "published")
    return {
        "platform": platform,
        "publishedUrl": url,
        "contentId": first_non_empty(item.get("contentId"), item.get("videoId"), item.get("repo"), published_items.content_id_from_url(platform, url)),
        "title": first_non_empty(item.get("title"), item.get("name"), item.get("headline")),
        "publishedAt": first_non_empty(item.get("publishedAt"), item.get("date"), item.get("createdAt")),
        "publishStatus": "published" if status in {"", "ready", "published"} else status,
        "source": source,
        "sourceType": clean_text(item.get("sourceType")) or "published_items_json",
    }


def capture_item(args: argparse.Namespace, out_dir: Path, item: dict[str, Any], index: int) -> dict[str, Any]:
    task_id = safe_slug(f"{index:03d}-{item.get('platform')}-{item.get('contentId') or item.get('publishedUrl') or 'item'}")
    result: dict[str, Any] = {
        "id": task_id,
        "platform": item.get("platform", ""),
        "publishedUrl": item.get("publishedUrl", ""),
        "title": item.get("title", ""),
        "status": "planned",
        "comments": [],
        "demandSignals": [],
    }
    if item.get("publishStatus") != "published":
        return with_manual_request(out_dir, item, result, "publish_pending")
    validation_issue = validate_item_url(item, args)
    if validation_issue:
        return with_manual_request(out_dir, item, result, validation_issue)
    if args.dry_run:
        result.update({"status": "dry_run", "reason": "Comment capture planned but not executed because --dry-run was supplied."})
        return result

    capture, status = load_capture(args, out_dir, item, task_id)
    result.update(status)
    if not capture:
        return with_manual_request(out_dir, item, result, result.get("reason") or "capture_failed")
    unsafe_issue = unsafe_capture_issue(capture)
    if unsafe_issue:
        return with_manual_request(out_dir, item, result, unsafe_issue)

    comments = extract_comments(capture, item)
    if not comments:
        return with_manual_request(out_dir, item, result, "no_visible_comments_found")
    signals = demand_signals_for_comments(comments)
    result.update(
        {
            "status": "ready",
            "reason": "",
            "title": first_non_empty(capture.get("title"), item.get("title")),
            "sourceEvidence": capture.get("sourceEvidence", ""),
            "commentCount": len(comments),
            "comments": comments,
            "demandSignals": signals,
        }
    )
    return result


def validate_item_url(item: dict[str, Any], args: argparse.Namespace) -> str:
    url = clean_text(item.get("publishedUrl"))
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "url_is_not_public_http"
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"} and not args.allow_localhost:
        return "localhost_blocked_without_allow_localhost"
    lowered = url.lower()
    if any(marker in lowered for marker in ["/login", "/signin", "/captcha", "/challenge", "/editor", "/draft", "/preview"]):
        return "url_looks_like_login_captcha_editor_draft_or_preview"
    return ""


def load_capture(args: argparse.Namespace, out_dir: Path, item: dict[str, Any], task_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if args.structured_json:
        return structured_capture(Path(args.structured_json), item)
    if args.html_file:
        return html_file_capture(Path(args.html_file), item)
    if args.text_file:
        return text_file_capture(Path(args.text_file), item)
    if args.capture_browser_assisted:
        capture, status = browser_visible_capture(args, out_dir, item, task_id)
        if capture:
            return capture, status
    return static_public_capture(args, out_dir, item, task_id)


def structured_capture(path: Path, item: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path.exists():
        return None, {"status": "error", "reason": "structured_json_missing"}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None, {"status": "error", "reason": "structured_json_invalid"}
    text = structured_text(data)
    return {
        "url": first_non_empty(get_mapping_value(data, "url", "publishedUrl", "canonicalUrl"), item.get("publishedUrl")),
        "title": first_non_empty(get_mapping_value(data, "title", "name", "headline"), item.get("title")),
        "text": text,
        "rawStructured": data,
        "sourceEvidence": str(path),
        "captureMode": "structured_json",
    }, {"sourceEvidence": str(path), "captureMode": "structured_json"}


def html_file_capture(path: Path, item: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path.exists():
        return None, {"status": "error", "reason": "html_file_missing"}
    return html_capture(path.read_text(encoding="utf-8-sig"), item, str(path), "html_file")


def text_file_capture(path: Path, item: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path.exists():
        return None, {"status": "error", "reason": "text_file_missing"}
    return {
        "url": item.get("publishedUrl", ""),
        "title": item.get("title", ""),
        "text": path.read_text(encoding="utf-8-sig"),
        "sourceEvidence": str(path),
        "captureMode": "text_file",
    }, {"sourceEvidence": str(path), "captureMode": "text_file"}


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
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    status = {
        "browserCommand": display_command(command),
        "browserExitCode": completed.returncode,
        "browserStdoutTail": tail(completed.stdout),
        "browserStderrTail": tail(completed.stderr),
    }
    if completed.returncode != 0 or not snapshot_path.exists():
        status.update({"status": "error", "reason": "browser_visible_capture_failed"})
        return None, status
    capture, capture_status = structured_capture(snapshot_path, item)
    status.update(capture_status)
    return capture, status


def static_public_capture(args: argparse.Namespace, out_dir: Path, item: dict[str, Any], task_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    url = clean_text(item.get("publishedUrl"))
    if not url:
        return None, {"status": "error", "reason": "published_url_missing"}
    try:
        html = fetch_public_html(url, args.timeout_ms / 1000)
    except Exception as exc:  # noqa: BLE001 - CLI reports safe fetch failures.
        return None, {"status": "error", "reason": f"static_public_fetch_failed: {exc}"}
    snapshot_path = capture_dir(out_dir) / "snapshots" / task_id / "static-page.json"
    capture, status = html_capture(html, item, str(snapshot_path), "static_public_html")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status["sourceEvidence"] = str(snapshot_path)
    capture["sourceEvidence"] = str(snapshot_path)
    return capture, status


def html_capture(html: str, item: dict[str, Any], evidence: str, mode: str) -> tuple[dict[str, Any], dict[str, Any]]:
    parser = VisibleHTMLParser()
    parser.feed(html)
    title = first_non_empty(parser.meta.get("og:title"), parser.meta.get("twitter:title"), parser.title, item.get("title"))
    capture = {
        "url": item.get("publishedUrl", ""),
        "title": title,
        "description": first_non_empty(parser.meta.get("description"), parser.meta.get("og:description"), parser.meta.get("twitter:description")),
        "text": parser.text,
        "sourceEvidence": evidence,
        "captureMode": mode,
    }
    return capture, {"sourceEvidence": evidence, "captureMode": mode}


def extract_comments(capture: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    raw = capture.get("rawStructured")
    if isinstance(raw, (dict, list)):
        comments.extend(comments_from_structured(raw, capture, item))
    comments.extend(comments_from_text(capture.get("text", ""), capture, item))
    return dedupe_comments(comments)


def comments_from_structured(raw: Any, capture: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for entry in collect_comment_entries(raw):
        if isinstance(entry, dict):
            text = first_non_empty(
                entry.get("text"),
                entry.get("comment"),
                entry.get("content"),
                entry.get("body"),
                entry.get("message"),
                entry.get("reply"),
            )
            if not text:
                continue
            author = first_non_empty(entry.get("author"), entry.get("user"), entry.get("username"), entry.get("name"))
            comments.append(normalize_comment(author, text, entry, capture, item))
        else:
            parsed = parse_comment_line(str(entry), capture, item)
            if parsed:
                comments.append(parsed)
    return comments


def collect_comment_entries(value: Any) -> list[Any]:
    entries: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered in {"comments", "commentlist", "replies", "replylist"} and isinstance(child, list):
                entries.extend(child)
            elif isinstance(child, (dict, list)):
                entries.extend(collect_comment_entries(child))
    elif isinstance(value, list):
        for child in value:
            entries.extend(collect_comment_entries(child))
    return entries


def comments_from_text(text: str, capture: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for line in comment_lines(text):
        parsed = parse_comment_line(line, capture, item)
        if parsed:
            comments.append(parsed)
    return comments


def comment_lines(text: str) -> list[str]:
    lines = []
    for raw in re.split(r"[\r\n]+", text):
        line = normalize_space(raw)
        if not line:
            continue
        chunks = re.split(r"(?i)(?=comment\s+by\s+)", line)
        lines.extend(normalize_space(chunk) for chunk in chunks if normalize_space(chunk))
    return lines


def parse_comment_line(line: str, capture: dict[str, Any], item: dict[str, Any]) -> dict[str, Any] | None:
    if looks_like_metric_line(line) or len(line) < 4:
        return None
    author = ""
    text = ""
    match = re.match(r"(?i)^comment\s+by\s+([^:]+):\s*(.+)$", line)
    if match:
        author, text = match.group(1), match.group(2)
    else:
        match = re.match(r"^([^:]{1,60}):\s*(.+)$", line)
        if match and is_comment_like(match.group(2)):
            author, text = match.group(1), match.group(2)
        elif is_comment_like(line):
            text = line
    if not text:
        return None
    metrics = comment_metrics(text)
    text = strip_comment_metrics(text)
    return normalize_comment(author, text, metrics, capture, item)


def normalize_comment(author: Any, text: Any, source: dict[str, Any], capture: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "author": first_non_empty(author, "unknown"),
        "text": strip_comment_metrics(clean_text(text)),
        "likes": parse_int(first_non_empty(source.get("likes"), source.get("likeCount"), source.get("upvotes"))),
        "replies": parse_int(first_non_empty(source.get("replies"), source.get("replyCount"))),
        "publishedAt": first_non_empty(source.get("publishedAt"), source.get("createdAt"), source.get("date")),
        "platform": item.get("platform", ""),
        "publishedUrl": item.get("publishedUrl", ""),
        "sourceEvidence": capture.get("sourceEvidence", ""),
    }


def comment_metrics(text: str) -> dict[str, Any]:
    return {
        "likes": metric_label_int(text, "likes?|upvotes?"),
        "replies": metric_label_int(text, "replies?|reply"),
    }


def metric_label_int(text: str, label: str) -> int | None:
    match = re.search(rf"(?i)(?:{label})\s*:\s*(\d+)", text) or re.search(rf"(?i)(\d+)\s*(?:{label})", text)
    return int(match.group(1)) if match else None


def strip_comment_metrics(text: str) -> str:
    text = re.sub(r"(?i)\b(?:likes?|upvotes?|replies?|reply)\s*:\s*\d+\b", "", text)
    text = re.sub(r"(?i)\b\d+\s*(?:likes?|upvotes?|replies?|reply)\b", "", text)
    return normalize_space(text)


def is_comment_like(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "?",
        "need",
        "wish",
        "solved",
        "workflow",
        "pricing",
        "price",
        "integration",
        "api",
        "support",
        "how ",
        "what ",
        "why ",
        "can ",
        "does ",
        "try",
        "buy",
        "demo",
    ]
    return any(marker in lowered for marker in markers)


def looks_like_metric_line(line: str) -> bool:
    lowered = line.lower()
    if ":" not in line:
        return False
    metric_labels = ["views", "plays", "likes", "comments", "favorites", "shares", "revenue", "orders"]
    return sum(1 for label in metric_labels if label in lowered) >= 2


def demand_signals_for_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for index, comment in enumerate(comments, start=1):
        text = comment.get("text", "")
        for signal_type in detect_signal_types(text):
            signals.append(
                {
                    "type": signal_type,
                    "commentIndex": index,
                    "platform": comment.get("platform", ""),
                    "publishedUrl": comment.get("publishedUrl", ""),
                    "excerpt": text[:180],
                    "sourceEvidence": comment.get("sourceEvidence", ""),
                }
            )
    return signals


def detect_signal_types(text: str) -> list[str]:
    lowered = text.lower()
    rules = {
        "question": ["?", "how ", "what ", "why ", "where ", "when ", "can ", "does ", "is ", "are "],
        "pricing": ["pricing", "price", "cost", "paid", "free", "plan", "subscription"],
        "integration": ["integration", "integrate", "zapier", "api", "webhook", "slack", "notion"],
        "feature_request": ["need", "wish", "support", "add ", "can you", "please add"],
        "pain_point": ["slow", "hard", "problem", "manual", "workflow", "stuck", "solved"],
        "objection": ["expensive", "confusing", "concern", "too much", "doesn't", "do not", "dont"],
        "cta_intent": ["try", "buy", "sign up", "demo", "download", "where can i get"],
    }
    result = []
    for signal_type, markers in rules.items():
        if any(marker in lowered for marker in markers):
            result.append(signal_type)
    return result


def dedupe_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for comment in comments:
        text = normalize_space(comment.get("text"))
        if not text:
            continue
        key = (normalize_space(comment.get("author")).lower(), text.lower())
        if key in seen:
            continue
        item = dict(comment)
        item["text"] = text
        result.append(item)
        seen.add(key)
    return result


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
        "risk verification",
        "security verification",
    ]
    if any(marker in text for marker in blocked):
        return "capture_looks_like_login_captcha_verification_or_access_denied"
    return ""


def with_manual_request(out_dir: Path, item: dict[str, Any], result: dict[str, Any], reason: str) -> dict[str, Any]:
    request_path = write_manual_evidence_request(out_dir, item, result, reason)
    result.update(
        {
            "status": "publish_pending" if reason == "publish_pending" else "queued_manual_evidence",
            "reason": reason,
            "evidenceRequest": str(request_path),
            "commentCount": 0,
            "comments": [],
            "demandSignals": [],
        }
    )
    return result


def write_manual_evidence_request(out_dir: Path, item: dict[str, Any], result: dict[str, Any], reason: str) -> Path:
    directory = capture_dir(out_dir) / "manual-evidence"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe_slug(result.get('id') or item.get('publishedUrl') or 'comment-evidence')}.md"
    path.write_text(render_manual_request(item, reason) + "\n", encoding="utf-8")
    return path


def build_report(args: argparse.Namespace, items: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    all_comments = [comment for item in results for comment in item.get("comments", [])]
    all_signals = [signal for item in results for signal in item.get("demandSignals", [])]
    summary = summarize(results, all_comments, all_signals)
    directory = capture_dir(Path(args.out_dir))
    return {
        "generatedAt": TODAY,
        "status": report_status(items, summary),
        "input": {
            "publishedItemsJson": args.published_items_json,
            "publishedUrls": args.published_url,
            "structuredJson": args.structured_json or "",
            "htmlFile": args.html_file or "",
            "textFile": args.text_file or "",
            "captureBrowserAssisted": args.capture_browser_assisted,
            "dryRun": args.dry_run,
        },
        "summary": summary,
        "items": results,
        "comments": all_comments,
        "demandSignals": all_signals,
        "artifacts": {
            "commentEvidenceExport": str(directory / "comment-evidence-export.json"),
        },
        "nextActions": next_actions(summary, directory),
        "guardrails": guardrails(),
    }


def summarize(results: list[dict[str, Any]], comments: list[dict[str, Any]], signals: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    platforms: dict[str, int] = {}
    signal_counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        platform = str(result.get("platform") or "unknown")
        platforms[platform] = platforms.get(platform, 0) + 1
    for signal in signals:
        signal_type = str(signal.get("type") or "unknown")
        signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
    return {
        "itemsChecked": len(results),
        "commentCount": len(comments),
        "commentsWithMetrics": sum(1 for comment in comments if comment.get("likes") is not None or comment.get("replies") is not None),
        "demandSignalCount": len(signals),
        "statuses": dict(sorted(statuses.items())),
        "platforms": dict(sorted(platforms.items())),
        "demandSignalCounts": dict(sorted(signal_counts.items())),
    }


def report_status(items: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    if not items:
        return "waiting_published_urls"
    if summary["commentCount"] and summary["commentCount"] < summary["itemsChecked"]:
        return "partial_ready"
    if summary["commentCount"]:
        return "ready"
    if summary["statuses"].get("queued_manual_evidence"):
        return "queued_manual_evidence"
    return "waiting_comment_evidence"


def write_outputs(out_dir: Path, report: dict[str, Any]) -> None:
    directory = capture_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    export = {
        "generatedAt": TODAY,
        "source": "comment_evidence_capture",
        "records": report["items"],
        "comments": report["comments"],
        "demandSignals": report["demandSignals"],
        "guardrails": guardrails(),
    }
    (directory / "comment-evidence-capture.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "comment-evidence-capture.md").write_text(render_markdown(report) + "\n", encoding="utf-8")
    (directory / "comment-evidence-export.json").write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Comment Evidence Capture",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Items checked: {report['summary']['itemsChecked']}",
        f"- Comments: {report['summary']['commentCount']}",
        f"- Demand signals: {report['summary']['demandSignalCount']}",
        f"- Export: {report['artifacts']['commentEvidenceExport']}",
        "",
        "## Items",
    ]
    for item in report["items"]:
        lines.extend(
            [
                "",
                f"### {item.get('id', 'item')} - {item.get('platform', '')}",
                f"- Status: `{item.get('status', '')}`",
                f"- URL: {item.get('publishedUrl') or 'missing'}",
                f"- Comments: {item.get('commentCount', len(item.get('comments', [])))}",
            ]
        )
        if item.get("reason"):
            lines.append(f"- Reason: {item['reason']}")
        if item.get("evidenceRequest"):
            lines.append(f"- Evidence request: {item['evidenceRequest']}")
    lines.extend(["", "## Demand Signals"])
    if report["summary"]["demandSignalCounts"]:
        for signal_type, count in report["summary"]["demandSignalCounts"].items():
            lines.append(f"- {signal_type}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {item}" for item in report["nextActions"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in report["guardrails"]])
    return "\n".join(lines)


def render_manual_request(item: dict[str, Any], reason: str) -> str:
    return "\n".join(
        [
            "# Comment Evidence Request",
            "",
            f"- Platform: {item.get('platform', '')}",
            f"- URL: {item.get('publishedUrl') or 'missing'}",
            f"- Title: {item.get('title') or 'unknown'}",
            f"- Reason: `{reason}`",
            "",
            "## Required Evidence",
            "- Browser-visible public comments, screenshot OCR, or official platform comment export.",
            "- Include visible likes/replies per comment when available.",
            "- Do not provide cookies, passwords, tokens, private analytics endpoints, or captcha bypass outputs.",
            "",
            "## Safe Import",
            "",
            "```bash",
            "python scripts/comment_evidence_capture.py --text-file \"<visible-comments.txt>\" --out-dir \"<promotion-output>\"",
            "```",
        ]
    )


def next_actions(summary: dict[str, Any], directory: Path) -> list[str]:
    if not summary["commentCount"]:
        return ["Import public/browser-visible comments or platform exports before comment-driven optimization."]
    return [
        "Use recurring questions and objections to revise the next hook/title variants.",
        "Feed comment demand signals into the next competitor-informed content pass.",
        f"Archive evidence export at {directory / 'comment-evidence-export.json'} with the retrospective.",
    ]


def guardrails() -> list[str]:
    return [
        "Capture only public or browser-visible comments and page text.",
        "Do not auto-login, solve captcha, bypass risk controls, or use private endpoints.",
        "Do not save cookies, passwords, API keys, OAuth tokens, or hidden browser tokens.",
        "Do not fabricate comments, likes, replies, demand signals, orders, or revenue.",
        "Treat hidden comments as manual evidence requirements, not as zero comments.",
    ]


def structured_text(value: Any) -> str:
    parts: list[str] = []
    if isinstance(value, dict):
        for key in ("title", "description", "text", "renderedText", "visibleText", "bodyText", "content", "markdown"):
            child = value.get(key)
            if isinstance(child, str):
                parts.append(child)
            elif isinstance(child, list):
                parts.extend(str(entry) for entry in child)
        for key in ("comments", "replies", "sections", "captions"):
            child = value.get(key)
            if isinstance(child, list):
                parts.extend(json.dumps(entry, ensure_ascii=False) if isinstance(entry, (dict, list)) else str(entry) for entry in child)
    elif isinstance(value, list):
        parts.extend(json.dumps(entry, ensure_ascii=False) if isinstance(entry, (dict, list)) else str(entry) for entry in value)
    return "\n".join(part for part in parts if part)


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


def source_title(args: argparse.Namespace) -> str:
    return first_non_empty(args.structured_json, args.html_file, args.text_file, "comment evidence")


def capture_dir(out_dir: Path) -> Path:
    return out_dir / REPORT_DIR


def first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def get_mapping_value(value: Any, *keys: str) -> str:
    if not isinstance(value, dict):
        return ""
    for key in keys:
        child = value.get(key)
        if child not in (None, ""):
            return str(child)
    return ""


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in items:
        key = f"{item.get('platform')}:{item.get('publishedUrl') or item.get('contentId') or item.get('source')}".lower().rstrip("/")
        if key and key not in seen:
            result.append(item)
            seen.add(key)
    return result


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


def normalize_lines(value: str) -> str:
    lines = [normalize_space(line) for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except ValueError:
        return None


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    return text if len(text) <= limit else text[-limit:]


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-") or "comment-evidence"


if __name__ == "__main__":
    main()
