#!/usr/bin/env python3
"""Generate publish-ready media assets and attach them to publish packs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - exercised by users without Pillow
    Image = None
    ImageDraw = None
    ImageFont = None


TODAY = date.today().isoformat()
VIDEO_REQUIRED_PLATFORMS = {"youtube", "douyin", "tiktok", "xiaohongshu"}
PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "youtube": {"size": (1280, 720), "cover": "youtube-thumbnail.png", "detail_count": 2, "accent": "#ef4444"},
    "zhihu": {"size": (1200, 628), "cover": "zhihu-header.png", "detail_count": 2, "accent": "#2563eb"},
    "xiaohongshu": {"size": (1080, 1440), "cover": "xiaohongshu-cover.png", "detail_count": 4, "accent": "#e11d48"},
    "douyin": {"size": (1080, 1920), "cover": "douyin-cover.png", "detail_count": 3, "accent": "#06b6d4"},
    "github": {"size": (1280, 640), "cover": "github-social-preview.png", "detail_count": 2, "accent": "#16a34a"},
    "tiktok": {"size": (1080, 1920), "cover": "tiktok-cover.png", "detail_count": 3, "accent": "#14b8a6"},
}


def main() -> None:
    args = parse_args()
    if Image is None or ImageDraw is None or ImageFont is None:
        raise SystemExit("Pillow is required for PNG media asset generation. Install it with: python -m pip install pillow")

    out_dir = Path(args.out_dir)
    content_path = Path(args.content_json)
    publish_pack_path = Path(args.publish_pack)
    if not content_path.exists():
        raise SystemExit(f"Generated content JSON not found: {content_path}")
    if not publish_pack_path.exists():
        raise SystemExit(f"Publish pack JSON not found: {publish_pack_path}")

    content = read_json(content_path)
    publish_pack = read_json(publish_pack_path)
    if not isinstance(content, dict):
        raise SystemExit("Generated content JSON must be an object keyed by platform.")
    if not isinstance(publish_pack, list):
        raise SystemExit("Publish pack JSON must be a list.")

    video_files = parse_video_files(args.video_file)
    platforms = split_csv(args.platforms) or list(content.keys())
    report = build_media_asset_pack(
        out_dir=out_dir,
        content=content,
        publish_pack=publish_pack,
        publish_pack_path=publish_pack_path,
        platforms=platforms,
        video_root=Path(args.video_root) if args.video_root else out_dir / "videos",
        video_files=video_files,
        update_publish_pack=args.update_publish_pack,
    )
    write_report(out_dir, report)
    print(f"Media asset pack written to: {(report_dir(out_dir) / 'media-asset-pack.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PNG covers/detail images and attach media paths to publish packs.")
    parser.add_argument("--content-json", required=True, help="Path to <product>-platform-content.json.")
    parser.add_argument("--publish-pack", required=True, help="Path to <product>-publish-pack.json.")
    parser.add_argument("--platforms", default="", help="Comma-separated platform filter. Defaults to platforms in content JSON.")
    parser.add_argument("--video-root", default="", help="Directory containing rendered MP4 files. Defaults to <out-dir>/videos.")
    parser.add_argument("--video-file", action="append", default=[], help="Explicit video as platform=path. Can repeat.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--no-update-publish-pack", dest="update_publish_pack", action="store_false")
    parser.set_defaults(update_publish_pack=True)
    return parser.parse_args()


def build_media_asset_pack(
    out_dir: Path,
    content: dict[str, Any],
    publish_pack: list[dict[str, Any]],
    publish_pack_path: Path,
    platforms: list[str],
    video_root: Path,
    video_files: dict[str, Path],
    update_publish_pack: bool,
) -> dict[str, Any]:
    by_platform = {str(item.get("platform") or ""): item for item in publish_pack if isinstance(item, dict)}
    product = product_from_content(content)
    product_slug = slugify(product.get("name") or publish_pack_path.stem.replace("-publish-pack", "") or "product")
    platform_reports = []
    for platform in platforms:
        item = content.get(platform)
        if not isinstance(item, dict):
            continue
        platform_report = generate_platform_assets(out_dir, product_slug, platform, item, video_root, video_files)
        platform_reports.append(platform_report)
        pack_item = by_platform.get(platform)
        if pack_item is not None:
            attach_to_publish_pack(pack_item, item, platform_report)

    if update_publish_pack:
        publish_pack_path.write_text(json.dumps(publish_pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "generatedAt": TODAY,
        "status": "ready" if platform_reports else "no_platform_assets",
        "publishPack": str(publish_pack_path),
        "publishPackUpdated": bool(update_publish_pack),
        "platforms": platform_reports,
        "summary": summarize(platform_reports),
        "guardrails": [
            "Generated images are deterministic local PNG drafts; review visual quality before live publishing.",
            "Video paths point only to locally rendered or explicitly supplied MP4 files.",
            "Missing video files are reported as missing; the script does not fabricate video completion.",
        ],
    }


def generate_platform_assets(
    out_dir: Path,
    product_slug: str,
    platform: str,
    item: dict[str, Any],
    video_root: Path,
    video_files: dict[str, Path],
) -> dict[str, Any]:
    spec = PLATFORM_SPECS.get(platform, {"size": (1200, 900), "cover": f"{platform}-cover.png", "detail_count": 2, "accent": "#4f46e5"})
    width, height = spec["size"]
    platform_dir = out_dir / "media-assets" / platform
    platform_dir.mkdir(parents=True, exist_ok=True)

    title = viral_title(item)
    copy = publication_copy(item)
    first_batch_payload = first_batch(item)
    tags = clean_list(item.get("tags"))
    cover_text = str(item.get("coverText") or title).strip()
    accent = str(spec["accent"])

    cover_path = platform_dir / str(spec["cover"])
    render_png(
        cover_path,
        width,
        height,
        title=cover_text or title,
        subtitle=title,
        body=summary_text(copy, 180),
        footer=f"{platform} | {TODAY}",
        accent=accent,
    )

    detail_images = []
    for index, detail in enumerate(detail_pages(item, copy, first_batch_payload, tags)[: int(spec["detail_count"])], start=1):
        detail_path = platform_dir / f"detail-{index:02d}.png"
        render_png(
            detail_path,
            width,
            height,
            title=detail["title"],
            subtitle=title,
            body=detail["body"],
            footer=f"{platform} detail {index}",
            accent=accent,
        )
        detail_images.append({"type": "detail_image", "index": index, "path": str(detail_path), "status": "ready"})

    video_path = resolve_video(platform, product_slug, video_root, video_files)
    video_required = platform in VIDEO_REQUIRED_PLATFORMS
    video = {
        "type": "video",
        "required": video_required,
        "status": "ready" if video_path and video_path.exists() else "missing" if video_required else "not_required",
        "path": str(video_path) if video_path and video_path.exists() else "",
    }
    cover = {"type": "cover_image", "required": True, "status": "ready", "path": str(cover_path), "coverText": cover_text}
    assets = [cover, *detail_images]
    if video["path"]:
        assets.insert(0, video)

    return {
        "platform": platform,
        "viralTitle": title,
        "copy": copy,
        "tags": tags,
        "firstBatch": first_batch_payload,
        "video": video,
        "cover": cover,
        "detailImages": detail_images,
        "assets": assets,
        "assetDirectory": str(platform_dir),
    }


def attach_to_publish_pack(pack_item: dict[str, Any], content_item: dict[str, Any], platform_report: dict[str, Any]) -> None:
    pack_item["viralTitle"] = platform_report["viralTitle"]
    pack_item["copy"] = platform_report["copy"]
    pack_item["tags"] = platform_report["tags"]
    pack_item["firstBatch"] = platform_report["firstBatch"]
    pack_item["video"] = platform_report["video"]
    pack_item["cover"] = platform_report["cover"]
    pack_item["detailImages"] = platform_report["detailImages"]
    pack_item["assets"] = platform_report["assets"]
    content_item["firstBatch"] = platform_report["firstBatch"]
    content_item["viralTitle"] = platform_report["viralTitle"]
    content_item["copy"] = platform_report["copy"]
    pack_item["content"] = content_item


def render_png(path: Path, width: int, height: int, title: str, subtitle: str, body: str, footer: str, accent: str) -> None:
    image = Image.new("RGB", (width, height), "#f8fafc")
    draw = ImageDraw.Draw(image)
    accent_rgb = hex_to_rgb(accent)
    draw.rectangle((0, 0, width, int(height * 0.18)), fill=accent_rgb)
    draw.rectangle((0, int(height * 0.18), width, height), fill="#f8fafc")
    draw.rectangle((0, height - max(56, height // 16), width, height), fill="#111827")

    margin = max(48, width // 18)
    title_font = load_font(max(34, width // 19), bold=True)
    subtitle_font = load_font(max(22, width // 38), bold=True)
    body_font = load_font(max(22, width // 42))
    footer_font = load_font(max(16, width // 58))

    draw.text((margin, max(28, height // 28)), platform_label(title), fill="#ffffff", font=subtitle_font)
    y = int(height * 0.23)
    y = draw_wrapped(draw, title, title_font, margin, y, width - margin * 2, "#0f172a", max(8, height // 90))
    y += max(16, height // 45)
    if subtitle and subtitle != title:
        y = draw_wrapped(draw, subtitle, subtitle_font, margin, y, width - margin * 2, "#334155", max(6, height // 120))
        y += max(18, height // 45)
    draw_wrapped(draw, body, body_font, margin, y, width - margin * 2, "#111827", max(8, height // 100))
    draw.text((margin, height - max(42, height // 22)), footer[:120], fill="#f8fafc", font=footer_font)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def draw_wrapped(draw: Any, text: str, font: Any, x: int, y: int, max_width: int, fill: str, spacing: int) -> int:
    for line in wrap_pixels(draw, clean_space(text), font, max_width):
        draw.text((x, y), line, fill=fill, font=font)
        y += text_height(draw, line, font) + spacing
    return y


def wrap_pixels(draw: Any, text: str, font: Any, max_width: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        if len(words) <= 1:
            lines.extend(wrap_long_token(draw, paragraph, font, max_width))
            continue
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if text_width(draw, candidate, font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                if text_width(draw, word, font) > max_width:
                    lines.extend(wrap_long_token(draw, word, font, max_width))
                    current = ""
                else:
                    current = word
        if current:
            lines.append(current)
    return lines[:12]


def wrap_long_token(draw: Any, token: str, font: Any, max_width: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for char in token:
        candidate = current + char
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = char
    if current:
        chunks.append(current)
    return chunks


def load_font(size: int, bold: bool = False) -> Any:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def detail_pages(item: dict[str, Any], copy: str, first_batch: dict[str, Any], tags: list[str]) -> list[dict[str, str]]:
    product = item.get("sourceProduct") if isinstance(item.get("sourceProduct"), dict) else {}
    pain_points = clean_list(product.get("pain_points") or product.get("painPoints"))
    storyboard = item.get("storyboard") if isinstance(item.get("storyboard"), list) else []
    first_comments = clean_list(first_batch.get("firstComments")) or clean_list(first_batch.get("replyPrompts"))
    return [
        {
            "title": "Pain point",
            "body": "\n".join(pain_points[:4]) or summary_text(str(item.get("description") or copy), 220),
        },
        {
            "title": "How it works",
            "body": storyboard_text(storyboard) or summary_text(copy, 260),
        },
        {
            "title": "First batch engagement",
            "body": "\n".join(first_comments[:4]) or str(first_batch.get("pinnedComment") or "Prepare the first comment and reply prompts before publishing."),
        },
        {
            "title": "Tags and CTA",
            "body": " ".join(f"#{tag}" for tag in tags[:12]) + "\n" + str(item.get("cta") or ""),
        },
    ]


def storyboard_text(storyboard: list[Any]) -> str:
    lines = []
    for item in storyboard[:4]:
        if isinstance(item, dict):
            lines.append(f"{item.get('time', '')}: {item.get('visual', '')} / {item.get('voiceover', '')}")
    return "\n".join(line.strip() for line in lines if line.strip())


def viral_title(item: dict[str, Any]) -> str:
    return str(item.get("viralTitle") or item.get("title") or item.get("description") or "Promotion title").strip()


def publication_copy(item: dict[str, Any]) -> str:
    formats = item.get("formats") if isinstance(item.get("formats"), dict) else {}
    candidates: list[Any] = [
        item.get("copy"),
        item.get("article"),
        item.get("shortVideoScript"),
        item.get("voiceover"),
        formats.get("readmePromotion"),
        first_list_item(formats.get("notes")),
        first_list_item(formats.get("thirtySecondScripts")),
        first_list_item(formats.get("videoScripts")),
        item.get("description"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return viral_title(item)


def first_batch(item: dict[str, Any]) -> dict[str, Any]:
    existing = item.get("firstBatch")
    if isinstance(existing, dict) and existing:
        return existing
    formats = item.get("formats") if isinstance(item.get("formats"), dict) else {}
    prompts = clean_list(formats.get("commentPrompts"))
    title = viral_title(item)
    cta = str(item.get("cta") or "").strip()
    return {
        "pinnedComment": cta or f"Try this workflow and tell us which platform should be optimized first: {title}",
        "firstComments": prompts
        or [
            "Which part of this workflow is hardest for you right now?",
            "Comment with your product URL or platform, and use the same structure to rewrite the angle.",
        ],
        "replyPrompts": [
            "Ask what product category the user is promoting.",
            "Ask which platform they want to publish on first.",
            "Offer one concrete title or hook rewrite.",
        ],
        "launchActions": [
            "Publish the prepared package only after manual review.",
            "Pin the strongest CTA comment.",
            "Record the real published URL for metrics recovery.",
        ],
    }


def resolve_video(platform: str, product_slug: str, video_root: Path, video_files: dict[str, Path]) -> Path | None:
    explicit = video_files.get(platform)
    if explicit:
        return explicit
    candidates = [
        video_root / f"{product_slug}-{platform}.mp4",
        video_root / f"product-{platform}.mp4",
    ]
    candidates.extend(sorted(video_root.glob(f"*{platform}*.mp4")) if video_root.exists() else [])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def summarize(platform_reports: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "platforms": len(platform_reports),
        "videosReady": sum(1 for item in platform_reports if item.get("video", {}).get("status") == "ready"),
        "videosMissing": sum(1 for item in platform_reports if item.get("video", {}).get("status") == "missing"),
        "coversReady": sum(1 for item in platform_reports if item.get("cover", {}).get("status") == "ready"),
        "detailImagesReady": sum(len(item.get("detailImages", [])) for item in platform_reports),
        "assetsReady": sum(len(item.get("assets", [])) for item in platform_reports),
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "media-asset-pack.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "media-asset-pack.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Media Asset Pack",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Publish pack updated: {report['publishPackUpdated']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Platforms"])
    for item in report["platforms"]:
        lines.extend(
            [
                "",
                f"### {item['platform']}",
                f"- Viral title: {item['viralTitle']}",
                f"- Video: `{item['video']['status']}` {item['video'].get('path', '')}",
                f"- Cover: {item['cover']['path']}",
                f"- Detail images: {len(item['detailImages'])}",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def product_from_content(content: dict[str, Any]) -> dict[str, Any]:
    for item in content.values():
        if isinstance(item, dict) and isinstance(item.get("sourceProduct"), dict):
            return item["sourceProduct"]
    return {}


def parse_video_files(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Expected platform=path for --video-file, got: {value}")
        platform, path = value.split("=", 1)
        platform = platform.strip().lower()
        if platform and path.strip():
            result[platform] = Path(path.strip())
    return result


def first_list_item(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return ""


def clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def summary_text(value: str, limit: int) -> str:
    value = clean_space(value)
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def platform_label(title: str) -> str:
    return title[:64]


def text_width(draw: Any, text: str, font: Any) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return int(box[2] - box[0])


def text_height(draw: Any, text: str, font: Any) -> int:
    box = draw.textbbox((0, 0), text or "Ag", font=font)
    return int(box[3] - box[1])


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return (79, 70, 229)
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/media-assets"


if __name__ == "__main__":
    main()
