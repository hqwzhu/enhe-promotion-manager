#!/usr/bin/env python3
"""Read product URLs into structured browser snapshots and product profiles."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from product_intake import decode_html_bytes, text_looks_mojibake
from env_loader import load_project_env, preparse_env_file
from web_data_provider import DEFAULT_FIRECRAWL_BASE_URL, WebDataProviderError, scrape_url

BROWSER_SNAPSHOT = SCRIPTS / "browser_snapshot.py"
PRODUCT_INTAKE = SCRIPTS / "product_intake.py"
TODAY = date.today().isoformat()
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"
DEFAULT_WEB_TEXT_FALLBACK_TEMPLATE = "https://r.jina.ai/{url}"


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = collect_urls(args)
    if not urls:
        raise SystemExit("No URLs were supplied.")
    records = [read_product_url(args, out_dir, url, index) for index, url in enumerate(urls, start=1)]
    report = build_report(args, out_dir, records)
    report["envLoad"] = env_load
    write_report(out_dir, report)
    print(f"Product URL reader report written to: {(report_dir(out_dir) / 'product-url-reader.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read product URLs with Codex/browser evidence before product intake.")
    parser.add_argument("--url", action="append", default=[], help="Product URL. Can be repeated.")
    parser.add_argument("--urls-file", default="", help="Text file with one product URL per line.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before reading provider credentials. Values are never written to reports.")
    parser.add_argument("--skip-browser", action="store_true", help="Skip browser rendering and use static URL intake only.")
    parser.add_argument("--no-static-fallback", action="store_true", help="Do not fall back to static URL intake when browser capture fails.")
    parser.add_argument("--install-browser-if-missing", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--screenshot", action="store_true", help="Save browser screenshots next to structured snapshots.")
    parser.add_argument("--disable-web-text-fallback", action="store_true", help="Disable public web-reader text fallback after browser/static intake failures.")
    parser.add_argument("--web-text-fallback-url-template", default=DEFAULT_WEB_TEXT_FALLBACK_TEMPLATE, help="Fallback text reader URL template. Supports {url} and {encoded_url}.")
    parser.add_argument("--web-text-fallback-file", default="", help="Local text/Markdown fallback file, mainly for Codex-provided page text or tests.")
    parser.add_argument("--web-data-provider", default=os.environ.get("WEB_DATA_PROVIDER", "auto"), choices=["auto", "local", "firecrawl"], help="Optional public web data provider used before web-text fallback.")
    parser.add_argument("--firecrawl-base-url", default=os.environ.get("FIRECRAWL_BASE_URL", DEFAULT_FIRECRAWL_BASE_URL), help="Firecrawl API base URL. API key is read only from FIRECRAWL_API_KEY.")
    parser.add_argument("--web-data-fixture-json", default="", help="Local web data fixture for tests/offline review.")
    return parser.parse_args()


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls = [item.strip() for item in args.url if item.strip()]
    if args.urls_file:
        path = Path(args.urls_file)
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    deduped = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def read_product_url(args: argparse.Namespace, out_dir: Path, url: str, index: int) -> dict[str, Any]:
    item_dir = out_dir / "product-url-reader" / f"{index:03d}-{slug_from_url(url)}"
    item_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    snapshot_path = item_dir / "structured-product-page.json"
    intake_dir = item_dir / "intake"

    browser_status: dict[str, Any] = {"status": "skipped", "reason": "--skip-browser was supplied."}
    web_data_status: dict[str, Any] = {"status": "skipped", "reason": "No provider fallback was needed."}
    web_text_status: dict[str, Any] = {"status": "skipped", "reason": "No fallback was needed."}
    profile_status: dict[str, Any] = {"status": "blocked", "profile": "", "markdown": ""}
    source_mode = "unavailable"

    if not args.skip_browser:
        browser_command = [
            sys.executable,
            str(BROWSER_SNAPSHOT),
            "--url",
            url,
            "--out-file",
            str(snapshot_path),
            "--out-dir",
            str(item_dir),
            "--timeout-ms",
            str(args.timeout_ms),
            "--wait-until",
            args.wait_until,
        ]
        if args.install_browser_if_missing:
            browser_command.append("--install-browser-if-missing")
        if args.screenshot:
            browser_command.append("--screenshot")
        browser_step = run_command("browser_snapshot", browser_command)
        steps.append(browser_step)
        browser_status = {
            "status": "ready" if browser_step["exitCode"] == 0 and snapshot_path.exists() else "error",
            "snapshot": str(snapshot_path) if snapshot_path.exists() else "",
            "exitCode": browser_step["exitCode"],
        }

    if browser_status["status"] == "ready":
        intake_command = [
            sys.executable,
            str(PRODUCT_INTAKE),
            "--structured-json",
            str(snapshot_path),
            "--out-dir",
            str(intake_dir),
        ]
        profile_status = run_intake_command(steps, intake_dir, intake_command, url)
        if usable_profile_status(profile_status):
            source_mode = "browser_structured_snapshot"
    elif args.no_static_fallback:
        intake_command = []
    else:
        intake_command = [
            sys.executable,
            str(PRODUCT_INTAKE),
            "--url",
            url,
            "--out-dir",
            str(intake_dir),
        ]
        profile_status = run_intake_command(steps, intake_dir, intake_command, url)
        if usable_profile_status(profile_status):
            source_mode = "static_url_fallback"

    if not usable_profile_status(profile_status):
        web_data_status = fetch_web_data_provider(args, item_dir, url)
        steps.append(web_data_status.get("_step", {}))
        if web_data_status.get("status") == "ready":
            intake_command = [
                sys.executable,
                str(PRODUCT_INTAKE),
                "--text-file",
                str(web_data_status["textFile"]),
                "--out-dir",
                str(intake_dir),
            ]
            profile_status = run_intake_command(steps, intake_dir, intake_command, url)
            if usable_profile_status(profile_status):
                source_mode = "firecrawl_scrape"

    if not usable_profile_status(profile_status) and not args.disable_web_text_fallback:
        web_text_status = fetch_web_text_fallback(args, item_dir, url)
        steps.append(web_text_status.get("_step", {}))
        if web_text_status.get("status") == "ready":
            intake_command = [
                sys.executable,
                str(PRODUCT_INTAKE),
                "--text-file",
                str(web_text_status["textFile"]),
                "--out-dir",
                str(intake_dir),
            ]
            profile_status = run_intake_command(steps, intake_dir, intake_command, url)
            if usable_profile_status(profile_status):
                source_mode = "web_text_fallback"
    elif not intake_command and not usable_profile_status(profile_status):
        profile_status = {
            "status": "blocked",
            "profile": "",
            "markdown": "",
            "reason": "Browser capture failed and static fallback was disabled.",
        }

    profile = read_json(Path(profile_status.get("profile", ""))) if profile_status.get("profile") else {}
    if profile_status.get("status") == "partial_ready" and profile:
        cached_text_path = write_cached_profile_text(item_dir, profile)
        web_text_status = {
            "status": "ready",
            "source": "cached_profile",
            "textFile": str(cached_text_path),
            "bytes": cached_text_path.stat().st_size,
        }
        source_mode = "cached_profile_fallback"
    workflow_text_path = Path(str(web_data_status.get("textFile") or web_text_status.get("textFile", "")))
    return {
        "id": f"product-url-{index:03d}",
        "url": url,
        "status": record_status(browser_status, profile_status),
        "sourceMode": source_mode if usable_profile_status(profile_status) else "unavailable",
        "workspace": str(item_dir),
        "browser": browser_status,
        "webData": public_web_text_status(web_data_status),
        "webText": public_web_text_status(web_text_status),
        "intake": profile_status,
        "product": summarize_profile(profile),
        "nextWorkflowCommand": next_workflow_command(url, source_mode, snapshot_path, workflow_text_path, out_dir, profile_status),
        "steps": steps,
    }


def run_intake_command(
    steps: list[dict[str, Any]], intake_dir: Path, intake_command: list[str], requested_url: str
) -> dict[str, Any]:
    intake_step = run_command("product_intake", intake_command)
    steps.append(intake_step)
    profile_path = intake_dir / "product-profile.json"
    profile = read_json(profile_path)
    cached_profile_matches = bool(profile) and profile_matches_url(profile, requested_url)
    cached_profile_is_clean = cached_profile_matches and not profile_looks_mojibake(profile)
    if intake_step["exitCode"] == 0 and profile_path.exists():
        status = "ready"
        reason = ""
    elif profile_path.exists() and cached_profile_is_clean:
        status = "partial_ready"
        reason = "Intake command failed, but a matching cached product profile is available."
    elif profile_path.exists() and cached_profile_matches:
        status = "error"
        reason = "Intake command failed and the matching cached product profile appears to contain mojibake."
    else:
        status = "error"
        reason = ""
    return {
        "status": status,
        "profile": str(profile_path) if profile_path.exists() else "",
        "markdown": str(intake_dir / "product-profile.md") if (intake_dir / "product-profile.md").exists() else "",
        "exitCode": intake_step["exitCode"],
        **({"reason": reason} if reason else {}),
    }


def fetch_web_data_provider(args: argparse.Namespace, item_dir: Path, url: str) -> dict[str, Any]:
    text_path = item_dir / "firecrawl-page.md"
    html_path = item_dir / "firecrawl-page.html"
    step = {
        "name": "web_data_provider",
        "command": [
            "python",
            "scripts/web_data_provider.py",
            "--provider",
            args.web_data_provider,
            "scrape",
            "--url",
            url,
        ],
        "exitCode": 0,
        "stdoutTail": "",
        "stderrTail": "",
    }
    try:
        result = scrape_url(
            url,
            provider=args.web_data_provider,
            base_url=args.firecrawl_base_url,
            fixture_json=args.web_data_fixture_json,
        )
    except WebDataProviderError as exc:
        step["exitCode"] = 1
        step["stderrTail"] = str(exc)
        return {"status": "error", "provider": "firecrawl", "textFile": "", "reason": str(exc), "_step": step}

    status = str(result.get("status") or "")
    markdown = str(result.get("markdown") or "")
    html = str(result.get("html") or "")
    if markdown:
        text_path.write_text(markdown, encoding="utf-8")
    if html:
        html_path.write_text(html, encoding="utf-8")
    if status == "ready" and text_path.exists():
        step["stdoutTail"] = f"Web data provider markdown written to: {text_path}"
        return {
            "status": "ready",
            "provider": result.get("provider", ""),
            "captureMode": result.get("captureMode", ""),
            "textFile": str(text_path),
            "htmlFile": str(html_path) if html_path.exists() else "",
            "apiKeyPresent": bool(result.get("apiKeyPresent")),
            "credentialValuesStored": False,
            "_step": step,
        }
    step["exitCode"] = 1 if status in {"blocked", "error"} else 0
    step["stderrTail"] = str(result.get("reason") or "")
    return {
        "status": status or "skipped",
        "provider": result.get("provider", ""),
        "captureMode": result.get("captureMode", ""),
        "textFile": "",
        "apiKeyPresent": bool(result.get("apiKeyPresent")),
        "credentialValuesStored": False,
        "reason": result.get("reason", ""),
        "_step": step,
    }


def fetch_web_text_fallback(args: argparse.Namespace, item_dir: Path, url: str) -> dict[str, Any]:
    text_path = item_dir / "web-reader-page.md"
    if args.web_text_fallback_file:
        source = str(Path(args.web_text_fallback_file))
        step = {
            "name": "web_text_fallback",
            "command": ["read-file", source],
            "exitCode": 0,
            "stdoutTail": "",
            "stderrTail": "",
        }
        try:
            text = Path(args.web_text_fallback_file).read_text(encoding="utf-8-sig")
        except OSError as exc:
            step["exitCode"] = 1
            step["stderrTail"] = str(exc)
            return {"status": "error", "source": source, "textFile": "", "error": str(exc), "_step": step}
    else:
        if not is_public_http_url(url):
            reason = "Web text fallback only reads public http/https URLs."
            return {
                "status": "blocked",
                "source": "",
                "textFile": "",
                "reason": reason,
                "_step": {
                    "name": "web_text_fallback",
                    "command": [],
                    "exitCode": 1,
                    "stdoutTail": "",
                    "stderrTail": reason,
                },
            }
        source = build_web_text_url(args.web_text_fallback_url_template, url)
        step = {
            "name": "web_text_fallback",
            "command": ["web-text-fetch", source],
            "exitCode": 0,
            "stdoutTail": "",
            "stderrTail": "",
        }
        try:
            request = urllib.request.Request(
                source,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/markdown,text/plain,text/html;q=0.8,*/*;q=0.5",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                charset = response.headers.get_content_charset() or ""
                text = decode_html_bytes(response.read(2_000_000), charset)
        except Exception as exc:  # noqa: BLE001 - fallback errors are reported, not raised.
            step["exitCode"] = 1
            step["stderrTail"] = str(exc)
            return {"status": "error", "source": source, "textFile": "", "error": str(exc), "_step": step}

    text_path.write_text(text, encoding="utf-8")
    step["stdoutTail"] = f"Web text fallback written to: {text_path}"
    return {
        "status": "ready",
        "source": source,
        "textFile": str(text_path),
        "bytes": len(text.encode("utf-8")),
        "_step": step,
    }


def public_web_text_status(status: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in status.items() if key != "_step"}


def build_web_text_url(template: str, url: str) -> str:
    return template.format(url=url, encoded_url=urllib.parse.quote(url, safe=""))


def is_public_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.startswith("127.") or host.startswith("0."):
        return False
    private_prefixes = ("10.", "192.168.", "169.254.")
    if host.startswith(private_prefixes):
        return False
    if re.match(r"^172\.(1[6-9]|2\d|3[01])\.", host):
        return False
    return True


def build_report(args: argparse.Namespace, out_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "outDir": str(out_dir),
        "status": report_status(records),
        "records": records,
        "summary": {
            "requestedUrls": len(records),
            "ready": sum(1 for item in records if item["status"] == "ready"),
            "partialReady": sum(1 for item in records if item["status"] == "partial_ready"),
            "blocked": sum(1 for item in records if item["status"] == "blocked"),
            "browserStructuredProfiles": sum(1 for item in records if item["sourceMode"] == "browser_structured_snapshot"),
            "staticFallbackProfiles": sum(1 for item in records if item["sourceMode"] == "static_url_fallback"),
            "firecrawlScrapeProfiles": sum(1 for item in records if item["sourceMode"] == "firecrawl_scrape"),
            "webTextFallbackProfiles": sum(1 for item in records if item["sourceMode"] == "web_text_fallback"),
            "cachedProfileFallbackProfiles": sum(1 for item in records if item["sourceMode"] == "cached_profile_fallback"),
        },
        "recommendedNextCommand": "Use records[].nextWorkflowCommand for the correct structured or static intake mode.",
        "guardrails": [
            "Read browser-visible product page evidence before product intake whenever Chromium is available.",
            "Static URL intake is only a fallback and may miss dynamic page content.",
            "Optional Firecrawl scrape is used only as a public web data fallback and reads FIRECRAWL_API_KEY from the environment.",
            "Public web-reader text fallback is used only after browser/static intake fails and records its source.",
            "Cached profile fallback is used only when a previously written profile matches the requested URL.",
            "Do not extract cookies, passwords, hidden tokens, private endpoints, or bypass login/captcha/risk controls.",
            "Treat pricing, testimonials, customer counts, and legal claims as assumptions unless the product page proves them.",
        ],
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "product-url-reader.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "product-url-reader.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Product URL Reader",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Requested URLs: {report['summary']['requestedUrls']}",
        f"- Browser structured profiles: {report['summary']['browserStructuredProfiles']}",
        f"- Static fallback profiles: {report['summary']['staticFallbackProfiles']}",
        f"- Firecrawl scrape profiles: {report['summary']['firecrawlScrapeProfiles']}",
        f"- Web text fallback profiles: {report['summary']['webTextFallbackProfiles']}",
        "",
        "## Records",
    ]
    for record in report["records"]:
        product = record.get("product", {})
        lines.extend(
            [
                "",
                f"### {record['id']}",
                f"- URL: {record['url']}",
                f"- Status: `{record['status']}`",
                f"- Source mode: `{record['sourceMode']}`",
                f"- Product: {product.get('productName', 'unknown')}",
                f"- Profile: {record['intake'].get('profile', '')}",
                f"- Snapshot: {record['browser'].get('snapshot', '')}",
                f"- Web data: {record.get('webData', {}).get('textFile', '')}",
                f"- Web text: {record.get('webText', {}).get('textFile', '')}",
                f"- Next workflow: `{record.get('nextWorkflowCommand', '')}`",
            ]
        )
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "name": name,
        "command": display_command(command),
        "exitCode": result.returncode,
        "stdoutTail": tail(result.stdout),
        "stderrTail": tail(result.stderr),
    }


def record_status(browser_status: dict[str, Any], profile_status: dict[str, Any]) -> str:
    if browser_status.get("status") == "ready" and profile_status.get("status") == "ready":
        return "ready"
    if usable_profile_status(profile_status):
        return "partial_ready"
    return "blocked"


def report_status(records: list[dict[str, Any]]) -> str:
    if all(item["status"] == "ready" for item in records):
        return "ready"
    if any(item["status"] in {"ready", "partial_ready"} for item in records):
        return "partial_ready"
    return "blocked"


def summarize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile:
        return {}
    return {
        "productName": profile.get("productName", ""),
        "canonicalUrl": profile.get("canonicalUrl", ""),
        "sourceType": profile.get("sourceType", ""),
        "valueProposition": profile.get("valueProposition", ""),
        "pricing": profile.get("pricing", ""),
        "confidence": profile.get("confidence", ""),
        "targetAudienceAssumptions": profile.get("targetAudienceAssumptions", []),
        "painPointAssumptions": profile.get("painPointAssumptions", []),
    }


def next_workflow_command(url: str, source_mode: str, snapshot_path: Path, text_path: Path, out_dir: Path, profile_status: dict[str, Any]) -> str:
    if not usable_profile_status(profile_status):
        return ""
    if source_mode == "browser_structured_snapshot" and snapshot_path.exists():
        return (
            f"python scripts/run_promotion_workflow.py --structured-json \"{snapshot_path}\" "
            f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
        )
    if source_mode in {"firecrawl_scrape", "web_text_fallback", "cached_profile_fallback"} and text_path.exists():
        return (
            f"python scripts/run_promotion_workflow.py --text-file \"{text_path}\" "
            f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
        )
    return (
        f"python scripts/run_promotion_workflow.py --product-url \"{url}\" "
        f"--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir \"{out_dir}\""
    )


def usable_profile_status(profile_status: dict[str, Any]) -> bool:
    return profile_status.get("status") in {"ready", "partial_ready"}


def profile_matches_url(profile: dict[str, Any], requested_url: str) -> bool:
    canonical = str(profile.get("canonicalUrl") or "").strip()
    return bool(canonical) and normalize_url(canonical) == normalize_url(requested_url)


def profile_looks_mojibake(profile: dict[str, Any]) -> bool:
    values: list[str] = []
    for key in ["productName", "title", "description", "valueProposition", "pricing"]:
        values.append(str(profile.get(key) or ""))
    for key in ["targetAudienceAssumptions", "painPointAssumptions", "keywords"]:
        value = profile.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value:
            values.append(str(value))
    return text_looks_mojibake(" ".join(values))


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/") or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{host}{path}{query}" if scheme and host else url.strip().rstrip("/")


def write_cached_profile_text(item_dir: Path, profile: dict[str, Any]) -> Path:
    text_path = item_dir / "cached-product-profile.md"
    lines = [
        f"Product: {profile.get('productName', '')}",
        f"URL: {profile.get('canonicalUrl', '')}",
        f"Description: {profile.get('valueProposition', '')}",
        f"Pricing: {profile.get('pricing', '')}",
        f"Audience: {', '.join(str(item) for item in profile.get('targetAudienceAssumptions', []) if item)}",
        f"Pain points: {', '.join(str(item) for item in profile.get('painPointAssumptions', []) if item)}",
        "Source: cached product profile from a previous matching URL intake.",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return text_path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def slug_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    raw = "-".join(part for part in [parsed.netloc, parsed.path.strip("/")] if part) or url
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    return slug[:80] or "product"


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/intake"


def display_command(command: list[str]) -> list[str]:
    return ["python" if item == sys.executable else item for item in command]


def tail(value: str, limit: int = 1200) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


if __name__ == "__main__":
    main()
