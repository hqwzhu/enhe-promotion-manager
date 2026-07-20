import json
import re
import subprocess
import unittest
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "browser-extension"


class _IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        element_id = dict(attrs).get("id")
        if element_id:
            self.ids.append(element_id)


@contextmanager
def _chromium_browser(test_case):
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        test_case.fail(
            "Install UI test dependencies with `python -m pip install -r requirements-test.txt`, "
            "then run `python -m playwright install chromium`."
        )

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as error:
            test_case.fail(
                "Chromium is required for extension UI tests. Run `python -m playwright install chromium`. "
                f"Original error: {error}"
            )
        try:
            yield browser
        finally:
            browser.close()


class ExtensionUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (EXTENSION / "popup.html").read_text(encoding="utf-8")
        cls.js = (EXTENSION / "popup.js").read_text(encoding="utf-8")
        cls.css = (EXTENSION / "popup.css").read_text(encoding="utf-8")
        cls.manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))

    def test_guide_markup_has_accessible_views_and_tabs(self):
        for element_id in (
            "openGuide",
            "openWorkspace",
            "guideView",
            "guideBack",
            "guideTabs",
            "guideFeatures",
            "guideUsage",
            "guideSubscription",
        ):
            self.assertRegex(self.html, rf'id=["\']{element_id}["\']')
        self.assertRegex(self.html, r'id=["\']guideTabs["\'][^>]*role=["\']tablist["\']')
        self.assertRegex(self.html, r'role=["\']tab["\']')
        self.assertRegex(self.html, r'aria-selected=["\'](?:true|false)["\']')
        self.assertRegex(self.html, r'aria-controls=["\']guide(?:Features|Usage|Subscription)["\']')

    def test_new_translation_keys_exist_in_both_dictionaries(self):
        en = self._dictionary_body("EN_TRANSLATIONS")
        zh = self._dictionary_body("ZH_TRANSLATIONS")
        keys = set(re.findall(r'^\s{2}([A-Za-z][A-Za-z0-9]*)\s*:', en, re.MULTILINE))
        new_keys = {
            key
            for key in keys
            if key.startswith("guide")
            or key in {"openGuide", "openWorkspace", "guideBack", "workspacePlaceholder"}
        }
        self.assertTrue(new_keys, "expected guide/workspace translation keys")
        for key in new_keys:
            self.assertRegex(zh, rf'\n  {re.escape(key)}\s*:', msg=key)

    def test_manifest_permissions_are_minimal(self):
        self.assertEqual(self.manifest["permissions"], ["activeTab", "storage", "clipboardWrite"])

    def test_hosted_worker_disabled_state_is_fail_closed_and_keeps_billing_available(self):
        self.assertIn("const HOSTED_WORKER_ENABLED = false;", self.js)
        page_url = f"{(EXTENSION / 'popup.html').resolve().as_uri()}?view=workspace"
        expected_messages = {
            "en-US": "Hosted Worker is currently off. Local Skill runs remain available.",
            "zh-CN": "Hosted Worker 当前关闭，本地 Skill 可继续使用。",
        }

        with _chromium_browser(self) as browser:
            for locale, expected_message in expected_messages.items():
                with self.subTest(locale=locale):
                    context = browser.new_context(locale=locale, viewport={"width": 1280, "height": 900})
                    page = context.new_page()
                    page.add_init_script(
                        """window.__fetchCalls = 0;
                        window.__clipboardWrites = 0;
                        window.fetch = async () => {
                          window.__fetchCalls += 1;
                          return { ok: true, json: async () => ({ allowed: true }) };
                        };
                        Object.defineProperty(navigator, 'clipboard', {
                          configurable: true,
                          value: { writeText: async () => { window.__clipboardWrites += 1; } }
                        });"""
                    )
                    page.goto(page_url, wait_until="load")
                    page.locator('body[data-initialized="true"]').wait_for(timeout=3000)

                    observed = page.evaluate(
                        """() => ({
                          hostedControls: ['startHostedRun', 'authorizeUsage', 'copyHostedPayload', 'hostedRunEndpoint']
                            .map((id) => {
                              const element = document.getElementById(id);
                              return {
                                id,
                                disabled: element.disabled,
                                ariaDisabled: element.getAttribute('aria-disabled'),
                                primary: element.classList.contains('primary')
                              };
                            }),
                          checkoutDisabled: document.getElementById('openCheckout').disabled,
                          portalDisabled: document.getElementById('openPortal').disabled,
                          usageMessage: document.getElementById('usageMessage').textContent,
                          hostedRunMessage: document.getElementById('hostedRunMessage').textContent
                        })"""
                    )
                    self.assertTrue(all(item["disabled"] for item in observed["hostedControls"]))
                    self.assertTrue(all(item["ariaDisabled"] == "true" for item in observed["hostedControls"]))
                    self.assertFalse(
                        next(item for item in observed["hostedControls"] if item["id"] == "startHostedRun")["primary"]
                    )
                    self.assertFalse(observed["checkoutDisabled"])
                    self.assertFalse(observed["portalDisabled"])
                    self.assertEqual(observed["usageMessage"], expected_message)
                    self.assertEqual(observed["hostedRunMessage"], expected_message)

                    invoked = page.evaluate(
                        """async () => {
                          await authorizeUsage();
                          await copyHostedPayload();
                          await startHostedRun();
                          return {
                            fetchCalls: window.__fetchCalls,
                            clipboardWrites: window.__clipboardWrites,
                            usageMessage: document.getElementById('usageMessage').textContent,
                            hostedRunMessage: document.getElementById('hostedRunMessage').textContent
                          };
                        }"""
                    )
                    self.assertEqual(invoked["fetchCalls"], 0)
                    self.assertEqual(invoked["clipboardWrites"], 0)
                    self.assertEqual(invoked["usageMessage"], expected_message)
                    self.assertEqual(invoked["hostedRunMessage"], expected_message)
                    context.close()

    def test_disabled_hosted_estimate_is_reference_only_without_upsell(self):
        page_url = f"{(EXTENSION / 'popup.html').resolve().as_uri()}?view=workspace"
        expected = {
            "en-US": (
                ("Reference only", "Hosted Worker off", "Local Skill runs do not consume hosted credits"),
                ("USD", "prepaid", "estimated hosted cost", "estimated gross cost"),
            ),
            "zh-CN": (
                ("仅供未来参考", "Hosted Worker 当前关闭", "本地 Skill 不消耗托管点数"),
                ("USD", "预付", "预计最高成本"),
            ),
        }

        with _chromium_browser(self) as browser:
            for locale, (required, forbidden) in expected.items():
                with self.subTest(locale=locale):
                    context = browser.new_context(locale=locale, viewport={"width": 1280, "height": 900})
                    page = context.new_page()
                    page.goto(page_url, wait_until="load")
                    page.locator('body[data-initialized="true"]').wait_for(timeout=3000)
                    self.assertEqual(page.input_value("#plan"), "starter")
                    self.assertEqual(page.input_value("#monthlyRuns"), "20")
                    summary = page.text_content("#costSummary")
                    for marker in required:
                        self.assertIn(marker, summary)
                    for marker in forbidden:
                        self.assertNotIn(marker, summary)
                    self.assertFalse(page.is_disabled("#openCheckout"))
                    self.assertFalse(page.is_disabled("#openPortal"))
                    context.close()

    def test_workspace_markup_groups_primary_and_secondary_content_with_unique_ids(self):
        self.assertRegex(self.html, r'<body[^>]*data-layout=["\']popup["\'][^>]*data-view=["\']main["\']')
        self.assertRegex(self.html, r'class=["\'][^"\']*workspace-grid[^"\']*["\']')
        self.assertRegex(self.html, r'class=["\'][^"\']*workspace-primary[^"\']*["\']')
        self.assertRegex(self.html, r'class=["\'][^"\']*workspace-secondary[^"\']*["\']')

        collector = _IdCollector()
        collector.feed(self.html)
        duplicates = sorted({element_id for element_id in collector.ids if collector.ids.count(element_id) > 1})
        self.assertEqual(duplicates, [])

    def test_workspace_styles_define_desktop_tablet_mobile_and_reduced_motion_contracts(self):
        self.assertRegex(
            self.css,
            re.compile(
                r'body\[data-layout=["\']workspace["\']\]\s*\{[^}]*width:\s*100%[^}]*min-width:\s*320px[^}]*max-width:\s*none',
                re.DOTALL,
            ),
        )
        self.assertRegex(
            self.css,
            re.compile(
                r'body\[data-layout=["\']workspace["\']\]\s+\.workspace-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1\.15fr\)\s+minmax\(300px,\s*\.85fr\)[^}]*gap:\s*16px',
                re.DOTALL,
            ),
        )
        self.assertRegex(self.css, r'@media\s*\([^)]*max-width:\s*900px[^)]*\)')
        self.assertRegex(self.css, r'@media\s*\([^)]*max-width:\s*520px[^)]*\)')
        self.assertRegex(self.css, r'@media\s*\(prefers-reduced-motion:\s*reduce\)')

    def test_hidden_guide_panels_are_not_overridden_by_component_display_rules(self):
        self.assertRegex(
            self.css,
            re.compile(r'\[hidden\]\s*\{[^}]*display:\s*none\s*!important', re.DOTALL),
        )

    def test_workspace_query_initializes_main_layout_and_guide_round_trip_preserves_it(self):
        script = f"""
const els = {{
  mainView: {{ hidden: false }},
  guideView: {{ hidden: true }},
  guideFeatures: {{ hidden: false }},
  guideUsage: {{ hidden: true }},
  guideSubscription: {{ hidden: true }}
}};
global.document = {{
  body: {{ dataset: {{}} }},
  querySelector: () => null,
  querySelectorAll: () => []
}};
{self._function_source("setLayout")}
{self._function_source("initializeViewState")}
{self._function_source("setView")}
{self._function_source("setGuideTab")}

initializeViewState("?view=workspace");
const workspace = {{
  layout: document.body.dataset.layout,
  view: document.body.dataset.view,
  mainHidden: els.mainView.hidden,
  guideHidden: els.guideView.hidden
}};
setView("guide");
const guide = {{ layout: document.body.dataset.layout, view: document.body.dataset.view }};
setView("main");
const returned = {{ layout: document.body.dataset.layout, view: document.body.dataset.view }};
initializeViewState("");
const popup = {{ layout: document.body.dataset.layout, view: document.body.dataset.view }};
process.stdout.write(JSON.stringify({{ workspace, guide, returned, popup }}));
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(
            observed["workspace"],
            {"layout": "workspace", "view": "main", "mainHidden": False, "guideHidden": True},
        )
        self.assertEqual(observed["guide"], {"layout": "workspace", "view": "guide"})
        self.assertEqual(observed["returned"], {"layout": "workspace", "view": "main"})
        self.assertEqual(observed["popup"], {"layout": "popup", "view": "main"})

    def test_actual_page_initializes_responsive_workspace_and_keyboard_guide(self):
        page_url = f"{(EXTENSION / 'popup.html').resolve().as_uri()}?view=workspace"
        viewports = ((360, 844, 1), (768, 900, 1), (1280, 900, 2))

        with _chromium_browser(self) as browser:
            for width, height, expected_columns in viewports:
                with self.subTest(viewport=f"{width}x{height}"):
                    context = browser.new_context(locale="en-US", viewport={"width": width, "height": height})
                    page = context.new_page()
                    page_errors = []
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.goto(page_url, wait_until="load")
                    page.locator('body[data-initialized="true"]').wait_for(timeout=3000)

                    observed = page.evaluate(
                        r"""() => ({
                          layout: document.body.dataset.layout,
                          view: document.body.dataset.view,
                          featureCards: document.querySelectorAll('#guideFeatureList .guide-card').length,
                          advancedDisclosures: document.querySelectorAll('#guideFeatureList .guide-disclosure').length,
                          usageItems: document.querySelectorAll('#guideUsageList .guide-usage-item').length,
                          planRows: document.querySelectorAll('#guidePlans .plan-row').length,
                          planNames: Array.from(
                            document.querySelectorAll('#guidePlans .plan-row-summary strong'),
                            (node) => node.textContent
                          ),
                          scrollWidth: document.documentElement.scrollWidth,
                          innerWidth: window.innerWidth,
                          columns: getComputedStyle(document.querySelector('.workspace-grid'))
                            .gridTemplateColumns.trim().split(/\s+/).length
                        })"""
                    )
                    self.assertEqual(observed["layout"], "workspace")
                    self.assertEqual(observed["view"], "main")
                    self.assertEqual(observed["featureCards"], 8)
                    self.assertEqual(observed["advancedDisclosures"], 1)
                    self.assertEqual(observed["usageItems"], 8)
                    self.assertEqual(observed["planRows"], 4)
                    self.assertEqual(observed["planNames"], ["Free", "Starter", "Growth", "Scale"])
                    self.assertLessEqual(observed["scrollWidth"], observed["innerWidth"])
                    self.assertEqual(observed["columns"], expected_columns)

                    page.click("#openGuide")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "guideTabFeatures")
                    self.assertEqual(self._visible_guide_panels(page), ["guideFeatures"])

                    page.keyboard.press("ArrowRight")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "guideTabUsage")
                    self.assertEqual(self._visible_guide_panels(page), ["guideUsage"])
                    page.keyboard.press("End")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "guideTabSubscription")
                    self.assertEqual(self._visible_guide_panels(page), ["guideSubscription"])
                    page.keyboard.press("Home")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "guideTabFeatures")
                    self.assertEqual(self._visible_guide_panels(page), ["guideFeatures"])
                    page.keyboard.press("ArrowLeft")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "guideTabSubscription")
                    self.assertEqual(self._visible_guide_panels(page), ["guideSubscription"])

                    page.click("#guideBack")
                    self.assertEqual(page.evaluate("document.activeElement.id"), "openGuide")
                    self.assertEqual(
                        page.evaluate(
                            """() => ({
                              layout: document.body.dataset.layout,
                              view: document.body.dataset.view,
                              mainHidden: document.getElementById('mainView').hidden,
                              guideHidden: document.getElementById('guideView').hidden
                            })"""
                        ),
                        {"layout": "workspace", "view": "main", "mainHidden": False, "guideHidden": True},
                    )
                    self.assertEqual(page_errors, [])
                    context.close()

    def test_actual_page_handles_rejected_chrome_storage_without_blocking_guide(self):
        page_url = f"{(EXTENSION / 'popup.html').resolve().as_uri()}?view=workspace"
        with _chromium_browser(self) as browser:
            context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
            page = context.new_page()
            page.add_init_script(
                """window.chrome = window.chrome || {};
                window.chrome.storage = { local: {
                  get: async () => { throw new Error('storage get rejected'); },
                  set: async () => { throw new Error('storage set rejected'); }
                }};"""
            )
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(page_url, wait_until="load")
            page.locator('body[data-initialized="true"]').wait_for(timeout=3000)
            self.assertEqual(page.locator("#guideFeatureList .guide-card").count(), 8)
            self.assertEqual(page.locator("#guideUsageList .guide-usage-item").count(), 8)
            self.assertEqual(page.locator("#guidePlans .plan-row").count(), 4)
            self.assertEqual(page_errors, [])
            context.close()

    def test_workspace_open_restores_non_sensitive_draft_in_new_page(self):
        page_url = (EXTENSION / "popup.html").resolve().as_uri()
        secret = "must-not-enter-workspace-draft"
        with _chromium_browser(self) as browser:
            context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
            popup = context.new_page()
            popup.goto(page_url, wait_until="load")
            popup.locator('body[data-initialized="true"]').wait_for(timeout=3000)
            popup.fill("#productUrl", "https://www.enhe-tech.com.cn/promotion-manager")
            popup.select_option("#workflowDepth", "research")
            popup.select_option("#commandType", "skill_entry")
            popup.fill("#outDir", ".\\saved-promotion-output")
            popup.select_option("#plan", "growth")
            popup.fill("#monthlyRuns", "7")
            popup.check("#deepReview")
            popup.fill("#licenseKey", secret)
            for checkbox in popup.locator("#platforms input").all():
                checkbox.uncheck()
            popup.check('#platforms input[value="youtube"]')
            popup.check('#platforms input[value="douyin"]')
            popup.click("#generate")
            command = popup.input_value("#commandOutput")
            self.assertTrue(command)

            with context.expect_page() as workspace_info:
                popup.click("#openWorkspace")
            workspace = workspace_info.value
            workspace.wait_for_load_state("load")
            workspace.locator('body[data-initialized="true"]').wait_for(timeout=3000)

            self.assertEqual(workspace.get_attribute("body", "data-layout"), "workspace")
            self.assertEqual(
                workspace.input_value("#productUrl"),
                "https://www.enhe-tech.com.cn/promotion-manager",
            )
            self.assertEqual(workspace.input_value("#workflowDepth"), "research")
            self.assertEqual(workspace.input_value("#commandType"), "skill_entry")
            self.assertEqual(workspace.input_value("#outDir"), ".\\saved-promotion-output")
            self.assertEqual(workspace.input_value("#plan"), "growth")
            self.assertEqual(workspace.input_value("#monthlyRuns"), "7")
            self.assertTrue(workspace.is_checked("#deepReview"))
            self.assertEqual(
                workspace.locator("#platforms input:checked").evaluate_all(
                    "inputs => inputs.map((input) => input.value)"
                ),
                ["youtube", "douyin"],
            )
            self.assertEqual(workspace.input_value("#commandOutput"), command)
            self.assertEqual(workspace.input_value("#licenseKey"), "")
            stored_values = popup.evaluate("Object.values(localStorage).join('\\n')")
            self.assertNotIn(secret, stored_values)
            context.close()

    def _visible_guide_panels(self, page):
        return page.locator("[role=tabpanel]").evaluate_all(
            "panels => panels.filter((panel) => !panel.hidden).map((panel) => panel.id)"
        )

    def test_plan_values_match_product_contract(self):
        for key, credits, price in (("starter", 60, 19), ("growth", 220, 59), ("scale", 800, 199)):
            self.assertRegex(self.js, rf'{key}:\s*\{{[^}}]*credits:\s*{credits}[^}}]*priceCny:\s*{price}')

    def test_workspace_tab_rejection_uses_safe_fallback(self):
        body = self._function_body("openWorkspace")
        self.assertRegex(body, r'await\s+chrome\.tabs\.create\(')
        self.assertRegex(body, re.compile(r'catch\s*\([^)]*\)\s*\{.*openWorkspaceFallback\(', re.DOTALL))
        self.assertRegex(self.js, r'openWorkspace\(\)\.catch\(')

        script = f"""
