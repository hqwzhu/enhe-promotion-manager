#!/usr/bin/env python3
"""Capture browser-visible video evidence without downloading private media streams."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"
ACCESS_GATE_RE = re.compile(
    r"(?i)(login|sign in|captcha|verify|verification|access denied|forbidden|risk control|unusual traffic|"
    r"登录|验证码|验证|访问受限|权限|风控|请先登录)"
)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    report = capture_video_evidence(args, out_dir)
    write_outputs(out_dir, report)
    print(f"Browser video sampler written to: {(report_dir(out_dir) / 'browser-video-sampler.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture visible video metadata and frame screenshots from a public/browser-visible page.")
    parser.add_argument("--url", required=True, help="Public or browser-visible page URL containing a video element.")
    parser.add_argument("--platform", default="auto", help="youtube, zhihu, xiaohongshu, douyin, tiktok, github, or auto.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--sample-count", type=int, default=5)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-until", default="domcontentloaded", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost URLs for fixtures/tests only.")
    parser.add_argument("--install-browser-if-missing", action="store_true", help="Run the official Playwright Chromium install if missing.")
    return parser.parse_args()


def capture_video_evidence(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    validation_issue = validate_url(args.url, args.allow_localhost)
    if validation_issue:
        return base_report(args, "blocked", validation_issue)
    try:
        return capture_with_playwright(args, out_dir)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - CLI turns browser failures into an evidence report.
        report = base_report(args, "error", f"Browser video sampling failed: {exc}")
        report["errorType"] = exc.__class__.__name__
        return report


def capture_with_playwright(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 - optional dependency.
        raise SystemExit(f"Playwright is not installed for this Python environment: {exc}") from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1200})
            response = page.goto(args.url, wait_until=args.wait_until, timeout=args.timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(args.timeout_ms, 10000))
            except PlaywrightTimeoutError:
                pass
            wait_for_video_metadata(page, min(args.timeout_ms, 10000))
            page_state = page.evaluate(PAGE_STATE_SCRIPT)
            videos = page_state.get("videos", []) if isinstance(page_state.get("videos"), list) else []
            warnings = access_warnings(page_state)
            frames = []
            if videos:
                frames = sample_frames(page, out_dir, max(args.sample_count, 0), videos[0])
            browser.close()
            status = "ready" if videos else "no_video"
            if warnings and not videos:
                status = "blocked"
            report = base_report(args, status, warnings[0] if status == "blocked" and warnings else "")
            report.update(
                {
                    "httpStatus": response.status if response else None,
                    "platform": choose_platform(args.platform, args.url),
                    "title": page_state.get("title", ""),
                    "canonicalUrl": sanitize_url(page_state.get("canonicalUrl") or args.url),
                    "videoCount": len(videos),
                    "videos": [sanitize_video(item) for item in videos],
                    "primaryVideo": sanitize_video(videos[0]) if videos else {},
                    "frames": frames,
                    "pageTextExcerpt": trim(page_state.get("text", ""), 1200),
                    "visibleTranscriptHints": transcript_hints(page_state.get("text", "")),
                    "accessWarnings": warnings,
                    "contentEvidence": build_content_evidence(args, page_state, videos, frames),
                }
            )
            return report
    except PlaywrightError as exc:
        message = str(exc)
        if "Executable doesn't exist" in message and args.install_browser_if_missing:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], cwd=ROOT, check=True)
            args.install_browser_if_missing = False
            return capture_with_playwright(args, out_dir)
        if "Executable doesn't exist" in message:
            raise SystemExit("Playwright Chromium is missing. Run: python -m playwright install chromium") from exc
        report = base_report(args, "error", f"Browser video sampling failed: {message}")
        return report


def sample_frames(page: Any, out_dir: Path, sample_count: int, primary_video: dict[str, Any]) -> list[dict[str, Any]]:
    if sample_count <= 0:
        return []
    frame_dir = report_dir(out_dir) / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    duration = numeric(primary_video.get("duration"), 0.0)
    times = sample_times(duration, sample_count)
    frames = []
    locator = page.locator("video").first
    for index, timestamp in enumerate(times, start=1):
        try:
            page.evaluate(
                """
                async ({time}) => {
                  const video = document.querySelector('video');
                  if (!video) return false;
                  video.pause();
                  const duration = Number.isFinite(video.duration) ? video.duration : 0;
                  video.currentTime = duration ? Math.min(time, Math.max(duration - 0.05, 0)) : 0;
                  await new Promise((resolve) => {
                    const done = () => resolve(true);
                    video.addEventListener('seeked', done, {once: true});
                    setTimeout(done, 1000);
                  });
                  return true;
                }
                """,
                {"time": timestamp},
            )
            path = frame_dir / f"frame-{index:02d}.png"
            locator.screenshot(path=str(path), timeout=5000)
            frames.append({"index": index, "time": timestamp, "screenshot": str(path), "status": "ready"})
        except Exception as exc:  # noqa: BLE001 - record partial evidence.
            frames.append({"index": index, "time": timestamp, "screenshot": "", "status": "error", "reason": str(exc)})
    return frames


def wait_for_video_metadata(page: Any, timeout_ms: int) -> None:
    try:
        page.evaluate(
            """
            async ({timeoutMs}) => {
              const video = document.querySelector('video');
              if (!video) return false;
              if (video.readyState >= 1) return true;
              await new Promise((resolve) => {
                const done = () => resolve(true);
                video.addEventListener('loadedmetadata', done, {once: true});
                setTimeout(done, timeoutMs);
              });
              return video.readyState >= 1;
            }
            """,
            {"timeoutMs": timeout_ms},
        )
    except Exception:
        return


def sample_times(duration: float, sample_count: int) -> list[float]:
    if sample_count <= 0:
        return []
    if duration and duration > 0:
        if sample_count == 1:
            return [round(min(duration / 2, max(duration - 0.05, 0)), 2)]
        return [round(min((duration * index) / (sample_count + 1), max(duration - 0.05, 0)), 2) for index in range(1, sample_count + 1)]
    return [0.0]


PAGE_STATE_SCRIPT = r"""
() => {
  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const canonical = document.querySelector('link[rel~="canonical"]')?.href || location.href;
  const videos = Array.from(document.querySelectorAll('video')).map((video, index) => {
    const rect = video.getBoundingClientRect();
    const sources = Array.from(video.querySelectorAll('source')).map((source) => source.src || source.getAttribute('src') || '').filter(Boolean);
    return {
      index,
      currentSrc: video.currentSrc || video.src || '',
      sources,
      duration: Number.isFinite(video.duration) ? video.duration : null,
      currentTime: video.currentTime || 0,
      paused: video.paused,
      muted: video.muted,
      controls: video.controls,
      readyState: video.readyState,
      videoWidth: video.videoWidth || 0,
      videoHeight: video.videoHeight || 0,
      visible: rect.width > 0 && rect.height > 0,
      rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
      poster: video.poster || ''
    };
  });
  return {
    url: location.href,
    canonicalUrl: canonical,
    title: clean(document.title),
    text: clean(document.body ? document.body.innerText : ''),
    videos
  };
}
"""


def build_content_evidence(args: argparse.Namespace, page_state: dict[str, Any], videos: list[dict[str, Any]], frames: list[dict[str, Any]]) -> dict[str, Any]:
    title = normalize_space(page_state.get("title", ""))
    text = normalize_space(page_state.get("text", ""))
    return {
        "platform": choose_platform(args.platform, args.url),
        "url": sanitize_url(args.url),
        "title": title,
        "contentFormat": "video" if videos else "page_without_detected_video",
        "contentExcerpt": trim(" ".join([title, text]), 1200),
        "videoEvidence": {
            "videoCount": len(videos),
            "frameCount": sum(1 for frame in frames if frame.get("status") == "ready"),
            "frames": frames,
        },
        "suggestedNextStep": "Use visibleTranscriptHints plus frame screenshots for competitor deconstruction; add user-provided transcript/audio notes when available.",
    }


def sanitize_video(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": item.get("index"),
        "duration": item.get("duration"),
        "currentTime": item.get("currentTime"),
        "paused": item.get("paused"),
        "muted": item.get("muted"),
        "controls": item.get("controls"),
        "readyState": item.get("readyState"),
        "videoWidth": item.get("videoWidth"),
        "videoHeight": item.get("videoHeight"),
        "visible": item.get("visible"),
        "rect": item.get("rect") if isinstance(item.get("rect"), dict) else {},
        "currentSrc": sanitize_media_url(item.get("currentSrc", "")),
        "sources": [sanitize_media_url(value) for value in item.get("sources", []) if value],
        "poster": sanitize_media_url(item.get("poster", "")),
    }


def sanitize_media_url(value: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(str(value or ""))
    if not parsed.scheme:
        return {"url": "", "queryRedacted": False}
    return {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path,
        "url": urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", "")),
        "queryRedacted": bool(parsed.query),
    }


def sanitize_url(value: str) -> str:
    parsed = urllib.parse.urlparse(str(value or ""))
    if not parsed.scheme:
        return str(value or "")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def access_warnings(page_state: dict[str, Any]) -> list[str]:
    text = " ".join([str(page_state.get("title") or ""), str(page_state.get("text") or "")])
    return ["Page appears to contain login, captcha, verification, or access-denied language."] if ACCESS_GATE_RE.search(text) else []


def transcript_hints(text: str) -> list[str]:
    lines = [normalize_space(line) for line in str(text or "").splitlines()]
    candidates = []
    for line in lines:
        lower = line.lower()
        if any(term in lower for term in ["transcript", "caption", "subtitle", "voiceover", "hook:", "cta:", "字幕", "文案", "口播"]):
            candidates.append(trim(line, 240))
    return dedupe(candidates)[:20]


def validate_url(url: str, allow_localhost: bool) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https", "file"}:
        return "Only http, https, and local file URLs are supported."
    host = parsed.hostname or ""
    if parsed.scheme == "file":
        return "" if allow_localhost else "Local file URLs require --allow-localhost."
    if host in {"localhost", "127.0.0.1", "::1"} and not allow_localhost:
        return "Localhost URLs require --allow-localhost."
    return ""


def base_report(args: argparse.Namespace, status: str, reason: str = "") -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "status": status,
        "reason": reason,
        "input": {
            "url": sanitize_url(args.url),
            "platform": args.platform,
            "sampleCount": args.sample_count,
        },
        "guardrails": guardrails(),
    }


def write_outputs(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "browser-video-sampler.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "browser-video-sampler.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Browser Video Sampler",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- URL: {report.get('input', {}).get('url', '')}",
        f"- Videos: {report.get('videoCount', 0)}",
        f"- Frames: {len(report.get('frames', []))}",
    ]
    if report.get("reason"):
        lines.append(f"- Reason: {report['reason']}")
    if report.get("title"):
        lines.append(f"- Title: {report['title']}")
    if report.get("frames"):
        lines.extend(["", "## Frames"])
        for frame in report["frames"]:
            lines.append(f"- {frame.get('index')}: `{frame.get('status')}` t={frame.get('time')} {frame.get('screenshot', '')}")
    if report.get("visibleTranscriptHints"):
        lines.extend(["", "## Transcript Hints"])
        lines.extend(f"- {item}" for item in report["visibleTranscriptHints"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def choose_platform(value: str, url: str) -> str:
    if value and value != "auto":
        return value.lower()
    host = urllib.parse.urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "zhihu.com" in host:
        return "zhihu"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "xiaohongshu"
    if "douyin.com" in host:
        return "douyin"
    if "tiktok.com" in host:
        return "tiktok"
    if "github.com" in host:
        return "github"
    return "unknown"


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/competitors/video-sampling"


def numeric(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def trim(value: Any, limit: int) -> str:
    text = normalize_space(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def dedupe(values: list[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = normalize_space(value)
        key = text.lower()
        if text and key not in seen:
            output.append(text)
            seen.add(key)
    return output


def guardrails() -> list[str]:
    return [
        "Capture browser-visible video metadata and screenshots only.",
        "Do not download private media streams or store signed media query tokens.",
        "Do not auto-login, solve captcha, bypass platform risk controls, or extract cookies.",
        "Use frame evidence and visible transcript hints for deconstruction; do not fabricate unseen audio, comments, or metrics.",
    ]


if __name__ == "__main__":
    main()
