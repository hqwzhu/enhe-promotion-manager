#!/usr/bin/env python3
"""ENHE Product Promo Maker CLI for guarded local platform evidence collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import mediacrawler_contract
import mediacrawler_downstream
import mediacrawler_sidecar


REMOVED_FIELD_NAMES = [
    "Authorization",
    "Cookie",
    "Token",
    "access_token",
    "msToken",
    "raw user IDs",
    "signature",
    "verifyFp",
    "xsec_token",
]


def main(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    install = mediacrawler_sidecar.SidecarInstall(Path(args.sidecar_root)) if args.sidecar_root else mediacrawler_sidecar.default_install()
    if args.command == "setup":
        if args.check:
            report = mediacrawler_sidecar.check_setup(install)
        else:
            report = mediacrawler_sidecar.install_sidecar(install)
    else:
        report = collect(args, install)
    print(json.dumps(mediacrawler_contract.sanitize_mapping(report), ensure_ascii=False, indent=2))
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect guarded local platform evidence through a pinned MediaCrawler sidecar.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Check or explicitly install the local MediaCrawler sidecar.")
    setup_mode = setup.add_mutually_exclusive_group(required=True)
    setup_mode.add_argument("--check", action="store_true", help="Read-only environment and pinned-version check.")
    setup_mode.add_argument("--install", action="store_true", help="Explicitly clone and install the pinned sidecar over the network.")
    setup.add_argument("--sidecar-root", default="", help="Override the local sidecar root for controlled installations or tests.")

    collect_parser = subparsers.add_parser("collect", help="Collect and normalize local platform evidence.")
    collect_parser.add_argument("--platform", required=True, choices=["xiaohongshu", "douyin", "zhihu"])
    collect_parser.add_argument("--mode", required=True, choices=["search", "detail", "creator"])
    collect_parser.add_argument("--query", default="", help="Required in search mode.")
    collect_parser.add_argument("--target", default="", help="Content URL/ID for detail mode or creator URL/ID for creator mode.")
    collect_parser.add_argument("--max-contents", type=bounded_contents, default=mediacrawler_sidecar.MAX_CONTENTS)
    collect_parser.add_argument("--max-comments", type=bounded_comments, default=mediacrawler_sidecar.MAX_COMMENTS)
    collect_parser.add_argument("--include-sub-comments", action="store_true")
    collect_parser.add_argument("--keep-raw", action="store_true")
    collect_parser.add_argument("--timeout-seconds", type=bounded_timeout, default=mediacrawler_sidecar.DEFAULT_TIMEOUT_SECONDS)
    collect_parser.add_argument("--fixture-dir", default="", help="Offline sanitized MediaCrawler fixture directory.")
    collect_parser.add_argument("--published-items-json", default="", help="Optional published-items registry for strict own-metric matching.")
    collect_parser.add_argument("--sidecar-root", default="", help="Override the local sidecar root for controlled installations or tests.")
    collect_parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args(list(argv) if argv is not None else None)


def collect(args: argparse.Namespace, install: mediacrawler_sidecar.SidecarInstall) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    detail_context_query = ""
    if args.platform == "xiaohongshu" and args.mode == "detail":
        detail_context_query = resolve_xiaohongshu_detail_query(out_dir, args.target)
    request = mediacrawler_sidecar.CollectRequest(
        platform=args.platform,
        mode=args.mode,
        query=args.query,
        target=args.target,
        max_contents=args.max_contents,
        max_comments=args.max_comments,
        include_sub_comments=args.include_sub_comments,
        timeout_seconds=args.timeout_seconds,
        detail_context_query=detail_context_query,
    )
    started_monotonic = time.monotonic()
    started_at = utc_now()
    run_id = new_run_id(request)
    run_dir = out_dir / "reports" / "promotion-manager" / "platform-data" / "mediacrawler" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = base_manifest(run_id, run_dir, request, started_at, "fixture" if args.fixture_dir else "sidecar")
    write_manifest(run_dir, manifest)

    payload: dict[str, Any] = {}
    status = "error"
    reason = ""
    retry_count = 0
    raw_kept = False
    warning = ""
    if args.fixture_dir:
        payload = normalize_fixture_dir(Path(args.fixture_dir), request.platform, run_dir)
        status = payload["status"]
    else:
        setup = mediacrawler_sidecar.check_setup(install)
        if setup["status"] != "ready":
            status = "provider_unavailable"
            reason = "The pinned local MediaCrawler sidecar is not ready."
        elif not install.identity_salt_path.is_file():
            status = "provider_unavailable"
            reason = "The local identity salt is missing; rerun explicit sidecar setup."
        else:
            salt = install.identity_salt_path.read_bytes()

            def consume(raw_dir: Path) -> dict[str, Any]:
                return normalize_raw_dir(
                    raw_dir,
                    request.platform,
                    run_dir,
                    salt,
                    content_limit=request.max_contents,
                    comments_per_content_limit=request.max_comments,
                )

            try:
                result = mediacrawler_sidecar.run_sidecar(
                    install,
                    request,
                    run_dir,
                    raw_consumer=consume,
                    keep_raw=args.keep_raw,
                )
            except RuntimeError as exc:
                result = mediacrawler_sidecar.RunResult(status="provider_unavailable", reason=mediacrawler_sidecar.safe_tail(str(exc)))
            payload = result.payload
            status = result.status
            reason = result.reason
            retry_count = result.retry_count
            raw_kept = result.keep_raw and (run_dir / "raw").exists()
            warning = result.warning

    contents = payload.pop("contents", [])
    comments = payload.pop("comments", [])
    artifacts: dict[str, Any] = {}
    if contents or comments:
        published_items = load_published_items(args.published_items_json, out_dir)
        artifacts = mediacrawler_downstream.write_downstream_artifacts(
            out_dir,
            run_dir,
            contents,
            comments,
            published_items=published_items,
        )

    finished_at = utc_now()
    manifest.update(
        {
            "status": status,
            "reason": reason,
            "finishedAt": finished_at,
            "durationSeconds": round(time.monotonic() - started_monotonic, 3),
            "counts": payload.get("counts", empty_counts()),
            "retryCount": retry_count,
            "raw": {
                "keepRequested": bool(args.keep_raw),
                "kept": raw_kept,
                "cleaned": not (run_dir / "raw").exists(),
                "warning": warning,
            },
            "redaction": {
                "schemaVersion": 1,
                "removedFieldNames": REMOVED_FIELD_NAMES,
                "rawUserIdsPersisted": False,
            },
            "artifacts": artifacts,
            "nextActions": next_actions(status),
        }
    )
    write_manifest(run_dir, manifest)
    return {
        "status": status,
        "reason": reason,
        "runId": run_id,
        "runDir": str(run_dir),
        "manifest": str(run_dir / "run-manifest.json"),
        "nextActions": manifest["nextActions"],
    }


def normalize_fixture_dir(fixture_dir: Path, platform: str, run_dir: Path) -> dict[str, Any]:
    content_rows = read_jsonl_files([fixture_dir / f"{platform}-contents.jsonl"])
    comment_rows = read_jsonl_files([fixture_dir / f"{platform}-comments.jsonl"])
    fixture_salt = hashlib.sha256(b"enhe-mediacrawler-offline-fixture").digest()
    return normalize_rows(platform, content_rows, comment_rows, run_dir, fixture_salt)


def normalize_raw_dir(
    raw_dir: Path,
    platform: str,
    run_dir: Path,
    salt: bytes,
    *,
    content_limit: int | None = None,
    comments_per_content_limit: int | None = None,
) -> dict[str, Any]:
    content_paths = sorted(path for path in raw_dir.rglob("*.jsonl") if "contents" in path.name.lower())
    comment_paths = sorted(path for path in raw_dir.rglob("*.jsonl") if "comments" in path.name.lower())
    return normalize_rows(
        platform,
        read_jsonl_files(content_paths),
        read_jsonl_files(comment_paths),
        run_dir,
        salt,
        content_limit=content_limit,
        comments_per_content_limit=comments_per_content_limit,
    )


def normalize_rows(
    platform: str,
    content_rows: list[dict[str, Any]],
    comment_rows: list[dict[str, Any]],
    run_dir: Path,
    salt: bytes,
    *,
    content_limit: int | None = None,
    comments_per_content_limit: int | None = None,
) -> dict[str, Any]:
    normalized_contents = []
    dropped_contents = 0
    for row in content_rows:
        record = mediacrawler_contract.normalize_content(platform, row, "", salt)
        if not record.get("contentId"):
            dropped_contents += 1
            continue
        normalized_contents.append(record)
    normalized_contents, duplicate_contents = dedupe_records(
        normalized_contents,
        lambda item: (item.get("platform"), item.get("contentId")),
    )
    content_limit = max(0, content_limit) if content_limit is not None else None
    limited_contents = 0
    if content_limit is not None:
        limited_contents = max(0, len(normalized_contents) - content_limit)
        normalized_contents = normalized_contents[:content_limit]
    for index, record in enumerate(normalized_contents, start=1):
        record["evidencePath"] = f"contents.jsonl#L{index}"

    mapped_comments = mediacrawler_contract.normalize_comments(platform, comment_rows, "comments.jsonl", salt)
    normalized_comments = []
    dropped_comments = 0
    for record in mapped_comments:
        if not record.get("contentId") or not record.get("commentId") or not record.get("text"):
            dropped_comments += 1
            continue
        normalized_comments.append(record)
    comments_per_content_limit = (
        max(0, comments_per_content_limit) if comments_per_content_limit is not None else None
    )
    limited_comments = 0
    if content_limit is not None:
        kept_content_ids = {record["contentId"] for record in normalized_contents}
        kept_comments = [record for record in normalized_comments if record["contentId"] in kept_content_ids]
        limited_comments += len(normalized_comments) - len(kept_comments)
        normalized_comments = kept_comments
    if comments_per_content_limit is not None:
        comment_counts: dict[str, int] = {}
        kept_comments = []
        for record in normalized_comments:
            content_id = record["contentId"]
            if comment_counts.get(content_id, 0) >= comments_per_content_limit:
                limited_comments += 1
                continue
            comment_counts[content_id] = comment_counts.get(content_id, 0) + 1
            kept_comments.append(record)
        normalized_comments = kept_comments
    for index, record in enumerate(normalized_comments, start=1):
        record["evidencePath"] = f"comments.jsonl#L{index}"

    mediacrawler_downstream.write_jsonl(run_dir / "contents.jsonl", normalized_contents)
    mediacrawler_downstream.write_jsonl(run_dir / "comments.jsonl", normalized_comments)
    if normalized_contents and (normalized_comments or not comment_rows):
        status = "ready"
    elif normalized_contents or normalized_comments:
        status = "partial_ready"
    else:
        status = "no_results"
    return {
        "status": status,
        "contents": normalized_contents,
        "comments": normalized_comments,
        "counts": {
            "sourceContents": len(content_rows),
            "sourceComments": len(comment_rows),
            "normalizedContents": len(normalized_contents),
            "normalizedComments": len(normalized_comments),
            "droppedContents": dropped_contents,
            "droppedComments": dropped_comments,
            "duplicateContents": duplicate_contents,
            "duplicateComments": max(0, len(comment_rows) - len(mapped_comments)),
            "limitedContents": limited_contents,
            "limitedComments": limited_comments,
        },
    }


def read_jsonl_files(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def resolve_xiaohongshu_detail_query(out_dir: Path, target: str) -> str:
    target_id = mediacrawler_sidecar.xiaohongshu_content_id(target)
    if not target_id:
        return ""
    root = Path(out_dir) / "reports" / "promotion-manager" / "platform-data" / "mediacrawler"
    paths = sorted(root.glob("*/contents.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in paths:
        for row in read_jsonl_files([path]):
            if (
                row.get("platform") == "xiaohongshu"
                and str(row.get("contentId") or "").strip() == target_id
                and str(row.get("sourceKeyword") or "").strip()
            ):
                return str(row["sourceKeyword"]).strip()
    return ""


def load_published_items(override: str, out_dir: Path) -> list[dict[str, Any]]:
    path = Path(override) if override else out_dir / "reports" / "promotion-manager" / "published-items" / "published-items.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("records", "items", "publishedItems", "published_items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]
    return []


def base_manifest(
    run_id: str,
    run_dir: Path,
    request: mediacrawler_sidecar.CollectRequest,
    started_at: str,
    capture_mode: str,
) -> dict[str, Any]:
    target = request.target.strip()
    if target.lower().startswith(("http://", "https://")):
        target = mediacrawler_contract.sanitize_url(target)
    return {
        "schemaVersion": 1,
        "runId": run_id,
        "provider": "mediacrawler",
        "upstreamRepository": mediacrawler_sidecar.UPSTREAM_REPOSITORY,
        "upstreamCommit": mediacrawler_sidecar.UPSTREAM_COMMIT,
        "platform": request.platform,
        "mode": request.mode,
        "captureMode": capture_mode,
        "query": request.query.strip(),
        "target": target,
        "limits": {
            "maxContents": request.max_contents,
            "maxFirstLevelCommentsPerContent": request.max_comments,
            "includeSubComments": request.include_sub_comments,
            "concurrency": 1,
            "minimumPageIntervalSeconds": 2,
            "timeoutSeconds": request.timeout_seconds,
        },
        "status": "error",
        "reason": "run_in_progress_or_interrupted",
        "startedAt": started_at,
        "finishedAt": None,
        "durationSeconds": None,
        "runDirectory": str(run_dir),
        "counts": empty_counts(),
        "retryCount": 0,
        "raw": {"keepRequested": False, "kept": False, "cleaned": False, "warning": ""},
        "redaction": {"schemaVersion": 1, "removedFieldNames": REMOVED_FIELD_NAMES, "rawUserIdsPersisted": False},
        "artifacts": {},
        "nextActions": [],
    }


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    sanitized = mediacrawler_contract.sanitize_mapping(manifest)
    (run_dir / "run-manifest.json").write_text(json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_actions(status: str) -> list[str]:
    if status == "waiting_login":
        return ["Log in manually in the visible local Chrome window, then rerun the same command."]
    if status == "manual_verification_required":
        return ["Complete the captcha, slider, QR confirmation, or account verification manually; automatic solving is disabled."]
    if status == "blocked_by_platform":
        return ["Stop collection and wait for the platform risk control to clear; do not retry in a loop."]
    if status == "provider_unavailable":
        return [
            "Run `python scripts/promotion_manager.py platform-data setup --check` for read-only diagnostics.",
            "Continue with the existing Firecrawl, browser-visible, or manual evidence workflow.",
        ]
    if status == "no_results":
        return ["Review the query or target manually; no automatic retry loop will run."]
    return []


def dedupe_records(values: list[dict[str, Any]], key: Any) -> tuple[list[dict[str, Any]], int]:
    result = []
    seen = set()
    duplicates = 0
    for value in values:
        marker = key(value)
        if marker in seen:
            duplicates += 1
            continue
        seen.add(marker)
        result.append(value)
    return result, duplicates


def empty_counts() -> dict[str, int]:
    return {
        "sourceContents": 0,
        "sourceComments": 0,
        "normalizedContents": 0,
        "normalizedComments": 0,
        "droppedContents": 0,
        "droppedComments": 0,
        "duplicateContents": 0,
        "duplicateComments": 0,
        "limitedContents": 0,
        "limitedComments": 0,
    }


def bounded_contents(value: str) -> int:
    return bounded_int(value, "max-contents", 1, mediacrawler_sidecar.MAX_CONTENTS)


def bounded_comments(value: str) -> int:
    return bounded_int(value, "max-comments", 0, mediacrawler_sidecar.MAX_COMMENTS)


def bounded_timeout(value: str) -> int:
    return bounded_int(value, "timeout-seconds", 1, mediacrawler_sidecar.MAX_TIMEOUT_SECONDS)


def bounded_int(value: str, name: str, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise argparse.ArgumentTypeError(f"{name} must be between {minimum} and {maximum}")
    return number


def new_run_id(request: mediacrawler_sidecar.CollectRequest) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{request.platform}-{request.mode}-{uuid.uuid4().hex[:8]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main(sys.argv[1:])
