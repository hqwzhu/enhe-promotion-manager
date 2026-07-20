#!/usr/bin/env python3
"""Normalize and redact MediaCrawler JSONL records for ENHE Product Promo Maker."""

from __future__ import annotations

import hashlib
import hmac
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Callable


SCHEMA_VERSION = 1
PROVIDER = "mediacrawler"
PLATFORM_ALIASES = {
    "xhs": "xiaohongshu",
    "xiaohongshu": "xiaohongshu",
    "dy": "douyin",
    "douyin": "douyin",
    "zhihu": "zhihu",
}

SENSITIVE_KEY_PARTS = ("authorization", "cookie", "signature", "token")
SENSITIVE_KEYS = {
    "abogus",
    "passportcsrf",
    "rawuserid",
    "secuid",
    "secuserid",
    "sign",
    "uid",
    "userid",
    "verifyfp",
    "xbogus",
    "xsecsource",
}
SENSITIVE_QUERY_KEYS = {
    "a_bogus",
    "access_token",
    "authorization",
    "cookie",
    "msToken",
    "refresh_token",
    "sign",
    "signature",
    "verifyFp",
    "X-Bogus",
    "xsec_source",
    "xsec_token",
}


def canonical_platform(value: str) -> str:
    platform = PLATFORM_ALIASES.get(str(value or "").strip().lower())
    if not platform:
        raise ValueError(f"Unsupported MediaCrawler platform: {value}")
    return platform


def normalize_content(platform: str, raw: dict[str, Any], evidence_path: str, salt: bytes) -> dict[str, Any]:
    normalized_platform = canonical_platform(platform)
    mapper = CONTENT_MAPPERS[normalized_platform]
    mapped = mapper(raw)
    author_value = mapped.pop("_authorHash", "")
    display_name = mapped.pop("_authorDisplayName", "")
    record = {
        "schemaVersion": SCHEMA_VERSION,
        "provider": PROVIDER,
        "platform": normalized_platform,
        **mapped,
        "authorHash": local_author_hash(author_value, salt),
        "authorDisplayName": mask_display_name(display_name),
        "capturedAt": utc_now(),
        "evidencePath": evidence_path,
    }
    return sanitize_mapping(record)


def normalize_comments(
    platform: str,
    rows: list[dict[str, Any]],
    evidence_path: str,
    salt: bytes,
) -> list[dict[str, Any]]:
    records = []
    for line_number, row in enumerate(rows, start=1):
        line_evidence = f"{evidence_path}#L{line_number}" if "#L" not in evidence_path else evidence_path
        records.append(normalize_comment(platform, row, line_evidence, salt))
    return dedupe_by(records, lambda item: (item["platform"], item["contentId"], item["commentId"]))


def normalize_comment(platform: str, raw: dict[str, Any], evidence_path: str, salt: bytes) -> dict[str, Any]:
    normalized_platform = canonical_platform(platform)
    mapper = COMMENT_MAPPERS[normalized_platform]
    mapped = mapper(raw)
    author_value = mapped.pop("_authorHash", "")
    display_name = mapped.pop("_authorDisplayName", "")
    record = {
        "schemaVersion": SCHEMA_VERSION,
        "provider": PROVIDER,
        "platform": normalized_platform,
        **mapped,
        "authorHash": local_author_hash(author_value, salt),
        "authorDisplayName": mask_display_name(display_name),
        "capturedAt": utc_now(),
        "evidencePath": evidence_path,
    }
    return sanitize_mapping(record)


def xiaohongshu_content(raw: dict[str, Any]) -> dict[str, Any]:
    note_type = clean_text(raw.get("type"))
    return {
        "contentId": clean_text(raw.get("note_id")),
        "sourceUrl": sanitize_url(clean_text(raw.get("note_url"))),
        "contentType": "short_video" if note_type == "video" else "note",
        "title": nullable_text(raw.get("title")),
        "text": nullable_text(raw.get("desc")),
        "_authorHash": clean_text(raw.get("creator_hash")),
        "_authorDisplayName": clean_text(raw.get("nickname")),
        "publishedAt": iso_timestamp(raw.get("time")),
        "sourceKeyword": nullable_text(raw.get("source_keyword")),
        "tags": string_list(raw.get("tag_list")),
        "metrics": visible_metrics(
            likes=raw.get("liked_count"),
            favorites=raw.get("collected_count"),
            comments=raw.get("comment_count"),
            shares=raw.get("share_count"),
        ),
    }


def douyin_content(raw: dict[str, Any]) -> dict[str, Any]:
    content_id = clean_text(raw.get("aweme_id"))
    return {
        "contentId": content_id,
        "sourceUrl": sanitize_url(clean_text(raw.get("aweme_url")) or f"https://www.douyin.com/video/{content_id}"),
        "contentType": "short_video",
        "title": nullable_text(raw.get("title")),
        "text": nullable_text(raw.get("desc")),
        "_authorHash": clean_text(raw.get("creator_hash")),
        "_authorDisplayName": clean_text(raw.get("nickname")),
        "publishedAt": iso_timestamp(raw.get("create_time")),
        "sourceKeyword": nullable_text(raw.get("source_keyword")),
        "tags": [],
        "metrics": visible_metrics(
            likes=raw.get("liked_count"),
            favorites=raw.get("collected_count"),
            comments=raw.get("comment_count"),
            shares=raw.get("share_count"),
        ),
    }


