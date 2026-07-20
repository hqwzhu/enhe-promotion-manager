#!/usr/bin/env python3
"""Optional web data backends for public product and competitor evidence."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from env_loader import load_project_env, preparse_env_file


TODAY = date.today().isoformat()
DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v2"
PROVIDER_CHOICES = {"auto", "local", "firecrawl"}
USER_AGENT = "Mozilla/5.0 (compatible; ViralProductPromotionSkill/1.0; +https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator)"


class WebDataProviderError(RuntimeError):
    """Raised when a configured web data provider cannot be used."""


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.command == "scrape":
        report = scrape_url(
            args.url,
            provider=args.provider,
            base_url=args.firecrawl_base_url,
            timeout=args.timeout,
            fixture_json=args.fixture_json,
            formats=split_csv(args.formats) or ["markdown", "html"],
        )
    elif args.command == "search":
        report = search_web(
            args.query,
            limit=args.limit,
            provider=args.provider,
            base_url=args.firecrawl_base_url,
            timeout=args.timeout,
            fixture_json=args.fixture_json,
        )
    elif args.command == "map":
        report = map_site(
            args.url,
            provider=args.provider,
            base_url=args.firecrawl_base_url,
            timeout=args.timeout,
            fixture_json=args.fixture_json,
            search=args.search,
        )
    elif args.command == "crawl":
        report = start_crawl(
            args.url,
            limit=args.limit,
            provider=args.provider,
            base_url=args.firecrawl_base_url,
            timeout=args.timeout,
            fixture_json=args.fixture_json,
        )
    elif args.command == "batch-scrape":
        report = batch_scrape(
            collect_urls(args),
            provider=args.provider,
            base_url=args.firecrawl_base_url,
            timeout=args.timeout,
            fixture_json=args.fixture_json,
            formats=split_csv(args.formats) or ["markdown"],
        )
    elif args.command == "interact-plan":
        report = interact_plan(
            args.url,
            goal=args.goal,
            actions=collect_actions(args),
            provider=args.provider,
            base_url=args.firecrawl_base_url,
        )
    else:
        raise SystemExit(f"Unknown command: {args.command}")
    report["envLoad"] = env_load
    write_report(out_dir, args.command, report)
    print(f"Web data provider report written to: {(report_dir(out_dir) / (args.command + '.json')).resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run optional public web data provider operations.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before reading provider credentials. Values are never written to reports.")
    parser.add_argument("--provider", default=os.environ.get("WEB_DATA_PROVIDER", "auto"), choices=sorted(PROVIDER_CHOICES))
    parser.add_argument("--firecrawl-base-url", default=os.environ.get("FIRECRAWL_BASE_URL", DEFAULT_FIRECRAWL_BASE_URL))
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--fixture-json", default="", help="Local fixture for tests or offline review. Never stores API keys.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape", help="Scrape one public URL into Markdown/HTML evidence.")
    scrape.add_argument("--url", required=True)
    scrape.add_argument("--formats", default="markdown,html")

    search = subparsers.add_parser("search", help="Search the web and return LLM-ready public results.")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=5)

    map_cmd = subparsers.add_parser("map", help="Discover public URLs on a site.")
    map_cmd.add_argument("--url", required=True)
    map_cmd.add_argument("--search", default="")

    crawl = subparsers.add_parser("crawl", help="Start a provider crawl job for a public site.")
    crawl.add_argument("--url", required=True)
    crawl.add_argument("--limit", type=int, default=50)

    batch = subparsers.add_parser("batch-scrape", help="Start a provider batch scrape job.")
    batch.add_argument("--url", action="append", default=[])
    batch.add_argument("--urls-file", default="")
    batch.add_argument("--formats", default="markdown")
    interact = subparsers.add_parser("interact-plan", help="Plan a safe user-visible interact flow without executing browser side effects.")
    interact.add_argument("--url", required=True)
    interact.add_argument("--goal", default="collect public page evidence")
    interact.add_argument("--action", action="append", default=[], help="Proposed visible action, e.g. click:Pricing or wait:networkidle.")
    interact.add_argument("--actions-file", default="", help="Optional text file with one proposed visible action per line.")
    return parser.parse_args()


def scrape_url(
    url: str,
    *,
    provider: str = "auto",
    base_url: str = DEFAULT_FIRECRAWL_BASE_URL,
    timeout: float = 45.0,
    fixture_json: str = "",
    formats: list[str] | None = None,
) -> dict[str, Any]:
    ctx = provider_context(provider, base_url)
    base_report = operation_base("scrape", ctx, {"url": url})
    if fixture_json:
        return normalize_scrape(load_fixture(fixture_json, "scrape"), base_report, "fixture")
    if not ctx["enabled"]:
        return skipped_or_blocked(base_report, ctx)
    if not is_public_http_url(url):
        return blocked(base_report, "Only public http/https URLs can be sent to the web data provider.")
    payload = {"url": url, "formats": formats or ["markdown", "html"]}
    raw = firecrawl_request(ctx, "/scrape", payload, timeout)
    return normalize_scrape(raw, base_report, "firecrawl")


def search_web(
    query: str,
    *,
    limit: int = 5,
    provider: str = "auto",
    base_url: str = DEFAULT_FIRECRAWL_BASE_URL,
    timeout: float = 45.0,
    fixture_json: str = "",
) -> dict[str, Any]:
    ctx = provider_context(provider, base_url)
    base_report = operation_base("search", ctx, {"query": query, "limit": limit})
    if fixture_json:
        return normalize_search(load_fixture(fixture_json, "search"), base_report, "fixture")
    if not ctx["enabled"]:
        return skipped_or_blocked(base_report, ctx)
    raw = firecrawl_request(ctx, "/search", {"query": query, "limit": limit}, timeout)
    return normalize_search(raw, base_report, "firecrawl")


def map_site(
    url: str,
    *,
    provider: str = "auto",
    base_url: str = DEFAULT_FIRECRAWL_BASE_URL,
    timeout: float = 45.0,
    fixture_json: str = "",
    search: str = "",
) -> dict[str, Any]:
    ctx = provider_context(provider, base_url)
    input_data = {"url": url, **({"search": search} if search else {})}
    base_report = operation_base("map", ctx, input_data)
    if fixture_json:
        return normalize_map(load_fixture(fixture_json, "map"), base_report, "fixture")
    if not ctx["enabled"]:
        return skipped_or_blocked(base_report, ctx)
    if not is_public_http_url(url):
        return blocked(base_report, "Only public http/https URLs can be sent to the web data provider.")
    raw = firecrawl_request(ctx, "/map", input_data, timeout)
    return normalize_map(raw, base_report, "firecrawl")


def start_crawl(
    url: str,
    *,
    limit: int = 50,
    provider: str = "auto",
    base_url: str = DEFAULT_FIRECRAWL_BASE_URL,
    timeout: float = 45.0,
    fixture_json: str = "",
) -> dict[str, Any]:
    ctx = provider_context(provider, base_url)
    base_report = operation_base("crawl", ctx, {"url": url, "limit": limit})
    if fixture_json:
        return normalize_job(load_fixture(fixture_json, "crawl"), base_report, "fixture")
    if not ctx["enabled"]:
        return skipped_or_blocked(base_report, ctx)
    if not is_public_http_url(url):
        return blocked(base_report, "Only public http/https URLs can be sent to the web data provider.")
    payload = {"url": url, "limit": limit, "scrapeOptions": {"formats": ["markdown"]}}
    raw = firecrawl_request(ctx, "/crawl", payload, timeout)
    return normalize_job(raw, base_report, "firecrawl")


def batch_scrape(
    urls: list[str],
    *,
    provider: str = "auto",
    base_url: str = DEFAULT_FIRECRAWL_BASE_URL,
    timeout: float = 45.0,
    fixture_json: str = "",
    formats: list[str] | None = None,
) -> dict[str, Any]:
    ctx = provider_context(provider, base_url)
    base_report = operation_base("batch_scrape", ctx, {"urls": urls, "urlCount": len(urls)})
    if fixture_json:
        return normalize_job(load_fixture(fixture_json, "batch_scrape"), base_report, "fixture")
    if not urls:
        return blocked(base_report, "At least one URL is required for batch scrape.")
    bad_urls = [url for url in urls if not is_public_http_url(url)]
    if bad_urls:
        return blocked(base_report, f"Only public http/https URLs can be sent to the web data provider. Refused: {bad_urls[0]}")
    if not ctx["enabled"]:
        return skipped_or_blocked(base_report, ctx)
    raw = firecrawl_request(ctx, "/batch/scrape", {"urls": urls, "formats": formats or ["markdown"]}, timeout)
    return normalize_job(raw, base_report, "firecrawl")


def interact_plan(
    url: str,
    *,
    goal: str,
    actions: list[str],
    provider: str = "auto",
    base_url: str = DEFAULT_FIRECRAWL_BASE_URL,
) -> dict[str, Any]:
    ctx = provider_context(provider, base_url)
    base_report = operation_base("interact_plan", ctx, {"url": url, "goal": goal, "actionCount": len(actions)})
    if not is_public_http_url(url):
        return blocked(base_report, "Only public http/https URLs can be planned for interaction.")
    blocked_actions = [action for action in actions if unsafe_interact_action(action)]
    allowed_actions = [action for action in actions if action not in blocked_actions]
    status = "blocked" if blocked_actions else "ready"
    return {
        **base_report,
        "status": status,
        "captureMode": "plan_only",
        "goal": goal,
        "allowedActions": allowed_actions,
        "blockedActions": blocked_actions,
        "requiresUserVisibleBrowser": True,
        "requiresManualApprovalBeforeExecution": True,
        "providerExecutionEnabled": False,
        "solution": {
            "recommendedPath": "Plan interactions in Codex, then use browser_publish_form_fill.py or browser_publish_session.py only for visible field filling and screenshots.",
            "stopConditions": [
                "login screen",
                "captcha",
                "risk-control prompt",
                "account verification",
                "private analytics page",
                "final publish, like, follow, comment, or DM action",
            ],
            "safeUseCases": [
                "open public pages",
                "scroll public pages",
                "click visible navigation that does not change account state",
                "wait for public content to render",
                "extract visible text, screenshots, and links as evidence",
            ],
        },
        "reason": "Unsafe action requested." if blocked_actions else "",
        "guardrails": guardrails(),
    }


def provider_context(provider: str = "auto", base_url: str = DEFAULT_FIRECRAWL_BASE_URL) -> dict[str, Any]:
    requested = (provider or os.environ.get("WEB_DATA_PROVIDER", "auto")).strip().lower()
    if requested not in PROVIDER_CHOICES:
        raise WebDataProviderError(f"Unsupported WEB_DATA_PROVIDER: {requested}")
    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    normalized_base = normalize_base_url(base_url or os.environ.get("FIRECRAWL_BASE_URL", DEFAULT_FIRECRAWL_BASE_URL))
    if requested == "local":
        return {
            "provider": "local",
            "requestedProvider": requested,
            "enabled": False,
            "status": "skipped",
            "reason": "WEB_DATA_PROVIDER=local keeps all web data collection on the existing local/browser/static paths.",
            "apiKeyPresent": False,
            "baseUrl": normalized_base,
        }
    if requested == "auto" and not api_key:
        return {
            "provider": "local",
            "requestedProvider": requested,
            "enabled": False,
            "status": "skipped",
            "reason": "No FIRECRAWL_API_KEY is present; existing local/browser/static fallbacks remain active.",
            "apiKeyPresent": False,
            "baseUrl": normalized_base,
        }
    if requested == "firecrawl" and not api_key:
        return {
            "provider": "firecrawl",
            "requestedProvider": requested,
            "enabled": False,
            "status": "blocked",
            "reason": "WEB_DATA_PROVIDER=firecrawl requires FIRECRAWL_API_KEY in the environment.",
            "apiKeyPresent": False,
            "baseUrl": normalized_base,
        }
    return {
        "provider": "firecrawl",
        "requestedProvider": requested,
        "enabled": True,
        "status": "ready",
        "reason": "",
        "apiKeyPresent": True,
        "baseUrl": normalized_base,
    }


def firecrawl_request(ctx: dict[str, Any], endpoint: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    if not ctx.get("enabled"):
        raise WebDataProviderError(ctx.get("reason") or "Web data provider is not enabled.")
    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        raise WebDataProviderError("FIRECRAWL_API_KEY is missing.")
    url = join_endpoint(ctx["baseUrl"], endpoint)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise WebDataProviderError(f"Firecrawl HTTP {exc.code}: {safe_error_text(error_text)}") from exc
    except urllib.error.URLError as exc:
        raise WebDataProviderError(f"Firecrawl request failed: {exc}") from exc
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WebDataProviderError(f"Firecrawl returned non-JSON response: {safe_error_text(text)}") from exc
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def normalize_scrape(raw: dict[str, Any], base: dict[str, Any], capture_mode: str) -> dict[str, Any]:
    data = data_object(raw)
    markdown = as_text(data.get("markdown") or raw.get("markdown"))
    html = as_text(data.get("html") or raw.get("html"))
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    status = "ready" if markdown or html else "partial_ready" if raw else "blocked"
    return {
        **base,
        "status": status,
        "captureMode": capture_mode,
        "markdown": markdown,
        "html": html,
        "screenshot": as_text(data.get("screenshot") or raw.get("screenshot")),
        "links": normalize_links(data.get("links") or raw.get("links") or []),
        "metadata": metadata,
        "reason": "" if status != "blocked" else "Provider response did not include usable markdown or html.",
        "rawSummary": raw_summary(raw),
        "guardrails": guardrails(),
    }


def normalize_search(raw: dict[str, Any], base: dict[str, Any], capture_mode: str) -> dict[str, Any]:
    rows = data_list(raw)
    results = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        url = as_text(item.get("url") or item.get("sourceURL") or item.get("sourceUrl"))
        results.append(
            {
                "url": url,
                "title": as_text(item.get("title")),
                "description": as_text(item.get("description") or item.get("snippet")),
                "markdown": as_text(item.get("markdown")),
                "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            }
        )
    return {
        **base,
        "status": "ready" if results else "partial_ready",
        "captureMode": capture_mode,
        "results": results,
        "resultCount": len(results),
        "reason": "" if results else "Provider response did not include search results.",
        "rawSummary": raw_summary(raw),
        "guardrails": guardrails(),
    }


def normalize_map(raw: dict[str, Any], base: dict[str, Any], capture_mode: str) -> dict[str, Any]:
    links = normalize_links(raw.get("links") or raw.get("data") or [])
    return {
        **base,
        "status": "ready" if links else "partial_ready",
        "captureMode": capture_mode,
        "links": links,
        "linkCount": len(links),
        "reason": "" if links else "Provider response did not include links.",
        "rawSummary": raw_summary(raw),
        "guardrails": guardrails(),
    }


def normalize_job(raw: dict[str, Any], base: dict[str, Any], capture_mode: str) -> dict[str, Any]:
    job_id = as_text(raw.get("id") or raw.get("jobId"))
    status_url = as_text(raw.get("url") or raw.get("statusUrl"))
    return {
        **base,
        "status": "ready" if job_id or raw.get("success") else "partial_ready",
        "captureMode": capture_mode,
        "jobId": job_id,
        "statusUrl": status_url,
        "providerStatus": as_text(raw.get("status")),
        "rawSummary": raw_summary(raw),
        "guardrails": guardrails(),
    }


def operation_base(operation: str, ctx: dict[str, Any], input_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "operation": operation,
        "provider": ctx["provider"],
        "requestedProvider": ctx["requestedProvider"],
        "providerEnabled": bool(ctx["enabled"]),
        "apiKeyPresent": bool(ctx["apiKeyPresent"]),
        "credentialValuesStored": False,
        "baseUrl": ctx["baseUrl"],
        "input": input_data,
    }


def skipped_or_blocked(base: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "status": ctx.get("status", "skipped"),
        "reason": ctx.get("reason", ""),
        "guardrails": guardrails(),
    }


def blocked(base: dict[str, Any], reason: str) -> dict[str, Any]:
    return {**base, "status": "blocked", "reason": reason, "guardrails": guardrails()}


def write_report(out_dir: Path, name: str, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / f"{name}.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Web Data Provider",
        "",
        f"- Generated: {report.get('generatedAt', TODAY)}",
        f"- Operation: `{report.get('operation', '')}`",
        f"- Provider: `{report.get('provider', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- API key present: `{bool(report.get('apiKeyPresent'))}`",
        f"- Credential values stored: `{bool(report.get('credentialValuesStored'))}`",
    ]
    if report.get("reason"):
        lines.append(f"- Reason: {report['reason']}")
    if report.get("results"):
        lines.extend(["", "## Results"])
        for item in report["results"][:20]:
            lines.append(f"- {item.get('title') or item.get('url')}: {item.get('url')}")
    if report.get("links"):
        lines.extend(["", "## Links"])
        for item in report["links"][:50]:
            lines.append(f"- {item.get('title') or item.get('url')}: {item.get('url')}")
    if report.get("jobId"):
        lines.extend(["", "## Job", f"- Job ID: `{report['jobId']}`", f"- Status URL: {report.get('statusUrl', '')}"])
    if report.get("allowedActions") or report.get("blockedActions"):
        lines.extend(["", "## Interact Plan"])
        for item in report.get("allowedActions", []):
            lines.append(f"- Allowed: {item}")
        for item in report.get("blockedActions", []):
            lines.append(f"- Blocked: {item}")
        solution = report.get("solution") if isinstance(report.get("solution"), dict) else {}
        if solution.get("recommendedPath"):
            lines.append(f"- Recommended path: {solution['recommendedPath']}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report.get("guardrails", guardrails()))
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/web-data"


def load_fixture(path: str, operation: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and operation in payload and isinstance(payload[operation], dict):
        return payload[operation]
    return payload if isinstance(payload, dict) else {"data": payload}


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls = [item.strip() for item in args.url if item.strip()]
    if args.urls_file:
        for line in Path(args.urls_file).read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return dedupe(urls)


def collect_actions(args: argparse.Namespace) -> list[str]:
    actions = [item.strip() for item in getattr(args, "action", []) if item.strip()]
    actions_file = getattr(args, "actions_file", "")
    if actions_file:
        for line in Path(actions_file).read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                actions.append(line)
    return dedupe(actions)


def unsafe_interact_action(action: str) -> bool:
    text = action.strip().lower()
    unsafe_terms = [
        "login",
        "captcha",
        "cookie",
        "token",
        "publish",
        "submit",
        "like",
        "follow",
        "comment",
        "dm",
        "message",
        "private",
        "risk",
        "verification",
    ]
    return any(term in text for term in unsafe_terms)


def normalize_base_url(value: str) -> str:
    text = (value or DEFAULT_FIRECRAWL_BASE_URL).strip().rstrip("/")
    if text.endswith("/v1") or text.endswith("/v2"):
        return text
    return f"{text}/v2"


def join_endpoint(base_url: str, endpoint: str) -> str:
    return base_url.rstrip("/") + "/" + endpoint.lstrip("/")


def is_public_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local)


def data_object(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data")
    if isinstance(data, dict):
        return data
    return raw


def data_list(raw: dict[str, Any]) -> list[Any]:
    data = raw.get("data")
    if isinstance(data, list):
        return data
    if isinstance(raw.get("results"), list):
        return raw["results"]
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]
    return []


def normalize_links(value: Any) -> list[dict[str, str]]:
    links = []
    if not isinstance(value, list):
        return links
    for item in value:
        if isinstance(item, str):
            links.append({"url": item, "title": "", "description": ""})
        elif isinstance(item, dict):
            url = as_text(item.get("url") or item.get("href") or item.get("sourceURL") or item.get("sourceUrl"))
            if url:
                links.append(
                    {
                        "url": url,
                        "title": as_text(item.get("title")),
                        "description": as_text(item.get("description")),
                    }
                )
    return links


def raw_summary(raw: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ["success", "id", "url", "status", "total", "completed", "creditsUsed"]:
        if key in raw:
            summary[key] = raw[key]
    if "data" in raw:
        summary["dataType"] = type(raw["data"]).__name__
        if isinstance(raw["data"], list):
            summary["dataCount"] = len(raw["data"])
    return summary


def safe_error_text(value: str, limit: int = 500) -> str:
    cleaned = re.sub(r"fc-[A-Za-z0-9_\-]+", "fc-REDACTED", value or "")
    return cleaned[:limit]


def as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def dedupe(values: list[str]) -> list[str]:
    result = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def guardrails() -> list[str]:
    return [
        "Only public URLs and public web search results may be sent to the provider.",
        "Provider API keys are read from environment variables only and are not written to reports.",
        "No login, captcha bypass, private endpoint access, browser cookie extraction, or hidden token reuse.",
        "Interact-style workflows are plan-only unless reviewed in a user-visible browser and must stop before final platform side effects.",
        "Provider results are evidence inputs; product claims, metrics, orders, and revenue still require verified sources.",
    ]


if __name__ == "__main__":
    main()
