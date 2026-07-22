#!/usr/bin/env python3
"""Fail-closed validation for the public distribution repository and archives."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

sys.dont_write_bytecode = True

import distribution_contract as contract


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = tuple(
    f"docs/{locale}/{name}.md"
    for locale in ("zh-CN", "en")
    for name in (
        "features",
        "installation",
        "quick-start",
        "skill-guide",
        "extension-guide",
        "platform-research",
        "publishing-and-review",
        "data-and-privacy",
        "troubleshooting",
        "version-sync",
    )
)
REQUIRED_FILES = (
    "README.md",
    "README.en.md",
    "LICENSE",
    "NOTICE.md",
    "SECURITY.md",
    "CHANGELOG.md",
    ".gitattributes",
    ".gitignore",
    "requirements-test.txt",
    ".github/workflows/tests.yml",
    "release-manifest.json",
    "skill/viral-product-copy-video-generator/SKILL.md",
    "skill/viral-product-copy-video-generator/requirements-youtube.txt",
    "skill/viral-product-copy-video-generator/component-manifest.json",
    "extension/chrome/manifest.json",
    "extension/chrome/component-manifest.json",
    "scripts/build_release.py",
    "scripts/generate_checksums.py",
    "scripts/verify_distribution.py",
    "scripts/distribution_contract.py",
    "tests/test_distribution.py",
) + REQUIRED_DOCS
CLAIM_PATTERNS = (
    (
        "guaranteed viral",
        re.compile(r"\b(?:guarantee(?:d|s|ing)?\s+(?:a\s+)?viral|viral\s+(?:is\s+)?guaranteed)\b", re.IGNORECASE),
    ),
    ("guaranteed hit", re.compile(r"保证爆款")),
    (
        "automatic final publish",
        re.compile(
            r"\b(?:automatic|automatically)\b.{0,40}\b(?:click(?:s|ed|ing)?\s+)?(?:the\s+)?(?:final\s+)?(?:publish(?:ing|ed)?|publication)\b",
            re.IGNORECASE,
        ),
    ),
    ("automatic final publish", re.compile(r"自动点击最终发布")),
    ("bypass captcha", re.compile(r"\bbypass(?:es|ed|ing)?\s+(?:a\s+)?captcha\b", re.IGNORECASE)),
    ("bypass captcha", re.compile(r"绕过验证码")),
)
_ENGLISH_NEGATION = re.compile(
    r"(?:does\s+not|do\s+not|is\s+not|are\s+not|will\s+not|cannot|can't|won't|never|not|without)\s+$",
    re.IGNORECASE,
)
_CHINESE_NEGATION = re.compile(r"(?:不|不会|不能|未|不支持|不允许|不提供)\s*$")
_TEXT_SUFFIXES = {".html", ".js", ".json", ".md", ".txt"}
_GENERATED_COMPONENT_PARTS = {"dist", "__pycache__", ".pytest_cache", "tmp-release-download"}
VERSION = contract.VERSION
EXPECTED_CHECKSUM_PATHS = (
    "release-manifest.json",
    f"dist/v{VERSION}/enhe-product-promo-maker-skill-{VERSION}.zip",
    f"dist/v{VERSION}/enhe-promotion-manager-extension-{VERSION}.zip",
)
EXPECTED_SKILL_ARCHIVE = f"enhe-product-promo-maker-skill-{VERSION}.zip"
EXPECTED_EXTENSION_ARCHIVE = f"enhe-promotion-manager-extension-{VERSION}.zip"
EXPECTED_VALIDATOR_COMMANDS = (
    f"python scripts/build_release.py --validated-extension-zip dist/validated/enhe-promotion-manager-{VERSION}.zip",
    "python scripts/verify_distribution.py",
    "python -m unittest discover -s tests -v",
)
EXPECTED_GITIGNORE_RULES = (".env", ".env.*", "!.env.example")
EXPECTED_GITATTRIBUTES_RULES = ("* text=auto eol=lf", "release-manifest.json -text")
EXPECTED_CI_STEPS = [
    {"name": "Check out repository", "uses": "actions/checkout@v4"},
    {
        "name": "Set up Python",
        "uses": "actions/setup-python@v5",
        "with": {
            "python-version": "3.12",
            "cache": "pip",
            "cache-dependency-path": "requirements-test.txt",
        },
    },
    {
        "name": "Install test dependencies",
        "run": "python -m pip install -r requirements-test.txt",
    },
    {
        "name": "Build deterministic release archives",
        "run": "python scripts/build_release.py --build-extension-from-component",
    },
    {
        "name": "Verify distribution contract",
        "run": "python scripts/verify_distribution.py",
    },
    {
        "name": "Run distribution tests",
        "run": "python -m unittest discover -s tests -v",
    },
]


def redact_error(message: str) -> str:
    redacted = str(message)
    for rule, pattern in contract._SECRET_PATTERNS:
        redacted = pattern.sub(f"<redacted:{rule}>", redacted)
    return redacted


def _redact_errors(errors: list[str]) -> list[str]:
    return [redact_error(error) for error in errors]


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _public_text_surfaces(root: Path) -> list[Path]:
    surfaces: set[Path] = set(root.glob("*.md"))
    for relative in (Path("docs"), Path("extension/chrome"), Path("skill")):
        start = root / relative
        if not start.is_dir():
            continue
        surfaces.update(
            path
            for path in start.rglob("*")
            if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
        )
    return sorted(surfaces, key=lambda path: path.relative_to(root).as_posix())


def _claim_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 48) : start]
    return bool(_ENGLISH_NEGATION.search(prefix) or _CHINESE_NEGATION.search(prefix))


def verify_required_files(root: Path) -> list[str]:
    return [
        f"missing required file: {name}"
        for name in REQUIRED_FILES
        if not (root / name).is_file()
    ]


def _effective_gitignore_rules(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _gitignore_rules_follow_safety_policy(rules: list[str]) -> bool:
    try:
        required_positions = tuple(rules.index(rule) for rule in EXPECTED_GITIGNORE_RULES)
    except ValueError:
        return False
    return required_positions == tuple(sorted(required_positions)) and all(
        not rule.startswith("!") or rule == "!.env.example" for rule in rules
    )


def _gitignore_has_expected_behavior(root: Path) -> bool | None:
    paths = (
        ".env",
        ".env.local",
        ".env.production",
        "nested/.env",
        "nested/.env.local",
        "nested/.env.production",
        ".env.example",
        "nested/.env.example",
    )
    expected_ignored = set(paths[:6])
    try:
        with tempfile.TemporaryDirectory() as temp:
            repository = Path(temp)
            (repository / ".gitignore").write_bytes((root / ".gitignore").read_bytes())
            initialized = subprocess.run(
                ["git", "init", "-q"],
                cwd=repository,
                capture_output=True,
                check=False,
            )
            if initialized.returncode != 0:
                return None
            checked = subprocess.run(
                ["git", "check-ignore", "--no-index", "--", *paths],
                cwd=repository,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if checked.returncode not in {0, 1}:
                return None
            ignored = {line.strip().replace("\\", "/") for line in checked.stdout.splitlines()}
            return ignored == expected_ignored
    except (OSError, subprocess.SubprocessError):
        return None


def verify_ci_contract(root: Path) -> list[str]:
    errors: list[str] = []
    gitignore = _effective_gitignore_rules((root / ".gitignore").read_text(encoding="utf-8"))
    for rule in EXPECTED_GITIGNORE_RULES:
        if rule not in gitignore:
            errors.append(f".gitignore is missing required rule: {rule}")
    gitignore_behavior = _gitignore_has_expected_behavior(root)
    if gitignore_behavior is None:
        return ["gitignore semantic validation unavailable"]
    if not _gitignore_rules_follow_safety_policy(gitignore) or not gitignore_behavior:
        errors.append(".gitignore environment-file behavior is incorrect")
    for path in root.rglob(".env*"):
        if path.is_file() and path.name != ".env.example":
            errors.append(f"environment file is not allowed in public distribution: {path.relative_to(root).as_posix()}")
    gitattributes = _effective_gitignore_rules(
        (root / ".gitattributes").read_text(encoding="utf-8")
    )
    if tuple(gitattributes) != EXPECTED_GITATTRIBUTES_RULES:
        errors.append(".gitattributes release normalization is incorrect")
    try:
        workflow = yaml.safe_load(
            (root / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        )
    except yaml.YAMLError as exc:
        return errors + [f"GitHub Actions workflow is invalid YAML: {exc}"]
    if not isinstance(workflow, dict):
        return errors + ["GitHub Actions workflow must be a mapping"]
    if workflow.get("permissions") != {"contents": "read"}:
        errors.append("GitHub Actions permissions are incorrect")
    triggers = workflow.get("on")
    if (
        not isinstance(triggers, dict)
        or set(triggers) != {"push", "pull_request"}
        or any(value is not None and not isinstance(value, dict) for value in triggers.values())
    ):
        errors.append("GitHub Actions workflow triggers are incorrect")
        return errors
    jobs = workflow.get("jobs")
    job = jobs.get("test") if isinstance(jobs, dict) else None
    if not isinstance(job, dict):
        return errors + ["GitHub Actions test job is missing"]
    if job.get("runs-on") != "${{ matrix.os }}":
        errors.append("GitHub Actions test runner is incorrect")
    strategy = job.get("strategy")
    if not isinstance(strategy, dict):
        errors.append("GitHub Actions strategy must be a mapping")
    else:
        if strategy.get("fail-fast") is not False:
            errors.append("GitHub Actions fail-fast policy is incorrect")
        matrix = strategy.get("matrix")
        if not isinstance(matrix, dict):
            errors.append("GitHub Actions matrix must be a mapping")
        elif matrix.get("os") != ["windows-latest", "ubuntu-latest"]:
            errors.append("GitHub Actions OS matrix is incorrect")
    steps = job.get("steps")
    if not isinstance(steps, list):
        errors.append("GitHub Actions steps must be a list")
    elif steps != EXPECTED_CI_STEPS:
        errors.append("GitHub Actions test steps are incorrect")
    return errors


def verify_identity_and_links(root: Path, release: dict) -> list[str]:
    errors: list[str] = []
    zh = (root / "README.md").read_text(encoding="utf-8")
    en = (root / "README.en.md").read_text(encoding="utf-8")
    required_zh = (
        contract.PRODUCT_ZH,
        contract.PRODUCT_PROMISE_ZH,
        "https://www.enhe-tech.com.cn/",
        "https://www.enhe-tech.com.cn/promotion-manager",
        f"https://chromewebstore.google.com/detail/enhe-promotion-manager/{contract.STORE_ITEM_ID}",
        "huqingwei5942@gmail.com",
    )
    required_en = (
        contract.PRODUCT_EN,
        contract.PRODUCT_PROMISE_EN,
        "https://www.enhe-tech.com.cn/",
        "https://www.enhe-tech.com.cn/promotion-manager",
        f"https://chromewebstore.google.com/detail/enhe-promotion-manager/{contract.STORE_ITEM_ID}",
        "https://github.com/hqwzhu",
    )
    errors.extend(f"README.md missing identity: {value}" for value in required_zh if value not in zh)
    errors.extend(f"README.en.md missing identity: {value}" for value in required_en if value not in en)
    if release.get("sourceRepository") != "https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator":
        errors.append("release sourceRepository is incorrect")
    if release.get("publicRepository") != "https://github.com/hqwzhu/enhe-promotion-manager":
        errors.append("release publicRepository is incorrect")
    store = release.get("chromeWebStore", {})
    if not isinstance(store, dict):
        errors.append("Chrome Web Store record must be a mapping")
    else:
        if store.get("itemId") != contract.STORE_ITEM_ID:
            errors.append("Chrome Web Store item ID is incorrect")
        if store.get("publishedVersion") != contract.PUBLISHED_STORE_VERSION:
            errors.append("Chrome Web Store published version is incorrect")
        if (
            store.get("submittedVersion") is not None
            or store.get("status") != "published"
            or store.get("listingUrl") != contract.STORE_LISTING_URL
        ):
            errors.append("Chrome Web Store submission state is incorrect")
    if release.get("skillArchive") != EXPECTED_SKILL_ARCHIVE:
        errors.append("release Skill archive name is incorrect")
    if release.get("extensionArchive") != EXPECTED_EXTENSION_ARCHIVE:
        errors.append("release extension archive name is incorrect")
    sync_audit = release.get("syncAudit", {})
    if not isinstance(sync_audit, dict):
        errors.append("release synchronization audit must be a mapping")
    else:
        if sync_audit.get("status") != "ready":
            errors.append("release synchronization audit is not ready")
        if sync_audit.get("scope") != "non-payment extension commands to shipped Skill scripts":
            errors.append("release synchronization scope is incorrect")
        if sync_audit.get("excluded") != [
            "payment",
            "subscription",
            "license purchase",
            "credits",
            "billing backend",
        ]:
            errors.append("release synchronization exclusions are incorrect")
    verification = release.get("verification", {})
    if not isinstance(verification, dict):
        errors.append("release verification must be a mapping")
    elif verification.get("commands") != list(EXPECTED_VALIDATOR_COMMANDS):
        errors.append("release validator commands are incorrect")
    return errors


def verify_versions(root: Path, release: dict) -> list[str]:
    errors: list[str] = []
    extension = read_json(root / "extension/chrome/manifest.json")
    skill_component = read_json(root / "skill/viral-product-copy-video-generator/component-manifest.json")
    extension_component = read_json(root / "extension/chrome/component-manifest.json")
    for label, value in (
        ("release", release.get("version")),
        ("extension", extension.get("version")),
        ("skill component", skill_component.get("version")),
        ("extension component", extension_component.get("version")),
    ):
        if value != contract.VERSION:
            errors.append(f"{label} version is {value!r}, expected {contract.VERSION}")
    for label, value in (
        ("skill component sourceCommit", skill_component.get("sourceCommit")),
        ("extension component sourceCommit", extension_component.get("sourceCommit")),
    ):
        if value != release.get("sourceCommit"):
            errors.append(f"{label} differs from release sourceCommit")
    if not isinstance(release.get("sourceCommit"), str) or not release["sourceCommit"].strip():
        errors.append("release sourceCommit is missing")
    if skill_component.get("runtime") != "Python 3.11 and Codex":
        errors.append("Skill component runtime is incorrect")
    if skill_component.get("entryPoints") != ["SKILL.md", "scripts/skill_entry.py"]:
        errors.append("Skill component entry points are incorrect")
    if skill_component.get("capabilityIds") != list(contract.NON_PAYMENT_COMMANDS):
        errors.append("Skill component capability IDs differ from the contract")
    if extension_component.get("runtime") != "Chrome Manifest V3":
        errors.append("extension component runtime is incorrect")
    if extension_component.get("name") != contract.PRODUCT_EN:
        errors.append("extension component product name is incorrect")
    if extension_component.get("entryPoints") != ["manifest.json", "popup.html", "popup.js"]:
        errors.append("extension component entry points are incorrect")
    if extension_component.get("nonPaymentCapabilityIds") != list(contract.NON_PAYMENT_COMMANDS):
        errors.append("extension component capability IDs differ from the contract")
    if extension.get("name") != "__MSG_extensionName__":
        errors.append("extension manifest localized name is incorrect")
    if extension.get("default_locale") != "en":
        errors.append("extension manifest default locale is incorrect")
    for locale, expected_name in (("en", contract.PRODUCT_EN), ("zh_CN", contract.PRODUCT_ZH)):
        messages = read_json(root / "extension/chrome/_locales" / locale / "messages.json")
        extension_name = messages.get("extensionName")
        if not isinstance(extension_name, dict):
            errors.append(f"{locale} extensionName must be a mapping")
        elif extension_name.get("message") != expected_name:
            errors.append(f"{locale} extension product name is incorrect")
    return errors


def verify_extension_boundary(root: Path) -> list[str]:
    manifest = read_json(root / "extension/chrome/manifest.json")
    errors: list[str] = []
    if manifest.get("manifest_version") != 3:
        errors.append("extension is not Manifest V3")
    if manifest.get("permissions") != ["activeTab", "storage", "clipboardWrite"]:
        errors.append(f"unexpected extension permissions: {manifest.get('permissions')}")
    if manifest.get("host_permissions") != ["https://www.enhe-tech.com.cn/*"]:
        errors.append(f"unexpected extension host permissions: {manifest.get('host_permissions')}")
    return errors


def verify_non_payment_sync(root: Path, release: dict) -> list[str]:
    popup = (root / "extension/chrome/popup.js").read_text(encoding="utf-8")
    try:
        commands = tuple(contract.extension_command_refs(popup))
    except ValueError as exc:
        return [f"extension command parsing failed: {exc}"]
    errors: list[str] = []
    if commands != contract.NON_PAYMENT_COMMANDS:
        errors.append(f"extension command drift: {commands}")
    sync_audit = release.get("syncAudit", {})
    if not isinstance(sync_audit, dict):
        errors.append("release synchronization audit must be a mapping")
    elif sync_audit.get("commands") != list(contract.NON_PAYMENT_COMMANDS):
        errors.append("release manifest command list differs from the contract")
    component = read_json(root / "extension/chrome/component-manifest.json")
    if component.get("billingParityIncluded") is not False:
        errors.append("billing parity must remain excluded")
    for name in contract.NON_PAYMENT_COMMANDS:
        if not (root / "skill/viral-product-copy-video-generator/scripts" / name).is_file():
            errors.append(f"shipped Skill is missing command script: {name}")
    return errors


def verify_component_paths(root: Path) -> list[str]:
    errors: list[str] = []
    for component_name in (
        "skill/viral-product-copy-video-generator",
        "extension/chrome",
    ):
        component = root / component_name
        files, directories, issues = contract._walk_tree(root, component)
        for issue in issues:
            errors.append(
                f"unsafe public component path: {component_name}/{issue['path']} ({issue['rule']})"
            )
        for path in files + directories:
            relative = path.relative_to(component)
            if (
                any(part.lower() in _GENERATED_COMPONENT_PARTS for part in relative.parts)
                or path.suffix.lower() == ".pyc"
            ):
                errors.append(
                    f"generated or cache path in public component: {component_name}/{relative.as_posix()}"
                )
    return errors


def verify_hosted_worker_language(root: Path) -> list[str]:
    zh = (root / "docs/zh-CN/version-sync.md").read_text(encoding="utf-8")
    en = (root / "docs/en/version-sync.md").read_text(encoding="utf-8")
    errors: list[str] = []
    if "Hosted Worker：关闭" not in zh:
        errors.append("Chinese version guide must state Hosted Worker is off")
    if "Hosted Worker: disabled" not in en:
        errors.append("English version guide must state Hosted Worker is disabled")
    return errors


def verify_claim_boundaries(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _public_text_surfaces(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for rule, pattern in CLAIM_PATTERNS:
            if any(not _claim_is_negated(text, match.start()) for match in pattern.finditer(text)):
                errors.append(
                    f"unsafe public claim: {rule} ({path.relative_to(root).as_posix()})"
                )
    return errors


def _safe_zip_members(archive: zipfile.ZipFile) -> list[str]:
    names = archive.namelist()
    for index, name in enumerate(names, start=1):
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError(f"unsafe archive member path at index {index}")
    return names


def verify_archives(root: Path, release: dict) -> list[str]:
    errors: list[str] = []
    if release.get("skillArchive") != EXPECTED_SKILL_ARCHIVE:
        errors.append("release Skill archive name is incorrect")
    if release.get("extensionArchive") != EXPECTED_EXTENSION_ARCHIVE:
        errors.append("release extension archive name is incorrect")
    if errors:
        return errors
    dist = root / "dist" / f"v{contract.VERSION}"
    skill_zip = dist / str(release.get("skillArchive", ""))
    extension_zip = dist / str(release.get("extensionArchive", ""))
    for path in (skill_zip, extension_zip):
        if not path.is_file():
            errors.append(f"release archive is missing: {path.name}")
    if errors:
        return errors

    skill_source = root / "skill" / "viral-product-copy-video-generator"
    expected_skill = {
        f"viral-product-copy-video-generator/{path.relative_to(skill_source).as_posix()}": path
        for path in contract._strict_files(root, skill_source)
    }
    try:
        with zipfile.ZipFile(skill_zip) as archive:
            names = _safe_zip_members(archive)
            errors.extend(
                f"Skill ZIP metadata is not deterministic: {name}"
                for name in contract.nondeterministic_zip_members(archive)
            )
            if len(names) != len(set(names)) or set(names) != set(expected_skill):
                errors.append("Skill ZIP member list differs from Skill source")
            else:
                for name, source in expected_skill.items():
                    if archive.read(name) != source.read_bytes():
                        errors.append(f"Skill ZIP bytes differ from source: {name}")
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        errors.append(f"invalid Skill ZIP: {exc}")

    expected_extension = {
        path.relative_to(root / "extension/chrome").as_posix(): path
        for path in contract._strict_files(root, root / "extension/chrome")
        if path.name != "component-manifest.json"
    }
    try:
        with zipfile.ZipFile(extension_zip) as archive:
            names = _safe_zip_members(archive)
            errors.extend(
                f"extension ZIP metadata is not deterministic: {name}"
                for name in contract.nondeterministic_zip_members(archive)
            )
            if "manifest.json" not in names:
                errors.append("extension ZIP is missing root manifest.json")
            if "component-manifest.json" in names:
                errors.append("public component-manifest.json must not enter the Chrome ZIP")
            if len(names) != len(set(names)) or set(names) != set(expected_extension):
                errors.append("extension ZIP member list differs from extension/chrome source")
            else:
                for name, source in expected_extension.items():
                    if archive.read(name) != source.read_bytes():
                        errors.append(f"extension ZIP bytes differ from source: {name}")
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        errors.append(f"invalid extension ZIP: {exc}")

    artifacts = release.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return errors + ["release artifacts must be a mapping"]
    if set(artifacts) != {skill_zip.name, extension_zip.name}:
        errors.append("release artifact records differ from the official archive set")
    for path in (skill_zip, extension_zip):
        record = artifacts.get(path.name, {})
        if not isinstance(record, dict):
            errors.append(f"artifact record must be a mapping: {path.name}")
            continue
        actual_bytes = path.stat().st_size
        actual_hash = contract.sha256_file(path).upper()
        if record.get("bytes") != actual_bytes:
            errors.append(f"artifact byte count mismatch in release manifest: {path.name}")
        if record.get("sha256") != actual_hash:
            errors.append(f"artifact hash mismatch in release manifest: {path.name}")

    with tempfile.TemporaryDirectory() as temp:
        extracted = Path(temp)
        try:
            with zipfile.ZipFile(skill_zip) as archive:
                _safe_zip_members(archive)
                archive.extractall(extracted / "skill")
            with zipfile.ZipFile(extension_zip) as archive:
                _safe_zip_members(archive)
                archive.extractall(extracted / "extension")
        except (OSError, zipfile.BadZipFile, ValueError) as exc:
            errors.append(f"archive extraction failed: {exc}")
        else:
            for item in contract.scan_forbidden(extracted):
                errors.append(f"archive forbidden content: {item['path']} ({item['rule']})")
    return errors


def canonical_tree_digest(root: Path, release: dict) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        contract._strict_files(root),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root)
        relative_name = relative.as_posix()
        if relative.parts and relative.parts[0] in {".git", "dist"}:
            continue
        if relative_name == "SHA256SUMS":
            continue
        data = path.read_bytes()
        if relative_name == "release-manifest.json":
            normalized = dict(release)
            verification = release.get("verification")
            commands = verification.get("commands") if isinstance(verification, dict) else None
            normalized["treeDigest"] = "normalized"
            normalized["artifacts"] = {}
            normalized["verification"] = {
                "status": "normalized",
                "commands": commands,
            }
            data = (json.dumps(normalized, ensure_ascii=False, sort_keys=True) + "\n").encode(
                "utf-8"
            )
        digest.update(relative_name.encode("utf-8") + b"\0" + data)
    return digest.hexdigest()


def verify_tree_digest(root: Path, release: dict) -> list[str]:
    expected = release.get("treeDigest")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        return ["release treeDigest is not a lowercase SHA-256 value"]
    actual = canonical_tree_digest(root, release)
    return [] if actual == expected else ["release treeDigest does not match the public tree"]


def verify_checksums(root: Path) -> list[str]:
    checksum_path = root / "SHA256SUMS"
    if not checksum_path.is_file():
        return ["SHA256SUMS is missing"]
    errors: list[str] = []
    records: dict[str, str] = {}
    names_in_order: list[str] = []
    for line_number, line in enumerate(
        checksum_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = re.fullmatch(r"([0-9A-F]{64})  (.+)", line)
        if not match:
            errors.append(
                f"invalid checksum line {line_number}: expected uppercase SHA-256 and relative path"
            )
            continue
        expected, name = match.groups()
        names_in_order.append(name)
        if name in records:
            errors.append(f"duplicate checksum entry at line {line_number}")
        records[name] = expected
        if name not in EXPECTED_CHECKSUM_PATHS:
            continue
        path = root / name
        if not path.is_file() or contract.sha256_file(path).upper() != expected:
            errors.append(f"checksum mismatch: {name}")
    if names_in_order != sorted(names_in_order):
        errors.append("SHA256SUMS entries are not sorted")
    if sorted(records) != sorted(EXPECTED_CHECKSUM_PATHS):
        errors.append("SHA256SUMS entries differ from the release artifact set")
    return errors


def verify_forbidden(root: Path) -> list[str]:
    violations = contract.scan_forbidden(root)
    return [
        f"forbidden public content: {item['path']} ({item['rule']})"
        for item in violations
        if not (
            Path(item["path"]).parts
            and Path(item["path"]).parts[0] in {".git", "dist"}
        )
        and not (
            any(part in {"__pycache__", ".pytest_cache"} for part in Path(item["path"]).parts)
            and not item["path"].startswith("skill/")
            and not item["path"].startswith("extension/")
        )
    ]


def validate(root: Path, check_checksums: bool = True) -> list[str]:
    root = Path(root).resolve()
    errors = verify_required_files(root)
    if errors:
        return _redact_errors(errors)
    try:
        release = read_json(root / "release-manifest.json")
        if release.get("version") != contract.VERSION:
            errors.append("release version differs from distribution contract")
        verification = release.get("verification")
        if not isinstance(verification, dict):
            errors.append("release verification must be a mapping")
            verification_status = None
        else:
            verification_status = verification.get("status")
        if check_checksums:
            if verification_status != "ready":
                errors.append("release verification status must be ready")
        elif verification_status not in {"built", "ready"}:
            errors.append("release verification status is not built or ready")
        errors.extend(verify_identity_and_links(root, release))
        errors.extend(verify_ci_contract(root))
        errors.extend(verify_versions(root, release))
        errors.extend(verify_extension_boundary(root))
        errors.extend(verify_non_payment_sync(root, release))
        errors.extend(verify_component_paths(root))
        errors.extend(verify_hosted_worker_language(root))
        errors.extend(verify_claim_boundaries(root))
        errors.extend(verify_archives(root, release))
        errors.extend(verify_tree_digest(root, release))
        if check_checksums:
            errors.extend(verify_checksums(root))
        errors.extend(verify_forbidden(root))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"validation failure: {exc}")
    except Exception:
        return ["validation failure: unexpected validator error"]
    return _redact_errors(errors)


def main() -> None:
    try:
        errors = validate(ROOT)
    except Exception:  # pragma: no cover - final CLI guard
        errors = ["validation failure: unexpected validator error"]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Distribution verification status: ready")


if __name__ == "__main__":
    main()
