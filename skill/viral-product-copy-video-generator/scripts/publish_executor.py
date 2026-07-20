#!/usr/bin/env python3
"""Execute approved official publishing actions for supported platforms."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from env_loader import (
    YOUTUBE_ACCESS_TOKEN_ENVS,
    first_env,
    load_project_env,
    preparse_env_file,
)


TODAY = date.today().isoformat()
APPROVAL_PHRASE = "I_APPROVE_PUBLISH"
GITHUB_API_VERSION = "2022-11-28"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main() -> None:
    env_load = load_project_env(preparse_env_file())
    args = parse_args()
    execution = build_execution(args, env_load)
    if args.platform == "github":
        result = execute_github(args, execution)
    elif args.platform == "youtube":
        result = execute_youtube(args, execution)
    elif args.platform == "douyin":
        result = execute_douyin(args, execution)
    else:
        raise SystemExit(f"Unsupported platform: {args.platform}")
    write_result(args.out_dir, result)
    write_audit_log(args.out_dir, result)
    print(f"Publish execution report written to: {Path(args.out_dir).resolve() / 'reports/promotion-manager/publish-results/publish-execution.json'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run approved official publishing actions.")
    parser.add_argument("--platform", required=True, choices=["github", "youtube", "douyin"])
    parser.add_argument("--execute", action="store_true", help="Perform the write action. Default is dry run.")
    parser.add_argument("--approval", default="", help=f"Must equal {APPROVAL_PHRASE} when --execute is used.")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before reading credentials. Values are never written to reports.")
    parser.add_argument("--out-dir", default="./promotion-output")

    github = parser.add_argument_group("GitHub")
    github.add_argument("--github-action", choices=["file", "pull_request", "issue", "release"], default="file")
    github.add_argument("--github-repo", help="owner/repo")
    github.add_argument("--branch", default="")
    github.add_argument("--base-branch", default="")
    github.add_argument("--pr-branch", default="")
    github.add_argument("--pr-branch-prefix", default="")
    github.add_argument("--pr-title", default="")
    github.add_argument("--pr-body", default="")
    github.add_argument("--path", help="Repository path for --github-action file.")
    github.add_argument("--commit-message", default="Publish promotion content")
    github.add_argument("--title", default="")
    github.add_argument("--body", default="")
    github.add_argument("--body-file")
    github.add_argument("--content", default="")
    github.add_argument("--content-file")
    github.add_argument("--tag-name", default="")
    github.add_argument("--draft", action="store_true")
    github.add_argument("--prerelease", action="store_true")

    youtube = parser.add_argument_group("YouTube")
    youtube.add_argument("--video-file")
    youtube.add_argument("--description", default="")
    youtube.add_argument("--description-file")
    youtube.add_argument("--tags", default="", help="Comma-separated YouTube tags.")
    youtube.add_argument("--category-id", default=os.environ.get("YOUTUBE_CATEGORY_ID") or "28")
    youtube.add_argument("--privacy-status", default="private", choices=["private", "public", "unlisted"])

    douyin = parser.add_argument_group("Douyin")
    douyin.add_argument("--douyin-video-file", default="", help="MP4 to upload through the Douyin Open Platform API.")
    douyin.add_argument("--douyin-text", default="", help="Douyin post text. Defaults to --title.")
    douyin.add_argument("--douyin-text-file", default="", help="File containing Douyin post text.")
    return parser.parse_args()


def build_execution(args: argparse.Namespace, env_load: dict[str, object]) -> dict[str, Any]:
    return {
        "generatedAt": TODAY,
        "generatedAtUtc": utc_now(),
        "platform": args.platform,
        "envLoad": env_load,
        "mode": "execute_requested" if args.execute else "dry_run",
        "approvalRequired": True,
        "approvalPhrase": APPROVAL_PHRASE,
        "approvalProvided": args.approval == APPROVAL_PHRASE,
        "environmentGate": publish_environment_gate(),
        "guardrails": [
            "Default mode is dry-run.",
            "Writes require --execute, I_APPROVE_PUBLISH=true, PUBLISH_DRY_RUN=false, and explicit approval when manual approval is required.",
            "Credentials are read from environment variables only and are never written to reports.",
            "Do not bypass captcha, login, risk controls, or platform review.",
        ],
    }


def execute_github(args: argparse.Namespace, execution: dict[str, Any]) -> dict[str, Any]:
    args.github_repo = args.github_repo or github_repo_from_env()
    args.branch = args.branch or os.environ.get("GITHUB_BRANCH", "")
    args.base_branch = args.base_branch or os.environ.get("GITHUB_PR_BASE", "") or args.branch or "main"
    args.pr_branch_prefix = args.pr_branch_prefix or os.environ.get("GITHUB_PR_BRANCH_PREFIX", "") or "auto-publish"
    if github_should_create_pr(args) and not args.pr_branch:
        args.pr_branch = github_target_branch(args)
    if not args.github_repo:
        return blocked(execution, "missing_github_repo", "Provide --github-repo owner/repo.")
    token_status = "present" if github_token() else "missing"
    plan = {
        **execution,
        "officialApi": "GitHub REST API",
        "action": args.github_action,
        "repository": args.github_repo,
        "credentialStatus": token_status,
        "request": github_request_preview(args),
        "publishPreview": github_publish_preview(args),
    }
    print_preview(plan)
    validation = validate_write_gate(args, token_status, "GITHUB_TOKEN or GH_TOKEN")
    if validation:
        return {**plan, **validation}
    if args.github_action in {"file", "pull_request"}:
        return {**plan, **github_put_file(args)}
    if args.github_action == "issue":
        return {**plan, **github_create_issue(args)}
    return {**plan, **github_create_release(args)}


def github_request_preview(args: argparse.Namespace) -> dict[str, Any]:
    if args.github_action in {"file", "pull_request"}:
        create_pr = github_should_create_pr(args)
        return {
            "method": "PUT",
            "endpoint": f"/repos/{args.github_repo}/contents/{args.path or ''}",
            "branch": args.pr_branch if create_pr else args.branch,
            "baseBranch": args.base_branch,
            "createPullRequest": create_pr,
            "message": args.commit_message,
        }
    if args.github_action == "issue":
        return {"method": "POST", "endpoint": f"/repos/{args.github_repo}/issues", "title": args.title}
    return {
        "method": "POST",
        "endpoint": f"/repos/{args.github_repo}/releases",
        "tag_name": args.tag_name,
        "draft": args.draft,
        "prerelease": args.prerelease,
    }


def github_put_file(args: argparse.Namespace) -> dict[str, Any]:
    if not args.path:
        return {"status": "blocked", "reason": "Provide --path for GitHub file publishing."}
    content = read_text_argument(args.content, args.content_file, "--content or --content-file")
    repo_path = urllib.parse.quote(args.path.strip("/"), safe="/")
    create_pr = github_should_create_pr(args)
    target_branch = args.pr_branch if create_pr else args.branch
    if create_pr:
        branch_result = github_prepare_branch(args, target_branch)
        if branch_result["status"] != "ready":
            return branch_result
    get_result = github_api("GET", f"/repos/{args.github_repo}/contents/{repo_path}", query={"ref": target_branch} if target_branch else None)
    sha = ""
    if get_result["status"] == "ready":
        sha = get_result["data"].get("sha", "")
    elif get_result.get("httpStatus") not in (404, None):
        return get_result
    body: dict[str, Any] = {
        "message": args.commit_message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if sha:
        body["sha"] = sha
    if target_branch:
        body["branch"] = target_branch
    result = github_api("PUT", f"/repos/{args.github_repo}/contents/{repo_path}", body=body)
    if result["status"] != "ready":
        return result
    data = result["data"]
    if create_pr:
        pr = github_create_pull_request(args, target_branch)
        if pr["status"] != "ready":
            return pr
        return {
            "status": "published",
            "publishMode": "pull_request_created",
            "publishedUrl": pr.get("publishedUrl", ""),
            "contentId": pr.get("contentId", ""),
            "commitSha": data.get("commit", {}).get("sha", ""),
            "evidence": [pr.get("publishedUrl", ""), data.get("content", {}).get("html_url", "")],
        }
    return {
        "status": "published",
        "publishMode": "direct_commit",
        "publishedUrl": data.get("content", {}).get("html_url", ""),
        "commitSha": data.get("commit", {}).get("sha", ""),
        "evidence": [data.get("content", {}).get("html_url", "")],
    }


def github_prepare_branch(args: argparse.Namespace, target_branch: str) -> dict[str, Any]:
    base_branch = args.base_branch or args.branch or "main"
    existing = github_api("GET", f"/repos/{args.github_repo}/git/ref/heads/{urllib.parse.quote(target_branch, safe='')}")
    if existing["status"] == "ready":
        return existing
    if existing.get("httpStatus") not in (404, None):
        return existing
    base_ref = github_api("GET", f"/repos/{args.github_repo}/git/ref/heads/{urllib.parse.quote(base_branch, safe='')}")
    if base_ref["status"] != "ready":
        return {
            "status": "error",
            "reason": f"Cannot read GitHub base branch '{base_branch}'. Check repository access and branch name.",
            "details": base_ref.get("reason", ""),
        }
    sha = nested_value(base_ref.get("data", {}), "sha")
    if not sha:
        return {"status": "error", "reason": f"GitHub base branch '{base_branch}' did not return an object SHA."}
    return github_api("POST", f"/repos/{args.github_repo}/git/refs", body={"ref": f"refs/heads/{target_branch}", "sha": sha})


def github_create_pull_request(args: argparse.Namespace, target_branch: str) -> dict[str, Any]:
    title = args.pr_title or args.title or args.commit_message or "Publish promotion content"
    body = args.pr_body or "Automated promotion content update generated by ENHE Product Promo Maker."
    result = github_api(
        "POST",
        f"/repos/{args.github_repo}/pulls",
        body={"title": title, "head": target_branch, "base": args.base_branch or "main", "body": body},
    )
    if result["status"] != "ready":
        return result
    data = result["data"]
    return {"status": "ready", "publishedUrl": data.get("html_url", ""), "contentId": str(data.get("number", ""))}


def github_create_issue(args: argparse.Namespace) -> dict[str, Any]:
    title = args.title or "Promotion content"
    body = read_text_argument(args.body, args.body_file, "--body or --body-file")
    result = github_api("POST", f"/repos/{args.github_repo}/issues", body={"title": title, "body": body})
    if result["status"] != "ready":
        return result
    data = result["data"]
    return {"status": "published", "publishedUrl": data.get("html_url", ""), "contentId": str(data.get("number", "")), "evidence": [data.get("html_url", "")]}


def github_create_release(args: argparse.Namespace) -> dict[str, Any]:
    if not args.tag_name:
        return {"status": "blocked", "reason": "Provide --tag-name for GitHub release publishing."}
    body = read_text_argument(args.body, args.body_file, "--body or --body-file")
    payload = {
        "tag_name": args.tag_name,
        "name": args.title or args.tag_name,
        "body": body,
        "draft": args.draft,
        "prerelease": args.prerelease,
    }
    result = github_api("POST", f"/repos/{args.github_repo}/releases", body=payload)
    if result["status"] != "ready":
        return result
    data = result["data"]
    return {"status": "published", "publishedUrl": data.get("html_url", ""), "contentId": str(data.get("id", "")), "evidence": [data.get("html_url", "")]}


def github_api(method: str, path: str, body: dict[str, Any] | None = None, query: dict[str, str] | None = None) -> dict[str, Any]:
    url = "https://api.github.com" + path
    if query:
        clean_query = {key: value for key, value in query.items() if value}
        if clean_query:
            url += "?" + urllib.parse.urlencode(clean_query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "ViralProductPromotionSkill/1.0",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "Authorization": "Bearer " + github_token(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"status": "ready", "httpStatus": response.status, "data": payload}
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "httpStatus": exc.code, "reason": message[:500]}
    except Exception as exc:  # noqa: BLE001 - CLI reports connector errors compactly.
        return {"status": "error", "reason": str(exc)}


def execute_youtube(args: argparse.Namespace, execution: dict[str, Any]) -> dict[str, Any]:
    token_status = "present" if youtube_token() else "missing"
    plan = {
        **execution,
        "officialApi": "YouTube Data API videos.insert",
        "action": "video_upload",
        "credentialStatus": token_status,
        "request": {
            "method": "POST",
            "endpoint": "youtube.videos.insert(part=snippet,status)",
            "clientLibrary": "google-api-python-client",
            "videoFile": args.video_file or "",
            "privacyStatus": args.privacy_status,
            "title": args.title,
        },
        "publishPreview": youtube_publish_preview(args),
    }
    print_preview(plan)
    if not args.video_file:
        return blocked(plan, "missing_video_file", "Provide --video-file for YouTube upload.")
    if not args.title:
        return blocked(plan, "missing_title", "Provide --title for YouTube upload.")
    validation = validate_write_gate(args, token_status, "YOUTUBE_ACCESS_TOKEN or YOUTUBE_OAUTH_ACCESS_TOKEN")
    if validation:
        return {**plan, **validation}
    return {**plan, **youtube_upload(args)}


def youtube_upload(args: argparse.Namespace) -> dict[str, Any]:
    client_error = google_api_client_dependency_error()
    if client_error:
        return client_error
    video_path = Path(args.video_file)
    if not video_path.exists():
        return {"status": "blocked", "reason": f"Video file not found: {video_path}"}
    description = read_optional_text_argument(args.description, args.description_file)
    metadata = {
        "snippet": {
            "title": args.title,
            "description": description,
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

        credentials = Credentials(token=youtube_token(), scopes=[YOUTUBE_UPLOAD_SCOPE])
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
        "evidence": [f"https://www.youtube.com/watch?v={video_id}" if video_id else ""],
        "clientLibrary": "google-api-python-client",
    }


def execute_douyin(args: argparse.Namespace, execution: dict[str, Any]) -> dict[str, Any]:
    video_file = args.douyin_video_file or args.video_file or ""
    text = read_optional_text_argument(args.douyin_text, args.douyin_text_file) or args.title
    token_status = "present" if douyin_token() and douyin_open_id() else "missing"
    plan = {
        **execution,
        "officialApi": "Douyin Open Platform video upload/create",
        "action": "video_upload_create",
        "credentialStatus": token_status,
        "request": douyin_request_preview(video_file, text),
        "publishPreview": douyin_publish_preview(video_file, text),
        "userConfirmationRequired": True,
        "platformReview": "created Douyin videos are subject to platform review before they should be treated as published.",
    }
    print_preview(plan)
    if not video_file:
        return blocked(plan, "missing_video_file", "Provide --douyin-video-file for Douyin upload.")
    if not text:
        return blocked(plan, "missing_text", "Provide --title, --douyin-text, or --douyin-text-file for Douyin upload.")
    validation = validate_write_gate(args, token_status, "DOUYIN_ACCESS_TOKEN and DOUYIN_OPEN_ID")
    if validation:
        return {**plan, **validation}
    return {**plan, **douyin_upload_and_create(video_file, text)}


def douyin_request_preview(video_file: str, text: str) -> dict[str, Any]:
    return {
        "upload": {
            "method": "POST",
            "endpoint": "/api/douyin/v1/video/upload_video/",
            "query": {"open_id": "<DOUYIN_OPEN_ID>"},
            "headers": {"access-token": "<DOUYIN_ACCESS_TOKEN>"},
            "videoFile": video_file,
        },
        "create": {
            "method": "POST",
            "endpoint": "/api/douyin/v1/video/create_video/",
            "query": {"open_id": "<DOUYIN_OPEN_ID>"},
            "headers": {"access-token": "<DOUYIN_ACCESS_TOKEN>"},
            "body": {"video_id": "<returned by upload_video>", "text": text},
        },
    }


def douyin_upload_and_create(video_file: str, text: str) -> dict[str, Any]:
    video_path = Path(video_file)
    if not video_path.exists():
        return {"status": "blocked", "reason": f"Video file not found: {video_path}"}
    upload = douyin_upload_video(video_path)
    if upload["status"] != "ready":
        return upload
    video_id = str(upload.get("videoId") or "")
    if not video_id:
        return {"status": "error", "reason": "Douyin upload did not return video_id."}
    create = douyin_create_video(video_id, text)
    if create["status"] != "ready":
        return create
    return {
        "status": "submitted_for_review",
        "publishStatus": "platform_review_pending",
        "contentId": str(create.get("itemId") or video_id),
        "publishedUrl": "",
        "evidence": [str(create.get("shareId") or create.get("itemId") or video_id)],
    }


def douyin_upload_video(video_path: Path) -> dict[str, Any]:
    boundary = "===============%s==" % uuid.uuid4().hex
    media_type = mimetypes.guess_type(str(video_path))[0] or "video/mp4"
    body = build_form_multipart_body(boundary, "video", video_path, media_type)
    return douyin_api(
        "POST",
        "/api/douyin/v1/video/upload_video/",
        body,
        f"multipart/form-data; boundary={boundary}",
        expected_id_keys=("video_id",),
    )


def douyin_create_video(video_id: str, text: str) -> dict[str, Any]:
    body = json.dumps({"video_id": video_id, "text": text}, ensure_ascii=False).encode("utf-8")
    return douyin_api(
        "POST",
        "/api/douyin/v1/video/create_video/",
        body,
        "application/json",
        expected_id_keys=("item_id", "share_id"),
    )


def douyin_api(
    method: str,
    path: str,
    body: bytes,
    content_type: str,
    expected_id_keys: tuple[str, ...],
) -> dict[str, Any]:
    url = "https://open.douyin.com" + path + "?" + urllib.parse.urlencode({"open_id": douyin_open_id()})
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "access-token": douyin_token(),
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "User-Agent": "ViralProductPromotionSkill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "httpStatus": exc.code, "reason": message[:500]}
    except Exception as exc:  # noqa: BLE001 - CLI reports connector errors compactly.
        return {"status": "error", "reason": str(exc)}

    return douyin_result_from_payload(payload, response.status, expected_id_keys)


def douyin_result_from_payload(payload: Any, http_status: int, expected_id_keys: tuple[str, ...]) -> dict[str, Any]:
    payload_obj = payload if isinstance(payload, dict) else {}
    data = payload_obj.get("data")
    data = data if isinstance(data, dict) else {}
    error_code = data.get("error_code", payload_obj.get("error_code"))
    if error_code not in (None, 0, "0"):
        description = data.get("description") or payload_obj.get("description") or payload_obj.get("message") or "Douyin API returned an error."
        return {"status": "error", "httpStatus": http_status, "reason": str(description)[:500]}
    result: dict[str, Any] = {"status": "ready", "httpStatus": http_status}
    for key in expected_id_keys:
        value = nested_value(data, key) or nested_value(payload_obj, key)
        if value:
            if key == "video_id":
                result["videoId"] = value
            elif key == "item_id":
                result["itemId"] = value
            elif key == "share_id":
                result["shareId"] = value
    return result


def nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if value.get(key):
            return value[key]
        for child in value.values():
            found = nested_value(child, key)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = nested_value(child, key)
            if found:
                return found
    return ""


def build_form_multipart_body(boundary: str, field_name: str, file_path: Path, media_type: str) -> bytes:
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'
        f"Content-Type: {media_type}\r\n\r\n"
    ).encode("utf-8")
    closing = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return header + file_path.read_bytes() + closing


def validate_write_gate(args: argparse.Namespace, token_status: str, credential_name: str) -> dict[str, Any] | None:
    if not args.execute:
        return {
            "status": "dry_run",
            "reason": "No write performed. Add --execute with explicit approval after reviewing the request.",
        }
    if token_status != "present":
        return {
            "status": "blocked",
            "reason": f"Execution requires {credential_name} in the environment.",
        }
    gate = publish_environment_gate()
    if not gate["publishApproved"]:
        return {
            "status": "blocked",
            "reason": "Execution requires I_APPROVE_PUBLISH=true in the environment.",
            "missing": ["I_APPROVE_PUBLISH=true"],
        }
    if gate["dryRun"]:
        return {
            "status": "blocked",
            "reason": "Execution requires PUBLISH_DRY_RUN=false in the environment.",
            "missing": ["PUBLISH_DRY_RUN=false"],
        }
    if gate["manualApprovalRequired"] and not explicit_manual_approval(args):
        return {
            "status": "blocked",
            "reason": f"Execution requires explicit manual approval via --approval {APPROVAL_PHRASE} or PUBLISH_APPROVAL_CODE={APPROVAL_PHRASE}.",
            "missing": ["explicit manual approval"],
        }
    return None


def publish_environment_gate() -> dict[str, Any]:
    return {
        "publishApproved": env_bool("I_APPROVE_PUBLISH", False),
        "dryRun": env_bool("PUBLISH_DRY_RUN", True),
        "manualApprovalRequired": env_bool("REQUIRE_MANUAL_APPROVAL", True),
        "approvalCodeProvided": bool(os.environ.get("PUBLISH_APPROVAL_CODE")),
    }


def explicit_manual_approval(args: argparse.Namespace) -> bool:
    return args.approval == APPROVAL_PHRASE or os.environ.get("PUBLISH_APPROVAL_CODE") == APPROVAL_PHRASE


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def blocked(execution: dict[str, Any], code: str, reason: str) -> dict[str, Any]:
    return {**execution, "status": "blocked", "code": code, "reason": reason}


def read_text_argument(value: str, file_value: str | None, label: str) -> str:
    text = read_optional_text_argument(value, file_value)
    if not text:
        raise SystemExit(f"Provide {label}.")
    return text


def read_optional_text_argument(value: str, file_value: str | None) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return value or ""


def write_result(out_dir: str, result: dict[str, Any]) -> None:
    report_dir = Path(out_dir) / "reports/promotion-manager/publish-results"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "publish-execution.json").write_text(json.dumps(sanitize_result(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report_dir / "publish-execution.md").write_text(render_markdown(result) + "\n", encoding="utf-8")


def write_audit_log(out_dir: str, result: dict[str, Any]) -> None:
    report_dir = Path(out_dir) / "reports/promotion-manager/publish-results"
    report_dir.mkdir(parents=True, exist_ok=True)
    audit = {
        "time": utc_now(),
        "platform": result.get("platform"),
        "status": result.get("status"),
        "mode": result.get("mode"),
        "contentId": result.get("contentId", ""),
        "url": result.get("publishedUrl", ""),
        "error": result.get("reason") or result.get("error") or "",
    }
    with (report_dir / "publish-audit-log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit, ensure_ascii=False) + "\n")


def sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
    if "data" in result:
        result = {key: value for key, value in result.items() if key != "data"}
    return result


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Publish Execution",
        "",
        f"- Platform: {result.get('platform')}",
        f"- Status: `{result.get('status')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Official API: {result.get('officialApi', 'n/a')}",
        f"- Credential status: {result.get('credentialStatus', 'n/a')}",
        f"- Published URL: {result.get('publishedUrl', '') or 'not published'}",
        "",
        "## Preview",
    ]
    for key, value in (result.get("publishPreview") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Request",
    ])
    for key, value in (result.get("request") or {}).items():
        lines.append(f"- {key}: {value}")
    if result.get("reason"):
        lines.extend(["", "## Reason", "", result["reason"]])
    lines.extend(["", "## Guardrails"])
    lines.extend([f"- {item}" for item in result.get("guardrails", [])])
    return "\n".join(lines)


def github_token() -> str:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def youtube_token() -> str:
    return first_env(YOUTUBE_ACCESS_TOKEN_ENVS)


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


def douyin_token() -> str:
    return os.environ.get("DOUYIN_ACCESS_TOKEN") or ""


def douyin_open_id() -> str:
    return os.environ.get("DOUYIN_OPEN_ID") or ""


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def github_repo_from_env() -> str:
    if os.environ.get("GITHUB_OWNER") and os.environ.get("GITHUB_REPO"):
        return f"{os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}"
    return ""


def github_should_create_pr(args: argparse.Namespace) -> bool:
    return args.github_action == "pull_request" or env_bool("GITHUB_CREATE_PR", False)


def github_target_branch(args: argparse.Namespace) -> str:
    if args.pr_branch:
        return args.pr_branch
    prefix = args.pr_branch_prefix or "auto-publish"
    return f"{prefix}/{TODAY}-{uuid.uuid4().hex[:8]}"


def summarize_text(value: str, limit: int = 180) -> str:
    clean = " ".join((value or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def github_publish_preview(args: argparse.Namespace) -> dict[str, Any]:
    content = read_optional_text_argument(args.content, args.content_file)
    body = read_optional_text_argument(args.body, args.body_file)
    expected_account = os.environ.get("GITHUB_OWNER") or (args.github_repo.split("/", 1)[0] if "/" in args.github_repo else args.github_repo)
    return {
        "platform": "github",
        "title": args.pr_title or args.title or args.commit_message,
        "bodySummary": summarize_text(content or body),
        "filePath": args.content_file or args.body_file or args.path or "",
        "privacyStatus": "repository_visibility",
        "expectedAccount": expected_account,
    }


def youtube_publish_preview(args: argparse.Namespace) -> dict[str, Any]:
    description = read_optional_text_argument(args.description, args.description_file)
    return {
        "platform": "youtube",
        "title": args.title,
        "bodySummary": summarize_text(description),
        "filePath": args.video_file or "",
        "privacyStatus": args.privacy_status,
        "expectedAccount": os.environ.get("YOUTUBE_CHANNEL_ID") or os.environ.get("YOUTUBE_ACCOUNT") or "oauth_authorized_channel",
    }


def douyin_publish_preview(video_file: str, text: str) -> dict[str, Any]:
    return {
        "platform": "douyin",
        "title": summarize_text(text, 80),
        "bodySummary": summarize_text(text),
        "filePath": video_file,
        "privacyStatus": "platform_default_review_required",
        "expectedAccount": os.environ.get("DOUYIN_OPEN_ID") or "oauth_authorized_open_id",
    }


def print_preview(result: dict[str, Any]) -> None:
    preview = result.get("publishPreview") or {}
    if not preview:
        return
    print("Publish preview:")
    for key in ("platform", "title", "bodySummary", "filePath", "privacyStatus", "expectedAccount"):
        print(f"- {key}: {preview.get(key, '')}")


if __name__ == "__main__":
    main()
