#!/usr/bin/env python3
"""Regression tests for the viral product promotion skill script."""

from __future__ import annotations

import importlib.util
import argparse
import hashlib
import json
import http.server
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import distribution_contract as release_contract


SCRIPT = ROOT / "scripts" / "promotion_manager.py"
PRODUCT_INTAKE = ROOT / "scripts" / "product_intake.py"
BROWSER_SNAPSHOT = ROOT / "scripts" / "browser_snapshot.py"
BROWSER_VIDEO_SAMPLER = ROOT / "scripts" / "browser_video_sampler.py"
WEB_DATA_PROVIDER = ROOT / "scripts" / "web_data_provider.py"
PRODUCT_URL_READER = ROOT / "scripts" / "product_url_reader.py"
PRODUCT_URL_DISCOVERY = ROOT / "scripts" / "product_url_discovery.py"
PRODUCT_BATCH_RUNNER = ROOT / "scripts" / "product_batch_runner.py"
RENDER_VIDEO = ROOT / "scripts" / "render_video.py"
MEDIA_ASSET_PACK = ROOT / "scripts" / "media_asset_pack.py"
COMPETITOR_INTAKE = ROOT / "scripts" / "competitor_intake.py"
COMPETITOR_DISCOVERY = ROOT / "scripts" / "competitor_discovery.py"
COMPETITOR_COLLECTOR = ROOT / "scripts" / "competitor_collector.py"
METRICS_INTAKE = ROOT / "scripts" / "metrics_intake.py"
METRICS_RECOVERY = ROOT / "scripts" / "metrics_recovery.py"
NEXT_ROUND_OPTIMIZER = ROOT / "scripts" / "next_round_optimizer.py"
BUSINESS_ATTRIBUTION = ROOT / "scripts" / "business_attribution.py"
PUBLISHED_ITEMS = ROOT / "scripts" / "published_items.py"
PUBLISH_EXECUTOR = ROOT / "scripts" / "publish_executor.py"
PUBLISH_QUEUE = ROOT / "scripts" / "publish_queue.py"
PUBLISH_READINESS = ROOT / "scripts" / "publish_readiness_runner.py"
PUBLISH_SETUP_ASSISTANT = ROOT / "scripts" / "publish_setup_assistant.py"
REAL_EVIDENCE_SETUP = ROOT / "scripts" / "real_evidence_setup.py"
REAL_EVIDENCE_INBOX_SETUP = ROOT / "scripts" / "real_evidence_inbox_setup.py"
REAL_EVIDENCE_INBOX = ROOT / "scripts" / "real_evidence_inbox.py"
SYNTHETIC_EVIDENCE_GENERATOR = ROOT / "scripts" / "synthetic_evidence_generator.py"
BROWSER_PUBLISH_ASSISTANT = ROOT / "scripts" / "browser_publish_assistant.py"
BROWSER_PUBLISH_FORM_FILL = ROOT / "scripts" / "browser_publish_form_fill.py"
BROWSER_PUBLISH_SESSION = ROOT / "scripts" / "browser_publish_session.py"
PUBLISH_URL_CAPTURE = ROOT / "scripts" / "publish_url_capture.py"
POST_PUBLISH_METRICS_CAPTURE = ROOT / "scripts" / "post_publish_metrics_capture.py"
COMMENT_EVIDENCE_CAPTURE = ROOT / "scripts" / "comment_evidence_capture.py"
PERFORMANCE_MONITOR = ROOT / "scripts" / "performance_monitor.py"
LAUNCH_UNLOCK_PACK = ROOT / "scripts" / "launch_unlock_pack.py"
YOUTUBE_OAUTH_PUBLISH = ROOT / "scripts" / "youtube_oauth_publish.py"
YOUTUBE_CREDENTIAL_CHECK = ROOT / "scripts" / "youtube_credential_check.py"
RUN_WORKFLOW = ROOT / "scripts" / "run_promotion_workflow.py"
PROMOTION_CYCLE_RUNNER = ROOT / "scripts" / "promotion_cycle_runner.py"
REAL_RUN_PLAYBOOK = ROOT / "scripts" / "real_run_playbook.py"
SKILL_ENTRY = ROOT / "scripts" / "skill_entry.py"
AUTOMATION_SCHEDULER = ROOT / "scripts" / "automation_scheduler.py"
PLATFORM_SEARCH_CAPTURE = ROOT / "scripts" / "platform_search_capture.py"
PLATFORM_SEARCH_BROWSER = ROOT / "scripts" / "platform_search_browser.py"
VIRAL_CONTENT_LIBRARY = ROOT / "scripts" / "viral_content_library.py"
VIRAL_EVIDENCE_INBOX_SETUP = ROOT / "scripts" / "viral_evidence_inbox_setup.py"
VIRAL_EVIDENCE_INBOX = ROOT / "scripts" / "viral_evidence_inbox.py"
FOLLOW_UP_CAPTURE_RUNNER = ROOT / "scripts" / "follow_up_capture_runner.py"
COMPETITOR_CONTENT_ENHANCER = ROOT / "scripts" / "competitor_content_enhancer.py"
CREATOR_LEADERBOARD = ROOT / "scripts" / "creator_leaderboard.py"
CREATOR_FOLLOW_UP_RUNNER = ROOT / "scripts" / "creator_follow_up_runner.py"
FINAL_CAPABILITY_AUDIT = ROOT / "scripts" / "final_capability_audit.py"
FINAL_CAPABILITY_RUNNER = ROOT / "scripts" / "final_capability_runner.py"
FINAL_CAPABILITY_READINESS = ROOT / "scripts" / "final_capability_readiness.py"
SELF_EVOLUTION_AUDIT = ROOT / "scripts" / "self_evolution_audit.py"
BILLING_CONTRACT_SIMULATOR = ROOT / "scripts" / "billing_contract_simulator.py"
PLATFORM_ACCESS_AUDIT = ROOT / "scripts" / "platform_access_audit.py"
PLATFORM_CAPABILITIES = ROOT / "scripts" / "platform_capabilities.py"
COMPLETION_ROADMAP = ROOT / "scripts" / "completion_roadmap.py"
OPERATOR_ACTION_CHECKLIST = ROOT / "scripts" / "operator_action_checklist.py"
VIRAL_DISCOVERY_RUNNER = ROOT / "scripts" / "viral_discovery_runner.py"
MULTI_QUERY_VIRAL_DISCOVERY = ROOT / "scripts" / "multi_query_viral_discovery.py"
PACKAGE_BROWSER_EXTENSION = ROOT / "scripts" / "package_browser_extension.py"
README = ROOT / "README.md"
DOCS = ROOT / "docs"
BROWSER_EXTENSION = ROOT / "browser-extension"
LICENSE_SERVICE = ROOT / "backend" / "license-service"


def load_script_module(path: Path):
    module_name = f"_promotion_manager_test_{path.stem}_{os.getpid()}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    original_sys_path = sys.path.copy()
    script_dir = str(path.resolve().parent)
    sys.path[:] = [script_dir, *(entry for entry in sys.path if entry != script_dir)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_sys_path
    return module


def write_minimal_xlsx(path: Path, rows: list[list[Any]]) -> None:
    def escape(value: Any) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def column_name(index: int) -> str:
        name = ""
        index += 1
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            ref = f"{column_name(col_index)}{row_index}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        workbook.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        workbook.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def playwright_chromium_available() -> bool:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from playwright.sync_api import sync_playwright\n"
                "p=sync_playwright().start()\n"
                "b=p.chromium.launch(headless=True)\n"
                "b.close()\n"
                "p.stop()\n"
            ),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


class PromotionManagerScriptTest(unittest.TestCase):
    def test_load_script_module_prefers_script_dir_and_restores_sys_path(self) -> None:
        sibling_name = f"_promotion_manager_sibling_{os.getpid()}_{id(self)}"
        self.assertNotIn(sibling_name, sys.modules)

        with tempfile.TemporaryDirectory(prefix="load-script-module-test-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            script_dir = (temp_dir / "script").resolve()
            shadow_dir = (temp_dir / "shadow").resolve()
            script_dir.mkdir()
            shadow_dir.mkdir()
            target_path = script_dir / "target.py"
            (script_dir / f"{sibling_name}.py").write_text("VALUE = 'local'\n", encoding="utf-8")
            (shadow_dir / f"{sibling_name}.py").write_text("VALUE = 'shadow'\n", encoding="utf-8")
            target_path.write_text(
                f"from {sibling_name} import VALUE\n"
                "import sys\n"
                f"SCRIPT_DIR_FIRST = sys.path[0] == {str(script_dir)!r}\n"
                f"SCRIPT_DIR_COUNT = sys.path.count({str(script_dir)!r})\n",
                encoding="utf-8",
            )
            original_sys_path = sys.path.copy()
            load_sys_path = [str(shadow_dir), *original_sys_path, str(script_dir), str(script_dir)]
            sys.path[:] = load_sys_path

            try:
                module = load_script_module(target_path)
                self.assertEqual(module.VALUE, "local")
                self.assertTrue(module.SCRIPT_DIR_FIRST)
                self.assertEqual(module.SCRIPT_DIR_COUNT, 1)
                self.assertEqual(sys.path, load_sys_path)
            finally:
                sys.path[:] = original_sys_path
                sys.modules.pop(sibling_name, None)

    def test_load_script_module_restores_sys_path_after_execution_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="load-script-module-error-test-") as temp_dir_name:
            script_dir = Path(temp_dir_name).resolve()
            target_path = script_dir / "target.py"
            target_path.write_text(
                "import sys\n"
                f"if sys.path[0] != {str(script_dir)!r} or sys.path.count({str(script_dir)!r}) != 1:\n"
                "    raise AssertionError('script dir was not normalized')\n"
                "sys.path.insert(0, 'target-mutated-path')\n"
                "raise RuntimeError('target failed')\n",
                encoding="utf-8",
            )
            original_sys_path = sys.path.copy()
            load_sys_path = ["before-load", str(script_dir), *original_sys_path, str(script_dir)]
            sys.path[:] = load_sys_path

            try:
                with self.assertRaisesRegex(RuntimeError, "target failed"):
                    load_script_module(target_path)
                self.assertEqual(sys.path, load_sys_path)
            finally:
                sys.path[:] = original_sys_path

    def run_all(self) -> Path:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-manager-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "all",
                "--product-name",
                "AI Prompt Kit",
                "--product-url",
                "https://www.enhe-tech.com.cn/validation/ai-prompt-kit",
                "--audience",
                "AI tool operators, creators, ecommerce sellers",
                "--value-proposition",
                "Prompt templates for product copy, SEO content, and video scripts",
                "--goal",
                "leads",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        return out_dir

    def load_json(self, out_dir: Path, relative: str):
        return json.loads((out_dir / relative).read_text(encoding="utf-8"))

    def test_full_pipeline_outputs_required_reports(self) -> None:
        out_dir = self.run_all()
        required = [
            "docs/promotion-manager/01-platform-publishing-feasibility.md",
            "docs/promotion-manager/02-github-reference-projects.md",
            "docs/promotion-manager/03-platform-risk-matrix.md",
            "docs/promotion-manager/04-self-learning-notes.md",
            "docs/promotion-manager/05-browser-extension-roadmap.md",
            "docs/promotion-manager/06-saas-product-roadmap.md",
            "reports/promotion-manager/research/platform-publishing-feasibility.json",
            "reports/promotion-manager/research/github-reference-projects.json",
            "reports/promotion-manager/content-plans/ai-prompt-kit-content-plan.json",
            "reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json",
            "reports/promotion-manager/generated-content/ai-prompt-kit-content-review.json",
            "reports/promotion-manager/cheat-review/ai-prompt-kit-cheat-review-pack.json",
            "reports/promotion-manager/publish-packs/ai-prompt-kit-publish-pack.json",
            "reports/promotion-manager/publish-results/ai-prompt-kit-publish-result-input.json",
            "reports/promotion-manager/retrospectives/ai-prompt-kit-retrospective.json",
        ]
        for relative in required:
            self.assertTrue((out_dir / relative).exists(), relative)

    def test_platform_capability_safety_defaults(self) -> None:
        out_dir = self.run_all()
        capabilities = self.load_json(out_dir, "reports/promotion-manager/publish-packs/platform-publish-capability-map.json")
        by_platform = {item["platform"]: item for item in capabilities}
        self.assertEqual(by_platform["youtube"]["recommendedMode"], "official_api_publish")
        self.assertEqual(by_platform["github"]["recommendedMode"], "official_api_publish")
        self.assertTrue(by_platform["youtube"]["approvalRequired"])
        self.assertTrue(by_platform["github"]["approvalRequired"])
        self.assertEqual(by_platform["xiaohongshu"]["recommendedMode"], "manual_publish_required")
        self.assertFalse(by_platform["xiaohongshu"]["supportsDirectPublish"])
        self.assertEqual(by_platform["zhihu"]["recommendedMode"], "manual_publish_required")
        self.assertFalse(by_platform["zhihu"]["supportsDirectPublish"])
        self.assertEqual(by_platform["douyin"]["recommendedMode"], "browser_assisted_publish")

    def test_generated_content_counts_and_cta(self) -> None:
        out_dir = self.run_all()
        content = self.load_json(out_dir, "reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json")
        self.assertEqual(len(content["youtube"]["formats"]["longVideoTitles"]), 10)
        self.assertEqual(len(content["youtube"]["formats"]["shortsTitles"]), 10)
        self.assertEqual(len(content["xiaohongshu"]["formats"]["noteTitles"]), 20)
        self.assertEqual(len(content["xiaohongshu"]["formats"]["notes"]), 5)
        self.assertEqual(len(content["douyin"]["formats"]["voiceoverTitles"]), 20)
        self.assertEqual(len(content["douyin"]["formats"]["thirtySecondScripts"]), 5)
        for item in content.values():
            self.assertTrue(item["cta"])

    def test_review_publish_result_and_retrospective_guardrails(self) -> None:
        out_dir = self.run_all()
        review = self.load_json(out_dir, "reports/promotion-manager/generated-content/ai-prompt-kit-content-review.json")
        self.assertTrue(all("complianceScore" in item for item in review))
        self.assertTrue(all(item["cheatOnContent"]["status"] == "cheat_review_pack_created" for item in review))
        self.assertTrue(all(Path(item["cheatOnContent"]["draftPath"]).exists() for item in review))
        self.assertTrue(all("cheat-score" in item["cheatOnContent"]["reviewPrompt"] for item in review))
        cheat_pack = self.load_json(out_dir, "reports/promotion-manager/cheat-review/ai-prompt-kit-cheat-review-pack.json")
        self.assertEqual(cheat_pack["status"], "cheat_review_pack_created")
        self.assertFalse(cheat_pack["safety"]["writesPredictionLogs"])
        self.assertEqual(len(cheat_pack["drafts"]), len(review))

        publish_pack = self.load_json(out_dir, "reports/promotion-manager/publish-packs/ai-prompt-kit-publish-pack.json")
        self.assertTrue(all(item["approvalRequired"] for item in publish_pack))
        self.assertTrue(all(item["publishSteps"] for item in publish_pack))
        self.assertTrue(all(item["trackingPlan"]["utm"]["utm_content"] for item in publish_pack))
        self.assertTrue(all("utm_campaign=" in item["trackingPlan"]["trackedUrl"] for item in publish_pack))
        for item in publish_pack:
            self.assertTrue(item["viralTitle"])
            self.assertTrue(item["copy"])
            self.assertIsInstance(item["tags"], list)
            self.assertTrue(item["tags"])
            self.assertTrue(item["firstBatch"]["pinnedComment"])
            self.assertIn("video", item)
            self.assertIn("cover", item)
            self.assertIn("detailImages", item)
        self.assertIn("utm_content", publish_pack[0]["trackingFields"])
        warnings = " ".join(" ".join(item["warnings"]) for item in publish_pack)
        self.assertIn("No cookie/token/password storage", warnings)
        self.assertIn("No captcha bypass", warnings)

        results = self.load_json(out_dir, "reports/promotion-manager/publish-results/ai-prompt-kit-publish-result-input.json")
        self.assertTrue(all(item["published"] is False for item in results))
        self.assertTrue(all(item["views"] is None and item["revenue"] is None for item in results))

        retrospective = self.load_json(out_dir, "reports/promotion-manager/retrospectives/ai-prompt-kit-retrospective.json")
        self.assertEqual(retrospective["status"], "waiting_real_data")
        self.assertEqual(retrospective["publishedItems"], [])

    def test_media_asset_pack_generates_required_assets_and_updates_publish_pack(self) -> None:
        out_dir = self.run_all()
        content_path = out_dir / "reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json"
        publish_pack_path = out_dir / "reports/promotion-manager/publish-packs/ai-prompt-kit-publish-pack.json"
        video_path = out_dir / "videos" / "ai-prompt-kit-youtube.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"dry-run video placeholder")

        subprocess.run(
            [
                sys.executable,
                str(MEDIA_ASSET_PACK),
                "--content-json",
                str(content_path),
                "--publish-pack",
                str(publish_pack_path),
                "--video-file",
                f"youtube={video_path}",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "reports/promotion-manager/media-assets/media-asset-pack.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertGreaterEqual(report["summary"]["coversReady"], 5)
        self.assertGreater(report["summary"]["detailImagesReady"], 0)

        publish_pack = json.loads(publish_pack_path.read_text(encoding="utf-8"))
        by_platform = {item["platform"]: item for item in publish_pack}
        youtube = by_platform["youtube"]
        self.assertEqual(youtube["video"]["status"], "ready")
        self.assertEqual(Path(youtube["video"]["path"]), video_path)
        for item in publish_pack:
            cover_path = Path(item["cover"]["path"])
            self.assertTrue(cover_path.exists(), item["platform"])
            self.assertEqual(cover_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", item["platform"])
            self.assertTrue(item["detailImages"], item["platform"])
            for image in item["detailImages"]:
                image_path = Path(image["path"])
                self.assertTrue(image_path.exists(), item["platform"])
                self.assertEqual(image_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", item["platform"])
            self.assertTrue(item["assets"], item["platform"])
            self.assertTrue(item["firstBatch"]["pinnedComment"], item["platform"])

    def test_product_intake_extracts_profile_from_html(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-intake-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "product.html"
        html_path.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit - ENHE</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <meta property="og:title" content="AI Prompt Kit">
  <meta property="og:image" content="https://example.com/cover.png">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>AI Prompt Kit</body>
</html>""",
            encoding="utf-8",
        )
        subprocess.run(
            [sys.executable, str(PRODUCT_INTAKE), "--html-file", str(html_path), "--out-dir", str(out_dir / "intake")],
            check=True,
            cwd=ROOT,
        )
        profile = json.loads((out_dir / "intake" / "product-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["productName"], "AI Prompt Kit")
        self.assertEqual(profile["pricing"], "19")
        self.assertIn("Prompt templates", profile["valueProposition"])
        self.assertTrue((out_dir / "intake" / "product-profile.md").exists())

    def test_product_intake_decodes_gb18030_html_without_mojibake(self) -> None:
        module = load_script_module(PRODUCT_INTAKE)
        out_dir = Path(tempfile.mkdtemp(prefix="product-intake-gb18030-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "product-gb18030.html"
        html = """<!doctype html>
<html>
<head>
  <meta charset="gb18030">
  <title>LumiOS AI - 恩禾</title>
  <meta name="description" content="Windows AI 桌面助手，支持语音、记忆和 MCP 工具。">
</head>
<body><h1>LumiOS AI</h1></body>
</html>"""
        html_path.write_bytes(html.encode("gb18030"))

        subprocess.run(
            [sys.executable, str(PRODUCT_INTAKE), "--html-file", str(html_path), "--out-dir", str(out_dir / "intake")],
            check=True,
            cwd=ROOT,
        )

        profile = json.loads((out_dir / "intake" / "product-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["productName"], "LumiOS AI - 恩禾")
        self.assertIn("桌面助手", profile["valueProposition"])
        self.assertFalse(module.text_looks_mojibake(json.dumps(profile, ensure_ascii=False)))

    def test_product_intake_accepts_structured_page_snapshot(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-structured-intake-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "pricing": "$19",
                    "images": [{"url": "https://example.com/cover.png"}],
                    "targetAudience": ["AI operators", "content marketers"],
                    "painPoints": ["Blank page copywriting", "Slow launch content"],
                    "text": "AI Prompt Kit helps turn a product URL into platform-native promotion content.",
                }
            ),
            encoding="utf-8-sig",
        )
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_INTAKE),
                "--structured-json",
                str(snapshot_path),
                "--out-dir",
                str(out_dir / "intake"),
            ],
            check=True,
            cwd=ROOT,
        )
        profile = json.loads((out_dir / "intake" / "product-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["sourceType"], "structured_json")
        self.assertEqual(profile["productName"], "AI Prompt Kit")
        self.assertEqual(profile["pricing"], "$19")
        self.assertEqual(profile["targetAudienceAssumptions"], ["AI operators", "content marketers"])
        self.assertEqual(profile["painPointAssumptions"], ["Blank page copywriting", "Slow launch content"])

    def test_product_intake_accepts_rendered_text_snapshot(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-text-intake-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        text_path = out_dir / "rendered.txt"
        text_path.write_text(
            """Product: AI Prompt Kit
URL: https://example.com/ai-prompt-kit
Pricing: $19
Audience: AI operators, content marketers
Pain Points: Blank page copywriting, slow launch content

Prompt templates for product copy, SEO content, and video scripts.
""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_INTAKE),
                "--text-file",
                str(text_path),
                "--out-dir",
                str(out_dir / "intake"),
            ],
            check=True,
            cwd=ROOT,
        )
        profile = json.loads((out_dir / "intake" / "product-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["sourceType"], "text")
        self.assertEqual(profile["productName"], "AI Prompt Kit")
        self.assertEqual(profile["pricing"], "$19")
        self.assertIn("AI operators", profile["targetAudienceAssumptions"])

    def test_browser_snapshot_normalizes_html_for_product_intake(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="browser-snapshot-html-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "product.html"
        html_path.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <link rel="canonical" href="https://example.com/ai-prompt-kit">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content. Start for $19.</p>
  <a href="/start">Start free</a>
  <img src="https://example.com/cover.png" alt="AI Prompt Kit cover">
</body>
</html>""",
            encoding="utf-8",
        )
        snapshot_path = out_dir / "snapshot.json"
        subprocess.run(
            [
                sys.executable,
                str(BROWSER_SNAPSHOT),
                "--html-file",
                str(html_path),
                "--base-url",
                "https://example.com/ai-prompt-kit",
                "--out-file",
                str(snapshot_path),
            ],
            check=True,
            cwd=ROOT,
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["snapshotType"], "browser_rendered")
        self.assertEqual(snapshot["productName"], "AI Prompt Kit")
        self.assertIn("Start free", snapshot["ctaCandidates"])
        self.assertIn("$19", snapshot["priceCandidates"])
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_INTAKE),
                "--structured-json",
                str(snapshot_path),
                "--out-dir",
                str(out_dir / "intake"),
            ],
            check=True,
            cwd=ROOT,
        )
        profile = json.loads((out_dir / "intake/product-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["sourceType"], "browser_rendered_snapshot")
        self.assertEqual(profile["productName"], "AI Prompt Kit")
        self.assertEqual(profile["pricing"], "19")

    def test_browser_snapshot_retries_domcontentloaded_after_networkidle_timeout(self) -> None:
        module = load_script_module(BROWSER_SNAPSHOT)

        class FakeTimeout(Exception):
            pass

        class FakeResponse:
            status = 200

        class FakePage:
            def __init__(self) -> None:
                self.wait_until_calls: list[str] = []

            def goto(self, _url: str, wait_until: str, timeout: int) -> FakeResponse:
                self.wait_until_calls.append(wait_until)
                if wait_until == "networkidle":
                    raise FakeTimeout("networkidle timeout")
                return FakeResponse()

        page = FakePage()
        args = argparse.Namespace(url="https://example.com/product", wait_until="networkidle", timeout_ms=30000)
        response, navigation = module.navigate_with_fallback(page, args, FakeTimeout)

        self.assertEqual(response.status, 200)
        self.assertEqual(page.wait_until_calls, ["networkidle", "domcontentloaded"])
        self.assertTrue(navigation["fallbackUsed"])
        self.assertEqual(navigation["usedWaitUntil"], "domcontentloaded")

    def test_browser_video_sampler_captures_visible_video_frames(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="browser-video-sampler-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        video_path = site_dir / "sample.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x2563eb:s=320x180:d=2",
                "-pix_fmt",
                "yuv420p",
                str(video_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        (site_dir / "video.html").write_text(
            """<!doctype html>
<html>
<head><title>Launch video teardown</title></head>
<body>
  <h1>Launch video teardown</h1>
  <p>Hook: stop writing product launch scripts from scratch.</p>
  <p>Voiceover: show pain, mechanism, proof, and CTA.</p>
  <video controls width="320" height="180" src="/sample.mp4?signature=secret-token"></video>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/video.html"
        subprocess.run(
            [
                sys.executable,
                str(BROWSER_VIDEO_SAMPLER),
                "--url",
                url,
                "--platform",
                "youtube",
                "--sample-count",
                "2",
                "--allow-localhost",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "output/reports/promotion-manager/competitors/video-sampling/browser-video-sampler.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["platform"], "youtube")
        self.assertEqual(report["videoCount"], 1)
        self.assertEqual(len(report["frames"]), 2)
        self.assertTrue(all(Path(frame["screenshot"]).exists() for frame in report["frames"]))
        self.assertTrue(report["primaryVideo"]["currentSrc"]["queryRedacted"])
        self.assertNotIn("secret-token", json.dumps(report, ensure_ascii=False))
        self.assertTrue(any("Voiceover" in item for item in report["visibleTranscriptHints"]))
        self.assertEqual(report["contentEvidence"]["videoEvidence"]["frameCount"], 2)
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/video-sampling/browser-video-sampler.md").exists())

    def test_product_url_reader_creates_structured_snapshot_then_profile(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-reader-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "product.html"
        html_path.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <link rel="canonical" href="https://example.com/ai-prompt-kit">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content. Start for $19.</p>
  <button>Start free</button>
</body>
</html>""",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            str(PRODUCT_URL_READER),
            "--url",
            html_path.as_uri(),
            "--out-dir",
            str(out_dir / "output"),
        ]
        expect_browser_structured = playwright_chromium_available()
        if not expect_browser_structured:
            command.append("--skip-browser")
        subprocess.run(command, check=True, cwd=ROOT)
        report_path = out_dir / "output/reports/promotion-manager/intake/product-url-reader.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["requestedUrls"], 1)
        record = report["records"][0]
        self.assertTrue(Path(record["intake"]["profile"]).exists())
        self.assertEqual(record["product"]["productName"], "AI Prompt Kit")
        if expect_browser_structured:
            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["summary"]["browserStructuredProfiles"], 1)
            self.assertEqual(record["sourceMode"], "browser_structured_snapshot")
            self.assertTrue(Path(record["browser"]["snapshot"]).exists())
            self.assertEqual(record["product"]["sourceType"], "browser_rendered_snapshot")
            self.assertIn("--structured-json", record["nextWorkflowCommand"])
        else:
            self.assertEqual(report["status"], "partial_ready")
            self.assertEqual(report["summary"]["staticFallbackProfiles"], 1)
            self.assertEqual(record["sourceMode"], "static_url_fallback")
            self.assertEqual(record["product"]["sourceType"], "html")
            self.assertIn("--product-url", record["nextWorkflowCommand"])
        self.assertTrue((out_dir / "output/reports/promotion-manager/intake/product-url-reader.md").exists())

    def test_web_data_provider_scrape_fixture_writes_report_without_secrets(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="web-data-provider-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        fixture = out_dir / "firecrawl-fixture.json"
        fixture.write_text(
            json.dumps(
                {
                    "scrape": {
                        "data": {
                            "markdown": "# LumiOS AI\n\nProduct: LumiOS AI\nURL: https://example.com/lumios\nDescription: Windows AI workspace.",
                            "metadata": {"sourceURL": "https://example.com/lumios", "title": "LumiOS AI"},
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(WEB_DATA_PROVIDER),
                "--provider",
                "firecrawl",
                "--fixture-json",
                str(fixture),
                "--out-dir",
                str(out_dir / "output"),
                "scrape",
                "--url",
                "https://example.com/lumios",
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/web-data/scrape.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertFalse(report["credentialValuesStored"])
        self.assertIn("LumiOS AI", report["markdown"])

    def test_web_data_provider_interact_plan_blocks_platform_side_effects(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="web-data-provider-interact-plan-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(WEB_DATA_PROVIDER),
                "--out-dir",
                str(out_dir / "output"),
                "interact-plan",
                "--url",
                "https://example.com/public-page",
                "--goal",
                "collect public launch evidence",
                "--action",
                "click:Pricing",
                "--action",
                "publish:final",
                "--action",
                "like:post",
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/web-data/interact-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("click:Pricing", report["allowedActions"])
        self.assertIn("publish:final", report["blockedActions"])
        self.assertIn("like:post", report["blockedActions"])
        self.assertFalse(report["providerExecutionEnabled"])
        self.assertTrue(report["requiresManualApprovalBeforeExecution"])

    def test_product_url_reader_uses_firecrawl_scrape_before_web_text_fallback(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-reader-firecrawl-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        fixture = out_dir / "firecrawl-fixture.json"
        fixture.write_text(
            json.dumps(
                {
                    "scrape": {
                        "data": {
                            "markdown": "\n".join(
                                [
                                    "Product: Firecrawl Product Lab",
                                    "URL: https://example.com/firecrawl-product-lab",
                                    "Description: Turns product pages into promotion research and launch content.",
                                    "Pricing: unknown",
                                    "Audience: AI tool operators, creators",
                                    "Pain points: slow competitor research, repeated launch copy setup",
                                ]
                            )
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_URL_READER),
                "--url",
                "https://127.0.0.1:9/firecrawl-product-lab",
                "--skip-browser",
                "--web-data-provider",
                "firecrawl",
                "--web-data-fixture-json",
                str(fixture),
                "--disable-web-text-fallback",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/intake/product-url-reader.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["sourceMode"], "firecrawl_scrape")
        self.assertEqual(report["summary"]["firecrawlScrapeProfiles"], 1)
        self.assertTrue(Path(record["webData"]["textFile"]).exists())
        self.assertIn("--text-file", record["nextWorkflowCommand"])

    def test_product_url_reader_uses_web_text_fallback_after_browser_and_static_fail(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-reader-web-fallback-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        fallback = out_dir / "fallback.md"
        fallback.write_text(
            "\n".join(
                [
                    "Product: LumiOS AI",
                    "URL: https://www.enhe-tech.com.cn/software/windows-ai",
                    "Description: Windows AI workspace that remembers work context and helps operators write, research, and organize tasks.",
                    "Pricing: unknown",
                    "Audience: AI tool users, content operators",
                    "Pain points: fragmented AI chat windows, repeated context setup",
                ]
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_URL_READER),
                "--url",
                "https://127.0.0.1:9/unreachable-product",
                "--skip-browser",
                "--web-text-fallback-file",
                str(fallback),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "output/reports/promotion-manager/intake/product-url-reader.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(report["status"], "partial_ready")
        self.assertEqual(record["sourceMode"], "web_text_fallback")
        self.assertEqual(record["webText"]["status"], "ready")
        self.assertTrue(Path(record["webText"]["textFile"]).exists())
        self.assertEqual(record["product"]["productName"], "LumiOS AI")
        self.assertEqual(record["product"]["sourceType"], "text")
        self.assertIn("--text-file", record["nextWorkflowCommand"])

    def test_product_url_reader_reuses_matching_cached_profile_after_intake_failure(self) -> None:
        module = load_script_module(PRODUCT_URL_READER)
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-reader-cached-profile-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        intake_dir = out_dir / "intake"
        intake_dir.mkdir(parents=True)
        (intake_dir / "product-profile.json").write_text(
            json.dumps(
                {
                    "productName": "LumiOS AI",
                    "canonicalUrl": "https://www.enhe-tech.com.cn/software/windows-ai",
                    "sourceType": "text",
                    "valueProposition": "Windows AI workspace for operators.",
                }
            ),
            encoding="utf-8",
        )

        status = module.run_intake_command(
            [],
            intake_dir,
            [sys.executable, "-c", "import sys; sys.exit(1)"],
            "https://www.enhe-tech.com.cn/software/windows-ai/",
        )

        self.assertEqual(status["status"], "partial_ready")
        self.assertEqual(status["exitCode"], 1)
        self.assertIn("matching cached product profile", status["reason"])
        self.assertTrue(module.usable_profile_status(status))
        self.assertEqual(module.record_status({"status": "error"}, status), "partial_ready")
        cached_text = module.write_cached_profile_text(
            out_dir,
            {
                "productName": "LumiOS AI",
                "canonicalUrl": "https://www.enhe-tech.com.cn/software/windows-ai",
                "valueProposition": "Windows AI workspace for operators.",
                "pricing": "unknown",
                "targetAudienceAssumptions": ["AI tool users"],
                "painPointAssumptions": ["repeated context setup"],
            },
        )
        command = module.next_workflow_command(
            "https://www.enhe-tech.com.cn/software/windows-ai",
            "cached_profile_fallback",
            out_dir / "missing-snapshot.json",
            cached_text,
            out_dir / "output",
            status,
        )
        self.assertIn("--text-file", command)
        self.assertIn("cached-product-profile.md", command)

    def test_product_url_reader_rejects_mojibake_cached_profile_after_intake_failure(self) -> None:
        module = load_script_module(PRODUCT_URL_READER)
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-reader-mojibake-cache-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        intake_dir = out_dir / "intake"
        intake_dir.mkdir(parents=True)
        (intake_dir / "product-profile.json").write_text(
            json.dumps(
                {
                    "productName": "Lumi-OS锝淎I鎯呮劅闄即鏅鸿兘",
                    "canonicalUrl": "https://www.enhe-tech.com.cn/software/windows-ai",
                    "sourceType": "text",
                    "valueProposition": "鍦ㄥ伐浣滀腑锛孡umiOS 鍙互浣滀负浣犵殑妗岄潰鍔╂墜",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        status = module.run_intake_command(
            [],
            intake_dir,
            [sys.executable, "-c", "import sys; sys.exit(1)"],
            "https://www.enhe-tech.com.cn/software/windows-ai",
        )

        self.assertEqual(status["status"], "error")
        self.assertIn("mojibake", status["reason"])
        self.assertFalse(module.usable_profile_status(status))

    def test_product_batch_runner_routes_web_text_fallback_to_text_file_cycle(self) -> None:
        module = load_script_module(PRODUCT_BATCH_RUNNER)
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-web-fallback-source-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        text_file = out_dir / "web-reader-page.md"
        text_file.write_text("Product: LumiOS AI\nDescription: Windows AI workspace.", encoding="utf-8")
        source = module.workflow_source(
            {
                "url": "https://example.invalid/product",
                "sourceMode": "web_text_fallback",
                "intake": {"status": "ready"},
                "webText": {"status": "ready", "textFile": str(text_file)},
            }
        )

        self.assertEqual(source["flag"], "--text-file")
        self.assertEqual(source["value"], str(text_file))
        self.assertEqual(source["sourceMode"], "web_text_fallback")

        static_source = module.workflow_source(
            {
                "url": "https://example.invalid/product",
                "sourceMode": "static_url_fallback",
                "intake": {"status": "partial_ready"},
            }
        )
        self.assertEqual(static_source["flag"], "--product-url")
        self.assertEqual(static_source["value"], "https://example.invalid/product")
        self.assertEqual(static_source["sourceMode"], "static_url_fallback")

        cached_source = module.workflow_source(
            {
                "url": "https://example.invalid/product",
                "sourceMode": "cached_profile_fallback",
                "intake": {"status": "partial_ready"},
                "webText": {"status": "ready", "textFile": str(text_file)},
            }
        )
        self.assertEqual(cached_source["flag"], "--text-file")
        self.assertEqual(cached_source["value"], str(text_file))
        self.assertEqual(cached_source["sourceMode"], "cached_profile_fallback")

    def test_product_url_discovery_selects_product_links_from_saved_html(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-discovery-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        index = out_dir / "index.html"
        index.write_text(
            """<!doctype html>
<html>
<head><title>Example AI Tools</title></head>
<body>
  <a href="/products/ai-prompt-kit">AI Prompt Kit product</a>
  <a href="/tools/video-script-generator">Video Script Generator tool</a>
  <a href="/blog/growth-notes">Growth notes blog</a>
  <a href="/login">Login</a>
  <a href="/privacy">Privacy</a>
</body>
</html>""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_URL_DISCOVERY),
                "--html-file",
                str(index),
                "--base-url",
                "https://example.com",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "output/reports/promotion-manager/intake/product-url-discovery.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["selectedUrls"], 2)
        self.assertEqual(
            set(report["selectedUrls"]),
            {"https://example.com/products/ai-prompt-kit", "https://example.com/tools/video-script-generator"},
        )
        urls_file = out_dir / "output/product-url-discovery/product-urls.txt"
        self.assertTrue(urls_file.exists())
        urls_text = urls_file.read_text(encoding="utf-8")
        self.assertIn("https://example.com/products/ai-prompt-kit", urls_text)
        self.assertNotIn("/blog/growth-notes", urls_text)
        self.assertNotIn("/login", urls_text)

    def test_product_url_discovery_selects_product_links_from_sitemap_file(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-sitemap-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        sitemap = out_dir / "sitemap.xml"
        sitemap.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/products/ai-prompt-kit</loc></url>
  <url><loc>https://example.com/tools/video-script-generator</loc></url>
  <url><loc>https://example.com/blog/growth-notes</loc></url>
  <url><loc>https://example.com/login</loc></url>
</urlset>""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_URL_DISCOVERY),
                "--sitemap-file",
                str(sitemap),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "output/reports/promotion-manager/intake/product-url-discovery.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["sitemapsRead"], 1)
        self.assertEqual(report["summary"]["sitemapUrls"], 4)
        self.assertEqual(
            set(report["selectedUrls"]),
            {"https://example.com/products/ai-prompt-kit", "https://example.com/tools/video-script-generator"},
        )
        source_types = {item["sourceType"] for item in report["candidates"]}
        self.assertEqual(source_types, {"sitemap"})

    def test_product_url_discovery_uses_firecrawl_map_fixture(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-url-firecrawl-map-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        fixture = out_dir / "firecrawl-map.json"
        fixture.write_text(
            json.dumps(
                {
                    "map": {
                        "success": True,
                        "links": [
                            {"url": "https://example.com/products/viral-copy-kit", "title": "Viral Copy Kit"},
                            {"url": "https://example.com/blog/launch-notes", "title": "Launch Notes"},
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_URL_DISCOVERY),
                "--site-url",
                "http://127.0.0.1:9",
                "--allow-localhost",
                "--include-external",
                "--skip-sitemaps",
                "--web-data-provider",
                "firecrawl",
                "--web-data-fixture-json",
                str(fixture),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/intake/product-url-discovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["webDataLinks"], 2)
        self.assertIn("https://example.com/products/viral-copy-kit", report["selectedUrls"])
        self.assertTrue(any(item["sourceType"] == "web_data_map" for item in report["candidates"]))

    def test_product_batch_runner_reads_urls_then_runs_promotion_cycles(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-runner-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_pages = [
            (
                "prompt-kit.html",
                "AI Prompt Kit",
                "Prompt templates for product copy, SEO content, and video scripts.",
            ),
            (
                "landing-auditor.html",
                "Landing Auditor",
                "Review landing pages and turn gaps into platform-native growth content.",
            ),
        ]
        urls_file = out_dir / "urls.txt"
        urls = []
        for filename, title, description in product_pages:
            page = out_dir / filename
            page.write_text(
                f"""<!doctype html>
<html>
<head>
  <title>{title}</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="https://example.com/{filename.replace('.html', '')}">
  <script type="application/ld+json">{{"@type":"Product","name":"{title}","offers":{{"price":"19"}}}}</script>
</head>
<body>
  <h1>{title}</h1>
  <p>{description} Start for $19.</p>
</body>
</html>""",
                encoding="utf-8",
            )
            urls.append(page.as_uri())
        urls_file.write_text("\n".join(urls) + "\n", encoding="utf-8")

        command = [
            sys.executable,
            str(PRODUCT_BATCH_RUNNER),
            "--urls-file",
            str(urls_file),
            "--platforms",
            "github,xiaohongshu",
            "--run-follow-up-captures",
            "--follow-up-dry-run",
            "--sample-video-frames",
            "--video-sample-count",
            "4",
            "--skip-video",
            "--out-dir",
            str(out_dir / "output"),
        ]
        expect_browser_structured = playwright_chromium_available()
        if not expect_browser_structured:
            command.append("--skip-browser")
        subprocess.run(command, check=True, cwd=ROOT)

        report_path = out_dir / "output/reports/promotion-manager/batch/product-batch-runner.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["requestedUrls"], 2)
        self.assertEqual(report["summary"]["readyProductProfiles"], 2)
        self.assertEqual(report["summary"]["readyPromotionRuns"], 2)
        self.assertTrue(Path(report["readerReport"]).exists())
        first_command = report["promotionRuns"][0]["command"]
        self.assertIn("--sample-video-frames", first_command)
        self.assertIn("--video-sample-count", first_command)
        self.assertIn("4", first_command)
        self.assertTrue((out_dir / "output/reports/promotion-manager/batch/product-batch-runner.md").exists())

        product_names = {run["product"]["productName"] for run in report["promotionRuns"]}
        self.assertEqual(product_names, {"AI Prompt Kit", "Landing Auditor"})
        for run in report["promotionRuns"]:
            self.assertEqual(run["status"], "ready")
            self.assertTrue(Path(run["outputDir"]).exists())
            self.assertTrue(Path(run["cycleReport"]).exists())
            self.assertTrue(Path(run["workflowManifest"]).exists())
            command_text = " ".join(run["command"])
            if expect_browser_structured:
                self.assertEqual(run["sourceMode"], "browser_structured_snapshot")
                self.assertIn("--structured-json", command_text)
            else:
                self.assertEqual(run["sourceMode"], "static_url_fallback")
                self.assertIn("--product-url", command_text)

    def test_product_batch_runner_discovers_urls_then_reads_and_runs_cycles(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-discovery-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        (site_dir / "products").mkdir(parents=True)
        (site_dir / "tools").mkdir(parents=True)
        (site_dir / "blog").mkdir(parents=True)
        (site_dir / "index.html").write_text(
            """<!doctype html>
<html>
<head><title>Example AI Tools</title></head>
<body>
  <a href="/products/ai-prompt-kit.html">AI Prompt Kit product</a>
  <a href="/tools/video-script-generator.html">Video Script Generator tool</a>
  <a href="/blog/growth-notes.html">Growth notes blog</a>
  <a href="/login">Login</a>
</body>
</html>""",
            encoding="utf-8",
        )
        (site_dir / "products" / "ai-prompt-kit.html").write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body><h1>AI Prompt Kit</h1><p>Turn one product URL into promotion content.</p></body>
</html>""",
            encoding="utf-8",
        )
        (site_dir / "tools" / "video-script-generator.html").write_text(
            """<!doctype html>
<html>
<head>
  <title>Video Script Generator</title>
  <meta name="description" content="Generate short-video scripts, hooks, and platform captions.">
  <script type="application/ld+json">{"@type":"Product","name":"Video Script Generator","offers":{"price":"29"}}</script>
</head>
<body><h1>Video Script Generator</h1><p>Create scripts for YouTube, Xiaohongshu, and Douyin.</p></body>
</html>""",
            encoding="utf-8",
        )
        (site_dir / "blog" / "growth-notes.html").write_text("<html><body>blog</body></html>", encoding="utf-8")

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        start_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_BATCH_RUNNER),
                "--discover-from-url",
                start_url,
                "--discovery-allow-localhost",
                "--skip-browser",
                "--platforms",
                "github,xiaohongshu",
                "--skip-video",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "output/reports/promotion-manager/batch/product-batch-runner.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["discoveredUrls"], 2)
        self.assertEqual(report["summary"]["requestedUrls"], 2)
        self.assertEqual(report["summary"]["readyProductProfiles"], 2)
        self.assertEqual(report["summary"]["readyPromotionRuns"], 2)
        self.assertTrue(Path(report["discoveryReport"]).exists())
        self.assertTrue(Path(report["readerReport"]).exists())
        self.assertEqual(len(report["discoveredUrls"]), 2)
        product_names = {run["product"]["productName"] for run in report["promotionRuns"]}
        self.assertEqual(product_names, {"AI Prompt Kit", "Video Script Generator"})

    def test_product_batch_runner_discovers_sitemap_from_site_then_runs_cycles(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-sitemap-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        (site_dir / "products").mkdir(parents=True)
        (site_dir / "index.html").write_text("<html><body><h1>AI Tool Station</h1></body></html>", encoding="utf-8")
        (site_dir / "products" / "ai-prompt-kit.html").write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body><h1>AI Prompt Kit</h1><p>Turn one product URL into promotion content.</p></body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        (site_dir / "robots.txt").write_text(f"Sitemap: {base_url}/sitemap.xml\n", encoding="utf-8")
        (site_dir / "sitemap.xml").write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{base_url}/products/ai-prompt-kit.html</loc></url>
  <url><loc>{base_url}/blog/post.html</loc></url>
</urlset>""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_BATCH_RUNNER),
                "--discover-from-url",
                f"{base_url}/index.html",
                "--discovery-allow-localhost",
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "output/reports/promotion-manager/batch/product-batch-runner.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["discoveredUrls"], 1)
        self.assertEqual(report["summary"]["readyPromotionRuns"], 1)
        discovery = json.loads(Path(report["discoveryReport"]).read_text(encoding="utf-8"))
        self.assertEqual(discovery["summary"]["robotsTxtRead"], 1)
        self.assertEqual(discovery["summary"]["sitemapsRead"], 1)
        self.assertEqual(discovery["summary"]["sitemapUrls"], 2)
        self.assertEqual(report["promotionRuns"][0]["product"]["productName"], "AI Prompt Kit")

    def test_product_batch_runner_runs_multi_query_discovery_after_each_cycle(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-multi-query-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        page = out_dir / "prompt-kit.html"
        page.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content.</p>
</body>
</html>""",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            str(PRODUCT_BATCH_RUNNER),
            "--url",
            page.as_uri(),
            "--platforms",
            "github,xiaohongshu",
            "--skip-video",
            "--run-multi-query-viral-discovery",
            "--multi-query-dry-run",
            "--multi-query-query-count",
            "2",
            "--multi-query-top-n",
            "5",
            "--multi-query-browser-search-timeout-ms",
            "15000",
            "--multi-query-browser-search-wait-until",
            "domcontentloaded",
            "--out-dir",
            str(out_dir / "output"),
        ]
        if not playwright_chromium_available():
            command.append("--skip-browser")
        subprocess.run(command, check=True, cwd=ROOT)

        report_path = out_dir / "output/reports/promotion-manager/batch/product-batch-runner.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["multiQueryDiscoveryRuns"], 1)
        self.assertEqual(report["summary"]["plannedMultiQueryDiscoveryRuns"], 1)
        run = report["promotionRuns"][0]
        multi_query = run["multiQueryViralDiscovery"]
        self.assertEqual(multi_query["status"], "planned")
        self.assertTrue(Path(multi_query["report"]).exists())
        self.assertTrue(Path(multi_query["mergedViralLibrary"]).exists())
        self.assertTrue(Path(multi_query["mergedCreatorLeaderboard"]).exists())
        command_text = " ".join(multi_query["command"])
        self.assertIn("--workflow-manifest", command_text)
        self.assertIn("--dry-run", command_text)
        self.assertIn("--browser-search-timeout-ms 15000", command_text)
        self.assertIn("--browser-search-wait-until domcontentloaded", command_text)
        discovery_report = json.loads(Path(multi_query["report"]).read_text(encoding="utf-8"))
        self.assertEqual(discovery_report["summary"]["queries"], 2)

    def test_product_batch_runner_runs_next_round_optimization_after_each_cycle(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-next-round-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_page = out_dir / "prompt-kit.html"
        product_page.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content.</p>
</body>
</html>""",
            encoding="utf-8",
        )
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <p>views: 4,200 likes: 360 comments: 41</p>
    <section class="comments">
      <p>Comment by Alice: How does pricing work? likes: 9</p>
      <p>Bob: Need Zapier integration replies: 2</p>
      <p>Carol: This solved our content workflow</p>
    </section>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        published_url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        business_csv = out_dir / "orders.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,referrer,revenue,status",
                    f"order-1,xiaohongshu,{published_url},99.00,paid",
                ]
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_BATCH_RUNNER),
                "--url",
                product_page.as_uri(),
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--skip-publish-queue",
                "--published-url",
                f"xiaohongshu={published_url}",
                "--run-post-publish-metrics-capture",
                "--post-publish-metrics-allow-localhost",
                "--run-comment-evidence-capture",
                "--comment-evidence-allow-localhost",
                "--run-business-attribution",
                "--business-csv",
                str(business_csv),
                "--run-next-round-optimization",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "output/reports/promotion-manager/batch/product-batch-runner.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "partial_ready")
        self.assertEqual(report["summary"]["readyPromotionRuns"], 1)
        self.assertEqual(report["summary"]["nextRoundOptimizationRuns"], 1)
        self.assertEqual(report["summary"]["partialReadyNextRoundOptimizationRuns"], 1)
        run = report["promotionRuns"][0]
        self.assertEqual(run["status"], "ready")
        self.assertEqual(run["nextRoundOptimization"]["status"], "partial_ready")
        self.assertTrue(Path(run["nextRoundOptimization"]["report"]).exists())
        self.assertEqual(run["nextRoundOptimization"]["summary"]["commentCount"], 3)
        self.assertEqual(run["nextRoundOptimization"]["summary"]["businessAttributions"], 1)
        self.assertIn("--run-next-round-optimization", " ".join(run["command"]))
        self.assertIn("--post-publish-metrics-allow-localhost", " ".join(run["command"]))
        self.assertIn("--comment-evidence-allow-localhost", " ".join(run["command"]))

    def test_product_batch_runner_passes_xlsx_evidence_to_cycle(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="product-batch-xlsx-evidence-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_page = out_dir / "prompt-kit.html"
        product_page.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content.</p>
</body>
</html>""",
            encoding="utf-8",
        )
        metrics_xlsx = out_dir / "metrics.xlsx"
        write_minimal_xlsx(
            metrics_xlsx,
            [
                ["platform", "publishedUrl", "title", "view_count", "like_count", "comment_count", "evidence"],
                ["xiaohongshu", "https://www.xiaohongshu.com/explore/note123", "Launch Note", "4200", "360", "41", "xhs-export.xlsx"],
            ],
        )
        business_xlsx = out_dir / "orders.xlsx"
        write_minimal_xlsx(
            business_xlsx,
            [
                ["orderId", "utm_source", "utm_content", "revenue", "status"],
                ["order-1", "xiaohongshu", "note123", "88.00", "paid"],
            ],
        )
        subprocess.run(
            [
                sys.executable,
                str(PRODUCT_BATCH_RUNNER),
                "--url",
                product_page.as_uri(),
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--skip-publish-queue",
                "--published-url",
                "xiaohongshu=https://www.xiaohongshu.com/explore/note123",
                "--metrics-xlsx",
                str(metrics_xlsx),
                "--business-xlsx",
                str(business_xlsx),
                "--run-business-attribution",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads(
            (out_dir / "output/reports/promotion-manager/batch/product-batch-runner.json").read_text(encoding="utf-8")
        )
        run = report["promotionRuns"][0]
        command = " ".join(run["command"])
        self.assertIn("--metrics-xlsx", command)
        self.assertIn("--business-xlsx", command)
        cycle = json.loads(Path(run["cycleReport"]).read_text(encoding="utf-8"))
        self.assertEqual(cycle["businessAttribution"]["summary"]["matchedRows"], 1)
        recovery = json.loads(Path(cycle["metricsRecovery"]["metricsRecovery"]).read_text(encoding="utf-8"))
        self.assertEqual(recovery["metricSources"][0]["type"], "metrics_xlsx")
        self.assertEqual(recovery["aggregates"]["totals"]["views"], 4200.0)
        self.assertEqual(recovery["aggregates"]["totals"]["revenue"], 88.0)

    def test_final_capability_runner_discovers_products_from_site_url(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-capability-discovery-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        (site_dir / "products").mkdir(parents=True)
        (site_dir / "index.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Tool Station</title></head>
<body>
  <a href="/products/ai-prompt-kit.html">AI Prompt Kit product</a>
  <a href="/blog/post.html">Blog post</a>
  <a href="/login">Login</a>
</body>
</html>""",
            encoding="utf-8",
        )
        (site_dir / "products" / "ai-prompt-kit.html").write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body><h1>AI Prompt Kit</h1><p>Turn one product URL into platform-native promotion content.</p></body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        start_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_RUNNER),
                "--discover-from-url",
                start_url,
                "--discovery-allow-localhost",
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--skip-publish-queue",
                "--skip-publish-readiness",
                "--skip-browser-publish-assistant",
                "--skip-metrics-recovery",
                "--skip-multi-query-viral-discovery",
                "--skip-post-publish-metrics-capture",
                "--skip-comment-evidence-capture",
                "--skip-business-attribution",
                "--skip-next-round-optimization",
                "--skip-platform-access-audit",
                "--skip-final-capability-audit",
                "--skip-self-evolution-audit",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "output/reports/promotion-manager/final-run/final-capability-run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "partial_ready")
        self.assertEqual(report["input"]["discoverFromUrl"], start_url)
        self.assertEqual(report["productBatch"]["summary"]["discoveredUrls"], 1)
        self.assertTrue(Path(report["productBatch"]["discoveryReport"]).exists())
        self.assertEqual(report["cycleEvidence"][0]["product"]["productName"], "AI Prompt Kit")

    def test_final_capability_runner_inherits_video_evidence_flags_for_multi_query_discovery(self) -> None:
        module = load_script_module(FINAL_CAPABILITY_RUNNER)
        original_argv = sys.argv
        try:
            sys.argv = [
                str(FINAL_CAPABILITY_RUNNER),
                "--url",
                "https://example.com/product",
                "--run-follow-up-captures",
                "--capture-browser-assisted-follow-ups",
                "--sample-video-frames",
                "--video-sample-count",
                "3",
                "--timeout-ms",
                "15000",
                "--wait-until",
                "domcontentloaded",
            ]
            args = module.parse_args()
        finally:
            sys.argv = original_argv

        command = [sys.executable, str(PRODUCT_BATCH_RUNNER), "--out-dir", "./promotion-output"]
        module.append_common_batch_args(command, args)

        self.assertIn("--run-multi-query-viral-discovery", command)
        self.assertIn("--multi-query-run-follow-up-captures", command)
        self.assertIn("--multi-query-capture-browser-assisted-follow-ups", command)
        self.assertIn("--multi-query-sample-video-frames", command)
        self.assertIn("--multi-query-video-sample-count", command)
        self.assertEqual(command[command.index("--multi-query-video-sample-count") + 1], "3")
        self.assertIn("--multi-query-browser-search-timeout-ms", command)
        self.assertEqual(command[command.index("--multi-query-browser-search-timeout-ms") + 1], "15000")
        self.assertIn("--multi-query-browser-search-wait-until", command)
        self.assertEqual(command[command.index("--multi-query-browser-search-wait-until") + 1], "domcontentloaded")

    def test_final_capability_runner_orchestrates_safe_full_flow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-capability-runner-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_page = out_dir / "prompt-kit.html"
        product_page.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content.</p>
</body>
</html>""",
            encoding="utf-8",
        )
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <p>views: 4,200 likes: 360 comments: 41</p>
    <section class="comments">
      <p>Comment by Alice: How does pricing work? likes: 9</p>
      <p>Bob: Need Zapier integration replies: 2</p>
      <p>Carol: This solved our content workflow</p>
    </section>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        published_url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        business_csv = out_dir / "orders.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,referrer,revenue,status",
                    f"order-1,xiaohongshu,{published_url},99.00,paid",
                ]
            ),
            encoding="utf-8",
        )
        search_snapshot_root = out_dir / "search-snapshots"
        search_snapshot_root.mkdir()
        (search_snapshot_root / "xiaohongshu.html").write_text(
            """<!doctype html>
<html>
<head><title>Xiaohongshu AI Prompt Kit Search</title></head>
<body>
  <article>
    <h2>3 minute AI product promotion workflow</h2>
    <a href="https://www.xiaohongshu.com/explore/demo-note">viral note</a>
    <p>likes 360 saves 88 comments 41</p>
    <p>creator: Content Growth Lab</p>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_RUNNER),
                "--url",
                product_page.as_uri(),
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--run-follow-up-captures",
                "--follow-up-dry-run",
                "--capture-browser-assisted-follow-ups",
                "--sample-video-frames",
                "--video-sample-count",
                "3",
                "--multi-query-dry-run",
                "--multi-query-query-count",
                "2",
                "--multi-query-html-snapshot-root",
                str(search_snapshot_root),
                "--multi-query-run-follow-up-captures",
                "--multi-query-sample-video-frames",
                "--multi-query-video-sample-count",
                "2",
                "--published-url",
                f"xiaohongshu={published_url}",
                "--post-publish-metrics-allow-localhost",
                "--comment-evidence-allow-localhost",
                "--business-csv",
                str(business_csv),
                "--execute-publish",
                "--approval",
                "I_APPROVE_PUBLISH",
                "--github-action",
                "release",
                "--github-branch",
                "launch",
                "--github-tag-name",
                "promo-test",
                "--youtube-privacy-status",
                "unlisted",
                "--youtube-category-id",
                "28",
                "--skip-platform-access-audit",
                "--skip-final-capability-audit",
                "--skip-self-evolution-audit",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "output/reports/promotion-manager/final-run/final-capability-run.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "partial_ready")
        batch_command = report["steps"][0]["command"]
        self.assertIn("--sample-video-frames", batch_command)
        self.assertIn("--video-sample-count", batch_command)
        self.assertIn("--capture-browser-assisted-follow-ups", batch_command)
        self.assertIn("--multi-query-sample-video-frames", batch_command)
        self.assertIn("--multi-query-video-sample-count", batch_command)
        self.assertIn("--multi-query-html-snapshot-root", batch_command)
        self.assertIn(str(search_snapshot_root), batch_command)
        batch_report = json.loads(Path(report["productBatch"]["report"]).read_text(encoding="utf-8"))
        multi_query_command = batch_report["promotionRuns"][0]["multiQueryViralDiscovery"]["command"]
        self.assertIn("--html-snapshot-root", multi_query_command)
        self.assertIn(str(search_snapshot_root), multi_query_command)
        readiness_command = next(item["command"] for item in report["steps"] if item["name"].startswith("publish_readiness_"))
        self.assertIn("--execute-publish", readiness_command)
        self.assertIn("--approval", readiness_command)
        self.assertIn("I_APPROVE_PUBLISH", readiness_command)
        self.assertIn("--github-action", readiness_command)
        self.assertIn("release", readiness_command)
        self.assertIn("--github-branch", readiness_command)
        self.assertIn("launch", readiness_command)
        self.assertIn("--github-tag-name", readiness_command)
        self.assertIn("promo-test", readiness_command)
        self.assertIn("--youtube-privacy-status", readiness_command)
        self.assertIn("unlisted", readiness_command)
        self.assertIn("--youtube-category-id", readiness_command)
        self.assertIn("28", readiness_command)
        self.assertTrue(report["input"]["publishExecutionRequested"])
        self.assertTrue(report["summary"]["publishExecutionRequested"])
        self.assertTrue(report["input"]["publishApprovalProvided"])
        self.assertTrue(report["summary"]["publishApprovalProvided"])
        self.assertEqual(report["summary"]["promotionRuns"], 1)
        self.assertEqual(report["summary"]["publishReadinessRuns"], 1)
        self.assertEqual(report["summary"]["publishSetupRuns"], 1)
        self.assertEqual(report["summary"]["browserPublishAssistantRuns"], 1)
        self.assertEqual(report["summary"]["launchUnlockPackRuns"], 1)
        self.assertGreaterEqual(report["summary"]["launchUnlockReadyGates"], 1)
        self.assertEqual(report["summary"]["nextRoundOptimizationRuns"], 1)
        self.assertEqual(report["summary"]["multiQueryDiscoveryRuns"], 1)
        self.assertEqual(report["summary"]["contentArtifacts"], 1)
        self.assertEqual(report["summary"]["videoFilesGenerated"], 0)
        self.assertEqual(report["summary"]["publishQueues"], 1)
        self.assertEqual(report["summary"]["realEvidenceSetupRuns"], 1)
        self.assertGreaterEqual(report["summary"]["realEvidenceSetupTargets"], 1)
        self.assertEqual(report["summary"]["publishedItemsReports"], 1)
        self.assertEqual(report["summary"]["postPublishMetricsCaptureRuns"], 1)
        self.assertEqual(report["summary"]["commentEvidenceCaptureRuns"], 1)
        self.assertEqual(report["summary"]["businessAttributionRuns"], 1)
        self.assertEqual(report["summary"]["metricsRecoveryRuns"], 1)
        self.assertEqual(report["summary"]["capturedMetricRecords"], 1)
        self.assertEqual(report["summary"]["commentCount"], 3)
        self.assertEqual(report["summary"]["matchedBusinessRows"], 1)
        self.assertEqual(len(report["cycleEvidence"]), 1)
        evidence = report["cycleEvidence"][0]
        self.assertTrue(Path(evidence["content"]["contentJson"]).exists())
        self.assertEqual(evidence["videoGeneration"]["generatedCount"], 0)
        self.assertEqual(evidence["publishQueue"]["status"], "ready")
        self.assertEqual(evidence["postPublishMetricsCapture"]["status"], "ready")
        self.assertEqual(evidence["commentEvidenceCapture"]["status"], "ready")
        self.assertEqual(evidence["businessAttribution"]["status"], "ready")
        self.assertEqual(evidence["evidenceCounts"]["capturedMetricRecords"], 1)
        self.assertEqual(evidence["evidenceCounts"]["commentCount"], 3)
        self.assertEqual(evidence["evidenceCounts"]["matchedBusinessRows"], 1)
        self.assertTrue(Path(report["productBatch"]["report"]).exists())
        self.assertEqual(report["publishReadiness"][0]["status"], "partial_ready")
        self.assertEqual(report["publishSetup"][0]["status"], "ready")
        self.assertTrue(Path(report["publishSetup"][0]["report"]).exists())
        self.assertTrue(Path(report["publishSetup"][0]["envTemplate"]).exists())
        self.assertEqual(report["realEvidenceSetup"][0]["status"], "ready")
        self.assertTrue(Path(report["realEvidenceSetup"][0]["report"]).exists())
        self.assertTrue(Path(report["realEvidenceSetup"][0]["platformMetricsTemplate"]).exists())
        self.assertTrue(Path(report["realEvidenceSetup"][0]["businessAttributionTemplate"]).exists())
        self.assertIn(report["summary"]["finalReadinessStatus"], {"partial_ready", "partial_ready_waiting_external_evidence"})
        self.assertTrue(Path(report["finalReadinessMatrix"]["report"]).exists())
        self.assertEqual(report["browserPublishAssistant"][0]["status"], "ready")
        self.assertTrue(Path(report["browserPublishAssistant"][0]["report"]).exists())
        self.assertEqual(report["launchUnlockPack"][0]["status"], "ready_unlock_pack")
        self.assertTrue(Path(report["launchUnlockPack"][0]["report"]).exists())
        self.assertTrue(Path(report["launchUnlockPack"][0]["checklist"]).exists())
        self.assertTrue(Path(report["launchUnlockPack"][0]["nextActionCommands"]).exists())
        self.assertTrue(any(item["name"].startswith("launch_unlock_pack_") for item in report["steps"]))
        self.assertTrue(any(item["area"] == "zhihu_xiaohongshu" for item in report["externalGates"]))
        self.assertTrue((out_dir / "output/reports/promotion-manager/final-run/final-capability-run.md").exists())

    def test_skill_entry_runs_one_link_safe_flow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="skill-entry-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_page = out_dir / "prompt-kit.html"
        product_page.write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit</title><meta name="description" content="Prompt templates for launch copy."></head>
<body><h1>AI Prompt Kit</h1><p>Turn one product URL into launch content.</p></body>
</html>""",
            encoding="utf-8",
        )
        business_xlsx = out_dir / "orders.xlsx"
        write_minimal_xlsx(
            business_xlsx,
            [
                ["orderId", "utm_source", "utm_content", "revenue", "status"],
                ["order-1", "xiaohongshu", "note123", "88.00", "paid"],
            ],
        )
        metrics_csv = out_dir / "platform-metrics.csv"
        metrics_csv.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,views,likes,comments,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,4200,360,41,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        comment_html = out_dir / "comments.html"
        comment_html.write_text(
            """<!doctype html>
<html><body>
  <p>Comment by Alice: How does pricing work? likes: 9</p>
  <p>Bob: Need Zapier integration replies: 2</p>
</body></html>""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ENTRY),
                "--link",
                product_page.as_uri(),
                "--link-mode",
                "auto",
                "--discovery-top-n",
                "3",
                "--discovery-min-score",
                "1.5",
                "--discovery-max-pages",
                "2",
                "--discovery-max-depth",
                "0",
                "--discovery-max-sitemap-urls",
                "4",
                "--discovery-timeout",
                "5",
                "--discovery-skip-sitemaps",
                "--discovery-allow-localhost",
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-auto-search-competitors",
                "--skip-creator-follow-up",
                "--skip-follow-up-captures",
                "--skip-video-sampling",
                "--skip-video",
                "--multi-query-dry-run",
                "--multi-query-query-count",
                "1",
                "--execute-publish",
                "--approval",
                "I_APPROVE_PUBLISH",
                "--github-action",
                "issue",
                "--github-branch",
                "launch",
                "--github-tag-name",
                "skill-entry-test",
                "--youtube-privacy-status",
                "unlisted",
                "--youtube-category-id",
                "28",
                "--published-url",
                "xiaohongshu=https://www.xiaohongshu.com/explore/note123",
                "--metrics-csv",
                str(metrics_csv),
                "--business-xlsx",
                str(business_xlsx),
                "--comment-evidence-html-file",
                str(comment_html),
                "--comment-evidence-install-browser-if-missing",
                "--skip-platform-access-audit",
                "--skip-final-capability-audit",
                "--skip-self-evolution-audit",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "output/reports/promotion-manager/skill-entry/skill-entry.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIn(report["status"], {"partial_ready", "partial_ready_blocked_by_platform_or_safety_limits", "partial_ready_waiting_external_evidence"})
        self.assertEqual(report["input"]["linkMode"], "auto")
        self.assertTrue(report["input"]["codexReadFirst"])
        self.assertEqual(report["input"]["discovery"]["topN"], 3)
        self.assertEqual(report["input"]["discovery"]["minScore"], 1.5)
        self.assertEqual(report["input"]["discovery"]["maxPages"], 2)
        self.assertEqual(report["input"]["discovery"]["maxDepth"], 0)
        self.assertEqual(report["input"]["discovery"]["maxSitemapUrls"], 4)
        self.assertEqual(report["input"]["discovery"]["timeout"], 5.0)
        self.assertTrue(report["input"]["discovery"]["skipSitemaps"])
        self.assertTrue(report["input"]["discovery"]["allowLocalhost"])
        self.assertEqual(report["summary"]["promotionRuns"], 1)
        self.assertTrue(report["input"]["publishExecutionRequested"])
        self.assertTrue(report["summary"]["publishExecutionRequested"])
        self.assertTrue(report["input"]["publishApprovalProvided"])
        self.assertTrue(report["summary"]["publishApprovalProvided"])
        self.assertEqual(report["summary"]["contentArtifacts"], 1)
        self.assertEqual(report["summary"]["launchUnlockPackRuns"], 1)
        self.assertTrue(Path(report["playbook"]["report"]).exists())
        self.assertTrue(Path(report["finalRun"]["report"]).exists())
        self.assertTrue(Path(report["readiness"]["report"]).exists())
        step_names = [item["name"] for item in report["steps"]]
        self.assertEqual(step_names, ["real_run_playbook", "final_capability_runner", "final_capability_readiness"])
        playbook_command = report["steps"][0]["command"]
        self.assertIn("--discovery-top-n", playbook_command)
        self.assertIn("3", playbook_command)
        self.assertIn("--discovery-skip-sitemaps", playbook_command)
        final_command = report["steps"][1]["command"]
        self.assertIn("--url", final_command)
        self.assertIn("--discover-from-url", final_command)
        self.assertIn("--discovery-top-n", final_command)
        self.assertIn("3", final_command)
        self.assertIn("--discovery-max-depth", final_command)
        self.assertIn("0", final_command)
        self.assertIn("--discovery-skip-sitemaps", final_command)
        self.assertIn("--discovery-allow-localhost", final_command)
        self.assertIn("--capture-browser-assisted-follow-ups", final_command)
        self.assertIn("--execute-publish", final_command)
        self.assertIn("--approval", final_command)
        self.assertIn("I_APPROVE_PUBLISH", final_command)
        self.assertIn("--github-action", final_command)
        self.assertIn("issue", final_command)
        self.assertIn("--github-branch", final_command)
        self.assertIn("launch", final_command)
        self.assertIn("--github-tag-name", final_command)
        self.assertIn("skill-entry-test", final_command)
        self.assertIn("--youtube-privacy-status", final_command)
        self.assertIn("unlisted", final_command)
        self.assertIn("--youtube-category-id", final_command)
        self.assertIn("28", final_command)
        self.assertIn("--published-url", final_command)
        self.assertIn("xiaohongshu=https://www.xiaohongshu.com/explore/note123", final_command)
        self.assertIn("--metrics-csv", final_command)
        self.assertIn(str(metrics_csv), final_command)
        self.assertIn("--business-xlsx", final_command)
        self.assertIn(str(business_xlsx), final_command)
        self.assertIn("--comment-evidence-html-file", final_command)
        self.assertIn(str(comment_html), final_command)
        self.assertIn("--comment-evidence-install-browser-if-missing", final_command)
        self.assertGreaterEqual(report["summary"]["capturedMetricRecords"], 1)
        self.assertGreaterEqual(report["summary"]["commentCount"], 2)
        self.assertTrue((out_dir / "output/reports/promotion-manager/skill-entry/skill-entry.md").exists())

    def test_skill_entry_can_run_browser_form_fill_from_one_link(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="skill-entry-form-fill-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_page = out_dir / "prompt-kit.html"
        product_page.write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit</title><meta name="description" content="Prompt templates for launch copy."></head>
<body><h1>AI Prompt Kit</h1><p>Turn one product URL into launch content.</p></body>
</html>""",
            encoding="utf-8",
        )
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "publish.html").write_text(
            """<!doctype html>
<html>
<head><title>Creator Publish Form</title></head>
<body>
  <form id="publish-form">
    <input name="title" placeholder="Title">
    <textarea name="body" placeholder="Body"></textarea>
    <input name="tags" placeholder="Tags">
    <input name="cover" placeholder="Cover">
    <button id="publish" type="submit">Publish</button>
  </form>
  <script>
    document.querySelector('#publish-form').addEventListener('submit', (event) => {
      event.preventDefault();
      document.body.dataset.submitted = 'yes';
    });
  </script>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        subprocess.run(
            [
                sys.executable,
                str(SKILL_ENTRY),
                "--link",
                product_page.as_uri(),
                "--link-mode",
                "product",
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-auto-search-competitors",
                "--skip-creator-follow-up",
                "--skip-follow-up-captures",
                "--skip-video-sampling",
                "--skip-video",
                "--multi-query-dry-run",
                "--multi-query-query-count",
                "1",
                "--platform-publish-url",
                f"xiaohongshu={base_url}/publish.html",
                "--run-browser-form-fill",
                "--browser-form-fill-allow-localhost",
                "--browser-form-fill-timeout-ms",
                "10000",
                "--skip-platform-access-audit",
                "--skip-final-capability-audit",
                "--skip-self-evolution-audit",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/skill-entry/skill-entry.json").read_text(encoding="utf-8"))
        final_command = report["steps"][1]["command"]
        self.assertIn("--run-browser-form-fill", final_command)
        self.assertIn("--browser-form-fill-allow-localhost", final_command)
        final_run = json.loads((out_dir / "output/reports/promotion-manager/final-run/final-capability-run.json").read_text(encoding="utf-8"))
        self.assertEqual(final_run["summary"]["browserFormFillRuns"], 1)
        self.assertEqual(final_run["summary"]["browserFormFillReady"], 1)
        fill_result = final_run["browserFormFill"][0]
        self.assertFalse(fill_result["submitted"])
        self.assertTrue(fill_result["finalPublishUserActionRequired"])
        self.assertTrue(Path(fill_result["screenshot"]).exists())

    def test_real_run_playbook_generates_end_to_end_command_pack_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="real-run-playbook-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        secret_value = "fake-secret-real-run-token"
        subprocess.run(
            [
                sys.executable,
                str(REAL_RUN_PLAYBOOK),
                "--url",
                "https://example.com/ai-prompt-kit",
                "--discover-from-url",
                "https://example.com/tools",
                "--discovery-html-file",
                "./catalog.html",
                "--discovery-sitemap-url",
                "https://example.com/sitemap.xml",
                "--discovery-sitemap-file",
                "./sitemap.xml",
                "--discovery-base-url",
                "https://example.com",
                "--discovery-top-n",
                "7",
                "--discovery-min-score",
                "2.5",
                "--discovery-max-pages",
                "9",
                "--discovery-max-depth",
                "3",
                "--discovery-max-sitemap-urls",
                "11",
                "--discovery-timeout",
                "4.5",
                "--discovery-include-external",
                "--discovery-skip-sitemaps",
                "--discovery-allow-localhost",
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--github-repo",
                "owner/repo",
                "--business-csv",
                "./orders-and-revenue.csv",
                "--business-xlsx",
                "./orders-and-revenue.xlsx",
                "--published-url",
                "github=https://github.com/owner/repo/blob/main/PROMOTION.md",
                "--platform-publish-url",
                "xiaohongshu=https://creator.example.test/publish",
                "--run-browser-form-fill",
                "--browser-form-fill-allow-localhost",
                "--browser-form-fill-timeout-ms",
                "12345",
                "--browser-form-fill-wait-until",
                "load",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env={**os.environ, "GITHUB_TOKEN": secret_value},
        )
        report_path = out_dir / "reports/promotion-manager/real-run-playbook/real-run-playbook.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["input"]["discoverFromUrl"], "https://example.com/tools")
        self.assertEqual(report["input"]["discovery"]["htmlFile"], "./catalog.html")
        self.assertEqual(report["input"]["discovery"]["sitemapUrl"], "https://example.com/sitemap.xml")
        self.assertEqual(report["input"]["discovery"]["sitemapFile"], "./sitemap.xml")
        self.assertEqual(report["input"]["discovery"]["baseUrl"], "https://example.com")
        self.assertEqual(report["input"]["discovery"]["topN"], 7)
        self.assertEqual(report["input"]["discovery"]["minScore"], 2.5)
        self.assertEqual(report["input"]["discovery"]["maxPages"], 9)
        self.assertEqual(report["input"]["discovery"]["maxDepth"], 3)
        self.assertEqual(report["input"]["discovery"]["maxSitemapUrls"], 11)
        self.assertEqual(report["input"]["discovery"]["timeout"], 4.5)
        self.assertTrue(report["input"]["discovery"]["includeExternal"])
        self.assertTrue(report["input"]["discovery"]["skipSitemaps"])
        self.assertTrue(report["input"]["discovery"]["allowLocalhost"])
        self.assertEqual(report["input"]["businessXlsx"], ["./orders-and-revenue.xlsx"])
        self.assertEqual(report["input"]["platformPublishUrl"], ["xiaohongshu=https://creator.example.test/publish"])
        self.assertTrue(report["input"]["runBrowserFormFill"])
        phase_ids = [item["id"] for item in report["phases"]]
        self.assertIn("real_full_run", phase_ids)
        self.assertIn("publish_preparation", phase_ids)
        self.assertIn("real_metrics_recovery", phase_ids)
        self.assertIn("controlled_self_evolution", phase_ids)
        commands = "\n".join(command["command"] for phase in report["phases"] for command in phase["commands"])
        self.assertIn("scripts/final_capability_runner.py", commands)
        self.assertIn("--discover-from-url https://example.com/tools", commands)
        self.assertIn("--discovery-html-file ./catalog.html", commands)
        self.assertIn("--discovery-sitemap-url https://example.com/sitemap.xml", commands)
        self.assertIn("--discovery-sitemap-file ./sitemap.xml", commands)
        self.assertIn("--discovery-base-url https://example.com", commands)
        self.assertIn("--discovery-top-n 7", commands)
        self.assertIn("--discovery-min-score 2.5", commands)
        self.assertIn("--discovery-max-pages 9", commands)
        self.assertIn("--discovery-max-depth 3", commands)
        self.assertIn("--discovery-max-sitemap-urls 11", commands)
        self.assertIn("--discovery-timeout 4.5", commands)
        self.assertIn("--discovery-include-external", commands)
        self.assertIn("--discovery-skip-sitemaps", commands)
        self.assertIn("--discovery-allow-localhost", commands)
        self.assertIn("--auto-search-competitors", commands)
        self.assertIn("--run-follow-up-captures", commands)
        self.assertIn("--capture-browser-assisted-follow-ups", commands)
        self.assertIn("--business-xlsx", commands)
        self.assertIn("./orders-and-revenue.xlsx", commands)
        self.assertIn("--platform-publish-url", commands)
        self.assertIn("xiaohongshu=https://creator.example.test/publish", commands)
        self.assertIn("--run-browser-form-fill", commands)
        self.assertIn("--browser-form-fill-timeout-ms 12345", commands)
        self.assertIn("--wait-until load", commands)
        self.assertIn("--multi-query-run-follow-up-captures", commands)
        self.assertIn("scripts/publish_setup_assistant.py", commands)
        self.assertIn("scripts/browser_publish_session.py", commands)
        self.assertIn("scripts/browser_publish_form_fill.py", commands)
        self.assertIn("scripts/metrics_recovery.py", commands)
        approvals = {command["approvalRequired"] for phase in report["phases"] for command in phase["commands"] if command["approvalRequired"]}
        self.assertEqual(approvals, {"I_APPROVE_PUBLISH", "I_APPROVE_SKILL_SYNC"})
        checklist_ids = {item["id"] for item in report["evidenceChecklist"]}
        self.assertIn("realPublishedUrls", checklist_ids)
        self.assertIn("realMetrics", checklist_ids)
        self.assertTrue(Path(report["artifacts"]["markdown"]).exists())
        self.assertTrue(Path(report["artifacts"]["powershell"]).exists())

    def test_final_capability_runner_can_fill_browser_publish_payloads(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="final-capability-form-fill-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_page = out_dir / "prompt-kit.html"
        product_page.write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit</title><meta name="description" content="Prompt templates for launch copy."></head>
<body><h1>AI Prompt Kit</h1><p>Turn one product URL into launch content.</p></body>
</html>""",
            encoding="utf-8",
        )
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "publish.html").write_text(
            """<!doctype html>
<html>
<head><title>Creator Publish Form</title></head>
<body>
  <form id="publish-form">
    <input name="title" placeholder="Title">
    <textarea name="body" placeholder="Body"></textarea>
    <input name="tags" placeholder="Tags">
    <input name="cover" placeholder="Cover">
    <button id="publish" type="submit">Publish</button>
  </form>
  <script>
    document.querySelector('#publish-form').addEventListener('submit', (event) => {
      event.preventDefault();
      document.body.dataset.submitted = 'yes';
    });
  </script>
</body>
</html>""",
            encoding="utf-8",
        )
        (site_dir / "note.html").write_text(
            "<!doctype html><html><body><p>views: 100 likes: 10 comments: 2</p></body></html>",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_RUNNER),
                "--url",
                product_page.as_uri(),
                "--skip-browser",
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--multi-query-dry-run",
                "--multi-query-query-count",
                "1",
                "--published-url",
                f"xiaohongshu={base_url}/note.html",
                "--post-publish-metrics-allow-localhost",
                "--platform-publish-url",
                f"xiaohongshu={base_url}/publish.html",
                "--run-browser-form-fill",
                "--browser-form-fill-allow-localhost",
                "--skip-platform-access-audit",
                "--skip-final-capability-audit",
                "--skip-self-evolution-audit",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads((out_dir / "output/reports/promotion-manager/final-run/final-capability-run.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["browserFormFillRuns"], 1)
        self.assertEqual(report["summary"]["browserFormFillReady"], 1)
        self.assertEqual(report["summary"]["browserFormFillErrors"], 0)
        self.assertGreaterEqual(report["summary"]["browserFormFillFilledFields"], 2)
        form_fill = report["browserFormFill"][0]
        self.assertEqual(form_fill["status"], "ready")
        self.assertFalse(form_fill["submitted"])
        self.assertTrue(form_fill["finalPublishUserActionRequired"])
        self.assertTrue(Path(form_fill["report"]).exists())
        self.assertTrue(Path(form_fill["screenshot"]).exists())

    def test_agent_workflow_runs_from_structured_snapshot(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-agent-workflow-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "pricing": "$19",
                    "targetAudience": ["AI operators", "content marketers"],
                    "painPoints": ["Blank page copywriting", "Slow launch content"],
                    "text": "AI Prompt Kit helps turn a product URL into platform-native promotion content.",
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--skip-video",
                "--top-n",
                "3",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        manifest_path = out_dir / "output/reports/promotion-manager/agent-run/workflow-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["product"]["name"], "AI Prompt Kit")
        self.assertEqual(manifest["input"]["sourceType"], "structured_json")
        self.assertEqual(manifest["competitorDiscovery"]["status"], "ready")
        self.assertIn("youtube", manifest["competitorDiscovery"]["platforms"])
        self.assertEqual(manifest["videoGeneration"][0]["status"], "skipped")
        self.assertEqual(manifest["metricsRecovery"]["status"], "waiting_real_data")
        publish_by_platform = {item["platform"]: item for item in manifest["publishAutomation"]}
        self.assertEqual(publish_by_platform["youtube"]["automationStatus"], "dry_run_ready_requires_credentials_and_approval")
        self.assertEqual(publish_by_platform["xiaohongshu"]["automationStatus"], "copy_pack_ready_manual_publish")
        self.assertFalse(manifest["selfEvolution"]["canInstallWithoutReview"])
        self.assertTrue((out_dir / "output/reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json").exists())
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/competitor-discovery.json").exists())

    def test_agent_workflow_runs_from_browser_url_when_browser_exists(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-browser-workflow-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "product.html"
        html_path.write_text(
            """<!doctype html>
<html>
<head>
  <title>AI Prompt Kit</title>
  <meta name="description" content="Prompt templates for product copy, SEO content, and video scripts.">
  <script type="application/ld+json">{"@type":"Product","name":"AI Prompt Kit","offers":{"price":"19"}}</script>
</head>
<body>
  <h1>AI Prompt Kit</h1>
  <p>Turn one product URL into platform-native promotion content. Start for $19.</p>
  <button>Start free</button>
</body>
</html>""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--browser-url",
                html_path.as_uri(),
                "--platforms",
                "github",
                "--skip-video",
                "--skip-competitor-discovery",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        manifest_path = out_dir / "output/reports/promotion-manager/agent-run/workflow-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["product"]["name"], "AI Prompt Kit")
        self.assertEqual(manifest["input"]["sourceType"], "browser_rendered_snapshot")
        self.assertTrue(Path(manifest["artifacts"]["browserSnapshot"]).exists())

    def test_platform_search_capture_imports_structured_results(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-search-capture-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "xiaohongshu.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "query": "AI product copy generator",
                    "items": [
                        {
                            "title": "7 prompts that turn one product page into launch content",
                            "url": "https://www.xiaohongshu.com/explore/test-note-1",
                            "creator": "Growth Notes",
                            "hook": "Stop rewriting the same product intro.",
                            "content": "Use one URL to create hooks, notes, and CTA variants. Try it with your next launch. comments 87 likes 1.2k saves 420",
                            "likes": "1.2k",
                            "favorites": "420",
                            "comments": "87",
                        },
                        {
                            "title": "Product launch content checklist",
                            "url": "https://www.xiaohongshu.com/explore/test-note-2",
                            "creator": "AI Operator",
                            "content": "Before posting, verify the claim, audience, offer, and evidence. likes 800 comments 35",
                            "likes": "800",
                            "comments": "35",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_SEARCH_CAPTURE),
                "--structured-json",
                str(snapshot_path),
                "--platform",
                "xiaohongshu",
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/competitors/captured-search-results-xiaohongshu.json").read_text(encoding="utf-8"))
        self.assertEqual(report["platform"], "xiaohongshu")
        self.assertEqual(report["recordCount"], 2)
        self.assertEqual(report["records"][0]["visibleMetrics"]["likes"]["normalized"], 1200.0)
        self.assertEqual(report["records"][0]["contentFormat"], "note")
        self.assertIn("contentDeconstruction", report["records"][0])
        self.assertGreaterEqual(report["records"][0]["contentDeconstruction"]["beatCount"], 1)
        self.assertIn("explicit_conversion_prompt", report["records"][0]["contentDeconstruction"]["copyMechanics"])
        self.assertEqual(report["aggregatePatterns"]["recordsWithObservedMetrics"], 2)

    def test_platform_search_capture_parses_chinese_visible_metrics(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-search-capture-chinese-metrics-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "douyin.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "query": "AI 产品推广",
                    "items": [
                        {
                            "title": "AI 工具站一条视频带来首批用户",
                            "url": "https://www.douyin.com/video/test-video-1",
                            "creator": "增长实验室",
                            "content": "开头先展示结果，再拆解工具站推广流程。播放量 1.2万 点赞 3.4k 收藏 560 评论 87 分享 42 粉丝 2万",
                        },
                        {
                            "title": "产品发布前要准备的内容清单",
                            "url": "https://www.douyin.com/video/test-video-2",
                            "creator": "AI 运营手记",
                            "content": "适合发布前自查。播放量 900 点赞 120 评论 9",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_SEARCH_CAPTURE),
                "--structured-json",
                str(snapshot_path),
                "--platform",
                "douyin",
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/competitors/captured-search-results-douyin.json").read_text(encoding="utf-8"))
        metrics = report["records"][0]["visibleMetrics"]
        self.assertEqual(metrics["views"]["normalized"], 12000.0)
        self.assertEqual(metrics["likes"]["normalized"], 3400.0)
        self.assertEqual(metrics["favorites"]["normalized"], 560.0)
        self.assertEqual(metrics["comments"]["normalized"], 87.0)
        self.assertEqual(metrics["shares"]["normalized"], 42.0)
        self.assertEqual(metrics["subscribers"]["normalized"], 20000.0)
        self.assertEqual(report["aggregatePatterns"]["recordsWithObservedMetrics"], 2)

    def test_platform_search_capture_filters_non_content_platform_pages(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-search-non-content-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "douyin.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "query": "AI product launch",
                    "items": [
                        {
                            "title": "用户协议",
                            "url": "https://www.douyin.com/agreements/?id=6773906068725565448",
                            "content": "privacy policy and user terms",
                        },
                        {
                            "title": "关于我们",
                            "url": "https://www.douyin.com/aboutus/",
                            "content": "company information",
                        },
                        {
                            "title": "AI launch video teardown",
                            "url": "https://www.douyin.com/video/7123456789012345678",
                            "creator": "Launch Lab",
                            "content": "A 30 second product launch teardown. 播放量 1.8万 点赞 2300 评论 91",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_SEARCH_CAPTURE),
                "--structured-json",
                str(snapshot_path),
                "--platform",
                "douyin",
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/competitors/captured-search-results-douyin.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recordCount"], 1)
        self.assertEqual(report["records"][0]["url"], "https://www.douyin.com/video/7123456789012345678")

    def test_viral_content_library_ranks_multiplatform_capture_reports(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="viral-content-library-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        capture_dir = out_dir / "captures"
        capture_dir.mkdir()
        (capture_dir / "captured-search-results-youtube.json").write_text(
            json.dumps(
                {
                    "platform": "youtube",
                    "query": "AI product copy generator",
                    "records": [
                        {
                            "id": "search-result-001",
                            "platform": "youtube",
                            "rank": 1,
                            "normalizedRank": 1,
                            "title": "One product URL into 30 launch videos",
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "creatorName": "Launch Lab",
                            "hook": "Your product page is already a content plan.",
                            "contentExcerpt": "views 120k likes 9k comments 500",
                            "visibleMetrics": {
                                "views": {"raw": "120k", "normalized": 120000.0},
                                "likes": {"raw": "9k", "normalized": 9000.0},
                                "comments": {"raw": "500", "normalized": 500.0},
                            },
                            "viralSignals": {"score": 160000.0, "hasObservedMetrics": True},
                            "reusablePatterns": ["visible_social_proof"],
                            "contentDeconstruction": {
                                "summary": "youtube/video structure hook -> proof with visible social proof.",
                                "beats": [{"order": 1, "role": "hook", "function": "stop-scroll opener or curiosity trigger"}],
                                "copyMechanics": ["visible_metric_proof"],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (capture_dir / "captured-search-results-xiaohongshu.json").write_text(
            json.dumps(
                {
                    "platform": "xiaohongshu",
                    "query": "AI product copy generator",
                    "records": [
                        {
                            "id": "search-result-001",
                            "platform": "xiaohongshu",
                            "rank": 1,
                            "normalizedRank": 1,
                            "title": "7 prompts that turn one product page into launch notes",
                            "url": "https://www.xiaohongshu.com/explore/test-note-1",
                            "creatorName": "Growth Notes",
                            "hook": "Stop rewriting the same product intro.",
                            "visibleMetrics": {"likes": {"raw": "1.2k", "normalized": 1200.0}},
                            "viralSignals": {"score": 5800.0, "hasObservedMetrics": True},
                            "reusablePatterns": ["numbered_title_or_claim"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(VIRAL_CONTENT_LIBRARY),
                "--search-capture-dir",
                str(capture_dir),
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        library = json.loads((out_dir / "output/reports/promotion-manager/competitors/viral-content-library.json").read_text(encoding="utf-8"))
        self.assertEqual(library["recordCount"], 2)
        self.assertEqual(library["materials"][0]["platform"], "youtube")
        self.assertEqual(library["materials"][0]["contentDeconstruction"]["summary"], "youtube/video structure hook -> proof with visible social proof.")
        self.assertEqual(library["materials"][0]["followUpCapture"]["mode"], "public_url_capture_candidate")
        self.assertEqual(library["materials"][1]["followUpCapture"]["mode"], "browser_assisted_capture_required")
        tasks = json.loads((out_dir / "output/reports/promotion-manager/competitors/follow-up-capture-tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(tasks["summary"]["modes"]["public_url_capture_candidate"], 1)
        self.assertEqual(tasks["summary"]["modes"]["browser_assisted_capture_required"], 1)
        self.assertIn(str(out_dir / "output"), tasks["tasks"][0]["command"])

    def test_viral_content_library_filters_non_content_platform_pages(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="viral-content-library-filter-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        capture_dir = out_dir / "captures"
        capture_dir.mkdir()
        (capture_dir / "captured-search-results-douyin.json").write_text(
            json.dumps(
                {
                    "platform": "douyin",
                    "query": "AI product launch",
                    "records": [
                        {
                            "id": "search-result-001",
                            "platform": "douyin",
                            "rank": 1,
                            "title": "用户协议",
                            "url": "https://www.douyin.com/agreements/?id=6773906068725565448",
                            "viralSignals": {"score": 9999},
                        },
                        {
                            "id": "search-result-002",
                            "platform": "douyin",
                            "rank": 2,
                            "title": "AI launch video teardown",
                            "url": "https://www.douyin.com/video/7123456789012345678",
                            "visibleMetrics": {"likes": {"raw": "2300", "normalized": 2300.0}},
                            "viralSignals": {"score": 2300, "hasObservedMetrics": True},
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(VIRAL_CONTENT_LIBRARY),
                "--search-capture-dir",
                str(capture_dir),
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        library = json.loads((out_dir / "output/reports/promotion-manager/competitors/viral-content-library.json").read_text(encoding="utf-8"))
        self.assertEqual(library["recordCount"], 1)
        self.assertEqual(library["materials"][0]["title"], "AI launch video teardown")

    def test_viral_evidence_inbox_setup_creates_empty_templates_without_fake_metrics(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="viral-evidence-inbox-setup-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        inbox_dir = out_dir / "viral-inbox"

        subprocess.run(
            [
                sys.executable,
                str(VIRAL_EVIDENCE_INBOX_SETUP),
                "--product-url",
                "https://www.enhe-tech.com.cn/software/windows-ai",
                "--product-name",
                "ENHE Windows AI",
                "--platforms",
                "youtube,xiaohongshu,douyin",
                "--inbox-dir",
                str(inbox_dir),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "reports/promotion-manager/competitors/viral-evidence-inbox-setup/viral-evidence-inbox-setup.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["platforms"], 3)
        self.assertEqual(report["summary"]["realCompetitorRecordsSeeded"], 0)
        self.assertEqual(report["summary"]["realMetricsSeeded"], 0)
        artifacts = {key: Path(value["path"]) for key, value in report["artifacts"].items()}
        for path in artifacts.values():
            self.assertTrue(path.exists(), path)
        source_csv = artifacts["sourceCsv"].read_text(encoding="utf-8-sig")
        copied_text = artifacts["copiedText"].read_text(encoding="utf-8")
        example = json.loads(artifacts["structuredExample"].read_text(encoding="utf-8"))
        self.assertIn("views", source_csv)
        self.assertEqual(len([line for line in source_csv.splitlines() if line.strip()]), 1)
        self.assertEqual(copied_text, "")
        self.assertTrue(example["exampleOnly"])
        self.assertTrue(example["doNotImportAsEvidence"])
        self.assertIn("viral_evidence_inbox.py", artifacts["importCommands"].read_text(encoding="utf-8"))

    def test_viral_evidence_inbox_imports_csv_and_keeps_screenshots_manual(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="viral-evidence-inbox-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        inbox_dir = out_dir / "viral-inbox"
        subprocess.run(
            [
                sys.executable,
                str(VIRAL_EVIDENCE_INBOX_SETUP),
                "--product-url",
                "https://www.enhe-tech.com.cn/software/windows-ai",
                "--platforms",
                "youtube,xiaohongshu,douyin",
                "--inbox-dir",
                str(inbox_dir),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        (inbox_dir / "viral-sources.csv").write_text(
            "\n".join(
                [
                    "platform,url,title,creatorName,contentFormat,hook,description,content,views,likes,favorites,comments,shares,subscribers,stars,forks,evidence,notes",
                    "youtube,https://www.youtube.com/watch?v=viral001,AI launch video teardown,Launch Lab,video,This product page became 30 videos,Observed breakdown,Hook proof CTA,120000,9000,,500,200,,,,public page,real visible metrics",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note001,AI 工具种草笔记,Growth Notes,note,别再手写产品介绍,Visible note text,痛点 对比 CTA,38000,4200,1600,260,90,,,,browser visible text,real copied note",
                    "douyin,https://www.douyin.com/video/7123456789012345678,30秒AI工具脚本,Shorts Lab,video,3秒说清产品价值,Visible video caption,开场 痛点 演示 CTA,98000,7800,1200,430,310,,,,OCR text,real copied caption",
                ]
            )
            + "\n",
            encoding="utf-8-sig",
        )
        (inbox_dir / "douyin-screenshot.png").write_bytes(b"not a real screenshot for unit test")

        subprocess.run(
            [
                sys.executable,
                str(VIRAL_EVIDENCE_INBOX),
                "--inbox-dir",
                str(inbox_dir),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "reports/promotion-manager/competitors/viral-evidence-inbox/viral-evidence-inbox.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["records"], 3)
        self.assertEqual(report["summary"]["captureReports"], 3)
        self.assertEqual(report["summary"]["screenshotEvidenceNeedingText"], 1)
        self.assertTrue(report["summary"]["libraryReady"])
        self.assertTrue(report["summary"]["creatorLeaderboardReady"])
        self.assertTrue(any(item["status"] == "manual_text_required" for item in report["sources"]))
        youtube_capture = json.loads(
            (out_dir / "reports/promotion-manager/competitors/captured-search-results-youtube.json").read_text(encoding="utf-8")
        )
        self.assertEqual(youtube_capture["recordCount"], 1)
        self.assertEqual(youtube_capture["records"][0]["creatorName"], "Launch Lab")
        library = json.loads((out_dir / "reports/promotion-manager/competitors/viral-content-library.json").read_text(encoding="utf-8"))
        leaderboard = json.loads((out_dir / "reports/promotion-manager/competitors/creator-leaderboard.json").read_text(encoding="utf-8"))
        self.assertEqual(library["recordCount"], 3)
        self.assertGreaterEqual(leaderboard["creatorCount"], 3)

    def test_creator_leaderboard_groups_viral_materials_by_creator(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="creator-leaderboard-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        library_path = out_dir / "viral-content-library.json"
        library_path.write_text(
            json.dumps(
                {
                    "materials": [
                        {
                            "id": "viral-material-001",
                            "libraryRank": 1,
                            "platform": "youtube",
                            "title": "One product URL into 30 launch videos",
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "creatorName": "Launch Lab",
                            "hook": "Your product page is already a content plan.",
                            "visibleMetrics": {
                                "views": {"raw": "120k", "normalized": 120000.0},
                                "likes": {"raw": "9k", "normalized": 9000.0},
                                "comments": {"raw": "500", "normalized": 500.0},
                            },
                            "viralSignals": {"score": 160000.0, "hasObservedMetrics": True},
                            "reusablePatterns": ["visible_social_proof"],
                            "followUpCapture": {"mode": "public_url_capture_candidate", "status": "ready"},
                        },
                        {
                            "id": "viral-material-002",
                            "libraryRank": 2,
                            "platform": "youtube",
                            "title": "Product copy system teardown",
                            "url": "https://www.youtube.com/watch?v=def456",
                            "creatorName": "Launch Lab",
                            "hook": "Stop writing launch copy from scratch.",
                            "visibleMetrics": {"views": {"raw": "80k", "normalized": 80000.0}},
                            "viralSignals": {"score": 85000.0, "hasObservedMetrics": True},
                            "reusablePatterns": ["explicit_call_to_action"],
                            "followUpCapture": {"mode": "public_url_capture_candidate", "status": "ready"},
                        },
                        {
                            "id": "viral-material-003",
                            "libraryRank": 3,
                            "platform": "xiaohongshu",
                            "title": "7 prompts that turn one product page into launch notes",
                            "url": "https://www.xiaohongshu.com/explore/test-note-1",
                            "creatorName": "Growth Notes",
                            "hook": "Stop rewriting the same product intro.",
                            "visibleMetrics": {"likes": {"raw": "1.2k", "normalized": 1200.0}},
                            "viralSignals": {"score": 5800.0, "hasObservedMetrics": True},
                            "reusablePatterns": ["numbered_title_or_claim"],
                            "followUpCapture": {"mode": "browser_assisted_capture_required", "status": "queued"},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(CREATOR_LEADERBOARD),
                "--viral-library",
                str(library_path),
                "--top-n",
                "10",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        leaderboard = json.loads((out_dir / "output/reports/promotion-manager/competitors/creator-leaderboard.json").read_text(encoding="utf-8"))
        self.assertEqual(leaderboard["creatorCount"], 2)
        self.assertEqual(leaderboard["creators"][0]["creatorName"], "Launch Lab")
        self.assertEqual(leaderboard["creators"][0]["materialCount"], 2)
        self.assertEqual(leaderboard["creators"][0]["metricTotals"]["views"], 200000.0)
        self.assertEqual(leaderboard["creators"][0]["trackingMode"], "public_or_official_research_candidate")
        self.assertEqual(leaderboard["creators"][1]["trackingMode"], "browser_assisted_or_user_export_required")
        tasks = json.loads((out_dir / "output/reports/promotion-manager/competitors/creator-follow-up-tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(tasks["taskCount"], 2)
        self.assertIn("Launch Lab", tasks["tasks"][0]["creatorName"])
        self.assertIn("official/public profile", tasks["tasks"][0]["requiredEvidence"][0])

    def test_creator_follow_up_runner_plans_public_and_queues_manual_tasks(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="creator-follow-up-runner-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        tasks_path = out_dir / "creator-follow-up-tasks.json"
        tasks_path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "creator-follow-up-001",
                            "creatorId": "creator-001",
                            "priority": 1,
                            "creatorName": "Launch Lab",
                            "platform": "youtube",
                            "trackingMode": "public_or_official_research_candidate",
                            "status": "ready",
                            "sampleUrls": ["https://www.youtube.com/watch?v=abc123"],
                            "requiredEvidence": ["official/public profile or channel URL"],
                        },
                        {
                            "id": "creator-follow-up-002",
                            "creatorId": "creator-002",
                            "priority": 2,
                            "creatorName": "Growth Notes",
                            "platform": "xiaohongshu",
                            "trackingMode": "browser_assisted_or_user_export_required",
                            "status": "queued_browser_assisted",
                            "sampleUrls": ["https://www.xiaohongshu.com/explore/test-note-1"],
                            "requiredEvidence": ["browser-visible creator profile or user export"],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(CREATOR_FOLLOW_UP_RUNNER),
                "--tasks-json",
                str(tasks_path),
                "--dry-run",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        result_path = out_dir / "output/reports/promotion-manager/competitors/creator-follow-up-results.json"
        report = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["statuses"]["dry_run"], 1)
        self.assertEqual(report["summary"]["statuses"]["queued_manual_evidence"], 1)
        self.assertIn("--platform", report["results"][0]["command"])
        evidence_path = Path(report["results"][1]["evidenceRequest"])
        self.assertTrue(evidence_path.exists())
        library = json.loads((out_dir / "output/reports/promotion-manager/competitors/creator-deep-library.json").read_text(encoding="utf-8"))
        self.assertEqual(library["recordCount"], 0)

    def test_follow_up_capture_runner_executes_public_and_queues_manual_tasks(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="follow-up-capture-runner-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "competitor.html").write_text(
            """<!doctype html>
<html>
<head>
  <title>Launch workflow repo</title>
  <meta name="description" content="Turn one product URL into a repeatable launch content workflow.">
</head>
<body>
  <h1>Launch workflow repo</h1>
  <p>Hook: your product page is already a campaign brief.</p>
  <p>Use it to generate titles, scripts, and GitHub launch copy. stars 42 forks 7</p>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/competitor.html"

        tasks_path = out_dir / "follow-up-capture-tasks.json"
        tasks_path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "follow-up-001",
                            "materialId": "viral-material-001",
                            "priority": 1,
                            "platform": "github",
                            "title": "Launch workflow repo",
                            "url": url,
                            "mode": "public_url_capture_candidate",
                            "status": "ready",
                            "requiredEvidence": ["public URL content"],
                        },
                        {
                            "id": "follow-up-002",
                            "materialId": "viral-material-002",
                            "priority": 2,
                            "platform": "xiaohongshu",
                            "title": "Launch note teardown",
                            "url": "https://www.xiaohongshu.com/explore/test-note-1",
                            "mode": "browser_assisted_capture_required",
                            "status": "queued",
                            "requiredEvidence": ["browser-visible page text"],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(FOLLOW_UP_CAPTURE_RUNNER),
                "--tasks-json",
                str(tasks_path),
                "--out-dir",
                str(out_dir / "output"),
                "--allow-localhost",
            ],
            check=True,
            cwd=ROOT,
        )
        results = json.loads((out_dir / "output/reports/promotion-manager/competitors/follow-up-capture-results.json").read_text(encoding="utf-8"))
        self.assertEqual(results["summary"]["statuses"]["ready"], 1)
        self.assertEqual(results["summary"]["statuses"]["queued_manual_evidence"], 1)
        deep = json.loads((out_dir / "output/reports/promotion-manager/competitors/deep-competitor-library.json").read_text(encoding="utf-8"))
        self.assertEqual(deep["recordCount"], 1)
        self.assertEqual(deep["records"][0]["platform"], "github")
        self.assertEqual(deep["records"][0]["sourceFollowUpTask"]["materialId"], "viral-material-001")
        self.assertIn("contentDeconstruction", deep["records"][0])
        self.assertIn("reuseGuidance", deep["records"][0]["contentDeconstruction"])
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/follow-up-captures/manual-evidence/follow-up-002.md").exists())

    def test_follow_up_capture_runner_imports_browser_visible_platform_page(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="follow-up-browser-capture-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head>
  <title>Launch note teardown</title>
  <meta name="description" content="A browser-visible launch note with creator and engagement evidence.">
</head>
<body>
  <article>
    <h1>Launch note teardown</h1>
    <p>Creator: Red Launch Lab</p>
    <p>Hook: turn one product URL into a week of short-form posts.</p>
    <p>Structure: pain point, demo, proof, save-worthy checklist.</p>
    <p>CTA: comment launch to get the checklist.</p>
    <p>likes 9000 comments 830 favorites 12000</p>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/note.html"

        tasks_path = out_dir / "follow-up-capture-tasks.json"
        tasks_path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "follow-up-001",
                            "materialId": "viral-material-001",
                            "priority": 1,
                            "platform": "xiaohongshu",
                            "title": "Launch note teardown",
                            "url": url,
                            "mode": "browser_assisted_capture_required",
                            "status": "queued",
                            "requiredEvidence": ["browser-visible page text"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(FOLLOW_UP_CAPTURE_RUNNER),
                "--tasks-json",
                str(tasks_path),
                "--capture-browser-assisted",
                "--allow-localhost",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        results = json.loads((out_dir / "output/reports/promotion-manager/competitors/follow-up-capture-results.json").read_text(encoding="utf-8"))
        self.assertEqual(results["summary"]["statuses"]["ready"], 1)
        self.assertEqual(results["summary"]["modes"]["browser_visible_capture"], 1)
        result = results["results"][0]
        self.assertTrue(Path(result["browserSnapshot"]).exists())
        self.assertTrue(Path(result["importedCompetitors"]).exists())
        deep = json.loads((out_dir / "output/reports/promotion-manager/competitors/deep-competitor-library.json").read_text(encoding="utf-8"))
        self.assertEqual(deep["recordCount"], 1)
        self.assertEqual(deep["records"][0]["platform"], "xiaohongshu")
        self.assertIn("Launch note teardown", deep["records"][0]["title"])
        self.assertIn("contentDeconstruction", deep["records"][0])
        self.assertGreaterEqual(deep["records"][0]["contentDeconstruction"]["beatCount"], 1)

    def test_follow_up_capture_runner_samples_video_frames(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="follow-up-video-sampling-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        video_path = site_dir / "sample.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x16a34a:s=320x180:d=2",
                "-pix_fmt",
                "yuv420p",
                str(video_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        (site_dir / "video.html").write_text(
            """<!doctype html>
<html>
<head><title>Launch video teardown</title></head>
<body>
  <h1>Launch video teardown</h1>
  <p>Hook: stop guessing the first three seconds.</p>
  <p>Voiceover: show pain, mechanism, proof, CTA.</p>
  <video controls width="320" height="180" src="/sample.mp4?token=secret-video-token"></video>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/video.html"
        tasks_path = out_dir / "follow-up-capture-tasks.json"
        tasks_path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "follow-up-video-001",
                            "materialId": "viral-video-001",
                            "priority": 1,
                            "platform": "youtube",
                            "title": "Launch video teardown",
                            "url": url,
                            "contentFormat": "video",
                            "mode": "public_url_capture_candidate",
                            "status": "ready",
                            "requiredEvidence": ["browser-visible video page"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(FOLLOW_UP_CAPTURE_RUNNER),
                "--tasks-json",
                str(tasks_path),
                "--sample-video-frames",
                "--video-sample-count",
                "2",
                "--allow-localhost",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        results_path = out_dir / "output/reports/promotion-manager/competitors/follow-up-capture-results.json"
        results = json.loads(results_path.read_text(encoding="utf-8"))
        self.assertEqual(results["summary"]["videoSampleRuns"], 1)
        self.assertEqual(results["summary"]["videoSampleReady"], 1)
        self.assertEqual(results["summary"]["videoSampleFrames"], 2)
        sample = results["results"][0]["videoSample"]
        self.assertEqual(sample["status"], "ready")
        self.assertEqual(sample["frameCount"], 2)
        self.assertTrue(Path(sample["report"]).exists())
        self.assertNotIn("secret-video-token", Path(sample["report"]).read_text(encoding="utf-8"))
        deep_path = out_dir / "output/reports/promotion-manager/competitors/deep-competitor-library.json"
        deep_text = deep_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-video-token", deep_text)
        deep = json.loads(deep_text)
        self.assertEqual(deep["aggregatePatterns"]["recordsWithVideoSampleEvidence"], 1)
        self.assertEqual(deep["aggregatePatterns"]["videoSampleFrames"], 2)
        deep_record = deep["records"][0]
        self.assertEqual(deep_record["videoSampleEvidence"]["frameCount"], 2)
        self.assertEqual(deep_record["contentDeconstruction"]["videoEvidence"]["frameCount"], 2)
        markdown = results_path.with_suffix(".md").read_text(encoding="utf-8")
        self.assertIn("Video sample report", markdown)

    def test_competitor_content_enhancer_writes_back_content_and_publish_pack(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="competitor-content-enhancer-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        content_path = out_dir / "ai-prompt-kit-platform-content.json"
        content_path.write_text(
            json.dumps(
                {
                    "youtube": {
                        "platform": "youtube",
                        "title": "AI Prompt Kit launch",
                        "description": "Base YouTube description.",
                        "shortVideoScript": "Base script.",
                        "voiceover": "Base voiceover.",
                        "storyboard": [],
                        "formats": {"videoScripts": ["Base script."]},
                        "sourceProduct": {"name": "AI Prompt Kit", "url": "https://example.com/ai-prompt-kit"},
                        "cta": "Try AI Prompt Kit",
                    },
                    "github": {
                        "platform": "github",
                        "title": "AI Prompt Kit repo launch",
                        "description": "Base GitHub description.",
                        "formats": {},
                        "sourceProduct": {"name": "AI Prompt Kit", "url": "https://example.com/ai-prompt-kit"},
                    },
                    "xiaohongshu": {
                        "platform": "xiaohongshu",
                        "title": "AI Prompt Kit note",
                        "description": "Base note.",
                        "formats": {},
                        "sourceProduct": {"name": "AI Prompt Kit", "url": "https://example.com/ai-prompt-kit"},
                    },
                    "douyin": {
                        "platform": "douyin",
                        "title": "AI Prompt Kit short video",
                        "description": "Base short video.",
                        "shortVideoScript": "Base short script.",
                        "voiceover": "Base voiceover.",
                        "storyboard": [],
                        "formats": {},
                        "sourceProduct": {"name": "AI Prompt Kit", "url": "https://example.com/ai-prompt-kit"},
                    },
                }
            ),
            encoding="utf-8",
        )
        viral_path = out_dir / "viral-content-library.json"
        viral_path.write_text(
            json.dumps(
                {
                    "materials": [
                        {
                            "platform": "youtube",
                            "title": "One product URL into 30 launch videos",
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "creatorName": "Launch Lab",
                            "hook": "Your product page is already a content plan.",
                            "reusablePatterns": ["numbered_title_or_claim", "visible_social_proof"],
                            "contentDeconstruction": {
                                "summary": "youtube/video structure hook -> problem -> solution -> cta with visible social proof.",
                                "beats": [
                                    {"order": 1, "role": "hook", "function": "stop-scroll opener or curiosity trigger"},
                                    {"order": 2, "role": "solution", "function": "shows the mechanism or promised path"},
                                ],
                            },
                            "viralSignals": {"score": 160000.0},
                            "visibleMetrics": {"views": {"raw": "120k", "normalized": 120000.0}},
                        },
                        {
                            "platform": "github",
                            "title": "Launch workflow repo",
                            "url": "https://github.com/example/launch-workflow",
                            "hook": "Stop writing launch copy from scratch.",
                            "reusablePatterns": ["explicit_call_to_action"],
                            "viralSignals": {"score": 4200.0},
                        },
                        {
                            "platform": "xiaohongshu",
                            "title": "7 prompts that turn one product page into launch notes",
                            "url": "https://www.xiaohongshu.com/explore/test-note-1",
                            "hook": "Stop rewriting the same product intro.",
                            "reusablePatterns": ["numbered_title_or_claim"],
                            "viralSignals": {"score": 5800.0},
                        },
                        {
                            "platform": "douyin",
                            "title": "One URL into 10 short videos",
                            "url": "https://www.douyin.com/video/123",
                            "hook": "Your product page is already a script.",
                            "reusablePatterns": ["visible_social_proof"],
                            "viralSignals": {"score": 9600.0},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        publish_pack_path = out_dir / "ai-prompt-kit-publish-pack.json"
        publish_pack_path.write_text(
            json.dumps(
                [
                    {"platform": "youtube", "content": {"title": "Old title"}},
                    {"platform": "github", "content": {"title": "Old repo title"}},
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(COMPETITOR_CONTENT_ENHANCER),
                "--content-json",
                str(content_path),
                "--viral-library",
                str(viral_path),
                "--publish-pack",
                str(publish_pack_path),
                "--write-back",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        enhanced = json.loads(content_path.read_text(encoding="utf-8"))
        self.assertEqual(enhanced["youtube"]["competitorInformed"]["status"], "ready")
        self.assertIn("youtube/video structure", enhanced["youtube"]["competitorInformed"]["deconstructionSummaries"][0])
        self.assertIn("stop-scroll opener", enhanced["youtube"]["competitorInformed"]["beatFunctions"][0])
        self.assertIn("Your product page is already a content plan", enhanced["youtube"]["shortVideoScript"])
        self.assertIn("Observed viral pattern", enhanced["xiaohongshu"]["description"])
        self.assertIn("Observed viral pattern", enhanced["douyin"]["voiceover"])
        self.assertTrue((out_dir / "ai-prompt-kit-platform-content.base.json").exists())
        self.assertTrue((out_dir / "output/reports/promotion-manager/generated-content/ai-prompt-kit-competitor-informed-content.json").exists())
        publish_pack = json.loads(publish_pack_path.read_text(encoding="utf-8"))
        self.assertEqual(publish_pack[0]["content"]["competitorInformed"]["status"], "ready")
        self.assertIn("AI Prompt Kit", publish_pack[1]["content"]["formats"]["readmePromotion"])

    def test_agent_workflow_uses_competitor_informed_content_before_video_and_publish(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-competitor-informed-workflow-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_path = out_dir / "product.json"
        product_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        snapshot_dir = out_dir / "search"
        snapshot_dir.mkdir()
        (snapshot_dir / "youtube.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "title": "One product URL into 30 launch videos",
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "creatorName": "Launch Lab",
                            "hook": "Your product page is already a content plan.",
                            "content": "views 120k likes 9k comments 500",
                            "views": "120k",
                            "likes": "9k",
                            "comments": "500",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(product_path),
                "--platforms",
                "youtube",
                "--search-snapshot-dir",
                str(snapshot_dir),
                "--use-competitor-informed-content",
                "--skip-video",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        manifest = json.loads((out_dir / "output/reports/promotion-manager/agent-run/workflow-manifest.json").read_text(encoding="utf-8"))
        enhancer_run = manifest["competitorDiscovery"]["competitorInformedContent"]
        self.assertEqual(enhancer_run["status"], "ready")
        self.assertTrue(Path(manifest["artifacts"]["competitorInformedContent"]).exists())
        content = json.loads(Path(manifest["artifacts"]["contentJson"]).read_text(encoding="utf-8"))
        self.assertEqual(content["youtube"]["competitorInformed"]["status"], "ready")
        self.assertIn("Your product page is already a content plan", content["youtube"]["shortVideoScript"])

    def test_platform_search_browser_generates_snapshots_from_saved_html(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-search-browser-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_dir = out_dir / "html"
        html_dir.mkdir()
        (html_dir / "youtube.html").write_text(
            """<!doctype html>
<html>
<head><title>YouTube search</title></head>
<body>
  <section>
    <a href="https://www.youtube.com/watch?v=abc123">One URL into 30 launch videos</a>
    <p>Launch Lab shows a product URL workflow. views 120k likes 9k comments 500</p>
  </section>
  <section>
    <a href="https://www.youtube.com/watch?v=def456">Product copy system teardown</a>
    <p>Breaks title, hook, proof, and CTA. views 80k likes 5k comments 240</p>
  </section>
</body>
</html>""",
            encoding="utf-8",
        )
        snapshot_dir = out_dir / "snapshots"
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_SEARCH_BROWSER),
                "--query",
                "AI product copy generator",
                "--platforms",
                "youtube",
                "--html-snapshot-dir",
                str(html_dir),
                "--snapshot-dir",
                str(snapshot_dir),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        snapshot = json.loads((snapshot_dir / "youtube.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["platform"], "youtube")
        self.assertEqual(snapshot["captureMode"], "saved_html_snapshot")
        self.assertEqual(len(snapshot["items"]), 2)
        self.assertIn("One URL", snapshot["items"][0]["title"])
        summary = json.loads((out_dir / "output/reports/promotion-manager/competitors/browser-search-snapshots.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["records"][0]["status"], "ready")

    def test_platform_search_browser_uses_firecrawl_search_fixture(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-search-firecrawl-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        fixture = out_dir / "firecrawl-search.json"
        fixture.write_text(
            json.dumps(
                {
                    "search": {
                        "data": [
                            {
                                "url": "https://www.youtube.com/watch?v=firecrawl123",
                                "title": "One product URL into a launch engine",
                                "markdown": "Public result with views 120k likes 9k and a strong hook.",
                            },
                            {
                                "url": "https://example.com/not-youtube",
                                "title": "Wrong platform",
                                "markdown": "Should be filtered by platform.",
                            },
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        snapshot_dir = out_dir / "snapshots"
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_SEARCH_BROWSER),
                "--query",
                "AI product promotion",
                "--platforms",
                "youtube",
                "--web-data-provider",
                "firecrawl",
                "--web-data-fixture-json",
                str(fixture),
                "--snapshot-dir",
                str(snapshot_dir),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        snapshot = json.loads((snapshot_dir / "youtube.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["captureMode"], "firecrawl_search")
        self.assertEqual(len(snapshot["items"]), 1)
        self.assertIn("site:youtube.com", snapshot["webDataQuery"])

    def test_platform_capabilities_registry_outputs_monetization_blueprint(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-capabilities-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_CAPABILITIES),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "output/reports/promotion-manager/capability/platform-capabilities.json").read_text(encoding="utf-8"))
        platforms = {item["platform"] for item in report["platforms"]}
        self.assertIn("youtube", platforms)
        self.assertIn("xiaohongshu", platforms)
        self.assertEqual(report["monetizationBlueprint"]["status"], "blueprint_ready")
        self.assertEqual(report["relayBridgePolicy"]["status"], "temporary_optional_bridge")
        self.assertIn("loginCookie storage", report["inspiredBy"]["AiToEarn"]["rejected"])
        self.assertIn("opaque third-party relay as the long-term core security promise", report["inspiredBy"]["AiToEarn"]["rejected"])
        self.assertIn("Chrome/Edge store builds do not implement automatic like, follow, comment, or DM actions.", report["guardrails"])
        by_platform = {item["platform"]: item for item in report["platforms"]}
        self.assertEqual(by_platform["douyin"]["publish"]["defaultMode"], "browser_assisted_publish_pack")
        self.assertEqual(by_platform["douyin"]["publish"]["requiredEnv"], [])

    def test_completion_roadmap_outputs_module_gaps_and_operator_steps(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="completion-roadmap-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(COMPLETION_ROADMAP),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "output/reports/promotion-manager/capability/completion-roadmap.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "roadmap_ready")
        modules = {item["id"]: item for item in report["modules"]}
        self.assertIn("codex_skill_local_promotion_loop", modules)
        self.assertIn("true_all_platform_auto_publish", modules)
        self.assertIn("creator_tasks_settlement_monetize_marketplace", modules)
        self.assertEqual(modules["true_all_platform_auto_publish"]["currentEstimate"], 40)
        self.assertTrue(modules["true_all_platform_auto_publish"]["operatorExternalGates"])
        self.assertTrue(modules["creator_tasks_settlement_monetize_marketplace"]["operatorSteps"])
        references = {item["project"] for item in report["openSourceReferences"]}
        self.assertIn("firecrawl/firecrawl", references)
        self.assertIn("yikart/AiToEarn", references)
        self.assertIn("cookie capture", report["summary"]["unsafeShortcutsRejected"])
        self.assertTrue((out_dir / "output/reports/promotion-manager/capability/completion-roadmap.md").exists())

    def test_operator_action_checklist_outputs_chinese_beginner_steps(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="operator-action-checklist-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(OPERATOR_ACTION_CHECKLIST),
                "--out-dir",
                str(out_dir / "output"),
                "--product-url",
                "https://example.com/real-product",
                "--github-repo",
                "hqwzhu/Viral-Product-Copy-Video-Generator",
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "output/reports/promotion-manager/capability/operator-action-checklist.zh-CN.json"
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        self.assertEqual(report["status"], "operator_action_checklist_ready")
        self.assertEqual(report["language"], "zh-CN")
        modules = {item["id"]: item for item in report["modules"]}
        self.assertIn("true_all_platform_auto_publish", modules)
        self.assertIn("创作者任务", modules["creator_tasks_settlement_monetize_marketplace"]["name"])
        self.assertTrue(modules["codex_skill_local_promotion_loop"]["beginnerSteps"])
        self.assertIn("https://example.com/real-product", report["copyReadyCommands"]["真实产品本地闭环"])
        self.assertIn("cookie capture", report["rejectedShortcuts"])
        self.assertTrue(report["acceptanceRule"])
        markdown = (out_dir / "output/reports/promotion-manager/capability/operator-action-checklist.zh-CN.md").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("100% 完成操作清单", markdown)
        self.assertIn("新手逐步执行", markdown)
        self.assertIn("验收证据", markdown)

    def test_agent_workflow_auto_searches_competitors_from_saved_html(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-auto-search-workflow-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_path = out_dir / "product.json"
        product_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        html_dir = out_dir / "html"
        html_dir.mkdir()
        (html_dir / "youtube.html").write_text(
            """<!doctype html>
<html><body>
  <article>
    <a href="https://www.youtube.com/watch?v=abc123">One URL into 30 launch videos</a>
    <p>Hook: your product page is already a content plan. views 120k likes 9k comments 500</p>
  </article>
</body></html>""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(product_path),
                "--platforms",
                "youtube",
                "--auto-search-competitors",
                "--search-html-snapshot-dir",
                str(html_dir),
                "--skip-video",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        manifest = json.loads((out_dir / "output/reports/promotion-manager/agent-run/workflow-manifest.json").read_text(encoding="utf-8"))
        browser_search = manifest["competitorDiscovery"]["browserSearchSnapshots"]
        self.assertEqual(browser_search["status"], "ready")
        self.assertEqual(browser_search["records"][0]["recordCount"], 1)
        captures = manifest["competitorDiscovery"]["searchCaptures"]
        self.assertEqual(captures[0]["status"], "ready")
        self.assertEqual(captures[0]["recordCount"], 1)
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/captured-search-results-youtube.json").exists())

    def test_agent_workflow_captures_search_snapshot_directory(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-search-snapshot-workflow-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        product_path = out_dir / "product.json"
        product_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        snapshot_dir = out_dir / "search"
        snapshot_dir.mkdir()
        (snapshot_dir / "douyin.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "title": "One URL into 10 short videos",
                            "url": "https://www.douyin.com/video/123",
                            "creatorName": "Launch Lab",
                            "content": "Hook: your product page is already a script. views 120k likes 9k comments 500",
                            "views": "120k",
                            "likes": "9k",
                            "comments": "500",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(product_path),
                "--platforms",
                "douyin",
                "--search-snapshot-dir",
                str(snapshot_dir),
                "--run-creator-follow-up",
                "--creator-follow-up-dry-run",
                "--run-follow-up-captures",
                "--skip-video",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        manifest = json.loads((out_dir / "output/reports/promotion-manager/agent-run/workflow-manifest.json").read_text(encoding="utf-8"))
        captures = manifest["competitorDiscovery"]["searchCaptures"]
        self.assertEqual(captures[0]["platform"], "douyin")
        self.assertEqual(captures[0]["status"], "ready")
        self.assertEqual(captures[0]["recordCount"], 1)
        report_path = out_dir / "output/reports/promotion-manager/competitors/captured-search-results-douyin.json"
        self.assertTrue(report_path.exists())
        viral_library = manifest["competitorDiscovery"]["viralContentLibrary"]
        self.assertEqual(viral_library["status"], "ready")
        self.assertEqual(viral_library["recordCount"], 1)
        self.assertTrue(Path(viral_library["library"]).exists())
        creator_leaderboard = manifest["competitorDiscovery"]["creatorLeaderboard"]
        self.assertEqual(creator_leaderboard["status"], "ready")
        self.assertEqual(creator_leaderboard["creatorCount"], 1)
        self.assertTrue(Path(manifest["artifacts"]["creatorLeaderboard"]).exists())
        creator_follow_up = manifest["competitorDiscovery"]["creatorFollowUpRun"]
        self.assertEqual(creator_follow_up["status"], "ready")
        self.assertEqual(creator_follow_up["deepRecordCount"], 0)
        self.assertEqual(creator_follow_up["resultSummary"]["statuses"]["queued_manual_evidence"], 1)
        self.assertTrue(Path(manifest["artifacts"]["creatorFollowUpResults"]).exists())
        library = json.loads(Path(viral_library["library"]).read_text(encoding="utf-8"))
        self.assertEqual(library["materials"][0]["platform"], "douyin")
        self.assertEqual(library["materials"][0]["followUpCapture"]["mode"], "browser_assisted_capture_required")
        follow_up = manifest["competitorDiscovery"]["followUpCaptureRun"]
        self.assertEqual(follow_up["status"], "ready")
        self.assertEqual(follow_up["deepRecordCount"], 0)
        self.assertEqual(follow_up["resultSummary"]["statuses"]["queued_manual_evidence"], 1)
        self.assertTrue(Path(follow_up["results"]).exists())

    def test_automation_scheduler_runs_due_workflow_job(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "pricing": "$19",
                    "targetAudience": ["AI operators", "content marketers"],
                    "painPoints": ["Blank page copywriting", "Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["youtube", "douyin", "github"],
                            "topN": 2,
                            "skipVideo": True,
                            "publish": {"enabled": False, "mode": "approval_required"},
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-weekly"]
        self.assertEqual(job_state["lastStatus"], "ready")
        manifest_path = Path(job_state["lastManifest"])
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["product"]["name"], "AI Prompt Kit")
        self.assertEqual(manifest["videoGeneration"][0]["status"], "skipped")
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        self.assertEqual(run_report["records"][0]["status"], "ready")
        self.assertFalse(run_report["records"][0]["publish"]["enabled"])

    def test_automation_scheduler_can_run_publish_queue_after_workflow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-publish-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        business_csv = out_dir / "business.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,clicks,orders,revenue,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,90,2,$88.00,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-publish-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["github", "xiaohongshu"],
                            "topN": 2,
                            "skipVideo": True,
                            "publish": {
                                "enabled": True,
                                "platforms": ["github", "xiaohongshu"],
                                "github": {
                                    "repo": "hqwzhu/Viral-Product-Copy-Video-Generator",
                                    "action": "file",
                                    "path": "PROMOTION.md",
                                },
                            },
                            "browserPublishAssistant": {
                                "enabled": True,
                                "platformPublishUrls": {"xiaohongshu": "https://creator.example.test/publish"},
                                "publishedUrls": ["xiaohongshu=https://www.xiaohongshu.com/explore/note123"],
                                "evidence": ["xhs-published.png"],
                            },
                            "metricsRecovery": {
                                "enabled": True,
                                "businessCsv": "business.csv",
                            },
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-publish-weekly"]
        self.assertEqual(job_state["lastStatus"], "ready")
        self.assertTrue(Path(job_state["lastPublishQueue"]).exists())
        self.assertTrue(Path(job_state["lastBrowserPublishAssistant"]).exists())
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        publish_queue = run_report["records"][0]["publishQueue"]
        self.assertEqual(publish_queue["status"], "ready")
        self.assertEqual(publish_queue["summary"]["officialDryRuns"], 1)
        self.assertEqual(publish_queue["summary"]["manualQueued"], 1)
        browser_publish = run_report["records"][0]["browserPublishAssistant"]
        self.assertEqual(browser_publish["status"], "ready")
        self.assertEqual(browser_publish["summary"]["prepared"], 1)
        self.assertEqual(browser_publish["summary"]["registeredPublishedUrls"], 1)
        self.assertTrue(Path(job_state["lastMetricsRecovery"]).exists())
        recovery = run_report["records"][0]["metricsRecovery"]
        self.assertEqual(recovery["status"], "ready")
        self.assertEqual(recovery["summary"]["recordsWithMetrics"], 1)

    def test_automation_scheduler_runs_browser_form_fill_after_publish_payloads(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-form-fill-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "publish.html").write_text(
            """<!doctype html>
<html>
<head><title>Creator Publish Form</title></head>
<body>
  <form id="publish-form">
    <input name="title" placeholder="Title">
    <textarea name="body" placeholder="Body"></textarea>
    <input name="tags" placeholder="Tags">
    <input name="cover" placeholder="Cover">
    <button id="publish" type="submit">Publish</button>
  </form>
  <script>
    document.querySelector('#publish-form').addEventListener('submit', (event) => {
      event.preventDefault();
      document.body.dataset.submitted = 'yes';
    });
  </script>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-form-fill-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["xiaohongshu"],
                            "topN": 2,
                            "skipVideo": True,
                            "publish": {"enabled": True, "platforms": ["xiaohongshu"]},
                            "browserPublishAssistant": {
                                "enabled": True,
                                "platformPublishUrls": {"xiaohongshu": f"{base_url}/publish.html"},
                            },
                            "browserFormFill": {
                                "enabled": True,
                                "allowLocalhost": True,
                                "timeoutMs": 10000,
                            },
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-form-fill-weekly"]
        self.assertEqual(job_state["lastStatus"], "ready")
        self.assertEqual(len(job_state["lastBrowserFormFill"]), 1)
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        form_fill = run_report["records"][0]["browserFormFill"]
        self.assertEqual(form_fill["status"], "ready")
        self.assertEqual(form_fill["summary"]["runs"], 1)
        self.assertEqual(form_fill["summary"]["ready"], 1)
        self.assertEqual(form_fill["summary"]["submitted"], 0)
        self.assertGreaterEqual(form_fill["summary"]["filledFields"], 2)
        record = form_fill["records"][0]
        self.assertEqual(record["platform"], "xiaohongshu")
        self.assertFalse(record["submitted"])
        self.assertTrue(record["finalPublishUserActionRequired"])
        self.assertTrue(Path(record["report"]).exists())
        self.assertTrue(Path(record["screenshot"]).exists())

    def test_automation_scheduler_passes_douyin_video_file_to_publish_queue(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-douyin-publish-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        video_path = out_dir / "douyin-draft.mp4"
        video_path.write_bytes(b"dry-run douyin video placeholder")
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-douyin-publish-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["douyin"],
                            "skipVideo": True,
                            "publish": {
                                "enabled": True,
                                "platforms": ["douyin"],
                                "douyin": {"videoFile": "douyin-draft.mp4"},
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        publish_queue = run_report["records"][0]["publishQueue"]
        self.assertEqual(publish_queue["status"], "ready")
        self.assertEqual(publish_queue["summary"]["officialDryRuns"], 0)
        self.assertEqual(publish_queue["summary"]["browserQueued"], 1)
        queue = json.loads(Path(publish_queue["report"]).read_text(encoding="utf-8"))
        record = queue["records"][0]
        self.assertEqual(record["platform"], "douyin")
        self.assertEqual(record["publishMode"], "browser_assisted_publish")
        self.assertEqual(record["status"], "queued_browser_assisted")
        self.assertEqual(record["video"]["path"], str(video_path))
        self.assertNotIn("officialExecution", record)

    def test_automation_scheduler_runs_business_attribution_before_recovery(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-attribution-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        published_items_path = out_dir / "published-items.json"
        published_items_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "contentId": "xhs-note-123",
                            "title": "Launch Note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        orders_csv = out_dir / "orders.csv"
        orders_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,utm_content,revenue,status",
                    "order-1,xiaohongshu,xhs-note-123,88.00,paid",
                    "order-2,xiaohongshu,xhs-note-123,32.00,paid",
                ]
            ),
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-attribution-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["xiaohongshu"],
                            "topN": 1,
                            "skipVideo": True,
                            "businessAttribution": {
                                "enabled": True,
                                "businessCsv": "orders.csv",
                                "publishedItemsJson": "published-items.json",
                            },
                            "metricsRecovery": {"enabled": True},
                            "nextRoundOptimization": {"enabled": True},
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-attribution-weekly"]
        self.assertTrue(Path(job_state["lastBusinessAttribution"]).exists())
        self.assertTrue(Path(job_state["lastMetricsRecovery"]).exists())
        self.assertTrue(Path(job_state["lastNextRoundOptimization"]).exists())
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        attribution = run_report["records"][0]["businessAttribution"]
        self.assertEqual(attribution["status"], "ready")
        self.assertEqual(attribution["summary"]["matchedRows"], 2)
        recovery = run_report["records"][0]["metricsRecovery"]
        self.assertEqual(recovery["status"], "ready")
        self.assertEqual(recovery["summary"]["recordsWithMetrics"], 1)
        optimization = run_report["records"][0]["nextRoundOptimization"]
        self.assertEqual(optimization["status"], "partial_ready")
        self.assertTrue(Path(optimization["report"]).exists())

    def test_automation_scheduler_accepts_xlsx_evidence_sources(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-xlsx-evidence-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        published_items_path = out_dir / "published-items.json"
        published_items_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "contentId": "note123",
                            "title": "Launch Note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        metrics_xlsx = out_dir / "metrics.xlsx"
        write_minimal_xlsx(
            metrics_xlsx,
            [
                ["platform", "publishedUrl", "title", "view_count", "like_count", "comment_count", "evidence"],
                ["xiaohongshu", "https://www.xiaohongshu.com/explore/note123", "Launch Note", "4200", "360", "41", "xhs-export.xlsx"],
            ],
        )
        orders_xlsx = out_dir / "orders.xlsx"
        write_minimal_xlsx(
            orders_xlsx,
            [
                ["orderId", "utm_source", "utm_content", "revenue", "status"],
                ["order-1", "xiaohongshu", "note123", "88.00", "paid"],
                ["order-2", "xiaohongshu", "note123", "32.00", "paid"],
            ],
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-xlsx-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["xiaohongshu"],
                            "topN": 1,
                            "skipVideo": True,
                            "metrics": {"xlsxFile": "metrics.xlsx"},
                            "businessAttribution": {
                                "enabled": True,
                                "businessXlsx": "orders.xlsx",
                                "publishedItemsJson": "published-items.json",
                            },
                            "metricsRecovery": {
                                "enabled": True,
                                "metricsXlsx": "metrics.xlsx",
                                "publishedItemsJson": "published-items.json",
                            },
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        record = run_report["records"][0]
        self.assertIn("--metrics-xlsx", record["command"])
        self.assertIn("--business-xlsx", record["businessAttribution"]["command"])
        self.assertIn("--metrics-xlsx", record["metricsRecovery"]["command"])
        self.assertEqual(record["businessAttribution"]["summary"]["matchedRows"], 2)
        self.assertEqual(record["metricsRecovery"]["summary"]["recordsWithMetrics"], 1)
        attribution = json.loads(Path(record["businessAttribution"]["report"]).read_text(encoding="utf-8"))
        self.assertEqual(attribution["sources"][0]["type"], "business_xlsx")
        recovery = json.loads(Path(record["metricsRecovery"]["report"]).read_text(encoding="utf-8"))
        self.assertEqual(recovery["metricSources"][0]["type"], "metrics_xlsx")

    def test_automation_scheduler_passes_real_evidence_file_sources(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-evidence-command-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        module = load_script_module(AUTOMATION_SCHEDULER)
        job = {
            "metricsRecovery": {
                "enabled": True,
                "metricsCsv": "metrics.csv",
                "metricsJson": ["metrics.json"],
                "metricsText": "metrics.txt",
                "metricsStructuredJson": "metrics-structured.json",
                "businessText": "orders.txt",
            },
            "commentEvidenceCapture": {
                "enabled": True,
                "platform": "xiaohongshu",
                "structuredJson": "comments-structured.json",
                "htmlFile": "comments.html",
                "textFile": "comments.txt",
                "captureBrowserAssisted": True,
                "installBrowserIfMissing": True,
                "allowLocalhost": True,
            },
            "businessAttribution": {
                "enabled": True,
                "businessText": "orders.txt",
                "publishedItemsJson": "published-items.json",
            },
        }
        manifest_path = out_dir / "workflow-manifest.json"
        recovery_command = module.build_metrics_recovery_command(job, out_dir / "run", out_dir, manifest_path, "")
        self.assertIn("--metrics-csv", recovery_command)
        self.assertIn(str((out_dir / "metrics.csv").resolve()), recovery_command)
        self.assertIn("--metrics-json", recovery_command)
        self.assertIn(str((out_dir / "metrics.json").resolve()), recovery_command)
        self.assertIn("--metrics-text", recovery_command)
        self.assertIn(str((out_dir / "metrics.txt").resolve()), recovery_command)
        self.assertIn("--metrics-structured-json", recovery_command)
        self.assertIn(str((out_dir / "metrics-structured.json").resolve()), recovery_command)
        self.assertIn("--business-text", recovery_command)
        self.assertIn(str((out_dir / "orders.txt").resolve()), recovery_command)

        comment_command = module.build_comment_evidence_capture_command(job, out_dir / "run", out_dir)
        for flag in ("--platform", "--structured-json", "--html-file", "--text-file", "--capture-browser-assisted", "--install-browser-if-missing", "--allow-localhost"):
            self.assertIn(flag, comment_command)
        self.assertIn("xiaohongshu", comment_command)
        self.assertIn(str((out_dir / "comments-structured.json").resolve()), comment_command)
        self.assertIn(str((out_dir / "comments.html").resolve()), comment_command)
        self.assertIn(str((out_dir / "comments.txt").resolve()), comment_command)

        attribution_command = module.build_business_attribution_command(job, out_dir / "run", out_dir)
        self.assertIn("--business-text", attribution_command)
        self.assertIn(str((out_dir / "orders.txt").resolve()), attribution_command)
        self.assertIn("--published-items-json", attribution_command)
        self.assertIn(str((out_dir / "published-items.json").resolve()), attribution_command)

    def test_automation_scheduler_runs_post_publish_metrics_capture_before_recovery(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-post-metrics-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>Launch Note Metrics</title></head>
<body><h1>Launch Note Metrics</h1><p>views: 4,200 likes: 360 comments: 41 orders: 3 revenue: $99.00</p></body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        published_url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        published_items_path = out_dir / "published-items.json"
        published_items_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": published_url,
                            "title": "Launch Note Metrics",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-post-metrics-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["xiaohongshu"],
                            "topN": 1,
                            "skipVideo": True,
                            "postPublishMetricsCapture": {
                                "enabled": True,
                                "publishedItemsJson": "published-items.json",
                                "allowLocalhost": True,
                            },
                            "metricsRecovery": {"enabled": True},
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-post-metrics-weekly"]
        self.assertTrue(Path(job_state["lastPostPublishMetricsCapture"]).exists())
        self.assertTrue(Path(job_state["lastMetricsRecovery"]).exists())
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        capture = run_report["records"][0]["postPublishMetricsCapture"]
        self.assertEqual(capture["status"], "ready")
        self.assertEqual(capture["summary"]["capturedMetricRecords"], 1)
        recovery = run_report["records"][0]["metricsRecovery"]
        self.assertEqual(recovery["status"], "ready")
        self.assertEqual(recovery["summary"]["recordsWithMetrics"], 1)

    def test_automation_scheduler_runs_comment_evidence_capture_after_workflow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-comment-evidence-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        comments_path = out_dir / "comments.html"
        comments_path.write_text(
            """<!doctype html>
<html><body>
<p>Comment by Alice: How does pricing work? likes: 9</p>
<p>Bob: Need Slack integration replies: 1</p>
</body></html>""",
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-comment-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["xiaohongshu"],
                            "topN": 1,
                            "skipVideo": True,
                            "commentEvidenceCapture": {
                                "enabled": True,
                                "htmlFile": "comments.html",
                                "publishedUrls": ["xiaohongshu=https://www.xiaohongshu.com/explore/note123"],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-comment-weekly"]
        self.assertTrue(Path(job_state["lastCommentEvidenceCapture"]).exists())
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        capture = run_report["records"][0]["commentEvidenceCapture"]
        self.assertEqual(capture["status"], "ready")
        self.assertEqual(capture["summary"]["commentCount"], 2)
        self.assertIn("comment_evidence_capture.py", " ".join(capture["command"]))

    def test_automation_scheduler_passes_competitor_informed_content_flags(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-enhancer-flags-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                }
            ),
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "enhancer-enabled",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["youtube"],
                            "skipCreatorLeaderboard": True,
                            "creatorFollowUp": {"enabled": True, "limit": 7, "topN": 3, "dryRun": True},
                            "followUpCapture": {"enabled": True, "dryRun": True, "sampleVideoFrames": True, "videoSampleCount": 3},
                            "competitorInformedContent": {"enabled": True},
                            "skipVideo": True,
                        },
                        {
                            "id": "enhancer-disabled",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["youtube"],
                            "competitorInformedContent": {"enabled": False},
                            "skipVideo": True,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
                "--dry-run",
            ],
            check=True,
            cwd=ROOT,
        )
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        commands = {record["jobId"]: record["command"] for record in run_report["records"]}
        self.assertIn("--skip-creator-leaderboard", commands["enhancer-enabled"])
        self.assertIn("--run-creator-follow-up", commands["enhancer-enabled"])
        self.assertIn("--creator-follow-up-limit", commands["enhancer-enabled"])
        self.assertIn("7", commands["enhancer-enabled"])
        self.assertIn("--creator-follow-up-top-n", commands["enhancer-enabled"])
        self.assertIn("3", commands["enhancer-enabled"])
        self.assertIn("--creator-follow-up-dry-run", commands["enhancer-enabled"])
        self.assertIn("--run-follow-up-captures", commands["enhancer-enabled"])
        self.assertIn("--follow-up-dry-run", commands["enhancer-enabled"])
        self.assertIn("--sample-video-frames", commands["enhancer-enabled"])
        self.assertIn("--video-sample-count", commands["enhancer-enabled"])
        self.assertIn("--use-competitor-informed-content", commands["enhancer-enabled"])
        self.assertIn("--skip-competitor-informed-content", commands["enhancer-disabled"])

    def test_automation_scheduler_runs_multi_query_viral_discovery_after_workflow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-multi-query-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                    "keywords": ["AI automation"],
                }
            ),
            encoding="utf-8",
        )
        config_path = out_dir / "automation.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "defaultOutputRoot": "./automation-output",
                    "jobs": [
                        {
                            "id": "ai-prompt-kit-multi-query-weekly",
                            "enabled": True,
                            "schedule": {"intervalDays": 7},
                            "input": {"structuredJson": "snapshot.json"},
                            "platforms": ["youtube", "github"],
                            "topN": 2,
                            "skipVideo": True,
                            "multiQueryViralDiscovery": {
                                "enabled": True,
                                "dryRun": True,
                                "queryCount": 4,
                                "topN": 3,
                                "queries": ["AI launch examples"],
                                "runFollowUpCaptures": True,
                                "sampleVideoFrames": True,
                                "videoSampleCount": 2,
                            },
                        }
                    ],
                    "guardrails": ["No automatic publishing without approval."],
                }
            ),
            encoding="utf-8",
        )
        state_path = out_dir / "state.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "run",
                "--config",
                str(config_path),
                "--state-file",
                str(state_path),
                "--now",
                "2026-07-07T00:00:00+00:00",
            ],
            check=True,
            cwd=ROOT,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        job_state = state["jobs"]["ai-prompt-kit-multi-query-weekly"]
        self.assertTrue(Path(job_state["lastMultiQueryViralDiscovery"]).exists())
        run_report = json.loads((out_dir / "automation-output/scheduler/automation-run.json").read_text(encoding="utf-8"))
        discovery = run_report["records"][0]["multiQueryViralDiscovery"]
        self.assertEqual(discovery["status"], "planned")
        self.assertIn("--workflow-manifest", discovery["command"])
        self.assertIn("--dry-run", discovery["command"])
        self.assertIn("--run-follow-up-captures", discovery["command"])
        self.assertIn("--sample-video-frames", discovery["command"])
        self.assertIn("--video-sample-count", discovery["command"])
        self.assertIn("2", discovery["command"])
        self.assertTrue(Path(discovery["report"]).exists())

    def test_automation_scheduler_init_can_enable_closed_loop_flags(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-automation-init-flags-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        config_path = out_dir / "automation.json"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "init",
                "--config",
                str(config_path),
                "--job-id",
                "product-weekly",
                "--browser-url",
                "https://example.com/product",
                "--platforms",
                "youtube,xiaohongshu",
                "--interval-days",
                "7",
                "--output-root",
                str(out_dir / "automation-output"),
                "--auto-search-competitors",
                "--enable-multi-query-viral-discovery",
                "--run-follow-up-captures",
                "--capture-browser-assisted-follow-ups",
                "--sample-video-frames",
                "--enable-publish-queue",
                "--enable-browser-publish-assistant",
                "--enable-browser-form-fill",
                "--enable-post-publish-metrics-capture",
                "--enable-comment-evidence-capture",
                "--enable-business-attribution",
                "--enable-metrics-recovery",
                "--enable-next-round-optimization",
            ],
            check=True,
            cwd=ROOT,
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        job = config["jobs"][0]
        self.assertEqual(job["id"], "product-weekly")
        self.assertEqual(job["platforms"], ["youtube", "xiaohongshu"])
        self.assertTrue(job["autoSearchCompetitors"])
        self.assertTrue(job["multiQueryViralDiscovery"]["enabled"])
        self.assertTrue(job["multiQueryViralDiscovery"]["sampleVideoFrames"])
        self.assertTrue(job["followUpCapture"]["enabled"])
        self.assertTrue(job["followUpCapture"]["captureBrowserAssisted"])
        self.assertTrue(job["publish"]["enabled"])
        self.assertTrue(job["browserPublishAssistant"]["enabled"])
        self.assertTrue(job["browserFormFill"]["enabled"])
        self.assertTrue(job["postPublishMetricsCapture"]["enabled"])
        self.assertTrue(job["commentEvidenceCapture"]["enabled"])
        self.assertTrue(job["businessAttribution"]["enabled"])
        self.assertTrue(job["metricsRecovery"]["enabled"])
        self.assertTrue(job["nextRoundOptimization"]["enabled"])

    def test_automation_scheduler_writes_windows_task_script(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-windows-task-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        config_path = out_dir / "automation.json"
        config_path.write_text(json.dumps({"version": 1, "jobs": []}), encoding="utf-8")
        script_path = out_dir / "register-task.ps1"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "windows-task",
                "--config",
                str(config_path),
                "--out-file",
                str(script_path),
                "--task-name",
                "ENHE Product Promo Maker Test",
                "--time",
                "09:30",
            ],
            check=True,
            cwd=ROOT,
        )
        script = script_path.read_text(encoding="utf-8")
        self.assertIn("Register-ScheduledTask", script)
        self.assertIn("automation_scheduler.py", script)
        self.assertIn("ENHE Product Promo Maker Test", script)

    def test_automation_scheduler_windows_task_uses_compatibility_default_name(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-windows-task-default-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        config_path = out_dir / "automation.json"
        config_path.write_text(json.dumps({"version": 1, "jobs": []}), encoding="utf-8")
        script_path = out_dir / "register-task.ps1"
        subprocess.run(
            [
                sys.executable,
                str(AUTOMATION_SCHEDULER),
                "windows-task",
                "--config",
                str(config_path),
                "--out-file",
                str(script_path),
                "--time",
                "09:30",
            ],
            check=True,
            cwd=ROOT,
        )

        registration = next(
            line
            for line in script_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("Register-ScheduledTask ")
        )
        self.assertEqual(
            re.findall(r"-TaskName ('[^']*')", registration),
            ["'ENHE Promotion Manager'"],
        )
        self.assertEqual(
            re.findall(r'-Description ("[^"]*")', registration),
            ['"Runs the ENHE Product Promo Maker scheduler."'],
        )
        self.assertNotIn("-TaskName 'ENHE Product Promo Maker'", registration)

    def test_competitor_intake_imports_html_evidence(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="competitor-intake-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "competitor.html"
        html_path.write_text(
            """<!doctype html>
<html>
<head>
  <title>One URL Into 30 Posts</title>
  <meta property="og:title" content="One URL Into 30 Posts">
  <meta property="og:description" content="A creator breaks down a product URL into platform-native posts.">
  <meta property="og:site_name" content="Growth Creator">
</head>
<body>
  <h1>One URL Into 30 Posts</h1>
  <p>Hook: Stop writing from a blank page. Turn one product URL into a week of content.</p>
  <p>12K views 1.2K likes 87 comments. Visit the template link to try it.</p>
</body>
</html>""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(COMPETITOR_INTAKE),
                "--html-file",
                str(html_path),
                "--platform",
                "youtube",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/competitors/imported-competitors.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["records"][0]["platform"], "youtube")
        self.assertEqual(report["records"][0]["title"], "One URL Into 30 Posts")
        self.assertEqual(report["records"][0]["creatorName"], "Growth Creator")
        self.assertEqual(report["records"][0]["visibleMetrics"]["views"]["normalized"], 12000.0)
        self.assertIn("contentDeconstruction", report["records"][0])
        self.assertIn("videoArchitecture", report["records"][0]["contentDeconstruction"])
        self.assertIn("visible_metric_proof", report["records"][0]["contentDeconstruction"]["copyMechanics"])
        self.assertEqual(report["aggregatePatterns"]["recordsWithObservedMetrics"], 1)
        self.assertTrue((out_dir / "reports/promotion-manager/competitors/imported-competitors.md").exists())

    def test_competitor_discovery_generates_platform_tasks(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="competitor-discovery-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(COMPETITOR_DISCOVERY),
                "--query",
                "AI product copy generator",
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/competitors/competitor-discovery.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        tasks = {item["platform"]: item for item in report["tasks"]}
        self.assertIn("youtube.com/results", tasks["youtube"]["searchUrl"])
        self.assertIn("github.com/search", tasks["github"]["searchUrl"])
        self.assertTrue(tasks["github"]["canRunFullyAutomatedNow"])
        self.assertFalse(tasks["xiaohongshu"]["canRunFullyAutomatedNow"])
        self.assertEqual(report["liveResults"], {})
        self.assertTrue((out_dir / "reports/promotion-manager/competitors/competitor-discovery.md").exists())

    def test_competitor_collector_imports_youtube_official_fixtures(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="competitor-collector-youtube-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        search_path = out_dir / "youtube-search.json"
        videos_path = out_dir / "youtube-videos.json"
        channels_path = out_dir / "youtube-channels.json"
        search_path.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "id": {"videoId": "vid123"},
                            "snippet": {
                                "title": "One URL Into 30 Posts",
                                "channelId": "chan123",
                                "channelTitle": "Growth Creator",
                                "description": "Turn one product URL into a week of content.",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        videos_path.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "id": "vid123",
                            "snippet": {
                                "title": "One URL Into 30 Posts",
                                "channelId": "chan123",
                                "channelTitle": "Growth Creator",
                                "description": "Turn one product URL into a week of content.",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            },
                            "statistics": {"viewCount": "12000", "likeCount": "1200", "commentCount": "87"},
                            "contentDetails": {"duration": "PT30S"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        channels_path.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "id": "chan123",
                            "snippet": {"title": "Growth Creator"},
                            "statistics": {"subscriberCount": "5000", "viewCount": "90000", "videoCount": "42"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(COMPETITOR_COLLECTOR),
                "--platform",
                "youtube",
                "--query",
                "product copy generator",
                "--youtube-search-json",
                str(search_path),
                "--youtube-videos-json",
                str(videos_path),
                "--youtube-channels-json",
                str(channels_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/competitors/auto-collected-competitors.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["platform"], "youtube")
        self.assertEqual(record["creatorName"], "Growth Creator")
        self.assertEqual(record["visibleMetrics"]["views"]["normalized"], 12000.0)
        self.assertEqual(record["visibleMetrics"]["channelSubscribers"]["normalized"], 5000.0)
        self.assertEqual(report["connectorStatus"][0]["status"], "ready")

    def test_competitor_collector_imports_github_public_fixtures(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="competitor-collector-github-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        search_path = out_dir / "github-search.json"
        search_path.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "full_name": "example/product-copy-generator",
                            "name": "product-copy-generator",
                            "html_url": "https://github.com/example/product-copy-generator",
                            "description": "Generate product copy from one URL.",
                            "owner": {"login": "example"},
                            "stargazers_count": 3400,
                            "forks_count": 210,
                            "watchers_count": 3400,
                            "open_issues_count": 12,
                            "language": "Python",
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2026-01-01T00:00:00Z",
                            "topics": ["ai", "copywriting"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(COMPETITOR_COLLECTOR),
                "--platform",
                "github",
                "--query",
                "product copy generator",
                "--github-search-json",
                str(search_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/competitors/auto-collected-competitors.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["platform"], "github")
        self.assertEqual(record["creatorName"], "example")
        self.assertEqual(record["visibleMetrics"]["stars"]["normalized"], 3400.0)
        self.assertEqual(record["language"], "Python")
        self.assertEqual(report["connectorStatus"][0]["source"], "GitHub Search REST API")

    def test_metrics_intake_imports_real_csv_metrics(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-intake-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        csv_path = out_dir / "metrics.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,views,likes,comments,shares,clicks,leads,orders,revenue,evidence",
                    "youtube,https://www.youtube.com/watch?v=abc123,Launch Video,12K,1.2K,87,33,240,28,6,$420.50,https://studio.youtube.com/export.csv",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--csv-file",
                str(csv_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/metrics/imported-metrics.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["metrics"]["views"]["normalized"], 12000.0)
        self.assertEqual(record["metrics"]["revenue"]["normalized"], 420.5)
        self.assertGreater(record["derived"]["engagementRate"], 0)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 6.0)
        self.assertEqual(report["retrospective"]["status"], "ready")
        self.assertTrue((out_dir / "reports/promotion-manager/metrics/imported-metrics.md").exists())

    def test_metrics_intake_imports_common_platform_export_aliases(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-alias-export-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        csv_path = out_dir / "metrics-export.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,view_count,like_count,comment_count,share_count,click_count,lead_count,order_count,paid_amount,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,4200,360,41,22,108,13,2,99.00,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--csv-file",
                str(csv_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics/imported-metrics.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["metrics"]["views"]["normalized"], 4200.0)
        self.assertEqual(record["metrics"]["likes"]["normalized"], 360.0)
        self.assertEqual(record["metrics"]["comments"]["normalized"], 41.0)
        self.assertEqual(record["metrics"]["shares"]["normalized"], 22.0)
        self.assertEqual(record["metrics"]["clicks"]["normalized"], 108.0)
        self.assertEqual(record["metrics"]["leads"]["normalized"], 13.0)
        self.assertEqual(record["metrics"]["orders"]["normalized"], 2.0)
        self.assertEqual(record["metrics"]["revenue"]["normalized"], 99.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 99.0)

    def test_metrics_intake_imports_structured_browser_snapshot_metrics(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-structured-intake-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "published-metrics-snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://www.xiaohongshu.com/explore/note123",
                    "title": "AI Prompt Kit launch note analytics",
                    "text": "浏览量: 3,000 点赞: 380 评论: 42 收藏: 55 订单: 2 收入: $88.00",
                    "screenshot": "xhs-analytics.png",
                    "capturedAt": "2026-07-08T09:00:00+08:00",
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--structured-json",
                str(snapshot_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/metrics/imported-metrics.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(report["inputMode"], "structured_json")
        self.assertEqual(record["platform"], "xiaohongshu")
        self.assertEqual(record["publishedUrl"], "https://www.xiaohongshu.com/explore/note123")
        self.assertEqual(record["metrics"]["views"]["normalized"], 3000.0)
        self.assertEqual(record["metrics"]["likes"]["normalized"], 380.0)
        self.assertEqual(record["metrics"]["comments"]["normalized"], 42.0)
        self.assertEqual(record["metrics"]["orders"]["normalized"], 2.0)
        self.assertEqual(record["metrics"]["revenue"]["normalized"], 88.0)
        self.assertIn("xhs-analytics.png", record["evidence"])

    def test_metrics_intake_imports_structured_nested_metric_aliases(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-structured-alias-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "published-metrics-snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Launch Video analytics",
                    "analytics": {
                        "viewCount": "12K",
                        "likeCount": "840",
                        "commentCount": "30",
                        "shareCount": "12",
                        "website_clicks": "144",
                        "paid_amount": "$420.50",
                    },
                    "screenshotPath": "youtube-analytics.png",
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--structured-json",
                str(snapshot_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics/imported-metrics.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["metrics"]["views"]["normalized"], 12000.0)
        self.assertEqual(record["metrics"]["likes"]["normalized"], 840.0)
        self.assertEqual(record["metrics"]["comments"]["normalized"], 30.0)
        self.assertEqual(record["metrics"]["shares"]["normalized"], 12.0)
        self.assertEqual(record["metrics"]["clicks"]["normalized"], 144.0)
        self.assertEqual(record["metrics"]["revenue"]["normalized"], 420.5)
        self.assertIn("youtube-analytics.png", record["evidence"])

    def test_metrics_recovery_merges_published_items_and_business_exports(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_items = out_dir / "published-items.json"
        published_items.write_text(
            json.dumps(
                [
                    {
                        "platform": "youtube",
                        "publishedUrl": "https://www.youtube.com/watch?v=abc123",
                        "title": "Launch Video",
                    },
                    {
                        "platform": "xiaohongshu",
                        "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        "title": "Launch Note",
                    },
                ]
            ),
            encoding="utf-8",
        )
        business_csv = out_dir / "business.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,views,likes,comments,clicks,orders,revenue,evidence",
                    "youtube,https://www.youtube.com/watch?v=abc123,Launch Video,12000,1200,87,240,6,$420.50,shop-export.csv",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,3000,380,44,90,2,$88.00,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--published-items-json",
                str(published_items),
                "--business-csv",
                str(business_csv),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "ready")
        self.assertEqual(report["aggregates"]["totals"]["orders"], 8.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 508.5)
        self.assertEqual(report["coverage"]["recordsWithMetrics"], 2)
        statuses = {(item["platform"], item["status"]) for item in report["connectorStatus"]}
        self.assertIn(("youtube", "requires_env_var"), statuses)
        self.assertIn(("xiaohongshu", "manual_export_required"), statuses)
        self.assertTrue((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.md").exists())
        serialized = json.dumps(report)
        self.assertNotIn("YOUTUBE_OAUTH_ACCESS_TOKEN", serialized)
        self.assertNotIn("GITHUB_TOKEN", serialized)

    def test_metrics_recovery_imports_platform_export_aliases(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-alias-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_items = out_dir / "published-items.json"
        published_items.write_text(
            json.dumps(
                [
                    {
                        "platform": "xiaohongshu",
                        "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        "title": "Launch Note",
                    }
                ]
            ),
            encoding="utf-8",
        )
        metrics_csv = out_dir / "metrics-export.csv"
        metrics_csv.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,view_count,like_count,comment_count,share_count,click_count,lead_count,order_count,paid_amount,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,4200,360,41,22,108,13,2,99.00,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--published-items-json",
                str(published_items),
                "--metrics-csv",
                str(metrics_csv),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "ready")
        self.assertEqual(report["coverage"]["publishedItemsDiscovered"], 1)
        self.assertEqual(report["coverage"]["recordsWithMetrics"], 1)
        self.assertEqual(report["coverage"]["manualOrPendingRequirements"], 0)
        self.assertEqual(report["aggregates"]["totals"]["views"], 4200.0)
        self.assertEqual(report["aggregates"]["totals"]["likes"], 360.0)
        self.assertEqual(report["aggregates"]["totals"]["comments"], 41.0)
        self.assertEqual(report["aggregates"]["totals"]["shares"], 22.0)
        self.assertEqual(report["aggregates"]["totals"]["clicks"], 108.0)
        self.assertEqual(report["aggregates"]["totals"]["leads"], 13.0)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 99.0)
        self.assertEqual(report["metricSources"][0]["type"], "metrics_csv")

    def test_metrics_recovery_imports_chinese_platform_export_headers(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-chinese-export-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_items = out_dir / "published-items.json"
        published_items.write_text(
            json.dumps(
                [
                    {
                        "platform": "xiaohongshu",
                        "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        "title": "Launch Note",
                    }
                ]
            ),
            encoding="utf-8",
        )
        metrics_csv = out_dir / "metrics-export.csv"
        header = ",".join(
            [
                "\u5e73\u53f0",
                "\u53d1\u5e03\u94fe\u63a5",
                "\u6807\u9898",
                "\u64ad\u653e\u91cf(\u6b21)",
                "\u70b9\u8d5e\u6570",
                "\u8bc4\u8bba\u6570",
                "\u5206\u4eab\u6570",
                "\u5b98\u7f51\u70b9\u51fb",
                "\u7ebf\u7d22\u6570",
                "\u8ba2\u5355\u6570",
                "\u6210\u4ea4\u91d1\u989d(\u5143)",
                "\u8bc1\u636e",
            ]
        )
        row = ",".join(
            [
                "\u5c0f\u7ea2\u4e66",
                "https://www.xiaohongshu.com/explore/note123",
                "Launch Note",
                "1.2\u4e07",
                "840",
                "66",
                "18",
                "144",
                "21",
                "3",
                "188.50",
                "xhs-export.csv",
            ]
        )
        metrics_csv.write_text("\n".join([header, row]), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--published-items-json",
                str(published_items),
                "--metrics-csv",
                str(metrics_csv),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "ready")
        self.assertEqual(report["coverage"]["manualOrPendingRequirements"], 0)
        self.assertEqual(report["aggregates"]["totals"]["views"], 12000.0)
        self.assertEqual(report["aggregates"]["totals"]["likes"], 840.0)
        self.assertEqual(report["aggregates"]["totals"]["comments"], 66.0)
        self.assertEqual(report["aggregates"]["totals"]["shares"], 18.0)
        self.assertEqual(report["aggregates"]["totals"]["clicks"], 144.0)
        self.assertEqual(report["aggregates"]["totals"]["leads"], 21.0)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 3.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 188.5)
        self.assertEqual(report["records"][0]["platform"], "xiaohongshu")
        self.assertIn("xhs-export.csv", report["records"][0]["evidence"])

    def test_metrics_intake_imports_xlsx_platform_export(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-intake-xlsx-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        metrics_xlsx = out_dir / "metrics-export.xlsx"
        write_minimal_xlsx(
            metrics_xlsx,
            [
                [
                    "\u5e73\u53f0",
                    "\u53d1\u5e03\u94fe\u63a5",
                    "\u6807\u9898",
                    "\u64ad\u653e\u91cf(\u6b21)",
                    "\u70b9\u8d5e\u6570",
                    "\u8bc4\u8bba\u6570",
                    "\u5206\u4eab\u6570",
                    "\u5b98\u7f51\u70b9\u51fb",
                    "\u7ebf\u7d22\u6570",
                    "\u8ba2\u5355\u6570",
                    "\u6210\u4ea4\u91d1\u989d(\u5143)",
                    "\u8bc1\u636e",
                ],
                [
                    "\u5c0f\u7ea2\u4e66",
                    "https://www.xiaohongshu.com/explore/note123",
                    "Launch Note",
                    "1.2\u4e07",
                    "840",
                    "66",
                    "18",
                    "144",
                    "21",
                    "3",
                    "188.50",
                    "xhs-export.xlsx",
                ],
            ],
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--xlsx-file",
                str(metrics_xlsx),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics/imported-metrics.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(report["inputMode"], "xlsx_file")
        self.assertEqual(record["platform"], "xiaohongshu")
        self.assertEqual(record["publishedUrl"], "https://www.xiaohongshu.com/explore/note123")
        self.assertEqual(record["metrics"]["views"]["normalized"], 12000.0)
        self.assertEqual(record["metrics"]["likes"]["normalized"], 840.0)
        self.assertEqual(record["metrics"]["comments"]["normalized"], 66.0)
        self.assertEqual(record["metrics"]["shares"]["normalized"], 18.0)
        self.assertEqual(record["metrics"]["clicks"]["normalized"], 144.0)
        self.assertEqual(record["metrics"]["leads"]["normalized"], 21.0)
        self.assertEqual(record["metrics"]["orders"]["normalized"], 3.0)
        self.assertEqual(record["metrics"]["revenue"]["normalized"], 188.5)
        self.assertIn("xhs-export.xlsx", record["evidence"])

    def test_metrics_recovery_imports_xlsx_platform_export(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-xlsx-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_items = out_dir / "published-items.json"
        published_items.write_text(
            json.dumps(
                [
                    {
                        "platform": "xiaohongshu",
                        "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        "title": "Launch Note",
                    }
                ]
            ),
            encoding="utf-8",
        )
        metrics_xlsx = out_dir / "metrics-export.xlsx"
        write_minimal_xlsx(
            metrics_xlsx,
            [
                ["platform", "publishedUrl", "title", "view_count", "like_count", "comment_count", "order_count", "paid_amount", "evidence"],
                ["xiaohongshu", "https://www.xiaohongshu.com/explore/note123", "Launch Note", "4200", "360", "41", "2", "99.00", "xhs-export.xlsx"],
            ],
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--published-items-json",
                str(published_items),
                "--metrics-xlsx",
                str(metrics_xlsx),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "ready")
        self.assertEqual(report["coverage"]["manualOrPendingRequirements"], 0)
        self.assertEqual(report["aggregates"]["totals"]["views"], 4200.0)
        self.assertEqual(report["aggregates"]["totals"]["likes"], 360.0)
        self.assertEqual(report["aggregates"]["totals"]["comments"], 41.0)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 99.0)
        self.assertEqual(report["metricSources"][0]["type"], "metrics_xlsx")

    def test_metrics_recovery_imports_business_xlsx_export(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-business-xlsx-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_items = out_dir / "published-items.json"
        published_items.write_text(
            json.dumps(
                [
                    {
                        "platform": "xiaohongshu",
                        "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        "title": "Launch Note",
                    }
                ]
            ),
            encoding="utf-8",
        )
        business_xlsx = out_dir / "business-export.xlsx"
        write_minimal_xlsx(
            business_xlsx,
            [
                ["platform", "publishedUrl", "title", "click_count", "lead_count", "order_count", "paid_amount", "evidence"],
                ["xiaohongshu", "https://www.xiaohongshu.com/explore/note123", "Launch Note", "108", "13", "2", "99.00", "shop-export.xlsx"],
            ],
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--published-items-json",
                str(published_items),
                "--business-xlsx",
                str(business_xlsx),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "ready")
        self.assertEqual(report["coverage"]["manualOrPendingRequirements"], 0)
        self.assertEqual(report["aggregates"]["totals"]["clicks"], 108.0)
        self.assertEqual(report["aggregates"]["totals"]["leads"], 13.0)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 99.0)
        self.assertEqual(report["businessSources"][0]["type"], "business_xlsx")

    def test_metrics_recovery_imports_structured_metrics_snapshot(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-structured-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "title": "AI Prompt Kit launch note analytics",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        snapshot_path = out_dir / "published-metrics-snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://www.xiaohongshu.com/explore/note123",
                    "title": "AI Prompt Kit launch note analytics",
                    "text": "views: 3,000 likes: 380 comments: 42 orders: 2 revenue: $88.00",
                    "screenshot": "xhs-analytics.png",
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--metrics-structured-json",
                str(snapshot_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "ready")
        self.assertEqual(report["coverage"]["publishedItemsDiscovered"], 1)
        self.assertEqual(report["coverage"]["recordsWithMetrics"], 1)
        self.assertEqual(report["coverage"]["manualOrPendingRequirements"], 0)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(report["aggregates"]["totals"]["revenue"], 88.0)

    def test_next_round_optimizer_builds_evidence_backed_plan(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="next-round-optimizer-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        workflow_dir = out_dir / "reports/promotion-manager/agent-run"
        workflow_dir.mkdir(parents=True)
        workflow_manifest = workflow_dir / "workflow-manifest.json"
        workflow_manifest.write_text(
            json.dumps(
                {
                    "product": {
                        "name": "AI Prompt Kit",
                        "url": "https://example.com/ai-prompt-kit",
                        "audience": "AI operators",
                        "valueProposition": "Prompt templates for launch copy and video scripts",
                    },
                    "platforms": ["youtube", "xiaohongshu"],
                }
            ),
            encoding="utf-8",
        )
        metrics_dir = out_dir / "reports/promotion-manager/metrics-recovery"
        metrics_dir.mkdir(parents=True)
        metrics_path = metrics_dir / "metrics-recovery.json"
        metrics_path.write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-08",
                    "recoveryStatus": "ready",
                    "records": [
                        {
                            "id": "metric-001",
                            "platform": "xiaohongshu",
                            "title": "AI Prompt Kit launch note",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "metrics": {
                                "views": {"raw": "4200", "normalized": 4200.0},
                                "likes": {"raw": "360", "normalized": 360.0},
                                "comments": {"raw": "41", "normalized": 41.0},
                                "orders": {"raw": "1", "normalized": 1.0},
                                "revenue": {"raw": "99.00", "normalized": 99.0},
                            },
                            "evidence": ["xhs-export.csv"],
                        },
                        {
                            "id": "metric-002",
                            "platform": "youtube",
                            "title": "AI Prompt Kit demo",
                            "publishedUrl": "https://www.youtube.com/watch?v=abc123",
                            "metrics": {
                                "views": {"raw": "12000", "normalized": 12000.0},
                                "likes": {"raw": "840", "normalized": 840.0},
                                "comments": {"raw": "30", "normalized": 30.0},
                            },
                            "evidence": ["youtube-api"],
                        },
                    ],
                    "aggregates": {
                        "recordsWithMetrics": 2,
                        "totals": {"views": 16200.0, "likes": 1200.0, "comments": 71.0, "orders": 1.0, "revenue": 99.0},
                    },
                    "manualExportRequired": [],
                    "retrospective": {"status": "ready", "nextRoundActions": ["Reuse the strongest observed hook in one new variant."]},
                }
            ),
            encoding="utf-8",
        )
        comment_dir = out_dir / "reports/promotion-manager/comment-evidence"
        comment_dir.mkdir(parents=True)
        comment_path = comment_dir / "comment-evidence-export.json"
        comment_path.write_text(
            json.dumps(
                {
                    "records": [],
                    "comments": [
                        {
                            "author": "Alice",
                            "text": "How does pricing work?",
                            "likes": 9,
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        },
                        {
                            "author": "Bob",
                            "text": "Need Zapier integration",
                            "replies": 2,
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                        },
                    ],
                    "demandSignals": [
                        {"type": "pricing", "excerpt": "How does pricing work?", "platform": "xiaohongshu"},
                        {"type": "integration", "excerpt": "Need Zapier integration", "platform": "xiaohongshu"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        business_dir = out_dir / "reports/promotion-manager/business-attribution"
        business_dir.mkdir(parents=True)
        business_path = business_dir / "business-attribution.json"
        business_path.write_text(
            json.dumps(
                {
                    "status": "ready",
                    "summary": {"matchedRows": 1, "attributedOrders": 1.0, "attributedRevenue": 99.0},
                    "attributions": [
                        {
                            "platform": "xiaohongshu",
                            "title": "AI Prompt Kit launch note",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "metrics": {
                                "orders": {"raw": "1", "normalized": 1.0},
                                "revenue": {"raw": "99", "normalized": 99.0},
                            },
                            "matchRules": ["referrer_url"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(NEXT_ROUND_OPTIMIZER),
                "--metrics-recovery-json",
                str(metrics_path),
                "--comment-evidence-json",
                str(comment_path),
                "--business-attribution-json",
                str(business_path),
                "--workflow-manifest",
                str(workflow_manifest),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/optimization/next-round-optimization.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["evidenceCoverage"]["metricRecords"], 2)
        self.assertEqual(report["evidenceCoverage"]["commentCount"], 2)
        self.assertEqual(report["evidenceCoverage"]["businessAttributions"], 1)
        self.assertEqual(report["winners"]["byRevenue"]["platform"], "xiaohongshu")
        self.assertEqual(report["winners"]["byViews"]["platform"], "youtube")
        self.assertTrue(any(item["type"] == "pricing" for item in report["commentDemand"]["topSignals"]))
        self.assertTrue(any("pricing" in item["angle"].lower() for item in report["nextRoundContent"]))
        self.assertTrue(any(item["purpose"] == "run_next_cycle" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "refresh_viral_discovery" for item in report["recommendedCommands"]))
        self.assertTrue((out_dir / "reports/promotion-manager/optimization/next-round-optimization.md").exists())

    def test_next_round_optimizer_waits_for_real_data(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="next-round-waiting-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(NEXT_ROUND_OPTIMIZER),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/optimization/next-round-optimization.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "waiting_real_data")
        self.assertFalse(report["nextRoundContent"])
        self.assertTrue(any("Import real" in item for item in report["nextActions"]))

    def test_post_publish_metrics_capture_extracts_public_page_metrics(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="post-publish-metrics-capture-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <p>views: 12,000 likes: 850 comments: 64 favorites: 120 shares: 18</p>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": url,
                            "title": "AI Prompt Kit launch note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(POST_PUBLISH_METRICS_CAPTURE),
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        capture_path = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json"
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        self.assertEqual(capture["status"], "ready")
        self.assertEqual(capture["summary"]["capturedMetricRecords"], 1)
        self.assertEqual(capture["results"][0]["status"], "ready")
        self.assertEqual(capture["structuredRecords"][0]["metrics"]["views"]["normalized"], 12000.0)
        self.assertEqual(capture["structuredRecords"][0]["metrics"]["likes"]["normalized"], 850.0)
        metric_export = out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json"
        self.assertTrue(metric_export.exists())
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--metrics-json",
                str(metric_export),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        recovery = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(recovery["coverage"]["recordsWithMetrics"], 1)
        self.assertEqual(recovery["aggregates"]["totals"]["views"], 12000.0)

    def test_performance_monitor_runs_post_publish_closed_loop(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="performance-monitor-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <p>views: 4,200 likes: 360 comments: 41 favorites: 80 shares: 12</p>
    <section class="comments">
      <p>Comment by Alice: How does pricing work? likes: 9</p>
      <p>Bob: Need Zapier integration replies: 2</p>
      <p>Carol: This solved our content workflow</p>
    </section>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        published_url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        business_csv = out_dir / "orders.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,referrer,revenue,status",
                    f"order-1,xiaohongshu,{published_url},99.00,paid",
                ]
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PERFORMANCE_MONITOR),
                "--published-url",
                f"xiaohongshu={published_url}",
                "--business-csv",
                str(business_csv),
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads((out_dir / "reports/promotion-manager/performance-monitor/performance-monitor.json").read_text(encoding="utf-8"))
        self.assertIn(report["status"], {"ready", "partial_ready"})
        self.assertEqual(report["summary"]["capturedMetricRecords"], 1)
        self.assertEqual(report["summary"]["commentCount"], 3)
        self.assertEqual(report["summary"]["matchedBusinessRows"], 1)
        self.assertIn(report["summary"]["nextRoundStatus"], {"ready", "partial_ready"})
        self.assertEqual(
            [step["id"] for step in report["steps"]],
            [
                "post_publish_metrics_capture",
                "comment_evidence_capture",
                "business_attribution",
                "metrics_recovery",
                "next_round_optimizer",
            ],
        )
        history_path = out_dir / "reports/promotion-manager/performance-monitor/performance-monitor-history.jsonl"
        self.assertTrue(history_path.exists())
        self.assertEqual(len(history_path.read_text(encoding="utf-8").strip().splitlines()), 1)
        self.assertTrue((out_dir / "reports/promotion-manager/optimization/next-round-optimization.json").exists())

    def test_metrics_intake_parses_chinese_units_and_currency(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-chinese-units-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        metrics_text = out_dir / "visible-metrics.txt"
        metrics_text.write_text(
            "\n".join(
                [
                    "Title: AI Prompt Kit launch note",
                    "URL: https://www.xiaohongshu.com/explore/note123",
                    "播放量 1.2万",
                    "点赞 3.4k",
                    "评论 256",
                    "收藏 5,600",
                    "订单 12",
                    "收入 ￥88.50",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--text-file",
                str(metrics_text),
                "--platform",
                "xiaohongshu",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics/imported-metrics.json").read_text(encoding="utf-8"))
        metrics = report["records"][0]["metrics"]
        self.assertEqual(metrics["views"]["normalized"], 12000.0)
        self.assertEqual(metrics["likes"]["normalized"], 3400.0)
        self.assertEqual(metrics["favorites"]["normalized"], 5600.0)
        self.assertEqual(metrics["orders"]["normalized"], 12.0)
        self.assertEqual(metrics["revenue"]["normalized"], 88.5)

    def test_metrics_intake_pairs_numbers_before_labels_without_cross_field_bleed(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-number-before-label-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        metrics_text = out_dir / "visible-metrics.txt"
        metrics_text.write_text(
            "\n".join(
                [
                    "Title: AI Prompt Kit launch note",
                    "1.2万 播放",
                    "2.4k likes",
                    "320 comments",
                    "$88.50 revenue",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_INTAKE),
                "--text-file",
                str(metrics_text),
                "--platform",
                "youtube",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics/imported-metrics.json").read_text(encoding="utf-8"))
        metrics = report["records"][0]["metrics"]
        self.assertEqual(metrics["views"]["normalized"], 12000.0)
        self.assertEqual(metrics["likes"]["normalized"], 2400.0)
        self.assertEqual(metrics["comments"]["normalized"], 320.0)
        self.assertEqual(metrics["revenue"]["normalized"], 88.5)

    def test_post_publish_metrics_capture_extracts_chinese_units_from_public_page(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="post-publish-chinese-metrics-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <p>播放量 2.5万 点赞 1.1万 评论 320 收藏 4,800 分享 900</p>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "douyin",
                            "publishedUrl": url,
                            "title": "AI Prompt Kit launch note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(POST_PUBLISH_METRICS_CAPTURE),
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        capture = json.loads((out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json").read_text(encoding="utf-8"))
        metrics = capture["structuredRecords"][0]["metrics"]
        self.assertEqual(metrics["views"]["normalized"], 25000.0)
        self.assertEqual(metrics["likes"]["normalized"], 11000.0)
        self.assertEqual(metrics["favorites"]["normalized"], 4800.0)
        self.assertEqual(metrics["shares"]["normalized"], 900.0)

    def test_post_publish_metrics_capture_queues_unsafe_pages_for_manual_evidence(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="post-publish-metrics-capture-unsafe-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "douyin",
                            "publishedUrl": "http://127.0.0.1/login/video123",
                            "title": "Draft page",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(POST_PUBLISH_METRICS_CAPTURE),
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        capture = json.loads((out_dir / "reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.json").read_text(encoding="utf-8"))
        self.assertEqual(capture["status"], "waiting_real_data")
        self.assertEqual(capture["summary"]["capturedMetricRecords"], 0)
        self.assertEqual(capture["results"][0]["status"], "queued_manual_evidence")
        self.assertEqual(capture["results"][0]["reason"], "url_looks_like_login_captcha_editor_draft_or_preview")
        self.assertTrue(Path(capture["results"][0]["evidenceRequest"]).exists())

    def test_comment_evidence_capture_extracts_public_comments_and_demand_signals(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="comment-evidence-capture-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <section class="comments">
      <p>Comment by Alice: How does pricing work? likes: 12</p>
      <p>Bob: Need Zapier integration replies: 2</p>
      <p>Carol: This solved our content workflow</p>
    </section>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        published_items_path = out_dir / "published-items.json"
        published_items_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": url,
                            "title": "AI Prompt Kit launch note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(COMMENT_EVIDENCE_CAPTURE),
                "--published-items-json",
                str(published_items_path),
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["commentCount"], 3)
        self.assertEqual(report["items"][0]["comments"][0]["author"], "Alice")
        self.assertEqual(report["items"][0]["comments"][0]["likes"], 12)
        self.assertEqual(report["items"][0]["comments"][1]["replies"], 2)
        signal_types = {item["type"] for item in report["demandSignals"]}
        self.assertIn("pricing", signal_types)
        self.assertIn("integration", signal_types)
        self.assertIn("question", signal_types)
        self.assertTrue((out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json").exists())
        self.assertFalse((out_dir / "reports/promotion-manager/comment-evidence/manual-evidence").exists())

    def test_comment_evidence_capture_queues_unsafe_pages_for_manual_evidence(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="comment-evidence-capture-unsafe-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "unsafe.html"
        html_path.write_text(
            """<!doctype html>
<html><body>Please sign in to continue. Captcha challenge required.</body></html>""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(COMMENT_EVIDENCE_CAPTURE),
                "--html-file",
                str(html_path),
                "--platform",
                "douyin",
                "--published-url",
                "https://www.douyin.com/video/123",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-capture.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "queued_manual_evidence")
        self.assertEqual(report["summary"]["commentCount"], 0)
        self.assertEqual(report["items"][0]["status"], "queued_manual_evidence")
        self.assertEqual(report["items"][0]["reason"], "capture_looks_like_login_captcha_verification_or_access_denied")
        self.assertTrue(Path(report["items"][0]["evidenceRequest"]).exists())

    def test_metrics_recovery_marks_publish_queue_items_pending(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-pending-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        queue_dir = out_dir / "reports/promotion-manager/publish-queue"
        queue_dir.mkdir(parents=True)
        queue_path = queue_dir / "publish-queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "records": [
                        {"platform": "github", "status": "dry_run", "publishMode": "official_api_publish", "contentDraft": ""},
                        {"platform": "xiaohongshu", "status": "queued_manual", "publishMode": "manual_publish_required", "contentDraft": ""},
                        {"platform": "douyin", "status": "queued_browser_assisted", "publishMode": "browser_assisted_publish", "contentDraft": ""},
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--publish-queue",
                str(queue_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recoveryStatus"], "waiting_real_data")
        self.assertEqual(report["coverage"]["plannedOrQueuedItems"], 3)
        self.assertEqual(report["coverage"]["recordsWithMetrics"], 0)
        pending = {(item["platform"], item["status"]) for item in report["manualExportRequired"]}
        self.assertIn(("github", "publish_pending"), pending)
        self.assertIn(("xiaohongshu", "publish_pending"), pending)
        self.assertIn(("douyin", "publish_pending"), pending)

    def test_published_items_registers_queue_and_manual_urls(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="published-items-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        queue_dir = out_dir / "reports/promotion-manager/publish-queue"
        queue_dir.mkdir(parents=True)
        draft_path = queue_dir / "drafts/github-draft.md"
        draft_path.parent.mkdir(parents=True)
        draft_path.write_text("# github Publish Draft\n\n- Title: GitHub Launch Draft\n", encoding="utf-8")
        execution_path = queue_dir / "official-executions/github/reports/promotion-manager/publish-results/publish-execution.json"
        execution_path.parent.mkdir(parents=True)
        execution_path.write_text(
            json.dumps(
                {
                    "platform": "github",
                    "status": "published",
                    "publishedUrl": "https://github.com/example/repo/blob/main/PROMOTION.md",
                    "commitSha": "abc123",
                    "request": {"title": "GitHub Launch Draft"},
                }
            ),
            encoding="utf-8",
        )
        queue_path = queue_dir / "publish-queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "github",
                            "status": "published",
                            "publishMode": "official_api_publish",
                            "contentDraft": str(draft_path),
                            "officialExecution": {
                                "publishedUrl": "https://github.com/example/repo/blob/main/PROMOTION.md",
                                "report": str(execution_path),
                            },
                        },
                        {"platform": "douyin", "status": "queued_browser_assisted", "publishMode": "browser_assisted_publish"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISHED_ITEMS),
                "--publish-queue",
                str(queue_path),
                "--platform",
                "xiaohongshu",
                "--published-url",
                "https://www.xiaohongshu.com/explore/note123",
                "--title",
                "Manual Launch Note",
                "--evidence",
                "xhs-screenshot.png",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/published-items/published-items.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        by_platform = {item["platform"]: item for item in report["records"]}
        self.assertEqual(report["summary"]["published"], 2)
        self.assertEqual(report["summary"]["pending"], 1)
        self.assertEqual(by_platform["github"]["title"], "GitHub Launch Draft")
        self.assertEqual(by_platform["xiaohongshu"]["contentId"], "note123")
        self.assertIn("xhs-screenshot.png", by_platform["xiaohongshu"]["evidence"])
        self.assertEqual(report["pendingQueueItems"][0]["platform"], "douyin")
        self.assertTrue((out_dir / "reports/promotion-manager/published-items/published-items.md").exists())

    def test_promotion_cycle_runner_connects_publish_queue_and_metrics_recovery(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-cycle-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        business_csv = out_dir / "business.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,views,likes,orders,revenue,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,3000,380,2,$88.00,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PROMOTION_CYCLE_RUNNER),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "github,xiaohongshu",
                "--skip-video",
                "--github-repo",
                "hqwzhu/Viral-Product-Copy-Video-Generator",
                "--github-path",
                "PROMOTION.md",
                "--published-url",
                "xiaohongshu=https://www.xiaohongshu.com/explore/note123",
                "--business-csv",
                str(business_csv),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        cycle_path = out_dir / "output/reports/promotion-manager/cycle/promotion-cycle.json"
        cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
        self.assertEqual(cycle["workflow"]["status"], "ready")
        self.assertEqual(cycle["publishQueue"]["status"], "ready")
        self.assertEqual(cycle["publishedItems"]["status"], "ready")
        self.assertEqual(cycle["metricsRecovery"]["status"], "ready")
        self.assertEqual(cycle["automationStatus"], "partial_ready_with_real_metrics")
        self.assertTrue(Path(cycle["publishQueue"]["queue"]).exists())
        self.assertTrue(Path(cycle["publishedItems"]["publishedItems"]).exists())
        recovery = json.loads(Path(cycle["metricsRecovery"]["metricsRecovery"]).read_text(encoding="utf-8"))
        self.assertEqual(recovery["coverage"]["recordsWithMetrics"], 1)
        self.assertEqual(recovery["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(recovery["aggregates"]["totals"]["revenue"], 88.0)
        self.assertTrue((out_dir / "output/reports/promotion-manager/cycle/promotion-cycle.md").exists())

    def test_promotion_cycle_runner_captures_public_metrics_comments_and_business_attribution(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="promotion-cycle-evidence-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "note.html").write_text(
            """<!doctype html>
<html>
<head><title>AI Prompt Kit launch note</title></head>
<body>
  <article>
    <h1>AI Prompt Kit launch note</h1>
    <p>views: 4,200 likes: 360 comments: 41</p>
    <section class="comments">
      <p>Comment by Alice: How does pricing work? likes: 9</p>
      <p>Bob: Need Zapier integration replies: 2</p>
      <p>Carol: This solved our content workflow</p>
    </section>
  </article>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        published_url = f"http://127.0.0.1:{server.server_address[1]}/note.html"
        business_csv = out_dir / "orders.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,referrer,revenue,status",
                    f"order-1,xiaohongshu,{published_url},99.00,paid",
                ]
            ),
            encoding="utf-8",
        )
        output_dir = out_dir / "output"
        subprocess.run(
            [
                sys.executable,
                str(PROMOTION_CYCLE_RUNNER),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "xiaohongshu",
                "--skip-video",
                "--skip-publish-queue",
                "--published-url",
                f"xiaohongshu={published_url}",
                "--run-post-publish-metrics-capture",
                "--post-publish-metrics-allow-localhost",
                "--run-comment-evidence-capture",
                "--comment-evidence-allow-localhost",
                "--run-business-attribution",
                "--business-csv",
                str(business_csv),
                "--run-next-round-optimization",
                "--out-dir",
                str(output_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        cycle = json.loads((output_dir / "reports/promotion-manager/cycle/promotion-cycle.json").read_text(encoding="utf-8"))
        self.assertEqual(cycle["automationStatus"], "partial_ready_with_real_metrics")
        self.assertEqual(cycle["postPublishMetricsCapture"]["status"], "ready")
        self.assertEqual(cycle["postPublishMetricsCapture"]["summary"]["capturedMetricRecords"], 1)
        self.assertEqual(cycle["commentEvidenceCapture"]["status"], "ready")
        self.assertEqual(cycle["commentEvidenceCapture"]["summary"]["commentCount"], 3)
        self.assertEqual(cycle["businessAttribution"]["status"], "ready")
        self.assertEqual(cycle["businessAttribution"]["summary"]["matchedRows"], 1)
        self.assertEqual(cycle["nextRoundOptimization"]["status"], "partial_ready")
        self.assertTrue(Path(cycle["nextRoundOptimization"]["report"]).exists())
        recovery = json.loads(Path(cycle["metricsRecovery"]["metricsRecovery"]).read_text(encoding="utf-8"))
        self.assertEqual(recovery["aggregates"]["totals"]["views"], 4200.0)
        self.assertEqual(recovery["aggregates"]["totals"]["orders"], 1.0)
        self.assertEqual(recovery["aggregates"]["totals"]["revenue"], 99.0)
        optimization = json.loads(Path(cycle["nextRoundOptimization"]["report"]).read_text(encoding="utf-8"))
        self.assertEqual(optimization["evidenceCoverage"]["commentCount"], 3)
        self.assertEqual(optimization["evidenceCoverage"]["businessAttributions"], 1)
        self.assertTrue(optimization["recommendedCommands"])
        self.assertTrue(Path(cycle["postPublishMetricsCapture"]["metricExport"]).exists())
        self.assertTrue(Path(cycle["commentEvidenceCapture"]["commentEvidenceExport"]).exists())
        self.assertTrue(Path(cycle["businessAttribution"]["businessAttributionExport"]).exists())

    def test_current_user_facing_files_do_not_use_retired_product_name(self) -> None:
        approved_legal_aliases = [
            "ENHE Product Promo Maker (formerly ENHE Promotion Manager)",
            "ENHE 产品推广素材生成器（原 ENHE Promotion Manager）",
        ]
        approved_compatibility_tokens = {
            "browser-extension/popup.js": [
                '"--task-name \\"ENHE Promotion Manager\\""',
            ],
            "scripts/automation_scheduler.py": [
                'task.add_argument("--task-name", default="ENHE Promotion Manager")',
            ],
        }
        retired_names = [
            "ENHE Promotion Manager",
            "ENHE 推广管理器",
            "Promotion Manager",
            "推广管理器",
        ]
        current_files = [
            "README.md",
            "README.en.md",
            "README.zh-CN.md",
            "browser-extension/popup.js",
            "backend/license-service/README.md",
            "backend/license-service/package.json",
            "backend/license-service/src/migrate.js",
            "backend/license-service/src/server.js",
            "backend/license-service/src/worker.js",
            "deploy/promotion-manager/README.md",
            "deploy/promotion-manager/enhe-promotion-manager-api.service",
            "deploy/promotion-manager/enhe-promotion-manager-worker.service",
            "docs/100-percent-completion-roadmap.md",
            "docs/browser-extension.md",
            "docs/mediacrawler-sidecar.md",
            "docs/open-source-integration.md",
            "docs/zh-CN/browser-extension.md",
            "references/workflow.md",
            "scripts/automation_scheduler.py",
            "scripts/billing_contract_simulator.py",
            "scripts/completion_roadmap.py",
            "scripts/final_capability_audit.py",
            "scripts/mediacrawler_contract.py",
            "scripts/mediacrawler_downstream.py",
            "scripts/package_browser_extension.py",
            "scripts/platform_capabilities.py",
            "scripts/platform_data_manager.py",
            "scripts/publish_executor.py",
        ]

        for relative_path in current_files:
            path = ROOT / relative_path
            text = path.read_text(encoding="utf-8")
            for approved_alias in approved_legal_aliases:
                text = text.replace(approved_alias, "")
            for approved_token in approved_compatibility_tokens.get(relative_path, []):
                self.assertEqual(text.count(approved_token), 1, str(path))
                text = text.replace(approved_token, "", 1)
            for retired_name in retired_names:
                self.assertNotIn(retired_name, text, str(path))

    def test_rebrand_preserves_internal_compatibility_identifiers(self) -> None:
        popup = (BROWSER_EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("/api/promotion-manager/license", popup)
        self.assertIn("/promotion-manager/checkout", popup)
        self.assertIn('"--task-name \\"ENHE Promotion Manager\\""', popup)

        scheduler = AUTOMATION_SCHEDULER.read_text(encoding="utf-8")
        self.assertIn('task.add_argument("--task-name", default="ENHE Promotion Manager")', scheduler)
        self.assertIn(
            '-Description "Runs the ENHE Product Promo Maker scheduler."',
            scheduler,
        )

        package_json = json.loads((LICENSE_SERVICE / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package_json["name"], "enhe-promotion-manager-license-service")

        package_script = PACKAGE_BROWSER_EXTENSION.read_text(encoding="utf-8")
        self.assertIn('return f"enhe-promotion-manager-{version}.zip"', package_script)

        state_store = (LICENSE_SERVICE / "src" / "state-store.js").read_text(encoding="utf-8")
        self.assertIn("promotion_manager_state", state_store)

        deploy_readme = (ROOT / "deploy" / "promotion-manager" / "README.md").read_text(encoding="utf-8")
        self.assertIn("/opt/enhe/promotion-manager/current", deploy_readme)
        self.assertIn("/var/lib/enhe-promotion-manager", deploy_readme)

        self.assertTrue((ROOT / "deploy/promotion-manager/enhe-promotion-manager-api.service").exists())
        self.assertTrue((ROOT / "deploy/promotion-manager/enhe-promotion-manager-worker.service").exists())

    def test_github_docs_include_intro_usage_install_extension_and_pricing(self) -> None:
        self.assertTrue(README.exists())
        readme = README.read_text(encoding="utf-8")
        for marker in [
            "ENHE Product Promo Maker",
            "README.zh-CN.md",
            "Quick Start",
            "Install",
            "Browser Extension",
            "Subscription Model",
            "Safety Gates",
            "I_APPROVE_SKILL_SYNC",
        ]:
            self.assertIn(marker, readme)
        required_docs = [
            "installation.md",
            "usage.md",
            "zh-CN/installation.md",
            "zh-CN/usage.md",
            "browser-extension.md",
            "extension-store-submission.md",
            "subscription-pricing.md",
            "billing-backend-contract.md",
            "final-capability-map.md",
            "legal/privacy-policy.md",
            "legal/terms-of-service.md",
            "legal/refund-policy.md",
            "legal/support.md",
            "store/chrome-listing.md",
            "store/edge-listing.md",
            "store/reviewer-notes.md",
            "store/screenshot-plan.md",
        ]
        for filename in required_docs:
            self.assertTrue((DOCS / filename).exists(), filename)
        for path in [
            ROOT / "deploy/promotion-manager/README.md",
            ROOT / "deploy/promotion-manager/.env.production.example",
            ROOT / "deploy/promotion-manager/nginx-promotion-manager.conf",
            ROOT / "deploy/promotion-manager/enhe-promotion-manager-api.service",
            ROOT / "deploy/promotion-manager/enhe-promotion-manager-worker.service",
        ]:
            self.assertTrue(path.exists(), path)
        chinese_readme = ROOT / "README.zh-CN.md"
        self.assertTrue(chinese_readme.exists())
        chinese_readme_text = chinese_readme.read_text(encoding="utf-8")
        self.assertIn("中文安装教程", chinese_readme_text)
        self.assertIn("中文使用说明", chinese_readme_text)
        self.assertIn("浏览器插件", chinese_readme_text)
        self.assertIn("I_APPROVE_SKILL_SYNC", chinese_readme_text)
        chinese_install = (DOCS / "zh-CN/installation.md").read_text(encoding="utf-8")
        self.assertIn("安装为 Codex Skill", chinese_install)
        chinese_usage = (DOCS / "zh-CN/usage.md").read_text(encoding="utf-8")
        self.assertIn("单个产品 URL", chinese_usage)
        self.assertIn("发布后性能监控", chinese_usage)
        pricing = (DOCS / "subscription-pricing.md").read_text(encoding="utf-8")
        self.assertIn("Credit Model", pricing)
        self.assertIn("Starter", pricing)
        self.assertIn("Growth", pricing)
        self.assertIn("Scale", pricing)
        self.assertIn("safety_multiplier", pricing)
        billing = (DOCS / "billing-backend-contract.md").read_text(encoding="utf-8")
        self.assertIn("Usage Authorization", billing)
        self.assertIn("checkout.session.completed", billing)
        self.assertIn("customer.subscription.updated", billing)
        self.assertIn("invoice.payment_failed", billing)
        self.assertIn("Loss-Control Rules", billing)
        self.assertIn("Reference Simulator", billing)
        self.assertIn("billing_contract_simulator.py", billing)

    def test_browser_extension_manifest_popup_and_subscription_ui_are_static_mv3(self) -> None:
        manifest = json.loads((BROWSER_EXTENSION / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertLessEqual(len(manifest["description"]), 132)
        self.assertEqual(manifest["action"]["default_popup"], "popup.html")
        self.assertEqual(manifest["icons"]["128"], "icons/icon128.png")
        self.assertEqual(manifest["action"]["default_icon"]["48"], "icons/icon48.png")
        csp = manifest["content_security_policy"]["extension_pages"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-eval", csp)
        popup = (BROWSER_EXTENSION / "popup.html").read_text(encoding="utf-8")
        self.assertIn("ENHE AI", popup)
        self.assertIn("Subscription estimate", popup)
        self.assertIn("Command type", popup)
        self.assertIn("Browser publish session", popup)
        self.assertIn("Launch unlock pack", popup)
        self.assertIn("Evidence inbox setup", popup)
        self.assertIn("Real evidence inbox", popup)
        self.assertIn("Performance monitor", popup)
        self.assertIn("Final readiness audit", popup)
        self.assertIn("Schedule init", popup)
        self.assertIn("Run scheduled jobs", popup)
        self.assertIn("Windows task script", popup)
        self.assertIn("Publish queue JSON", popup)
        self.assertIn("Automation config", popup)
        self.assertIn("Enable metrics recovery", popup)
        self.assertIn("License key", popup)
        self.assertIn("Usage authorization endpoint", popup)
        self.assertIn("Hosted run endpoint", popup)
        self.assertIn("Reserve credits", popup)
        self.assertIn("Copy hosted payload", popup)
        self.assertIn("Hosted Worker off", popup)
        self.assertRegex(
            popup,
            r'<button(?=[^>]*\bid="startHostedRun")(?=[^>]*\bdisabled\b)(?=[^>]*\baria-disabled="true")[^>]*>',
        )
        self.assertIn("Open checkout", popup)
        self.assertIn("Billing portal", popup)
        self.assertIn("www.enhe-tech.com.cn", popup)
        self.assertIn("popup.js", popup)
        self.assertNotIn('src="https://', popup)
        script = (BROWSER_EXTENSION / "popup.js").read_text(encoding="utf-8")
        self.assertIn("chrome.storage.local", script)
        self.assertIn("validateLicense", script)
        self.assertIn("openCheckout", script)
        self.assertIn("openPortal", script)
        self.assertIn("authorizeUsage", script)
        self.assertIn("buildHostedRunPayload", script)
        self.assertIn("startHostedRun", script)
        self.assertIn("usageAuthorizeEndpoint", script)
        self.assertIn("hostedRunEndpoint", script)
        self.assertIn("const HOSTED_WORKER_ENABLED = false;", script)
        self.assertIn("applyHostedWorkerState", script)
        self.assertIn("idempotencyKey", script)
        self.assertIn("estimatedMonthlyCredits", script)
        self.assertIn("COST_PER_CREDIT", script)
        self.assertIn('starter: { label: "Starter", credits: 60, priceCny: 19 }', script)
        self.assertIn('growth: { label: "Growth", credits: 220, priceCny: 59 }', script)
        self.assertIn('scale: { label: "Scale", credits: 800, priceCny: 199 }', script)
        self.assertIn('at CNY ${plan.priceCny}/30 days', script)
        self.assertNotIn('at USD ${plan.price}/month', script)
        self.assertIn("skill_entry.py", script)
        self.assertIn("browser_publish_session.py", script)
        self.assertIn("launch_unlock_pack.py", script)
        self.assertIn("viral_evidence_inbox_setup.py", script)
        self.assertIn("viral_evidence_inbox.py", script)
        self.assertIn("real_evidence_inbox_setup.py", script)
        self.assertIn("real_evidence_inbox.py", script)
        self.assertIn("performance_monitor.py", script)
        self.assertIn("final_capability_readiness.py", script)
        self.assertIn("automation_scheduler.py", script)
        self.assertIn("browser_publish_session", script)
        self.assertIn("launch_unlock_pack", script)
        self.assertIn("viral_evidence_inbox_setup", script)
        self.assertIn("viral_evidence_inbox", script)
        self.assertIn("real_evidence_inbox_setup", script)
        self.assertIn("real_evidence_inbox", script)
        self.assertIn("performance_monitor", script)
        self.assertIn("automation_config_init", script)
        self.assertIn("automation_due_run", script)
        self.assertIn("automation_windows_task", script)
        css = (BROWSER_EXTENSION / "popup.css").read_text(encoding="utf-8")
        self.assertIn("--accent", css)
        self.assertIn("grid-template-columns", css)
        contract = json.loads((BROWSER_EXTENSION / "billing-contract.json").read_text(encoding="utf-8"))
        self.assertIn("checkoutUrl", contract)
        self.assertIn("customerPortalUrl", contract)
        self.assertIn("usageAuthorizeEndpoint", contract)
        self.assertIn("usageCommitEndpoint", contract)
        self.assertIn("hostedRunEndpoint", contract)
        self.assertIn("hostedRunStatusEndpointTemplate", contract)
        self.assertIn("legalUrls", contract)
        self.assertIn("privacyPolicy", contract["legalUrls"])
        self.assertIn("termsOfService", contract["legalUrls"])
        self.assertIn("refundPolicy", contract["legalUrls"])
        self.assertIn("support", contract["legalUrls"])
        self.assertEqual(contract["creditCosts"]["standard_run"], 4)
        self.assertIn("browser_publish_session", contract["creditCosts"])
        self.assertIn("launch_unlock_pack", contract["creditCosts"])
        self.assertEqual(contract["creditCosts"]["viral_evidence_inbox_setup"], 1)
        self.assertIn("viral_evidence_inbox", contract["creditCosts"])
        self.assertEqual(contract["creditCosts"]["real_evidence_inbox_setup"], 1)
        self.assertIn("real_evidence_inbox", contract["creditCosts"])
        self.assertIn("performance_monitor", contract["creditCosts"])
        self.assertIn("final_readiness_audit", contract["creditCosts"])
        self.assertIn("automation_config_init", contract["creditCosts"])
        self.assertIn("automation_due_run", contract["creditCosts"])
        self.assertIn("automation_windows_task", contract["creditCosts"])
        self.assertIn("commandType", contract["licenseRequest"]["body"])
        self.assertIn("usageAuthorizeRequest", contract)
        self.assertIn("workflowType", contract["usageAuthorizeRequest"]["body"])
        self.assertIn("idempotencyKey", contract["usageAuthorizeRequest"]["body"])
        self.assertIn("hostedRunRequest", contract)
        self.assertIn("usageId", contract["hostedRunRequest"]["body"])
        self.assertIn("localCommand", contract["hostedRunRequest"]["body"])
        self.assertIn("hostedRunResponse", contract)
        self.assertIn("statusUrl", contract["hostedRunResponse"])
        self.assertIn("checkout.session.completed", contract["requiredWebhookEvents"])
        self.assertIn("customer.subscription.updated", contract["requiredWebhookEvents"])
        self.assertIn("invoice.payment_failed", contract["requiredWebhookEvents"])

    def test_browser_extension_popup_is_bilingual_and_remembers_language(self) -> None:
        manifest = json.loads((BROWSER_EXTENSION / "manifest.json").read_text(encoding="utf-8"))
        popup = (BROWSER_EXTENSION / "popup.html").read_text(encoding="utf-8")
        script = (BROWSER_EXTENSION / "popup.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], release_contract.VERSION)
        self.assertEqual(manifest["default_locale"], "en")
        self.assertEqual(manifest["name"], "__MSG_extensionName__")
        self.assertEqual(manifest["action"]["default_title"], "__MSG_actionTitle__")
        self.assertIn('id="languageZh"', popup)
        self.assertIn('id="languageEn"', popup)
        self.assertIn("data-i18n=", popup)
        self.assertIn("data-i18n-placeholder=", popup)
        self.assertIn("data-i18n-aria-label=", popup)
        self.assertIn("chrome.i18n.getUILanguage", script)
        self.assertIn('"uiLanguage"', script)
        self.assertIn("writeLocalStorage({ uiLanguage: currentLanguage })", script)
        self.assertIn("aria-pressed", script)

        english_block = script.split("const EN_TRANSLATIONS = Object.freeze({", 1)[1].split("});", 1)[0]
        chinese_block = script.split("const ZH_TRANSLATIONS = Object.freeze({", 1)[1].split("});", 1)[0]
        english_keys = set(re.findall(r"^  ([A-Za-z][A-Za-z0-9]*):", english_block, re.MULTILINE))
        chinese_keys = set(re.findall(r"^  ([A-Za-z][A-Za-z0-9]*):", chinese_block, re.MULTILINE))
        html_keys = set(
            re.findall(r'data-i18n(?:-placeholder|-aria-label)?="([A-Za-z][A-Za-z0-9]*)"', popup)
        )
        self.assertSetEqual(english_keys, chinese_keys)
        self.assertTrue(html_keys)
        self.assertTrue(html_keys.issubset(english_keys), sorted(html_keys - english_keys))

        for locale in ["en", "zh_CN"]:
            messages = json.loads(
                (BROWSER_EXTENSION / "_locales" / locale / "messages.json").read_text(encoding="utf-8")
            )
            for key in ["extensionName", "extensionShortName", "extensionDescription", "actionTitle"]:
                self.assertTrue(messages[key]["message"].strip())

    def test_browser_extension_uses_approved_product_identity(self) -> None:
        manifest = json.loads((BROWSER_EXTENSION / "manifest.json").read_text(encoding="utf-8"))
        locales = {
            locale: json.loads(
                (BROWSER_EXTENSION / "_locales" / locale / "messages.json").read_text(encoding="utf-8")
            )
            for locale in ["en", "zh_CN"]
        }
        popup = (BROWSER_EXTENSION / "popup.html").read_text(encoding="utf-8")
        script = (BROWSER_EXTENSION / "popup.js").read_text(encoding="utf-8")
        contract = json.loads((BROWSER_EXTENSION / "billing-contract.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["version"], release_contract.VERSION)
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["permissions"], ["activeTab", "storage", "clipboardWrite"])
        self.assertEqual(manifest["host_permissions"], ["https://www.enhe-tech.com.cn/*"])

        expected_messages = {
            "en": {
                "extensionName": "ENHE Product Promo Maker",
                "extensionShortName": "ENHE Promo",
                "actionTitle": "ENHE Product Promo Maker",
                "extensionDescription": (
                    "Turn product pages into promotional copy, video scripts, publishing assets, and guarded "
                    "local or hosted promotion tasks."
                ),
            },
            "zh_CN": {
                "extensionName": "ENHE 产品推广素材生成器",
                "extensionShortName": "ENHE 推广素材",
                "actionTitle": "ENHE 产品推广素材生成器",
                "extensionDescription": "把产品网页变成推广文案、视频脚本和发布素材，并生成受控的本地或托管推广任务。",
            },
        }
        for locale, expected in expected_messages.items():
            actual = {key: locales[locale][key]["message"] for key in expected}
            self.assertEqual(actual, expected)
            self.assertLessEqual(len(actual["extensionShortName"]), 12)
            self.assertLessEqual(len(actual["extensionDescription"]), 132)

        self.assertIn('data-i18n="productPromise"', popup)
        self.assertIn(
            "Turn product pages into promotional copy, video scripts, and publishing assets.",
            script,
        )
        self.assertIn("把产品网页变成推广文案、视频脚本和发布素材", script)
        self.assertIn('appTitle: "ENHE Product Promo Maker"', script)
        self.assertIn('appTitle: "ENHE 产品推广素材生成器"', script)
        apply_translations = script.split("function applyTranslations() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('document.title = t("appTitle");', apply_translations)
        self.assertNotIn('document.title = `ENHE ${t("appTitle")}`;', apply_translations)
        self.assertEqual(contract["name"], "ENHE Product Promo Maker Billing Contract")

        display_text = "\n".join(
            [
                popup,
                script,
                contract["name"],
                *(json.dumps(messages, ensure_ascii=False) for messages in locales.values()),
            ]
        )
        self.assertNotIn("ENHE 推广管理器", display_text)

    def test_browser_extension_icons_have_expected_size_and_alpha(self) -> None:
        import zlib

        def decode_rgba_png(data: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
            if data[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("invalid PNG signature")

            ihdr = None
            idat_parts = []
            iend_seen = False
            offset = 8
            while offset < len(data):
                if offset + 8 > len(data):
                    raise ValueError("truncated PNG chunk header")
                length = struct.unpack(">I", data[offset : offset + 4])[0]
                chunk_type = data[offset + 4 : offset + 8]
                chunk_start = offset + 8
                chunk_end = chunk_start + length
                if chunk_end + 4 > len(data):
                    raise ValueError("truncated PNG chunk")
                chunk_data = data[chunk_start:chunk_end]
                stored_crc = struct.unpack(">I", data[chunk_end : chunk_end + 4])[0]
                computed_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
                if stored_crc != computed_crc:
                    chunk_name = chunk_type.decode("ascii", errors="replace")
                    raise ValueError(f"{chunk_name} CRC mismatch")
                offset = chunk_end + 4
                if chunk_type == b"IHDR":
                    ihdr = chunk_data
                elif chunk_type == b"IDAT":
                    idat_parts.append(chunk_data)
                elif chunk_type == b"IEND":
                    if length != 0:
                        raise ValueError("IEND chunk must be empty")
                    iend_seen = True
                    if offset != len(data):
                        raise ValueError("trailing data after IEND")
                    break

            if not iend_seen:
                raise ValueError("missing IEND")
            if ihdr is None or len(ihdr) != 13:
                raise ValueError("missing or invalid PNG IHDR")
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", ihdr
            )
            if width <= 0 or height <= 0:
                raise ValueError("invalid PNG dimensions")
            if (bit_depth, color_type, compression, filter_method, interlace) != (8, 6, 0, 0, 0):
                raise ValueError("only 8-bit non-interlaced RGBA PNGs are supported")
            if not idat_parts:
                raise ValueError("missing PNG IDAT")

            bytes_per_pixel = 4
            stride = width * bytes_per_pixel
            raw = zlib.decompress(b"".join(idat_parts))
            if len(raw) != height * (stride + 1):
                raise ValueError("unexpected PNG scanline data length")

            def paeth(left: int, up: int, upper_left: int) -> int:
                estimate = left + up - upper_left
                left_distance = abs(estimate - left)
                up_distance = abs(estimate - up)
                upper_left_distance = abs(estimate - upper_left)
                if left_distance <= up_distance and left_distance <= upper_left_distance:
                    return left
                if up_distance <= upper_left_distance:
                    return up
                return upper_left

            pixels = []
            previous = bytearray(stride)
            offset = 0
            for _ in range(height):
                filter_type = raw[offset]
                scanline = bytearray(raw[offset + 1 : offset + stride + 1])
                offset += stride + 1
                if filter_type not in {0, 1, 2, 3, 4}:
                    raise ValueError(f"unsupported PNG filter type {filter_type}")
                for index in range(stride):
                    left = scanline[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                    up = previous[index]
                    upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                    if filter_type == 0:
                        predictor = 0
                    elif filter_type == 1:
                        predictor = left
                    elif filter_type == 2:
                        predictor = up
                    elif filter_type == 3:
                        predictor = (left + up) // 2
                    else:
                        predictor = paeth(left, up, upper_left)
                    scanline[index] = (scanline[index] + predictor) & 0xFF
                pixels.extend(tuple(scanline[index : index + 4]) for index in range(0, stride, 4))
                previous = scanline
            return width, height, pixels

        versions = {16: "v2", 48: "v2", 128: "v3"}
        for size, version in versions.items():
            icon_path = BROWSER_EXTENSION / "icons" / f"icon{size}.png"
            versioned_path = BROWSER_EXTENSION / "icons" / f"icon{size}-{version}.png"
            self.assertTrue(versioned_path.exists(), versioned_path)
            data = icon_path.read_bytes()
            self.assertEqual(data, versioned_path.read_bytes())
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
            self.assertEqual((width, height), (size, size))
            self.assertEqual(bit_depth, 8)
            self.assertEqual(color_type, 6)
            decoded_width, decoded_height, pixels = decode_rgba_png(data)
            self.assertEqual((decoded_width, decoded_height), (size, size))
            corner_indexes = (0, size - 1, (size - 1) * size, size * size - 1)
            self.assertEqual([pixels[index][3] for index in corner_indexes], [0, 0, 0, 0])

        v2_data = (BROWSER_EXTENSION / "icons" / "icon128-v2.png").read_bytes()
        v3_data = (BROWSER_EXTENSION / "icons" / "icon128-v3.png").read_bytes()
        self.assertEqual(v3_data[-12:-4], b"\x00\x00\x00\x00IEND")
        with self.subTest("missing IEND"):
            with self.assertRaisesRegex(ValueError, "missing IEND"):
                decode_rgba_png(v3_data[:-12])
        invalid_ihdr_crc = bytearray(v3_data)
        ihdr_crc_offset = 8 + 4 + 4 + 13
        invalid_ihdr_crc[ihdr_crc_offset] ^= 0x01
        with self.subTest("invalid IHDR CRC"):
            with self.assertRaisesRegex(ValueError, "CRC"):
                decode_rgba_png(bytes(invalid_ihdr_crc))
        self.assertTrue(v2_data != v3_data, "icon128-v3.png must differ from icon128-v2.png")
        v2_width, v2_height, v2_pixels = decode_rgba_png(v2_data)
        v3_width, v3_height, v3_pixels = decode_rgba_png(v3_data)
        self.assertEqual((v2_width, v2_height), (128, 128))
        self.assertEqual((v3_width, v3_height), (128, 128))
        differences = [
            (index % 128, index // 128)
            for index, (v2_pixel, v3_pixel) in enumerate(zip(v2_pixels, v3_pixels))
            if v2_pixel != v3_pixel
        ]
        self.assertTrue(differences, "icon128-v3.png must contain decoded RGBA pixel changes")
        # Half-open union of the old/new label glyph bounds, padded 1px for antialiasing.
        label_rect = (26, 97, 104, 106)
        outside_differences = [
            (x, y)
            for x, y in differences
            if not (label_rect[0] <= x < label_rect[2] and label_rect[1] <= y < label_rect[3])
        ]
        self.assertFalse(
            outside_differences,
            f"{len(outside_differences)} pixel changes outside label rect; "
            f"first={outside_differences[0] if outside_differences else None}",
        )

    def test_browser_extension_package_script_builds_store_submission_zip(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="browser-extension-package-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(PACKAGE_BROWSER_EXTENSION),
                "--out-dir",
                str(out_dir / "dist"),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads((out_dir / "dist/browser-extension-package-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["version"], release_contract.VERSION)
        package_path = Path(report["package"])
        self.assertEqual(package_path.name, f"enhe-promotion-manager-{release_contract.VERSION}.zip")
        self.assertTrue(package_path.exists())
        archive_sha256 = hashlib.sha256(package_path.read_bytes()).hexdigest().upper()
        self.assertEqual(report.get("archiveName"), package_path.name)
        self.assertEqual(report.get("archiveSha256"), archive_sha256)
        report_markdown = (out_dir / "dist/browser-extension-package-report.md").read_text(encoding="utf-8")
        self.assertIn(f"- Archive: `{package_path.name}`", report_markdown)
        self.assertIn(f"- SHA-256: `{archive_sha256}`", report_markdown)
        self.assertIn(f"- Version: `{release_contract.VERSION}`", report_markdown)
        self.assertTrue(report["checks"]["versionMatchesDistributionContract"])
        self.assertTrue(report["checks"]["deterministicArchiveMetadata"])
        self.assertTrue(report["checks"]["manifestV3"])
        self.assertTrue(report["checks"]["icons"])
        self.assertTrue(report["checks"]["noRemoteExecutableCode"])
        self.assertEqual(
            report["storeSubmission"]["privacyPolicyUrl"],
            "https://www.enhe-tech.com.cn/promotion-manager/privacy",
        )
        self.assertEqual(
            report["storeSubmission"]["supportUrl"],
            "https://www.enhe-tech.com.cn/promotion-manager/support",
        )
        with zipfile.ZipFile(package_path) as package:
            infos = package.infolist()
            names = {info.filename for info in infos}
            self.assertEqual([info.filename for info in infos], sorted(names))
            self.assertEqual(package.comment, b"")
            for info in infos:
                self.assertEqual(info.date_time, release_contract.FIXED_ZIP_TIMESTAMP)
                self.assertEqual(info.create_system, release_contract.FIXED_ZIP_CREATE_SYSTEM)
                self.assertEqual(info.external_attr, release_contract.FIXED_ZIP_EXTERNAL_ATTR)
                self.assertEqual(info.compress_type, release_contract.FIXED_ZIP_COMPRESSION)
                self.assertEqual(info.extra, b"")
                self.assertEqual(info.comment, b"")
        self.assertIn("manifest.json", names)
        self.assertIn("popup.html", names)
        self.assertIn("popup.css", names)
        self.assertIn("popup.js", names)
        self.assertIn("billing-contract.json", names)
        self.assertIn("icons/icon16.png", names)
        self.assertIn("icons/icon48.png", names)
        self.assertIn("icons/icon128.png", names)
        self.assertIn("_locales/en/messages.json", names)
        self.assertIn("_locales/zh_CN/messages.json", names)

    def test_browser_extension_package_is_deterministic_across_source_metadata_changes(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="browser-extension-determinism-test-"))
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        project_dir = base / "mini-project"
        scripts_dir = project_dir / "scripts"
        extension_dir = project_dir / "browser-extension"
        scripts_dir.mkdir(parents=True)
        shutil.copy2(PACKAGE_BROWSER_EXTENSION, scripts_dir / PACKAGE_BROWSER_EXTENSION.name)
        shutil.copy2(ROOT / "scripts" / "distribution_contract.py", scripts_dir / "distribution_contract.py")
        shutil.copytree(BROWSER_EXTENSION, extension_dir)

        first_out = project_dir / "first"
        second_out = project_dir / "second"
        subprocess.run(
            [sys.executable, str(scripts_dir / PACKAGE_BROWSER_EXTENSION.name), "--out-dir", str(first_out)],
            cwd=project_dir,
            check=True,
        )
        for index, path in enumerate(sorted(item for item in extension_dir.rglob("*") if item.is_file())):
            timestamp = 946684800 + index * 2
            os.utime(path, (timestamp, timestamp))
            path.chmod(0o600 if index % 2 else 0o644)
        subprocess.run(
            [sys.executable, str(scripts_dir / PACKAGE_BROWSER_EXTENSION.name), "--out-dir", str(second_out)],
            cwd=project_dir,
            check=True,
        )

        archive_name = f"enhe-promotion-manager-{release_contract.VERSION}.zip"
        first_bytes = (first_out / archive_name).read_bytes()
        second_bytes = (second_out / archive_name).read_bytes()
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(hashlib.sha256(first_bytes).digest(), hashlib.sha256(second_bytes).digest())

    def test_browser_extension_package_rejects_manifest_contract_version_drift(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="browser-extension-version-drift-test-"))
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        project_dir = base / "mini-project"
        scripts_dir = project_dir / "scripts"
        extension_dir = project_dir / "browser-extension"
        scripts_dir.mkdir(parents=True)
        shutil.copy2(PACKAGE_BROWSER_EXTENSION, scripts_dir / PACKAGE_BROWSER_EXTENSION.name)
        shutil.copy2(ROOT / "scripts" / "distribution_contract.py", scripts_dir / "distribution_contract.py")
        shutil.copytree(BROWSER_EXTENSION, extension_dir)
        manifest_path = extension_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "9.9.9"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        out_dir = project_dir / "dist"
        result = subprocess.run(
            [sys.executable, str(scripts_dir / PACKAGE_BROWSER_EXTENSION.name), "--out-dir", str(out_dir)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads((out_dir / "browser-extension-package-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("versionMatchesDistributionContract", report["missing"])
        self.assertFalse((out_dir / "enhe-promotion-manager-9.9.9.zip").exists())

    def test_browser_extension_package_defaults_to_v054_without_touching_v053_archive(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="browser-extension-default-package-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        project_dir = out_dir / "mini-project"
        package_script = project_dir / "scripts" / "package_browser_extension.py"
        extension_dir = project_dir / "browser-extension"
        package_script.parent.mkdir(parents=True)
        shutil.copy2(PACKAGE_BROWSER_EXTENSION, package_script)
        shutil.copy2(ROOT / "scripts" / "distribution_contract.py", package_script.parent / "distribution_contract.py")
        for relative_path in [
            "manifest.json",
            "popup.html",
            "popup.css",
            "popup.js",
            "billing-contract.json",
            "icons/icon16.png",
            "icons/icon48.png",
            "icons/icon128.png",
        ]:
            destination = extension_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BROWSER_EXTENSION / relative_path, destination)

        historical_paths = [
            project_dir / "dist" / "v0.5.3" / "enhe-promotion-manager-0.5.3.zip",
            project_dir / "dist" / "v0.5.3" / "browser-extension-package-report.json",
            project_dir / "dist" / "v0.5.3" / "browser-extension-package-report.md",
        ]
        historical_contents = {
            path: f"controlled historical sentinel: {path.name}".encode("utf-8")
            for path in historical_paths
        }
        for path, contents in historical_contents.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)

        subprocess.run(
            [sys.executable, str(package_script)],
            check=True,
            cwd=project_dir,
        )

        versioned_dir = project_dir / "dist" / f"v{release_contract.VERSION}"
        report_path = versioned_dir / "browser-extension-package-report.json"
        self.assertTrue(report_path.exists())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["version"], release_contract.VERSION)
        self.assertTrue(
            (versioned_dir / f"enhe-promotion-manager-{release_contract.VERSION}.zip").exists()
        )
        for path, expected in historical_contents.items():
            self.assertEqual(path.read_bytes(), expected, str(path))

    def test_current_readmes_use_isolated_v054_package_command(self) -> None:
        expected_command = (
            'python scripts\\package_browser_extension.py --out-dir '
            f'".\\dist\\v{release_contract.VERSION}"'
        )
        retired_tokens = [
            'python scripts\\package_browser_extension.py --out-dir ".\\dist"',
            r"dist\enhe-promotion-manager-<version>.zip",
            r"dist\browser-extension-package-report.json",
            r"dist\browser-extension-package-report.md",
        ]

        for readme_path in [
            README,
            ROOT / "README.en.md",
            ROOT / "README.zh-CN.md",
        ]:
            readme = readme_path.read_text(encoding="utf-8")
            with self.subTest(readme=readme_path):
                self.assertIn(expected_command, readme)
                for retired_token in retired_tokens:
                    self.assertNotIn(retired_token, readme)

    def test_browser_extension_guides_use_isolated_v054_package_outputs(self) -> None:
        expected_command = (
            'python scripts\\package_browser_extension.py --out-dir '
            f'".\\dist\\v{release_contract.VERSION}"'
        )
        expected_outputs = [
            fr"dist\v{release_contract.VERSION}\enhe-promotion-manager-{release_contract.VERSION}.zip",
            fr"dist\v{release_contract.VERSION}\browser-extension-package-report.json",
            fr"dist\v{release_contract.VERSION}\browser-extension-package-report.md",
        ]
        retired_tokens = [
            'python scripts\\package_browser_extension.py --out-dir ".\\dist"',
            r"dist\enhe-promotion-manager-<version>.zip",
            r"dist\browser-extension-package-report.json",
            r"dist\browser-extension-package-report.md",
            "`browser-extension-package-report.json`",
        ]

        for guide_path in [
            DOCS / "browser-extension.md",
            DOCS / "zh-CN" / "browser-extension.md",
        ]:
            guide = guide_path.read_text(encoding="utf-8")
            with self.subTest(guide=guide_path):
                self.assertIn(release_contract.VERSION, guide)
                self.assertIn(expected_command, guide)
                for output in expected_outputs:
                    self.assertIn(output, guide)
                for retired_token in retired_tokens:
                    self.assertNotIn(retired_token, guide)

        for roadmap_path in [
            DOCS / "100-percent-completion-roadmap.md",
            DOCS / "zh-CN" / "100-percent-completion-guide.md",
        ]:
            roadmap = roadmap_path.read_text(encoding="utf-8")
            with self.subTest(roadmap=roadmap_path):
                self.assertIn(expected_command, roadmap)
                for retired_token in retired_tokens:
                    self.assertNotIn(retired_token, roadmap)

    def test_license_service_backend_skeleton_matches_extension_billing_contract(self) -> None:
        package_json_path = LICENSE_SERVICE / "package.json"
        server_path = LICENSE_SERVICE / "src" / "server.js"
        state_store_path = LICENSE_SERVICE / "src" / "state-store.js"
        hosted_worker_path = LICENSE_SERVICE / "src" / "hosted-worker.js"
        migrate_path = LICENSE_SERVICE / "src" / "migrate.js"
        worker_path = LICENSE_SERVICE / "src" / "worker.js"
        migration_path = LICENSE_SERVICE / "migrations" / "001_state_store.sql"
        env_example_path = LICENSE_SERVICE / ".env.example"
        readme_path = LICENSE_SERVICE / "README.md"

        for path in [
            package_json_path,
            server_path,
            state_store_path,
            hosted_worker_path,
            migrate_path,
            worker_path,
            migration_path,
            env_example_path,
            readme_path,
        ]:
            self.assertTrue(path.exists(), path)

        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        dependencies = package_json.get("dependencies", {})
        scripts = package_json.get("scripts", {})
        self.assertIn("express", dependencies)
        self.assertIn("stripe", dependencies)
        self.assertIn("pg", dependencies)
        self.assertEqual(scripts["migrate"], "node src/migrate.js")
        self.assertEqual(scripts["worker"], "node src/worker.js")
        self.assertEqual(scripts["test"], "node --test")

        server = server_path.read_text(encoding="utf-8")
        for endpoint in [
            "/health",
            "/promotion-manager/checkout",
            "/promotion-manager/billing",
            "/promotion-manager/:page(privacy|terms|refund|support)",
            "/promotion-manager/runs/:runId",
            "/api/promotion-manager/license",
            "/api/promotion-manager/usage/authorize",
            "/api/promotion-manager/usage/commit",
            "/api/promotion-manager/run",
            "/api/promotion-manager/run/:runId",
            "/api/promotion-manager/webhooks/stripe",
        ]:
            self.assertIn(endpoint, server)
        for marker in [
            "stripe.checkout.sessions.create",
            'mode: "subscription"',
            "stripe.webhooks.constructEvent",
            "express.raw",
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "LICENSE_PEPPER",
            "licenseKeyHash",
            "idempotencyKey",
            "createStateStore",
            "startHostedWorker",
            "statusUrl",
            "renderLegalPage",
        ]:
            self.assertIn(marker, server)

        state_store = state_store_path.read_text(encoding="utf-8")
        for marker in ["PostgresStateStore", "DATABASE_URL", "pg_advisory_xact_lock", "promotion_manager_state"]:
            self.assertIn(marker, state_store)
        hosted_worker = hosted_worker_path.read_text(encoding="utf-8")
        for marker in [
            "buildHostedCommand",
            "unsupported_hosted_command_type",
            "safeWorkerEnv",
            "I_APPROVE_PUBLISH",
            "PUBLISH_DRY_RUN",
            "REQUIRE_MANUAL_APPROVAL",
            "private_product_url_blocked",
        ]:
            self.assertIn(marker, hosted_worker)
        self.assertNotIn("childProcess.exec(", hosted_worker)
        self.assertIn("DATABASE_URL is not set", migrate_path.read_text(encoding="utf-8"))
        self.assertIn("startHostedWorker", worker_path.read_text(encoding="utf-8"))
        self.assertIn("CREATE TABLE IF NOT EXISTS promotion_manager_state", migration_path.read_text(encoding="utf-8"))

        env_example = env_example_path.read_text(encoding="utf-8")
        for marker in [
            "DATABASE_URL=",
            "STRIPE_SECRET_KEY=",
            "STRIPE_WEBHOOK_SECRET=",
            "STRIPE_PRICE_STARTER=",
            "STRIPE_PRICE_GROWTH=",
            "ENHE_PUBLIC_BASE_URL=",
            "LICENSE_PEPPER=",
            "LICENSE_SERVICE_STATE_FILE=",
            "HOSTED_RUN_OUTPUT_ROOT=",
            "HOSTED_WORKER_ENABLED=",
            "HOSTED_WORKER_MODE=",
            "PYTHON_BIN=",
        ]:
            self.assertIn(marker, env_example)
        for forbidden in ["sk_live_", "whsec_", "github_pat_", "GITHUB_TOKEN=" + "github_"]:
            self.assertNotIn(forbidden, env_example)
            self.assertNotIn(forbidden, server)

        readme = readme_path.read_text(encoding="utf-8")
        self.assertIn("npm install", readme)
        self.assertIn("npm run migrate", readme)
        self.assertIn("npm run worker", readme)
        self.assertIn("npm run start", readme)
        self.assertIn("PostgreSQL", readme)
        self.assertIn("hosted worker", readme)
        self.assertIn("/promotion-manager/privacy", readme)
        self.assertIn("Stripe CLI", readme)
        self.assertIn("store approval remains external", readme)

        deploy_readme = (ROOT / "deploy/promotion-manager/README.md").read_text(encoding="utf-8")
        deploy_env = (ROOT / "deploy/promotion-manager/.env.production.example").read_text(encoding="utf-8")
        nginx = (ROOT / "deploy/promotion-manager/nginx-promotion-manager.conf").read_text(encoding="utf-8")
        for marker in ["same HTTPS host", "Server Requirement", "systemd", "npm run migrate"]:
            self.assertIn(marker, deploy_readme)
        for marker in ["DATABASE_URL=", "HOSTED_RUN_OUTPUT_ROOT=", "HOSTED_WORKER_MODE=execute"]:
            self.assertIn(marker, deploy_env)
        for marker in ["/api/promotion-manager/", "/promotion-manager/privacy", "/promotion-manager/runs/"]:
            self.assertIn(marker, nginx)

    def test_store_copy_uses_approved_bilingual_product_identity(self) -> None:
        chrome = (DOCS / "store" / "chrome-listing.md").read_text(encoding="utf-8")
        edge = (DOCS / "store" / "edge-listing.md").read_text(encoding="utf-8")
        reviewer_notes = (DOCS / "store" / "reviewer-notes.md").read_text(encoding="utf-8")
        screenshot_plan = (DOCS / "store" / "screenshot-plan.md").read_text(encoding="utf-8")
        submission_en = (DOCS / "extension-store-submission.md").read_text(encoding="utf-8")
        submission_zh = (DOCS / "zh-CN" / "extension-store-submission.md").read_text(encoding="utf-8")

        documents = {
            "chrome listing": chrome,
            "edge listing": edge,
            "reviewer notes": reviewer_notes,
            "screenshot plan": screenshot_plan,
            "English submission guide": submission_en,
            "Chinese submission guide": submission_zh,
        }
        for label, text in documents.items():
            self.assertIn("ENHE Product Promo Maker", text)
            self.assertNotIn("ENHE 推广管理器", text)
            self.assertNotIn(
                "ENHE Promotion Manager",
                text,
                f"{label} contains the legacy English display name",
            )
        for label, text in [
            ("chrome listing", chrome),
            ("edge listing", edge),
            ("reviewer notes", reviewer_notes),
            ("screenshot plan", screenshot_plan),
        ]:
            self.assertNotIn("0.5.2", text, f"{label} contains the superseded version")

        outcomes_en = r"(?:virality|viral|conversions?|traffic|sales|revenue)"
        outcomes_zh = r"(?:爆款|转化|流量|销量|销售额|销售增长|收入|收益)"
        negative_en = re.compile(
            r"(?:\bno(?:\s+[A-Za-z'-]+){0,3}|"
            r"\b(?:do|does|did|is|are|was|were|will|can|could|should|would|have|has)"
            r"(?:\s+not|n't)(?:\s+[A-Za-z'-]+){0,3}|"
            r"\b(?:not|never|cannot|can't|won't)(?:\s+[A-Za-z'-]+){0,3}|"
            r"\bunable\s+to(?:\s+[A-Za-z'-]+){0,3})\s*$",
            flags=re.IGNORECASE,
        )
        negative_zh = re.compile(r"(?:无法|不能|不会|没有|不|未)[\u4e00-\u9fff]{0,4}\s*$")
        emphatic_en = re.compile(
            r"(?:\bnot\s+(?:only|just)|n't\s+(?:only|just))\s*$",
            flags=re.IGNORECASE,
        )
        emphatic_zh = re.compile(r"(?:不仅|不只)\s*$")
        negation_suffix_length = 128
        promotional_claim_patterns = [
            (
                re.compile(
                    rf"\b(?P<trigger>guarantee(?:d|s)?|guaranteeing|"
                    rf"ensure(?:d|s)?|ensuring)\b[^.!?;,\n]{{0,80}}"
                    rf"\b{outcomes_en}\b",
                    flags=re.IGNORECASE,
                ),
                negative_en,
            ),
            (
                re.compile(
                    rf"\b(?P<trigger>increas(?:e|es|ed|ing)|boost(?:s|ed|ing)?|"
                    rf"driv(?:e|es|en|ing)|drove|deliver(?:s|ed|ing)?)\b"
                    rf"[^.!?;,\n]{{0,80}}\b{outcomes_en}\b",
                    flags=re.IGNORECASE,
                ),
                negative_en,
            ),
            (
                re.compile(
                    r"\b(?P<trigger>support(?:s|ed|ing)?|enabl(?:e|es|ed|ing)|"
                    r"offer(?:s|ed|ing)?|provid(?:e|es|ed|ing))\b[^.!?;,\n]{0,40}"
                    r"\b(?:automatic|automated) publishing\b",
                    flags=re.IGNORECASE,
                ),
                negative_en,
            ),
            (
                re.compile(
                    r"\b(?P<trigger>will|can)\s+(?:automatically\s+publish|auto-publish)\b",
                    flags=re.IGNORECASE,
                ),
                negative_en,
            ),
            (
                re.compile(
                    rf"\b{outcomes_en}\b[^.!?;,\n]{{0,30}}"
                    r"\b(?P<trigger>(?:is|are|was|were)\s+guaranteed)\b",
                    flags=re.IGNORECASE,
                ),
                negative_en,
            ),
            (
                re.compile(
                    rf"\b(?P<trigger>is|are|was|were)\s+{outcomes_en}\s+guaranteed\b",
                    flags=re.IGNORECASE,
                ),
                negative_en,
            ),
            (
                re.compile(rf"(?P<trigger>保证|确保)[^。！？；，\n]{{0,40}}{outcomes_zh}"),
                negative_zh,
            ),
            (
                re.compile(rf"(?P<trigger>提升|增加|带来|实现)[^。！？；，\n]{{0,40}}{outcomes_zh}"),
                negative_zh,
            ),
            (
                re.compile(r"(?P<trigger>支持|提供|实现)[^。！？；，\n]{0,12}自动发布"),
                negative_zh,
            ),
            (re.compile(r"(?P<trigger>将|会|可)自动发布"), negative_zh),
        ]

        def is_negated(clause: str, trigger_index: int, negative_pattern: re.Pattern[str]) -> bool:
            suffix = clause[max(0, trigger_index - negation_suffix_length) : trigger_index]
            if negative_pattern is negative_en and emphatic_en.search(suffix):
                return False
            if negative_pattern is negative_zh and emphatic_zh.search(suffix):
                return False
            return negative_pattern.search(suffix) is not None

        def has_promotional_claim(text: str) -> bool:
            clauses = re.split(
                r"(?:[,.!?;\n。！？；，]+|\b(?:but|and|yet)\b|但是|但|并且|并|而且|而)",
                text,
                flags=re.IGNORECASE,
            )
            for clause in clauses:
                for claim_pattern, negative_pattern in promotional_claim_patterns:
                    for match in claim_pattern.finditer(clause):
                        if not is_negated(clause, match.start("trigger"), negative_pattern):
                            return True
            return False

        for sample in [
            "does not guarantee sales or revenue and does not support automatic publishing",
            "不保证销量，也不支持自动发布",
            "We make no guarantee of sales",
            "We do not explicitly guarantee sales",
            "我们无法保证销量",
            "我们不会确保销售额",
            "We don't guarantee sales",
            "We don't support automatic publishing",
            "This tool isn't designed to guarantee sales",
        ]:
            self.assertFalse(has_promotional_claim(sample), f"legal disclaimer was rejected: {sample}")
        for sample in [
            "We guarantee sales and support automatic publishing.",
            "我们保证销量并支持自动发布。",
            "We guarantee conversions",
            "Guaranteed sales",
            "support automated publishing",
            "will auto-publish",
            "我们保证销售增长",
            "No setup required, guaranteed sales",
            "We do not collect credentials, yet guarantee sales",
            "Sales are guaranteed",
            "无需设置即可保证销量",
            "我们不收集密码, 保证销量",
            "We not only guarantee sales",
            "It doesn't just guarantee revenue",
            "Not only are sales guaranteed",
            "我们不仅保证销量",
        ]:
            self.assertTrue(has_promotional_claim(sample), f"promotional claim was missed: {sample}")
        for label, text in documents.items():
            self.assertFalse(
                has_promotional_claim(text),
                f"{label} contains a positive promotional outcome claim",
            )

        for text in [chrome, edge, submission_zh]:
            self.assertIn("ENHE 产品推广素材生成器", text)

        english_promise = (
            "Turn product pages into promotional copy, video scripts, publishing assets, "
            "and guarded local or hosted promotion tasks."
        )
        chinese_promise = "把产品网页变成推广文案、视频脚本和发布素材，并生成受控的本地或托管推广任务。"
        self.assertIn(english_promise, chrome)
        self.assertIn(chinese_promise, chrome)
        english_field_block = (
            "## English (default)\n\n"
            "### Name\n\n"
            "ENHE Product Promo Maker\n\n"
            "### Short Description\n\n"
            f"{english_promise}"
        )
        chinese_field_block = (
            "## Simplified Chinese\n\n"
            "### 名称\n\n"
            "ENHE 产品推广素材生成器\n\n"
            "### 简短说明\n\n"
            f"{chinese_promise}"
        )
        for label, listing in [("chrome listing", chrome), ("edge listing", edge)]:
            self.assertIn(english_field_block, listing, f"{label} has the wrong English fields")
            self.assertIn(chinese_field_block, listing, f"{label} has the wrong Chinese fields")
            self.assertIn(f"### Detailed Description\n\n{english_promise}", listing)
            self.assertIn(f"### 详细说明\n\n{chinese_promise}", listing)

        reviewer_sentence = (
            "ENHE Product Promo Maker is a Manifest V3 extension that turns a product page "
            "selected by the user into promotional copy, video scripts, publishing assets, "
            "and guarded local commands or hosted ENHE run payloads."
        )
        self.assertIn(f"```text\n{reviewer_sentence}\n", reviewer_notes)

        self.assertIn("ENHE Promo Maker", screenshot_plan)
        screenshot_lines = screenshot_plan.splitlines()
        for asset_line in [
            "- `browser-extension/icons/icon128.png` — global store icon with the ENHE logo and "
            "the label `ENHE Promo Maker`.",
            f"- `dist/v{release_contract.VERSION}/store-assets/"
            "enhe-product-promo-maker-en-1280x800.png` — English popup.",
            f"- `dist/v{release_contract.VERSION}/store-assets/"
            "enhe-product-promo-maker-zh-1280x800.png` — Simplified Chinese popup.",
        ]:
            self.assertIn(asset_line, screenshot_lines)

        submission_markers = [
            "https://developer.chrome.com/docs/webstore/publish",
            "https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/publish/publish-extension",
            "https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code",
            "dloklkbnmoigemnfigbkibogmgbieppl",
            "https://www.enhe-tech.com.cn/promotion-manager/privacy",
            "https://www.enhe-tech.com.cn/promotion-manager/support",
            "enhe-promotion-manager-0.5.3.zip",
        ]
        for label, text in [
            ("English submission guide", submission_en),
            ("Chinese submission guide", submission_zh),
        ]:
            for marker in submission_markers:
                self.assertIn(marker, text, f"{label} missing {marker}")
            self.assertIn("dist/v0.5.3", text.replace("\\", "/"))

        self.assertIn(
            "Its validated archive is `dist\\v0.5.3\\enhe-promotion-manager-0.5.3.zip`; "
            "this is an immutable historical verification asset, not a package to upload again.",
            submission_en,
        )
        self.assertIn(
            "其已验证归档为 `dist\\v0.5.3\\enhe-promotion-manager-0.5.3.zip`；"
            "它只是不可修改的历史验证资产，不是再次上传的操作指令。",
            submission_zh,
        )
        for text in (submission_en, submission_zh):
            self.assertNotIn("v0.5.2", text)
            self.assertIn("<NEXT_VERSION>", text)
        self.assertNotIn("pending review", submission_en.lower())
        self.assertNotIn(
            "Upload `dist\\v0.5.3\\enhe-promotion-manager-0.5.3.zip`",
            submission_en,
        )
        self.assertNotIn(
            "上传 `dist\\v0.5.3\\enhe-promotion-manager-0.5.3.zip`",
            submission_zh,
        )

        chrome_upload_step_en = (
            f"Package v{release_contract.VERSION} and upload "
            f"`dist\\v{release_contract.VERSION}\\enhe-promotion-manager-"
            f"{release_contract.VERSION}.zip` "
            "as a later update to this item."
        )
        screenshots_step_en = (
            "Upload next-version icons and both reviewed localized screenshots from "
            "`dist\\v<NEXT_VERSION>\\store-assets`."
        )
        chrome_submit_step_en = (
            "Paste `docs/store/reviewer-notes.md`, confirm the item ID again, and submit the "
            "next version for review. If login, account verification, or captcha is required, "
            "pause for the account owner to complete it."
        )
        edge_status_step_en = (
            "Verify the current Edge listing status independently. If v0.5.3 is published for "
            "that Edge item, increment the manifest version for the next version; if v0.5.3 is "
            "not published, follow the applicable Edge submission flow without treating the "
            "Chrome publication as Edge publication."
        )
        edge_upload_step_en = (
            "Package and upload "
            "`dist\\v<NEXT_VERSION>\\enhe-promotion-manager-<NEXT_VERSION>.zip` "
            "as the next-version update."
        )
        edge_submit_step_en = (
            "Confirm the generated publishing assets require user approval, then submit the "
            "next version for certification. If login, account verification, or captcha is "
            "required, pause for the account owner to complete it."
        )
        chrome_upload_step_zh = (
            f"打包 v{release_contract.VERSION}，并在后续将 `dist\\v{release_contract.VERSION}\\"
            f"enhe-promotion-manager-{release_contract.VERSION}.zip` "
            "作为该条目的更新上传。"
        )
        screenshots_step_zh = (
            "上传 `dist\\v<NEXT_VERSION>\\store-assets` 中下一版图标和两张已审核的本地化截图。"
        )
        chrome_submit_step_zh = (
            "粘贴 `docs/store/reviewer-notes.md`，再次确认条目 ID 后提交下一版审核。"
            "若需要登录、账号验证或 captcha，由账号所有者完成后再继续。"
        )
        edge_status_step_zh = (
            "独立核验当前 Edge 条目状态。若 v0.5.3 已在该 Edge 条目发布，再提高 manifest "
            "的版本号；若 v0.5.3 尚未发布，则按适用的 Edge 提交流程处理，不得把 Chrome "
            "的发布状态当作 Edge 已发布。"
        )
        edge_upload_step_zh = (
            "打包并上传 `dist\\v<NEXT_VERSION>\\enhe-promotion-manager-<NEXT_VERSION>.zip` "
            "作为下一版更新。"
        )
        edge_submit_step_zh = (
            "确认生成的发布素材需要用户批准后提交下一版认证。若需要登录、账号验证或 "
            "captcha，由账号所有者完成后再继续。"
        )
        submission_sections = [
            (
                "English Chrome steps",
                submission_en.split("## Chrome Web Store Steps", 1)[1].split(
                    "## Microsoft Edge Add-ons Steps", 1
                )[0],
                [chrome_upload_step_en, screenshots_step_en, chrome_submit_step_en],
            ),
            (
                "English Edge steps",
                submission_en.split("## Microsoft Edge Add-ons Steps", 1)[1].split(
                    "## Reviewer Notes Template", 1
                )[0],
                [edge_status_step_en, edge_upload_step_en, screenshots_step_en, edge_submit_step_en],
            ),
            (
                "Chinese Chrome steps",
                submission_zh.split("## Chrome Web Store 上架步骤", 1)[1].split(
                    "## Microsoft Edge Add-ons 上架步骤", 1
                )[0],
                [chrome_upload_step_zh, screenshots_step_zh, chrome_submit_step_zh],
            ),
            (
                "Chinese Edge steps",
                submission_zh.split("## Microsoft Edge Add-ons 上架步骤", 1)[1].split(
                    "## 审核备注模板", 1
                )[0],
                [edge_status_step_zh, edge_upload_step_zh, screenshots_step_zh, edge_submit_step_zh],
            ),
        ]
        for label, section, required_steps in submission_sections:
            normalized_section_lines = [
                re.sub(r"^\d+\.\s*", "", line) for line in section.splitlines()
            ]
            for required_step in required_steps:
                self.assertIn(required_step, normalized_section_lines, f"{label} missing step")
            step_positions = [normalized_section_lines.index(step) for step in required_steps]
            self.assertEqual(step_positions, sorted(step_positions), f"{label} steps are out of order")

        submission_en_lines = [
            re.sub(r"^\d+\.\s*", "", line) for line in submission_en.splitlines()
        ]
        for line in [
            "- `activeTab`: capture the current product URL only after the user acts on the extension.",
            "- `storage`: store local license and endpoint settings.",
            "- `clipboardWrite`: copy generated local commands and hosted-run payloads only when requested by the user.",
            "- `https://www.enhe-tech.com.cn/*`: validate licenses, open checkout and billing, reserve credits, submit hosted-run payloads, and retrieve hosted-run status.",
            "- No remote code is loaded by `<script src=\"https://...\">`, dynamic imports, `importScripts`, `eval`, or `new Function`.",
            "- Remote ENHE endpoints are used for data only: license validation, usage authorization, hosted run requests, checkout, and billing portal.",
            "All extension logic stays inside the package. Remote services return data only and do not provide executable extension code.",
        ]:
            self.assertIn(line, submission_en_lines)

        submission_zh_lines = [
            re.sub(r"^\d+\.\s*", "", line) for line in submission_zh.splitlines()
        ]
        for line in [
            "- `activeTab`：仅在用户操作扩展后读取当前产品页面 URL。",
            "- `storage`：保存本地许可证和 endpoint 设置。",
            "- `clipboardWrite`：仅按用户请求复制生成的本地命令和托管运行载荷。",
            "- `https://www.enhe-tech.com.cn/*`：校验许可证、打开结账和账单页面、预留积分、提交托管运行载荷及查询状态。",
            "- 不加载 remote code：没有远程 `<script src=\"https://...\">`、动态 import、`importScripts`、`eval` 或 `new Function`。",
            "- ENHE 远程接口只返回许可证校验、使用授权、托管运行请求、结账和账单门户所需的数据。",
            "所有扩展逻辑都在安装包内。远程服务仅返回数据，不向扩展提供可执行代码。",
        ]:
            self.assertIn(line, submission_zh_lines)
        self.assertIn("生成的发布素材需要用户批准", submission_zh)
        self.assertIn("运行完成后按实际消耗结算积分。", submission_zh)
        self.assertNotIn("运行完成后按实际消耗提交积分。", submission_zh)

    def test_browser_extension_store_submission_docs_are_bilingual(self) -> None:
        english = (DOCS / "extension-store-submission.md").read_text(encoding="utf-8")
        chinese = (DOCS / "zh-CN" / "extension-store-submission.md").read_text(encoding="utf-8")
        zh_extension = (DOCS / "zh-CN" / "browser-extension.md").read_text(encoding="utf-8")

        for text in [english, chinese]:
            self.assertIn("https://developer.chrome.com/docs/webstore/publish", text)
            self.assertIn(
                "https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/publish/publish-extension",
                text,
            )
            self.assertIn("browser-extension-package-report.json", text)
            self.assertIn("privacy", text.lower())
            self.assertIn("remote code", text.lower())
        self.assertIn("收费订阅", zh_extension)
        self.assertIn("上架", chinese)

    def test_privacy_policy_is_publication_ready(self) -> None:
        privacy = (DOCS / "legal/privacy-policy.md").read_text(encoding="utf-8")
        lower = privacy.lower()

        self.assertNotIn("publication-ready draft", lower)
        self.assertNotIn("review it with counsel", lower)
        self.assertNotIn("before production launch", lower)
        self.assertIn("automatically deleted 30 days", lower)
        self.assertIn("security and audit logs are retained for 180 days", lower)
        self.assertIn("payment, refund, and legally required accounting records", lower)
        self.assertIn("applicable law", lower)
        self.assertIn("huqingwei5942@gmail.com", privacy)
        self.assertIn("request access to or deletion of data", lower)
        self.assertIn("mandatory retention", lower)

    def test_legal_store_and_deployment_launch_materials_are_ready(self) -> None:
        required_markers = {
            DOCS / "legal/privacy-policy.md": ["Privacy Policy", "Data We Do Not Collect"],
            DOCS / "legal/terms-of-service.md": ["Terms Of Service", "Publishing Boundary"],
            DOCS / "legal/refund-policy.md": ["Refund Policy", "Credit Usage"],
            DOCS / "legal/support.md": ["Support", "Hosted run ID"],
            DOCS / "store/chrome-listing.md": ["Chrome Web Store Listing Draft", "Permission Justification"],
            DOCS / "store/edge-listing.md": ["Microsoft Edge Add-ons Listing Draft", "Certification Notes"],
            DOCS / "store/reviewer-notes.md": ["Store Reviewer Notes", "Manifest V3"],
            DOCS / "store/screenshot-plan.md": ["Store Screenshot Plan", "Hosted run"],
            ROOT / "deploy/promotion-manager/README.md": ["same HTTPS host", "Server Requirement", "systemd"],
            ROOT / "deploy/promotion-manager/nginx-promotion-manager.conf": [
                "/api/promotion-manager/",
                "/promotion-manager/privacy",
                "/promotion-manager/runs/",
            ],
            ROOT / "deploy/promotion-manager/enhe-promotion-manager-api.service": ["ExecStart", "api.env"],
            ROOT / "deploy/promotion-manager/enhe-promotion-manager-worker.service": ["ExecStart", "api.env"],
        }
        for path, markers in required_markers.items():
            self.assertTrue(path.exists(), path)
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, f"{path} missing {marker}")

        english_identity = "ENHE Product Promo Maker (formerly ENHE Promotion Manager)"
        english_legal_expectations = {
            DOCS / "legal/privacy-policy.md": {
                "prefix": (
                    "# ENHE Product Promo Maker Privacy Policy\n\n"
                    "Effective date: 2026-07-15\n\n"
                    "This policy explains how ENHE AI processes information for "
                    "ENHE Product Promo Maker (formerly ENHE Promotion Manager), including its browser "
                    "extension and optional hosted service.\n\n"
                ),
            },
            DOCS / "legal/terms-of-service.md": {
                "prefix": (
                    "# ENHE Product Promo Maker Terms Of Service\n\n"
                    "Effective date: 2026-07-10\n\n"
                    "This is a launch draft. Review with counsel before public launch.\n\n"
                    "## Service\n\n"
                    "ENHE Product Promo Maker (formerly ENHE Promotion Manager) provides a browser "
                    "extension, local Codex workflow commands, and optional ENHE-hosted promotion task execution.\n\n"
                ),
            },
            DOCS / "legal/refund-policy.md": {
                "prefix": (
                    "# ENHE Product Promo Maker Refund Policy\n\n"
                    "Effective date: 2026-07-10\n\n"
                    "This policy applies to purchases of "
                    "ENHE Product Promo Maker (formerly ENHE Promotion Manager).\n\n"
                ),
            },
            DOCS / "legal/support.md": {
                "prefix": (
                    "# ENHE Product Promo Maker Support\n\n"
                    "Support for ENHE Product Promo Maker (formerly ENHE Promotion Manager) "
                    "is available through the public support URL below.\n\n"
                ),
            },
        }
        for path, expected in english_legal_expectations.items():
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(expected["prefix"]), f"{path} has the wrong opening block")
            self.assertEqual(
                text.count(english_identity),
                1,
                f"{path} must contain the full identity exactly once",
            )
            self.assertEqual(
                text.count("ENHE Promotion Manager"),
                1,
                f"{path} must contain the old product name exactly once",
            )

        chinese_privacy_path = DOCS / "legal/privacy-policy.zh-CN.md"
        chinese_privacy = chinese_privacy_path.read_text(encoding="utf-8")
        chinese_identity = "ENHE 产品推广素材生成器（原 ENHE Promotion Manager）"
        chinese_prefix = (
            "# ENHE 产品推广素材生成器隐私政策\n\n"
            "生效日期：2026-07-15\n\n"
            "本政策说明 ENHE AI 如何处理 ENHE 产品推广素材生成器（原 ENHE Promotion Manager）"
            "浏览器扩展程序及其可选托管服务中的信息。\n\n"
        )
        self.assertTrue(
            chinese_privacy.startswith(chinese_prefix),
            f"{chinese_privacy_path} has the wrong opening block",
        )
        self.assertEqual(
            chinese_privacy.count(chinese_identity),
            1,
            f"{chinese_privacy_path} must contain the full identity exactly once",
        )
        self.assertEqual(
            chinese_privacy.count("（原 ENHE Promotion Manager）"),
            1,
            f"{chinese_privacy_path} must contain the transition alias exactly once",
        )
        self.assertEqual(
            chinese_privacy.count("ENHE Promotion Manager"),
            1,
            f"{chinese_privacy_path} must contain the old product name exactly once",
        )

    def test_manual_publish_package_strategy_is_documented_across_skill_usage_and_capability_map(self) -> None:
        files = [
            ROOT / "SKILL.md",
            DOCS / "usage.md",
            DOCS / "final-capability-map.md",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("manual publish packages are the primary path", text)
            self.assertIn("auto-publish ports are reserved", text)
            self.assertIn("official API-only", text)
        capability_map = (DOCS / "final-capability-map.md").read_text(encoding="utf-8")
        self.assertIn("Generate publish packages first; keep auto-publish ports reserved", capability_map)

    def test_final_readiness_publish_row_uses_manual_package_first_strategy(self) -> None:
        module = load_script_module(FINAL_CAPABILITY_READINESS)
        row = module.publish_row(
            {},
            {},
            [
                {
                    "records": [
                        {"platform": "github", "readiness": "dry_run_ready"},
                        {"platform": "xiaohongshu", "readiness": "manual_publish_required"},
                    ]
                }
            ],
            [],
        )

        self.assertEqual(row["id"], "official_or_browser_assisted_publish")
        self.assertEqual(row["status"], "manual_package_ready_auto_ports_reserved")
        self.assertIn("manual publish packages", row["label"])
        self.assertTrue(row["metrics"]["autoPublishPortsReserved"])
        self.assertEqual(row["metrics"]["manualOrBrowserRequired"], 1)

    def test_billing_contract_simulator_runs_license_usage_and_webhook_flow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="billing-simulator-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        secret_license = "pm_demo_secret_license_for_test"
        subprocess.run(
            [
                sys.executable,
                str(BILLING_CONTRACT_SIMULATOR),
                "demo",
                "--license-key",
                secret_license,
                "--plan",
                "growth",
                "--workflow-type",
                "research_run",
                "--out-dir",
                str(out_dir),
                "--reset-state",
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/billing-simulator/billing-simulator.json"
        state_path = out_dir / "reports/promotion-manager/billing-simulator/billing-simulator-state.json"
        report_text = report_path.read_text(encoding="utf-8")
        state_text = state_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_license, report_text)
        self.assertNotIn(secret_license, state_text)
        report = json.loads(report_text)
        state = json.loads(state_text)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["contract"]["status"], "ready")
        self.assertFalse(report["secretStored"])
        self.assertEqual(report["response"]["usageAuthorization"]["allowed"], True)
        self.assertEqual(report["response"]["usageCommit"]["status"], "succeeded")
        self.assertEqual(report["response"]["webhook"]["event"], "invoice.payment_succeeded")
        self.assertEqual(report["summary"]["licenses"], 1)
        self.assertEqual(report["summary"]["committedUsageRecords"], 1)
        self.assertEqual(report["summary"]["webhookEvents"], 1)
        license_record = next(iter(state["licenses"].values()))
        self.assertIn("licenseKeyHash", license_record)
        self.assertNotIn("licenseKey", license_record)
        usage_record = next(iter(state["usageLedger"].values()))
        self.assertEqual(usage_record["workflowType"], "research_run")
        self.assertEqual(usage_record["creditsReserved"], 3)
        self.assertEqual(usage_record["creditsUsed"], 3)

    def test_billing_contract_simulator_accepts_automation_due_run(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="billing-automation-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(BILLING_CONTRACT_SIMULATOR),
                "demo",
                "--plan",
                "growth",
                "--workflow-type",
                "automation_due_run",
                "--out-dir",
                str(out_dir),
                "--reset-state",
            ],
            check=True,
            cwd=ROOT,
        )
        state_path = out_dir / "reports/promotion-manager/billing-simulator/billing-simulator-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        usage_record = next(iter(state["usageLedger"].values()))
        self.assertEqual(usage_record["workflowType"], "automation_due_run")
        self.assertEqual(usage_record["creditsReserved"], 4)

    def test_billing_contract_simulator_runs_hosted_run_flow(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="billing-hosted-run-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        secret_license = "pm_demo_hosted_run_secret_for_test"
        subprocess.run(
            [
                sys.executable,
                str(BILLING_CONTRACT_SIMULATOR),
                "demo-hosted-run",
                "--license-key",
                secret_license,
                "--plan",
                "growth",
                "--workflow-type",
                "standard_run",
                "--product-url",
                "https://example.com/product",
                "--local-command",
                'python scripts\\skill_entry.py --link "https://example.com/product"',
                "--out-dir",
                str(out_dir),
                "--reset-state",
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/billing-simulator/billing-simulator.json"
        state_path = out_dir / "reports/promotion-manager/billing-simulator/billing-simulator-state.json"
        report_text = report_path.read_text(encoding="utf-8")
        state_text = state_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_license, report_text)
        self.assertNotIn(secret_license, state_text)
        report = json.loads(report_text)
        state = json.loads(state_text)
        self.assertEqual(report["status"], "ready")
        self.assertTrue(report["response"]["hostedRun"]["accepted"])
        self.assertEqual(report["response"]["hostedRun"]["status"], "queued")
        self.assertEqual(report["response"]["usageCommit"]["status"], "succeeded")
        self.assertEqual(report["summary"]["hostedRuns"], 1)
        self.assertEqual(report["summary"]["completedHostedRuns"], 1)
        hosted_run = next(iter(state["hostedRuns"].values()))
        usage_record = state["usageLedger"][hosted_run["usageId"]]
        self.assertEqual(hosted_run["workflowType"], "standard_run")
        self.assertEqual(hosted_run["status"], "succeeded")
        self.assertEqual(usage_record["creditsReserved"], 4)
        self.assertEqual(usage_record["creditsUsed"], 4)

    def test_billing_contract_simulator_blocks_hosted_run_without_matching_reservation(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="billing-hosted-run-blocked-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        secret_license = "pm_demo_hosted_run_blocked_secret"
        subprocess.run(
            [
                sys.executable,
                str(BILLING_CONTRACT_SIMULATOR),
                "issue-license",
                "--license-key",
                secret_license,
                "--plan",
                "growth",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        authorization = subprocess.run(
            [
                sys.executable,
                str(BILLING_CONTRACT_SIMULATOR),
                "authorize-usage",
                "--license-key",
                secret_license,
                "--workflow-type",
                "research_run",
                "--idempotency-key",
                "blocked-hosted-run-test",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        usage_id = json.loads(authorization.stdout)["usage"]["usageId"]
        hosted = subprocess.run(
            [
                sys.executable,
                str(BILLING_CONTRACT_SIMULATOR),
                "hosted-run",
                "--license-key",
                secret_license,
                "--usage-id",
                usage_id,
                "--workflow-type",
                "standard_run",
                "--product-url",
                "https://example.com/product",
                "--platforms",
                "youtube",
                "--local-command",
                'python scripts\\skill_entry.py --link "https://example.com/product"',
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        response = json.loads(hosted.stdout)
        self.assertFalse(response["hostedRun"]["accepted"])
        self.assertEqual(response["hostedRun"]["reason"], "usage_workflow_mismatch")

    def test_self_evolution_managed_files_include_docs_and_browser_extension(self) -> None:
        module = load_script_module(SELF_EVOLUTION_AUDIT)
        files = {item.as_posix() for item in module.managed_skill_files(ROOT)}
        self.assertIn("README.md", files)
        self.assertIn("README.en.md", files)
        self.assertIn("README.zh-CN.md", files)
        self.assertIn("requirements-youtube.txt", files)
        self.assertIn("docs/installation.md", files)
        self.assertIn("docs/zh-CN/installation.md", files)
        self.assertIn("docs/zh-CN/usage.md", files)
        self.assertIn("docs/subscription-pricing.md", files)
        self.assertIn("docs/billing-backend-contract.md", files)
        self.assertIn("docs/legal/privacy-policy.md", files)
        self.assertIn("docs/legal/terms-of-service.md", files)
        self.assertIn("docs/legal/refund-policy.md", files)
        self.assertIn("docs/legal/support.md", files)
        self.assertIn("docs/store/chrome-listing.md", files)
        self.assertIn("docs/store/edge-listing.md", files)
        self.assertIn("docs/store/reviewer-notes.md", files)
        self.assertIn("docs/store/screenshot-plan.md", files)
        self.assertIn("deploy/promotion-manager/README.md", files)
        self.assertIn("deploy/promotion-manager/.env.production.example", files)
        self.assertIn("deploy/promotion-manager/nginx-promotion-manager.conf", files)
        self.assertIn("deploy/promotion-manager/enhe-promotion-manager-api.service", files)
        self.assertIn("deploy/promotion-manager/enhe-promotion-manager-worker.service", files)
        self.assertIn("browser-extension/manifest.json", files)
        self.assertIn("browser-extension/billing-contract.json", files)
        self.assertIn("browser-extension/popup.html", files)
        self.assertIn("browser-extension/popup.css", files)
        self.assertIn("browser-extension/popup.js", files)
        self.assertIn("browser-extension/icons/icon128.png", files)
        self.assertIn("scripts/fixtures/mediacrawler/xiaohongshu-contents.jsonl", files)
        self.assertIn("scripts/fixtures/mediacrawler/xiaohongshu-comments.jsonl", files)
        self.assertIn("scripts/fixtures/mediacrawler/douyin-contents.jsonl", files)
        self.assertIn("scripts/fixtures/mediacrawler/douyin-comments.jsonl", files)
        self.assertIn("scripts/fixtures/mediacrawler/zhihu-contents.jsonl", files)
        self.assertIn("scripts/fixtures/mediacrawler/zhihu-comments.jsonl", files)
        self.assertIn("backend/license-service/package.json", files)
        self.assertIn("backend/license-service/package-lock.json", files)
        self.assertIn("backend/license-service/.env.example", files)
        self.assertIn("backend/license-service/src/server.js", files)
        self.assertIn("backend/license-service/src/state-store.js", files)
        self.assertIn("backend/license-service/src/hosted-worker.js", files)
        self.assertIn("backend/license-service/src/migrate.js", files)
        self.assertIn("backend/license-service/src/worker.js", files)
        self.assertIn("backend/license-service/migrations/001_state_store.sql", files)
        self.assertIn("backend/license-service/README.md", files)
        self.assertFalse(any("/node_modules/" in item for item in files))
        self.assertFalse(any("/var/" in item for item in files))
        self.assertIn("scripts/billing_contract_simulator.py", files)
        self.assertIn("scripts/package_browser_extension.py", files)
        self.assertIn("scripts/launch_unlock_pack.py", files)

        with tempfile.TemporaryDirectory(prefix="managed-skill-files-test-") as temp_dir:
            fixture_root = Path(temp_dir)
            scripts_dir = fixture_root / "scripts"
            fixture_dir = scripts_dir / "fixtures" / "mediacrawler"
            fixture_dir.mkdir(parents=True)
            (scripts_dir / "helper.py").write_text("pass\n", encoding="utf-8")
            (scripts_dir / "unrelated-output.jsonl").write_text('{"private": true}\n', encoding="utf-8")
            fixture_names = [
                "xiaohongshu-contents.jsonl",
                "xiaohongshu-comments.jsonl",
                "douyin-contents.jsonl",
                "douyin-comments.jsonl",
                "zhihu-contents.jsonl",
                "zhihu-comments.jsonl",
            ]
            for name in fixture_names:
                (fixture_dir / name).write_text("{}\n", encoding="utf-8")

            modeled_files = {item.as_posix() for item in module.managed_skill_files(fixture_root)}

        self.assertIn("scripts/helper.py", modeled_files)
        self.assertNotIn("scripts/unrelated-output.jsonl", modeled_files)
        for name in fixture_names:
            self.assertIn(f"scripts/fixtures/mediacrawler/{name}", modeled_files)

    def test_self_evolution_audit_reports_tool_and_skill_state_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="self-evolution-audit-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env = os.environ.copy()
        secret_value = "super-secret-self-evolution-token"
        env["GITHUB_TOKEN"] = secret_value
        subprocess.run(
            [
                sys.executable,
                str(SELF_EVOLUTION_AUDIT),
                "--skip-runtime-checks",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertIn(
            report["status"],
            {
                "ready_controlled_autonomy",
                "partial_ready_skill_drift_detected",
                "partial_ready_installed_skill_missing",
                "partial_ready_runtime_gaps",
            },
        )
        self.assertEqual(report["selfUpgradePolicy"]["mode"], "controlled_autonomy")
        self.assertIn("installedSkill", report)
        self.assertIn("repository", report)
        self.assertTrue(any(item["id"] == "playwright_chromium" for item in report["safeInstallCandidates"]))
        self.assertEqual(report["platformLearning"]["status"], "missing_platform_access_audit")
        self.assertIn("reviewRequiredUpgradeRequests", report)
        self.assertIn("reviewQueueSummary", report)
        self.assertTrue(
            any(item["id"] == "refresh_platform_access_learning" for item in report["reviewRequiredUpgradeRequests"])
        )
        self.assertGreaterEqual(report["reviewQueueSummary"]["total"], 1)
        self.assertGreaterEqual(report["reviewQueueSummary"]["agentExecutableNow"], 1)
        self.assertTrue(any(item["area"] == "learning_loop" for item in report["nextActions"]))
        self.assertEqual(report["syncInstalledSkill"]["status"], "not_requested")
        self.assertTrue((out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.md").exists())

    def test_final_capability_audit_reports_real_limits_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-capability-audit-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env = os.environ.copy()
        secret_value = "super-secret-token-for-test"
        for name in [
            "YOUTUBE_API_KEY",
            "YOUTUBE_ACCESS_TOKEN",
            "YOUTUBE_OAUTH_ACCESS_TOKEN",
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "DOUYIN_CLIENT_KEY",
            "DOUYIN_CLIENT_SECRET",
            "DOUYIN_ACCESS_TOKEN",
            "DOUYIN_OPEN_ID",
            "TIKTOK_CLIENT_KEY",
            "TIKTOK_CLIENT_SECRET",
            "TIKTOK_ACCESS_TOKEN",
            "TIKTOK_OPEN_ID",
        ]:
            env.pop(name, None)
        env["GITHUB_TOKEN"] = secret_value
        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_AUDIT),
                "--skip-runtime-checks",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/capability/final-capability-audit.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["credentials"]["github_write"]["presentEnv"], ["GITHUB_TOKEN"])
        self.assertFalse(report["credentials"]["github_write"]["valuesStored"])
        by_requirement = {item["id"]: item for item in report["requirements"]}
        self.assertIn(by_requirement["product_url_structured_intake"]["status"], {"ready", "partial_ready"})
        self.assertEqual(by_requirement["viral_creator_content_research"]["status"], "partial_ready")
        self.assertIn(by_requirement["copy_and_real_video_generation"]["status"], {"ready", "partial_ready"})
        self.assertEqual(
            by_requirement["all_platform_auto_publish"]["status"],
            "blocked_by_authorization_or_platform_limits",
        )
        self.assertIn(
            by_requirement["fully_autonomous_self_evolution"]["status"],
            {"ready_review_gated_autonomy", "partial_ready_review_gated_autonomy"},
        )
        self.assertEqual(by_requirement["github_documentation_and_install_tutorial"]["status"], "ready")
        extension_requirement = by_requirement["browser_extension_operator_ui_subscription"]
        self.assertEqual(extension_requirement["status"], "partial_ready")
        self.assertIn(
            "browser-extension/popup.js declares HOSTED_WORKER_ENABLED = false; hosted usage reservation and run submission are disabled",
            extension_requirement["missing"],
        )
        self.assertTrue(
            any("Local Skill runs remain available" in limit for limit in extension_requirement["limits"])
        )
        self.assertFalse(
            any(
                "reserve hosted usage credits, start hosted runs" in limit
                for limit in extension_requirement["limits"]
            )
        )
        self.assertEqual(by_requirement["completion_roadmap_to_100_percent"]["status"], "ready")
        self.assertEqual(by_requirement["zh_cn_operator_action_checklist_to_100_percent"]["status"], "ready")
        self.assertEqual(by_requirement["phase_progress_reporting"]["status"], "ready")
        self.assertEqual(by_requirement["retrospective_next_round_optimization"]["status"], "ready")
        self.assertTrue(
            any("browser_video_sampler.py" in path for path in by_requirement["viral_creator_content_research"]["evidence"])
        )
        self.assertEqual(report["platforms"]["xiaohongshu"]["directPublish"], "manual_or_browser_assisted_only")
        self.assertEqual(report["platforms"]["douyin"]["directPublish"], "browser_assisted_publish_selected")
        self.assertTrue(any(item["purpose"] == "one_command_cycle" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "build_real_run_playbook" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "capture_browser_visible_video_evidence" for item in report["recommendedCommands"]))
        self.assertTrue(report["platformAccessAudit"]["ready"])
        self.assertTrue(any(item["purpose"] == "audit_platform_official_access" for item in report["recommendedCommands"]))
        self.assertTrue(report["selfEvolutionAudit"]["ready"])
        self.assertTrue(report["selfEvolutionAudit"]["reportExists"])
        self.assertTrue(report["scripts"]["publish_setup_assistant"]["exists"])
        self.assertTrue(report["scripts"]["browser_publish_assistant"]["exists"])
        self.assertTrue(report["scripts"]["browser_publish_form_fill"]["exists"])
        self.assertTrue(report["scripts"]["browser_publish_session"]["exists"])
        self.assertTrue(report["scripts"]["post_publish_metrics_capture"]["exists"])
        self.assertTrue(report["scripts"]["comment_evidence_capture"]["exists"])
        self.assertTrue(report["scripts"]["business_attribution"]["exists"])
        self.assertTrue(report["scripts"]["real_evidence_inbox_setup"]["exists"])
        self.assertTrue(report["scripts"]["real_evidence_inbox"]["exists"])
        self.assertTrue(report["scripts"]["performance_monitor"]["exists"])
        self.assertTrue(report["scripts"]["next_round_optimizer"]["exists"])
        self.assertTrue(report["scripts"]["multi_query_viral_discovery"]["exists"])
        self.assertTrue(report["scripts"]["viral_evidence_inbox_setup"]["exists"])
        self.assertTrue(report["scripts"]["viral_evidence_inbox"]["exists"])
        self.assertTrue(report["scripts"]["product_batch_runner"]["exists"])
        self.assertTrue(report["scripts"]["real_run_playbook"]["exists"])
        self.assertTrue(report["scripts"]["skill_entry"]["exists"])
        self.assertTrue(report["scripts"]["final_capability_audit"]["exists"])
        self.assertTrue(report["scripts"]["final_capability_runner"]["exists"])
        self.assertTrue(report["scripts"]["final_capability_readiness"]["exists"])
        self.assertTrue(report["scripts"]["self_evolution_audit"]["exists"])
        self.assertTrue(report["scripts"]["completion_roadmap"]["exists"])
        self.assertTrue(report["scripts"]["operator_action_checklist"]["exists"])
        viral_evidence = "\n".join(by_requirement["viral_creator_content_research"]["evidence"])
        self.assertIn("multi_query_viral_discovery.py", viral_evidence)
        self.assertIn("viral_evidence_inbox_setup.py", viral_evidence)
        self.assertIn("viral_evidence_inbox.py", viral_evidence)
        publish_evidence = "\n".join(by_requirement["all_platform_auto_publish"]["evidence"])
        self.assertIn("publish_setup_assistant.py", publish_evidence)
        self.assertIn("browser_publish_form_fill.py", publish_evidence)
        self.assertIn("browser_publish_session.py", publish_evidence)
        metrics_evidence = "\n".join(by_requirement["real_metrics_orders_revenue_recovery"]["evidence"])
        self.assertIn("business_attribution.py", metrics_evidence)
        self.assertIn("real_evidence_inbox_setup.py", metrics_evidence)
        self.assertIn("real_evidence_inbox.py", metrics_evidence)
        self.assertIn("performance_monitor.py", metrics_evidence)
        optimization_evidence = "\n".join(by_requirement["retrospective_next_round_optimization"]["evidence"])
        self.assertIn("next_round_optimizer.py", optimization_evidence)
        self.assertIn("performance_monitor.py", optimization_evidence)
        docs_evidence = "\n".join(by_requirement["github_documentation_and_install_tutorial"]["evidence"]).replace("\\", "/")
        self.assertIn("README.md", docs_evidence)
        self.assertIn("README.en.md", docs_evidence)
        self.assertIn("docs/100-percent-completion-roadmap.md", docs_evidence)
        self.assertIn("docs/zh-CN/100-percent-completion-guide.md", docs_evidence)
        roadmap_evidence = "\n".join(by_requirement["completion_roadmap_to_100_percent"]["evidence"]).replace("\\", "/")
        self.assertIn("scripts/completion_roadmap.py", roadmap_evidence)
        self.assertIn("docs/100-percent-completion-roadmap.md", roadmap_evidence)
        checklist_evidence = "\n".join(by_requirement["zh_cn_operator_action_checklist_to_100_percent"]["evidence"]).replace("\\", "/")
        self.assertIn("scripts/operator_action_checklist.py", checklist_evidence)
        self.assertIn("docs/zh-CN/100-percent-completion-guide.md", checklist_evidence)
        self.assertIn("README.zh-CN.md", docs_evidence)
        self.assertIn("docs/installation.md", docs_evidence)
        self.assertIn("docs/zh-CN/installation.md", docs_evidence)
        self.assertIn("docs/zh-CN/usage.md", docs_evidence)
        extension_evidence = "\n".join(by_requirement["browser_extension_operator_ui_subscription"]["evidence"]).replace("\\", "/")
        self.assertIn("browser-extension/manifest.json", extension_evidence)
        self.assertIn("browser-extension/popup.js", extension_evidence)
        self.assertIn("scripts/billing_contract_simulator.py", extension_evidence)
        phase_evidence = "\n".join(by_requirement["phase_progress_reporting"]["evidence"]).replace("\\", "/")
        self.assertIn("scripts/final_capability_readiness.py", phase_evidence)
        self.assertIn("scripts/real_run_playbook.py", phase_evidence)
        self.assertTrue(report["scripts"]["billing_contract_simulator"]["exists"])
        self.assertTrue(any(item["purpose"] == "audit_self_evolution" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "build_zh_cn_operator_action_checklist" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "prepare_browser_assisted_publish" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "run_browser_publish_session" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "build_publish_setup_kit" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "multi_query_viral_discovery" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "setup_viral_evidence_inbox" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "import_viral_evidence_inbox" for item in report["recommendedCommands"]))
        self.assertTrue(
            any(
                item["purpose"] == "batch_product_url_cycles_with_multi_query_viral_discovery"
                for item in report["recommendedCommands"]
            )
        )
        self.assertTrue(
            any(
                item["purpose"] == "batch_product_url_closed_loop_with_next_round_optimization"
                for item in report["recommendedCommands"]
            )
        )
        self.assertTrue(any(item["purpose"] == "final_capability_runner" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "one_link_skill_entry" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "build_final_readiness_matrix" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "review_github_docs" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "load_browser_extension" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "billing_contract_simulator_demo" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "monitor_post_publish_performance" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "capture_public_post_publish_metrics" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "setup_real_evidence_inbox" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "import_real_evidence_inbox" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "capture_public_comment_evidence" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "attribute_business_results" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "optimize_next_round_from_recovered_evidence" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "audit_platform_official_access_with_live_docs" for item in report["recommendedCommands"]))
        self.assertTrue(any(item["purpose"] == "sync_installed_skill_when_approved" for item in report["recommendedCommands"]))
        self.assertIn("reviewQueueSummary", report["selfEvolution"])
        self.assertIn("reviewRequiredUpgradeRequests", report["selfEvolution"])
        self.assertTrue(report["selfEvolution"]["safeSkillSync"])
        self.assertTrue((out_dir / "reports/promotion-manager/self-evolution/self-evolution-audit.md").exists())
        self.assertTrue((out_dir / "reports/promotion-manager/capability/final-capability-audit.md").exists())

    def test_final_capability_audit_loads_env_file_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-capability-audit-env-file-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env_file = out_dir / ".env"
        secret_value = "google-client-secret-test"
        env_file.write_text(
            "\n".join(
                [
                    "GOOGLE_OAUTH_CLIENT_ID=client-id-test.apps.googleusercontent.com",
                    f"GOOGLE_OAUTH_CLIENT_SECRET={secret_value}",
                    "YOUTUBE_API_KEY=youtube-api-key-test",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        for name in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "YOUTUBE_API_KEY"]:
            env.pop(name, None)
        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_AUDIT),
                "--env-file",
                str(env_file),
                "--skip-runtime-checks",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_text = (out_dir / "reports/promotion-manager/capability/final-capability-audit.json").read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertTrue(report["credentials"]["youtube_oauth_flow"]["ready"])
        self.assertTrue(report["credentials"]["youtube_search_metrics"]["ready"])
        self.assertIn("GOOGLE_OAUTH_CLIENT_SECRET", report["envLoad"]["loadedKeys"])
        self.assertNotIn(secret_value, report_text)

    def test_final_capability_audit_accepts_youtube_client_aliases(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-capability-audit-youtube-alias-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env_file = out_dir / ".env"
        secret_value = "youtube-client-secret-test"
        env_file.write_text(
            "\n".join(
                [
                    "YOUTUBE_CLIENT_ID=client-id-test.apps.googleusercontent.com",
                    f"YOUTUBE_CLIENT_SECRET={secret_value}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        for name in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"]:
            env.pop(name, None)
        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_AUDIT),
                "--env-file",
                str(env_file),
                "--skip-runtime-checks",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_text = (out_dir / "reports/promotion-manager/capability/final-capability-audit.json").read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertTrue(report["credentials"]["youtube_oauth_flow"]["ready"])
        self.assertIn("YOUTUBE_CLIENT_SECRET", report["envLoad"]["loadedKeys"])
        self.assertEqual(report["credentials"]["youtube_oauth_flow"]["blankEnv"], [])
        self.assertNotIn(secret_value, report_text)

    def test_final_capability_readiness_builds_requirement_matrix_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-readiness-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        secret_value = "fake-final-readiness-secret"
        final_run_dir = out_dir / "reports/promotion-manager/final-run"
        final_run_dir.mkdir(parents=True)
        (final_run_dir / "final-capability-run.json").write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-08",
                    "status": "partial_ready",
                    "input": {"codexReadFirst": True},
                    "summary": {
                        "promotionRuns": 1,
                        "multiQueryDiscoveryRuns": 1,
                        "multiQuerySearchCapturesReady": 2,
                        "multiQueryViralMaterialsObserved": 4,
                        "multiQueryMergedMaterials": 3,
                        "multiQueryMergedCreators": 2,
                        "multiQueryDeepEvidenceRuns": 1,
                        "multiQueryFollowUpCaptureRuns": 1,
                        "multiQueryFollowUpImportedRecords": 1,
                        "multiQueryBrowserVisibleCaptureReady": 1,
                        "multiQueryVideoSampleRuns": 1,
                        "multiQueryVideoSampleReady": 1,
                        "multiQueryVideoSampleFrames": 2,
                        "contentArtifacts": 1,
                        "videoFilesGenerated": 0,
                        "capturedMetricRecords": 0,
                        "commentCount": 0,
                        "matchedBusinessRows": 0,
                        "recordsWithMetrics": 0,
                        "nextRoundContent": 0,
                    },
                    "productBatch": {"report": str(out_dir / "reports/promotion-manager/batch/product-batch-runner.json")},
                    "debug": secret_value,
                }
            ),
            encoding="utf-8",
        )
        capability_dir = out_dir / "reports/promotion-manager/capability"
        capability_dir.mkdir(parents=True)
        (capability_dir / "final-capability-audit.json").write_text(
            json.dumps(
                {
                    "finalStatus": "partial_ready_blocked_by_platform_or_safety_limits",
                    "requirements": [
                        {
                            "id": "product_url_structured_intake",
                            "status": "ready",
                            "evidence": ["scripts/product_url_reader.py"],
                            "missing": [],
                        },
                        {
                            "id": "viral_creator_content_research",
                            "status": "partial_ready",
                            "evidence": ["scripts/multi_query_viral_discovery.py"],
                            "missing": [],
                            "limits": ["browser-visible evidence only for some platforms"],
                        },
                        {
                            "id": "copy_and_real_video_generation",
                            "status": "ready",
                            "evidence": ["scripts/render_video.py"],
                            "missing": [],
                        },
                        {
                            "id": "all_platform_auto_publish",
                            "status": "blocked_by_authorization_or_platform_limits",
                            "evidence": ["scripts/publish_readiness_runner.py"],
                            "missing": ["GITHUB_TOKEN or GH_TOKEN for GitHub writes"],
                            "limits": ["platform authorization required"],
                        },
                        {
                            "id": "real_metrics_orders_revenue_recovery",
                            "status": "partial_ready",
                            "evidence": ["scripts/metrics_recovery.py"],
                            "missing": ["published URLs or business exports"],
                        },
                        {
                            "id": "retrospective_next_round_optimization",
                            "status": "ready",
                            "evidence": ["scripts/next_round_optimizer.py"],
                            "missing": [],
                        },
                        {
                            "id": "fully_autonomous_self_evolution",
                            "status": "ready_review_gated_autonomy",
                            "evidence": ["scripts/self_evolution_audit.py"],
                            "missing": ["explicit review/approval"],
                        },
                        {
                            "id": "github_documentation_and_install_tutorial",
                            "status": "ready",
                            "evidence": ["README.md", "docs/installation.md"],
                            "missing": [],
                        },
                        {
                            "id": "browser_extension_operator_ui_subscription",
                            "status": "ready",
                            "evidence": ["browser-extension/manifest.json", "browser-extension/popup.js"],
                            "missing": [],
                        },
                    ],
                    "platforms": {
                        "youtube": {"viralSearch": "ready", "directPublish": "needs_oauth_or_access_token"},
                        "xiaohongshu": {"viralSearch": "browser_visible_ready", "directPublish": "manual_or_browser_assisted_only"},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self_dir = out_dir / "reports/promotion-manager/self-evolution"
        self_dir.mkdir(parents=True)
        (self_dir / "self-evolution-audit.json").write_text(
            json.dumps(
                {
                    "status": "partial_ready_skill_drift_detected",
                    "repository": {"clean": True},
                    "installedSkill": {
                        "status": "drift_detected",
                        "syncCommand": "python scripts/self_evolution_audit.py --sync-installed-skill --approval I_APPROVE_SKILL_SYNC",
                    },
                    "reviewQueueSummary": {
                        "total": 2,
                        "agentExecutableNow": 1,
                        "requiresApprovalOrManualReview": 1,
                    },
                }
            ),
            encoding="utf-8",
        )
        platform_access_dir = out_dir / "reports/promotion-manager/platform-access"
        platform_access_dir.mkdir(parents=True)
        (platform_access_dir / "platform-access-audit.json").write_text(
            json.dumps(
                {
                    "checkLive": False,
                    "learningFreshness": {
                        "status": "stale_not_live_checked",
                        "checkLive": False,
                        "reachableDocs": 0,
                        "missingDocCapabilities": 2,
                        "refreshCommand": "python scripts/platform_access_audit.py --check-live --out-dir \"./promotion-output\"",
                    },
                    "officialDocSummary": {"reachableDocs": 0, "missingDocCapabilities": 2},
                    "officialDocGapResearch": {
                        "status": "unresolved_missing_official_docs",
                        "summary": {
                            "records": 2,
                            "missingOfficialDocCapabilities": 2,
                            "manualOrBrowserFallbacks": 2,
                            "officialAppOrExecutorGaps": 0,
                        },
                        "records": [
                            {
                                "platform": "zhihu",
                                "area": "publish",
                                "safeFallback": "manual_or_browser_assisted_publish",
                                "finding": "No verified official public creator article publishing endpoint is configured.",
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        readiness_dir = out_dir / "product-batch-runs/ai-prompt-kit/reports/promotion-manager/publish-readiness"
        readiness_dir.mkdir(parents=True)
        (readiness_dir / "publish-readiness.json").write_text(
            json.dumps(
                {
                    "records": [
                        {"platform": "youtube", "publishMode": "official_api_publish", "readiness": "missing_credentials"},
                        {"platform": "xiaohongshu", "publishMode": "manual_publish_required", "readiness": "manual_publish_required"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        setup_dir = out_dir / "product-batch-runs/ai-prompt-kit/reports/promotion-manager/publish-setup"
        setup_dir.mkdir(parents=True)
        (setup_dir / "publish-setup.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "youtube",
                            "setupCategory": "credential_setup_required",
                            "commands": {"rerunReadiness": "python scripts/publish_readiness_runner.py --platforms youtube"},
                        },
                        {
                            "platform": "xiaohongshu",
                            "setupCategory": "browser_or_manual_publish",
                            "commands": {"prepareBrowserPublish": "python scripts/browser_publish_assistant.py --platforms xiaohongshu"},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [sys.executable, str(FINAL_CAPABILITY_READINESS), "--out-dir", str(out_dir)],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "partial_ready_waiting_external_evidence")
        by_requirement = {item["id"]: item for item in report["requirements"]}
        self.assertEqual(by_requirement["product_url_codex_structured_intake"]["status"], "ready")
        self.assertEqual(by_requirement["viral_creator_video_research"]["status"], "ready_with_video_evidence")
        self.assertTrue(by_requirement["viral_creator_video_research"]["satisfied"])
        self.assertEqual(by_requirement["viral_creator_video_research"]["metrics"]["videoSampleFrames"], 2)
        self.assertEqual(by_requirement["copy_and_real_video_generation"]["status"], "partial_ready")
        self.assertEqual(by_requirement["real_metrics_comments_orders_revenue"]["status"], "waiting_real_data")
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["installedSkillStatus"], "drift_detected")
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["platformLearningStatus"], "stale_not_live_checked")
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["officialDocGapResearchStatus"], "unresolved_missing_official_docs")
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["officialDocGapResearchRecords"], 2)
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["officialDocGapResearchMissingCapabilities"], 2)
        self.assertEqual(by_requirement["controlled_self_evolution"]["status"], "partial_ready_review_gated_autonomy")
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["reviewQueueTotal"], 2)
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["reviewQueueAgentExecutableNow"], 1)
        self.assertEqual(by_requirement["controlled_self_evolution"]["metrics"]["reviewQueueRequiresApprovalOrManualReview"], 1)
        self.assertEqual(by_requirement["github_documentation_and_install_tutorial"]["status"], "ready")
        self.assertEqual(by_requirement["browser_extension_operator_ui_subscription"]["status"], "ready")
        self.assertEqual(by_requirement["phase_progress_reporting"]["status"], "ready")
        self.assertIn(
            "official platform doc gap research still has unresolved missing capabilities",
            by_requirement["controlled_self_evolution"]["missing"],
        )
        self.assertTrue(any(item["id"] == "sync_installed_skill_when_approved" for item in report["actionQueue"]))
        self.assertTrue(any(item["id"] == "refresh_platform_access_docs" for item in report["actionQueue"]))
        self.assertTrue(any(item["id"] == "monitor_post_publish_performance" for item in report["actionQueue"]))
        self.assertTrue(any(item["id"] == "setup_real_evidence_inbox" for item in report["actionQueue"]))
        self.assertTrue(any(item["id"] == "import_real_evidence_inbox" for item in report["actionQueue"]))
        self.assertTrue(any(item["id"] == "run_xiaohongshu_browser_publish_session" for item in report["actionQueue"]))
        self.assertEqual(report["platformMatrix"]["xiaohongshu"]["publishReadiness"], "manual_publish_required")
        self.assertTrue((out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.md").exists())

    def test_final_readiness_accepts_non_critical_platform_learning_warnings(self) -> None:
        module = load_script_module(FINAL_CAPABILITY_READINESS)
        row = module.self_evolution_row(
            {
                "repository": {"clean": True},
                "installedSkill": {
                    "status": "synced",
                    "syncCommand": "python scripts/self_evolution_audit.py --sync-installed-skill --approval I_APPROVE_SKILL_SYNC",
                },
                "reviewQueueSummary": {
                    "total": 0,
                    "agentExecutableNow": 0,
                    "requiresApprovalOrManualReview": 0,
                },
            },
            {
                "requirements": [
                    {
                        "id": "fully_autonomous_self_evolution",
                        "status": "ready_review_gated_autonomy",
                        "evidence": ["scripts/self_evolution_audit.py"],
                        "missing": [],
                        "limits": [],
                    }
                ]
            },
            {
                "checkLive": True,
                "learningFreshness": {
                    "status": "fresh_live_checked_with_warnings",
                    "checkLive": True,
                    "reachableDocs": 14,
                    "missingDocCapabilities": 0,
                    "failedDocs": 4,
                    "criticalFailedDocs": 0,
                    "fallbackFailedDocs": 4,
                    "warning": "Some fallback docs were unreachable.",
                },
                "officialDocSummary": {
                    "reachableDocs": 14,
                    "missingDocCapabilities": 0,
                    "criticalFailedDocs": 0,
                    "fallbackFailedDocs": 4,
                },
                "officialDocGapResearch": {
                    "status": "manual_or_evidence_fallbacks_documented",
                    "summary": {
                        "records": 4,
                        "missingOfficialDocCapabilities": 0,
                        "manualOrBrowserFallbacks": 4,
                        "officialAppOrExecutorGaps": 0,
                    },
                },
            },
        )

        self.assertEqual(row["status"], "ready_review_gated_autonomy")
        self.assertEqual(row["missing"], [])
        self.assertEqual(row["metrics"]["platformLearningStatus"], "fresh_live_checked_with_warnings")
        self.assertEqual(row["metrics"]["platformLearningCriticalFailedDocs"], 0)
        self.assertEqual(row["metrics"]["platformLearningFallbackFailedDocs"], 4)

    def test_final_capability_readiness_surfaces_synthetic_validation_without_satisfying_real_data(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-readiness-synthetic-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        final_run_dir = out_dir / "reports/promotion-manager/final-run"
        final_run_dir.mkdir(parents=True)
        (final_run_dir / "final-capability-run.json").write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-10",
                    "status": "partial_ready",
                    "input": {
                        "codexReadFirst": True,
                        "platforms": "youtube,github",
                        "urls": ["https://www.enhe-tech.com.cn/software/windows-ai"],
                    },
                    "summary": {
                        "promotionRuns": 1,
                        "contentArtifacts": 1,
                        "videoFilesGenerated": 1,
                        "capturedMetricRecords": 0,
                        "recordsWithMetrics": 0,
                        "commentCount": 0,
                        "matchedBusinessRows": 0,
                        "nextRoundContent": 0,
                    },
                }
            ),
            encoding="utf-8",
        )
        capability_dir = out_dir / "reports/promotion-manager/capability"
        capability_dir.mkdir(parents=True)
        (capability_dir / "final-capability-audit.json").write_text(
            json.dumps(
                {
                    "requirements": [
                        {"id": "product_url_structured_intake", "status": "ready", "evidence": [], "missing": []},
                        {"id": "viral_creator_content_research", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "copy_and_real_video_generation", "status": "ready", "evidence": [], "missing": []},
                        {"id": "all_platform_auto_publish", "status": "blocked_by_authorization_or_platform_limits", "evidence": [], "missing": []},
                        {"id": "real_metrics_orders_revenue_recovery", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "retrospective_next_round_optimization", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "fully_autonomous_self_evolution", "status": "blocked_by_safety_boundary", "evidence": [], "missing": []},
                    ],
                    "platforms": {},
                }
            ),
            encoding="utf-8",
        )
        synthetic_dir = out_dir / "synthetic-validation/reports/promotion-manager/synthetic-evidence"
        synthetic_dir.mkdir(parents=True)
        (synthetic_dir / "synthetic-evidence.json").write_text(
            json.dumps(
                {
                    "status": "synthetic_validation_ready",
                    "synthetic": True,
                    "warning": "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT",
                    "input": {"platforms": ["youtube", "github"]},
                    "summary": {
                        "metricRows": 2,
                        "commentLines": 4,
                        "businessRows": 2,
                        "recoveryExitCode": 0,
                    },
                    "recovery": {
                        "exitCode": 0,
                        "reports": {
                            "metricsRecovery": "synthetic-validation/reports/promotion-manager/metrics-recovery/metrics-recovery.json",
                            "nextRoundOptimization": "synthetic-validation/reports/promotion-manager/optimization/next-round-optimization.json",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        subprocess.run([sys.executable, str(FINAL_CAPABILITY_READINESS), "--out-dir", str(out_dir)], check=True, cwd=ROOT)

        report_path = out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        by_requirement = {item["id"]: item for item in report["requirements"]}
        metrics_row = by_requirement["real_metrics_comments_orders_revenue"]
        self.assertEqual(metrics_row["status"], "waiting_real_data")
        self.assertFalse(metrics_row["satisfied"])
        self.assertFalse(metrics_row["metrics"]["hasFullFunnelEvidence"])
        self.assertEqual(metrics_row["metrics"]["capturedMetricRecords"], 0)
        self.assertTrue(metrics_row["metrics"]["syntheticValidationReady"])
        self.assertTrue(metrics_row["metrics"]["syntheticRecoveryValidated"])
        self.assertTrue(metrics_row["metrics"]["syntheticNextRoundValidated"])
        self.assertEqual(metrics_row["metrics"]["syntheticValidationMetricRows"], 2)
        self.assertEqual(metrics_row["metrics"]["syntheticValidationCommentLines"], 4)
        self.assertEqual(metrics_row["metrics"]["syntheticValidationBusinessRows"], 2)
        self.assertEqual(metrics_row["metrics"]["syntheticValidationWarning"], "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT")
        self.assertIn("SYNTHETIC_DEMO_DATA_DO_NOT_REPORT", metrics_row["limits"])
        next_round_row = by_requirement["next_round_optimization"]
        self.assertEqual(next_round_row["status"], "waiting_real_data")
        self.assertTrue(next_round_row["metrics"]["syntheticNextRoundValidated"])
        self.assertIn("synthetic/demo next-round validation exists but real evidence is still required", next_round_row["missing"])
        self.assertTrue(report["sourceReports"]["syntheticEvidence"][0]["exists"])
        self.assertFalse(any(item["id"] == "run_synthetic_evidence_validation" for item in report["actionQueue"]))
        report_markdown = (out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Synthetic validation", report_markdown)
        self.assertIn("SYNTHETIC_DEMO_DATA_DO_NOT_REPORT", report_markdown)

    def test_final_capability_readiness_flags_missing_requested_video_platform_evidence(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-readiness-video-gap-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        final_run_dir = out_dir / "reports/promotion-manager/final-run"
        final_run_dir.mkdir(parents=True)
        (final_run_dir / "final-capability-run.json").write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-10",
                    "status": "partial_ready",
                    "input": {
                        "codexReadFirst": True,
                        "platforms": "youtube,douyin,github",
                        "urls": ["https://www.enhe-tech.com.cn/software/windows-ai"],
                    },
                    "summary": {
                        "promotionRuns": 1,
                        "multiQueryDiscoveryRuns": 1,
                        "multiQuerySearchCapturesReady": 1,
                        "multiQueryMergedMaterials": 2,
                        "multiQueryMergedCreators": 1,
                        "multiQueryDeepEvidenceRuns": 1,
                        "multiQueryVideoSampleFrames": 2,
                        "contentArtifacts": 1,
                        "videoFilesGenerated": 1,
                    },
                    "productBatch": {
                        "platforms": "youtube,douyin,github",
                        "promotionRuns": [
                            {
                                "multiQueryViralDiscovery": {
                                    "summary": {"platforms": ["github"], "mergedMaterials": 2}
                                }
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        capability_dir = out_dir / "reports/promotion-manager/capability"
        capability_dir.mkdir(parents=True)
        (capability_dir / "final-capability-audit.json").write_text(
            json.dumps(
                {
                    "requirements": [
                        {"id": "product_url_structured_intake", "status": "ready", "evidence": [], "missing": []},
                        {"id": "viral_creator_content_research", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "copy_and_real_video_generation", "status": "ready", "evidence": [], "missing": []},
                        {"id": "all_platform_auto_publish", "status": "blocked_by_authorization_or_platform_limits", "evidence": [], "missing": []},
                        {"id": "real_metrics_orders_revenue_recovery", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "retrospective_next_round_optimization", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "fully_autonomous_self_evolution", "status": "blocked_by_safety_boundary", "evidence": [], "missing": []},
                    ],
                    "platforms": {},
                }
            ),
            encoding="utf-8",
        )

        subprocess.run([sys.executable, str(FINAL_CAPABILITY_READINESS), "--out-dir", str(out_dir)], check=True, cwd=ROOT)

        report = json.loads(
            (out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json").read_text(
                encoding="utf-8"
            )
        )
        viral_row = {item["id"]: item for item in report["requirements"]}["viral_creator_video_research"]
        self.assertEqual(viral_row["status"], "partial_ready_non_video_platform_evidence")
        self.assertEqual(viral_row["metrics"]["observedResearchPlatforms"], ["github"])
        self.assertEqual(viral_row["metrics"]["missingVideoPlatformEvidence"], ["douyin", "youtube"])
        self.assertIn("no viral material evidence was captured for requested video platforms: douyin, youtube", viral_row["missing"])
        capture_action = next(item for item in report["actionQueue"] if item["id"] == "capture_missing_video_platform_evidence")
        self.assertIn("--platforms douyin,youtube", capture_action["command"])
        self.assertIn("--multi-query-sample-video-frames", capture_action["command"])
        self.assertIn("--multi-query-query-count 1", capture_action["command"])
        self.assertIn("--multi-query-top-n 5", capture_action["command"])
        self.assertIn("--timeout-ms 15000", capture_action["command"])
        self.assertIn("--wait-until domcontentloaded", capture_action["command"])
        self.assertIn("--multi-query-browser-search-timeout-ms 15000", capture_action["command"])
        self.assertIn("--multi-query-browser-search-wait-until domcontentloaded", capture_action["command"])
        self.assertIn("--multi-query-video-sample-count 2", capture_action["command"])
        self.assertIn("https://www.enhe-tech.com.cn/software/windows-ai", capture_action["command"])
        self.assertTrue(any(item["id"] == "setup_viral_evidence_inbox" for item in report["actionQueue"]))
        self.assertTrue(any(item["id"] == "import_viral_evidence_inbox" for item in report["actionQueue"]))
        synthetic_action = next(item for item in report["actionQueue"] if item["id"] == "run_synthetic_evidence_validation")
        self.assertIn("https://www.enhe-tech.com.cn/software/windows-ai", synthetic_action["command"])
        final_step = next(item for item in report["operatingSequence"] if item["step"] == "run_final_capability")
        self.assertIn("https://www.enhe-tech.com.cn/software/windows-ai", final_step["command"])

    def test_final_capability_readiness_does_not_relist_observed_video_platform_as_missing(self) -> None:
        module = load_script_module(FINAL_CAPABILITY_READINESS)
        row = module.viral_research_row(
            {
                "input": {"platforms": "youtube,douyin,xiaohongshu"},
                "summary": {
                    "multiQueryDiscoveryRuns": 1,
                    "multiQuerySearchCapturesReady": 3,
                    "multiQueryMergedMaterials": 4,
                    "multiQueryMergedCreators": 1,
                    "multiQueryDeepEvidenceRuns": 1,
                    "multiQueryVideoSampleFrames": 3,
                },
                "productBatch": {
                    "promotionRuns": [
                        {
                            "multiQueryViralDiscovery": {
                                "summary": {"platforms": ["youtube"]}
                            }
                        }
                    ]
                },
            },
            {
                "requirements": [
                    {
                        "id": "viral_creator_content_research",
                        "status": "partial_ready",
                        "evidence": [],
                        "missing": [],
                        "limits": [],
                    }
                ]
            },
            [],
            [],
            [],
        )

        self.assertEqual(row["metrics"]["observedVideoPlatforms"], ["youtube"])
        self.assertEqual(row["metrics"]["missingVideoPlatformEvidence"], ["douyin", "xiaohongshu"])
        self.assertIn(
            "no browser-visible video frame samples were captured for requested video platforms: douyin, xiaohongshu",
            row["missing"],
        )
        self.assertNotIn(
            "no browser-visible video frame samples were captured for requested video platforms: douyin, xiaohongshu, youtube",
            row["missing"],
        )

    def test_final_capability_readiness_distinguishes_field_level_real_evidence(self) -> None:
        root_dir = Path(tempfile.mkdtemp(prefix="final-readiness-fields-test-"))
        self.addCleanup(shutil.rmtree, root_dir, ignore_errors=True)

        def write_sources(out_dir: Path, summary: dict[str, Any], evidence_setup_targets: int = 0) -> None:
            final_run_dir = out_dir / "reports/promotion-manager/final-run"
            final_run_dir.mkdir(parents=True)
            (final_run_dir / "final-capability-run.json").write_text(
                json.dumps(
                    {
                        "generatedAt": "2026-07-08",
                        "status": "partial_ready",
                        "input": {"codexReadFirst": True},
                        "summary": {
                            "promotionRuns": 1,
                            "multiQueryDiscoveryRuns": 1,
                            "multiQueryMergedMaterials": 2,
                            "multiQueryMergedCreators": 1,
                            "multiQueryVideoSampleFrames": 1,
                            "contentArtifacts": 1,
                            "videoFilesGenerated": 1,
                            "nextRoundContent": 1,
                            **summary,
                        },
                        "productBatch": {},
                    }
                ),
                encoding="utf-8",
            )
            if evidence_setup_targets:
                evidence_dir = out_dir / "reports/promotion-manager/real-evidence-setup"
                evidence_dir.mkdir(parents=True)
                (evidence_dir / "real-evidence-setup.json").write_text(
                    json.dumps(
                        {
                            "generatedAt": "2026-07-08",
                            "status": "ready",
                            "summary": {"targets": evidence_setup_targets},
                            "records": [],
                            "artifacts": {},
                        }
                    ),
                    encoding="utf-8",
                )
            capability_dir = out_dir / "reports/promotion-manager/capability"
            capability_dir.mkdir(parents=True)
            (capability_dir / "final-capability-audit.json").write_text(
                json.dumps(
                    {
                        "requirements": [
                            {"id": "product_url_structured_intake", "status": "ready", "evidence": [], "missing": []},
                            {"id": "viral_creator_content_research", "status": "partial_ready", "evidence": [], "missing": []},
                            {"id": "copy_and_real_video_generation", "status": "ready", "evidence": [], "missing": []},
                            {"id": "all_platform_auto_publish", "status": "blocked_by_authorization_or_platform_limits", "evidence": [], "missing": []},
                            {"id": "real_metrics_orders_revenue_recovery", "status": "partial_ready", "evidence": [], "missing": []},
                            {"id": "retrospective_next_round_optimization", "status": "ready", "evidence": [], "missing": []},
                            {"id": "fully_autonomous_self_evolution", "status": "blocked_by_safety_boundary", "evidence": [], "missing": []},
                        ],
                        "platforms": {},
                    }
                ),
                encoding="utf-8",
            )

        cases = [
            (
                "full_funnel",
                {
                    "capturedMetricRecords": 1,
                    "recordsWithMetrics": 1,
                    "commentCount": 2,
                    "matchedBusinessRows": 1,
                    "viewsEvidenceRecords": 1,
                    "likesEvidenceRecords": 1,
                    "commentsEvidenceRecords": 2,
                    "ordersEvidenceRecords": 1,
                    "revenueEvidenceRecords": 1,
                },
                "ready_with_full_funnel_evidence",
                True,
                0,
            ),
            (
                "social_only",
                {
                    "capturedMetricRecords": 1,
                    "recordsWithMetrics": 1,
                    "commentCount": 2,
                    "viewsEvidenceRecords": 1,
                    "likesEvidenceRecords": 1,
                    "commentsEvidenceRecords": 2,
                    "ordersEvidenceRecords": 0,
                    "revenueEvidenceRecords": 0,
                },
                "partial_ready_social_metrics_only",
                False,
                0,
            ),
            (
                "templates_only",
                {},
                "waiting_real_data_with_evidence_templates",
                False,
                2,
            ),
        ]
        for name, summary, expected_status, expected_satisfied, evidence_setup_targets in cases:
            with self.subTest(name=name):
                out_dir = root_dir / name
                write_sources(out_dir, summary, evidence_setup_targets)
                subprocess.run(
                    [sys.executable, str(FINAL_CAPABILITY_READINESS), "--out-dir", str(out_dir)],
                    check=True,
                    cwd=ROOT,
                )
                report = json.loads(
                    (out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json").read_text(
                        encoding="utf-8"
                    )
                )
                metrics_row = {item["id"]: item for item in report["requirements"]}["real_metrics_comments_orders_revenue"]
                self.assertEqual(metrics_row["status"], expected_status)
                self.assertEqual(metrics_row["satisfied"], expected_satisfied)
                self.assertEqual(metrics_row["metrics"]["hasFullFunnelEvidence"], expected_satisfied)
                if name == "social_only":
                    self.assertIn("no real order evidence in final run", metrics_row["missing"])
                    self.assertIn("no real revenue evidence in final run", metrics_row["missing"])
                if name == "templates_only":
                    self.assertEqual(metrics_row["metrics"]["realEvidenceSetupTargets"], 2)
                    self.assertIn("real evidence templates are ready but no filled real data has been imported", metrics_row["missing"])
                    self.assertTrue(report["sourceReports"]["realEvidenceSetup"][0]["exists"])
                    self.assertFalse(any(item["id"] == "build_real_evidence_setup" for item in report["actionQueue"]))

    def test_final_capability_readiness_explicit_sources_override_discovery(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="final-readiness-explicit-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)

        final_run_dir = out_dir / "reports/promotion-manager/final-run"
        final_run_dir.mkdir(parents=True)
        (final_run_dir / "final-capability-run.json").write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-10",
                    "status": "partial_ready",
                    "input": {"codexReadFirst": True, "platforms": "youtube,github"},
                    "summary": {
                        "promotionRuns": 1,
                        "multiQueryDiscoveryRuns": 1,
                        "multiQueryMergedMaterials": 1,
                        "multiQueryMergedCreators": 1,
                        "multiQueryVideoSampleFrames": 1,
                        "contentArtifacts": 1,
                        "videoFilesGenerated": 1,
                    },
                    "productBatch": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        capability_dir = out_dir / "reports/promotion-manager/capability"
        capability_dir.mkdir(parents=True)
        (capability_dir / "final-capability-audit.json").write_text(
            json.dumps(
                {
                    "requirements": [
                        {"id": "product_url_structured_intake", "status": "ready", "evidence": [], "missing": []},
                        {"id": "viral_creator_content_research", "status": "ready", "evidence": [], "missing": []},
                        {"id": "copy_and_real_video_generation", "status": "ready", "evidence": [], "missing": []},
                        {
                            "id": "all_platform_auto_publish",
                            "status": "blocked_by_authorization_or_platform_limits",
                            "evidence": [],
                            "missing": [
                                "GITHUB_TOKEN or GH_TOKEN for GitHub writes",
                                "YouTube OAuth access token or OAuth client credentials",
                            ],
                        },
                        {"id": "real_metrics_orders_revenue_recovery", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "retrospective_next_round_optimization", "status": "partial_ready", "evidence": [], "missing": []},
                        {"id": "fully_autonomous_self_evolution", "status": "blocked_by_safety_boundary", "evidence": [], "missing": []},
                    ],
                    "platforms": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        default_readiness_dir = out_dir / "reports/promotion-manager/publish-readiness"
        default_readiness_dir.mkdir(parents=True)
        (default_readiness_dir / "publish-readiness.json").write_text(
            json.dumps(
                {
                    "status": "partial_ready",
                    "records": [
                        {"platform": "old-youtube", "readiness": "manual_publish_required"},
                        {"platform": "old-github", "readiness": "manual_publish_required"},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        explicit_dir = out_dir / "explicit"
        explicit_dir.mkdir()
        explicit_readiness = explicit_dir / "publish-readiness.json"
        explicit_readiness.write_text(
            json.dumps(
                {
                    "status": "partial_ready",
                    "records": [
                        {"platform": "github", "readiness": "dry_run_ready"},
                        {
                            "platform": "youtube",
                            "readiness": "missing_credentials",
                            "credentialStatus": {
                                "missingEnv": [
                                    "YOUTUBE_OAUTH_ACCESS_TOKEN",
                                    "GOOGLE_OAUTH_CLIENT_ID",
                                    "GOOGLE_OAUTH_CLIENT_SECRET",
                                ]
                            },
                        },
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        explicit_setup = explicit_dir / "publish-setup.json"
        explicit_setup.write_text(
            json.dumps({"status": "ready", "records": [{"platform": "github"}]}) + "\n",
            encoding="utf-8",
        )
        explicit_evidence_setup = explicit_dir / "real-evidence-setup.json"
        explicit_evidence_setup.write_text(
            json.dumps({"status": "ready", "summary": {"targets": 1}, "records": []}) + "\n",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(FINAL_CAPABILITY_READINESS),
                "--out-dir",
                str(out_dir),
                "--publish-readiness",
                str(explicit_readiness),
                "--publish-setup",
                str(explicit_setup),
                "--real-evidence-setup",
                str(explicit_evidence_setup),
            ],
            check=True,
            cwd=ROOT,
        )

        report = json.loads(
            (out_dir / "reports/promotion-manager/final-readiness/final-capability-readiness.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(report["sourceReports"]["publishReadiness"]), 1)
        self.assertEqual(report["sourceReports"]["publishReadiness"][0]["path"], str(explicit_readiness))
        publish_row = {item["id"]: item for item in report["requirements"]}["official_or_browser_assisted_publish"]
        self.assertEqual(publish_row["metrics"]["readinessRecords"], 2)
        self.assertEqual(publish_row["metrics"]["setupRecords"], 1)
        self.assertNotIn("GITHUB_TOKEN or GH_TOKEN for GitHub writes", publish_row["missing"])
        self.assertIn("YouTube OAuth access token or OAuth client credentials", publish_row["missing"])
        metrics_row = {item["id"]: item for item in report["requirements"]}["real_metrics_comments_orders_revenue"]
        self.assertEqual(metrics_row["metrics"]["realEvidenceSetupTargets"], 1)

    def test_platform_access_audit_maps_official_paths_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="platform-access-audit-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env = os.environ.copy()
        secret_value = "super-secret-platform-token"
        for name in [
            "YOUTUBE_API_KEY",
            "YOUTUBE_ACCESS_TOKEN",
            "YOUTUBE_OAUTH_ACCESS_TOKEN",
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "DOUYIN_CLIENT_KEY",
            "DOUYIN_CLIENT_SECRET",
            "DOUYIN_ACCESS_TOKEN",
            "DOUYIN_OPEN_ID",
            "TIKTOK_CLIENT_KEY",
            "TIKTOK_CLIENT_SECRET",
            "TIKTOK_ACCESS_TOKEN",
            "TIKTOK_OPEN_ID",
        ]:
            env.pop(name, None)
        env["YOUTUBE_OAUTH_ACCESS_TOKEN"] = secret_value
        subprocess.run(
            [
                sys.executable,
                str(PLATFORM_ACCESS_AUDIT),
                "--platforms",
                "youtube,github,xiaohongshu,zhihu,douyin,tiktok",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/platform-access/platform-access-audit.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        by_platform = {item["platform"]: item for item in report["platforms"]}
        self.assertEqual(by_platform["youtube"]["publish"]["access"], "implemented_official_api")
        self.assertTrue(by_platform["youtube"]["publish"]["readyForAutomation"])
        self.assertEqual(by_platform["github"]["publish"]["access"], "implemented_official_api")
        self.assertEqual(by_platform["xiaohongshu"]["publish"]["access"], "no_verified_public_creator_publish_endpoint")
        self.assertEqual(by_platform["zhihu"]["publish"]["mode"], "manual_or_browser_assisted_until_verified")
        self.assertEqual(by_platform["douyin"]["publish"]["access"], "manual_or_browser_assisted_required")
        self.assertIn("browser_publish_session.py", by_platform["douyin"]["publish"]["implementedBy"])
        self.assertFalse(by_platform["douyin"]["publish"]["readyForAutomation"])
        self.assertEqual(by_platform["tiktok"]["automationLevel"], "official_app_integration_required")
        self.assertEqual(report["learningFreshness"]["status"], "stale_not_live_checked")
        self.assertTrue(any(item["gap"] == "verified_official_creator_publish_api_missing" for item in report["implementationGaps"]))
        gap_research = report["officialDocGapResearch"]
        self.assertEqual(gap_research["status"], "official_app_or_executor_gaps_documented")
        self.assertGreaterEqual(gap_research["summary"]["records"], 1)
        zhihu_research = [
            item for item in gap_research["records"] if item["platform"] == "zhihu" and item["area"] == "publish"
        ]
        self.assertTrue(zhihu_research)
        self.assertEqual(zhihu_research[0]["docEvidenceStatus"], "configured_not_live_checked")
        self.assertEqual(zhihu_research[0]["safeFallback"], "manual_or_browser_assisted_publish")
        self.assertTrue(zhihu_research[0]["searchedOfficialSources"])
        douyin_research = [
            item for item in gap_research["records"] if item["platform"] == "douyin" and item["area"] == "publish"
        ]
        self.assertTrue(douyin_research)
        self.assertEqual(douyin_research[0]["safeFallback"], "manual_or_browser_assisted_publish")
        self.assertTrue((out_dir / "reports/promotion-manager/platform-access/platform-access-audit.md").exists())

    def test_platform_access_audit_summarizes_live_official_doc_evidence(self) -> None:
        module = load_script_module(PLATFORM_ACCESS_AUDIT)
        module.check_url = lambda url: {
            "status": "reachable",
            "httpStatus": 200,
            "finalUrl": url,
            "contentType": "text/html",
            "checkedAt": "2026-07-08T00:00:00Z",
        }

        records = [module.platform_record("youtube", True), module.platform_record("zhihu", True)]
        youtube = records[0]
        zhihu = records[1]
        self.assertEqual(youtube["publish"]["officialDocEvidenceStatus"], "all_reachable")
        self.assertEqual(youtube["publish"]["officialDocs"][0]["liveCheck"]["checkedAt"], "2026-07-08T00:00:00Z")
        self.assertEqual(zhihu["publish"]["officialDocEvidenceStatus"], "all_reachable")

        summary = module.official_doc_summary(records)
        self.assertEqual(summary["reachableDocs"], 6)
        self.assertEqual(summary["missingDocCapabilities"], 0)
        self.assertIn("all_reachable", summary["capabilityEvidenceStatus"])
        self.assertEqual(module.learning_freshness(True, module.official_doc_summary([youtube]))["status"], "fresh_live_checked")
        self.assertEqual(module.learning_freshness(False, summary)["status"], "stale_not_live_checked")
        gaps = module.implementation_gaps(records)
        self.assertFalse(any(item["gap"] == "official_doc_evidence_missing" for item in gaps))
        gap_research = module.official_doc_gap_research(records, True)
        self.assertEqual(gap_research["status"], "manual_or_evidence_fallbacks_documented")
        self.assertEqual(gap_research["summary"]["missingOfficialDocCapabilities"], 0)
        zhihu_publish = [
            item for item in gap_research["records"] if item["platform"] == "zhihu" and item["area"] == "publish"
        ][0]
        self.assertEqual(zhihu_publish["docEvidenceStatus"], "all_reachable")
        self.assertEqual(zhihu_publish["safeFallback"], "manual_or_browser_assisted_publish")
        self.assertEqual(zhihu_publish["searchedOfficialSources"][0]["liveCheck"]["checkedAt"], "2026-07-08T00:00:00Z")

    def test_platform_access_learning_treats_fallback_doc_failures_as_warnings(self) -> None:
        module = load_script_module(PLATFORM_ACCESS_AUDIT)

        def mixed_check(url: str) -> dict[str, Any]:
            if "xiaohongshu" in url:
                return {"status": "unreachable", "reason": "timeout", "checkedAt": "2026-07-08T00:00:00Z"}
            return {
                "status": "reachable",
                "httpStatus": 200,
                "finalUrl": url,
                "contentType": "text/html",
                "checkedAt": "2026-07-08T00:00:00Z",
            }

        module.check_url = mixed_check
        records = [module.platform_record("youtube", True), module.platform_record("xiaohongshu", True)]
        summary = module.official_doc_summary(records)
        freshness = module.learning_freshness(True, summary)

        self.assertEqual(summary["criticalFailedDocs"], 0)
        self.assertEqual(summary["fallbackFailedDocs"], 2)
        self.assertEqual(freshness["status"], "fresh_live_checked_with_warnings")
        self.assertEqual(freshness["failedDocs"], 2)
        self.assertIn("manual/browser-assisted fallback", freshness["warning"])

        module.check_url = lambda url: {
            "status": "unreachable" if "youtube" in url else "reachable",
            "reason": "timeout",
            "checkedAt": "2026-07-08T00:00:00Z",
        }
        critical_records = [module.platform_record("youtube", True)]
        critical_summary = module.official_doc_summary(critical_records)
        self.assertGreater(critical_summary["criticalFailedDocs"], 0)
        self.assertEqual(module.learning_freshness(True, critical_summary)["status"], "partial_live_check_failed")

    def test_platform_access_live_check_handles_remote_disconnect(self) -> None:
        module = load_script_module(PLATFORM_ACCESS_AUDIT)

        def disconnected(_request: object, timeout: int = 10) -> object:
            raise module.http.client.RemoteDisconnected("closed without response")

        original_urlopen = module.urllib.request.urlopen
        try:
            module.urllib.request.urlopen = disconnected
            result = module.check_url("https://developer.example.test/docs")
        finally:
            module.urllib.request.urlopen = original_urlopen

        self.assertEqual(result["status"], "unreachable")
        self.assertIn("closed without response", result["reason"])
        self.assertIn("checkedAt", result)

    def test_viral_discovery_runner_builds_multiplatform_library_and_creator_tasks(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="viral-discovery-runner-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_dir = out_dir / "html"
        html_dir.mkdir()
        fixtures = {
            "youtube": (
                "https://www.youtube.com/watch?v=abc123",
                "AI workflow exploded to 1M views",
                "creator: Launch Lab views: 1.2M likes: 52K comments: 1200",
            ),
            "zhihu": (
                "https://www.zhihu.com/question/123/answer/456",
                "How AI operators build content engines",
                "creator: Zhihu Builder likes: 8800 comments: 640",
            ),
            "xiaohongshu": (
                "https://www.xiaohongshu.com/explore/note123",
                "3 steps to launch an AI product note",
                "creator: Red Launch favorites: 12000 likes: 9000 comments: 830",
            ),
            "douyin": (
                "https://www.douyin.com/video/123",
                "30 seconds AI product demo hook",
                "creator: Demo Studio views: 2.4M likes: 180K shares: 9000",
            ),
            "github": (
                "https://github.com/example/ai-promo-kit",
                "AI promo kit repository",
                "creator: example stars: 4200 forks: 380",
            ),
        }
        for platform, (url, title, body) in fixtures.items():
            (html_dir / f"{platform}.html").write_text(
                f"""
                <html><head><title>{platform} search</title></head>
                <body>
                  <article>
                    <a href="{url}">{title}</a>
                    <p>{body}</p>
                    <p>Hook: stop writing product copy from scratch.</p>
                    <p>CTA: try the workflow and follow for more.</p>
                  </article>
                </body></html>
                """,
                encoding="utf-8",
            )
        subprocess.run(
            [
                sys.executable,
                str(VIRAL_DISCOVERY_RUNNER),
                "--query",
                "AI product promotion",
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--top-n",
                "5",
                "--html-snapshot-dir",
                str(html_dir),
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "output/reports/promotion-manager/competitors/viral-discovery-run.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["coverage"]["requestedPlatforms"], 5)
        self.assertEqual(report["coverage"]["searchCapturesReady"], 5)
        self.assertEqual(report["coverage"]["viralMaterials"], 5)
        self.assertGreaterEqual(report["coverage"]["creators"], 1)
        self.assertTrue(Path(report["viralContentLibrary"]["library"]).exists())
        self.assertTrue(Path(report["creatorLeaderboard"]["leaderboard"]).exists())
        self.assertTrue(Path(report["creatorLeaderboard"]["followUpTasks"]).exists())
        task_summary = report["viralContentLibrary"]["taskSummary"]["modes"]
        self.assertEqual(task_summary["public_url_capture_candidate"], 2)
        self.assertEqual(task_summary["browser_assisted_capture_required"], 3)
        self.assertEqual(report["coverage"]["followUpTasksQueued"], 5)
        self.assertEqual(report["coverage"]["followUpPublicUrlTasks"], 2)
        self.assertEqual(report["coverage"]["followUpBrowserAssistedTasks"], 3)
        self.assertEqual(report["coverage"]["followUpCaptureStatus"], "skipped")
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/viral-discovery-run.md").exists())

    def test_viral_discovery_runner_passes_browser_search_wait_and_timeout(self) -> None:
        module = load_script_module(VIRAL_DISCOVERY_RUNNER)
        out_dir = Path(tempfile.mkdtemp(prefix="viral-discovery-browser-search-args-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        captured: dict[str, Any] = {}

        def fake_run_command(name: str, command: list[str], check: bool = False) -> dict[str, Any]:
            captured["name"] = name
            captured["command"] = command
            report_dir = out_dir / "reports/promotion-manager/competitors"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "browser-search-snapshots.json").write_text(
                json.dumps({"snapshotDir": str(out_dir / "snapshots"), "records": []}),
                encoding="utf-8",
            )
            return {"name": name, "command": command, "exitCode": 0, "stdoutTail": "", "stderrTail": ""}

        original_run_command = module.run_command
        try:
            module.run_command = fake_run_command
            args = module.argparse.Namespace(
                query="AI product promotion",
                platforms="douyin,xiaohongshu",
                top_n=5,
                out_dir=str(out_dir),
                snapshot_dir="",
                html_snapshot_dir="",
                install_browser_if_missing=False,
                skip_browser_search=False,
                browser_search_timeout_ms=15000,
                browser_search_wait_until="domcontentloaded",
            )
            result = module.run_browser_search(args, out_dir, [])
        finally:
            module.run_command = original_run_command

        self.assertEqual(result["status"], "ready")
        self.assertEqual(captured["name"], "platform_search_browser")
        command = captured["command"]
        self.assertIn("--timeout-ms", command)
        self.assertEqual(command[command.index("--timeout-ms") + 1], "15000")
        self.assertIn("--wait-until", command)
        self.assertEqual(command[command.index("--wait-until") + 1], "domcontentloaded")

    def test_viral_discovery_runner_reports_deep_video_follow_up_evidence(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="viral-discovery-video-evidence-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        video_path = site_dir / "sample.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x2563eb:s=320x180:d=2",
                "-pix_fmt",
                "yuv420p",
                str(video_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        (site_dir / "video.html").write_text(
            """<!doctype html>
<html>
<head><title>Launch video teardown</title></head>
<body>
  <h1>Launch video teardown</h1>
  <p>creator: Launch Lab views: 120000 likes: 9000 comments: 420</p>
  <p>Hook: show the product result before explaining the workflow.</p>
  <p>Voiceover: problem, mechanism, proof, CTA.</p>
  <video controls width="320" height="180" src="/sample.mp4?token=secret-video-token"></video>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        video_page_url = f"http://127.0.0.1:{server.server_address[1]}/video.html"
        html_dir = out_dir / "html"
        html_dir.mkdir()
        (html_dir / "youtube.html").write_text(
            f"""
            <html><head><title>youtube search</title></head>
            <body>
              <article>
                <a href="{video_page_url}">Launch video teardown</a>
                <p>creator: Launch Lab views: 120000 likes: 9000 comments: 420</p>
                <p>Hook: show the product result before explaining the workflow.</p>
              </article>
            </body></html>
            """,
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(VIRAL_DISCOVERY_RUNNER),
                "--query",
                "AI product video launch",
                "--platforms",
                "youtube",
                "--top-n",
                "1",
                "--html-snapshot-dir",
                str(html_dir),
                "--run-follow-up-captures",
                "--allow-localhost-follow-up",
                "--sample-video-frames",
                "--video-sample-count",
                "2",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "output/reports/promotion-manager/competitors/viral-discovery-run.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-video-token", report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["coverage"]["followUpCaptureStatus"], "ready")
        self.assertEqual(report["coverage"]["followUpImportedRecords"], 1)
        self.assertEqual(report["coverage"]["followUpPublicCaptureReady"], 1)
        self.assertEqual(report["coverage"]["videoSampleRuns"], 1)
        self.assertEqual(report["coverage"]["videoSampleReady"], 1)
        self.assertEqual(report["coverage"]["videoSampleFrames"], 2)
        self.assertTrue(Path(report["followUpCaptures"]["deepCompetitorLibrary"]).exists())

    def test_multi_query_viral_discovery_dry_run_builds_product_search_plan(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="multi-query-discovery-plan-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        subprocess.run(
            [
                sys.executable,
                str(MULTI_QUERY_VIRAL_DISCOVERY),
                "--product-name",
                "AI Prompt Kit",
                "--value-proposition",
                "Prompt templates for product copy, SEO content, and video scripts",
                "--keywords",
                "自动化",
                "--pain-points",
                "内容发布慢",
                "--audience",
                "独立开发者",
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--query-count",
                "6",
                "--browser-search-timeout-ms",
                "15000",
                "--browser-search-wait-until",
                "domcontentloaded",
                "--dry-run",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "output/reports/promotion-manager/competitors/multi-query-viral-discovery.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        queries = [item["query"] for item in report["queryPlan"]]
        self.assertEqual(report["status"], "planned")
        self.assertIn("AI Prompt Kit", queries)
        self.assertIn("自动化 工具", queries)
        self.assertIn("自动化 教程", queries)
        self.assertIn("自动化 测评", queries)
        slugs = [item["slug"] for item in report["queryPlan"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(report["summary"]["plannedRuns"], 6)
        self.assertTrue(all("--platforms" in run["command"] for run in report["runs"]))
        for run in report["runs"]:
            command = run["command"]
            self.assertIn("--browser-search-timeout-ms", command)
            self.assertEqual(command[command.index("--browser-search-timeout-ms") + 1], "15000")
            self.assertIn("--browser-search-wait-until", command)
            self.assertEqual(command[command.index("--browser-search-wait-until") + 1], "domcontentloaded")
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/multi-query-viral-discovery.md").exists())

    def test_multi_query_viral_discovery_loads_env_file_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="multi-query-discovery-env-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env_file = out_dir / ".env"
        secret_value = "firecrawl-secret-must-not-be-stored"
        env_file.write_text(
            "\n".join(
                [
                    "WEB_DATA_PROVIDER=firecrawl",
                    f"FIRECRAWL_API_KEY={secret_value}",
                    "FIRECRAWL_BASE_URL=https://api.firecrawl.dev/v2",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(MULTI_QUERY_VIRAL_DISCOVERY),
                "--env-file",
                str(env_file),
                "--product-name",
                "AI Prompt Kit",
                "--query-count",
                "1",
                "--dry-run",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "output/reports/promotion-manager/competitors/multi-query-viral-discovery.json"
        report_text = report_path.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertIn("FIRECRAWL_API_KEY", report["envLoad"]["loadedKeys"])
        self.assertFalse(report["envLoad"]["valuesStored"])
        self.assertNotIn(secret_value, report_text)

    def test_multi_query_viral_discovery_merges_existing_runs_and_creators(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="multi-query-discovery-merge-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        run_a = out_dir / "run-a"
        run_b = out_dir / "run-b"
        for run_dir in [run_a, run_b]:
            (run_dir / "reports/promotion-manager/competitors").mkdir(parents=True)
        (run_a / "reports/promotion-manager/competitors/viral-content-library.json").write_text(
            json.dumps(
                {
                    "materials": [
                        {
                            "platform": "youtube",
                            "query": "AI product launch",
                            "creatorName": "Launch Lab",
                            "title": "Old AI launch breakdown",
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "visibleMetrics": {"views": 10000},
                            "viralSignals": {"score": 11},
                            "reusablePatterns": ["problem-first hook"],
                        },
                        {
                            "platform": "zhihu",
                            "query": "AI 增长案例",
                            "creatorName": "Zhihu Builder",
                            "title": "AI operators build content engines",
                            "url": "https://www.zhihu.com/question/123/answer/456",
                            "visibleMetrics": {"likes": 800},
                            "viralSignals": {"score": 8},
                            "reusablePatterns": ["case-study structure"],
                        },
                        {
                            "platform": "douyin",
                            "query": "AI product launch",
                            "creatorName": "",
                            "title": "用户协议",
                            "url": "https://www.douyin.com/agreements/?id=6773906068725565448",
                            "visibleMetrics": {},
                            "viralSignals": {"score": 999},
                            "reusablePatterns": ["needs_manual_pattern_review"],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        (run_b / "reports/promotion-manager/competitors/viral-content-library.json").write_text(
            json.dumps(
                {
                    "materials": [
                        {
                            "platform": "youtube",
                            "query": "AI viral launch",
                            "creatorName": "Launch Lab",
                            "title": "New AI launch breakdown",
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "visibleMetrics": {"views": 25000, "likes": 1200},
                            "viralSignals": {"score": 27},
                            "reusablePatterns": ["problem-first hook", "fast proof"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(MULTI_QUERY_VIRAL_DISCOVERY),
                "--product-name",
                "AI Prompt Kit",
                "--existing-run-dir",
                str(run_a),
                "--existing-run-dir",
                str(run_b),
                "--query-count",
                "0",
                "--top-n",
                "5",
                "--out-dir",
                str(out_dir / "output"),
            ],
            check=True,
            cwd=ROOT,
        )
        library = json.loads(
            (out_dir / "output/reports/promotion-manager/competitors/multi-query-viral-content-library.json").read_text(encoding="utf-8")
        )
        self.assertEqual(library["recordCount"], 2)
        self.assertTrue(all("agreements" not in item["url"] for item in library["materials"]))
        self.assertEqual(library["materials"][0]["title"], "New AI launch breakdown")
        self.assertEqual(library["materials"][0]["sourceQueries"], ["AI product launch", "AI viral launch"])
        self.assertEqual(library["aggregatePatterns"]["recordsWithObservedMetrics"], 2)
        creators = json.loads(
            (out_dir / "output/reports/promotion-manager/competitors/multi-query-creator-leaderboard.json").read_text(encoding="utf-8")
        )
        self.assertEqual(creators["creatorCount"], 2)
        self.assertEqual(creators["creators"][0]["creatorName"], "Launch Lab")
        self.assertEqual(creators["creators"][0]["materialCount"], 1)
        self.assertTrue((out_dir / "output/reports/promotion-manager/competitors/multi-query-creator-leaderboard.md").exists())

    def test_publish_url_capture_registers_structured_snapshot(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-url-capture-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "published-snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://www.xiaohongshu.com/explore/note123",
                    "title": "AI Prompt Kit launch note",
                    "text": "Published note page visible in browser.",
                    "screenshot": "xhs-published.png",
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_URL_CAPTURE),
                "--structured-json",
                str(snapshot_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        capture = json.loads((out_dir / "reports/promotion-manager/publish-capture/publish-url-capture.json").read_text(encoding="utf-8"))
        self.assertEqual(capture["status"], "ready")
        self.assertEqual(capture["record"]["platform"], "xiaohongshu")
        self.assertEqual(capture["record"]["contentId"], "note123")
        published = json.loads((out_dir / "reports/promotion-manager/published-items/published-items.json").read_text(encoding="utf-8"))
        self.assertEqual(published["summary"]["published"], 1)
        self.assertEqual(published["records"][0]["publishedUrl"], "https://www.xiaohongshu.com/explore/note123")

    def test_publish_url_capture_extracts_html_canonical_url(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-url-capture-html-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        html_path = out_dir / "published.html"
        html_path.write_text(
            """<!doctype html>
<html>
<head>
  <title>知乎发布文章</title>
  <link rel="canonical" href="https://zhuanlan.zhihu.com/p/123456">
  <meta property="og:title" content="AI Prompt Kit launch article">
</head>
<body><h1>AI Prompt Kit launch article</h1></body>
</html>""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_URL_CAPTURE),
                "--html-file",
                str(html_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/publish-capture/publish-url-capture.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["record"]["platform"], "zhihu")
        self.assertEqual(report["record"]["publishedUrl"], "https://zhuanlan.zhihu.com/p/123456")

    def test_publish_url_capture_blocks_preview_urls(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-url-capture-preview-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        text_path = out_dir / "preview.txt"
        text_path.write_text(
            "Platform: douyin\nURL: https://www.douyin.com/user/self/preview/video123\nTitle: Draft preview\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_URL_CAPTURE),
                "--text-file",
                str(text_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/publish-capture/publish-url-capture.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("url_looks_like_draft_or_preview", report["issues"])
        self.assertFalse((out_dir / "reports/promotion-manager/published-items/published-items.json").exists())

    def test_metrics_recovery_reads_default_published_items_report(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="metrics-recovery-published-items-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "title": "Launch Note",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        business_csv = out_dir / "business.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,views,likes,orders,revenue,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,3000,380,2,$88.00,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--business-csv",
                str(business_csv),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(report["coverage"]["publishedItemsDiscovered"], 1)
        self.assertEqual(report["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(report["recoveryStatus"], "ready")

    def test_business_attribution_matches_orders_by_utm_content_and_referrer(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="business-attribution-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "contentId": "xhs-note-123",
                            "title": "Launch Note",
                            "publishStatus": "published",
                        },
                        {
                            "platform": "youtube",
                            "publishedUrl": "https://www.youtube.com/watch?v=yt001",
                            "contentId": "yt001",
                            "title": "Launch Video",
                            "publishStatus": "published",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        business_csv = out_dir / "orders.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,utm_campaign,utm_content,referrer,revenue,status",
                    "order-1,xiaohongshu,launch,xhs-note-123,,88.00,paid",
                    "order-2,youtube,launch,,https://www.youtube.com/watch?v=yt001,120.00,paid",
                    "order-3,email,launch,unknown,,50.00,paid",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(BUSINESS_ATTRIBUTION),
                "--business-csv",
                str(business_csv),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/business-attribution/business-attribution.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "partial_ready")
        self.assertEqual(report["summary"]["orderRows"], 3)
        self.assertEqual(report["summary"]["matchedRows"], 2)
        self.assertEqual(report["summary"]["unmatchedRows"], 1)
        self.assertEqual(report["summary"]["attributedOrders"], 2.0)
        self.assertEqual(report["summary"]["attributedRevenue"], 208.0)
        by_platform = {item["platform"]: item for item in report["attributions"]}
        self.assertEqual(by_platform["xiaohongshu"]["metrics"]["orders"]["normalized"], 1.0)
        self.assertEqual(by_platform["xiaohongshu"]["metrics"]["revenue"]["normalized"], 88.0)
        self.assertEqual(by_platform["youtube"]["metrics"]["orders"]["normalized"], 1.0)
        self.assertIn("utm_content", by_platform["xiaohongshu"]["matchRules"])
        self.assertIn("referrer_url", by_platform["youtube"]["matchRules"])
        export = json.loads((out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json").read_text(encoding="utf-8"))
        self.assertEqual(len(export["records"]), 2)
        self.assertTrue((out_dir / "reports/promotion-manager/business-attribution/business-attribution.md").exists())

    def test_business_attribution_imports_xlsx_orders_export(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="business-attribution-xlsx-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "contentId": "note123",
                            "title": "Launch Note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        business_xlsx = out_dir / "orders.xlsx"
        write_minimal_xlsx(
            business_xlsx,
            [
                ["orderId", "utm_source", "utm_content", "revenue", "status"],
                ["order-1", "xiaohongshu", "note123", "88.00", "paid"],
                ["order-2", "xiaohongshu", "note123", "32.00", "paid"],
                ["order-3", "email", "unknown", "50.00", "paid"],
            ],
        )
        subprocess.run(
            [
                sys.executable,
                str(BUSINESS_ATTRIBUTION),
                "--business-xlsx",
                str(business_xlsx),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/business-attribution/business-attribution.json").read_text(encoding="utf-8"))
        self.assertEqual(report["sources"][0]["type"], "business_xlsx")
        self.assertEqual(report["summary"]["orderRows"], 3)
        self.assertEqual(report["summary"]["matchedRows"], 2)
        self.assertEqual(report["summary"]["unmatchedRows"], 1)
        self.assertEqual(report["summary"]["attributedOrders"], 2.0)
        self.assertEqual(report["summary"]["attributedRevenue"], 120.0)
        export = json.loads((out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json").read_text(encoding="utf-8"))
        self.assertEqual(float(export["records"][0]["revenue"]), 120.0)

    def test_business_attribution_imports_text_orders_export(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="business-attribution-text-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        published_items_path = published_dir / "published-items.json"
        published_items_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "contentId": "note123",
                            "title": "Launch Note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        business_text = out_dir / "orders.txt"
        business_text.write_text(
            "\n".join(
                [
                    "title: Launch Note",
                    "publishedUrl: https://www.xiaohongshu.com/explore/note123",
                    "contentId: note123",
                    "orders: 2",
                    "revenue: 88.00",
                    "clicks: 40",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(BUSINESS_ATTRIBUTION),
                "--business-text",
                str(business_text),
                "--published-items-json",
                str(published_items_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/business-attribution/business-attribution.json").read_text(encoding="utf-8"))
        self.assertEqual(report["sources"][0]["type"], "business_text")
        self.assertEqual(report["summary"]["matchedRows"], 1)
        self.assertEqual(report["summary"]["attributedOrders"], 2.0)
        self.assertEqual(report["summary"]["attributedRevenue"], 88.0)

    def test_metrics_recovery_accepts_business_attribution_export(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="business-attribution-recovery-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        published_dir = out_dir / "reports/promotion-manager/published-items"
        published_dir.mkdir(parents=True)
        (published_dir / "published-items.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "publishedUrl": "https://www.xiaohongshu.com/explore/note123",
                            "contentId": "xhs-note-123",
                            "title": "Launch Note",
                            "publishStatus": "published",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        business_csv = out_dir / "orders.csv"
        business_csv.write_text(
            "\n".join(
                [
                    "orderId,utm_source,utm_content,revenue,status",
                    "order-1,xiaohongshu,xhs-note-123,88.00,paid",
                    "order-2,xiaohongshu,xhs-note-123,32.00,paid",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(BUSINESS_ATTRIBUTION),
                "--business-csv",
                str(business_csv),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        export_path = out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json"
        subprocess.run(
            [
                sys.executable,
                str(METRICS_RECOVERY),
                "--business-json",
                str(export_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        recovery = json.loads((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").read_text(encoding="utf-8"))
        self.assertEqual(recovery["aggregates"]["totals"]["orders"], 2.0)
        self.assertEqual(recovery["aggregates"]["totals"]["revenue"], 120.0)
        self.assertEqual(recovery["recoveryStatus"], "ready")

    def test_real_evidence_inbox_runs_recovery_and_next_round_from_inbox_files(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="real-evidence-inbox-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        inbox_dir = out_dir / "inbox"
        inbox_dir.mkdir()
        (inbox_dir / "published-urls.csv").write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,contentId,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,xhs-note-123,published-screenshot.png",
                ]
            ),
            encoding="utf-8",
        )
        (inbox_dir / "metrics.csv").write_text(
            "\n".join(
                [
                    "platform,publishedUrl,title,views,likes,comments,favorites,shares,evidence",
                    "xiaohongshu,https://www.xiaohongshu.com/explore/note123,Launch Note,3000,380,24,90,15,xhs-export.csv",
                ]
            ),
            encoding="utf-8",
        )
        (inbox_dir / "comments.txt").write_text(
            "\n".join(
                [
                    "Comment by Ada: Can this integrate with Notion API? likes: 5 replies: 1",
                    "Comment by Ben: Pricing looks good, where can I try the demo?",
                ]
            ),
            encoding="utf-8",
        )
        (inbox_dir / "orders.csv").write_text(
            "\n".join(
                [
                    "orderId,utm_source,utm_content,referrer,revenue,status",
                    "order-1,xiaohongshu,xhs-note-123,,88.00,paid",
                    "order-2,email,unknown,,50.00,paid",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(REAL_EVIDENCE_INBOX),
                "--inbox-dir",
                str(inbox_dir),
                "--out-dir",
                str(out_dir),
                "--skip-post-publish-capture",
            ],
            check=True,
            cwd=ROOT,
        )
        inbox_report = json.loads((out_dir / "reports/promotion-manager/real-evidence-inbox/real-evidence-inbox.json").read_text(encoding="utf-8"))
        self.assertEqual(inbox_report["status"], "ready")
        self.assertEqual(inbox_report["coverage"]["publishedRecords"], 1)
        self.assertEqual(inbox_report["coverage"]["recordsWithMetrics"], 1)
        self.assertEqual(inbox_report["coverage"]["commentCount"], 2)
        self.assertEqual(inbox_report["coverage"]["matchedBusinessRows"], 1)
        self.assertEqual(inbox_report["coverage"]["attributedOrders"], 1.0)
        self.assertEqual(inbox_report["coverage"]["attributedRevenue"], 88.0)
        self.assertGreater(inbox_report["coverage"]["nextRoundContent"], 0)
        step_statuses = {step["id"]: step["status"] for step in inbox_report["steps"]}
        self.assertEqual(step_statuses["published_items"], "ready")
        self.assertEqual(step_statuses["comment_evidence_capture"], "ready")
        self.assertEqual(step_statuses["business_attribution"], "ready")
        self.assertEqual(step_statuses["metrics_recovery"], "ready")
        self.assertEqual(step_statuses["next_round_optimizer"], "ready")
        self.assertTrue((out_dir / "reports/promotion-manager/published-items/published-items.json").exists())
        self.assertTrue((out_dir / "reports/promotion-manager/metrics-recovery/metrics-recovery.json").exists())
        self.assertTrue((out_dir / "reports/promotion-manager/comment-evidence/comment-evidence-export.json").exists())
        self.assertTrue((out_dir / "reports/promotion-manager/business-attribution/business-attribution-export.json").exists())
        self.assertTrue((out_dir / "reports/promotion-manager/optimization/next-round-optimization.json").exists())

    def test_publish_executor_github_dry_run_requires_explicit_execution(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-github-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        body_path = out_dir / "README-promo.md"
        body_path.write_text("# Launch draft\n\nPromotion copy.", encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "github",
                "--github-action",
                "file",
                "--github-repo",
                "hqwzhu/Viral-Product-Copy-Video-Generator",
                "--path",
                "PROMOTION.md",
                "--content-file",
                str(body_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["platform"], "github")
        self.assertTrue(report["approvalRequired"])
        self.assertEqual(report["request"]["method"], "PUT")
        self.assertNotIn("GITHUB_TOKEN", json.dumps(report))

    def test_publish_executor_github_dry_run_can_plan_pull_request_from_env(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-github-pr-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        body_path = out_dir / "README-promo.md"
        body_path.write_text("# Launch draft\n\nPromotion copy for PR.", encoding="utf-8")
        env = os.environ.copy()
        env["GITHUB_OWNER"] = "hqwzhu"
        env["GITHUB_REPO"] = "Viral-Product-Copy-Video-Generator"
        env["GITHUB_CREATE_PR"] = "true"
        env["GITHUB_PR_BASE"] = "main"
        env["GITHUB_PR_BRANCH_PREFIX"] = "auto-publish"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "github",
                "--github-action",
                "pull_request",
                "--path",
                "PROMOTION.md",
                "--content-file",
                str(body_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["repository"], "hqwzhu/Viral-Product-Copy-Video-Generator")
        self.assertTrue(report["request"]["createPullRequest"])
        self.assertEqual(report["request"]["baseBranch"], "main")
        self.assertTrue(report["request"]["branch"].startswith("auto-publish/"))
        self.assertEqual(report["publishPreview"]["platform"], "github")
        audit_path = out_dir / "reports/promotion-manager/publish-results/publish-audit-log.jsonl"
        audit = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(audit[-1]["platform"], "github")
        self.assertEqual(audit[-1]["status"], "dry_run")
        self.assertNotIn("GITHUB_TOKEN", report_path.read_text(encoding="utf-8"))

    def test_publish_executor_execute_requires_environment_publish_gate(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-env-gate-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        body_path = out_dir / "README-promo.md"
        body_path.write_text("# Launch draft\n\nPromotion copy.", encoding="utf-8")
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = "unit-test-github-token-secret"
        env.pop("I_APPROVE_PUBLISH", None)
        env["PUBLISH_DRY_RUN"] = "false"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "github",
                "--execute",
                "--approval",
                "I_APPROVE_PUBLISH",
                "--github-action",
                "file",
                "--github-repo",
                "hqwzhu/Viral-Product-Copy-Video-Generator",
                "--path",
                "PROMOTION.md",
                "--content-file",
                str(body_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report_text = report_path.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("I_APPROVE_PUBLISH=true", report["reason"])
        self.assertNotIn("unit-test-github-token-secret", report_text)
        audit_path = out_dir / "reports/promotion-manager/publish-results/publish-audit-log.jsonl"
        audit = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(audit[-1]["status"], "blocked")

    def test_publish_executor_youtube_dry_run_uses_oauth_boundary(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-youtube-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"not a real video but enough for dry-run")
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "youtube",
                "--video-file",
                str(video_path),
                "--title",
                "Launch draft",
                "--description",
                "Promotion video draft.",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["platform"], "youtube")
        self.assertEqual(report["officialApi"], "YouTube Data API videos.insert")
        self.assertEqual(report["request"]["endpoint"], "youtube.videos.insert(part=snippet,status)")
        self.assertEqual(report["request"]["clientLibrary"], "google-api-python-client")
        self.assertNotIn("YOUTUBE_OAUTH_ACCESS_TOKEN", json.dumps(report))
        self.assertEqual(report["publishPreview"]["privacyStatus"], "private")

    def test_publish_executor_youtube_loads_env_file_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-youtube-env-file-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"not a real video but enough for dry-run")
        env_file = out_dir / ".env"
        secret_value = "youtube-env-file-secret"
        env_file.write_text(
            "\n".join(
                [
                    f"YOUTUBE_OAUTH_ACCESS_TOKEN={secret_value}",
                    "YOUTUBE_CATEGORY_ID=28",
                    "YOUTUBE_CHANNEL_ID=channel-from-env-file",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.pop("YOUTUBE_ACCESS_TOKEN", None)
        env.pop("YOUTUBE_OAUTH_ACCESS_TOKEN", None)
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--env-file",
                str(env_file),
                "--platform",
                "youtube",
                "--video-file",
                str(video_path),
                "--title",
                "Launch draft",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_text = (out_dir / "reports/promotion-manager/publish-results/publish-execution.json").read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["credentialStatus"], "present")
        self.assertIn("YOUTUBE_OAUTH_ACCESS_TOKEN", report["envLoad"]["loadedKeys"])
        self.assertEqual(report["publishPreview"]["expectedAccount"], "channel-from-env-file")
        self.assertNotIn(secret_value, report_text)

    def test_youtube_credential_check_reports_blank_aliases_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="youtube-credential-check-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env_file = out_dir / ".env"
        env_file.write_text(
            "\n".join(
                [
                    "YOUTUBE_CLIENT_ID=",
                    "YOUTUBE_CLIENT_SECRET=",
                    "YOUTUBE_ACCESS_TOKEN=",
                    "YOUTUBE_REFRESH_TOKEN=",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        for name in [
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_ACCESS_TOKEN",
            "YOUTUBE_OAUTH_ACCESS_TOKEN",
            "YOUTUBE_REFRESH_TOKEN",
        ]:
            env.pop(name, None)
        subprocess.run(
            [
                sys.executable,
                str(YOUTUBE_CREDENTIAL_CHECK),
                "--env-file",
                str(env_file),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_text = (out_dir / "reports/promotion-manager/capability/youtube-credential-check.json").read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["status"], "blocked_missing_or_blank_youtube_credentials")
        self.assertEqual(report["credentialGroups"]["oauthClientId"]["state"], "blank")
        self.assertEqual(report["credentialGroups"]["oauthClientSecret"]["state"], "blank")
        self.assertEqual(report["credentialGroups"]["uploadAccessToken"]["state"], "blank")
        self.assertIn("YOUTUBE_CLIENT_ID", report["credentialGroups"]["oauthClientId"]["blankEnv"])
        self.assertFalse(report["readiness"]["dryRunUploadPortReady"])

    def test_youtube_credential_check_env_file_overrides_blank_process_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="youtube-credential-check-blank-env-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        env_file = out_dir / ".env"
        env_file.write_text(
            "\n".join(
                [
                    "YOUTUBE_CLIENT_ID=client-id-test.apps.googleusercontent.com",
                    "YOUTUBE_CLIENT_SECRET=client-secret-test",
                    "YOUTUBE_ACCESS_TOKEN=access-token-test",
                    "YOUTUBE_REFRESH_TOKEN=refresh-token-test",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        for name in [
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "YOUTUBE_OAUTH_ACCESS_TOKEN",
            "YOUTUBE_OAUTH_REFRESH_TOKEN",
        ]:
            env.pop(name, None)
        env["YOUTUBE_CLIENT_ID"] = ""
        env["YOUTUBE_CLIENT_SECRET"] = ""
        env["YOUTUBE_ACCESS_TOKEN"] = ""
        env["YOUTUBE_REFRESH_TOKEN"] = ""
        subprocess.run(
            [
                sys.executable,
                str(YOUTUBE_CREDENTIAL_CHECK),
                "--env-file",
                str(env_file),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_text = (out_dir / "reports/promotion-manager/capability/youtube-credential-check.json").read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["status"], "ready_oauth_flow_and_access_token_present")
        self.assertEqual(report["credentialGroups"]["oauthClientId"]["state"], "ready")
        self.assertEqual(report["credentialGroups"]["oauthClientSecret"]["state"], "ready")
        self.assertEqual(report["credentialGroups"]["uploadAccessToken"]["state"], "ready")
        self.assertTrue(report["readiness"]["dryRunUploadPortReady"])
        self.assertNotIn("client-secret-test", report_text)
        self.assertNotIn("access-token-test", report_text)

    def test_publish_executor_youtube_accepts_access_token_alias_before_gate(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-youtube-env-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"not a real video but enough for blocked execute")
        env = os.environ.copy()
        env["YOUTUBE_ACCESS_TOKEN"] = "oauth-unit-test-secret"
        env.pop("I_APPROVE_PUBLISH", None)
        env["PUBLISH_DRY_RUN"] = "false"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "youtube",
                "--execute",
                "--approval",
                "I_APPROVE_PUBLISH",
                "--video-file",
                str(video_path),
                "--title",
                "Launch draft",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report_text = report_path.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["credentialStatus"], "present")
        self.assertEqual(report["status"], "blocked")
        self.assertIn("I_APPROVE_PUBLISH=true", report["reason"])
        self.assertNotIn("oauth-unit-test-secret", report_text)

    def test_publish_executor_douyin_dry_run_uses_official_upload_and_create_boundary(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-douyin-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"not a real video but enough for dry-run")
        env = os.environ.copy()
        secret_value = "act.super-secret-douyin-token"
        env["DOUYIN_ACCESS_TOKEN"] = secret_value
        env["DOUYIN_OPEN_ID"] = "open-id-for-test"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "douyin",
                "--douyin-video-file",
                str(video_path),
                "--title",
                "Launch draft #AI",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(report["platform"], "douyin")
        self.assertEqual(report["officialApi"], "Douyin Open Platform video upload/create")
        self.assertEqual(report["request"]["upload"]["endpoint"], "/api/douyin/v1/video/upload_video/")
        self.assertEqual(report["request"]["create"]["endpoint"], "/api/douyin/v1/video/create_video/")
        self.assertEqual(report["request"]["create"]["body"]["text"], "Launch draft #AI")
        self.assertTrue(report["approvalRequired"])

    def test_publish_executor_douyin_execute_requires_user_authorized_credentials(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-executor-douyin-blocked-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"not a real video but enough for blocked execute")
        env = os.environ.copy()
        for name in ["DOUYIN_ACCESS_TOKEN", "DOUYIN_OPEN_ID"]:
            env.pop(name, None)
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_EXECUTOR),
                "--platform",
                "douyin",
                "--execute",
                "--approval",
                "I_APPROVE_PUBLISH",
                "--douyin-video-file",
                str(video_path),
                "--title",
                "Launch draft #AI",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/publish-execution.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("DOUYIN_ACCESS_TOKEN", report["reason"])
        self.assertIn("DOUYIN_OPEN_ID", report["reason"])

    def test_publish_executor_douyin_parses_nested_official_response_ids(self) -> None:
        module = load_script_module(PUBLISH_EXECUTOR)
        upload_payload = {"data": {"error_code": 0, "video": {"video_id": "video-123"}}}
        create_payload = {"data": {"error_code": 0, "item": {"item_id": "item-456"}, "share_id": "share-789"}}

        upload = module.douyin_result_from_payload(upload_payload, 200, ("video_id",))
        create = module.douyin_result_from_payload(create_payload, 200, ("item_id", "share_id"))

        self.assertEqual(upload["videoId"], "video-123")
        self.assertEqual(create["itemId"], "item-456")
        self.assertEqual(create["shareId"], "share-789")

    def test_publish_queue_builds_official_dry_runs_and_manual_tasks(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-queue-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        workflow_out = out_dir / "output"
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--skip-video",
                "--out-dir",
                str(workflow_out),
            ],
            check=True,
            cwd=ROOT,
        )
        video_path = out_dir / "youtube-draft.mp4"
        video_path.write_bytes(b"dry-run video placeholder")
        manifest_path = workflow_out / "reports/promotion-manager/agent-run/workflow-manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_QUEUE),
                "--workflow-manifest",
                str(manifest_path),
                "--promotion-out-dir",
                str(workflow_out),
                "--out-dir",
                str(workflow_out),
                "--github-repo",
                "hqwzhu/Viral-Product-Copy-Video-Generator",
                "--github-path",
                "PROMOTION.md",
                "--youtube-video-file",
                str(video_path),
            ],
            check=True,
            cwd=ROOT,
        )
        queue_path = workflow_out / "reports/promotion-manager/publish-queue/publish-queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        by_platform = {item["platform"]: item for item in queue["records"]}
        self.assertEqual(by_platform["github"]["status"], "dry_run")
        self.assertEqual(by_platform["youtube"]["status"], "dry_run")
        self.assertEqual(by_platform["xiaohongshu"]["status"], "queued_manual")
        self.assertEqual(by_platform["zhihu"]["status"], "queued_manual")
        self.assertEqual(by_platform["douyin"]["status"], "queued_browser_assisted")
        self.assertIn("utm_content", by_platform["xiaohongshu"]["trackingPlan"]["utm"])
        draft_text = Path(by_platform["xiaohongshu"]["contentDraft"]).read_text(encoding="utf-8")
        self.assertIn("## Tracking Plan", draft_text)
        self.assertIn("utm_content", draft_text)
        self.assertIn("## Media Assets", draft_text)
        self.assertIn("## First Batch", draft_text)
        self.assertTrue(by_platform["xiaohongshu"]["assets"])
        self.assertTrue(Path(by_platform["xiaohongshu"]["cover"]["path"]).exists())
        self.assertTrue(by_platform["xiaohongshu"]["detailImages"])
        self.assertTrue(Path(by_platform["github"]["officialExecution"]["report"]).exists())
        self.assertTrue(Path(by_platform["youtube"]["officialExecution"]["report"]).exists())
        self.assertTrue(Path(by_platform["xiaohongshu"]["contentDraft"]).exists())
        published_items_path = workflow_out / "reports/promotion-manager/published-items/published-items.json"
        self.assertTrue(published_items_path.exists())
        published_items = json.loads(published_items_path.read_text(encoding="utf-8"))
        self.assertEqual(published_items["summary"]["published"], 0)
        self.assertEqual(published_items["summary"]["pending"], 5)
        serialized = json.dumps(queue)
        self.assertNotIn("GITHUB_TOKEN", serialized)
        self.assertNotIn("YOUTUBE_OAUTH_ACCESS_TOKEN", serialized)

    def test_publish_queue_keeps_douyin_browser_assisted_when_video_file_supplied(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-queue-douyin-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        workflow_out = out_dir / "output"
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "douyin",
                "--skip-video",
                "--out-dir",
                str(workflow_out),
            ],
            check=True,
            cwd=ROOT,
        )
        video_path = out_dir / "douyin-draft.mp4"
        video_path.write_bytes(b"dry-run douyin video placeholder")
        manifest_path = workflow_out / "reports/promotion-manager/agent-run/workflow-manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_QUEUE),
                "--workflow-manifest",
                str(manifest_path),
                "--promotion-out-dir",
                str(workflow_out),
                "--out-dir",
                str(workflow_out),
                "--douyin-video-file",
                str(video_path),
            ],
            check=True,
            cwd=ROOT,
        )
        queue_path = workflow_out / "reports/promotion-manager/publish-queue/publish-queue.json"
        queue_text = queue_path.read_text(encoding="utf-8")
        queue = json.loads(queue_text)
        record = queue["records"][0]
        self.assertEqual(record["platform"], "douyin")
        self.assertEqual(record["status"], "queued_browser_assisted")
        self.assertEqual(record["publishMode"], "browser_assisted_publish")
        self.assertEqual(record["video"]["path"], str(video_path))
        self.assertEqual(record["video"]["status"], "ready")
        self.assertNotIn("officialExecution", record)
        self.assertNotIn("DOUYIN_ACCESS_TOKEN", queue_text)
        self.assertNotIn("DOUYIN_OPEN_ID", queue_text)

    def test_browser_publish_assistant_prepares_payloads_and_registers_real_url(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="browser-publish-assistant-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        queue_dir = out_dir / "reports/promotion-manager/publish-queue"
        drafts_dir = queue_dir / "drafts"
        drafts_dir.mkdir(parents=True)
        xhs_draft = drafts_dir / "xiaohongshu-draft.md"
        xhs_draft.write_text(
            "\n".join(
                [
                    "# xiaohongshu Publish Draft",
                    "",
                    "- Title: 3 steps to launch AI content",
                    "- CTA: Try the product",
                    "- Cover text: Launch faster",
                    "- Tags: #AI #ProductLaunch",
                    "",
                    "## Description",
                    "",
                    "Use this tool to turn one product URL into a promotion pack.",
                ]
            ),
            encoding="utf-8",
        )
        douyin_draft = drafts_dir / "douyin-draft.md"
        douyin_draft.write_text(
            "\n".join(
                [
                    "# douyin Publish Draft",
                    "",
                    "- Title: AI launch script",
                    "- Tags: #AI #工具",
                    "",
                    "## shortVideoScript",
                    "",
                    "Hook, proof, demo, CTA.",
                ]
            ),
            encoding="utf-8",
        )
        queue_path = queue_dir / "publish-queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "status": "queued_manual",
                            "publishMode": "manual_publish_required",
                            "contentDraft": str(xhs_draft),
                            "trackingPlan": {
                                "trackedUrl": "https://example.com/product?utm_source=xiaohongshu&utm_medium=social&utm_campaign=launch&utm_content=launch-xhs",
                                "utm": {
                                    "utm_source": "xiaohongshu",
                                    "utm_medium": "social",
                                    "utm_campaign": "launch",
                                    "utm_content": "launch-xhs",
                                },
                            },
                        },
                        {
                            "platform": "douyin",
                            "status": "queued_browser_assisted",
                            "publishMode": "browser_assisted_publish",
                            "contentDraft": str(douyin_draft),
                        },
                        {
                            "platform": "github",
                            "status": "dry_run",
                            "publishMode": "official_api_publish",
                            "contentDraft": "",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(BROWSER_PUBLISH_ASSISTANT),
                "--publish-queue",
                str(queue_path),
                "--platform-publish-url",
                "xiaohongshu=https://creator.example.test/publish",
                "--published-url",
                "xiaohongshu=https://www.xiaohongshu.com/explore/note123",
                "--evidence",
                "xhs-published.png",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/browser-publish/browser-publish-assistant.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["prepared"], 2)
        self.assertEqual(report["summary"]["registeredPublishedUrls"], 1)
        by_platform = {item["platform"]: item for item in report["records"]}
        self.assertEqual(by_platform["xiaohongshu"]["publisherUrl"], "https://creator.example.test/publish")
        self.assertTrue(Path(by_platform["xiaohongshu"]["payloadFiles"]["clipboard"]).exists())
        self.assertEqual(
            by_platform["xiaohongshu"]["payload"]["trackedUrl"],
            "https://example.com/product?utm_source=xiaohongshu&utm_medium=social&utm_campaign=launch&utm_content=launch-xhs",
        )
        clipboard = Path(by_platform["xiaohongshu"]["payloadFiles"]["clipboard"]).read_text(encoding="utf-8")
        self.assertIn("Tracked URL:", clipboard)
        self.assertIn("First batch:", clipboard)
        self.assertIn("Media assets:", clipboard)
        self.assertTrue(Path(by_platform["douyin"]["payloadFiles"]["formFillScript"]).exists())
        self.assertIn("browser_publish_form_fill.py", by_platform["douyin"]["browserFormFill"]["command"])
        self.assertTrue(Path(by_platform["douyin"]["browserFormFill"]["payloadJson"]).exists())
        self.assertTrue(by_platform["douyin"]["finalPublishUserActionRequired"])
        published = json.loads((out_dir / "reports/promotion-manager/published-items/published-items.json").read_text(encoding="utf-8"))
        self.assertEqual(published["summary"]["published"], 1)
        self.assertEqual(published["records"][0]["publishedUrl"], "https://www.xiaohongshu.com/explore/note123")
        self.assertTrue((out_dir / "reports/promotion-manager/browser-publish/browser-publish-assistant.md").exists())

    def test_browser_publish_form_fill_fills_visible_form_without_submit(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="browser-publish-form-fill-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "publish.html").write_text(
            """<!doctype html>
<html>
<head><title>Creator Publish Form</title></head>
<body>
  <form id="publish-form">
    <input name="title" placeholder="Title">
    <textarea name="body" placeholder="Body"></textarea>
    <input name="tags" placeholder="Tags">
    <input name="cover" placeholder="Cover">
    <button id="publish" type="submit">Publish</button>
  </form>
  <script>
    document.querySelector('#publish-form').addEventListener('submit', (event) => {
      event.preventDefault();
      document.body.dataset.submitted = 'yes';
    });
  </script>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        payload_path = out_dir / "payload.json"
        payload_path.write_text(
            json.dumps(
                {
                    "platform": "xiaohongshu",
                    "publisherUrl": f"http://127.0.0.1:{server.server_address[1]}/publish.html",
                    "payload": {
                        "title": "3 steps to launch AI content",
                        "body": "Use one product URL to prepare platform-native launch content.",
                        "tags": ["#AI", "#ProductLaunch"],
                        "coverText": "Launch faster",
                    },
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(BROWSER_PUBLISH_FORM_FILL),
                "--payload-json",
                str(payload_path),
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report = json.loads((out_dir / "reports/promotion-manager/browser-publish/browser-form-fill.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertFalse(report["submitted"])
        self.assertTrue(report["finalPublishUserActionRequired"])
        filled = {item["field"]: item for item in report["filledFields"]}
        self.assertEqual(filled["title"]["value"], "3 steps to launch AI content")
        self.assertEqual(filled["body"]["value"], "Use one product URL to prepare platform-native launch content.")
        self.assertIn("#AI", filled["tags"]["value"])
        self.assertEqual(filled["coverText"]["value"], "Launch faster")
        self.assertTrue(Path(report["artifacts"]["screenshot"]).exists())
        self.assertTrue((out_dir / "reports/promotion-manager/browser-publish/browser-form-fill.md").exists())

    def test_browser_publish_session_runs_payloads_and_form_fill_without_submit(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="browser-publish-session-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        site_dir = out_dir / "site"
        site_dir.mkdir()
        (site_dir / "publish.html").write_text(
            """<!doctype html>
<html>
<head><title>Creator Publish Form</title></head>
<body>
  <form id="publish-form">
    <input name="title" placeholder="Title">
    <textarea name="body" placeholder="Body"></textarea>
    <input name="tags" placeholder="Tags">
    <input name="cover" placeholder="Cover">
    <button id="publish" type="submit">Publish</button>
  </form>
  <script>
    document.querySelector('#publish-form').addEventListener('submit', (event) => {
      event.preventDefault();
      document.body.dataset.submitted = 'yes';
    });
  </script>
</body>
</html>""",
            encoding="utf-8",
        )

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(site_dir), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.addCleanup(stop_server)
        queue_dir = out_dir / "reports/promotion-manager/publish-queue"
        drafts_dir = queue_dir / "drafts"
        drafts_dir.mkdir(parents=True)
        draft_path = drafts_dir / "xiaohongshu-draft.md"
        draft_path.write_text(
            "\n".join(
                [
                    "# xiaohongshu Publish Draft",
                    "",
                    "- Title: 3 steps to launch AI content",
                    "- CTA: Try the product",
                    "- Cover text: Launch faster",
                    "- Tags: #AI #ProductLaunch",
                    "",
                    "## Description",
                    "",
                    "Use one product URL to prepare platform-native launch content.",
                ]
            ),
            encoding="utf-8",
        )
        queue_path = queue_dir / "publish-queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "xiaohongshu",
                            "status": "queued_browser_assisted",
                            "publishMode": "browser_assisted_publish",
                            "contentDraft": str(draft_path),
                            "trackingPlan": {
                                "trackedUrl": "https://example.com/product?utm_source=xiaohongshu&utm_medium=social&utm_campaign=launch&utm_content=launch-xhs"
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        publisher_url = f"http://127.0.0.1:{server.server_address[1]}/publish.html"
        subprocess.run(
            [
                sys.executable,
                str(BROWSER_PUBLISH_SESSION),
                "--publish-queue",
                str(queue_path),
                "--platforms",
                "xiaohongshu",
                "--platform-publish-url",
                f"xiaohongshu={publisher_url}",
                "--run-form-fill",
                "--allow-localhost",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )
        report_path = out_dir / "reports/promotion-manager/browser-publish-session/browser-publish-session.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready_form_fill_completed")
        self.assertEqual(report["summary"]["payloadsPrepared"], 1)
        self.assertEqual(report["summary"]["formFillReady"], 1)
        self.assertEqual(report["summary"]["submitted"], 0)
        self.assertEqual(report["summary"]["finalPublishUserActionRequired"], 1)
        self.assertTrue(Path(report["assistant"]["report"]).exists())
        record = report["records"][0]
        self.assertEqual(record["platform"], "xiaohongshu")
        self.assertTrue(Path(record["payloadJson"]).exists())
        self.assertTrue(Path(record["clipboard"]).exists())
        self.assertIn("published_items.py", record["registerPublishedUrlCommand"])
        self.assertIn("publish_url_capture.py", record["capturePublishedUrlCommand"])
        self.assertEqual(record["formFill"]["status"], "ready")
        self.assertFalse(record["formFill"]["submitted"])
        self.assertTrue(record["formFill"]["finalPublishUserActionRequired"])
        self.assertTrue(Path(record["formFill"]["report"]).exists())
        self.assertTrue(Path(record["formFill"]["screenshot"]).exists())
        filled = {item["field"]: item for item in record["formFill"]["filledFields"]}
        self.assertEqual(filled["title"]["value"], "3 steps to launch AI content")
        self.assertIn("Use one product URL", filled["body"]["value"])
        self.assertIn("real_evidence_inbox.py", report["postPublish"]["realEvidenceInboxCommand"])
        self.assertTrue((out_dir / "reports/promotion-manager/browser-publish-session/browser-publish-session.md").exists())

    def test_publish_readiness_runner_audits_queue_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-readiness-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        workflow_out = out_dir / "output"
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "youtube,zhihu,xiaohongshu,douyin,github",
                "--skip-video",
                "--out-dir",
                str(workflow_out),
            ],
            check=True,
            cwd=ROOT,
        )
        video_path = out_dir / "youtube-draft.mp4"
        video_path.write_bytes(b"dry-run video placeholder")
        env = os.environ.copy()
        secret_value = "fake-gh-token-for-readiness-test"
        for name in [
            "YOUTUBE_ACCESS_TOKEN",
            "YOUTUBE_OAUTH_ACCESS_TOKEN",
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "DOUYIN_CLIENT_KEY",
            "DOUYIN_CLIENT_SECRET",
            "DOUYIN_ACCESS_TOKEN",
            "DOUYIN_OPEN_ID",
        ]:
            env.pop(name, None)
        env["GITHUB_TOKEN"] = secret_value
        manifest_path = workflow_out / "reports/promotion-manager/agent-run/workflow-manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_READINESS),
                "--workflow-manifest",
                str(manifest_path),
                "--build-queue",
                "--github-repo",
                "hqwzhu/Viral-Product-Copy-Video-Generator",
                "--youtube-video-file",
                str(video_path),
                "--out-dir",
                str(workflow_out),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = workflow_out / "reports/promotion-manager/publish-readiness/publish-readiness.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "partial_ready")
        by_platform = {item["platform"]: item for item in report["records"]}
        self.assertEqual(by_platform["github"]["readiness"], "dry_run_ready")
        self.assertEqual(by_platform["github"]["credentialStatus"]["presentEnv"], ["GITHUB_TOKEN"])
        self.assertEqual(by_platform["youtube"]["readiness"], "missing_credentials")
        self.assertEqual(by_platform["zhihu"]["readiness"], "manual_publish_required")
        self.assertEqual(by_platform["xiaohongshu"]["readiness"], "manual_publish_required")
        self.assertEqual(by_platform["douyin"]["readiness"], "browser_assisted_publish_ready")
        self.assertTrue(Path(report["inputs"]["publishQueue"]).exists())
        self.assertTrue((workflow_out / "reports/promotion-manager/publish-readiness/publish-readiness.md").exists())

    def test_publish_setup_assistant_builds_env_template_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-setup-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        readiness_dir = out_dir / "reports/promotion-manager/publish-readiness"
        readiness_dir.mkdir(parents=True)
        queue_path = out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"
        queue_path.parent.mkdir(parents=True)
        queue_path.write_text('{"records":[]}\n', encoding="utf-8")
        secret_value = "fake-secret-that-must-not-appear"
        readiness_path = readiness_dir / "publish-readiness.json"
        readiness_path.write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-08",
                    "status": "partial_ready",
                    "inputs": {
                        "publishQueue": str(queue_path),
                        "githubRepo": "owner/repo",
                        "youtubeVideoFile": "./youtube.mp4",
                        "douyinVideoFile": "./douyin.mp4",
                    },
                    "records": [
                        {
                            "platform": "youtube",
                            "publishMode": "official_api_publish",
                            "readiness": "missing_credentials",
                            "credentialStatus": {
                                "requiredAny": ["YOUTUBE_ACCESS_TOKEN", "YOUTUBE_OAUTH_ACCESS_TOKEN"],
                                "alternativeAll": ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"],
                                "alternativeGroups": [
                                    ["GOOGLE_OAUTH_CLIENT_ID", "YOUTUBE_CLIENT_ID"],
                                    ["GOOGLE_OAUTH_CLIENT_SECRET", "YOUTUBE_CLIENT_SECRET"],
                                ],
                                "missingEnv": [
                                    "YOUTUBE_ACCESS_TOKEN",
                                    "YOUTUBE_OAUTH_ACCESS_TOKEN",
                                    "GOOGLE_OAUTH_CLIENT_ID or YOUTUBE_CLIENT_ID",
                                    "GOOGLE_OAUTH_CLIENT_SECRET or YOUTUBE_CLIENT_SECRET",
                                ],
                                "presentEnv": [],
                                "valuesStored": False,
                            },
                            "targetStatus": {"ready": True, "field": "youtubeVideoFile", "missing": ""},
                            "approvalStatus": {"required": True, "approvalProvided": False},
                            "nextAction": "Set required YouTube OAuth environment variables.",
                        },
                        {
                            "platform": "xiaohongshu",
                            "publishMode": "manual_publish_required",
                            "readiness": "manual_publish_required",
                            "credentialStatus": {"missingEnv": [], "presentEnv": [], "valuesStored": False},
                            "targetStatus": {"ready": True, "field": "", "missing": ""},
                            "approvalStatus": {"required": True, "approvalProvided": False},
                            "nextAction": "Use browser-assisted publishing.",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_SETUP_ASSISTANT),
                "--publish-readiness",
                str(readiness_path),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env={**os.environ, "YOUTUBE_OAUTH_ACCESS_TOKEN": secret_value},
        )

        report_path = out_dir / "reports/promotion-manager/publish-setup/publish-setup.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["credentialEnvNames"], 6)
        by_platform = {item["platform"]: item for item in report["records"]}
        self.assertEqual(by_platform["youtube"]["setupCategory"], "credential_setup_required")
        self.assertEqual(by_platform["xiaohongshu"]["setupCategory"], "browser_or_manual_publish")
        self.assertIn("executeWhenReady", by_platform["youtube"]["commands"])
        self.assertIn("prepareBrowserPublish", by_platform["xiaohongshu"]["commands"])
        env_template = Path(report["artifacts"]["envTemplate"])
        env_text = env_template.read_text(encoding="utf-8")
        self.assertIn("YOUTUBE_OAUTH_ACCESS_TOKEN=", env_text)
        self.assertIn("GOOGLE_OAUTH_CLIENT_ID=", env_text)
        self.assertIn("YOUTUBE_CLIENT_ID=", env_text)
        self.assertIn("YOUTUBE_CLIENT_SECRET=", env_text)
        self.assertNotIn(secret_value, env_text)
        self.assertTrue(Path(report["artifacts"]["checklist"]).exists())
        platform_guide_json = Path(report["artifacts"]["platformSetupGuideJson"])
        platform_guide_text = platform_guide_json.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, platform_guide_text)
        platform_guides = json.loads(platform_guide_text)
        guide_by_platform = {item["platform"]: item for item in platform_guides}
        self.assertEqual(guide_by_platform["youtube"]["automationStatus"], "official_executor_integrated")
        self.assertIn("YouTube videos.insert", json.dumps(guide_by_platform["youtube"], ensure_ascii=False))
        self.assertIn("YOUTUBE_OAUTH_ACCESS_TOKEN", guide_by_platform["youtube"]["credentialEnvNames"])
        self.assertIn("YOUTUBE_CLIENT_ID", guide_by_platform["youtube"]["credentialEnvNames"])
        self.assertEqual(
            guide_by_platform["xiaohongshu"]["automationStatus"],
            "browser_or_manual_until_official_publish_access_verified",
        )
        self.assertTrue(Path(report["artifacts"]["platformSetupGuide"]).exists())
        self.assertTrue((out_dir / "reports/promotion-manager/publish-setup/publish-setup.md").exists())

    def test_real_evidence_setup_builds_templates_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="real-evidence-setup-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        queue_path = out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"
        queue_path.parent.mkdir(parents=True)
        draft_path = out_dir / "youtube-draft.md"
        draft_path.write_text("- Title: YouTube launch draft\n", encoding="utf-8")
        secret_value = "fake-secret-that-must-not-appear-in-evidence-templates"
        queue_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "youtube",
                            "status": "dry_run",
                            "publishMode": "official_api_publish",
                            "contentDraft": str(draft_path),
                            "trackingPlan": {
                                "trackedUrl": "https://example.com/ai-prompt-kit?utm_campaign=launch&utm_content=yt-001",
                                "campaignId": "launch",
                                "contentId": "yt-001",
                                "utm": {
                                    "utm_source": "youtube",
                                    "utm_medium": "video",
                                    "utm_campaign": "launch",
                                    "utm_content": "yt-001",
                                },
                            },
                        },
                        {
                            "platform": "xiaohongshu",
                            "status": "browser_assisted_publish",
                            "publishMode": "browser_assisted_publish",
                            "title": "\u5c0f\u7ea2\u4e66\u53d1\u5e03\u7b14\u8bb0",
                            "trackingPlan": {
                                "trackedUrl": "https://example.com/ai-prompt-kit?utm_campaign=launch&utm_content=xhs-001",
                                "campaignId": "launch",
                                "contentId": "xhs-001",
                                "utm": {
                                    "utm_source": "xiaohongshu",
                                    "utm_medium": "social",
                                    "utm_campaign": "launch",
                                    "utm_content": "xhs-001",
                                },
                            },
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [sys.executable, str(REAL_EVIDENCE_SETUP), "--publish-queue", str(queue_path), "--out-dir", str(out_dir)],
            check=True,
            cwd=ROOT,
            env={**os.environ, "GITHUB_TOKEN": secret_value},
        )

        report_path = out_dir / "reports/promotion-manager/real-evidence-setup/real-evidence-setup.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        self.assertTrue(report_text.isascii())
        report = json.loads(report_text)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["targets"], 2)
        self.assertEqual(report["summary"]["trackedUrls"], 2)
        by_platform = {item["platform"]: item for item in report["records"]}
        self.assertEqual(by_platform["youtube"]["title"], "YouTube launch draft")
        self.assertEqual(by_platform["youtube"]["trackingPlan"]["utm_content"], "yt-001")
        self.assertEqual(by_platform["xiaohongshu"]["title"], "\u5c0f\u7ea2\u4e66\u53d1\u5e03\u7b14\u8bb0")
        self.assertEqual(by_platform["xiaohongshu"]["trackingPlan"]["utm_source"], "xiaohongshu")
        for path in report["artifacts"].values():
            self.assertTrue(Path(path).exists(), path)
            self.assertNotIn(secret_value, Path(path).read_text(encoding="utf-8-sig"))
        metrics_template = Path(report["artifacts"]["platformMetricsTemplate"]).read_text(encoding="utf-8-sig")
        business_template = Path(report["artifacts"]["businessAttributionTemplate"]).read_text(encoding="utf-8-sig")
        self.assertIn("views", metrics_template)
        self.assertIn("likes", metrics_template)
        self.assertIn("orders", metrics_template)
        self.assertIn("revenue", metrics_template)
        self.assertIn("utm_content", business_template)
        self.assertIn("xhs-001", business_template)

    def test_real_evidence_inbox_setup_creates_fillable_inbox_without_fake_metrics(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="real-evidence-inbox-setup-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        inbox_dir = out_dir / "evidence-inbox"

        subprocess.run(
            [
                sys.executable,
                str(REAL_EVIDENCE_INBOX_SETUP),
                "--product-url",
                "https://example.com/ai-prompt-kit",
                "--product-name",
                "AI Prompt Kit",
                "--platforms",
                "youtube,xiaohongshu,github",
                "--published-url",
                "github=https://github.com/example/ai-prompt-kit",
                "--inbox-dir",
                str(inbox_dir),
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "reports/promotion-manager/real-evidence-inbox-setup/real-evidence-inbox-setup.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["summary"]["platforms"], 3)
        self.assertEqual(report["summary"]["publishedUrlsSeeded"], 1)
        self.assertEqual(report["summary"]["realMetricsSeeded"], 0)
        self.assertEqual(report["summary"]["realOrdersSeeded"], 0)
        self.assertEqual(report["summary"]["realRevenueSeeded"], 0)
        artifacts = {key: Path(value["path"]) for key, value in report["artifacts"].items()}
        for path in artifacts.values():
            self.assertTrue(path.exists(), path)
        manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"], "real_evidence_inbox_setup")
        self.assertNotIn("metricsStructuredJson", manifest["evidence"])
        metrics_csv = artifacts["metricsCsv"].read_text(encoding="utf-8-sig")
        orders_csv = artifacts["ordersCsv"].read_text(encoding="utf-8-sig")
        comments_text = artifacts["commentsText"].read_text(encoding="utf-8")
        self.assertIn("views", metrics_csv)
        self.assertEqual(len([line for line in metrics_csv.splitlines() if line.strip()]), 1)
        self.assertIn("revenue", orders_csv)
        self.assertEqual(len([line for line in orders_csv.splitlines() if line.strip()]), 1)
        self.assertEqual(comments_text, "")
        self.assertIn("real_evidence_inbox.py", artifacts["importCommands"].read_text(encoding="utf-8"))
        example = json.loads(artifacts["structuredMetricsExample"].read_text(encoding="utf-8"))
        self.assertTrue(example["exampleOnly"])
        self.assertTrue(example["doNotImportAsEvidence"])

        subprocess.run(
            [
                sys.executable,
                str(REAL_EVIDENCE_INBOX),
                "--inbox-dir",
                str(inbox_dir),
                "--out-dir",
                str(out_dir),
                "--skip-post-publish-capture",
            ],
            check=True,
            cwd=ROOT,
        )
        inbox_report = json.loads((out_dir / "reports/promotion-manager/real-evidence-inbox/real-evidence-inbox.json").read_text(encoding="utf-8"))
        ignored_sources = [item for item in inbox_report["sources"] if item.get("status") == "ignored_template_or_example"]
        self.assertTrue(any("structured-metrics-snapshot.example.json" in item["source"] for item in ignored_sources))
        self.assertEqual(inbox_report["discoveredEvidence"]["metricsStructuredJson"], [])
        business_report = json.loads((out_dir / "reports/promotion-manager/business-attribution/business-attribution.json").read_text(encoding="utf-8"))
        self.assertEqual(business_report["status"], "waiting_business_data")
        self.assertEqual(business_report["summary"]["totalOrders"], 0.0)
        self.assertEqual(business_report["summary"]["totalRevenue"], 0.0)

    def test_synthetic_evidence_generator_validates_recovery_without_real_claims(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="synthetic-evidence-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)

        subprocess.run(
            [
                sys.executable,
                str(SYNTHETIC_EVIDENCE_GENERATOR),
                "--product-url",
                "https://example.com/ai-prompt-kit",
                "--product-name",
                "AI Prompt Kit",
                "--platforms",
                "youtube,github",
                "--run-recovery",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
        )

        report_path = out_dir / "reports/promotion-manager/synthetic-evidence/synthetic-evidence.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "synthetic_validation_ready")
        self.assertTrue(report["synthetic"])
        self.assertEqual(report["warning"], "SYNTHETIC_DEMO_DATA_DO_NOT_REPORT")
        self.assertEqual(report["summary"]["platforms"], 2)
        self.assertEqual(report["summary"]["recoveryExitCode"], 0)
        for path in report["artifacts"].values():
            self.assertTrue(Path(path).exists(), path)
            self.assertIn("synthetic", Path(path).read_text(encoding="utf-8-sig", errors="replace").lower())
        self.assertTrue(Path(report["recovery"]["reports"]["realEvidenceInbox"]).exists())
        self.assertTrue(Path(report["recovery"]["reports"]["metricsRecovery"]).exists())
        self.assertTrue(Path(report["recovery"]["reports"]["nextRoundOptimization"]).exists())
        report_markdown = (out_dir / "reports/promotion-manager/synthetic-evidence/synthetic-evidence.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("SYNTHETIC_DEMO_DATA_DO_NOT_REPORT", report_markdown)
        self.assertIn("must not be reported as real performance", report_markdown)

    def test_launch_unlock_pack_orchestrates_external_gate_setup_without_secret_values(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="launch-unlock-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        queue_path = out_dir / "reports/promotion-manager/publish-queue/publish-queue.json"
        readiness_path = out_dir / "reports/promotion-manager/publish-readiness/publish-readiness.json"
        queue_path.parent.mkdir(parents=True)
        readiness_path.parent.mkdir(parents=True)
        youtube_draft = out_dir / "youtube-draft.md"
        xhs_draft = out_dir / "xhs-draft.md"
        youtube_draft.write_text("- Title: YouTube launch draft\n- Body: Launch copy\n", encoding="utf-8")
        xhs_draft.write_text("- Title: Xiaohongshu note draft\n- Body: Note copy\n", encoding="utf-8")
        secret_value = "secret-value-must-not-appear-in-launch-unlock"
        queue_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "platform": "youtube",
                            "status": "dry_run",
                            "publishMode": "official_api_publish",
                            "contentDraft": str(youtube_draft),
                            "trackingPlan": {
                                "trackedUrl": "https://example.com/?utm_source=youtube&utm_content=yt-001",
                                "contentId": "yt-001",
                                "utm": {"utm_source": "youtube", "utm_medium": "video", "utm_campaign": "launch", "utm_content": "yt-001"},
                            },
                        },
                        {
                            "platform": "xiaohongshu",
                            "status": "queued_manual",
                            "publishMode": "manual_publish_required",
                            "contentDraft": str(xhs_draft),
                            "trackingPlan": {
                                "trackedUrl": "https://example.com/?utm_source=xiaohongshu&utm_content=xhs-001",
                                "contentId": "xhs-001",
                                "utm": {"utm_source": "xiaohongshu", "utm_medium": "social", "utm_campaign": "launch", "utm_content": "xhs-001"},
                            },
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        readiness_path.write_text(
            json.dumps(
                {
                    "generatedAt": "2026-07-09",
                    "status": "partial_ready",
                    "inputs": {
                        "publishQueue": str(queue_path),
                        "youtubeVideoFile": "./youtube.mp4",
                    },
                    "records": [
                        {
                            "platform": "youtube",
                            "publishMode": "official_api_publish",
                            "readiness": "missing_credentials",
                            "credentialStatus": {
                                "requiredAny": ["YOUTUBE_ACCESS_TOKEN", "YOUTUBE_OAUTH_ACCESS_TOKEN"],
                                "alternativeAll": ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"],
                                "alternativeGroups": [
                                    ["GOOGLE_OAUTH_CLIENT_ID", "YOUTUBE_CLIENT_ID"],
                                    ["GOOGLE_OAUTH_CLIENT_SECRET", "YOUTUBE_CLIENT_SECRET"],
                                ],
                                "missingEnv": [
                                    "YOUTUBE_ACCESS_TOKEN",
                                    "YOUTUBE_OAUTH_ACCESS_TOKEN",
                                    "GOOGLE_OAUTH_CLIENT_ID or YOUTUBE_CLIENT_ID",
                                    "GOOGLE_OAUTH_CLIENT_SECRET or YOUTUBE_CLIENT_SECRET",
                                ],
                                "presentEnv": [],
                                "valuesStored": False,
                            },
                            "targetStatus": {"ready": True, "field": "youtubeVideoFile", "missing": ""},
                            "approvalStatus": {"required": True, "approvalProvided": False},
                            "nextAction": "Set required YouTube OAuth environment variables.",
                        },
                        {
                            "platform": "xiaohongshu",
                            "publishMode": "manual_publish_required",
                            "readiness": "manual_publish_required",
                            "credentialStatus": {"missingEnv": [], "presentEnv": [], "valuesStored": False},
                            "targetStatus": {"ready": True, "field": "", "missing": ""},
                            "approvalStatus": {"required": True, "approvalProvided": False},
                            "nextAction": "Use browser-assisted publishing.",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(LAUNCH_UNLOCK_PACK),
                "--publish-queue",
                str(queue_path),
                "--publish-readiness",
                str(readiness_path),
                "--platforms",
                "youtube,xiaohongshu",
                "--platform-publish-url",
                "xiaohongshu=https://creator.xiaohongshu.example/publish",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env={**os.environ, "YOUTUBE_OAUTH_ACCESS_TOKEN": secret_value},
        )

        report_path = out_dir / "reports/promotion-manager/launch-unlock/launch-unlock.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_value, report_text)
        report = json.loads(report_text)
        self.assertEqual(report["status"], "ready_unlock_pack")
        self.assertEqual(report["summary"]["gates"], 5)
        self.assertTrue(report["sourceReports"]["platformAccess"]["exists"])
        self.assertTrue(report["sourceReports"]["publishSetup"]["exists"])
        self.assertTrue(report["sourceReports"]["realEvidenceSetup"]["exists"])
        self.assertTrue(report["sourceReports"]["browserPublishAssistant"]["exists"])
        gate_ids = {item["id"] for item in report["gates"]}
        self.assertIn("publish_authorization", gate_ids)
        self.assertIn("browser_assisted_publish", gate_ids)
        self.assertIn("real_evidence_collection", gate_ids)
        command_purposes = {item["purpose"] for item in report["nextCommands"]}
        self.assertIn("browser_publish_session", command_purposes)
        self.assertIn("performance_monitor", command_purposes)
        browser_step = next(item for item in report["steps"] if item["name"] == "browser_publish_assistant")
        self.assertIn("--platform-publish-url", browser_step["command"])
        self.assertIn("xiaohongshu=https://creator.xiaohongshu.example/publish", browser_step["command"])
        self.assertTrue(Path(report["artifacts"]["checklist"]).exists())
        self.assertTrue(Path(report["artifacts"]["nextActionCommands"]).exists())
        self.assertTrue((out_dir / "reports/promotion-manager/launch-unlock/launch-unlock.md").exists())
        self.assertIn("YOUTUBE_OAUTH_ACCESS_TOKEN=", (out_dir / "reports/promotion-manager/publish-setup/publish-credentials.example.env").read_text(encoding="utf-8"))

    def test_publish_readiness_runner_audits_douyin_browser_assisted_target(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="publish-readiness-douyin-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        snapshot_path = out_dir / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "url": "https://example.com/ai-prompt-kit",
                    "title": "AI Prompt Kit",
                    "description": "Prompt templates for product copy, SEO content, and video scripts.",
                    "targetAudience": ["AI operators"],
                    "painPoints": ["Slow launch content"],
                }
            ),
            encoding="utf-8",
        )
        workflow_out = out_dir / "output"
        subprocess.run(
            [
                sys.executable,
                str(RUN_WORKFLOW),
                "--structured-json",
                str(snapshot_path),
                "--platforms",
                "douyin",
                "--skip-video",
                "--out-dir",
                str(workflow_out),
            ],
            check=True,
            cwd=ROOT,
        )
        video_path = out_dir / "douyin-draft.mp4"
        video_path.write_bytes(b"dry-run douyin video placeholder")
        env = os.environ.copy()
        for name in ["DOUYIN_CLIENT_KEY", "DOUYIN_CLIENT_SECRET", "DOUYIN_ACCESS_TOKEN", "DOUYIN_OPEN_ID"]:
            env.pop(name, None)
        manifest_path = workflow_out / "reports/promotion-manager/agent-run/workflow-manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_READINESS),
                "--workflow-manifest",
                str(manifest_path),
                "--build-queue",
                "--douyin-video-file",
                str(video_path),
                "--out-dir",
                str(workflow_out),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report = json.loads((workflow_out / "reports/promotion-manager/publish-readiness/publish-readiness.json").read_text(encoding="utf-8"))
        record = report["records"][0]
        self.assertEqual(record["platform"], "douyin")
        self.assertEqual(record["publishMode"], "browser_assisted_publish")
        self.assertEqual(record["readiness"], "browser_assisted_publish_ready")
        self.assertTrue(record["targetStatus"]["ready"])
        self.assertEqual(record["credentialStatus"]["missingEnv"], [])
        self.assertEqual(record["credentialStatus"]["requiredAll"], [])
        self.assertTrue(Path(report["inputs"]["publishQueue"]).exists())

    def test_youtube_oauth_publish_dry_run_generates_auth_url_without_tokens(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="youtube-oauth-publish-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"dry-run only")
        env = os.environ.copy()
        env["GOOGLE_OAUTH_CLIENT_ID"] = "client-id.apps.googleusercontent.com"
        env.pop("GOOGLE_OAUTH_CLIENT_SECRET", None)
        subprocess.run(
            [
                sys.executable,
                str(YOUTUBE_OAUTH_PUBLISH),
                "--video-file",
                str(video_path),
                "--title",
                "Launch draft",
                "--description",
                "Promotion video draft.",
                "--state",
                "test-state",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/youtube-oauth-publish.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "dry_run")
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", report["authUrl"])
        self.assertIn("youtube.upload", report["authUrl"])
        self.assertFalse(report["credentialStatus"]["tokensSaved"])
        self.assertNotIn("access_token", json.dumps(report))
        self.assertNotIn("GOOGLE_OAUTH_CLIENT_SECRET", json.dumps(report))

    def test_youtube_oauth_publish_accepts_youtube_client_id_alias(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="youtube-oauth-publish-alias-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"dry-run only")
        env = os.environ.copy()
        env.pop("GOOGLE_OAUTH_CLIENT_ID", None)
        env.pop("GOOGLE_OAUTH_CLIENT_SECRET", None)
        env["YOUTUBE_CLIENT_ID"] = "client-id.apps.googleusercontent.com"
        subprocess.run(
            [
                sys.executable,
                str(YOUTUBE_OAUTH_PUBLISH),
                "--video-file",
                str(video_path),
                "--title",
                "Launch draft",
                "--state",
                "test-state",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/youtube-oauth-publish.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "dry_run")
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", report["authUrl"])
        self.assertEqual(report["credentialStatus"]["clientId"], "present")

    def test_youtube_oauth_publish_execute_requires_client_secret(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="youtube-oauth-publish-blocked-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        video_path = out_dir / "draft.mp4"
        video_path.write_bytes(b"dry-run only")
        env = os.environ.copy()
        env["GOOGLE_OAUTH_CLIENT_ID"] = "client-id.apps.googleusercontent.com"
        env.pop("GOOGLE_OAUTH_CLIENT_SECRET", None)
        subprocess.run(
            [
                sys.executable,
                str(YOUTUBE_OAUTH_PUBLISH),
                "--execute",
                "--approval",
                "I_APPROVE_PUBLISH",
                "--video-file",
                str(video_path),
                "--title",
                "Launch draft",
                "--out-dir",
                str(out_dir),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        report_path = out_dir / "reports/promotion-manager/publish-results/youtube-oauth-publish.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("GOOGLE_OAUTH_CLIENT_SECRET", report["reason"])
        self.assertNotIn("accessToken", json.dumps(report))

    def test_video_renderer_creates_mp4_when_ffmpeg_exists(self) -> None:
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg is not installed")
        out_dir = self.run_all()
        content_json = out_dir / "reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json"
        video_path = out_dir / "videos" / "ai-prompt-kit-douyin.mp4"
        subprocess.run(
            [
                sys.executable,
                str(RENDER_VIDEO),
                "--content-json",
                str(content_json),
                "--platform",
                "douyin",
                "--out",
                str(video_path),
            ],
            check=True,
            cwd=ROOT,
        )
        self.assertTrue(video_path.exists())
        self.assertGreater(video_path.stat().st_size, 1000)
        metadata = json.loads(video_path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["platform"], "douyin")

        relative_root = Path(tempfile.mkdtemp(prefix="video-relative-test-", dir=ROOT / "promotion-output"))
        self.addCleanup(shutil.rmtree, relative_root, ignore_errors=True)
        relative_video_path = Path(os.path.relpath(relative_root / "nested" / "relative-douyin.mp4", ROOT))
        subprocess.run(
            [
                sys.executable,
                str(RENDER_VIDEO),
                "--content-json",
                str(content_json),
                "--platform",
                "douyin",
                "--out",
                str(relative_video_path),
            ],
            check=True,
            cwd=ROOT,
        )
        absolute_relative_video_path = ROOT / relative_video_path
        self.assertTrue(absolute_relative_video_path.exists())
        self.assertGreater(absolute_relative_video_path.stat().st_size, 1000)

    def test_video_renderer_muxes_voiceover_audio_file(self) -> None:
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg is not installed")
        out_dir = Path(tempfile.mkdtemp(prefix="video-voiceover-test-"))
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        content_json = out_dir / "content.json"
        audio_path = out_dir / "voiceover.wav"
        video_path = out_dir / "promo-with-voiceover.mp4"
        content_json.write_text(
            json.dumps(
                {
                    "douyin": {
                        "title": "Launch draft",
                        "storyboard": [
                            {"time": "0-2s", "visual": "Show the product", "voiceover": "Turn one product URL into content."}
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                str(audio_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                sys.executable,
                str(RENDER_VIDEO),
                "--content-json",
                str(content_json),
                "--platform",
                "douyin",
                "--voiceover-audio",
                str(audio_path),
                "--out",
                str(video_path),
            ],
            check=True,
            cwd=ROOT,
        )
        self.assertTrue(video_path.exists())
        metadata = json.loads(video_path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["audioMode"], "file")
        self.assertEqual(Path(metadata["audio"]), audio_path)


if __name__ == "__main__":
    unittest.main()
