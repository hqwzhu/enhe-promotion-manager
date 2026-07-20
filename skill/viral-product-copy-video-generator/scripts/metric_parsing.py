"""Shared metric label and number parsing helpers."""

from __future__ import annotations

import re
from typing import Any


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
    "stars",
    "forks",
    "watchers",
    "openIssues",
]

METRIC_ALIASES = {
    "views": [
        "views?",
        "plays?",
        "impressions?",
        "reads?",
        "播放(?:量)?",
        "浏览(?:量)?",
        "观看(?:量)?",
        "曝光(?:量)?",
        "阅读(?:量)?",
    ],
    "likes": ["likes?", "点赞", "赞", "喜欢"],
    "favorites": ["favorites?", "saves?", "收藏", "保存"],
    "comments": ["comments?", "评论", "留言"],
    "shares": ["shares?", "转发", "分享"],
    "clicks": ["clicks?", "点击", "访问(?:量)?"],
    "messages": ["messages?", "私信", "咨询", "会话"],
    "leads": ["leads?", "线索", "留资", "注册"],
    "orders": ["orders?", "订单", "成交单"],
    "revenue": ["revenue", "gmv", "sales", "收入", "营收", "销售额", "成交额"],
    "stars": ["stars?", "星标"],
    "forks": ["forks?"],
    "watchers": ["watchers?", "subscribers?", "followers?", "订阅", "粉丝", "关注者"],
    "openIssues": ["open\\s*issues?", "issues?"],
}

NUMBER_PATTERN = (
    r"(?P<number>"
    r"(?:(?:[$¥￥€£]|RMB|CNY)\s*)?"
    r"[+-]?\d+(?:,\d{3})*(?:\.\d+)?"
    r"(?:\s*(?:万|亿|千|百|k|m|b|w))?\+?"
    r"(?:\s*元)?"
    r")"
)


def metric_value(value: Any) -> dict[str, Any]:
    raw = "" if value is None else str(value).strip()
    return {"raw": raw, "normalized": parse_metric_number(raw)}


def parse_metric_number(value: Any) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    text = (
        text.replace(",", "")
        .replace("$", "")
        .replace("¥", "")
        .replace("￥", "")
        .replace("€", "")
        .replace("£", "")
        .replace("元", "")
        .replace("+", "")
        .replace(" ", "")
    )
    text = re.sub(r"^(?:RMB|CNY)", "", text, flags=re.IGNORECASE)
    multiplier = 1.0
    suffix = text[-1:].lower()
    if suffix in {"k", "千"}:
        multiplier = 1_000.0
        text = text[:-1]
    elif suffix in {"w", "万"}:
        multiplier = 10_000.0
        text = text[:-1]
    elif suffix == "m":
        multiplier = 1_000_000.0
        text = text[:-1]
    elif suffix == "亿":
        multiplier = 100_000_000.0
        text = text[:-1]
    elif suffix == "百":
        multiplier = 100.0
        text = text[:-1]
    elif suffix == "b":
        multiplier = 1_000_000_000.0
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def extract_metrics(text: str, fields: list[str] | None = None) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    selected = fields or METRIC_FIELDS
    labels = label_tokens(text, selected)
    numbers = number_tokens(text)
    if not labels or not numbers:
        return metrics
    preferred = preferred_direction(text, labels, numbers)
    used_numbers: set[int] = set()
    for label in labels:
        field = label["field"]
        if field in metrics:
            continue
        candidates = adjacent_number_candidates(text, label, numbers, used_numbers)
        if not candidates:
            continue
        candidates.sort(
            key=lambda candidate: (
                0 if candidate["direction"] == preferred else 1,
                candidate["distance"],
                candidate["start"],
            )
        )
        best = candidates[0]
        metrics[field] = metric_value(best["raw"])
        used_numbers.add(best["index"])
    return metrics


def label_tokens(text: str, fields: list[str]) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for field in fields:
        label = label_pattern(field)
        if not label:
            continue
        for match in re.finditer(label, text, flags=re.IGNORECASE):
            tokens.append({"type": "label", "field": field, "start": match.start(), "end": match.end()})
    tokens.sort(key=lambda token: (token["start"], token["end"]))
    return tokens


def number_tokens(text: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for match in re.finditer(NUMBER_PATTERN, text, flags=re.IGNORECASE):
        if not valid_number_span(text, match.start(), match.end()):
            continue
        tokens.append({"type": "number", "raw": match.group("number"), "start": match.start(), "end": match.end()})
    return tokens


def valid_number_span(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if before and before.isascii() and (before.isalnum() or before in "/._-"):
        return False
    if after and after.isascii() and (after.isalpha() or after in "/._-"):
        return False
    return True


def preferred_direction(text: str, labels: list[dict[str, Any]], numbers: list[dict[str, Any]]) -> str:
    pairs: list[dict[str, Any]] = []
    for label in labels:
        for number in numbers:
            direction = adjacent_direction(text, label, number)
            if direction:
                pairs.append({"start": min(label["start"], number["start"]), "direction": direction})
    if not pairs:
        return "right"
    pairs.sort(key=lambda pair: pair["start"])
    return pairs[0]["direction"]


def adjacent_number_candidates(
    text: str,
    label: dict[str, Any],
    numbers: list[dict[str, Any]],
    used_numbers: set[int],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, number in enumerate(numbers):
        if index in used_numbers:
            continue
        direction = adjacent_direction(text, label, number)
        if not direction:
            continue
        candidates.append(
            {
                "index": index,
                "raw": number["raw"],
                "direction": direction,
                "distance": abs(number["start"] - label["start"]),
                "start": min(label["start"], number["start"]),
            }
        )
    return candidates


def adjacent_direction(text: str, label: dict[str, Any], number: dict[str, Any]) -> str | None:
    if number["end"] <= label["start"]:
        gap = text[number["end"] : label["start"]]
        return "left" if is_metric_separator(gap) else None
    if label["end"] <= number["start"]:
        gap = text[label["end"] : number["start"]]
        return "right" if is_metric_separator(gap) else None
    return None


def is_metric_separator(value: str) -> bool:
    return bool(re.fullmatch(r"[\s:;\uFF1A=|,./\\\-]*", value))


def label_pattern(field: str) -> str:
    aliases = METRIC_ALIASES.get(field, [])
    return "|".join(f"(?:{item})" for item in aliases)
