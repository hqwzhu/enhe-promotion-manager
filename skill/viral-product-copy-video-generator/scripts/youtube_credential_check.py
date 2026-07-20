#!/usr/bin/env python3
"""Check YouTube official API credential readiness without printing secrets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from env_loader import (
    YOUTUBE_ACCESS_TOKEN_ENVS,
    YOUTUBE_CLIENT_ID_ENVS,
    YOUTUBE_CLIENT_SECRET_ENVS,
    YOUTUBE_REFRESH_TOKEN_ENVS,
    blank_env_names,
    first_env,
    load_project_env,
    present_env_names,
    preparse_env_file,
)


TODAY = date.today().isoformat()
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args, env_load)
    write_report(out_dir, report)
    print(f"YouTube credential check written to: {(report_dir(out_dir) / 'youtube-credential-check.json').resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify YouTube API credential presence without exposing values.")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before checking credentials. Values are never written to reports.")
    parser.add_argument("--out-dir", default="./promotion-output")
    parser.add_argument(
        "--check-channel",
        action="store_true",
        help="Use the official YouTube Data API channels.list(mine=true) read-only call when an access token is present.",
    )
    return parser.parse_args()


def build_report(args: argparse.Namespace, env_load: dict[str, object]) -> dict[str, Any]:
    groups = {
        "oauthClientId": env_group(YOUTUBE_CLIENT_ID_ENVS, required_for="oauth_consent_flow"),
        "oauthClientSecret": env_group(YOUTUBE_CLIENT_SECRET_ENVS, required_for="oauth_consent_flow"),
        "uploadAccessToken": env_group(YOUTUBE_ACCESS_TOKEN_ENVS, required_for="direct_upload_executor"),
        "refreshToken": env_group(YOUTUBE_REFRESH_TOKEN_ENVS, required_for="future_token_refresh", optional=True),
        "apiKey": env_group(("YOUTUBE_API_KEY",), required_for="public_metrics_recovery", optional=True),
        "channelHint": env_group(("YOUTUBE_CHANNEL_ID", "YOUTUBE_ACCOUNT"), required_for="preview_expected_account", optional=True),
    }
    oauth_flow_ready = groups["oauthClientId"]["ready"] and groups["oauthClientSecret"]["ready"]
    access_token_ready = groups["uploadAccessToken"]["ready"]
    dependencies = {
        "googleApiPythonClient": python_module_status("googleapiclient"),
        "googleAuthOauthlib": python_module_status("google_auth_oauthlib"),
        "googleAuthHttplib2": python_module_status("google_auth_httplib2"),
    }
    channel_probe = channel_probe_status(args.check_channel, access_token_ready, dependencies)
    status = overall_status(oauth_flow_ready, access_token_ready, channel_probe)
    return {
        "generatedAt": TODAY,
        "status": status,
        "envLoad": env_load,
        "officialApi": "YouTube Data API v3 + Google OAuth 2.0",
        "credentialGroups": groups,
        "readiness": {
            "oauthConsentFlowReady": oauth_flow_ready,
            "directUploadTokenPresent": access_token_ready,
            "dryRunUploadPortReady": oauth_flow_ready or access_token_ready,
            "realPublishGateSatisfied": publish_gate_satisfied(),
            "requiredUploadScope": YOUTUBE_UPLOAD_SCOPE,
        },
        "dependencies": dependencies,
        "officialReadOnlyProbe": channel_probe,
        "guardrails": [
            "This checker records environment variable names and readiness states only.",
            "It never prints, stores, or validates raw credential values.",
            "Default behavior does not call YouTube APIs; --check-channel performs a read-only official API probe when an access token is present.",
            "Real uploads still require the publish executor, a reviewed video file, I_APPROVE_PUBLISH=true, PUBLISH_DRY_RUN=false, and explicit approval.",
        ],
    }


def env_group(names: tuple[str, ...], *, required_for: str, optional: bool = False) -> dict[str, Any]:
    present = present_env_names(names)
    blank = blank_env_names(names)
    if present:
        state = "ready"
    elif blank:
        state = "blank"
    else:
        state = "missing"
    return {
        "acceptedEnv": list(names),
        "presentEnv": present,
        "blankEnv": blank,
        "ready": bool(present),
        "state": state,
        "requiredFor": required_for,
        "optional": optional,
        "valuesStored": False,
    }


def python_module_status(name: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return {"available": result.returncode == 0, "module": name}


def channel_probe_status(check_channel: bool, access_token_ready: bool, dependencies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not check_channel:
        return {"status": "skipped", "reason": "Run with --check-channel to perform a read-only official API probe."}
    if not access_token_ready:
        return {"status": "blocked", "reason": "No YouTube OAuth access token is present."}
    missing = [name for name, info in dependencies.items() if not info.get("available")]
    if missing:
        return {"status": "blocked", "reason": "Missing Google API Python dependencies.", "missingDependencies": missing}
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        credentials = Credentials(token=first_env(YOUTUBE_ACCESS_TOKEN_ENVS), scopes=[YOUTUBE_UPLOAD_SCOPE])
        youtube = build("youtube", "v3", credentials=credentials)
        response = youtube.channels().list(part="snippet", mine=True).execute()
    except HttpError as exc:
        content = exc.content.decode("utf-8", errors="replace") if getattr(exc, "content", None) else str(exc)
        return {"status": "error", "httpStatus": getattr(getattr(exc, "resp", None), "status", 0), "reason": content[:500]}
    except Exception as exc:  # noqa: BLE001 - CLI reports connector errors compactly.
        return {"status": "error", "reason": str(exc)[:500]}
    items = response.get("items") if isinstance(response, dict) else []
    safe_channels = []
    for item in (items if isinstance(items, list) else []):
        snippet = item.get("snippet") if isinstance(item, dict) else {}
        safe_channels.append(
            {
                "channelIdPresent": bool(item.get("id")) if isinstance(item, dict) else False,
                "titlePresent": bool(snippet.get("title")) if isinstance(snippet, dict) else False,
            }
        )
    return {"status": "ready", "channelCount": len(safe_channels), "channels": safe_channels, "valuesStored": False}


def publish_gate_satisfied() -> bool:
    return env_bool("I_APPROVE_PUBLISH", False) and not env_bool("PUBLISH_DRY_RUN", True)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def overall_status(oauth_flow_ready: bool, access_token_ready: bool, channel_probe: dict[str, Any]) -> str:
    if channel_probe.get("status") == "ready":
        return "ready_official_readonly_probe_passed"
    if oauth_flow_ready and access_token_ready:
        return "ready_oauth_flow_and_access_token_present"
    if oauth_flow_ready:
        return "ready_oauth_flow_credentials_present"
    if access_token_ready:
        return "ready_access_token_present"
    return "blocked_missing_or_blank_youtube_credentials"


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    directory = report_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "youtube-credential-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "youtube-credential-check.md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# YouTube Credential Check",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Official API: {report['officialApi']}",
        "",
        "## Credential Groups",
    ]
    for name, group in report["credentialGroups"].items():
        lines.append(
            f"- `{name}`: `{group['state']}`; accepted env: {', '.join(group['acceptedEnv'])}; "
            f"present: {', '.join(group['presentEnv']) or 'none'}; blank: {', '.join(group['blankEnv']) or 'none'}"
        )
    lines.extend(["", "## Readiness"])
    for key, value in report["readiness"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Read-Only Probe", f"- Status: `{report['officialReadOnlyProbe'].get('status')}`"])
    if report["officialReadOnlyProbe"].get("reason"):
        lines.append(f"- Reason: {report['officialReadOnlyProbe']['reason']}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def report_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/capability"


if __name__ == "__main__":
    main()
