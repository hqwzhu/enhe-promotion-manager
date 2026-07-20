#!/usr/bin/env python3
"""Authorize YouTube upload with OAuth and publish in the same process."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from env_loader import (
    YOUTUBE_CLIENT_ID_ENVS,
    YOUTUBE_CLIENT_SECRET_ENVS,
    first_env,
    load_project_env,
    preparse_env_file,
)


TODAY = date.today().isoformat()
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    client_id = args.client_id or first_env(YOUTUBE_CLIENT_ID_ENVS)
    client_secret = first_env(YOUTUBE_CLIENT_SECRET_ENVS)
    auth_url = build_auth_url(client_id, args.redirect_uri, args.state)
    plan = build_plan(args, client_id, client_secret, auth_url, env_load)
    if not args.execute:
        write_report(args.out_dir, {**plan, "status": "dry_run", "reason": "No OAuth or upload performed. Review auth URL and rerun with --execute and approval."})
        print_report_path(args.out_dir)
        return
    validation = validate_execute(args, client_id, client_secret)
    if validation:
        write_report(args.out_dir, {**plan, **validation})
        print_report_path(args.out_dir)
        return
    code_result = get_authorization_code(args, auth_url)
    if code_result.get("status") != "ready":
        write_report(args.out_dir, {**plan, **code_result})
        print_report_path(args.out_dir)
        return
    token_result = exchange_code_for_token(code_result["code"], client_id, client_secret, args.redirect_uri)
    if token_result.get("status") != "ready":
        write_report(args.out_dir, {**plan, **token_result})
        print_report_path(args.out_dir)
        return
    upload_result = upload_video(args, token_result["accessToken"])
    write_report(args.out_dir, {**plan, **upload_result})
    print_report_path(args.out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YouTube OAuth authorization and upload without saving tokens.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval", default="", help=f"Must equal {APPROVAL_PHRASE} when --execute is used.")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before reading credentials. Values are never written to reports.")
    parser.add_argument("--client-id", default="", help="OAuth client ID. Prefer GOOGLE_OAUTH_CLIENT_ID or YOUTUBE_CLIENT_ID in the environment.")
    parser.add_argument("--redirect-uri", default="http://127.0.0.1:8765/oauth2callback")
    parser.add_argument("--auth-code", default="", help="Optional authorization code if you do not want the local callback server.")
    parser.add_argument("--no-browser", action="store_true", help="Print the URL and wait for the callback/code without opening a browser.")
    parser.add_argument("--callback-timeout", type=int, default=180)
    parser.add_argument("--state", default="")
    parser.add_argument("--video-file", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--description-file")
    parser.add_argument("--tags", default="")
    parser.add_argument("--category-id", default="22")
    parser.add_argument("--privacy-status", default="private", choices=["private", "public", "unlisted"])
    parser.add_argument("--out-dir", default="./promotion-output")
    return parser.parse_args()


def build_plan(args: argparse.Namespace, client_id: str, client_secret: str, auth_url: str, env_load: dict[str, object]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "platform": "youtube",
        "envLoad": env_load,
        "officialApi": "Google OAuth 2.0 + YouTube Data API videos.insert",
        "mode": "execute" if args.execute else "dry_run",
        "approvalRequired": True,
        "approvalPhrase": APPROVAL_PHRASE,
        "approvalProvided": args.approval == APPROVAL_PHRASE,
        "credentialStatus": {
            "clientId": "present" if client_id else "missing",
            "clientSecret": "present" if client_secret else "missing",
            "tokensSaved": False,
        },
        "authUrl": auth_url if client_id else "",
        "request": {
            "videoFile": args.video_file,
            "title": args.title,
            "privacyStatus": args.privacy_status,
            "scope": YOUTUBE_UPLOAD_SCOPE,
            "redirectUri": args.redirect_uri,
            "clientLibrary": "google-api-python-client",
        },
        "guardrails": [
            "Default mode is dry-run.",
            "Execution requires explicit approval.",
            "OAuth access and refresh tokens are not written to files or reports.",
            "The script uploads only after a user-visible Google consent flow.",
        ],
    }


def validate_execute(args: argparse.Namespace, client_id: str, client_secret: str) -> dict[str, Any] | None:
    if args.approval != APPROVAL_PHRASE:
        return {"status": "blocked", "reason": f"Execution requires --approval {APPROVAL_PHRASE}."}
    if not client_id:
        return {"status": "blocked", "reason": "Execution requires GOOGLE_OAUTH_CLIENT_ID/YOUTUBE_CLIENT_ID or --client-id."}
    if not client_secret:
        return {"status": "blocked", "reason": "Execution requires GOOGLE_OAUTH_CLIENT_SECRET or YOUTUBE_CLIENT_SECRET in the environment."}
    if not Path(args.video_file).exists():
        return {"status": "blocked", "reason": f"Video file not found: {args.video_file}"}
    return None


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    if not client_id:
        return ""
    state = state or uuid.uuid4().hex
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": YOUTUBE_UPLOAD_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return "https://accounts.google.com/o/oauth2/v2/auth?" + query


def get_authorization_code(args: argparse.Namespace, auth_url: str) -> dict[str, Any]:
    if args.auth_code:
        return {"status": "ready", "code": args.auth_code, "source": "provided_auth_code"}
    server = CallbackServer(args.redirect_uri)
    server.start()
    if not args.no_browser:
        webbrowser.open(auth_url)
    deadline = time.time() + max(args.callback_timeout, 5)
    while time.time() < deadline:
        result = server.result
        if result:
            server.stop()
            if result.get("error"):
                return {"status": "error", "reason": result["error"]}
            if result.get("code"):
                return {"status": "ready", "code": result["code"], "source": "local_callback"}
        time.sleep(0.2)
    server.stop()
    return {"status": "blocked", "reason": "Timed out waiting for OAuth callback."}


class CallbackServer:
    def __init__(self, redirect_uri: str) -> None:
        parsed = urllib.parse.urlparse(redirect_uri)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 8765
        self.path = parsed.path or "/oauth2callback"
        self.result: dict[str, str] = {}
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler.
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != owner.path:
                    self.send_response(404)
                    self.end_headers()
                    return
                query = urllib.parse.parse_qs(parsed.query)
                owner.result = {key: values[0] for key, values in query.items() if values}
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Authorization received. You can close this browser tab and return to Codex.")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

        self.httpd = HTTPServer((self.host, self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict[str, Any]:
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "ViralProductPromotionSkill/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "httpStatus": exc.code, "reason": message[:500]}
    except Exception as exc:  # noqa: BLE001 - CLI reports connector errors compactly.
        return {"status": "error", "reason": str(exc)}
    access_token = data.get("access_token", "")
    if not access_token:
        return {"status": "error", "reason": "OAuth token response did not include an access token."}
    return {
        "status": "ready",
        "accessToken": access_token,
        "tokenType": data.get("token_type", ""),
        "expiresIn": data.get("expires_in"),
        "refreshTokenReceived": bool(data.get("refresh_token")),
    }


def upload_video(args: argparse.Namespace, access_token: str) -> dict[str, Any]:
    client_error = google_api_client_dependency_error()
    if client_error:
        return client_error
    video_path = Path(args.video_file)
    metadata = {
        "snippet": {
            "title": args.title,
            "description": read_description(args),
            "tags": split_csv(args.tags),
            "categoryId": args.category_id,
        },
        "status": {"privacyStatus": args.privacy_status},
    }
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        credentials = Credentials(token=access_token, scopes=[YOUTUBE_UPLOAD_SCOPE])
        youtube = build("youtube", "v3", credentials=credentials)
        media = MediaFileUpload(str(video_path), mimetype=mimetypes.guess_type(str(video_path))[0] or "video/mp4", resumable=True)
        data = youtube.videos().insert(part="snippet,status", body=metadata, media_body=media).execute()
    except HttpError as exc:
        content = exc.content.decode("utf-8", errors="replace") if getattr(exc, "content", None) else str(exc)
        return {"status": "error", "httpStatus": getattr(getattr(exc, "resp", None), "status", 0), "reason": content[:500]}
    except Exception as exc:  # noqa: BLE001 - CLI reports connector errors compactly.
        return {"status": "error", "reason": str(exc)}
    video_id = data.get("id", "")
    return {
        "status": "published",
        "publishedUrl": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
        "contentId": video_id,
        "tokenSaved": False,
        "evidence": [f"https://www.youtube.com/watch?v={video_id}" if video_id else ""],
        "clientLibrary": "google-api-python-client",
    }


def read_description(args: argparse.Namespace) -> str:
    if args.description_file:
        return Path(args.description_file).read_text(encoding="utf-8")
    return args.description


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def google_api_client_dependency_error() -> dict[str, Any] | None:
    try:
        import google.oauth2.credentials  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
        import googleapiclient.http  # noqa: F401
    except ImportError as exc:
        return {
            "status": "blocked",
            "reason": (
                "YouTube upload requires google-api-python-client and Google auth helpers. "
                "Install with: python -m pip install -r requirements-youtube.txt"
            ),
            "missingDependency": str(exc),
        }
    return None


def write_report(out_dir: str, result: dict[str, Any]) -> None:
    sanitized = sanitize(result)
    report_dir = Path(out_dir) / "reports/promotion-manager/publish-results"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "youtube-oauth-publish.json").write_text(json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report_dir / "youtube-oauth-publish.md").write_text(render_markdown(sanitized) + "\n", encoding="utf-8")


def sanitize(result: dict[str, Any]) -> dict[str, Any]:
    blocked_keys = {"accessToken", "refresh_token", "access_token", "id_token"}
    return {key: value for key, value in result.items() if key not in blocked_keys}


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# YouTube OAuth Publish",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Official API: {result.get('officialApi')}",
        f"- Published URL: {result.get('publishedUrl', '') or 'not published'}",
        "",
        "## Request",
    ]
    for key, value in (result.get("request") or {}).items():
        lines.append(f"- {key}: {value}")
    if result.get("authUrl"):
        lines.extend(["", "## Auth URL", "", result["authUrl"]])
    if result.get("reason"):
        lines.extend(["", "## Reason", "", result["reason"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in result.get("guardrails", [])])
    return "\n".join(lines)


def print_report_path(out_dir: str) -> None:
    print(f"YouTube OAuth publish report written to: {Path(out_dir).resolve() / 'reports/promotion-manager/publish-results/youtube-oauth-publish.json'}")


if __name__ == "__main__":
    main()
