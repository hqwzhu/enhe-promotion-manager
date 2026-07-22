#!/usr/bin/env python3
"""Public distribution identity, file boundaries, and safety checks."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import zipfile
from pathlib import Path


VERSION = "0.5.4"
PUBLISHED_STORE_VERSION = "0.5.3"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_ZIP_CREATE_SYSTEM = 3
FIXED_ZIP_EXTERNAL_ATTR = (stat.S_IFREG | 0o644) << 16
FIXED_ZIP_COMPRESSION = zipfile.ZIP_DEFLATED
FIXED_ZIP_COMPRESSLEVEL = 9
STORE_ITEM_ID = "dloklkbnmoigemnfigbkibogmgbieppl"
STORE_LISTING_URL = (
    "https://chromewebstore.google.com/detail/enhe-promotion-manager/"
    f"{STORE_ITEM_ID}"
)
PUBLIC_REPOSITORY = "hqwzhu/enhe-promotion-manager"
PRODUCT_EN = "ENHE Product Promo Maker"
PRODUCT_ZH = "ENHE 产品推广素材生成器"
PRODUCT_PROMISE_EN = "Turn product pages into promotional copy, video scripts, and publishing assets."
PRODUCT_PROMISE_ZH = "把产品网页变成推广文案、视频脚本和发布素材。"

NON_PAYMENT_COMMANDS = (
    "automation_scheduler.py",
    "browser_publish_session.py",
    "final_capability_readiness.py",
    "launch_unlock_pack.py",
    "performance_monitor.py",
    "promotion_manager.py",
    "real_evidence_inbox.py",
    "real_evidence_inbox_setup.py",
    "skill_entry.py",
    "viral_evidence_inbox.py",
    "viral_evidence_inbox_setup.py",
)

_SKILL_STANDALONES = ("SKILL.md", "LICENSE", "requirements-youtube.txt")
_DISTRIBUTION_ONLY_SCRIPTS = {
    "build_public_distribution.py",
    "distribution_contract.py",
    "test_public_distribution.py",
}
_SKILL_FORBIDDEN_PARTS = {
    ".venv",
    "backend",
    "browser-extension",
    "dependencies",
    "deploy",
    "node_modules",
    "promotion-output",
}
_MAX_TEXT_FILE_SIZE = 2_000_000
_SCRIPT_NAME_PATTERN = r"[A-Za-z0-9_.-]+\.py"
_SCRIPT_REFERENCE = re.compile(rf"\bscripts[\\/]+({_SCRIPT_NAME_PATTERN})\b", re.IGNORECASE)
_SUPPORTED_SCRIPT_COMMAND = re.compile(
    rf"(?<![A-Za-z0-9_.-])(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?\s+"
    rf"scripts[\\/]+({_SCRIPT_NAME_PATTERN})\b",
    re.IGNORECASE,
)
_SECRET_PATTERNS = (
    (
        "github_token",
        re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{36,})\b"),
    ),
    ("firecrawl_key", re.compile(r"\bfc-[A-Za-z0-9_-]{20,}\b")),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
    ),
    ("live_license", re.compile(r"\bpm_live_[A-Za-z0-9]{20,}\b")),
)


def deterministic_zip_info(name: str) -> zipfile.ZipInfo:
    """Return normalized metadata for a regular file in a release ZIP."""
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIMESTAMP)
    info.create_system = FIXED_ZIP_CREATE_SYSTEM
    info.external_attr = FIXED_ZIP_EXTERNAL_ATTR
    info.compress_type = FIXED_ZIP_COMPRESSION
    info.extra = b""
    info.comment = b""
    return info


def nondeterministic_zip_members(archive: zipfile.ZipFile) -> list[str]:
    """Return archive/member labels whose ZIP metadata violates the release contract."""
    infos = archive.infolist()
    drift: list[str] = []
    if archive.comment != b"":
        drift.append("<archive-comment>")
    if [info.filename for info in infos] != sorted(info.filename for info in infos):
        drift.append("<member-order>")
    for info in infos:
        if (
            info.date_time != FIXED_ZIP_TIMESTAMP
            or info.create_system != FIXED_ZIP_CREATE_SYSTEM
            or info.external_attr != FIXED_ZIP_EXTERNAL_ATTR
            or info.compress_type != FIXED_ZIP_COMPRESSION
            or info.extra != b""
            or info.comment != b""
        ):
            drift.append(info.filename)
    return list(dict.fromkeys(drift))


def extension_command_refs(text: str) -> list[str]:
    """Return unique Python script names referenced by extension commands."""
    references = list(_SCRIPT_REFERENCE.finditer(text))
    supported = {match.start(1): match.group(1) for match in _SUPPORTED_SCRIPT_COMMAND.finditer(text)}
    names: set[str] = set()
    for reference in references:
        if reference.start(1) not in supported:
            raise ValueError(f"unsupported interpreter for {reference.group(1)}")
        names.add(reference.group(1))
    return sorted(names)


def _is_env_part(part: str) -> bool:
    lowered = part.lower()
    return lowered == ".env" or lowered.startswith(".env.")


def _skill_path_allowed(relative: Path) -> bool:
    lowered_parts = {part.lower() for part in relative.parts}
    return not (
        lowered_parts.intersection(_SKILL_FORBIDDEN_PARTS)
        or any(_is_env_part(part) for part in relative.parts)
    )


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _resolved_root(root: Path) -> Path:
    try:
        if _is_link_or_reparse(root):
            raise ValueError(f"unsafe link or reparse point at root: {root}")
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"unreadable distribution root: {root}") from exc
    if not root.is_dir():
        raise ValueError(f"distribution root is not a directory: {root}")
    return resolved


def _source_issue(root_resolved: Path, path: Path) -> str | None:
    try:
        if _is_link_or_reparse(path):
            return "unsafe_link"
        resolved = path.resolve(strict=True)
    except OSError:
        return "unreadable_file"
    if not resolved.is_relative_to(root_resolved):
        return "unsafe_link"
    return None


def _relative_name(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _walk_tree(root: Path, start: Path | None = None) -> tuple[list[Path], list[Path], list[dict[str, str]]]:
    root_resolved = _resolved_root(root)
    start = root if start is None else start
    try:
        start.lstat()
    except FileNotFoundError:
        return [], [], []
    except OSError:
        return [], [], [{"path": _relative_name(root, start), "rule": "unreadable_file"}]

    start_issue = _source_issue(root_resolved, start)
    if start_issue:
        return [], [], [{"path": _relative_name(root, start), "rule": start_issue}]

    files: list[Path] = []
    directories: list[Path] = []
    issues: list[dict[str, str]] = []

    def record_walk_error(error: OSError) -> None:
        failed = Path(error.filename) if error.filename else start
        issues.append({"path": _relative_name(root, failed), "rule": "unreadable_file"})

    for current, directory_names, file_names in os.walk(
        start,
        topdown=True,
        onerror=record_walk_error,
        followlinks=False,
    ):
        current_path = Path(current)
        safe_directories: list[str] = []
        for name in sorted(directory_names):
            path = current_path / name
            issue = _source_issue(root_resolved, path)
            if issue:
                issues.append({"path": _relative_name(root, path), "rule": issue})
            else:
                directories.append(path)
                safe_directories.append(name)
        directory_names[:] = safe_directories

        for name in sorted(file_names):
            path = current_path / name
            issue = _source_issue(root_resolved, path)
            if issue:
                issues.append({"path": _relative_name(root, path), "rule": issue})
            else:
                files.append(path)

    return files, directories, issues


def _strict_files(root: Path, start: Path | None = None) -> list[Path]:
    files, _, issues = _walk_tree(root, start)
    if issues:
        issue = issues[0]
        raise ValueError(
            f"unsafe link, reparse point, unreadable path, or path outside root: {issue['path']}"
        )
    return files


def skill_files(root: Path) -> list[Path]:
    """List source files allowed in the public Skill package."""
    root_resolved = _resolved_root(root)
    files: list[Path] = []
    for name in _SKILL_STANDALONES:
        path = root / name
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ValueError(f"unreadable public source: {name}") from exc
        issue = _source_issue(root_resolved, path)
        if issue:
            raise ValueError(f"unsafe link, reparse point, or path outside root: {name}")
        if path.is_file():
            files.append(Path(name))

    for path in _strict_files(root, root / "references"):
        relative = path.relative_to(root)
        if path.suffix == ".md" and _skill_path_allowed(relative):
            files.append(relative)

    script_paths = _strict_files(root, root / "scripts")
    for path in script_paths:
        relative = path.relative_to(root)
        if (
            path.suffix == ".py"
            and path.name not in _DISTRIBUTION_ONLY_SCRIPTS
            and _skill_path_allowed(relative)
        ):
            files.append(relative)

    fixture_directory = Path("scripts/fixtures/mediacrawler")
    for path in script_paths:
        relative = path.relative_to(root)
        if (
            relative.parent == fixture_directory
            and path.suffix == ".jsonl"
            and _skill_path_allowed(relative)
        ):
            files.append(relative)

    return sorted(set(files), key=lambda item: item.as_posix())


def extension_files(root: Path) -> list[Path]:
    """List visible browser extension files relative to its source directory."""
    extension = root / "browser-extension"
    return sorted(
        (
            path.relative_to(extension)
            for path in _strict_files(root, extension)
            if not any(part.startswith(".") for part in path.relative_to(extension).parts)
        ),
        key=lambda item: item.as_posix(),
    )


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(root: Path) -> str:
    """Return a deterministic digest of relative file paths and bytes."""
    digest = hashlib.sha256()
    paths = sorted(
        _strict_files(root),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def _is_forbidden_path_part(part: str) -> bool:
    lowered = part.lower()
    if _is_env_part(lowered):
        return True
    if lowered in {
        ".venv",
        "node_modules",
        "promotion-output",
        "cookies.json",
        "__pycache__",
    }:
        return True

    normalized = lowered.strip(".").replace("_", "-").replace(" ", "-")
    return (
        normalized.startswith("chrome-profile")
        or normalized.startswith("chrome-user-data")
        or normalized in {"user-data", "user-data-dir"}
        or ("mediacrawler" in normalized and "backup" in normalized)
    )


def scan_forbidden(root: Path) -> list[dict[str, str]]:
    """Find private paths and secret patterns without returning secret values."""
    files, directories, violations = _walk_tree(root)
    for path in sorted(directories + files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if any(_is_forbidden_path_part(part) for part in relative.parts):
            violations.append({"path": relative.as_posix(), "rule": "forbidden_path"})
            continue
        if path in directories:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            violations.append({"path": relative.as_posix(), "rule": "unreadable_file"})
            continue
        if size > _MAX_TEXT_FILE_SIZE:
            continue
        try:
            content = path.read_bytes()
        except OSError:
            violations.append({"path": relative.as_posix(), "rule": "unreadable_file"})
            continue
        text = content.decode("utf-8", errors="replace")
        for rule, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                violations.append({"path": relative.as_posix(), "rule": rule})
    return violations