def zhihu_content(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "contentId": clean_text(raw.get("content_id")),
        "sourceUrl": sanitize_url(clean_text(raw.get("content_url"))),
        "contentType": clean_text(raw.get("content_type")) or "article_or_answer",
        "title": nullable_text(raw.get("title")),
        "text": nullable_text(raw.get("content_text") or raw.get("desc")),
        "_authorHash": clean_text(raw.get("creator_hash")),
        "_authorDisplayName": clean_text(raw.get("user_nickname")),
        "publishedAt": iso_timestamp(raw.get("created_time")),
        "sourceKeyword": nullable_text(raw.get("source_keyword")),
        "tags": [],
        "metrics": visible_metrics(
            likes=raw.get("voteup_count"),
            comments=raw.get("comment_count"),
        ),
    }


def xiaohongshu_comment(raw: dict[str, Any]) -> dict[str, Any]:
    content_id = clean_text(raw.get("note_id"))
    return comment_mapping(
        raw,
        content_id=content_id,
        comment_id=raw.get("comment_id"),
        parent_id=raw.get("parent_comment_id"),
        text=raw.get("content"),
        author_hash=raw.get("creator_hash"),
        display_name=raw.get("nickname"),
        created_at=raw.get("create_time"),
        likes=raw.get("like_count"),
        replies=raw.get("sub_comment_count"),
        source_url=f"https://www.xiaohongshu.com/explore/{content_id}",
    )


def douyin_comment(raw: dict[str, Any]) -> dict[str, Any]:
    content_id = clean_text(raw.get("aweme_id"))
    return comment_mapping(
        raw,
        content_id=content_id,
        comment_id=raw.get("comment_id"),
        parent_id=raw.get("parent_comment_id"),
        text=raw.get("content"),
        author_hash=raw.get("creator_hash"),
        display_name=raw.get("nickname"),
        created_at=raw.get("create_time"),
        likes=raw.get("like_count"),
        replies=raw.get("sub_comment_count"),
        source_url=f"https://www.douyin.com/video/{content_id}",
    )


def zhihu_comment(raw: dict[str, Any]) -> dict[str, Any]:
    return comment_mapping(
        raw,
        content_id=raw.get("content_id"),
        comment_id=raw.get("comment_id"),
        parent_id=raw.get("parent_comment_id"),
        text=raw.get("content"),
        author_hash=raw.get("creator_hash"),
        display_name=raw.get("user_nickname"),
        created_at=raw.get("publish_time"),
        likes=raw.get("like_count"),
        replies=raw.get("sub_comment_count"),
        source_url="",
    )


def comment_mapping(
    raw: dict[str, Any],
    *,
    content_id: Any,
    comment_id: Any,
    parent_id: Any,
    text: Any,
    author_hash: Any,
    display_name: Any,
    created_at: Any,
    likes: Any,
    replies: Any,
    source_url: str,
) -> dict[str, Any]:
    del raw
    normalized_parent = clean_text(parent_id)
    return {
        "contentId": clean_text(content_id),
        "commentId": clean_text(comment_id),
        "parentCommentId": None if normalized_parent in {"", "0"} else normalized_parent,
        "text": clean_text(text),
        "_authorHash": clean_text(author_hash),
        "_authorDisplayName": clean_text(display_name),
        "createdAt": iso_timestamp(created_at),
        "likes": optional_int(likes),
        "replyCount": optional_int(replies),
        "sourceUrl": sanitize_url(source_url),
    }


CONTENT_MAPPERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "xiaohongshu": xiaohongshu_content,
    "douyin": douyin_content,
    "zhihu": zhihu_content,
}
COMMENT_MAPPERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "xiaohongshu": xiaohongshu_comment,
    "douyin": douyin_comment,
    "zhihu": zhihu_comment,
}


def sanitize_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            if is_sensitive_key(str(key)):
                continue
            sanitized[str(key)] = sanitize_mapping(child)
        return sanitized
    if isinstance(value, list):
        return [sanitize_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_mapping(item) for item in value]
    if isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        return sanitize_url(value)
    return value


def is_sensitive_key(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", value.lower())
    return normalized in SENSITIVE_KEYS or any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_url(value: str) -> str:
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return value.strip()
    sensitive = {key.lower() for key in SENSITIVE_QUERY_KEYS}
    query = []
    for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in sensitive or lowered.startswith("utm_") or is_sensitive_key(key):
            continue
        query.append((key, item))
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, urllib.parse.urlencode(query), ""))


def local_author_hash(value: Any, salt: bytes) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return hmac.new(salt, text.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def mask_display_name(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    if "*" in text:
        return text
    if len(text) == 1:
        return "*"
    if len(text) == 2:
        return f"{text[0]}*"
    return f"{text[0]}***{text[-1]}"


def visible_metrics(
    *,
    views: Any = None,
    likes: Any = None,
    favorites: Any = None,
    comments: Any = None,
    shares: Any = None,
) -> dict[str, int | None]:
    return {
        "views": optional_int(views),
        "likes": optional_int(likes),
        "favorites": optional_int(favorites),
        "comments": optional_int(comments),
        "shares": optional_int(shares),
    }


def optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    text = clean_text(value).replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def iso_timestamp(value: Any) -> str | None:
    number = optional_int(value)
    if number is None or number <= 0:
        return None
    seconds = number / 1000 if number > 10_000_000_000 else number
    try:
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError):
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        rows = [clean_text(item.get("name") if isinstance(item, dict) else item) for item in value]
    else:
        rows = [clean_text(item) for item in re.split(r"[,，]", clean_text(value))]
    return dedupe_by([item for item in rows if item], lambda item: item)


def dedupe_by(values: list[Any], key: Callable[[Any], Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        marker = key(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def nullable_text(value: Any) -> str | None:
    return clean_text(value) or None


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()