const calls = [];
let createCalls = 0;
let persistCalls = 0;
async function persistWorkspaceDraft() {{ persistCalls += 1; }}
global.window = {{
  location: {{ href: "chrome-extension://test/popup.html?view=guide&source=test" }},
  open: (...args) => calls.push(args)
}};
global.chrome = {{
  tabs: {{
    create: async () => {{
      createCalls += 1;
      throw new Error("tabs unavailable");
    }}
  }}
}};
{self._function_source("openWorkspace")}
{self._function_source("openWorkspaceFallback")}
(async () => {{
  await openWorkspace();
  process.stdout.write(JSON.stringify({{ createCalls, persistCalls, calls }}));
}})().catch((error) => {{
  console.error(error.stack);
  process.exit(1);
}});
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["createCalls"], 1)
        self.assertEqual(observed["persistCalls"], 1)
        self.assertEqual(
            observed["calls"],
            [["chrome-extension://test/popup.html?view=workspace", "_blank", "noopener,noreferrer"]],
        )

    def test_each_subscription_plan_has_audience_and_included_usage(self):
        en = self._dictionary_body("EN_TRANSLATIONS")
        zh = self._dictionary_body("ZH_TRANSLATIONS")
        for plan in ("Free", "Starter", "Growth", "Scale"):
            audience = f"guidePlan{plan}Audience"
            included = f"guidePlan{plan}Included"
            for dictionary, hosted_term in ((en, "hosted"), (zh, "托管")):
                self.assertRegex(dictionary, rf'\n  {audience}:\s*"[^"\n]+"')
                included_match = re.search(rf'\n  {included}:\s*"(?P<text>[^"\n]*\{{credits\}}[^"\n]*)"', dictionary)
                self.assertIsNotNone(included_match, included)
                self.assertIn(hosted_term, included_match.group("text").lower())
            self.assertRegex(
                self.js,
                rf'{plan.lower()}:\s*\{{[^}}]*audience:\s*"{audience}"[^}}]*included:\s*"{included}"',
            )
        self.assertIn("Object.entries(PLANS)", self.js)
        self.assertIn('t(details.included, { credits: plan.credits })', self.js)

    def _dictionary_body(self, name):
        match = re.search(rf'const {name} = Object\.freeze\(\{{(?P<body>.*?)\}}\);', self.js, re.DOTALL)
        self.assertIsNotNone(match, name)
        return match.group("body")

    def _function_body(self, name):
        match = re.search(rf'(?:async\s+)?function {name}\([^)]*\) \{{(?P<body>.*?)\n\}}\n\nfunction', self.js, re.DOTALL)
        self.assertIsNotNone(match, name)
        return match.group("body")

    def _function_source(self, name):
        match = re.search(
            rf'(?P<source>(?:async\s+)?function {name}\([^)]*\) \{{.*?\n\}})(?=\n\nfunction)',
            self.js,
            re.DOTALL,
        )
        self.assertIsNotNone(match, name)
        return match.group("source")


if __name__ == "__main__":
    unittest.main()
