#!/usr/bin/env python3
"""Attribute real business exports to proven published promotion content."""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

import metrics_intake


TODAY = date.today().isoformat()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    published_items = load_published_items(args, out_dir)
    orders, sources = load_order_rows(args)
    report = build_report(published_items, orders, sources)
    write_report(out_dir, report)
    print(f"Business attribution report written to: {(business_dir(out_dir) / 'business-attribution.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attribute real order/revenue exports to published promotion content.")
    parser.add_argument("--business-csv", action="append", default=[], help="CSV export containing order/revenue rows.")
    parser.add_argument("--business-xlsx", action="append", default=[], help="Excel .xlsx export containing order/revenue rows.")
    parser.add_argument("--business-json", action="append", default=[], help="JSON export containing order/revenue rows.")
    parser.add_argument("--business-text", action="append", default=[], help="Text evidence containing order/revenue rows.")
    parser.add_argument("--published-items-json", action="append", default=[], help="Published items JSON evidence.")
    parser.add_argument("--published-url", action="append", default=[], help="Published URL or platform=url evidence.")
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def load_published_items(args: argparse.Namespace, out_dir: Path) -> list[dict[str, Any]]:
    paths = [Path(value) for value in args.published_items_json]
    default_path = out_dir / "reports/promotion-manager/published-items/published-items.json"
    if default_path.exists() and default_path not in paths:
        paths.append(default_path)
    items: list[dict[str, Any]] = []
    for path in paths:
        data = read_json(path)
        records = list_records(data)
        for record in records:
            if isinstance(record, dict):
                item = normalize_published_item(record, str(path))
                if item:
                    items.append(item)
    for value in args.published_url:
        item = published_item_from_cli(value)
        if item:
            items.append(item)
    return dedupe_items(items)


def published_item_from_cli(value: str) -> dict[str, Any]:
    platform = ""
    url = value.strip()
    if "=" in url:
        platform, url = [part.strip() for part in url.split("=", 1)]
    platform = platform or metrics_intake.choose_platform("auto", url)
    return {
        "platform": platform,
        "publishedUrl": url,
        "contentId": content_id_from_url(platform, url),
        "title": "",
        "publishStatus": "published",
        "source": "cli",
        "evidence": [url],
    }


def normalize_published_item(item: dict[str, Any], source: str) -> dict[str, Any]:
    url = get_alias(item, "publishedUrl", "url", "link", "sourceUrl")
    platform = get_alias(item, "platform") or metrics_intake.choose_platform("auto", url or source)
    content_id = get_alias(item, "contentId", "videoId", "repo", "id", "noteId") or content_id_from_url(platform, url)
    status = get_alias(item, "publishStatus", "status") or "published"
    if not platform:
        return {}
    return {
        "platform": platform.lower(),
        "publishedUrl": url,
        "contentId": content_id,
        "title": get_alias(item, "title", "name", "headline"),
        "publishStatus": "published" if url and status in {"", "ready", "published"} else status,
        "source": source,
        "evidence": split_evidence(get_alias(item, "evidence", "evidenceUrl", "screenshot", "export")) or [source],
    }


def load_order_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for value in args.business_csv:
        path = Path(value)
        loaded = rows_from_csv(path)
        rows.extend(loaded)
        sources.append({"type": "business_csv", "source": str(path), "status": "loaded", "rowCount": len(loaded)})
    for value in args.business_xlsx:
        path = Path(value)
        loaded = rows_from_xlsx(path)
        rows.extend(loaded)
        sources.append({"type": "business_xlsx", "source": str(path), "status": "loaded", "rowCount": len(loaded)})
    for value in args.business_json:
        path = Path(value)
        loaded = rows_from_json(path)
        rows.extend(loaded)
        sources.append({"type": "business_json", "source": str(path), "status": "loaded", "rowCount": len(loaded)})
    for value in args.business_text:
        path = Path(value)
        loaded = rows_from_text(path)
        rows.extend(loaded)
        sources.append({"type": "business_text", "source": str(path), "status": "loaded", "rowCount": len(loaded)})
    return rows, sources


def rows_from_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [normalize_order_row(row, str(path), index) for index, row in enumerate(csv.DictReader(handle), start=1)]


def rows_from_xlsx(path: Path) -> list[dict[str, Any]]:
    rows = metrics_intake.xlsx_rows(path)
    if not rows:
        return []
    headers = [str(value).strip() for value in rows[0]]
    records = []
    for index, row in enumerate(rows[1:], start=1):
        if not any(str(value).strip() for value in row):
            continue
        item = {header: row[column] if column < len(row) else "" for column, header in enumerate(headers) if header}
        records.append(normalize_order_row(item, str(path), index))
    return records


