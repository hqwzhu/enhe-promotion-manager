#!/usr/bin/env python3
"""Offline tests for the guarded MediaCrawler local sidecar integration."""

from __future__ import annotations

import json
import asyncio
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPTS = Path(__file__).resolve().parent
FIXTURES = SCRIPTS / "fixtures" / "mediacrawler"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import mediacrawler_contract as contract
import mediacrawler_bootstrap as bootstrap
import mediacrawler_downstream as downstream
import mediacrawler_sidecar as sidecar
import platform_data_manager


class ContractTests(unittest.TestCase):
    salt = b"fixture-only-local-salt"

    def load_fixture(self, name: str) -> list[dict[str, object]]:
        return [json.loads(line) for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_normalizes_three_platform_content_without_sensitive_fields(self) -> None:
        expected = {
            "xiaohongshu": ("xhs-note-001", "note", 128, 36),
            "douyin": ("dy-aweme-001", "short_video", 260, 48),
            "zhihu": ("zh-content-001", "answer", 88, None),
        }
        for platform, (content_id, content_type, likes, favorites) in expected.items():
            with self.subTest(platform=platform):
                raw = self.load_fixture(f"{platform}-contents.jsonl")[0]
                record = contract.normalize_content(platform, raw, "contents.jsonl#L1", self.salt)
                self.assertEqual(record["schemaVersion"], 1)
                self.assertEqual(record["provider"], "mediacrawler")
                self.assertEqual(record["platform"], platform)
                self.assertEqual(record["contentId"], content_id)
                self.assertEqual(record["contentType"], content_type)
                self.assertEqual(record["metrics"]["likes"], likes)
                self.assertEqual(record["metrics"]["favorites"], favorites)
                self.assertRegex(record["publishedAt"], r"^2024-")
                self.assertEqual(record["evidencePath"], "contents.jsonl#L1")
                self.assertTrue(record["authorHash"])
                serialized = json.dumps(record, ensure_ascii=False).lower()
                for secret in ("xhs-secret-token", "dy-secret-token", "zh-secret-signature", "xsec_token", "mstoken", "signature"):
                    self.assertNotIn(secret, serialized)

    def test_normalizes_parent_child_comments_and_deduplicates(self) -> None:
        rows = self.load_fixture("xiaohongshu-comments.jsonl")
        records = contract.normalize_comments("xiaohongshu", rows + [rows[0]], "comments.jsonl", self.salt)
        self.assertEqual(len(records), 2)
        self.assertIsNone(records[0]["parentCommentId"])
        self.assertEqual(records[1]["parentCommentId"], records[0]["commentId"])
        self.assertEqual(records[0]["replyCount"], 1)
        self.assertEqual(records[0]["likes"], 9)
        self.assertEqual(records[0]["contentId"], "xhs-note-001")

    def test_normalizes_all_comment_platforms(self) -> None:
        for platform in ("xiaohongshu", "douyin", "zhihu"):
            with self.subTest(platform=platform):
                rows = self.load_fixture(f"{platform}-comments.jsonl")
                records = contract.normalize_comments(platform, rows, f"{platform}-comments.jsonl", self.salt)
                self.assertEqual(len(records), 2)
                self.assertEqual(records[0]["platform"], platform)
                self.assertTrue(records[0]["commentId"])
                self.assertTrue(records[0]["text"])
                self.assertTrue(records[0]["authorHash"])
                self.assertRegex(records[0]["createdAt"], r"^2024-")

    def test_sanitizer_removes_tokens_signatures_cookies_and_raw_ids_recursively(self) -> None:
        value = {
            "url": "https://www.xiaohongshu.com/explore/xhs-note-001?xsec_token=secret&xsec_source=pc_search&keep=ok",
            "Authorization": "Bearer secret",
            "nested": {
                "cookie": "a=b",
                "signature": "signed",
                "user_id": "raw-user-001",
                "safe": "retained",
            },
        }
        sanitized = contract.sanitize_mapping(value)
        text = json.dumps(sanitized, ensure_ascii=False).lower()
        for secret in ("secret", "bearer", "a=b", "signed", "raw-user-001", "xsec_token"):
            self.assertNotIn(secret, text)
        self.assertIn("retained", text)
        self.assertIn("keep=ok", text)

    def test_author_hash_is_stable_per_install_salt(self) -> None:
        first = contract.local_author_hash("upstream-creator", self.salt)
        second = contract.local_author_hash("upstream-creator", self.salt)
        other = contract.local_author_hash("upstream-creator", b"different-salt")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertEqual(len(first), 24)

    def test_unknown_platform_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported MediaCrawler platform"):
            contract.normalize_content("weibo", {}, "fixture", self.salt)


class SidecarCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.install = sidecar.SidecarInstall(self.root / "install")
        self.raw_dir = self.root / "raw"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_build_command_enforces_safe_limits_and_never_accepts_cookies(self) -> None:
        request = sidecar.CollectRequest(
            platform="xiaohongshu",
            mode="search",
            query="AI 工具",
            max_contents=20,
            max_comments=30,
            include_sub_comments=False,
            timeout_seconds=900,
        )
        command = sidecar.build_mediacrawler_command(self.install, request, self.raw_dir)
        self.assertEqual(command[0], str(self.install.python_executable))
        self.assertTrue(command[1].endswith("mediacrawler_bootstrap.py"))
        self.assertEqual(command[command.index("--checkout") + 1], str(self.install.checkout))
        self.assertIn("--", command)
        self.assertEqual(command[command.index("--platform") + 1], "xhs")
        self.assertEqual(command[command.index("--type") + 1], "search")
        self.assertEqual(command[command.index("--save_data_option") + 1], "jsonl")
        self.assertEqual(command[command.index("--max_concurrency_num") + 1], "1")
        self.assertEqual(command[command.index("--crawler_max_notes_count") + 1], "20")
        self.assertEqual(command[command.index("--max_comments_count_singlenotes") + 1], "30")
        self.assertEqual(command[command.index("--enable_ip_proxy") + 1], "false")
        self.assertEqual(command[command.index("--headless") + 1], "false")
        self.assertEqual(command[command.index("--get_sub_comment") + 1], "false")
        self.assertNotIn("--cookies", command)
        self.assertNotIn("Cookie", " ".join(command))

    def test_build_command_maps_detail_and_creator_targets(self) -> None:
        detail = sidecar.build_mediacrawler_command(
            self.install,
            sidecar.CollectRequest(platform="douyin", mode="detail", target="https://www.douyin.com/video/dy-aweme-001"),
            self.raw_dir,
        )
        creator = sidecar.build_mediacrawler_command(
            self.install,
            sidecar.CollectRequest(platform="zhihu", mode="creator", target="creator-id-001"),
            self.raw_dir,
        )
        self.assertEqual(detail[detail.index("--specified_id") + 1], "https://www.douyin.com/video/dy-aweme-001")
        self.assertEqual(creator[creator.index("--creator_id") + 1], "creator-id-001")

    def test_xiaohongshu_detail_command_uses_safe_context_without_signed_parameters(self) -> None:
        request = sidecar.CollectRequest(
            platform="xiaohongshu",
            mode="detail",
            target=(
                "https://www.xiaohongshu.com/explore/xhs-note-001"
                "?xsec_token=must-not-persist&xsec_source=pc_search"
            ),
            max_contents=1,
            max_comments=5,
            detail_context_query="AI 工具",
        )

        command = sidecar.build_mediacrawler_command(self.install, request, self.raw_dir)
        serialized = " ".join(command)

        self.assertEqual(command[command.index("--xhs-detail-query") + 1], "AI 工具")
        self.assertEqual(command[command.index("--xhs-detail-target") + 1], "xhs-note-001")
        self.assertEqual(
            command[command.index("--specified_id") + 1],
            "https://www.xiaohongshu.com/explore/xhs-note-001",
        )
        self.assertNotIn("xsec_token", serialized)
        self.assertNotIn("must-not-persist", serialized)

    def test_build_command_resolves_relative_output_path_for_upstream_working_directory(self) -> None:
        command = sidecar.build_mediacrawler_command(
            self.install,
            sidecar.CollectRequest(platform="xiaohongshu", mode="search", query="AI"),
            Path("promotion-output") / "raw",
        )

        output_path = Path(command[command.index("--save_data_path") + 1])
        self.assertTrue(output_path.is_absolute())

    def test_collect_request_rejects_invalid_modes_and_hard_cap_overrides(self) -> None:
        invalid = [
            {"platform": "weibo", "mode": "search", "query": "AI"},
            {"platform": "douyin", "mode": "feed", "query": "AI"},
            {"platform": "douyin", "mode": "search", "query": "AI", "max_contents": 21},
            {"platform": "douyin", "mode": "search", "query": "AI", "max_comments": 31},
            {"platform": "douyin", "mode": "search", "query": ""},
            {"platform": "douyin", "mode": "detail", "target": ""},
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                sidecar.CollectRequest(**kwargs)

    def test_setup_check_is_read_only_when_sidecar_is_missing(self) -> None:
        self.install.root.mkdir(parents=True)
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        report = sidecar.check_setup(self.install, find_executable=lambda _: None)
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(report["status"], "provider_unavailable")
        self.assertFalse(report["writesPerformed"])
        self.assertEqual(report["expectedCommit"], sidecar.UPSTREAM_COMMIT)


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_parser_defaults_requested_max_contents_when_omitted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mediacrawler-bootstrap-test-") as temp_dir:
            checkout = Path(temp_dir)
            (checkout / "main.py").touch()

            try:
                parsed_checkout, upstream_args, overrides = bootstrap.parse_bootstrap_args(
                    ["--checkout", str(checkout), "--", "--platform", "dy"]
                )
            except SystemExit as exc:
                self.fail(f"omitting --requested-max-contents must use the safe default: {exc}")

        self.assertEqual(parsed_checkout, checkout.resolve())
        self.assertEqual(upstream_args, ["--platform", "dy"])
        self.assertEqual(overrides.requested_max_contents, 20)

    def test_cdp_port_can_follow_current_authenticated_chrome(self) -> None:
        config = SimpleNamespace(CDP_DEBUG_PORT=9222)
        bootstrap.apply_cdp_port_override(config, "7486")
        self.assertEqual(config.CDP_DEBUG_PORT, 7486)

    def test_zhihu_creator_target_is_applied_to_upstream_config(self) -> None:
        config = SimpleNamespace(ZHIHU_CREATOR_URL_LIST=[])
        parsed = SimpleNamespace(platform="zhihu", type="creator", creator_id="https://www.zhihu.com/people/a,https://www.zhihu.com/people/b")
        bootstrap.apply_creator_override(config, parsed)
        self.assertEqual(
            config.ZHIHU_CREATOR_URL_LIST,
            ["https://www.zhihu.com/people/a", "https://www.zhihu.com/people/b"],
        )

    def test_zhihu_search_limits_upstream_results_before_comment_collection(self) -> None:
        patcher = getattr(bootstrap, "patch_zhihu_search_limit", None)
        self.assertIsNotNone(patcher)

        class FakeClient:
            async def get_note_by_keyword(self, *args: object, **kwargs: object) -> list[dict[str, str]]:
                return [{"content_id": f"answer-{index}"} for index in range(20)]

        patcher(FakeClient, 3)
        rows = asyncio.run(FakeClient().get_note_by_keyword(keyword="AI 内容生产"))
        self.assertEqual([item["content_id"] for item in rows], ["answer-0", "answer-1", "answer-2"])

    def test_xiaohongshu_detail_context_switches_to_filtered_search(self) -> None:
        config = SimpleNamespace(CRAWLER_TYPE="detail", KEYWORDS="")
        parsed = SimpleNamespace(platform="xhs", type="detail")
        apply_context = getattr(bootstrap, "apply_xiaohongshu_detail_context", None)
        patcher = getattr(bootstrap, "patch_xiaohongshu_detail_search", None)
        self.assertIsNotNone(apply_context)
        self.assertIsNotNone(patcher)

        class FakeClient:
            async def get_note_by_keyword(self, *args: object, **kwargs: object) -> dict[str, object]:
                return {
                    "has_more": True,
                    "items": [
                        {"id": "other-note", "xsec_token": "other-secret"},
                        {"id": "target-note", "xsec_token": "target-secret"},
                    ],
                }

        apply_context(config, parsed, "AI 工具", "target-note")
        patcher(FakeClient, "target-note")
        response = asyncio.run(FakeClient().get_note_by_keyword(keyword="AI 工具"))
        self.assertEqual(config.CRAWLER_TYPE, "search")
        self.assertEqual(config.KEYWORDS, "AI 工具")
        self.assertEqual(parsed.type, "search")
        self.assertEqual([item["id"] for item in response["items"]], ["target-note"])
        self.assertTrue(response["has_more"])

    def test_existing_cdp_cleanup_drops_references_without_closing_context(self) -> None:
        calls: list[str] = []

        class FakeManager:
            def __init__(self) -> None:
                self.browser_context = object()
                self.browser = object()

            async def cleanup(self, force: bool = False) -> None:
                calls.append(f"original:{force}")

        bootstrap.patch_safe_cdp_cleanup(SimpleNamespace(CDP_CONNECT_EXISTING=True), FakeManager)
        manager = FakeManager()
        asyncio.run(manager.cleanup(force=True))
        self.assertEqual(calls, [])
        self.assertIsNone(manager.browser_context)
        self.assertIsNone(manager.browser)

    def test_non_existing_cdp_mode_keeps_upstream_cleanup(self) -> None:
        calls: list[str] = []

        class FakeManager:
            async def cleanup(self, force: bool = False) -> None:
                calls.append(f"original:{force}")

        bootstrap.patch_safe_cdp_cleanup(SimpleNamespace(CDP_CONNECT_EXISTING=False), FakeManager)
        asyncio.run(FakeManager().cleanup(force=True))
        self.assertEqual(calls, ["original:True"])


class SidecarRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.install = sidecar.SidecarInstall(self.root / "install")
        self.request = sidecar.CollectRequest(platform="xiaohongshu", mode="search", query="AI 工具")
        self.run_dir = self.root / "run"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_runner_times_out_releases_lock_and_removes_raw_by_default(self) -> None:
        def timeout_executor(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(command, timeout)

        result = sidecar.run_sidecar(self.install, self.request, self.run_dir, executor=timeout_executor)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason, "timeout")
        self.assertFalse(sidecar.lock_path(self.install).exists())
        self.assertFalse((self.run_dir / "raw").exists())

    def test_runner_converts_keyboard_interrupt_to_cancelled_and_releases_resources(self) -> None:
        def cancelled_executor(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
            raise KeyboardInterrupt

        result = sidecar.run_sidecar(self.install, self.request, self.run_dir, executor=cancelled_executor)
        self.assertEqual(result.status, "cancelled")
        self.assertEqual(result.reason, "user_cancelled")
        self.assertFalse(sidecar.lock_path(self.install).exists())
        self.assertFalse((self.run_dir / "raw").exists())

    def test_runner_consumes_output_then_cleans_raw(self) -> None:
        consumed: list[Path] = []

        def success_executor(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
            raw_dir = Path(command[command.index("--save_data_path") + 1])
            output = raw_dir / "xhs" / "jsonl" / "search_contents_2026-07-13.jsonl"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text('{"note_id":"xhs-note-001"}\n', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="completed", stderr="")

        def consumer(raw_dir: Path) -> dict[str, int]:
            consumed.extend(raw_dir.rglob("*.jsonl"))
            return {"contentCount": 1, "commentCount": 0}

        result = sidecar.run_sidecar(self.install, self.request, self.run_dir, executor=success_executor, raw_consumer=consumer)
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.payload["contentCount"], 1)
        self.assertEqual(len(consumed), 1)
        self.assertFalse((self.run_dir / "raw").exists())

    def test_runner_keeps_raw_only_when_explicitly_requested(self) -> None:
        def success_executor(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
            raw_dir = Path(command[command.index("--save_data_path") + 1])
            output = raw_dir / "xhs" / "jsonl" / "search_contents_2026-07-13.jsonl"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text('{"note_id":"xhs-note-001"}\n', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="completed", stderr="")

        result = sidecar.run_sidecar(self.install, self.request, self.run_dir, executor=success_executor, keep_raw=True)
        self.assertTrue((self.run_dir / "raw").exists())
        self.assertTrue(result.keep_raw)
        self.assertIn("sensitive", result.warning.lower())

    def test_runner_classifies_user_action_and_platform_states(self) -> None:
        cases = {
            "Please login with QR code": "waiting_login",
            "Captcha slider verification required": "manual_verification_required",
            "Account risk control blocked this request": "blocked_by_platform",
        }
        for index, (stderr, expected) in enumerate(cases.items(), start=1):
            with self.subTest(stderr=stderr):
                run_dir = self.root / f"run-{index}"

                def failed_executor(command: list[str], cwd: Path, timeout: int, message: str = stderr) -> subprocess.CompletedProcess[str]:
                    return subprocess.CompletedProcess(command, 1, stdout="", stderr=message)

                result = sidecar.run_sidecar(self.install, self.request, run_dir, executor=failed_executor)
                self.assertEqual(result.status, expected)
                self.assertNotIn("Cookie", result.stderr_tail)

    def test_safe_tail_redacts_quoted_fields_and_signed_url_parameters(self) -> None:
        value = (
            "{'xsec_token': 'xhs-secret', \"msToken\": \"ms-secret\", "
            "'url': 'https://example.test/video.mp4?sign=url-secret&t=123'}"
        )

        sanitized = sidecar.safe_tail(value)

        for secret in ("xhs-secret", "ms-secret", "url-secret"):
            self.assertNotIn(secret, sanitized)
        self.assertIn("REDACTED", sanitized)

    def test_runner_reports_no_results_for_success_without_jsonl_rows(self) -> None:
        def empty_executor(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="completed", stderr="")

        result = sidecar.run_sidecar(self.install, self.request, self.run_dir, executor=empty_executor)
        self.assertEqual(result.status, "no_results")

    def test_runner_retries_one_transient_network_failure(self) -> None:
        calls = 0

        def flaky_executor(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
            nonlocal calls
            calls += 1
            if calls == 1:
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="temporary network connection reset")
            raw_dir = Path(command[command.index("--save_data_path") + 1])
            output = raw_dir / "xhs" / "jsonl" / "search_contents_2026-07-13.jsonl"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text('{"note_id":"xhs-note-001"}\n', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="completed", stderr="")

        result = sidecar.run_sidecar(self.install, self.request, self.run_dir, executor=flaky_executor)
        self.assertEqual(calls, 2)
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.retry_count, 1)

    def test_execute_process_decodes_upstream_output_as_utf8(self) -> None:
        completed = subprocess.CompletedProcess(["python"], 0, stdout="中文输出", stderr="")
        with mock.patch.object(sidecar.subprocess, "run", return_value=completed) as run:
            result = sidecar.execute_process(["python", "main.py"], self.root, 30)

        self.assertIs(result, completed)
        run.assert_called_once_with(
            ["python", "main.py"],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )


class SidecarInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.install = sidecar.SidecarInstall(self.root / "install")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_explicit_install_uses_staging_pins_commit_and_writes_local_salt(self) -> None:
        calls: list[list[str]] = []

        def find_executable(name: str) -> str | None:
            return {"git": "git", "uv": "uv", "chrome": "chrome"}.get(name)

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[:2] == ["git", "clone"]:
                checkout = Path(command[-1])
                (checkout / ".git").mkdir(parents=True)
                (checkout / "config").mkdir()
                (checkout / "main.py").write_text("print('fixture')\n", encoding="utf-8")
                (checkout / "config" / "base_config.py").write_text(
                    "ENABLE_CDP_MODE = True\nCDP_CONNECT_EXISTING = True\nENABLE_GET_MEIDAS = False\nCRAWLER_MAX_SLEEP_SEC = 2\n",
                    encoding="utf-8",
                )
            if command and command[0] == "uv":
                project = Path(command[command.index("--project") + 1])
                python = project / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                python.parent.mkdir(parents=True, exist_ok=True)
                python.write_text("fixture", encoding="utf-8")
            if command[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(command, 0, stdout=sidecar.UPSTREAM_COMMIT + "\n", stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        report = sidecar.install_sidecar(
            self.install,
            find_executable=find_executable,
            command_runner=runner,
            random_bytes=lambda size: b"s" * size,
        )
        self.assertEqual(report["status"], "ready")
        self.assertTrue(report["checks"]["manifest"])
        self.assertTrue(report["checks"]["identitySalt"])
        self.assertTrue(report["checks"]["bootstrap"])
        self.assertTrue(self.install.manifest_path.exists())
        self.assertEqual(self.install.identity_salt_path.read_bytes(), b"s" * 32)
        manifest = json.loads(self.install.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["upstreamCommit"], sidecar.UPSTREAM_COMMIT)
        self.assertTrue(any(command[:2] == ["git", "clone"] for command in calls))
        self.assertTrue(any(command and command[0] == "uv" for command in calls))

    def test_failed_install_removes_staging_without_replacing_checkout(self) -> None:
        def find_executable(name: str) -> str | None:
            return {"git": "git", "uv": "uv", "chrome": "chrome"}.get(name)

        def failed_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="network failed")

        report = sidecar.install_sidecar(self.install, find_executable=find_executable, command_runner=failed_runner)
        self.assertEqual(report["status"], "provider_unavailable")
        self.assertFalse(self.install.checkout.exists())
        self.assertFalse(self.install.manifest_path.exists())
        self.assertEqual(list(self.install.root.glob("installing-*")), [])


class NormalizationLimitTests(unittest.TestCase):
    salt = b"fixture-only-local-salt"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def load_fixture(self, name: str) -> list[dict[str, object]]:
        return [json.loads(line) for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_enforces_requested_content_limit_before_persistence(self) -> None:
        template = self.load_fixture("xiaohongshu-contents.jsonl")[0]
        rows = [{**template, "note_id": f"xhs-note-{index:03d}"} for index in range(20)]

        payload = platform_data_manager.normalize_rows(
            "xiaohongshu",
            rows,
            [],
            self.run_dir,
            self.salt,
            content_limit=1,
            comments_per_content_limit=0,
        )

        self.assertEqual(len(payload["contents"]), 1)
        self.assertEqual(payload["counts"]["sourceContents"], 20)
        self.assertEqual(payload["counts"]["normalizedContents"], 1)
        self.assertEqual(payload["counts"]["limitedContents"], 19)
        self.assertEqual(len((self.run_dir / "contents.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_enforces_requested_comment_limit_per_kept_content(self) -> None:
        content = self.load_fixture("xiaohongshu-contents.jsonl")[0]
        comment = self.load_fixture("xiaohongshu-comments.jsonl")[0]
        comments = [
            {**comment, "comment_id": f"xhs-comment-{index:03d}", "note_id": content["note_id"]}
            for index in range(3)
        ]

        payload = platform_data_manager.normalize_rows(
            "xiaohongshu",
            [content],
            comments,
            self.run_dir,
            self.salt,
            content_limit=1,
            comments_per_content_limit=1,
        )

        self.assertEqual(len(payload["comments"]), 1)
        self.assertEqual(payload["counts"]["sourceComments"], 3)
        self.assertEqual(payload["counts"]["normalizedComments"], 1)
        self.assertEqual(payload["counts"]["limitedComments"], 2)
        self.assertEqual(len((self.run_dir / "comments.jsonl").read_text(encoding="utf-8").splitlines()), 1)


class DownstreamTests(unittest.TestCase):
    salt = b"fixture-only-local-salt"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out_dir = self.root / "promotion-output"
        self.run_dir = self.out_dir / "reports" / "promotion-manager" / "platform-data" / "mediacrawler" / "run-fixture"
        self.run_dir.mkdir(parents=True)
        self.contents = []
        self.comments = []
        for platform in ("xiaohongshu", "douyin", "zhihu"):
            content_rows = self.load_fixture(f"{platform}-contents.jsonl")
            comment_rows = self.load_fixture(f"{platform}-comments.jsonl")
            self.contents.extend(
                contract.normalize_content(platform, row, f"contents.jsonl#L{index}", self.salt)
                for index, row in enumerate(content_rows, start=1)
            )
            self.comments.extend(contract.normalize_comments(platform, comment_rows, "comments.jsonl", self.salt))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def load_fixture(self, name: str) -> list[dict[str, object]]:
        return [json.loads(line) for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_writes_viral_creator_comment_and_creator_jsonl_outputs(self) -> None:
        artifacts = downstream.write_downstream_artifacts(
            self.out_dir,
            self.run_dir,
            self.contents,
            self.comments,
            published_items=[],
        )
        for key in ("viralContentLibrary", "creatorLeaderboard", "commentEvidence", "creatorRecords", "ownedMetrics"):
            self.assertTrue(Path(artifacts[key]).exists(), key)

        viral = json.loads(Path(artifacts["viralContentLibrary"]).read_text(encoding="utf-8"))
        creators = json.loads(Path(artifacts["creatorLeaderboard"]).read_text(encoding="utf-8"))
        comments = json.loads(Path(artifacts["commentEvidence"]).read_text(encoding="utf-8"))
        self.assertEqual(len(viral["materials"]), 3)
        self.assertEqual(len(creators["creators"]), 3)
        self.assertEqual(comments["summary"]["commentCount"], 6)
        child = next(item for item in comments["comments"] if item["commentId"] == "xhs-comment-002")
        self.assertEqual(child["parentCommentId"], "xhs-comment-001")

    def test_only_exact_registered_content_id_enters_owned_metrics(self) -> None:
        published = [
            {
                "platform": "douyin",
                "contentId": "dy-aweme-001",
                "publishedUrl": "https://www.douyin.com/video/dy-aweme-001",
                "publishStatus": "published",
                "title": "一分钟完成产品短视频脚本",
            }
        ]
        competitor = {
            **self.contents[1],
            "contentId": "competitor-999",
            "sourceUrl": "https://www.douyin.com/video/competitor-999",
            "title": self.contents[1]["title"],
            "authorHash": self.contents[1]["authorHash"],
            "sourceKeyword": self.contents[1]["sourceKeyword"],
        }
        matched = downstream.match_owned_metrics([self.contents[1], competitor], published)
        self.assertEqual([item["contentId"] for item in matched], ["dy-aweme-001"])

    def test_similar_text_title_author_and_keyword_never_match(self) -> None:
        content = self.contents[0]
        published = [
            {
                "platform": "xiaohongshu",
                "contentId": "different-id",
                "publishedUrl": "https://www.xiaohongshu.com/explore/different-id",
                "publishStatus": "published",
                "title": content["title"],
                "authorHash": content["authorHash"],
                "sourceKeyword": content["sourceKeyword"],
            }
        ]
        self.assertEqual(downstream.match_owned_metrics([content], published), [])

    def test_url_fallback_requires_registry_item_without_content_id_and_exact_canonical_url(self) -> None:
        content = {
            **self.contents[1],
            "contentId": "capture-id-not-registered",
            "sourceUrl": "https://www.douyin.com/video/url-only-001?utm_medium=capture",
        }
        registered = {
            "platform": "douyin",
            "contentId": "",
            "publishedUrl": "https://www.douyin.com/video/url-only-001?utm_source=registry",
            "publishStatus": "published",
        }
        matched = downstream.match_owned_metrics([content], [registered])
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["publishedUrl"], registered["publishedUrl"])

    def test_unpublished_registry_rows_never_receive_metrics(self) -> None:
        content = self.contents[2]
        published = [{"platform": "zhihu", "contentId": content["contentId"], "publishStatus": "queued"}]
        self.assertEqual(downstream.match_owned_metrics([content], published), [])


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_main(self, argv: list[str]) -> dict[str, object]:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return platform_data_manager.main(argv)

    def test_collect_parser_applies_safe_defaults_and_rejects_cookie_arguments(self) -> None:
        args = platform_data_manager.parse_args(
            ["collect", "--platform", "xiaohongshu", "--mode", "search", "--query", "AI 工具"]
        )
        self.assertEqual(args.max_contents, 20)
        self.assertEqual(args.max_comments, 30)
        self.assertEqual(args.timeout_seconds, 900)
        self.assertFalse(args.include_sub_comments)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            platform_data_manager.parse_args(
                [
                    "collect",
                    "--platform",
                    "xiaohongshu",
                    "--mode",
                    "search",
                    "--query",
                    "AI",
                    "--cookies",
                    "secret",
                ]
            )

    def test_setup_check_is_read_only_through_cli(self) -> None:
        sidecar_root = self.root / "sidecar"
        sidecar_root.mkdir()
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        report = self.run_main(["setup", "--check", "--sidecar-root", str(sidecar_root)])
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(report["status"], "provider_unavailable")
        self.assertFalse(report["writesPerformed"])

    def test_xiaohongshu_detail_recovers_query_from_prior_normalized_output(self) -> None:
        out_dir = self.root / "promotion-output"
        prior_run = out_dir / "reports" / "promotion-manager" / "platform-data" / "mediacrawler" / "prior-search"
        downstream.write_jsonl(
            prior_run / "contents.jsonl",
            [
                {
                    "platform": "xiaohongshu",
                    "contentId": "target-note",
                    "sourceUrl": "https://www.xiaohongshu.com/explore/target-note",
                    "sourceKeyword": "AI 工具",
                }
            ],
        )
        resolver = getattr(platform_data_manager, "resolve_xiaohongshu_detail_query", None)
        self.assertIsNotNone(resolver)

        query = resolver(
            out_dir,
            "https://www.xiaohongshu.com/explore/target-note?xsec_token=must-not-persist&xsec_source=pc_search",
        )

        self.assertEqual(query, "AI 工具")

    def test_offline_fixture_collect_writes_manifest_normalized_files_and_downstream_artifacts(self) -> None:
        out_dir = self.root / "promotion-output"
        report = self.run_main(
            [
                "collect",
                "--platform",
                "xiaohongshu",
                "--mode",
                "search",
                "--query",
                "AI 工具",
                "--fixture-dir",
                str(FIXTURES),
                "--out-dir",
                str(out_dir),
            ]
        )
        run_dir = Path(report["runDir"])
        manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(manifest["captureMode"], "fixture")
        self.assertEqual(manifest["counts"]["normalizedContents"], 1)
        self.assertEqual(manifest["counts"]["normalizedComments"], 2)
        self.assertTrue((run_dir / "contents.jsonl").exists())
        self.assertTrue((run_dir / "comments.jsonl").exists())
        self.assertTrue((run_dir / "creators.jsonl").exists())
        self.assertFalse((run_dir / "raw").exists())
        self.assertTrue(Path(manifest["artifacts"]["viralContentLibrary"]).exists())
        self.assertTrue(Path(manifest["artifacts"]["commentEvidence"]).exists())

    def test_fixture_manifest_and_outputs_do_not_contain_sensitive_markers(self) -> None:
        out_dir = self.root / "promotion-output"
        report = self.run_main(
            [
                "collect",
                "--platform",
                "douyin",
                "--mode",
                "search",
                "--query",
                "短视频脚本",
                "--fixture-dir",
                str(FIXTURES),
                "--out-dir",
                str(out_dir),
            ]
        )
        run_dir = Path(report["runDir"])
        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in run_dir.rglob("*")
            if path.is_file()
        ).lower()
        for marker in ("dy-secret-token", "dy-signature", "bearer secret", "raw-user-001", "a=b"):
            self.assertNotIn(marker, combined)

    def test_real_collect_degrades_without_installed_sidecar(self) -> None:
        out_dir = self.root / "promotion-output"
        report = self.run_main(
            [
                "collect",
                "--platform",
                "zhihu",
                "--mode",
                "search",
                "--query",
                "内容生产",
                "--sidecar-root",
                str(self.root / "missing-sidecar"),
                "--out-dir",
                str(out_dir),
            ]
        )
        self.assertEqual(report["status"], "provider_unavailable")
        self.assertIn("existing Firecrawl", " ".join(report["nextActions"]))

    def test_promotion_manager_delegates_platform_data_before_product_arguments(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "promotion_manager.py"),
                "platform-data",
                "setup",
                "--check",
                "--sidecar-root",
                str(self.root / "sidecar"),
            ],
            cwd=SCRIPTS.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "provider_unavailable")
        self.assertFalse(report["writesPerformed"])


class ExtensionTests(unittest.TestCase):
    def test_extension_generates_sidecar_command_without_new_high_privilege_permissions(self) -> None:
        root = SCRIPTS.parent
        manifest = json.loads((root / "browser-extension" / "manifest.json").read_text(encoding="utf-8"))
        html = (root / "browser-extension" / "popup.html").read_text(encoding="utf-8")
        javascript = (root / "browser-extension" / "popup.js").read_text(encoding="utf-8")
        self.assertIn('value="platform_data_collect"', html)
        self.assertIn('id="platformDataPlatform"', html)
        self.assertIn('id="platformDataMode"', html)
        self.assertIn('id="platformDataTarget"', html)
        self.assertIn('id="platformDataSubComments"', html)
        self.assertIn("generatePlatformDataCommand", javascript)
        self.assertIn(r"scripts\\promotion_manager.py platform-data collect", javascript)
        self.assertNotIn("nativeMessaging", manifest.get("permissions", []))
        self.assertNotIn("cookies", [str(value).lower() for value in manifest.get("permissions", [])])
        self.assertFalse(any("localhost" in value.lower() for value in manifest.get("host_permissions", [])))


class AcceptanceTests(unittest.TestCase):
    def test_three_platform_offline_runs_are_normalized_redacted_and_raw_free(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp) / "promotion-output"
            total_contents = 0
            total_comments = 0
            for platform, query in (
                ("xiaohongshu", "AI 工具"),
                ("douyin", "短视频脚本"),
                ("zhihu", "内容生产"),
            ):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    report = platform_data_manager.main(
                        [
                            "collect",
                            "--platform",
                            platform,
                            "--mode",
                            "search",
                            "--query",
                            query,
                            "--fixture-dir",
                            str(FIXTURES),
                            "--out-dir",
                            str(out_dir),
                        ]
                    )
                run_dir = Path(report["runDir"])
                manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["status"], "ready")
                total_contents += manifest["counts"]["normalizedContents"]
                total_comments += manifest["counts"]["normalizedComments"]
                self.assertFalse((run_dir / "raw").exists())
                combined = "\n".join(
                    path.read_text(encoding="utf-8", errors="replace")
                    for path in run_dir.rglob("*")
                    if path.is_file()
                ).lower()
                for value in ("xhs-secret-token", "dy-secret-token", "dy-signature", "zh-secret-signature"):
                    self.assertNotIn(value, combined)
            self.assertEqual(total_contents, 3)
            self.assertEqual(total_comments, 6)

    def test_operations_guide_and_gitignore_cover_the_local_boundary(self) -> None:
        root = SCRIPTS.parent
        guide = (root / "docs" / "mediacrawler-sidecar.md").read_text(encoding="utf-8")
        ignore = (root / ".gitignore").read_text(encoding="utf-8")
        for value in (
            "platform-data setup --check",
            "platform-data setup --install",
            sidecar.UPSTREAM_COMMIT,
            "waiting_login",
            "manual_verification_required",
            "blocked_by_platform",
            "--keep-raw",
            "Ctrl+C",
        ):
            self.assertIn(value, guide)
        self.assertIn("promotion-output/", ignore)


if __name__ == "__main__":
    unittest.main()
