#!/usr/bin/env python3
"""Pinned, bounded subprocess boundary for a local MediaCrawler checkout."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import mediacrawler_contract


UPSTREAM_REPOSITORY = "https://github.com/NanmiCoder/MediaCrawler.git"
UPSTREAM_COMMIT = "3bde9e2015f912f2e19ee63b615a0f48b9a90315"
PLATFORM_FLAGS = {"xiaohongshu": "xhs", "douyin": "dy", "zhihu": "zhihu"}
MODES = {"search", "detail", "creator"}
MAX_CONTENTS = 20
MAX_COMMENTS = 30
MAX_TIMEOUT_SECONDS = 3600
DEFAULT_TIMEOUT_SECONDS = 900
RAW_WARNING = "Raw MediaCrawler output may contain sensitive tokens or identifiers. Keep it only for local debugging and never upload it."
BOOTSTRAP_PATH = Path(__file__).with_name("mediacrawler_bootstrap.py")


@dataclass(frozen=True)
class SidecarInstall:
    root: Path

    @property
    def checkout(self) -> Path:
        return self.root / "checkout"

    @property
    def python_executable(self) -> Path:
        if os.name == "nt":
            return self.checkout / ".venv" / "Scripts" / "python.exe"
        return self.checkout / ".venv" / "bin" / "python"

    @property
    def manifest_path(self) -> Path:
        return self.root / "install-manifest.json"

    @property
    def identity_salt_path(self) -> Path:
        return self.root / "identity.salt"


@dataclass(frozen=True)
class CollectRequest:
    platform: str
    mode: str
    query: str = ""
    target: str = ""
    max_contents: int = MAX_CONTENTS
    max_comments: int = MAX_COMMENTS
    include_sub_comments: bool = False
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    detail_context_query: str = ""

    def __post_init__(self) -> None:
        canonical = mediacrawler_contract.canonical_platform(self.platform)
        object.__setattr__(self, "platform", canonical)
        if self.mode not in MODES:
            raise ValueError(f"Unsupported MediaCrawler mode: {self.mode}")
        if not 1 <= self.max_contents <= MAX_CONTENTS:
            raise ValueError(f"max_contents must be between 1 and {MAX_CONTENTS}")
        if not 0 <= self.max_comments <= MAX_COMMENTS:
            raise ValueError(f"max_comments must be between 0 and {MAX_COMMENTS}")
        if not 1 <= self.timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ValueError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")
        if self.mode == "search" and not self.query.strip():
            raise ValueError("query is required for search mode")
        if self.mode in {"detail", "creator"} and not self.target.strip():
            raise ValueError(f"target is required for {self.mode} mode")
        if canonical == "xiaohongshu" and self.mode == "detail":
            object.__setattr__(self, "target", mediacrawler_contract.sanitize_url(self.target.strip()))


@dataclass
class RunResult:
    status: str
    reason: str = ""
    exit_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    retry_count: int = 0
    keep_raw: bool = False
    warning: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


Executor = Callable[[list[str], Path, int], subprocess.CompletedProcess[str]]
RawConsumer = Callable[[Path], dict[str, Any]]


def default_install() -> SidecarInstall:
    local_data = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return SidecarInstall(local_data / "ENHE" / "promotion-manager" / "mediacrawler")


def build_mediacrawler_command(install: SidecarInstall, request: CollectRequest, raw_dir: Path) -> list[str]:
    command = [
        str(install.python_executable),
        str(BOOTSTRAP_PATH),
        "--checkout",
        str(install.checkout),
        "--requested-max-contents",
        str(request.max_contents),
    ]
    if request.platform == "xiaohongshu" and request.mode == "detail" and request.detail_context_query.strip():
        command.extend(
            [
                "--xhs-detail-query",
                request.detail_context_query.strip(),
                "--xhs-detail-target",
                xiaohongshu_content_id(request.target),
            ]
        )
    command.extend(
        [
            "--",
            "--platform",
            PLATFORM_FLAGS[request.platform],
            "--lt",
            "qrcode",
            "--type",
            request.mode,
            "--headless",
            "false",
            "--save_data_option",
            "jsonl",
            "--save_data_path",
            str(raw_dir.resolve()),
            "--get_comment",
            "true" if request.max_comments else "false",
            "--get_sub_comment",
            "true" if request.include_sub_comments else "false",
            "--max_comments_count_singlenotes",
            str(request.max_comments),
            "--crawler_max_notes_count",
            str(request.max_contents),
            "--max_concurrency_num",
            "1",
            "--enable_ip_proxy",
            "false",
        ]
    )
    if request.mode == "search":
        command.extend(["--keywords", request.query.strip()])
    elif request.mode == "detail":
        command.extend(["--specified_id", request.target.strip()])
    else:
        command.extend(["--creator_id", request.target.strip()])
    return command


def check_setup(
    install: SidecarInstall | None = None,
    *,
    find_executable: Callable[[str], str | None] = shutil.which,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    selected = install or default_install()
    checkout_present = selected.checkout.is_dir()
    main_present = (selected.checkout / "main.py").is_file()
    python_present = selected.python_executable.is_file()
    manifest_present = selected.manifest_path.is_file()
    identity_salt_present = selected.identity_salt_path.is_file() and selected.identity_salt_path.stat().st_size >= 32
    bootstrap_present = BOOTSTRAP_PATH.is_file()
    git_path = find_executable("git")
    uv_path = find_executable("uv")
    chrome_path = find_chrome(find_executable)
    actual_commit = ""
    if checkout_present and git_path:
        completed = command_runner(
            [git_path, "-C", str(selected.checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            actual_commit = completed.stdout.strip()
    safeguards = pinned_safeguards(selected.checkout) if checkout_present else {}
    ready = all(
        [
            git_path,
            uv_path,
            chrome_path,
            main_present,
            python_present,
            manifest_present,
            identity_salt_present,
            bootstrap_present,
            actual_commit == UPSTREAM_COMMIT,
            safeguards.get("cdpMode"),
            safeguards.get("connectExisting"),
            safeguards.get("mediaDownloadsDisabled"),
            safeguards.get("sleepSecondsAtLeastTwo"),
        ]
    )
    return {
        "status": "ready" if ready else "provider_unavailable",
        "writesPerformed": False,
        "root": str(selected.root),
        "repository": UPSTREAM_REPOSITORY,
        "expectedCommit": UPSTREAM_COMMIT,
        "actualCommit": actual_commit,
        "checks": {
            "git": bool(git_path),
            "uv": bool(uv_path),
            "chrome": bool(chrome_path),
            "checkout": checkout_present,
            "main": main_present,
            "python": python_present,
            "manifest": manifest_present,
            "identitySalt": identity_salt_present,
            "bootstrap": bootstrap_present,
            "commit": actual_commit == UPSTREAM_COMMIT,
            **safeguards,
        },
    }


def install_sidecar(
    install: SidecarInstall | None = None,
    *,
    find_executable: Callable[[str], str | None] = shutil.which,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    random_bytes: Callable[[int], bytes] = os.urandom,
) -> dict[str, Any]:
    selected = install or default_install()
    git_path = find_executable("git")
    uv_path = find_executable("uv")
    if not git_path or not uv_path:
        return {
            "status": "provider_unavailable",
            "reason": "git_and_uv_are_required",
            "writesPerformed": False,
            "expectedCommit": UPSTREAM_COMMIT,
        }
    if selected.checkout.exists():
        current = check_setup(selected, find_executable=find_executable, command_runner=command_runner)
        if current["status"] == "ready":
            return current
        return {
            **current,
            "reason": "existing_checkout_requires_explicit_pinned_update",
            "writesPerformed": False,
        }

    selected.root.mkdir(parents=True, exist_ok=True)
    staging = selected.root / f"installing-{uuid.uuid4().hex[:12]}"
    moved_to_checkout = False
    commands = [
        [git_path, "clone", "--no-checkout", UPSTREAM_REPOSITORY, str(staging)],
        [git_path, "-C", str(staging), "checkout", "--detach", UPSTREAM_COMMIT],
        [uv_path, "sync", "--project", str(staging), "--python", "3.11"],
        [git_path, "-C", str(staging), "rev-parse", "HEAD"],
    ]
    try:
        actual_commit = ""
        for command in commands:
            completed = command_runner(command, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                return {
                    "status": "provider_unavailable",
                    "reason": safe_tail(completed.stderr or completed.stdout) or "sidecar_install_command_failed",
                    "writesPerformed": True,
                    "expectedCommit": UPSTREAM_COMMIT,
                }
            if command[-2:] == ["rev-parse", "HEAD"]:
                actual_commit = completed.stdout.strip()
        if actual_commit != UPSTREAM_COMMIT:
            return {
                "status": "provider_unavailable",
                "reason": "upstream_commit_verification_failed",
                "writesPerformed": True,
                "expectedCommit": UPSTREAM_COMMIT,
                "actualCommit": actual_commit,
            }
        safeguards = pinned_safeguards(staging)
        if not all(safeguards.values()):
            return {
                "status": "provider_unavailable",
                "reason": "pinned_safety_defaults_verification_failed",
                "writesPerformed": True,
                "expectedCommit": UPSTREAM_COMMIT,
                "checks": safeguards,
            }
        staging_python = staging / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not staging_python.is_file():
            return {
                "status": "provider_unavailable",
                "reason": "isolated_python_environment_missing",
                "writesPerformed": True,
                "expectedCommit": UPSTREAM_COMMIT,
            }
        shutil.move(str(staging), str(selected.checkout))
        moved_to_checkout = True
        if not selected.identity_salt_path.exists():
            selected.identity_salt_path.write_bytes(random_bytes(32))
        manifest = {
            "schemaVersion": 1,
            "repository": UPSTREAM_REPOSITORY,
            "upstreamCommit": UPSTREAM_COMMIT,
            "checkout": str(selected.checkout),
            "installedAt": utc_now(),
            "commercialAuthorizationConfirmedByOwner": True,
        }
        selected.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = check_setup(selected, find_executable=find_executable, command_runner=command_runner)
        report["writesPerformed"] = True
        if report["status"] != "ready":
            selected.manifest_path.unlink(missing_ok=True)
            if moved_to_checkout:
                shutil.rmtree(selected.checkout, ignore_errors=True)
            return {**report, "reason": "post_install_check_failed"}
        return report
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def find_chrome(find_executable: Callable[[str], str | None] = shutil.which) -> str | None:
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe", "chromium", "chromium.exe"):
        found = find_executable(name)
        if found:
            return found
    if os.name == "nt":
        roots = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")]
        candidates = [
            Path(root) / relative
            for root in roots
            if root
            for relative in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe")
        ]
        for path in candidates:
            if path.is_file():
                return str(path)
    return None


def pinned_safeguards(checkout: Path) -> dict[str, bool]:
    config_path = checkout / "config" / "base_config.py"
    if not config_path.is_file():
        return {
            "cdpMode": False,
            "connectExisting": False,
            "mediaDownloadsDisabled": False,
            "sleepSecondsAtLeastTwo": False,
        }
    text = config_path.read_text(encoding="utf-8", errors="replace")
    sleep_match = re.search(r"(?m)^CRAWLER_MAX_SLEEP_SEC\s*=\s*(\d+(?:\.\d+)?)", text)
    return {
        "cdpMode": bool(re.search(r"(?m)^ENABLE_CDP_MODE\s*=\s*True\s*$", text)),
        "connectExisting": bool(re.search(r"(?m)^CDP_CONNECT_EXISTING\s*=\s*True\s*$", text)),
        "mediaDownloadsDisabled": bool(re.search(r"(?m)^ENABLE_GET_MEIDAS\s*=\s*False\s*$", text)),
        "sleepSecondsAtLeastTwo": bool(sleep_match and float(sleep_match.group(1)) >= 2),
    }


def run_sidecar(
    install: SidecarInstall,
    request: CollectRequest,
    run_dir: Path,
    *,
    executor: Executor | None = None,
    raw_consumer: RawConsumer | None = None,
    keep_raw: bool = False,
) -> RunResult:
    execute = executor or execute_process
    raw_dir = run_dir / "raw"
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    acquired = False
    retry_count = 0
    try:
        acquire_lock(install)
        acquired = True
        command = build_mediacrawler_command(install, request, raw_dir)
        try:
            completed = execute(command, install.checkout, request.timeout_seconds)
        except subprocess.TimeoutExpired:
            return RunResult(status="error", reason="timeout", keep_raw=keep_raw, warning=RAW_WARNING if keep_raw else "")
        except KeyboardInterrupt:
            return RunResult(status="cancelled", reason="user_cancelled", keep_raw=keep_raw, warning=RAW_WARNING if keep_raw else "")

        if completed.returncode != 0 and is_transient_network_error(completed.stderr or completed.stdout):
            retry_count = 1
            try:
                completed = execute(command, install.checkout, request.timeout_seconds)
            except subprocess.TimeoutExpired:
                return RunResult(status="error", reason="timeout", retry_count=retry_count, keep_raw=keep_raw, warning=RAW_WARNING if keep_raw else "")
            except KeyboardInterrupt:
                return RunResult(
                    status="cancelled",
                    reason="user_cancelled",
                    retry_count=retry_count,
                    keep_raw=keep_raw,
                    warning=RAW_WARNING if keep_raw else "",
                )

        stdout_tail = safe_tail(completed.stdout)
        stderr_tail = safe_tail(completed.stderr)
        if completed.returncode != 0:
            status = classify_failure(f"{completed.stdout}\n{completed.stderr}")
            return RunResult(
                status=status,
                reason=status,
                exit_code=completed.returncode,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                retry_count=retry_count,
                keep_raw=keep_raw,
                warning=RAW_WARNING if keep_raw else "",
            )

        row_count = jsonl_row_count(raw_dir)
        if not row_count:
            return RunResult(
                status="no_results",
                exit_code=completed.returncode,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                retry_count=retry_count,
                keep_raw=keep_raw,
                warning=RAW_WARNING if keep_raw else "",
            )
        payload: dict[str, Any] = {}
        if raw_consumer:
            try:
                payload = raw_consumer(raw_dir)
            except Exception as exc:  # noqa: BLE001 - caller receives a sanitized boundary error.
                return RunResult(
                    status="normalization_error",
                    reason=safe_tail(str(exc)),
                    exit_code=completed.returncode,
                    stdout_tail=stdout_tail,
                    stderr_tail=stderr_tail,
                    retry_count=retry_count,
                    keep_raw=keep_raw,
                    warning=RAW_WARNING if keep_raw else "",
                )
        status = "partial_ready" if payload.get("status") == "partial_ready" else "ready"
        return RunResult(
            status=status,
            exit_code=completed.returncode,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            retry_count=retry_count,
            keep_raw=keep_raw,
            warning=RAW_WARNING if keep_raw else "",
            payload=payload,
        )
    finally:
        if not keep_raw and raw_dir.exists():
            shutil.rmtree(raw_dir)
        if acquired:
            release_lock(install)


def execute_process(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )


def xiaohongshu_content_id(target: str) -> str:
    value = mediacrawler_contract.sanitize_url(str(target or "").strip())
    if not value.lower().startswith(("http://", "https://")):
        return value
    parts = [part for part in urllib.parse.urlsplit(value).path.split("/") if part]
    if "explore" in parts:
        index = parts.index("explore")
        if index + 1 < len(parts):
            return parts[index + 1]
    return parts[-1] if parts else ""


def lock_path(install: SidecarInstall) -> Path:
    return install.root / "run.lock"


def acquire_lock(install: SidecarInstall) -> None:
    path = lock_path(install)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("another_mediacrawler_task_is_running") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "createdAt": utc_now()}) + "\n")


def release_lock(install: SidecarInstall) -> None:
    lock_path(install).unlink(missing_ok=True)


def classify_failure(value: str) -> str:
    text = str(value or "").lower()
    if any(marker in text for marker in ("captcha", "slider", "verification required", "验证码", "滑块", "人机验证")):
        return "manual_verification_required"
    if any(marker in text for marker in ("risk control", "account risk", "blocked", "forbidden", "风控", "访问受限")):
        return "blocked_by_platform"
    if any(marker in text for marker in ("login", "qr code", "qrcode", "扫码", "登录")):
        return "waiting_login"
    return "error"


def is_transient_network_error(value: str) -> bool:
    text = str(value or "").lower()
    return any(marker in text for marker in ("connection reset", "temporarily unavailable", "temporary network", "remote disconnected", "network timeout"))


def jsonl_row_count(raw_dir: Path) -> int:
    count = 0
    for path in raw_dir.rglob("*.jsonl"):
        try:
            with path.open("r", encoding="utf-8-sig") as stream:
                count += sum(1 for line in stream if line.strip())
        except OSError:
            continue
    return count


def safe_tail(value: str | None, limit: int = 1200) -> str:
    text = str(value or "")
    text = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer REDACTED", text)
    sensitive_key = r"authorization|cookie|xsec_token|mstoken|verifyfp|signature|access_token|sign"
    text = re.sub(
        rf"(?i)(?P<key_quote>[\"']?)(?P<key>{sensitive_key})(?P=key_quote)(?P<separator>\s*[:=]\s*)(?P<value_quote>[\"'])(?P<value>.*?)(?P=value_quote)",
        lambda match: (
            f"{match.group('key_quote')}{match.group('key')}{match.group('key_quote')}"
            f"{match.group('separator')}{match.group('value_quote')}REDACTED{match.group('value_quote')}"
        ),
        text,
    )
    text = re.sub(
        rf"(?i)({sensitive_key})\s*[:=]\s*[^\s,;&}}\]]+",
        r"\1=REDACTED",
        text,
    )
    return text[-limit:]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