def rows_from_json(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    return [normalize_order_row(row, str(path), index) for index, row in enumerate(list_records(data), start=1) if isinstance(row, dict)]


def rows_from_text(path: Path) -> list[dict[str, Any]]:
    record = metrics_intake.record_from_text(path.read_text(encoding="utf-8"), str(path), "auto")
    metrics = record.get("metrics") or {}
    if not any(metric_raw(metrics, field) for field in ("orders", "revenue", "clicks", "leads")):
        return []
    row = {
        "platform": record.get("platform", ""),
        "publishedUrl": record.get("publishedUrl", ""),
        "contentId": record.get("contentId", ""),
        "title": record.get("title", ""),
        "orders": metric_raw(metrics, "orders"),
        "revenue": metric_raw(metrics, "revenue"),
        "clicks": metric_raw(metrics, "clicks"),
        "leads": metric_raw(metrics, "leads"),
    }
    return [normalize_order_row(row, str(path), 1)]


def normalize_order_row(row: dict[str, Any], source: str, index: int) -> dict[str, Any]:
    url = get_alias(row, "publishedUrl", "contentUrl", "postUrl", "url", "link")
    referrer = get_alias(row, "referrer", "referrerUrl", "referringUrl", "sourceUrl")
    landing_page = get_alias(row, "landingPage", "landingUrl", "pageUrl", "targetUrl")
    platform_hint = get_alias(row, "platform", "utm_source", "utmSource", "source", "channel")
    platform = metrics_intake.choose_platform(platform_hint or "auto", first_non_empty(url, referrer, landing_page, source))
    content_id = get_alias(row, "contentId", "content_id", "videoId", "noteId", "repo", "utm_content", "utmContent")
    title = get_alias(row, "title", "contentTitle", "campaignName", "adName", "utm_campaign", "utmCampaign")
    revenue_raw = get_alias(row, "revenue", "amount", "total", "orderTotal", "paidAmount", "gmv", "sales")
    orders_raw = get_alias(row, "orders", "orderCount", "order_count", "quantity", "qty")
    clicks_raw = get_alias(row, "clicks", "clickCount", "click_count")
    leads_raw = get_alias(row, "leads", "leadCount", "lead_count")
    order_id = get_alias(row, "orderId", "order_id", "id", "transactionId", "transaction_id")
    status = get_alias(row, "status", "orderStatus", "paymentStatus")
    return {
        "rowId": order_id or f"row-{index:04d}",
        "source": source,
        "platform": platform,
        "publishedUrl": url,
        "referrer": referrer,
        "landingPage": landing_page,
        "contentId": content_id,
        "title": title,
        "orders": metric_number(orders_raw) if orders_raw else 1.0,
        "revenue": metric_number(revenue_raw),
        "clicks": metric_number(clicks_raw),
        "leads": metric_number(leads_raw),
        "status": status,
        "excluded": status_is_excluded(status),
    }


def build_report(
    published_items: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    attributions: dict[str, dict[str, Any]] = {}
    unmatched = []
    total_orders = 0.0
    total_revenue = 0.0
    for row in rows:
        if row.get("excluded"):
            unmatched.append(unmatched_row(row, "excluded_order_status"))
            continue
        total_orders += row.get("orders") or 0.0
        total_revenue += row.get("revenue") or 0.0
        match = match_row(row, published_items)
        if not match:
            unmatched.append(unmatched_row(row, "no_content_level_match"))
            continue
        item, rule, confidence = match
        key = item_key(item)
        current = attributions.setdefault(
            key,
            {
                "platform": item["platform"],
                "publishedUrl": item.get("publishedUrl", ""),
                "contentId": item.get("contentId", ""),
                "title": item.get("title", ""),
                "metrics": {
                    "orders": {"raw": "0", "normalized": 0.0},
                    "revenue": {"raw": "0", "normalized": 0.0},
                },
                "evidence": list(item.get("evidence", [])),
                "matchRules": [],
                "matchedOrderRows": [],
                "confidence": confidence,
            },
        )
        add_metric(current["metrics"], "orders", row.get("orders"))
        add_metric(current["metrics"], "revenue", row.get("revenue"))
        add_metric(current["metrics"], "clicks", row.get("clicks"))
        add_metric(current["metrics"], "leads", row.get("leads"))
        current["matchRules"] = unique([*current["matchRules"], rule])
        current["evidence"] = unique([*current["evidence"], row["source"]])
        current["matchedOrderRows"].append(
            {
                "rowId": row["rowId"],
                "source": row["source"],
                "orders": row.get("orders"),
                "revenue": row.get("revenue"),
                "matchRule": rule,
                "confidence": confidence,
            }
        )
        current["confidence"] = min_confidence(current["confidence"], confidence)
    attribution_list = list(attributions.values())
    export_records = [export_record(item) for item in attribution_list]
    matched_rows = sum(len(item["matchedOrderRows"]) for item in attribution_list)
    attributed_orders = sum(metric_normalized(item["metrics"], "orders") or 0.0 for item in attribution_list)
    attributed_revenue = sum(metric_normalized(item["metrics"], "revenue") or 0.0 for item in attribution_list)
    return {
        "generatedAt": TODAY,
        "status": attribution_status(rows, published_items, matched_rows, unmatched),
        "summary": {
            "publishedItems": len(published_items),
            "orderRows": len(rows),
            "matchedRows": matched_rows,
            "unmatchedRows": len(unmatched),
            "totalOrders": round(total_orders, 6),
            "totalRevenue": round(total_revenue, 6),
            "attributedOrders": round(attributed_orders, 6),
            "attributedRevenue": round(attributed_revenue, 6),
            "platforms": sorted({item["platform"] for item in attribution_list if item.get("platform")}),
        },
        "sources": sources,
        "publishedItems": published_items,
        "attributions": attribution_list,
        "unmatchedRows": unmatched,
        "export": {"records": export_records},
        "guardrails": [
            "Use only user-provided business exports and proven published item evidence.",
            "Do not infer orders or revenue from public social engagement.",
            "Do not attribute revenue from platform-only hints when no URL, content id, or title/campaign match exists.",
            "Do not store or print cookies, passwords, API keys, payment tokens, or customer secrets.",
        ],
    }


def match_row(row: dict[str, Any], items: list[dict[str, Any]]) -> tuple[dict[str, Any], str, str] | None:
    candidates = []
    for item in items:
        result = match_score(row, item)
        if result:
            candidates.append((result[0], item, result[1], result[2]))
    if not candidates:
        return None
    candidates.sort(key=lambda value: value[0], reverse=True)
    _, item, rule, confidence = candidates[0]
    return item, rule, confidence


def match_score(row: dict[str, Any], item: dict[str, Any]) -> tuple[int, str, str] | None:
    item_url = canonical_url(item.get("publishedUrl", ""))
    row_url = canonical_url(row.get("publishedUrl", ""))
    referrer = canonical_url(row.get("referrer", ""))
    landing_page = canonical_url(row.get("landingPage", ""))
    if item_url and row_url and item_url == row_url:
        return 100, "published_url", "high"
    if item_url and referrer and (item_url == referrer or item_url in referrer):
        return 95, "referrer_url", "high"
    if item_url and landing_page and (item_url == landing_page or item_url in landing_page):
        return 90, "landing_page_url", "high"
    row_platform = clean(row.get("platform")).lower()
    item_platform = clean(item.get("platform")).lower()
    if row_platform and item_platform and row_platform != item_platform:
        return None
    item_content_id = slug(item.get("contentId", ""))
    row_content_id = slug(row.get("contentId", ""))
    if item_content_id and row_content_id and item_content_id == row_content_id:
        return 85, "utm_content", "high"
    item_title = slug(item.get("title", ""))
    row_title = slug(row.get("title", ""))
    if item_platform and row_platform == item_platform and item_title and row_title and (item_title == row_title or item_title in row_title or row_title in item_title):
        return 70, "title_or_campaign", "medium"
    return None


def attribution_status(rows: list[dict[str, Any]], items: list[dict[str, Any]], matched_rows: int, unmatched: list[dict[str, Any]]) -> str:
    if not rows:
        return "waiting_business_data"
    if not items:
        return "waiting_published_items"
    if matched_rows and unmatched:
        return "partial_ready"
    if matched_rows:
        return "ready"
    return "waiting_content_level_attribution"


def export_record(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {})
    record = {
        "platform": item.get("platform", ""),
        "publishedUrl": item.get("publishedUrl", ""),
        "contentId": item.get("contentId", ""),
        "title": item.get("title", ""),
        "orders": metric_raw(metrics, "orders"),
        "revenue": metric_raw(metrics, "revenue"),
        "evidence": ";".join(item.get("evidence", [])),
        "notes": "Business attribution from real order/revenue export; match rules: " + ", ".join(item.get("matchRules", [])),
    }
    for field in ("clicks", "leads"):
        raw = metric_raw(metrics, field)
        if raw:
            record[field] = raw
    return record


def add_metric(metrics: dict[str, dict[str, Any]], field: str, value: float | None) -> None:
    if value is None:
        return
    current = metric_normalized(metrics, field) or 0.0
    total = current + float(value)
    metrics[field] = {"raw": compact_number(total), "normalized": round(total, 6)}


def metric_raw(metrics: dict[str, dict[str, Any]], field: str) -> str:
    item = metrics.get(field) or {}
    return str(item.get("raw") or "")


def metric_normalized(metrics: dict[str, dict[str, Any]], field: str) -> float | None:
    item = metrics.get(field) or {}
    value = item.get("normalized")
    return float(value) if isinstance(value, (int, float)) else None


def metric_number(value: Any) -> float | None:
    parsed = metrics_intake.parse_metric_number(str(value))
    return float(parsed) if isinstance(parsed, (int, float)) else None


def unmatched_row(row: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "rowId": row.get("rowId", ""),
        "source": row.get("source", ""),
        "platform": row.get("platform", ""),
        "publishedUrl": row.get("publishedUrl", ""),
        "referrer": row.get("referrer", ""),
        "landingPage": row.get("landingPage", ""),
        "contentId": row.get("contentId", ""),
        "title": row.get("title", ""),
        "orders": row.get("orders"),
        "revenue": row.get("revenue"),
        "reason": reason,
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = business_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "business-attribution.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "business-attribution-export.json").write_text(json.dumps(report["export"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "business-attribution.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Business Attribution",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Published items: {summary['publishedItems']}",
        f"- Order rows: {summary['orderRows']}",
        f"- Matched rows: {summary['matchedRows']}",
        f"- Unmatched rows: {summary['unmatchedRows']}",
        f"- Attributed orders: {summary['attributedOrders']}",
        f"- Attributed revenue: {summary['attributedRevenue']}",
        "",
        "## Attributions",
    ]
    for item in report["attributions"]:
        lines.extend(
            [
                "",
                f"### {item.get('platform', 'unknown')} - {item.get('title') or item.get('contentId') or item.get('publishedUrl')}",
                f"- URL: {item.get('publishedUrl') or 'unknown'}",
                f"- Match rules: {', '.join(item.get('matchRules', []))}",
                f"- Orders: {metric_raw(item['metrics'], 'orders')}",
                f"- Revenue: {metric_raw(item['metrics'], 'revenue')}",
            ]
        )
    if report["unmatchedRows"]:
        lines.extend(["", "## Unmatched Rows"])
        for row in report["unmatchedRows"]:
            lines.append(f"- {row['rowId']}: `{row['reason']}` platform={row.get('platform', '')} contentId={row.get('contentId', '')}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def business_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/business-attribution"


def list_records(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "items", "orders", "transactions", "results", "publishedItems", "published_items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    return []


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def get_alias(item: dict[str, Any], *keys: str) -> str:
    normalized = {normalize_key(key): value for key, value in item.items()}
    for key in keys:
        value = normalized.get(normalize_key(key))
        if value not in (None, ""):
            return str(value).strip()
    return ""


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", value).lower()


def status_is_excluded(value: str) -> bool:
    text = value.lower()
    return any(marker in text for marker in ("cancel", "refund", "failed", "unpaid", "void"))


def content_id_from_url(platform: str, url: str) -> str:
    if platform == "youtube":
        return metrics_intake.youtube_video_id_from_url(url)
    if platform == "github":
        return metrics_intake.github_repo_from_url(url)
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[-1] if parts else ""


def canonical_url(url: str) -> str:
    text = clean(url)
    parsed = urllib.parse.urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return text.lower().rstrip("/")
    return parsed._replace(fragment="").geturl().lower().rstrip("/")


def item_key(item: dict[str, Any]) -> str:
    return "|".join([clean(item.get("platform")).lower(), canonical_url(item.get("publishedUrl", "")), clean(item.get("contentId")).lower()])


def slug(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", clean(value).lower()).strip("-")


def compact_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(round(value, 6))


def split_evidence(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[;,]\s*", value) if item.strip()]


def first_non_empty(*values: str) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def unique(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        key = item_key(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def min_confidence(current: str, new: str) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    return current if rank.get(current, 0) <= rank.get(new, 0) else new


if __name__ == "__main__":
    main()
