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
            "name": "Synthetic Extension",
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
    write_json(root, f"{extension}/_locales/en/messages.json", {"label": "Safe fixture"})
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
                "status": "not_submitted",
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
    with zipfile.ZipFile(validated, "w") as archive:
        for path in sorted(extension_root.rglob("*")):
            if path.is_file() and path.name != "component-manifest.json":
                archive.writestr(path.relative_to(extension_root).as_posix(), path.read_bytes())
    return root, validated


class PublicDistributionTest(unittest.TestCase):
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
            skill_zip = dist / release["skillArchive"]
            with zipfile.ZipFile(skill_zip) as archive:
                names = archive.namelist()
                self.assertIn("viral-product-copy-video-generator/SKILL.md", names)
                self.assertEqual(names, sorted(names))
                self.assertTrue(
                    all(info.date_time == build_release.FIXED_ZIP_TIMESTAMP for info in archive.infolist())
                )
            for name in contract.NON_PAYMENT_COMMANDS:
                self.assertTrue(
                    (root / "skill/viral-product-copy-video-generator/scripts" / name).is_file()
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
