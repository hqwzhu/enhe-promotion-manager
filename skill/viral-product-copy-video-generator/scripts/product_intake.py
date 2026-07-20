#!/usr/bin/env python3
"""Extract a structured product profile from a public URL, HTML, text, or rendered page snapshot."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.json_ld: list[str] = []
        self._script_type: str | None = None
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {name.lower(): value or "" for name, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = attrs_map.get("property") or attrs_map.get("name")
            content = attrs_map.get("content")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)
        elif tag == "link":
            if attrs_map.get("rel") or attrs_map.get("href"):
                self.links.append(attrs_map)
        elif tag == "script":
            self._script_type = attrs_map.get("type", "").lower()
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "script":
            if self._script_type == "application/ld+json" and self._script_parts:
                self.json_ld.append("".join(self._script_parts).strip())
            self._script_type = None
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._script_type == "application/ld+json":
            self._script_parts.append(data)


def main() -> None:
    args = parse_args()
    profile = load_profile(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "product-profile.json"
    md_path = out_dir / "product-profile.md"
    json_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(profile) + "\n", encoding="utf-8")
    print(f"Product profile written to: {json_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract product metadata from a URL, HTML file, text file, or structured page snapshot.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public product URL to fetch.")
    source.add_argument("--html-file", help="Saved product HTML file to parse.")
    source.add_argument("--text-file", help="Rendered page text captured by Codex/browser tooling.")
    source.add_argument("--structured-json", help="Structured page snapshot JSON captured by Codex/browser tooling.")
    parser.add_argument("--out-dir", default="./promotion-output/intake")
    return parser.parse_args()


def load_profile(args: argparse.Namespace) -> dict[str, Any]:
    if args.structured_json:
        path = Path(args.structured_json)
        return extract_profile_from_structured_json(json.loads(path.read_text(encoding="utf-8-sig")), str(path))
    if args.text_file:
        path = Path(args.text_file)
        return extract_profile_from_text(path.read_text(encoding="utf-8"), str(path))
    html, source = load_html(args)
    return extract_profile_from_html(html, source)


def load_html(args: argparse.Namespace) -> tuple[str, str]:
    if args.html_file:
        path = Path(args.html_file)
        return decode_html_bytes(path.read_bytes(), "utf-8"), str(path)
    request = urllib.request.Request(
        args.url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or ""
        return decode_html_bytes(response.read(), charset), args.url


def decode_html_bytes(raw: bytes, declared_charset: str = "") -> str:
    candidates: list[str] = []

    def add(candidate: str) -> None:
        normalized = normalize_charset(candidate)
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    if raw.startswith(b"\xef\xbb\xbf"):
        add("utf-8-sig")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        add("utf-16")
    add(declared_charset)
    add(meta_declared_charset(raw))
    add("utf-8")
    add("utf-8-sig")
    add("gb18030")
    add("gbk")

    utf8_valid = can_decode(raw, "utf-8")
    best: tuple[int, int, int, str] | None = None
    for index, charset in enumerate(candidates):
        try:
            text = raw.decode(charset, errors="replace")
        except LookupError:
            continue
        priority = 0 if utf8_valid and charset in {"utf-8", "utf-8-sig"} else 1
        score = (decode_penalty(text), priority, index, text)
        if best is None or score[:3] < best[:3]:
            best = score
    return best[3] if best else raw.decode("utf-8", errors="replace")


def normalize_charset(value: str) -> str:
    return value.strip().strip("\"'").lower().replace("_", "-")


def meta_declared_charset(raw: bytes) -> str:
    head = raw[:4096]
    patterns = [
        rb"<meta[^>]+charset\s*=\s*['\"]?\s*([a-zA-Z0-9._-]+)",
        rb"<meta[^>]+content\s*=\s*['\"][^'\"]*charset\s*=\s*([a-zA-Z0-9._-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, head, flags=re.IGNORECASE)
        if match:
            return match.group(1).decode("ascii", errors="ignore")
    return ""


def can_decode(raw: bytes, charset: str) -> bool:
    try:
        raw.decode(charset)
    except UnicodeDecodeError:
        return False
    return True


def decode_penalty(text: str) -> int:
    penalty = text.count("\ufffd") * 20
    penalty += text.count("锟") * 8
    penalty += sum(text.count(item) * 4 for item in ["Ã", "Â", "â€", "å", "ä"])
    penalty += sum(
        text.count(item) * 3
        for item in ["锝", "鎯", "闄", "浼", "璐", "鐨", "鍦", "浣", "涓€", "銆", "绋", "鏃"]
    )
    return penalty


def text_looks_mojibake(text: str) -> bool:
    if not text:
        return False
    return decode_penalty(text) >= max(12, len(text) // 120)


def extract_profile_from_html(html: str, source: str) -> dict[str, Any]:
    parser = MetadataParser()
    parser.feed(html)
    title = first_non_empty(
        parser.meta.get("og:title"),
        parser.meta.get("twitter:title"),
        normalize_space(" ".join(parser.title_parts)),
    )
    description = first_non_empty(
        parser.meta.get("og:description"),
        parser.meta.get("description"),
        parser.meta.get("twitter:description"),
    )
    image = first_non_empty(parser.meta.get("og:image"), parser.meta.get("twitter:image"))
    canonical = canonical_url(parser.links)
    jsonld_objects = parse_json_ld(parser.json_ld)
    inferred_name = first_non_empty(
        value_from_json_ld(jsonld_objects, "name"),
        title,
        "Unknown product",
    )
    inferred_offer = first_non_empty(
        value_from_json_ld(jsonld_objects, "offers.price"),
        value_from_json_ld(jsonld_objects, "price"),
        "unknown",
    )
    keywords = infer_keywords(title, description, parser.meta.get("keywords", ""))
    value_proposition = infer_value_proposition(inferred_name, description)
    profile = {
        "source": source,
        "sourceType": "html",
        "canonicalUrl": canonical or source,
        "productName": inferred_name,
        "title": title,
        "description": description,
        "valueProposition": value_proposition,
        "pricing": inferred_offer,
        "image": image,
        "keywords": keywords,
        "targetAudienceAssumptions": infer_audience(keywords, description),
        "painPointAssumptions": infer_pain_points(keywords, description),
        "jsonLdTypes": sorted({str(item.get("@type")) for item in jsonld_objects if isinstance(item, dict) and item.get("@type")}),
        "confidence": confidence_score(title, description, jsonld_objects),
        "notes": [
            "Derived from public page metadata. Verify product claims, pricing, audience, and legal terms before publishing.",
            "Dynamic pages may expose less metadata than the rendered browser page.",
        ],
    }
    return profile


def extract_profile_from_structured_json(data: dict[str, Any], source: str) -> dict[str, Any]:
    flattened = flatten_snapshot(data)
    source_type = "browser_rendered_snapshot" if data.get("snapshotType") == "browser_rendered" else "structured_json"
    title = first_non_empty(
        flattened.get("productName"),
        flattened.get("name"),
        flattened.get("title"),
        flattened.get("og:title"),
        flattened.get("twitter:title"),
    )
    description = first_non_empty(
        flattened.get("valueProposition"),
        flattened.get("description"),
        flattened.get("metaDescription"),
        flattened.get("og:description"),
        flattened.get("twitter:description"),
        flattened.get("summary"),
        flattened.get("text"),
    )
    url = first_non_empty(flattened.get("canonicalUrl"), flattened.get("url"), flattened.get("href"), source)
    image = first_non_empty(flattened.get("image"), flattened.get("og:image"), flattened.get("twitter:image"), first_list_value(data, "images"))
    pricing = first_non_empty(
        flattened.get("pricing"),
        flattened.get("price"),
        flattened.get("offers.price"),
        extract_price(" ".join([title, description, flattened.get("text", "")])),
        "unknown",
    )
    keywords = infer_keywords(title, description, flattened.get("keywords", ""), flattened.get("text", ""))
    text = " ".join([title, description, flattened.get("text", "")])
    return {
        "source": source,
        "sourceType": source_type,
        "canonicalUrl": url,
        "productName": first_non_empty(flattened.get("productName"), flattened.get("name"), title, "Unknown product"),
        "title": title,
        "description": description,
        "valueProposition": infer_value_proposition(title or "Product", description),
        "pricing": pricing,
        "image": image,
        "keywords": keywords,
        "targetAudienceAssumptions": explicit_or_infer_list(data, ["targetAudience", "audience", "audiences"], infer_audience(keywords, text)),
        "painPointAssumptions": explicit_or_infer_list(data, ["painPoints", "painPointAssumptions", "problems"], infer_pain_points(keywords, text)),
        "jsonLdTypes": list_from_any(data.get("jsonLdTypes") or data.get("jsonLdType")),
        "confidence": confidence_score(title, description, [{"source": "structured_json"}]),
        "notes": [
            "Derived from a structured page snapshot supplied by Codex/browser tooling.",
            "Verify product claims, pricing, audience, and legal terms before publishing.",
        ],
    }


def extract_profile_from_text(text: str, source: str) -> dict[str, Any]:
    fields = parse_labeled_lines(text)
    title = first_non_empty(fields.get("product"), fields.get("product name"), fields.get("title"), first_content_line(text))
    description = first_non_empty(fields.get("description"), fields.get("summary"), fields.get("value proposition"), first_paragraph(text, title))
    url = first_non_empty(fields.get("url"), fields.get("canonical url"), first_url(text), source)
    pricing = first_non_empty(fields.get("pricing"), fields.get("price"), extract_price(text), "unknown")
    keywords = infer_keywords(title, description, text)
    return {
        "source": source,
        "sourceType": "text",
        "canonicalUrl": url,
        "productName": title or "Unknown product",
        "title": title,
        "description": description,
        "valueProposition": infer_value_proposition(title or "Product", description),
        "pricing": pricing,
        "image": first_non_empty(fields.get("image"), first_image_url(text)),
        "keywords": keywords,
        "targetAudienceAssumptions": explicit_text_list(fields, ["audience", "target audience"]) or infer_audience(keywords, text),
        "painPointAssumptions": explicit_text_list(fields, ["pain points", "painpoints", "problems"]) or infer_pain_points(keywords, text),
        "jsonLdTypes": [],
        "confidence": confidence_score(title, description, []),
        "notes": [
            "Derived from rendered page text supplied by Codex/browser tooling.",
            "Verify product claims, pricing, audience, and legal terms before publishing.",
        ],
    }


def parse_json_ld(blocks: list[str]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                parsed.extend([item for item in graph if isinstance(item, dict)])
            parsed.append(data)
        elif isinstance(data, list):
            parsed.extend([item for item in data if isinstance(item, dict)])
    return parsed


def value_from_json_ld(items: list[dict[str, Any]], dotted_key: str) -> str:
    parts = dotted_key.split(".")
    for item in items:
        value: Any = item
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if value not in (None, ""):
            return str(value)
    return ""


def canonical_url(links: list[dict[str, str]]) -> str:
    for link in links:
        rel = link.get("rel", "").lower()
        if "canonical" in rel and link.get("href"):
            return link["href"]
    return ""


def flatten_snapshot(data: Any, prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (dict, list)):
                flattened.update(flatten_snapshot(value, dotted))
            elif value not in (None, ""):
                flattened[dotted] = normalize_space(str(value))
                flattened.setdefault(str(key), normalize_space(str(value)))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            flattened.update(flatten_snapshot(value, f"{prefix}.{index}" if prefix else str(index)))
    return flattened


def first_list_value(data: Any, key: str) -> str:
    if not isinstance(data, dict):
        return ""
    value = data.get(key)
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                candidate = first_non_empty(str(item.get("url") or ""), str(item.get("src") or ""), str(item.get("href") or ""))
                if candidate:
                    return candidate
    if isinstance(value, str):
        return value
    return ""


def explicit_or_infer_list(data: dict[str, Any], keys: list[str], fallback: list[str]) -> list[str]:
    for key in keys:
        if key in data:
            values = list_from_any(data[key])
            if values:
                return values
    return fallback


def list_from_any(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_space(str(item)) for item in value if normalize_space(str(item))]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()]
    return []


def parse_labeled_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = normalize_space(key).lower()
        value = normalize_space(value)
        if key and value:
            fields[key] = value
    return fields


def first_content_line(text: str) -> str:
    for line in text.splitlines():
        line = normalize_space(line)
        if line and ":" not in line:
            return line
    return ""


def first_paragraph(text: str, skip: str = "") -> str:
    for block in re.split(r"\n\s*\n", text):
        block = normalize_space(block)
        if block and block != skip and ":" not in block[:40]:
            return block
    return ""


def first_url(text: str) -> str:
    match = re.search(r"https?://[^\s)>\]\"']+", text)
    return match.group(0) if match else ""


def first_image_url(text: str) -> str:
    for url in re.findall(r"https?://[^\s)>\]\"']+", text):
        if re.search(r"\.(png|jpe?g|webp|gif)(\?|$)", url, re.IGNORECASE):
            return url
    return ""


def explicit_text_list(fields: dict[str, str], keys: list[str]) -> list[str]:
    for key in keys:
        if fields.get(key):
            return list_from_any(fields[key])
    return []


def extract_price(text: str) -> str:
    match = re.search(r"([$€£¥￥]\s?\d+(?:[.,]\d+)?)", text)
    if match:
        return normalize_space(match.group(1))
    match = re.search(r"(?i)(?:price|pricing|价格|售价)[:：]?\s*([\w$€£¥￥.,/\-\s\u4e00-\u9fff]+)", text)
    if match:
        return normalize_space(match.group(1))[:80]
    return ""


def infer_keywords(*values: str) -> list[str]:
    text = " ".join(values).lower()
    raw = re.split(r"[,，、;；:：|/\s]+", text)
    keywords = []
    for item in raw:
        cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff-]", "", item).strip("-")
        if len(cleaned) >= 2 and cleaned not in keywords:
            keywords.append(cleaned)
    return keywords[:20]


def infer_value_proposition(name: str, description: str) -> str:
    if description:
        return description
    return f"{name} product page. Value proposition needs manual verification."


def infer_audience(keywords: list[str], description: str) -> list[str]:
    text = " ".join(keywords) + " " + description.lower()
    audiences = []
    if any(term in text for term in ["ai", "prompt", "automation", "workflow"]):
        audiences.append("AI tool users and operators")
    if any(term in text for term in ["seo", "content", "blog", "marketing"]):
        audiences.append("content and growth operators")
    if any(term in text for term in ["developer", "github", "api", "open source"]):
        audiences.append("developers and technical founders")
    if any(term in text for term in ["shop", "ecommerce", "seller", "store"]):
        audiences.append("ecommerce sellers")
    return audiences or ["target audience needs manual verification"]


def infer_pain_points(keywords: list[str], description: str) -> list[str]:
    text = " ".join(keywords) + " " + description.lower()
    points = []
    if any(term in text for term in ["copy", "content", "prompt", "template"]):
        points.append("hard to turn product value into reusable content")
    if any(term in text for term in ["seo", "traffic", "growth"]):
        points.append("needs more qualified traffic")
    if any(term in text for term in ["automation", "workflow", "tool"]):
        points.append("manual workflows are slow")
    return points or ["pain points need manual verification"]


def confidence_score(title: str, description: str, jsonld: list[dict[str, Any]]) -> str:
    score = 0
    if title:
        score += 1
    if description:
        score += 1
    if jsonld:
        score += 1
    return {0: "low", 1: "low", 2: "medium", 3: "high"}[score]


def first_non_empty(*values: str | None) -> str:
    for value in values:
        normalized = normalize_space(value or "")
        if normalized:
            return normalized
    return ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def render_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# Product Profile",
        "",
        f"- Source: {profile['source']}",
        f"- Canonical URL: {profile['canonicalUrl']}",
        f"- Product name: {profile['productName']}",
        f"- Value proposition: {profile['valueProposition']}",
        f"- Pricing: {profile['pricing']}",
        f"- Confidence: {profile['confidence']}",
        "",
        "## Audience Assumptions",
    ]
    lines.extend([f"- {item}" for item in profile["targetAudienceAssumptions"]])
    lines.extend(["", "## Pain Point Assumptions"])
    lines.extend([f"- {item}" for item in profile["painPointAssumptions"]])
    lines.extend(["", "## Keywords"])
    lines.extend([f"- {item}" for item in profile["keywords"]])
    lines.extend(["", "## Notes"])
    lines.extend([f"- {item}" for item in profile["notes"]])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
