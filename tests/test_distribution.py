#!/usr/bin/env python3
"""End-to-end contract tests for the standalone public repository."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SOURCE_SCRIPTS = ROOT.parent / "scripts"
if not (SCRIPTS / "distribution_contract.py").is_file() and str(SOURCE_SCRIPTS) not in sys.path:
    sys.path.insert(1, str(SOURCE_SCRIPTS))

import build_release  # noqa: E402
import distribution_contract as contract  # noqa: E402
import generate_checksums  # noqa: E402
import verify_distribution  # noqa: E402


FIXED_ZIP_TIMESTAMP = contract.FIXED_ZIP_TIMESTAMP
FIXED_ZIP_CREATE_SYSTEM = contract.FIXED_ZIP_CREATE_SYSTEM
FIXED_ZIP_EXTERNAL_ATTR = contract.FIXED_ZIP_EXTERNAL_ATTR
FIXED_ZIP_COMPRESSLEVEL = contract.FIXED_ZIP_COMPRESSLEVEL


def write_deterministic_zip_member(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIMESTAMP)
    info.create_system = FIXED_ZIP_CREATE_SYSTEM
    info.external_attr = FIXED_ZIP_EXTERNAL_ATTR
    info.compress_type = zipfile.ZIP_DEFLATED
    info.extra = b""
    info.comment = b""
    archive.writestr(
        info,
        data,
        compress_type=zipfile.ZIP_DEFLATED,
        compresslevel=FIXED_ZIP_COMPRESSLEVEL,
    )


def write_text(root: Path, relative: str, text: str = "fixture\n") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(root: Path, relative: str, payload: dict) -> Path:
    return write_text(
        root,
        relative,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def create_public_repository(base: Path) -> tuple[Path, Path]:
    root = base / "public"
    root.mkdir()
    store_url = (
        "https://chromewebstore.google.com/detail/enhe-promotion-manager/"
        f"{contract.STORE_ITEM_ID}"
    )
    write_text(
        root,
        "README.md",
        "\n".join(
            (
                contract.PRODUCT_ZH,
                contract.PRODUCT_PROMISE_ZH,
                "https://www.enhe-tech.com.cn/",
                "https://www.enhe-tech.com.cn/promotion-manager",
                store_url,
                "huqingwei5942@gmail.com",
            )
        ),
    )
    write_text(
        root,
        "README.en.md",
        "\n".join(
            (
                contract.PRODUCT_EN,
                contract.PRODUCT_PROMISE_EN,
                "https://www.enhe-tech.com.cn/",
                "https://www.enhe-tech.com.cn/promotion-manager",
                store_url,
                "https://github.com/hqwzhu",
                "Results are not guaranteed viral. The tool does not bypass CAPTCHA.",
            )
        ),
    )
    for name in ("LICENSE", "NOTICE.md", "SECURITY.md", "CHANGELOG.md"):
        write_text(root, name)
    for relative in verify_distribution.REQUIRED_DOCS:
        content = "Public distribution guide.\n"
        if relative == "docs/zh-CN/version-sync.md":
            content = "Hosted Worker：关闭\n"
        elif relative == "docs/en/version-sync.md":
            content = "Hosted Worker: disabled\n"
        write_text(root, relative, content)

    write_text(root, ".gitignore", "dist/\ntmp-release-download/\n.env\n.env.*\n!.env.example\n__pycache__/\n*.pyc\n.pytest_cache/\n")
    write_text(root, ".gitattributes", "* text=auto eol=lf\nrelease-manifest.json -text\n")
    write_text(root, "requirements-test.txt", "PyYAML==6.0.3\n")
    write_text(
        root,
        ".github/workflows/tests.yml",
        "\n".join(
            (
                "name: tests",
                "'on':",
                "  push:",
                "  pull_request:",
                "permissions:",
                "  contents: read",
                "jobs:",
                "  test:",
                "    strategy:",
                "      fail-fast: false",
                "      matrix:",
                "        os: [windows-latest, ubuntu-latest]",
                "    runs-on: ${{ matrix.os }}",
                "    steps:",
                "      - name: Check out repository",
                "        uses: actions/checkout@v4",
                "      - name: Set up Python",
                "        uses: actions/setup-python@v5",
                "        with:",
                "          python-version: '3.12'",
                "          cache: pip",
                "          cache-dependency-path: requirements-test.txt",
                "      - name: Install test dependencies",
                "        run: python -m pip install -r requirements-test.txt",
                "      - name: Build deterministic release archives",
                "        run: python scripts/build_release.py --build-extension-from-component",
                "      - name: Verify distribution contract",
                "        run: python scripts/verify_distribution.py",
                "      - name: Run distribution tests",
                "        run: python -m unittest discover -s tests -v",
            )
            + ("",)
        ),
    )

    skill = "skill/viral-product-copy-video-generator"
    write_text(root, f"{skill}/SKILL.md", "# Synthetic Skill\n")
    write_text(root, f"{skill}/requirements-youtube.txt", "requests==2.32.0\n")
    for name in contract.NON_PAYMENT_COMMANDS:
        write_text(root, f"{skill}/scripts/{name}", f"# {name}\n")
    write_json(
        root,
        f"{skill}/component-manifest.json",
        {
            "name": "viral-product-copy-video-generator",
            "version": contract.VERSION,
            "sourceCommit": "synthetic-commit",
            "runtime": "Python 3.11 and Codex",
            "entryPoints": ["SKILL.md", "scripts/skill_entry.py"],
            "capabilityIds": list(contract.NON_PAYMENT_COMMANDS),
        },
    )

    extension = "extension/chrome"
    write_json(
        root,
        f"{extension}/manifest.json",
        {
            "manifest_version": 3,
            "name": "__MSG_extensionName__",
            "default_locale": "en",
            "version": contract.VERSION,
            "permissions": ["activeTab", "storage", "clipboardWrite"],
            "host_permissions": ["https://www.enhe-tech.com.cn/*"],
        },
    )
    popup = "\n".join(
        f'const command{index} = "python scripts/{name}";'
        for index, name in enumerate(contract.NON_PAYMENT_COMMANDS)
    )
    write_text(root, f"{extension}/popup.js", popup + "\n")
    write_text(root, f"{extension}/popup.html", "<!doctype html><title>Safe fixture</title>\n")
    write_json(
        root,
        f"{extension}/_locales/en/messages.json",
        {"extensionName": {"message": contract.PRODUCT_EN}},
    )
    write_json(
        root,
        f"{extension}/_locales/zh_CN/messages.json",
        {"extensionName": {"message": contract.PRODUCT_ZH}},
    )
    write_json(
        root,
        f"{extension}/component-manifest.json",
        {
            "name": contract.PRODUCT_EN,
            "version": contract.VERSION,
            "sourceCommit": "synthetic-commit",
            "runtime": "Chrome Manifest V3",
            "entryPoints": ["manifest.json", "popup.html", "popup.js"],
            "nonPaymentCapabilityIds": list(contract.NON_PAYMENT_COMMANDS),
            "billingParityIncluded": False,
        },
    )

    for relative in (
        "scripts/build_release.py",
        "scripts/generate_checksums.py",
        "scripts/verify_distribution.py",
        "scripts/distribution_contract.py",
        "tests/test_distribution.py",
    ):
        write_text(root, relative, f"# {relative}\n")
    version = contract.VERSION
    write_json(
        root,
        "release-manifest.json",
        {
            "version": version,
            "sourceRepository": "https://github.com/hqwzhu/Viral-Product-Copy-Video-Generator",
            "sourceCommit": "synthetic-commit",
            "publicRepository": "https://github.com/hqwzhu/enhe-promotion-manager",
            "treeDigest": "pending-final-build",
            "skillArchive": f"enhe-product-promo-maker-skill-{version}.zip",
            "extensionArchive": f"enhe-promotion-manager-extension-{version}.zip",
            "chromeWebStore": {
                "itemId": contract.STORE_ITEM_ID,
                "publishedVersion": contract.PUBLISHED_STORE_VERSION,
                "submittedVersion": None,
                "status": "published",
                "listingUrl": store_url,
            },
            "syncAudit": {
                "scope": "non-payment extension commands to shipped Skill scripts",
                "excluded": [
                    "payment",
                    "subscription",
                    "license purchase",
                    "credits",
                    "billing backend",
                ],
                "commands": list(contract.NON_PAYMENT_COMMANDS),
                "status": "ready",
            },
            "artifacts": {},
            "verification": {
                "status": "pending",
                "commands": list(verify_distribution.EXPECTED_VALIDATOR_COMMANDS),
            },
        },
    )

    validated = base / f"validated-extension-{version}.zip"
    extension_root = root / extension
    with zipfile.ZipFile(
        validated,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=FIXED_ZIP_COMPRESSLEVEL,
    ) as archive:
        archive.comment = b""
        for path in sorted(extension_root.rglob("*")):
            if path.is_file() and path.name != "component-manifest.json":
                write_deterministic_zip_member(
                    archive,
                    path.relative_to(extension_root).as_posix(),
                    path.read_bytes(),
                )
    return root, validated


class PublicDistributionTest(unittest.TestCase):
    def test_gitignore_contract_uses_git_semantics_for_each_isolated_drift(self) -> None:
        mutations = {
            "commented rules": "# .env\n# .env.*\n!.env.example\n",
            "wrong order": "!.env.example\n.env\n.env.*\n",
            "root reinclude": ".env\n.env.*\n!.env.example\n!/.env.local\n",
            "anchored rules": "/.env\n/.env.*\n!/.env.example\n",
            "glob reinclude": ".env\n.env.*\n!.env.example\n!nested/.env*\n",
            "character class reinclude": ".env\n.env.*\n!.env.example\n!**/[.]env.local\n",
            "nested reinclude": ".env\n.env.*\n!.env.example\n!nested/.env.production\n",
            "example reignored": ".env\n.env.*\n!.env.example\n.env.example\n",
        }
        for name, content in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root, _ = create_public_repository(Path(temp))
                self.assertEqual(verify_distribution.verify_ci_contract(root), [])
                write_text(root, ".gitignore", content)
                self.assertIn(
                    ".gitignore environment-file behavior is incorrect",
                    verify_distribution.verify_ci_contract(root),
                )

    def test_gitignore_contract_rejects_unsafe_negations_and_masked_rule_order(self) -> None:
        mutations = {
            "root secret reinclude": (".env\n.env.*\n!.env.example\n!/.env.secret\n", True),
            "production reinclude": (".env\n.env.*\n!.env.example\n!.env.production\n", False),
            "recursive local reinclude": (".env\n.env.*\n!.env.example\n!**/.env.local\n", False),
            "masked required-rule order": (".env\n!.env.example\n.env.*\n!.env.example\n", True),
        }
        for name, (content, sampled_semantics_pass) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root, _ = create_public_repository(Path(temp))
                self.assertEqual(verify_distribution.verify_ci_contract(root), [])
                write_text(root, ".gitignore", content)
                self.assertEqual(
                    verify_distribution._gitignore_has_expected_behavior(root),
                    sampled_semantics_pass,
                )
                self.assertIn(
                    ".gitignore environment-file behavior is incorrect",
                    verify_distribution.verify_ci_contract(root),
                )

    def test_ci_contract_rejects_each_isolated_yaml_drift(self) -> None:
        mutations = (
            ("trigger comment", "text", ("  push:", "  # push:"), "GitHub Actions workflow triggers are incorrect"),
            ("push false", "text", ("  push:", "  push: false"), "GitHub Actions workflow triggers are incorrect"),
            ("strategy scalar", "yaml", ("strategy",), "GitHub Actions strategy must be a mapping"),
            ("matrix scalar", "yaml", ("strategy", "matrix"), "GitHub Actions matrix must be a mapping"),
            ("steps scalar", "yaml", ("steps",), "GitHub Actions steps must be a list"),
        )
        for name, mutation_type, mutation, expected in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root, _ = create_public_repository(Path(temp))
                self.assertEqual(verify_distribution.verify_ci_contract(root), [])
                path = root / ".github/workflows/tests.yml"
                if mutation_type == "text":
                    old, new = mutation
                    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
                else:
                    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
                    target = workflow["jobs"]["test"]
                    for key in mutation[:-1]:
                        target = target[key]
                    target[mutation[-1]] = "broken"
                    path.write_text(yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8")
                self.assertIn(expected, verify_distribution.verify_ci_contract(root))

    def test_ci_contract_rejects_security_and_bootstrap_drift(self) -> None:
        mutations = (
            (
                "permissions",
                lambda workflow: workflow.__setitem__("permissions", {"contents": "write"}),
                "GitHub Actions permissions are incorrect",
            ),
            (
                "fail fast",
                lambda workflow: workflow["jobs"]["test"]["strategy"].__setitem__("fail-fast", True),
                "GitHub Actions fail-fast policy is incorrect",
            ),
            (
                "setup cache",
                lambda workflow: workflow["jobs"]["test"]["steps"][1]["with"].__setitem__("cache", ""),
                "GitHub Actions test steps are incorrect",
            ),
            (
                "bootstrap command",
                lambda workflow: workflow["jobs"]["test"]["steps"][3].__setitem__(
                    "run", "python scripts/verify_distribution.py"
                ),
                "GitHub Actions test steps are incorrect",
            ),
        )
        for name, mutate, expected in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root, _ = create_public_repository(Path(temp))
                self.assertEqual(verify_distribution.verify_ci_contract(root), [])
                path = root / ".github/workflows/tests.yml"
                workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
                mutate(workflow)
                path.write_text(yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8")
                self.assertIn(expected, verify_distribution.verify_ci_contract(root))

        with tempfile.TemporaryDirectory() as temp:
            root, _ = create_public_repository(Path(temp))
            self.assertEqual(verify_distribution.verify_ci_contract(root), [])
            write_text(root, ".gitattributes", "* text=auto\n")
            self.assertIn(
                ".gitattributes release normalization is incorrect",
                verify_distribution.verify_ci_contract(root),
            )

    def test_gitignore_contract_reports_git_unavailable_without_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, _ = create_public_repository(Path(temp))
            with mock.patch("subprocess.run", side_effect=OSError("private-path")):
                errors = verify_distribution.verify_ci_contract(root)
            self.assertEqual(errors, ["gitignore semantic validation unavailable"])
            self.assertNotIn("private-path", " | ".join(errors))

    def test_store_contract_rejects_each_isolated_drift_with_specific_error(self) -> None:
        mutations = (
            ("publishedVersion", "0.0.0", "Chrome Web Store published version is incorrect"),
            ("status", "pending_review", "Chrome Web Store submission state is incorrect"),
            ("listingUrl", "https://example.invalid/listing", "Chrome Web Store submission state is incorrect"),
        )
        for field, value, expected in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                root, _ = create_public_repository(Path(temp))
                release = verify_distribution.read_json(root / "release-manifest.json")
                self.assertEqual(verify_distribution.verify_identity_and_links(root, release), [])
                release["chromeWebStore"][field] = value
                self.assertIn(expected, verify_distribution.verify_identity_and_links(root, release))

        with tempfile.TemporaryDirectory() as temp:
            root, _ = create_public_repository(Path(temp))
            release = verify_distribution.read_json(root / "release-manifest.json")
            self.assertEqual(verify_distribution.verify_identity_and_links(root, release), [])
            release["chromeWebStore"] = "secret-store-value"
            self.assertEqual(
                verify_distribution.verify_identity_and_links(root, release),
                ["Chrome Web Store record must be a mapping"],
            )

    def test_product_contract_rejects_each_isolated_manifest_drift(self) -> None:
        mutations = (
            ("extension/chrome/manifest.json", ("name", "Wrong"), "extension manifest localized name is incorrect"),
            ("extension/chrome/manifest.json", ("default_locale", "zh_CN"), "extension manifest default locale is incorrect"),
            ("extension/chrome/component-manifest.json", ("name", "Wrong"), "extension component product name is incorrect"),
            ("extension/chrome/_locales/en/messages.json", ("extensionName", "Wrong"), "en extensionName must be a mapping"),
            ("extension/chrome/_locales/zh_CN/messages.json", ("extensionName", {"message": "Wrong"}), "zh_CN extension product name is incorrect"),
        )
        for relative, (field, value), expected in mutations:
            with self.subTest(relative=relative, field=field), tempfile.TemporaryDirectory() as temp:
                root, _ = create_public_repository(Path(temp))
                release = verify_distribution.read_json(root / "release-manifest.json")
                self.assertEqual(verify_distribution.verify_versions(root, release), [])
                payload = verify_distribution.read_json(root / relative)
                payload[field] = value
                write_json(root, relative, payload)
                self.assertIn(expected, verify_distribution.verify_versions(root, release))

    def test_validate_redacts_unexpected_exception_details(self) -> None:
        secret = "github_" + "pat_" + "abcdefghijklmnopqrstuvwxyz123456"
        with tempfile.TemporaryDirectory() as temp:
            root, _ = create_public_repository(Path(temp))
            with mock.patch.object(
                verify_distribution,
                "verify_identity_and_links",
                side_effect=AttributeError(f"{secret} C:/private/path"),
            ):
                errors = verify_distribution.validate(root, check_checksums=False)
            self.assertEqual(errors, ["validation failure: unexpected validator error"])
            self.assertNotIn(secret, " | ".join(errors))
            self.assertNotIn("C:/private/path", " | ".join(errors))

    def test_release_rolls_back_existing_publication_after_prevalidation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, validated = create_public_repository(base)
            version_dir = root / "dist" / f"v{contract.VERSION}"
            version_dir.mkdir(parents=True)
            skill_output = version_dir / verify_distribution.EXPECTED_SKILL_ARCHIVE
            extension_output = version_dir / verify_distribution.EXPECTED_EXTENSION_ARCHIVE
            checksum_output = root / "SHA256SUMS"
            release_output = root / "release-manifest.json"
            previous = {
                skill_output: b"previous-skill-archive",
                extension_output: b"previous-extension-archive",
                checksum_output: b"previous-checksums\n",
                release_output: release_output.read_bytes(),
            }
            for path, data in previous.items():
                path.write_bytes(data)
            external = base / "external-sentinel.zip"
            external.write_bytes(b"external-sentinel")

            with (
                mock.patch.object(build_release, "ROOT", root),
                mock.patch.object(
                    verify_distribution,
                    "validate",
                    return_value=["forced prevalidation failure"],
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced prevalidation failure"):
                    build_release.build_release(validated)

            for path, data in previous.items():
                self.assertEqual(path.read_bytes(), data, path.name)
            self.assertEqual(external.read_bytes(), b"external-sentinel")
            self.assertEqual(list(version_dir.glob(".tmp-*")), [])
            self.assertEqual(list(root.glob(".tmp-*")), [])

    def test_release_removes_new_publication_after_final_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            release_output = root / "release-manifest.json"
            previous_release = release_output.read_bytes()
            version_dir = root / "dist" / f"v{contract.VERSION}"
            skill_output = version_dir / verify_distribution.EXPECTED_SKILL_ARCHIVE
            extension_output = version_dir / verify_distribution.EXPECTED_EXTENSION_ARCHIVE
            checksum_output = root / "SHA256SUMS"

            with (
                mock.patch.object(build_release, "ROOT", root),
                mock.patch.object(
                    verify_distribution,
                    "validate",
                    side_effect=[[], ["forced final validation failure"]],
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced final validation failure"):
                    build_release.build_release(validated)

            self.assertEqual(release_output.read_bytes(), previous_release)
            self.assertFalse(skill_output.exists())
            self.assertFalse(extension_output.exists())
            self.assertFalse(checksum_output.exists())
            self.assertEqual(list(version_dir.glob(".tmp-*")), [])
            self.assertEqual(list(root.glob(".tmp-*")), [])

    def test_release_rejects_mocked_reparse_destination_without_partial_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, validated = create_public_repository(base)
            version_dir = root / "dist" / f"v{contract.VERSION}"
            version_dir.mkdir(parents=True)
            skill_output = version_dir / verify_distribution.EXPECTED_SKILL_ARCHIVE
            extension_output = version_dir / verify_distribution.EXPECTED_EXTENSION_ARCHIVE
            sentinel = b"external-sentinel"
            extension_output.write_bytes(sentinel)
            real_is_link = contract._is_link_or_reparse

            def mocked_reparse(path: Path) -> bool:
                return path == extension_output or real_is_link(path)

            with (
                mock.patch.object(build_release, "ROOT", root),
                mock.patch.object(
                    contract,
                    "_is_link_or_reparse",
                    side_effect=mocked_reparse,
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "link|reparse|destination"):
                    build_release.build_release(validated)

            self.assertEqual(extension_output.read_bytes(), sentinel)
            self.assertFalse(skill_output.exists())
            self.assertEqual(list(version_dir.glob(".tmp-*.zip")), [])

    def test_release_rejects_real_symlink_destination_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, validated = create_public_repository(base)
            version_dir = root / "dist" / f"v{contract.VERSION}"
            version_dir.mkdir(parents=True)
            skill_output = version_dir / verify_distribution.EXPECTED_SKILL_ARCHIVE
            extension_output = version_dir / verify_distribution.EXPECTED_EXTENSION_ARCHIVE
            external = base / "external.zip"
            sentinel = b"external-sentinel"
            external.write_bytes(sentinel)
            try:
                extension_output.symlink_to(external)
            except OSError as exc:
                self.skipTest(f"OS denied symlink creation: {exc}")

            with mock.patch.object(build_release, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "link|reparse|destination"):
                    build_release.build_release(validated)

            self.assertEqual(external.read_bytes(), sentinel)
            self.assertFalse(skill_output.exists())
            self.assertTrue(extension_output.is_symlink())
            self.assertEqual(list(version_dir.glob(".tmp-*.zip")), [])

    def test_release_rejects_non_directory_dist_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            (root / "dist").write_bytes(b"not-a-directory")

            with mock.patch.object(build_release, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "directory|ancestor"):
                    build_release.build_release(validated)

    def test_release_cleans_staged_archives_when_extension_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            version_dir = root / "dist" / f"v{contract.VERSION}"
            skill_output = version_dir / verify_distribution.EXPECTED_SKILL_ARCHIVE
            extension_output = version_dir / verify_distribution.EXPECTED_EXTENSION_ARCHIVE

            with (
                mock.patch.object(build_release, "ROOT", root),
                mock.patch.object(
                    build_release,
                    "copy_validated_extension",
                    side_effect=RuntimeError("fixture validation failure"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "fixture validation failure"):
                    build_release.build_release(validated)

            self.assertFalse(skill_output.exists())
            self.assertFalse(extension_output.exists())
            self.assertEqual(list(version_dir.glob(".tmp-*.zip")), [])

    def test_release_build_is_complete_deterministic_and_byte_faithful(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            with mock.patch.object(build_release, "ROOT", root):
                dist = build_release.build_release(validated)

            release = verify_distribution.read_json(root / "release-manifest.json")
            self.assertEqual(release["verification"]["status"], "ready")
            self.assertEqual(verify_distribution.validate(root), [])
            extension_zip = dist / release["extensionArchive"]
            self.assertEqual(extension_zip.read_bytes(), validated.read_bytes())
            with zipfile.ZipFile(extension_zip) as archive:
                self.assertIn("manifest.json", archive.namelist())
                self.assertNotIn("component-manifest.json", archive.namelist())
                self.assertEqual(archive.comment, b"")
                for info in archive.infolist():
                    self.assertEqual(info.date_time, FIXED_ZIP_TIMESTAMP)
                    self.assertEqual(info.create_system, FIXED_ZIP_CREATE_SYSTEM)
                    self.assertEqual(info.external_attr, FIXED_ZIP_EXTERNAL_ATTR)
                    self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
                    self.assertEqual(info.extra, b"")
                    self.assertEqual(info.comment, b"")
            skill_zip = dist / release["skillArchive"]
            with zipfile.ZipFile(skill_zip) as archive:
                names = archive.namelist()
                self.assertIn("viral-product-copy-video-generator/SKILL.md", names)
                self.assertEqual(names, sorted(names))
                self.assertEqual(archive.comment, b"")
                for info in archive.infolist():
                    self.assertEqual(info.date_time, FIXED_ZIP_TIMESTAMP)
                    self.assertEqual(info.create_system, FIXED_ZIP_CREATE_SYSTEM)
                    self.assertEqual(info.external_attr, FIXED_ZIP_EXTERNAL_ATTR)
                    self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
                    self.assertEqual(info.extra, b"")
                    self.assertEqual(info.comment, b"")
            for name in contract.NON_PAYMENT_COMMANDS:
                self.assertTrue(
                    (root / "skill/viral-product-copy-video-generator/scripts" / name).is_file()
                )

    def test_release_component_bootstrap_matches_validated_bytes_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            base_a = base / "a"
            base_b = base / "b"
            base_a.mkdir()
            base_b.mkdir()
            root_a, validated_a = create_public_repository(base_a)
            root_b, validated_b = create_public_repository(base_b)

            with mock.patch.object(build_release, "ROOT", root_a):
                dist_a = build_release.build_release(build_extension_from_component=True)
            with mock.patch.object(build_release, "ROOT", root_b):
                dist_b = build_release.build_release(build_extension_from_component=True)

            release_a = verify_distribution.read_json(root_a / "release-manifest.json")
            release_b = verify_distribution.read_json(root_b / "release-manifest.json")
            extension_a = dist_a / release_a["extensionArchive"]
            extension_b = dist_b / release_b["extensionArchive"]
            skill_a = dist_a / release_a["skillArchive"]
            skill_b = dist_b / release_b["skillArchive"]

            self.assertEqual(extension_a.read_bytes(), validated_a.read_bytes())
            self.assertEqual(extension_b.read_bytes(), validated_b.read_bytes())
            self.assertEqual(extension_a.read_bytes(), extension_b.read_bytes())
            self.assertEqual(skill_a.read_bytes(), skill_b.read_bytes())
            self.assertEqual(verify_distribution.validate(root_a), [])
            self.assertEqual(verify_distribution.validate(root_b), [])

    def test_verifier_rejects_extension_archive_metadata_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            with mock.patch.object(build_release, "ROOT", root):
                dist = build_release.build_release(validated)

            release = verify_distribution.read_json(root / "release-manifest.json")
            extension_zip = dist / release["extensionArchive"]
            with zipfile.ZipFile(extension_zip) as source:
                contents = [(name, source.read(name)) for name in source.namelist()]
            with zipfile.ZipFile(extension_zip, "w", compression=zipfile.ZIP_DEFLATED) as drifted:
                for name, data in contents:
                    drifted.writestr(name, data)
            release["artifacts"][extension_zip.name] = {
                "bytes": extension_zip.stat().st_size,
                "sha256": contract.sha256_file(extension_zip).upper(),
            }

            errors = verify_distribution.verify_archives(root, release)
            self.assertIn(
                "extension ZIP metadata is not deterministic: manifest.json",
                errors,
            )

    def test_release_rejects_duplicate_and_traversal_extension_members(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, validated = create_public_repository(base)
            extension = root / "extension" / "chrome"
            expected = [
                path
                for path in sorted(extension.rglob("*"))
                if path.is_file() and path.name != "component-manifest.json"
            ]
            duplicate = base / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicate, "w") as archive:
                    for path in expected:
                        archive.writestr(path.relative_to(extension).as_posix(), path.read_bytes())
                    archive.writestr("manifest.json", (extension / "manifest.json").read_bytes())
            traversal_secret = "github_" + "pat_" + "abcdefghijklmnopqrstuvwxyz123456"
            traversal = base / "traversal.zip"
            with zipfile.ZipFile(validated) as source, zipfile.ZipFile(traversal, "w") as archive:
                for name in source.namelist():
                    archive.writestr(name, source.read(name))
                archive.writestr(f"../{traversal_secret}", b"secret")

            with mock.patch.object(build_release, "ROOT", root):
                for candidate in (duplicate, traversal):
                    with self.subTest(candidate=candidate.name):
                        with self.assertRaises(RuntimeError) as caught:
                            build_release.copy_validated_extension(candidate, base / "out.zip")
                        self.assertNotIn(traversal_secret, str(caught.exception))

    def test_canonical_digest_covers_every_component_path_and_rejects_generated_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            release = verify_distribution.read_json(root / "release-manifest.json")
            before = verify_distribution.canonical_tree_digest(root, release)
            skill_root = root / "skill/viral-product-copy-video-generator"
            extension_root = root / "extension/chrome"
            archived_sources = [path for path in skill_root.rglob("*") if path.is_file()]
            archived_sources.extend(
                path
                for path in extension_root.rglob("*")
                if path.is_file() and path.name != "component-manifest.json"
            )
            for path in archived_sources:
                with self.subTest(path=path.relative_to(root).as_posix()):
                    original = path.read_bytes()
                    path.write_bytes(original + b"mutation")
                    self.assertNotEqual(
                        verify_distribution.canonical_tree_digest(root, release), before
                    )
                    path.write_bytes(original)

            nested_dist = root / "skill/viral-product-copy-video-generator/dist/evil.py"
            nested_dist.parent.mkdir()
            nested_dist.write_text("print('not shipped')\n", encoding="utf-8")
            self.assertNotEqual(verify_distribution.canonical_tree_digest(root, release), before)
            self.assertTrue(verify_distribution.verify_component_paths(root))
            with mock.patch.object(build_release, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "generated|unsafe"):
                    build_release.build_release(validated)

    def test_checksums_are_sorted_uppercase_and_missing_inputs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_text(root, "z.txt", "z")
            write_text(root, "a.txt", "a")
            output = root / "SHA256SUMS"
            generate_checksums.write_checksums(root, ["z.txt", "a.txt"], output)
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual([line.split("  ", 1)[1] for line in lines], ["a.txt", "z.txt"])
            self.assertTrue(
                all(re.fullmatch(r"[0-9A-F]{64}", line.split("  ", 1)[0]) for line in lines)
            )
            with self.assertRaisesRegex(FileNotFoundError, "checksum input is missing"):
                generate_checksums.write_checksums(root, ["missing.txt"], output)

    def test_checksum_inputs_and_output_are_root_contained(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "root"
            root.mkdir()
            write_text(root, "artifact.txt", "artifact\n")
            outside = write_text(base, "outside.txt", "outside\n")

            for name in (str(outside.resolve()), "../outside.txt"):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ValueError, "outside|relative|unsafe"):
                        generate_checksums.write_checksums(root, [name], root / "SHA256SUMS")
            with self.assertRaisesRegex(ValueError, "output|outside|unsafe"):
                generate_checksums.write_checksums(root, ["artifact.txt"], base / "outside.sum")
            with mock.patch.object(contract, "_source_issue", return_value="unsafe_link"):
                with self.assertRaisesRegex(ValueError, "link|outside|unsafe"):
                    generate_checksums.write_checksums(
                        root, ["artifact.txt"], root / "SHA256SUMS"
                    )
            output_parent = root / "output"
            output_parent.mkdir()
            real_is_link = contract._is_link_or_reparse

            def mocked_reparse(path: Path) -> bool:
                return path == output_parent or real_is_link(path)

            with mock.patch.object(contract, "_is_link_or_reparse", side_effect=mocked_reparse):
                with self.assertRaisesRegex(ValueError, "link|reparse|unsafe"):
                    generate_checksums.write_checksums(
                        root, ["artifact.txt"], output_parent / "SHA256SUMS"
                    )

    def test_checksum_rejects_real_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "root"
            root.mkdir()
            outside = write_text(base, "outside.txt", "outside\n")
            link = root / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"OS denied symlink creation: {exc}")
            with self.assertRaisesRegex(ValueError, "link|outside|unsafe"):
                generate_checksums.write_checksums(root, ["linked.txt"], root / "SHA256SUMS")

    def test_verification_status_lifecycle_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, validated = create_public_repository(Path(temp))
            with mock.patch.object(build_release, "ROOT", root):
                build_release.build_release(validated)
            release_path = root / "release-manifest.json"
            release = verify_distribution.read_json(release_path)
            release["verification"]["status"] = "built"
            write_json(root, "release-manifest.json", release)

            self.assertNotIn(
                "release verification status must be ready",
                verify_distribution.validate(root, check_checksums=False),
            )
            self.assertIn(
                "release verification status must be ready",
                verify_distribution.validate(root, check_checksums=True),
            )

    def test_claim_scan_accepts_disclaimers_and_checks_extension_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_text(
                root,
                "README.md",
                "Results are not guaranteed viral. This does not bypass CAPTCHA. 不保证爆款，也不绕过验证码。\n",
            )
            write_text(
                root,
                "extension/chrome/popup.html",
                "<p>It does not automatically click final publish.</p>\n",
            )
            write_text(
                root,
                "scripts/verify_distribution.py",
                "guaranteed viral; bypass captcha; 自动点击最终发布\n",
            )
            self.assertEqual(verify_distribution.verify_claim_boundaries(root), [])

            write_text(root, "docs/en/features.md", "Guaranteed viral results.\n")
            write_text(root, "docs/zh-CN/features.md", "保证爆款。\n")
            write_text(root, "extension/chrome/popup.js", "const claim = 'bypass CAPTCHA';\n")
            write_json(
                root,
                "extension/chrome/_locales/en/messages.json",
                {"claim": "Automatically click final publish"},
            )
            errors = verify_distribution.verify_claim_boundaries(root)
            self.assertTrue(any("guaranteed viral" in error for error in errors))
            self.assertTrue(any("guaranteed hit" in error for error in errors))
            self.assertTrue(any("bypass captcha" in error for error in errors))
            self.assertTrue(any("automatic final publish" in error for error in errors))

    def test_validator_errors_redact_secrets_and_checksum_lines(self) -> None:
        secrets = (
            "github_" + "pat_" + "abcdefghijklmnopqrstuvwxyz123456",
            "fc" + "-abcdefghijklmnopqrstuvwxyz123456",
            "pm_" + "live_" + "abcdefghijklmnopqrstuvwxyz123456",
            "-----BEGIN " + "PRIVATE KEY-----",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_text(root, "SHA256SUMS", secrets[0] + "\n")
            errors = verify_distribution.verify_checksums(root)
            self.assertTrue(any("line 1" in error for error in errors))
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(f"../{secrets[1]}", b"secret")
            with zipfile.ZipFile(archive_path) as archive:
                with self.assertRaises(ValueError) as caught:
                    verify_distribution._safe_zip_members(archive)
            combined = " | ".join(errors) + " | " + str(caught.exception)
            combined += " | " + verify_distribution.redact_error(" ".join(secrets))
            for secret in secrets:
                self.assertNotIn(secret, combined)


if __name__ == "__main__":
    unittest.main()
