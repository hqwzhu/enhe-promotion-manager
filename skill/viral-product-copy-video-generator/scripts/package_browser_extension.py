#!/usr/bin/env python3
"""Validate and package the ENHE Product Promo Maker browser extension."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import distribution_contract as contract


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_DIR = ROOT / "browser-extension"
TODAY = date.today().isoformat()
REQUIRED_FILES = [
    "manifest.json",
    "popup.html",
    "popup.css",
    "popup.js",
    "billing-contract.json",
    "icons/icon16.png",
    "icons/icon48.png",
    "icons/icon128.png",
]
ALLOWED_PERMISSIONS = {"activeTab", "storage", "clipboardWrite"}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(out_dir)
    write_report(out_dir, report)
    if report["status"] != "ready":
        raise SystemExit(f"browser extension package is not ready: {', '.join(report['missing'])}")
    print(f"Browser extension package written to: {Path(report['package']).resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Chrome/Edge store submission zip for browser-extension/.")
    parser.add_argument(
        "--out-dir",
        default=default_out_dir(),
        help="Output directory for the zip and package report.",
    )
    return parser.parse_args()


def default_out_dir() -> str:
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))
    version = str(manifest.get("version") or "dev").strip() or "dev"
    return str(Path(".") / "dist" / f"v{version}")


def build_report(out_dir: Path) -> dict[str, Any]:
    manifest_path = EXTENSION_DIR / "manifest.json"
    manifest = read_json(manifest_path)
    missing = [path for path in REQUIRED_FILES if not (EXTENSION_DIR / path).exists()]
    package_path = out_dir / package_name(manifest)
    files = package_files()
    checks = {
        "requiredFiles": not missing,
        "versionMatchesDistributionContract": str(manifest.get("version", "")) == contract.VERSION,
        "manifestV3": manifest.get("manifest_version") == 3,
        "icons": icons_ready(manifest),
        "allowedPermissions": permissions_ready(manifest),
        "hostPermissionsScopedToEnhe": host_permissions_ready(manifest),
        "noRemoteExecutableCode": no_remote_executable_code(files),
        "noUnsafeEval": no_unsafe_eval(manifest, files),
        "packageCreated": False,
        "deterministicArchiveMetadata": False,
    }
    for key, ready in checks.items():
        if key not in {"packageCreated", "deterministicArchiveMetadata"} and not ready:
            missing.append(key)
    status = "ready" if not missing else "blocked"
    if status == "ready":
        write_zip(package_path, files)
        checks["packageCreated"] = package_path.exists()
        if not checks["packageCreated"]:
            status = "blocked"
            missing.append("packageCreated")
        else:
            with zipfile.ZipFile(package_path) as archive:
                checks["deterministicArchiveMetadata"] = not contract.nondeterministic_zip_members(
                    archive
                )
            if not checks["deterministicArchiveMetadata"]:
                status = "blocked"
                missing.append("deterministicArchiveMetadata")
    archive_sha256 = sha256_file(package_path) if checks["packageCreated"] else ""
    return {
        "generatedAt": TODAY,
        "status": status,
        "extensionDir": str(EXTENSION_DIR),
        "package": str(package_path),
        "archiveName": package_path.name,
        "archiveSha256": archive_sha256,
        "version": str(manifest.get("version", "")),
        "name": str(manifest.get("name", "")),
        "checks": checks,
        "files": [path.as_posix() for path in files],
        "missing": sorted(set(missing)),
        "storeSubmission": {
            "chrome": "https://developer.chrome.com/docs/webstore/publish",
            "edge": "https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/publish/publish-extension",
            "privacyPolicyUrl": "https://www.enhe-tech.com.cn/promotion-manager/privacy",
            "supportUrl": "https://www.enhe-tech.com.cn/promotion-manager/support",
        },
        "guardrails": [
            "Package local extension code only; remote services may return data, not executable code.",
            "No platform API keys, payment secrets, cookies, OAuth tokens, or webhook secrets are packaged.",
            "Final platform publishing remains gated by user review and explicit platform approval.",
        ],
    }


def package_name(manifest: dict[str, Any]) -> str:
    version = re.sub(r"[^0-9A-Za-z_.-]+", "-", str(manifest.get("version") or "dev")).strip("-") or "dev"
    return f"enhe-promotion-manager-{version}.zip"


def package_files() -> list[Path]:
    return sorted(
        [
            path.relative_to(EXTENSION_DIR)
            for path in EXTENSION_DIR.rglob("*")
            if path.is_file() and not any(part.startswith(".") for part in path.relative_to(EXTENSION_DIR).parts)
        ],
        key=lambda item: item.as_posix(),
    )


def write_zip(package_path: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(
        package_path,
        "w",
        compression=contract.FIXED_ZIP_COMPRESSION,
        compresslevel=contract.FIXED_ZIP_COMPRESSLEVEL,
    ) as archive:
        archive.comment = b""
        for rel in sorted(files, key=lambda item: item.as_posix()):
            archive.writestr(
                contract.deterministic_zip_info(rel.as_posix()),
                (EXTENSION_DIR / rel).read_bytes(),
                compress_type=contract.FIXED_ZIP_COMPRESSION,
                compresslevel=contract.FIXED_ZIP_COMPRESSLEVEL,
            )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def icons_ready(manifest: dict[str, Any]) -> bool:
    icons = manifest.get("icons") if isinstance(manifest.get("icons"), dict) else {}
    action = manifest.get("action") if isinstance(manifest.get("action"), dict) else {}
    action_icons = action.get("default_icon") if isinstance(action.get("default_icon"), dict) else {}
    for size in ["16", "48", "128"]:
        icon = icons.get(size)
        action_icon = action_icons.get(size)
        if not icon or not action_icon:
            return False
        if not (EXTENSION_DIR / str(icon)).exists() or not (EXTENSION_DIR / str(action_icon)).exists():
            return False
    return True


def permissions_ready(manifest: dict[str, Any]) -> bool:
    permissions = set(manifest.get("permissions") or [])
    return permissions.issubset(ALLOWED_PERMISSIONS)


def host_permissions_ready(manifest: dict[str, Any]) -> bool:
    permissions = [str(item) for item in manifest.get("host_permissions") or []]
    return permissions == ["https://www.enhe-tech.com.cn/*"]


def no_remote_executable_code(files: list[Path]) -> bool:
    html_pattern = re.compile(r"<script[^>]+src=['\"]https?://|<link[^>]+href=['\"]https?://", re.IGNORECASE)
    js_pattern = re.compile(r"import\s*\(\s*['\"]https?://|importScripts\s*\(\s*['\"]https?://", re.IGNORECASE)
    for rel in files:
        if rel.suffix.lower() not in {".html", ".js"}:
            continue
        text = (EXTENSION_DIR / rel).read_text(encoding="utf-8")
        if html_pattern.search(text) or js_pattern.search(text):
            return False
    return True


def no_unsafe_eval(manifest: dict[str, Any], files: list[Path]) -> bool:
    csp = manifest.get("content_security_policy") if isinstance(manifest.get("content_security_policy"), dict) else {}
    if "unsafe-eval" in str(csp.get("extension_pages", "")):
        return False
    for rel in files:
        if rel.suffix.lower() != ".js":
            continue
        text = (EXTENSION_DIR / rel).read_text(encoding="utf-8")
        if re.search(r"\beval\s*\(|new\s+Function\s*\(", text):
            return False
    return True


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    json_path = out_dir / "browser-extension-package-report.json"
    markdown_path = out_dir / "browser-extension-package-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Browser Extension Package Report",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Package: {report['package']}",
        f"- Archive: `{report['archiveName']}`",
        f"- SHA-256: `{report['archiveSha256']}`",
        f"- Version: `{report['version']}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in report["checks"].items())
    if report["missing"]:
        lines.extend(["", "## Missing"])
        lines.extend(f"- {item}" for item in report["missing"])
    lines.extend(["", "## Store Submission"])
    for key, value in report["storeSubmission"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
