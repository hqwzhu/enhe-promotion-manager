---
name: viral-product-copy-video-generator
description: Generate product promotion research, viral copy, video scripts, safe publish packs, and retrospective templates for YouTube, Zhihu, Xiaohongshu, Douyin, GitHub, and similar channels. Use when the user provides a product URL, website URL, app/tool page, GitHub repo, or asks to promote a product with multi-platform copy/video content, competitor deconstruction, publish planning, or content performance review.
---

# Viral Product Copy Video Generator

## Core Rule

Act as a product promotion manager, not a generic copywriter. Convert a product URL or product brief into a repeatable promotion loop:

`research -> deconstruct -> generate copy/scripts -> review -> publish pack -> real-data retrospective -> next round`

Never auto-publish, auto-login, save cookies/tokens/passwords, or fabricate platform metrics. When a captcha appears, the operator must complete it manually; the workflow does not process it.

Current publishing policy: manual publish packages are the primary path; auto-publish ports are reserved for later official API-only upgrades. Generate publish queues, browser/manual payloads, launch unlock packs, and evidence templates first. Keep GitHub and YouTube as dry-run-first official API integration ports. Douyin is currently browser-assisted/manual because operator authorization is unavailable; its final submission remains manual unless a future official API authorization has been verified.

## Quick Start

When the user sends a product link, do this:

1. Inspect the product page or ask for missing basics: product name, target audience, pain points, value proposition, price, target platforms, and primary goal.
2. Research platform constraints and competitors when the request depends on current information. Prefer official docs for API/publishing claims.
3. Use `scripts/skill_entry.py` when the user simply gives a link and asks Codex to execute the Skill. It generates the real-run playbook, runs the highest-automation safe flow, and refreshes the final readiness matrix.
4. Review the generated content. The workflow writes a `cheat-review` pack with platform draft files and Codex prompts for `cheat-score`. If `cheat-on-content` is installed, use it for a second-pass content review; otherwise use the generated scorecard. Read [references/cheat-on-content-integration.md](references/cheat-on-content-integration.md) before writing prediction logs.
5. Give the user publish packs and ask for approval before any publishing action.
6. After each completed stage, report: current stage, completed goals, unfinished goals, next plan, and estimated remaining time. Use `scripts/final_capability_readiness.py` for the machine-readable phase/status matrix.

Default one-command workflow:

```bash
python scripts/skill_entry.py \
  --link "https://example.com/product-or-site" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --github-repo owner/repo \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

For the Chrome extension operator UI, load `browser-extension/` as an unpacked Manifest V3 extension. It captures the active product tab, estimates subscription credits, stores a license key locally, validates licenses, reserves hosted usage credits before hosted runs, copies or submits hosted run payloads, links to ENHE website traffic pages, and generates safe Codex commands for one-link Skill runs, browser publish sessions, launch unlock packs, real evidence inbox setup/recovery, post-publish performance monitoring, final readiness audits, periodic automation configs, due scheduled runs, and Windows Task Scheduler scripts. To build a Chrome/Edge submission zip, run `scripts/package_browser_extension.py --out-dir "./dist"` and review `docs/extension-store-submission.md`. See `docs/browser-extension.md` and `docs/subscription-pricing.md`.

To validate the paid-subscription contract locally before deploying a backend:

```bash
python scripts/billing_contract_simulator.py demo \
  --plan growth \
  --workflow-type research_run \
  --out-dir "./promotion-output"
```

To validate the scheduled automation credit path locally:

```bash
python scripts/billing_contract_simulator.py demo \
  --plan growth \
  --workflow-type automation_due_run \
  --out-dir "./promotion-output"
```

To validate the browser extension hosted-run handoff after credit reservation:

```bash
python scripts/billing_contract_simulator.py demo-hosted-run \
  --plan growth \
  --workflow-type standard_run \
  --product-url "https://example.com/product" \
  --out-dir "./promotion-output"
```

To package the browser extension for Chrome Web Store or Microsoft Edge Add-ons submission:

```bash
python scripts/package_browser_extension.py --out-dir "./dist"
```

For GitHub/open-source users, start with `README.md`, `docs/installation.md`, `docs/usage.md`, and `docs/final-capability-map.md`.

When the user asks why a module is not 100% complete, what remains, what Codex can complete, what open-source projects can help, or what exact operator steps are required, use `docs/100-percent-completion-roadmap.md`, `docs/zh-CN/100-percent-completion-guide.md`, and refresh the machine-readable reports:

```bash
python scripts/completion_roadmap.py --out-dir "./promotion-output"
python scripts/operator_action_checklist.py --out-dir "./promotion-output"
```

Optional Firecrawl-style public web data provider:

```bash
WEB_DATA_PROVIDER=auto
FIRECRAWL_API_KEY=
FIRECRAWL_BASE_URL=https://api.firecrawl.dev/v2
```

Most CLI entrypoints load a local `.env` automatically when present. If credentials live outside the repository, pass `--env-file "C:/path/to/.env"`; reports record only loaded key names, never values.
For YouTube, official API helpers accept either `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` or `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET`. Upload-token checks accept `YOUTUBE_ACCESS_TOKEN` or `YOUTUBE_OAUTH_ACCESS_TOKEN`; `YOUTUBE_REFRESH_TOKEN` is recorded only as an optional future refresh-token input.

To verify YouTube credential readiness without uploading or printing secrets:

```bash
python scripts/youtube_credential_check.py \
  --env-file "C:/path/to/.env" \
  --out-dir "./promotion-output"
```

Add `--check-channel` only when you want a read-only official YouTube Data API `channels.list(mine=true)` probe with an OAuth access token.

When `FIRECRAWL_API_KEY` is present, `scripts/web_data_provider.py` can run public Search, Scrape, Map, Crawl, and Batch Scrape operations. The product URL reader, product URL discovery, and browser search snapshot scripts use it as an optional evidence layer before falling back to local browser/static/user-evidence paths. Firecrawl-style Interact is plan-only in this Skill:

```bash
python scripts/web_data_provider.py \
  --env-file "C:/path/to/.env" \
  --out-dir "./promotion-output" \
  interact-plan \
  --url "https://example.com/public-page" \
  --goal "collect public launch evidence" \
  --action "scroll:bottom" \
  --action "extract:visible text"
```

The `interact-plan` command must block login, captcha, risk-control, account verification, final publish, like, follow, comment, and DM actions. To inspect platform Create/Publish/Engage/Monetize/Search boundaries inspired by AiToEarn, including the temporary Relay bridge policy, run:

```bash
python scripts/platform_capabilities.py --out-dir "./promotion-output"
```

When real published URLs, platform exports, browser snapshots, comment evidence, or business exports already exist, pass them into the same one-link entry so the Skill can recover evidence and generate the next round:

```bash
python scripts/skill_entry.py \
  --link "https://example.com/product-or-site" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --published-url "xiaohongshu=https://www.xiaohongshu.com/explore/real-note-id" \
  --metrics-csv "./real-platform-metrics.csv" \
  --metrics-structured-json "./published-metrics-snapshot.json" \
  --comment-evidence-html-file "./visible-comments.html" \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

When real published URLs are registered, run the post-publish monitor:

```bash
python scripts/performance_monitor.py \
  --out-dir "./promotion-output"
```

Run the monitor after real published URLs are registered. It captures public/browser-visible metrics, captures visible comments and demand signals, attributes optional order/revenue exports, runs metrics recovery, writes a history file, and generates next-round recommendations. Before or after publishing, initialize a fillable evidence inbox:

```bash
python scripts/real_evidence_inbox_setup.py \
  --product-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --inbox-dir "./promotion-evidence-inbox" \
  --out-dir "./promotion-output"
```

For multiple evidence files, use the inbox orchestrator:

```bash
python scripts/real_evidence_inbox.py \
  --inbox-dir "./promotion-evidence-inbox" \
  --out-dir "./promotion-output"
```

The inbox setup writes `inbox-manifest.json`, `published-urls.csv`, `metrics.csv`, `comments.txt`, `orders.csv`, `structured-metrics-snapshot.example.json`, `README.md`, and an import command file without seeding fake metrics, comments, orders, or revenue. The inbox can contain `published-urls.csv`, `metrics.csv`, `metrics.xlsx`, `comments.txt`, `comments.html`, `orders.csv`, `orders.xlsx`, JSON/text variants, or an optional `inbox-manifest.json` with explicit roles. The inbox runner registers real published URLs, imports metrics, captures comment demand signals, attributes orders/revenue, runs metrics recovery, and generates next-round recommendations.

If no real data exists yet and the operator only needs to validate the recovery and next-round loop, generate clearly marked synthetic/demo evidence:

```bash
python scripts/synthetic_evidence_generator.py \
  --product-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --run-recovery \
  --out-dir "./promotion-output/synthetic-validation"
```

Synthetic reports carry `SYNTHETIC_DEMO_DATA_DO_NOT_REPORT`. They are for local pipeline validation only and must never be reported as real platform, order, or revenue performance.

When browser-assisted platforms have known creator entry URLs, the one-link entry can also fill visible fields and stop before final publish:

```bash
python scripts/skill_entry.py \
  --link "https://example.com/product" \
  --platforms xiaohongshu \
  --platform-publish-url "xiaohongshu=https://creator.xiaohongshu.com/" \
  --run-browser-form-fill \
  --browser-form-fill-timeout-ms 30000 \
  --out-dir "./promotion-output"
```

`--link-mode auto` is the default. It treats the link as a product candidate and also uses the first link as a public website discovery seed, then passes product pages through Codex/browser structured intake before generation.

For website/tool-directory links, the one-link entry forwards the full product URL discovery controls to the playbook and final runner:

```bash
python scripts/skill_entry.py \
  --link "https://example.com/tools" \
  --discovery-sitemap-url "https://example.com/sitemap.xml" \
  --discovery-top-n 25 \
  --discovery-max-depth 2 \
  --discovery-max-pages 50 \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

Lower-level workflow:

```bash
python scripts/run_promotion_workflow.py \
  --browser-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

Highest-automation safe runner:

```bash
python scripts/final_capability_runner.py \
  --url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --run-follow-up-captures \
  --capture-browser-assisted-follow-ups \
  --sample-video-frames \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

When a publish queue exists, the final runner internally builds the launch unlock pack for each product run unless `--skip-launch-unlock-pack` is supplied. This generation step does not execute platform publication.

To request official publishing for supported GitHub/YouTube paths from the high-level runner, add the execution gate. Douyin can still be included in the run, but it remains browser-assisted/manual and `--douyin-video-file` only attaches the MP4 asset:

```bash
python scripts/final_capability_runner.py \
  --url "https://example.com/product" \
  --platforms youtube,douyin,github \
  --github-repo owner/repo \
  --youtube-video-file "./promotion-output/videos/product-youtube.mp4" \
  --douyin-video-file "./promotion-output/videos/product-douyin.mp4" \
  --execute-publish \
  --approval I_APPROVE_PUBLISH \
  --out-dir "./promotion-output"
```

Real run command pack before a live product cycle:

```bash
python scripts/real_run_playbook.py \
  --url "https://example.com/product" \
  --discover-from-url "https://example.com/tools" \
  --discovery-sitemap-url "https://example.com/sitemap.xml" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --github-repo owner/repo \
  --business-csv "./orders-and-revenue.csv" \
  --platform-publish-url "xiaohongshu=https://creator.xiaohongshu.com/" \
  --run-browser-form-fill \
  --out-dir "./promotion-output"
```

The runner also writes a final readiness matrix that compares the run against the user's requested end state:

```bash
python scripts/final_capability_readiness.py --out-dir "./promotion-output"
```

Use the readiness matrix and generated Markdown as the phase progress report after every major stage. The report must state the current stage, completed goals, unfinished goals, next plan, and estimated remaining time. Time estimates are planning estimates because platform review, account authorization, publishing, and real metrics exports are external gates.

To also fill visible browser-assisted publisher fields from prepared payloads and stop before final publish:

```bash
python scripts/final_capability_runner.py \
  --url "https://example.com/product" \
  --platforms xiaohongshu \
  --platform-publish-url "xiaohongshu=https://creator.xiaohongshu.com/" \
  --run-browser-form-fill \
  --out-dir "./promotion-output"
```

For static pages or environments without Playwright Chromium, use static HTML intake:

```bash
python scripts/run_promotion_workflow.py \
  --product-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

For dynamic pages, Codex can capture the rendered page first and pass a structured snapshot:

```bash
python scripts/browser_snapshot.py \
  --url "https://example.com/product" \
  --out-file "./rendered-product-page.json"
```

```bash
python scripts/run_promotion_workflow.py \
  --structured-json "./rendered-product-page.json" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

Example:

```bash
python scripts/promotion_manager.py all \
  --product-name "AI Prompt Kit" \
  --product-url "https://example.com/product" \
  --audience "AI tool operators, creators, ecommerce sellers" \
  --value-proposition "Prompt templates for product copy, SEO content, and video scripts" \
  --goal leads \
  --out-dir "./promotion-output"
```

To extract a product profile directly from a public page or saved HTML:

```bash
python scripts/product_intake.py --url "https://example.com/product" --out-dir "./promotion-output/intake"
```

To have Codex read one or more product URLs into structured snapshots and product profiles:

```bash
python scripts/product_url_reader.py \
  --url "https://example.com/product" \
  --out-dir "./promotion-output"
```

If the local browser and static HTML fetch both fail for a public product URL, the reader falls back to a public web-text reader, saves `product-url-reader/<id>/web-reader-page.md`, and runs `product_intake.py --text-file` so the promotion cycle can continue from verified page text. Disable that third-party fallback with `--disable-web-text-fallback`, or pass Codex-provided page text with `--web-text-fallback-file`.

To discover likely product URLs from a public website or tool-station entry page before Codex reads them:

```bash
python scripts/product_url_discovery.py \
  --site-url "https://example.com" \
  --out-dir "./promotion-output"
```

The discovery step reads public HTML links plus public sitemap sources discovered from `robots.txt` and `/sitemap.xml`.
You can also pass a sitemap directly:

```bash
python scripts/product_url_discovery.py \
  --sitemap-url "https://example.com/sitemap.xml" \
  --out-dir "./promotion-output"
```

To discover product URLs and immediately batch-run each discovered product through Codex-first reading and promotion cycles:

```bash
python scripts/product_batch_runner.py \
  --discover-from-url "https://example.com" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

For a known sitemap source, use:

```bash
python scripts/product_batch_runner.py \
  --discovery-sitemap-url "https://example.com/sitemap.xml" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

To batch-run multiple product URLs through Codex-first reading and one promotion cycle per ready product:

```bash
python scripts/product_batch_runner.py \
  --urls-file "./product-urls.txt" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

To also run product-driven multi-query viral discovery after each ready product cycle:

```bash
python scripts/product_batch_runner.py \
  --urls-file "./product-urls.txt" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --run-multi-query-viral-discovery \
  --multi-query-query-count 5 \
  --multi-query-top-n 20 \
  --multi-query-browser-search-timeout-ms 15000 \
  --multi-query-browser-search-wait-until domcontentloaded \
  --multi-query-run-follow-up-captures \
  --multi-query-sample-video-frames \
  --out-dir "./promotion-output"
```

For dynamic platform search pages that keep long-running network connections open, prefer `--browser-search-wait-until domcontentloaded` on `viral_discovery_runner.py` or `multi_query_viral_discovery.py`; in product batch and final runs use `--multi-query-browser-search-wait-until domcontentloaded` plus a bounded timeout such as `--multi-query-browser-search-timeout-ms 15000`.

To batch-run product URLs through the closed loop with real evidence recovery and next-round optimization:

```bash
python scripts/product_batch_runner.py \
  --urls-file "./product-urls.txt" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --run-post-publish-metrics-capture \
  --run-comment-evidence-capture \
  --run-business-attribution \
  --run-next-round-optimization \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

To parse a rendered page snapshot captured by Codex/browser tooling:

```bash
python scripts/product_intake.py \
  --structured-json "./rendered-product-page.json" \
  --out-dir "./promotion-output/intake"
```

If Chromium is missing, install the official Playwright browser runtime:

```bash
python -m playwright install chromium
```

Or allow the workflow to attempt the official install when `--browser-url` is used:

```bash
python scripts/run_promotion_workflow.py \
  --browser-url "https://example.com/product" \
  --install-browser-if-missing \
  --out-dir "./promotion-output"
```

To render a real MP4 draft video after content generation:

```bash
python scripts/render_video.py \
  --content-json "./promotion-output/reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json" \
  --platform douyin \
  --out "./promotion-output/videos/ai-prompt-kit-douyin.mp4"
```

To render with a voiceover audio file:

```bash
python scripts/render_video.py \
  --content-json "./promotion-output/reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json" \
  --platform youtube \
  --voiceover-audio "./voiceover.wav" \
  --out "./promotion-output/videos/ai-prompt-kit-youtube.mp4"
```

To generate the complete media asset pack and write it back into the publish pack:

```bash
python scripts/media_asset_pack.py \
  --content-json "./promotion-output/reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json" \
  --publish-pack "./promotion-output/reports/promotion-manager/publish-packs/ai-prompt-kit-publish-pack.json" \
  --video-file "youtube=./promotion-output/videos/ai-prompt-kit-youtube.mp4" \
  --video-file "douyin=./promotion-output/videos/ai-prompt-kit-douyin.mp4" \
  --out-dir "./promotion-output"
```

The full workflow runs the media asset pack automatically after video rendering. If `--skip-video` is supplied, the media pack still generates cover/detail PNGs and marks required videos as missing instead of pretending they exist.

To import competitor evidence from a public page, saved HTML, JSON export, or copied transcript:

```bash
python scripts/competitor_intake.py \
  --html-file "./competitor.html" \
  --platform youtube \
  --out-dir "./promotion-output"
```

To create platform search tasks for competitor discovery:

```bash
python scripts/competitor_discovery.py \
  --query "AI product copy generator" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

To automatically open public platform search pages and create browser-visible search snapshots:

```bash
python scripts/platform_search_browser.py \
  --query "AI product copy generator" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

To run the standalone viral discovery pipeline from a keyword:

```bash
python scripts/viral_discovery_runner.py \
  --query "AI product copy generator" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --top-n 20 \
  --run-follow-up-captures \
  --sample-video-frames \
  --out-dir "./promotion-output"
```

To generate multiple product-driven search queries, run discovery for each, and merge the strongest viral materials and creators:

```bash
python scripts/multi_query_viral_discovery.py \
  --workflow-manifest "./promotion-output/reports/promotion-manager/agent-run/workflow-manifest.json" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --top-n 20 \
  --run-follow-up-captures \
  --sample-video-frames \
  --out-dir "./promotion-output"
```

When public platform search is blocked, unstable, or missing content because Zhihu, Xiaohongshu, Douyin, or similar platforms require browser-visible/manual evidence, initialize a fillable viral evidence inbox:

```bash
python scripts/viral_evidence_inbox_setup.py \
  --product-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --inbox-dir "./viral-evidence-inbox" \
  --out-dir "./promotion-output"
```

After adding real competitor URLs, visible text, transcripts, platform exports, or screenshot OCR text, import it into the same viral library and creator leaderboard:

```bash
python scripts/viral_evidence_inbox.py \
  --inbox-dir "./viral-evidence-inbox" \
  --out-dir "./promotion-output"
```

The viral evidence inbox is a fallback for real competitor evidence only. It does not seed fake creators or metrics, and screenshot files remain `manual_text_required` until OCR or copied visible text is supplied.

To automatically collect competitor evidence through supported official/public connectors:

```bash
python scripts/competitor_collector.py \
  --platform github \
  --query "AI product copy generator" \
  --out-dir "./promotion-output"
```

To capture multi-result search pages from Codex/browser-rendered snapshots:

```bash
python scripts/platform_search_capture.py \
  --structured-json "./search-snapshots/douyin.json" \
  --platform douyin \
  --query "AI product copy generator" \
  --out-dir "./promotion-output"
```

Search capture parses visible English and Chinese metrics such as views/plays, likes, saves/favorites, comments, shares, stars/forks, and creator audience labels such as `followers`, `粉丝`, `关注者`, and `订阅`. These values are ranking evidence only when visible in the public page, browser snapshot, official API/export, screenshot OCR/text, or user export.

To rank captured platform search results into a viral material library and follow-up capture queue:

```bash
python scripts/viral_content_library.py \
  --search-capture-dir "./promotion-output/reports/promotion-manager/competitors" \
  --top-n 20 \
  --out-dir "./promotion-output"
```

To group ranked viral materials into a creator/account leaderboard and follow-up tracking tasks:

```bash
python scripts/creator_leaderboard.py \
  --viral-library "./promotion-output/reports/promotion-manager/competitors/viral-content-library.json" \
  --top-n 20 \
  --out-dir "./promotion-output"
```

To run safe creator/account follow-up research from that leaderboard:

```bash
python scripts/creator_follow_up_runner.py \
  --tasks-json "./promotion-output/reports/promotion-manager/competitors/creator-follow-up-tasks.json" \
  --dry-run \
  --out-dir "./promotion-output"
```

To execute safe follow-up captures from that queue:

```bash
python scripts/follow_up_capture_runner.py \
  --tasks-json "./promotion-output/reports/promotion-manager/competitors/follow-up-capture-tasks.json" \
  --capture-browser-assisted \
  --out-dir "./promotion-output"
```

To also sample browser-visible video metadata and frame screenshots for video materials:

```bash
python scripts/follow_up_capture_runner.py \
  --tasks-json "./promotion-output/reports/promotion-manager/competitors/follow-up-capture-tasks.json" \
  --capture-browser-assisted \
  --sample-video-frames \
  --video-sample-count 5 \
  --out-dir "./promotion-output"
```

To sample one known public/browser-visible video page directly:

```bash
python scripts/browser_video_sampler.py \
  --url "https://example.com/video-page" \
  --platform youtube \
  --sample-count 5 \
  --out-dir "./promotion-output"
```

To rewrite generated platform content with the ranked viral/deep competitor libraries before video rendering and publish-pack preparation:

```bash
python scripts/competitor_content_enhancer.py \
  --content-json "./promotion-output/reports/promotion-manager/generated-content/ai-prompt-kit-platform-content.json" \
  --viral-library "./promotion-output/reports/promotion-manager/competitors/viral-content-library.json" \
  --deep-library "./promotion-output/reports/promotion-manager/competitors/deep-competitor-library.json" \
  --write-back \
  --out-dir "./promotion-output"
```

For a full workflow, place files such as `youtube.json`, `zhihu.json`, `xiaohongshu.json`, and `douyin.json` in one directory:

```bash
python scripts/run_promotion_workflow.py \
  --product-url "https://example.com/product" \
  --search-snapshot-dir "./search-snapshots" \
  --out-dir "./promotion-output"
```

Or let the workflow create public search snapshots first:

```bash
python scripts/run_promotion_workflow.py \
  --browser-url "https://example.com/product" \
  --auto-search-competitors \
  --run-follow-up-captures \
  --capture-browser-assisted-follow-ups \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --out-dir "./promotion-output"
```

To import real post-publish metrics from a platform or business export:

```bash
python scripts/metrics_intake.py \
  --csv-file "./metrics-export.csv" \
  --out-dir "./promotion-output"
```

Excel `.xlsx` exports are also supported for common platform and business dashboards:

```bash
python scripts/metrics_intake.py \
  --xlsx-file "./metrics-export.xlsx" \
  --out-dir "./promotion-output"
```

Metric parsing supports visible English and Chinese labels plus common units/currency, including `12K`, `2.4M`, `1.2万`, `3亿`, `$88.00`, and `￥88.00`. Treat parsed values as evidence only when the source is a public page, official API/export, screenshot OCR/text, or business export.

To import real metrics from a Codex/browser structured snapshot of a published page or analytics page:

```bash
python scripts/metrics_intake.py \
  --structured-json "./published-metrics-snapshot.json" \
  --out-dir "./promotion-output"
```

To recover metrics across a completed workflow, publish queue, published URLs, and business exports:

```bash
python scripts/metrics_recovery.py \
  --workflow-manifest "./promotion-output/reports/promotion-manager/agent-run/workflow-manifest.json" \
  --publish-queue "./promotion-output/reports/promotion-manager/publish-queue/publish-queue.json" \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

Use `--metrics-xlsx` or `--business-xlsx` when the platform or order system exports Excel instead of CSV:

```bash
python scripts/metrics_recovery.py \
  --metrics-xlsx "./platform-metrics.xlsx" \
  --business-xlsx "./orders-and-revenue.xlsx" \
  --out-dir "./promotion-output"
```

To attribute business orders and revenue exports that use UTM/content/referrer fields before recovery:

```bash
python scripts/business_attribution.py \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

For Excel order exports:

```bash
python scripts/business_attribution.py \
  --business-xlsx "./orders-and-revenue.xlsx" \
  --out-dir "./promotion-output"
```

Then merge the attribution export:

```bash
python scripts/metrics_recovery.py \
  --business-json "./promotion-output/reports/promotion-manager/business-attribution/business-attribution-export.json" \
  --out-dir "./promotion-output"
```

To merge structured metric snapshots with published URL evidence during recovery:

```bash
python scripts/metrics_recovery.py \
  --metrics-structured-json "./published-metrics-snapshot.json" \
  --out-dir "./promotion-output"
```

To register a manually published platform URL for later metrics recovery:

```bash
python scripts/published_items.py \
  --platform xiaohongshu \
  --published-url "https://www.xiaohongshu.com/explore/real-note-id" \
  --title "Published launch note" \
  --evidence "./screenshots/xhs-published.png" \
  --out-dir "./promotion-output"
```

To capture a browser-visible published page snapshot and register its real URL:

```bash
python scripts/publish_url_capture.py \
  --structured-json "./published-page-snapshot.json" \
  --out-dir "./promotion-output"
```

To automatically capture public/browser-visible metrics from registered published URLs:

```bash
python scripts/post_publish_metrics_capture.py \
  --out-dir "./promotion-output"
```

Then merge those captured metrics into the retrospective:

```bash
python scripts/metrics_recovery.py \
  --metrics-json "./promotion-output/reports/promotion-manager/post-publish-capture/post-publish-metrics-export.json" \
  --out-dir "./promotion-output"
```

To capture public/browser-visible comments and demand signals for the next content round:

```bash
python scripts/comment_evidence_capture.py \
  --out-dir "./promotion-output"
```

To initialize a fillable evidence inbox before importing real published URLs, metrics, comments, orders, and revenue:

```bash
python scripts/real_evidence_inbox_setup.py \
  --product-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --inbox-dir "./promotion-evidence-inbox" \
  --out-dir "./promotion-output"
```

To turn recovered metrics, comment demand signals, and business attribution into the next promotion round:

```bash
python scripts/performance_monitor.py \
  --out-dir "./promotion-output"
```

For manual step-by-step recovery:

```bash
python scripts/next_round_optimizer.py \
  --metrics-recovery-json "./promotion-output/reports/promotion-manager/metrics-recovery/metrics-recovery.json" \
  --comment-evidence-json "./promotion-output/reports/promotion-manager/comment-evidence/comment-evidence-export.json" \
  --business-attribution-json "./promotion-output/reports/promotion-manager/business-attribution/business-attribution.json" \
  --out-dir "./promotion-output"
```

To configure periodic local automation:

```bash
python scripts/automation_scheduler.py init \
  --config "./promotion-automation.json" \
  --job-id "product-weekly" \
  --browser-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --interval-days 7 \
  --output-root "./promotion-output/automation" \
  --auto-search-competitors \
  --enable-multi-query-viral-discovery \
  --run-follow-up-captures \
  --capture-browser-assisted-follow-ups \
  --enable-publish-queue \
  --enable-browser-publish-assistant \
  --enable-metrics-recovery \
  --enable-next-round-optimization
```

Then run due jobs manually or from an OS scheduler:

```bash
python scripts/automation_scheduler.py run --config "./promotion-automation.json"
```

To generate a Windows Task Scheduler registration script:

```bash
python scripts/automation_scheduler.py windows-task \
  --config "./promotion-automation.json" \
  --out-file "./register-enhe-promotion-task.ps1" \
  --time "09:00"
```

To run an official publish action, start with a dry run:

```bash
python scripts/publish_executor.py \
  --platform github \
  --github-action file \
  --github-repo owner/repo \
  --path PROMOTION.md \
  --content-file "./promotion-output/reports/promotion-manager/generated-content/product-platform-content.md" \
  --out-dir "./promotion-output"
```

Reserved future port: to inspect the low-level official Douyin Open Platform upload/create dry-run helper, provide the rendered MP4 and post text. Do not use this as the default publishing path while Douyin authorization is unavailable:

```bash
python scripts/publish_executor.py \
  --platform douyin \
  --douyin-video-file "./promotion-output/videos/product-douyin.mp4" \
  --title "Product launch draft #AI" \
  --out-dir "./promotion-output"
```

To turn a completed workflow into a guarded publish queue for all target platforms:

```bash
python scripts/publish_queue.py \
  --workflow-manifest "./promotion-output/reports/promotion-manager/agent-run/workflow-manifest.json" \
  --github-repo owner/repo \
  --youtube-video-file "./promotion-output/videos/product-youtube.mp4" \
  --douyin-video-file "./promotion-output/videos/product-douyin.mp4" \
  --out-dir "./promotion-output"
```

To audit whether each queued platform is ready for dry-run review, official execution, or manual/browser-assisted publishing:

```bash
python scripts/publish_readiness_runner.py \
  --workflow-manifest "./promotion-output/reports/promotion-manager/agent-run/workflow-manifest.json" \
  --build-queue \
  --github-repo owner/repo \
  --youtube-video-file "./promotion-output/videos/product-youtube.mp4" \
  --douyin-video-file "./promotion-output/videos/product-douyin.mp4" \
  --out-dir "./promotion-output"
```

For a reviewed official execution attempt through the readiness/queue path, add `--execute-publish --approval I_APPROVE_PUBLISH`. In the current setup this applies only to supported GitHub/YouTube official writes; Douyin remains browser-assisted/manual and does not require `DOUYIN_*` credentials unless a future verified Open Platform authorization is re-enabled.

To turn that readiness report into a credential/target/platform setup kit without storing secret values:

```bash
python scripts/publish_setup_assistant.py \
  --publish-readiness "./promotion-output/reports/promotion-manager/publish-readiness/publish-readiness.json" \
  --out-dir "./promotion-output"
```

To generate fillable real-evidence templates for platform metrics, comments, published URLs, orders, and revenue:

```bash
python scripts/real_evidence_setup.py \
  --publish-queue "./promotion-output/reports/promotion-manager/publish-queue/publish-queue.json" \
  --publish-readiness "./promotion-output/reports/promotion-manager/publish-readiness/publish-readiness.json" \
  --out-dir "./promotion-output"
```

To build one safe launch unlock pack for platform access, publish setup, browser-assisted publishing, and real evidence collection:

```bash
python scripts/launch_unlock_pack.py \
  --publish-queue "./promotion-output/reports/promotion-manager/publish-queue/publish-queue.json" \
  --publish-readiness "./promotion-output/reports/promotion-manager/publish-readiness/publish-readiness.json" \
  --out-dir "./promotion-output"
```

The unlock pack writes a checklist, next-action commands, credential variable-name templates, browser payload references, and real-evidence templates. It does not read or store secret values and does not bypass account authorization.

To prepare browser-assisted publishing payloads for Zhihu, Xiaohongshu, Douyin, TikTok, or other non-official direct-publish platforms:

```bash
python scripts/browser_publish_assistant.py \
  --publish-queue "./promotion-output/reports/promotion-manager/publish-queue/publish-queue.json" \
  --out-dir "./promotion-output"
```

To run one browser-assisted publish session that prepares payloads, optionally fills visible fields, writes screenshots, and stops before final publish:

```bash
python scripts/browser_publish_session.py \
  --publish-queue "./promotion-output/reports/promotion-manager/publish-queue/publish-queue.json" \
  --platform-publish-url "xiaohongshu=https://creator.xiaohongshu.com/" \
  --run-form-fill \
  --out-dir "./promotion-output"
```

To fill visible publisher form fields from one prepared payload and stop before final publish:

```bash
python scripts/browser_publish_form_fill.py \
  --payload-json "./promotion-output/reports/promotion-manager/browser-publish/payloads/xiaohongshu.payload.json" \
  --out-dir "./promotion-output"
```

After the user publishes manually or in a user-visible browser session, register the real URL through the same assistant:

```bash
python scripts/browser_publish_assistant.py \
  --publish-queue "./promotion-output/reports/promotion-manager/publish-queue/publish-queue.json" \
  --published-url "xiaohongshu=https://www.xiaohongshu.com/explore/real-note-id" \
  --evidence "./screenshots/xhs-published.png" \
  --out-dir "./promotion-output"
```

To audit official publishing and metrics access paths before claiming full automation:

```bash
python scripts/platform_access_audit.py --out-dir "./promotion-output"
```

To refresh official documentation reachability during that audit:

```bash
python scripts/platform_access_audit.py --check-live --out-dir "./promotion-output"
```

To run one full local promotion cycle from product intake through publish queue, published URL registration, and real metrics recovery:

```bash
python scripts/promotion_cycle_runner.py \
  --browser-url "https://example.com/product" \
  --platforms youtube,zhihu,xiaohongshu,douyin,github \
  --github-repo owner/repo \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

To include public post-publish metric capture, comment evidence capture, and business attribution in that same cycle:

```bash
python scripts/promotion_cycle_runner.py \
  --browser-url "https://example.com/product" \
  --published-url "xiaohongshu=https://www.xiaohongshu.com/explore/real-note-id" \
  --run-post-publish-metrics-capture \
  --run-comment-evidence-capture \
  --run-business-attribution \
  --run-next-round-optimization \
  --business-csv "./orders-and-revenue.csv" \
  --out-dir "./promotion-output"
```

To audit final-agent readiness before a real run:

```bash
python scripts/final_capability_audit.py --out-dir "./promotion-output"
```

To audit controlled self-evolution, local tool gaps, repository state, and installed Skill drift:

```bash
python scripts/self_evolution_audit.py --out-dir "./promotion-output"
```

To explicitly install the allowlisted browser runtime if missing:

```bash
python scripts/final_capability_audit.py \
  --install-safe-missing-tools \
  --safe-install playwright_chromium \
  --out-dir "./promotion-output"
```

To sync reviewed local Skill files into the installed Codex Skill after verification:

```bash
python scripts/self_evolution_audit.py \
  --sync-installed-skill \
  --approval I_APPROVE_SKILL_SYNC \
  --out-dir "./promotion-output"
```

To authorize and upload a YouTube video without saving tokens:

```bash
python -m pip install -r requirements-youtube.txt
```

```bash
python scripts/youtube_oauth_publish.py \
  --env-file "C:/path/to/.env" \
  --video-file "./promotion-output/videos/product-youtube.mp4" \
  --title "Product launch draft" \
  --out-dir "./promotion-output"
```

The YouTube official publishing port uses `google-api-python-client` with the YouTube Data API `videos.insert` method and the `https://www.googleapis.com/auth/youtube.upload` scope. It remains dry-run-first unless official OAuth credentials, account authorization, a video file, `I_APPROVE_PUBLISH=true`, and `PUBLISH_DRY_RUN=false` are present.

The command writes:

- `docs/promotion-manager/01-platform-publishing-feasibility.md`
- `docs/promotion-manager/02-github-reference-projects.md`
- `docs/promotion-manager/03-platform-risk-matrix.md`
- `docs/promotion-manager/04-self-learning-notes.md`
- `docs/promotion-manager/05-browser-extension-roadmap.md`
- `docs/promotion-manager/06-saas-product-roadmap.md`
- `reports/promotion-manager/...` JSON and Markdown reports for research, deconstruction, content, review, publish packs, result input, and retrospective.
- `reports/promotion-manager/agent-run/workflow-manifest.{json,md}` when `scripts/run_promotion_workflow.py` is run.
- `browser-snapshot/product-page-snapshot.json` when `scripts/browser_snapshot.py` or `--browser-url` captures a rendered product page.
- `reports/promotion-manager/intake/product-url-discovery.{json,md}` and `product-url-discovery/product-urls.txt` when `scripts/product_url_discovery.py` discovers likely product URLs from public website links, `robots.txt` sitemap declarations, `/sitemap.xml`, or direct sitemap URL/file input.
- `reports/promotion-manager/intake/product-url-reader.{json,md}`, `product-url-reader/<id>/structured-product-page.json`, and optionally `product-url-reader/<id>/web-reader-page.md` when `scripts/product_url_reader.py` reads product URLs into browser-visible structured snapshots, static profiles, or public web-text fallback profiles.
- `reports/promotion-manager/batch/product-batch-runner.{json,md}` and `product-batch-runs/<id>/...` when `scripts/product_batch_runner.py` discovers or reads multiple product URLs first, runs one promotion cycle per ready product, and optionally runs multi-query viral discovery and next-round optimization per product.
- `search-snapshots/browser-search/<platform>.json` and `reports/promotion-manager/competitors/browser-search-snapshots.{json,md}` when `scripts/platform_search_browser.py` or `--auto-search-competitors` captures public search pages.
- `reports/promotion-manager/competitors/viral-discovery-run.{json,md}` when `scripts/viral_discovery_runner.py` runs keyword search, browser-visible capture, viral library creation, creator leaderboard generation, optional follow-up capture, and optional video frame sampling as one standalone discovery pass. Its `coverage` records search captures, queued follow-up modes, imported deep records, browser-visible capture successes, and video sample frame counts.
- `reports/promotion-manager/competitors/multi-query-viral-discovery.{json,md}`, `multi-query-viral-content-library.{json,md}`, and `multi-query-creator-leaderboard.{json,md}` when `scripts/multi_query_viral_discovery.py` runs product-driven multi-query discovery and merges ranked materials and creators. Its summary carries the per-query deep evidence and video sampling coverage up to product batch and final readiness reports.
- `reports/promotion-manager/competitors/viral-evidence-inbox-setup/viral-evidence-inbox-setup.{json,md}` and `viral-evidence-inbox/*` when `scripts/viral_evidence_inbox_setup.py` creates fillable competitor evidence files without seeding fake creators or metrics.
- `reports/promotion-manager/competitors/viral-evidence-inbox/viral-evidence-inbox.{json,md}` when `scripts/viral_evidence_inbox.py` imports user-provided competitor URLs, visible text, transcripts, exports, or OCR text into captured search reports, the viral content library, and the creator leaderboard.
- `reports/promotion-manager/competitors/captured-search-results-<platform>.{json,md}` when `scripts/platform_search_capture.py` captures search evidence.
- `reports/promotion-manager/competitors/viral-content-library.{json,md}` and `follow-up-capture-tasks.{json,md}` when `scripts/viral_content_library.py` ranks captured search evidence.
- `reports/promotion-manager/competitors/creator-leaderboard.{json,md}` and `creator-follow-up-tasks.{json,md}` when `scripts/creator_leaderboard.py` groups viral materials by creator/account and creates safe tracking tasks.
- `reports/promotion-manager/competitors/creator-follow-up-results.{json,md}` and `creator-deep-library.{json,md}` when `scripts/creator_follow_up_runner.py` runs safe public creator/account follow-up research or queues manual evidence.
- `reports/promotion-manager/competitors/follow-up-capture-results.{json,md}` and `deep-competitor-library.{json,md}` when `scripts/follow_up_capture_runner.py` executes safe follow-up captures.
- `reports/promotion-manager/competitors/follow-up-captures/<task>/browser-visible-snapshot.json` when browser-assisted follow-up capture opens a public platform URL and imports browser-visible page evidence.
- `reports/promotion-manager/competitors/video-sampling/browser-video-sampler.{json,md}` and `video-sampling/frames/*.png` when `scripts/browser_video_sampler.py` captures browser-visible video metadata and frame screenshots. When run from follow-up captures, the same files are written under `follow-up-captures/<task>/reports/promotion-manager/competitors/video-sampling/`, and safe `videoSampleEvidence` is copied into `deep-competitor-library.json` for downstream script/storyboard deconstruction.
- `reports/promotion-manager/generated-content/<product>-competitor-informed-content.{json,md}` and `<product>-competitor-informed-strategy.json` when `scripts/competitor_content_enhancer.py` rewrites generated content from observed viral patterns. The workflow writes this back to `<product>-platform-content.json` before video rendering unless `--skip-competitor-informed-content` is supplied.
- `reports/promotion-manager/media-assets/media-asset-pack.{json,md}` and `media-assets/<platform>/*.png` when `scripts/media_asset_pack.py` generates cover/detail PNG assets and writes video, cover, detail image, first-batch, and `assets` references back into the publish pack.
- `reports/promotion-manager/cheat-review/<product>-cheat-review-pack.{json,md}` and `cheat-review/drafts/*.md` when `scripts/promotion_manager.py review|all` prepares platform drafts for Codex `cheat-score` without writing prediction logs.
- `reports/promotion-manager/publish-queue/publish-queue.{json,md}` and per-platform drafts when `scripts/publish_queue.py` prepares official dry-runs and manual/browser-assisted tasks.
- `reports/promotion-manager/publish-readiness/publish-readiness.{json,md}` when `scripts/publish_readiness_runner.py` audits queue status, credential presence by environment variable name, target readiness, approval status, and next actions.
- `reports/promotion-manager/publish-setup/publish-setup.{json,md}`, `publish-credentials.example.env`, `publish-setup-checklist.md`, and `platform-setup-guide.{json,md}` when `scripts/publish_setup_assistant.py` turns readiness into credential names, target requirements, official setup references, approval gates, and next commands without storing secret values.
- `reports/promotion-manager/real-evidence-setup/real-evidence-setup.{json,md}`, `real-evidence-checklist.md`, `templates/*`, and `commands/import-real-evidence.ps1` when `scripts/real_evidence_setup.py` creates fillable platform metrics, comment, published URL, and business attribution evidence templates.
- `reports/promotion-manager/launch-unlock/launch-unlock.{json,md}`, `launch-unlock-checklist.md`, and `commands/launch-unlock-next-actions.ps1` when `scripts/launch_unlock_pack.py` combines platform access, publish setup, browser-assisted publishing, and real-evidence setup into one safe operator pack.
- `reports/promotion-manager/real-evidence-inbox-setup/real-evidence-inbox-setup.{json,md}` and `promotion-evidence-inbox/*` when `scripts/real_evidence_inbox_setup.py` creates fillable inbox files and import commands without fabricating metrics, comments, orders, or revenue.
- `reports/promotion-manager/real-evidence-inbox/real-evidence-inbox.{json,md}` and normalized helper files when `scripts/real_evidence_inbox.py` scans a local evidence folder, registers published URLs, imports metrics/comments/orders/revenue, and runs next-round optimization.
- `reports/promotion-manager/browser-publish/browser-publish-assistant.{json,md}` and `payloads/*` when `scripts/browser_publish_assistant.py` prepares user-visible publish payloads, form-fill helpers, browser form-fill commands, checklists, and optional real URL registration for manual/browser-assisted platforms.
- `reports/promotion-manager/browser-publish/browser-form-fill.{json,md}` and `browser-form-fill.png` when `scripts/browser_publish_form_fill.py` fills visible publisher fields from one prepared payload and stops before final publish.
- `reports/promotion-manager/browser-publish-session/browser-publish-session.{json,md}` and per-platform form-fill reports when `scripts/browser_publish_session.py` orchestrates payload preparation, optional visible-field fill, screenshots, final publish checklist, and post-publish evidence commands.
- `reports/promotion-manager/platform-access/platform-access-audit.{json,md}` when `scripts/platform_access_audit.py` maps official API, app-review, manual/browser-assisted, and metrics access boundaries. With `--check-live`, it also records official documentation reachability, UTC check time, `learningFreshness`, and `officialDocGapResearch` so missing official sources stay on safe manual/browser/export fallbacks instead of being treated as automation-ready.
- `reports/promotion-manager/publish-capture/publish-url-capture.{json,md}` when `scripts/publish_url_capture.py` captures a browser-visible published page and registers the real URL.
- `reports/promotion-manager/published-items/published-items.{json,md}` when `scripts/published_items.py` registers proven published URLs from queue execution reports or manual evidence.
- `reports/promotion-manager/post-publish-capture/post-publish-metrics-capture.{json,md}`, `post-publish-metrics-export.json`, and `post-publish-metrics-snapshot.json` when `scripts/post_publish_metrics_capture.py` captures public/browser-visible metrics from registered published URLs.
- `reports/promotion-manager/comment-evidence/comment-evidence-capture.{json,md}` and `comment-evidence-export.json` when `scripts/comment_evidence_capture.py` captures public/browser-visible comments and demand signals.
- `reports/promotion-manager/business-attribution/business-attribution.{json,md}` and `business-attribution-export.json` when `scripts/business_attribution.py` attributes real business exports to proven published content using URL, UTM content, referrer, or title/campaign evidence.
- `reports/promotion-manager/metrics-recovery/metrics-recovery.{json,md}` when `scripts/metrics_recovery.py` coordinates official metrics connectors and business exports.
- `reports/promotion-manager/optimization/next-round-optimization.{json,md}` when `scripts/next_round_optimizer.py` converts real metrics, comment demand signals, and business attribution into next-round content angles, platform actions, and copy-ready commands.
- `reports/promotion-manager/performance-monitor/performance-monitor.{json,md}` and `performance-monitor-history.jsonl` when `scripts/performance_monitor.py` orchestrates public metric capture, comment capture, business attribution, metrics recovery, and next-round optimization for registered published URLs.
- `reports/promotion-manager/cycle/promotion-cycle.{json,md}` when `scripts/promotion_cycle_runner.py` runs the workflow, publish queue, published item registration, optional post-publish metrics capture, optional comment evidence capture, optional business attribution, optional next-round optimization, and metrics recovery as one local operating cycle.
- `reports/promotion-manager/real-run-playbook/real-run-playbook.{json,md}` and `real-run-commands.ps1` when `scripts/real_run_playbook.py` generates a copy-ready live-run command pack, evidence checklist, platform gates, and approval gates for a real product cycle.
- `reports/promotion-manager/skill-entry/skill-entry.{json,md}` when `scripts/skill_entry.py` runs the Codex-facing one-link entry through real-run playbook generation, final capability execution, and final readiness refresh.
- `reports/promotion-manager/final-run/final-capability-run.{json,md}` when `scripts/final_capability_runner.py` runs the highest-automation safe flow: Codex-first product reading, promotion cycles, multi-query viral discovery, publish readiness, launch unlock packs, browser-assisted publish payloads, optional visible-field form fill, real evidence recovery, next-round optimization, and audits. The report includes `cycleEvidence[]`, a per-product manager-facing rollup of generated content, videos, publish queues, launch unlock packs, published URL registration, public metrics, comments, business attribution, and next-round recommendations.
- `reports/promotion-manager/final-readiness/final-capability-readiness.{json,md}` when `scripts/final_capability_readiness.py` merges final-run, final-audit, publish-readiness, publish-setup, platform-access, and self-evolution reports into a requirement-by-requirement end-state matrix, phase progress reporting row, and action queue.
- `reports/promotion-manager/capability/final-capability-audit.{json,md}` when `scripts/final_capability_audit.py` checks scripts, tools, credential presence, platform limits, and final requirement gaps.
- `reports/promotion-manager/self-evolution/self-evolution-audit.{json,md}` when `scripts/self_evolution_audit.py` checks local tools, repository state, installed Skill drift, safe install candidates, platform-learning freshness, and approved Skill sync actions.
- `reports/promotion-manager/billing-simulator/billing-simulator.{json,md}` and `billing-simulator-state.json` when `scripts/billing_contract_simulator.py` validates the extension billing contract, hashed license storage, usage reservation, hosted run acceptance, usage commit, and simulated webhook flow.
- `promotion-output/automation/scheduler/automation-run.{json,md}` and `promotion-automation-state.json` when `scripts/automation_scheduler.py` runs scheduled jobs.
- `videos/*.mp4` only when `scripts/render_video.py` is run and `ffmpeg` is available.
- `media-assets/<platform>/*.png` when `scripts/media_asset_pack.py` runs and Pillow is available.
- `README.md`, `README.en.md`, `docs/*.md`, `browser-extension/*`, and `scripts/package_browser_extension.py` as the public GitHub docs and store-ready browser extension package when syncing the installed Skill.

## Workflows

### 1. Product URL Intake

- Extract factual product information from the page.
- Mark uncertain details as assumptions; do not invent pricing, testimonials, sales, or usage numbers.
- If a page cannot be read, ask for pasted product info.
- Use `scripts/product_intake.py` for deterministic metadata extraction from public HTML, saved product pages, rendered page text, or structured page snapshots captured by Codex/browser tooling.
- Use `scripts/browser_snapshot.py` or `scripts/run_promotion_workflow.py --browser-url` when the product page is dynamic or Codex needs rendered DOM evidence before intake.
- Use `scripts/product_url_reader.py` when the user sends one or more product URLs and wants Codex to read the rendered page first, write a structured snapshot, pass it into `product_intake.py`, and return a product profile plus the correct next workflow command. If browser and static intake both fail for a public URL, it may use public web-text fallback and pass the saved text file to the workflow; this source is marked `web_text_fallback` and can be disabled with `--disable-web-text-fallback`.
- Use `scripts/product_url_discovery.py` when the user sends a website/homepage URL and wants the Skill to find likely product URLs first. It uses public HTML links, public `robots.txt` sitemap declarations, `/sitemap.xml`, or direct sitemap URL/file input, filters obvious non-product pages, and writes `product-url-discovery/product-urls.txt` for follow-up reading.
- Use `scripts/product_batch_runner.py` when the user sends multiple product URLs, a URL file, or a website URL via `--discover-from-url`, and wants the Skill to read each URL first, then run a guarded promotion cycle for every ready product. Add `--run-multi-query-viral-discovery` when each product should also derive multiple search queries and merge viral materials/creators after the cycle. Add `--sample-video-frames` for per-cycle follow-up video evidence, or `--multi-query-sample-video-frames` for the post-cycle multi-query discovery pass. Add `--run-next-round-optimization` with real published URLs, public/browser-visible metrics, comment evidence, or business exports when each product cycle should produce next-round recommendations.
- Use `scripts/skill_entry.py` when the user sends one link and says to execute the Skill. It defaults to `--link-mode auto`, generates a real-run playbook, runs `scripts/final_capability_runner.py` with safe high-automation defaults, refreshes `scripts/final_capability_readiness.py`, and writes a manager-facing run summary.
- `scripts/skill_entry.py` passes real evidence files and browser-assisted comment capture flags through to the final runner, including `--comment-evidence-install-browser-if-missing` when the official Playwright Chromium runtime can be installed on a trusted machine.
- Use `scripts/real_run_playbook.py` before the first live run for a product or website. It writes a command pack that sequences final capability runner, publish readiness/setup, browser-assisted publishing, approved official publishing, real URL registration, public metrics/comment capture, business attribution, metrics recovery, next-round optimization, periodic operation, and controlled self-evolution. It records approval gates and evidence requirements; it does not execute platform writes.
- Use `scripts/final_capability_runner.py` when the user says "execute the Skill", "run the full promotion manager", or wants the highest-automation safe path from product URL or discovered website product URLs to publish queue, browser-assisted publish payloads, optional visible-field form fill, metrics/comment/business recovery, next-round optimization, and readiness audits. Add `--discover-from-url` when the user provides a website/homepage rather than exact product URLs. Use `--sample-video-frames` and `--multi-query-sample-video-frames` when the final run should carry browser-visible video sampling through product cycles and multi-query viral discovery.
- Use `scripts/final_capability_readiness.py` after a final run or audit when you need a single acceptance matrix for the requested final Agent scope. It identifies which requirements are satisfied, which need real run evidence, which are blocked by platform authorization, and which exact commands or approvals are next. It also includes the phase progress reporting requirement, with required fields for current stage, completed goals, unfinished goals, next plan, and estimated remaining time. For viral research, it distinguishes search-only evidence, deep competitor records, browser-visible capture successes, and real video frame samples. For real performance recovery, it distinguishes full-funnel evidence from social-only, business-only, or incomplete evidence across views, likes, comments, orders, and revenue. For controlled self-evolution, it reports whether official platform access docs were freshly live-checked and whether the platform-access audit has unresolved official doc gap research before changing publishing or metrics executors.
- Use `scripts/final_capability_audit.py` before claiming final-agent readiness. The audit checks local scripts, browser runtime, `ffmpeg`, credential presence, publish constraints, metrics inputs, and self-evolution limits without writing credential values. It also runs `scripts/self_evolution_audit.py` and records the self-evolution report path.
- Use `scripts/self_evolution_audit.py` when the Skill needs to inspect local tool gaps, repo/installed-Skill drift, safe runtime install candidates, or approved local Skill sync actions.
- Prefer `scripts/run_promotion_workflow.py` for a full run. It calls product intake first and writes an agent workflow manifest.

### 2. Competitor And Trend Research

- For YouTube and GitHub, prefer official/public pages and APIs when available.
- For Zhihu, Xiaohongshu, and Douyin, use manual links, browser-assisted review, or user-provided screenshots/content where automated access is risky.
- Save findings in the output reports. Do not claim a platform API exists without official evidence.
- For detailed routing, read [references/platform-publishing.md](references/platform-publishing.md).
- Use the script `research` command first when platform feasibility or self-learning notes are needed.
- Use `scripts/competitor_discovery.py` to create platform search tasks and optional official API search results before importing evidence.
- Use `scripts/competitor_collector.py` to automatically collect YouTube official API evidence or GitHub public API evidence when credentials/access allow.
- Use `scripts/platform_search_browser.py` or `scripts/run_promotion_workflow.py --auto-search-competitors` to create browser-visible public search snapshots for YouTube, Zhihu, Xiaohongshu, Douyin, GitHub, TikTok, and similar platforms.
- Use `scripts/viral_discovery_runner.py` when the user specifically asks to automatically find viral creators, posts, videos, or repositories from a keyword before product copy generation. It chains browser-visible platform search, normalized capture, ranked viral library creation, creator leaderboard generation, and optional follow-up queues.
- Use `scripts/multi_query_viral_discovery.py` when one keyword is too narrow. It derives queries from the product profile, value proposition, keywords, audience, and pain points; runs or plans one discovery pass per query; then dedupes and ranks the merged viral materials and creator leaderboard.
- Use `scripts/viral_evidence_inbox_setup.py` when automatic/browser search cannot reliably collect enough real competitor evidence from risk-controlled platforms. It creates empty templates and import commands only.
- Use `scripts/viral_evidence_inbox.py` after real competitor URLs, visible text, transcripts, exports, or OCR text have been placed in the inbox. It normalizes the evidence into captured search reports and reruns the viral library and creator leaderboard. Screenshot files alone are recorded as `manual_text_required`.
- Use `scripts/platform_search_capture.py` to normalize multi-result rendered search snapshots for YouTube, Zhihu, Xiaohongshu, Douyin, GitHub, TikTok, or similar platforms. It parses visible English/Chinese metrics and creator audience labels from search evidence for ranking; missing metrics remain missing.
- Use `scripts/viral_content_library.py` after search capture to rank top viral materials across platforms and create follow-up capture tasks. Public YouTube/GitHub URLs become safe capture candidates; Zhihu, Xiaohongshu, Douyin, and TikTok stay browser-assisted/user-export tasks unless official access is verified. Preserve `contentDeconstruction` as the primary hook/beat/video-architecture evidence for later copy and script generation.
- Use `scripts/creator_leaderboard.py` after the viral library exists to identify high-signal creators/accounts, aggregate their observed public metrics, and create creator follow-up tasks. The full workflow does this automatically unless `--skip-creator-leaderboard` is supplied.
- Use `scripts/creator_follow_up_runner.py` after the creator leaderboard exists to run safe YouTube/GitHub creator follow-up through official/public connectors and queue manual/browser evidence requests for Zhihu, Xiaohongshu, Douyin, TikTok, and unverified platforms. In the full workflow, add `--run-creator-follow-up`; use `--creator-follow-up-dry-run` for planning-only runs.
- Use `scripts/follow_up_capture_runner.py` to execute only safe public follow-up capture tasks and generate manual evidence request files for browser-assisted platforms. In the full workflow, add `--run-follow-up-captures` when you want this stage to run.
- Add `--capture-browser-assisted` to `scripts/follow_up_capture_runner.py`, or `--capture-browser-assisted-follow-ups` to the full workflow, when queued Zhihu, Xiaohongshu, Douyin, TikTok, or similar follow-up tasks should attempt public browser-visible snapshots before falling back to manual evidence requests.
- Add `--sample-video-frames` and `--video-sample-count 5` to `scripts/follow_up_capture_runner.py`, `scripts/viral_discovery_runner.py`, `scripts/multi_query_viral_discovery.py`, `scripts/run_promotion_workflow.py`, `scripts/promotion_cycle_runner.py`, `scripts/product_batch_runner.py`, or `scripts/final_capability_runner.py` when YouTube, Douyin, TikTok, or other video-like follow-up tasks should capture browser-visible video metadata and frame screenshots. In product batch and final runs, use `--multi-query-sample-video-frames` and `--multi-query-video-sample-count 5` for the separate multi-query discovery stage. When Douyin, Xiaohongshu, or similar dynamic search pages time out while waiting for `networkidle`, pass `--browser-search-wait-until domcontentloaded` to `viral_discovery_runner.py`/`multi_query_viral_discovery.py`, or `--multi-query-browser-search-wait-until domcontentloaded` to `product_batch_runner.py`/`final_capability_runner.py`. Successful follow-up imports copy `videoSampleEvidence` into deep competitor records so the enhancer can report frame-backed evidence. This does not download private media streams or store signed media query tokens.
- Use `scripts/browser_video_sampler.py` directly when the user provides a specific public/browser-visible video URL and wants frame evidence before deconstruction.
- Use `scripts/competitor_content_enhancer.py` after the viral/deep libraries exist to apply observed hooks, reusable patterns, content deconstruction summaries, and safe structure roles to the generated platform content. The full workflow does this automatically when a library exists; use `--skip-competitor-informed-content` to disable it.
- Use `scripts/competitor_intake.py` to turn public competitor pages, saved HTML, JSON exports, or pasted transcripts into `imported-competitors` reports before deconstruction. Imported records include `contentDeconstruction` with ordered beats, copy mechanics, optional video architecture, reuse guidance, and evidence confidence.

### 3. Content Generation

Generate platform-native material:

- YouTube: long-video titles, Shorts titles, descriptions, scripts, tags.
- Zhihu: long-form article titles, outlines, opening, CTA.
- Xiaohongshu: note titles, post bodies, cover text, tags, comment prompts.
- Douyin: 30-second hooks, voiceover scripts, storyboard, captions, hashtags.
- GitHub: README promotion copy, Release/Issue/Discussion drafts.
- Every publish package item must expose the direct publication payload fields: viral title, copy, tags, first-batch comments/replies, video status/path, cover image, detail images, and the consolidated `assets` list.

When competitor search evidence exists, generated drafts should include `competitorInformed` metadata and should preserve source titles/hooks/deconstruction summaries as evidence metadata only. Reuse structure and beat functions; do not copy competitor wording or transfer competitor metrics into product claims.

When the user asks for a video file, run `scripts/render_video.py` to create an MP4 from the generated content JSON. Use `--voiceover-audio` for a real recorded/AI voiceover file, or `--generate-voiceover` on Windows for review-quality system TTS. Without either option the renderer creates a silent captioned artifact.
After video rendering, run `scripts/media_asset_pack.py` or the full workflow so the publish pack also receives PNG cover images, PNG detail images, video path/status, and a machine-readable media asset manifest.

### 4. Review And Score

Score every platform draft for:

- viral potential
- title/hook strength
- clarity
- conversion CTA
- platform fit
- SEO/GEO value
- compliance risk

If `cheat-on-content` is available, run a qualitative review through that skill. Do not write immutable prediction logs unless the user explicitly asks to start a real `cheat-on-content` prediction cycle. For details, read [references/cheat-on-content-integration.md](references/cheat-on-content-integration.md).
The built-in promotion review writes `reports/promotion-manager/cheat-review/<product>-cheat-review-pack.{json,md}` plus per-platform draft files under `cheat-review/drafts/`. Treat those files as the handoff to Codex `cheat-score`; they are review inputs, not proof that a prediction cycle has started.

### 5. Publish Pack

Every publish pack must include:

- viral title / explosive title candidate
- final copy/body for the platform
- platform tags/hashtags
- first-batch comments, pinned comment, reply prompts, and launch actions
- video object with required/status/path
- cover image object with status/path/cover text
- detail image list
- consolidated `assets` list for browser/manual publishing
- `publishMode`: `official_api_publish`, `browser_assisted_publish`, `manual_publish_required`, or `unsupported`
- `approvalRequired: true`
- manual steps
- warnings
- `trackingPlan` with `campaignId`, `contentId`, `trackedUrl`, UTM fields, business-export match keys, recommended export columns, and the no-inferred-revenue guardrail
- tracking fields for published URL, tracked URL, UTM fields, real engagement, orders, revenue, and evidence
- schedule suggestion

YouTube and GitHub have active official API executor paths, but execution still requires platform credentials, user authorization, and explicit approval. Douyin, Zhihu, and Xiaohongshu remain manual or browser-assisted unless current official creator-publishing evidence proves otherwise.
For full-automation boundaries, read [references/final-capability-boundaries.md](references/final-capability-boundaries.md).
Use `scripts/publish_executor.py` for supported official publishing actions. It defaults to dry-run and only writes when `--execute --approval I_APPROVE_PUBLISH` is supplied with the required environment token.
For Douyin, `scripts/publish_queue.py --douyin-video-file ...` attaches the MP4 to the browser-assisted payload and does not call the official API executor. `scripts/publish_executor.py --platform douyin` remains only as a reserved future official upload/create port.
Use `scripts/youtube_credential_check.py` first when the user says YouTube credentials are configured. It distinguishes `ready`, `blank`, and `missing` credential groups without writing secret values.
Use `scripts/youtube_oauth_publish.py` when the user needs the full YouTube OAuth consent flow before upload. It requires `GOOGLE_OAUTH_CLIENT_ID`/`YOUTUBE_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`/`YOUTUBE_CLIENT_SECRET` for execution and does not save OAuth tokens.
Use `scripts/publish_queue.py` after a workflow run to convert publish packs into executable GitHub/YouTube dry-runs plus manual/browser-assisted queue records for Douyin, Zhihu, Xiaohongshu, and other unsupported direct-publish platforms. `--douyin-video-file` only attaches a rendered MP4 asset to the Douyin payload.
Use `scripts/publish_readiness_runner.py` after a workflow run or existing publish queue to produce a machine-checkable readiness report before execution. It may build the guarded queue first with `--build-queue`; it records credential presence only by environment variable name and still requires `--execute-publish --approval I_APPROVE_PUBLISH` before official writes. `scripts/final_capability_runner.py` and `scripts/skill_entry.py` can pass the same gated execution request down to publish readiness.
Use `scripts/publish_setup_assistant.py` after publish readiness to write a publish setup kit: platform-by-platform credential environment variable names, target gaps, official setup references, approval gates, rerun/execution commands, `publish-credentials.example.env`, `publish-setup-checklist.md`, and `platform-setup-guide.{json,md}`. It never writes credential values.
Use `scripts/launch_unlock_pack.py` after publish readiness or a publish queue exists when the operator wants one consolidated safe setup package. It runs platform access audit, publish setup, real evidence setup, browser publish payload preparation, and writes a launch checklist plus next commands without reading credential values or performing platform writes.
Use `scripts/browser_publish_assistant.py` after `publish_queue.py` to prepare browser-assisted payload files, platform entry URLs, generic form-fill helper scripts, browser form-fill commands, and post-publish URL registration commands for Zhihu, Xiaohongshu, Douyin, TikTok, or similar platforms. It may open publisher entry URLs in the user's default browser with `--open-browser`, but it must not auto-login, solve captcha, or click the final publish button.
Use `scripts/browser_publish_form_fill.py` only on a prepared payload JSON when the user wants Codex to fill visible publisher fields. It writes a screenshot and report, does not submit the form, and must stop for login, captcha, risk control, account verification, or final publish.
Use `scripts/platform_access_audit.py` when you need a machine-readable official access boundary report for YouTube, Zhihu, Xiaohongshu, Douyin, GitHub, and TikTok before deciding whether a platform can be automated or must remain manual/browser-assisted. Add `--check-live` when the decision depends on current official documentation; live reachability is evidence for documentation existence, not account authorization.
Use `scripts/published_items.py` after a manual/browser-assisted publish to register the real published URL and evidence. `scripts/publish_queue.py` also writes a `published-items` report automatically; dry-runs and queued tasks remain pending, not published.
Use `scripts/publish_url_capture.py` when Codex or the user has a post-publish browser snapshot, saved HTML, or copied page text. It extracts the real platform URL/title, blocks draft or preview URLs, and updates `published-items` for metrics recovery.
Use `scripts/post_publish_metrics_capture.py` after real published URLs are registered. It fetches public pages or browser-visible snapshots, extracts visible views/likes/comments/saves/shares/clicks/leads/orders/revenue when present, including English and Chinese labels with `k/m/b`, `万/亿/千/百`, and common currency symbols, writes a `post-publish-metrics-export.json` file for `metrics_recovery.py`, and queues manual evidence when login/captcha/private analytics are required.
Use `scripts/promotion_cycle_runner.py` when the user wants one command to run generation, guarded publish queue, published URL registration, optional public metrics capture, optional comment evidence capture, optional business attribution, metrics recovery, and next-round optimization. Add `--run-next-round-optimization` to write `next-round-optimization.json` after recovery. Official GitHub/YouTube writes still require `--execute-publish --approval I_APPROVE_PUBLISH` plus credentials; Douyin, dry-runs, and other manual/browser-assisted tasks remain pending rather than published.

### 6. Retrospective

Use only real data supplied by the user or exported from platforms:

- views
- likes
- favorites
- comments
- shares
- clicks
- messages
- leads
- orders
- revenue
- evidence URLs/screenshots/exports

If no real data exists, output `waiting_real_data`. Never estimate or fabricate performance.
Excel `.xlsx` platform and business exports are valid real-data inputs through `metrics_intake.py --xlsx-file`, `metrics_recovery.py --metrics-xlsx`, and `metrics_recovery.py --business-xlsx`.
Use `scripts/metrics_intake.py` to import real CSV, JSON, text, Codex/browser structured snapshots, GitHub, or YouTube metrics before doing a retrospective. It parses visible English/Chinese metric labels and common units/currency (`12K`, `2.4M`, `1.2万`, `3亿`, `$88.00`, `￥88.00`) from text and structured snapshots. YouTube live metrics require `YOUTUBE_API_KEY`; GitHub public repository metrics can use the public REST API.
Use `scripts/metrics_recovery.py` when the run has a workflow manifest, publish queue, `published-items` report, published URL list, structured metric snapshot, or business export. It merges official GitHub/YouTube metrics with user-provided platform snapshots and orders/revenue exports, and marks Zhihu, Xiaohongshu, Douyin, TikTok, or unpublished queue items as `manual_export_required` or `publish_pending` instead of inventing data.
Use `scripts/real_evidence_inbox_setup.py` before or immediately after publishing when the operator needs a ready-to-fill evidence folder. It writes empty published URL, metrics, comment, and order/revenue templates plus an inbox manifest and import command. Templates and `.example` files are placeholders only and must not be treated as real evidence.
Use `scripts/real_evidence_inbox.py` when the user has a folder of real evidence files from several platforms. It discovers or reads an optional `inbox-manifest.json`, normalizes published URL evidence, then orchestrates `published_items.py`, `post_publish_metrics_capture.py`, `comment_evidence_capture.py`, `business_attribution.py`, `metrics_recovery.py`, and `next_round_optimizer.py`.
Use `scripts/performance_monitor.py` after published URLs are registered and the user wants a repeatable post-publish monitor. It orchestrates public/browser-visible metrics capture, comment evidence capture, optional business attribution files, metrics recovery, next-round optimization, and a history JSONL without fabricating missing values.
Before a retrospective, run `scripts/post_publish_metrics_capture.py` when `published-items.json` contains real URLs. It captures only public/browser-visible metrics and produces `post-publish-metrics-export.json`; pass that file to `metrics_recovery.py --metrics-json`. If metrics are hidden behind platform analytics, login, captcha, or risk checks, use the generated manual evidence request and import a real export or screenshot-derived text.
Run `scripts/comment_evidence_capture.py` after real published URLs or visible comment exports exist. It extracts public/browser-visible comments, likes/replies per comment when visible, and demand signals such as questions, pricing objections, integrations, feature requests, pain points, and CTA intent. Treat its manual evidence requests as missing evidence, not recovered comments.
Run `scripts/business_attribution.py` when orders or revenue are exported from a business system with UTM fields, referrers, content IDs, or campaign/title fields. It attributes only rows that match proven published content and leaves weak platform-only rows unmatched.
Run `scripts/next_round_optimizer.py` after `metrics_recovery.py`, `comment_evidence_capture.py`, or `business_attribution.py` has produced real evidence. It outputs `waiting_real_data` when no metrics, comments, or attribution exist; otherwise it ranks winners, summarizes demand signals, proposes next titles/hooks/script briefs, and emits copy-ready commands for the next cycle. Treat `partial_ready` as usable but incomplete when some platforms still require manual evidence.

### 7. Periodic Automation

Use `scripts/automation_scheduler.py` to run one or more product promotion jobs on a local schedule. The scheduler reads a JSON config, decides which jobs are due, calls `scripts/run_promotion_workflow.py`, writes a state file, and writes an automation run report. It can also generate a PowerShell script for Windows Task Scheduler.

The scheduler may generate content, videos, publish packs, official dry-run publish plans, and metrics import attempts. It must not bypass the publish approval gate. Official writes still require the publish executor, environment credentials, and `--approval I_APPROVE_PUBLISH`.
If a scheduled job has `publish.enabled: true`, the scheduler runs `scripts/publish_queue.py` after a successful workflow and records the queue report path in state. This still defaults to dry-run unless the job explicitly enables execution and supplies the approval phrase.
Scheduled jobs can set `publish.douyin.videoFile` to pass a rendered MP4 into the Douyin browser-assisted/manual payload; it does not enable official API publishing.
If a scheduled job has `browserPublishAssistant.enabled: true`, the scheduler runs `scripts/browser_publish_assistant.py` after publish queue generation and records the browser/manual payload report path in state.
If a scheduled job has `browserFormFill.enabled: true`, the scheduler runs `scripts/browser_publish_form_fill.py` for each prepared browser-publish payload after `browserPublishAssistant` finishes. It fills visible fields only, writes per-platform screenshots/reports under `browser-form-fill-runs/`, records `lastBrowserFormFill` in state, and still requires the user to review and perform the final publish action.
If a scheduled job has `postPublishMetricsCapture.enabled: true`, the scheduler runs `scripts/post_publish_metrics_capture.py` after published URL registration and before metrics recovery. Captured metrics are passed into `scripts/metrics_recovery.py` as a JSON metrics source when `metricsRecovery.enabled` is also true.
If a scheduled job has `commentEvidenceCapture.enabled: true`, the scheduler runs `scripts/comment_evidence_capture.py` after the workflow and records the public/browser-visible comment evidence report path in state.
If a scheduled job has `businessAttribution.enabled: true`, the scheduler runs `scripts/business_attribution.py` before metrics recovery and passes `business-attribution-export.json` into `scripts/metrics_recovery.py` when recovery is enabled. Use `businessAttribution.businessCsv`, `businessXlsx`, `businessJson`, or `businessText` for real order/revenue exports.
If a scheduled job has `metricsRecovery.enabled: true`, the scheduler runs `scripts/metrics_recovery.py` after the workflow and optional publish queue, then records the metrics recovery report path in state.
Scheduled jobs can set `metrics.csvFile`, `xlsxFile`, `jsonFile`, or `textFile` for workflow-time metric intake. For post-workflow recovery, use `metricsRecovery.metricsCsv`, `metricsXlsx`, `metricsJson`, `metricsText`, `metricsStructuredJson`, `businessCsv`, `businessXlsx`, `businessJson`, or `businessText` to pass real evidence files when business attribution is not run separately.
If a scheduled job has `nextRoundOptimization.enabled: true`, the scheduler runs `scripts/next_round_optimizer.py` after metrics/comment/business recovery and records `lastNextRoundOptimization` in state.
If a scheduled job has `multiQueryViralDiscovery.enabled: true`, the scheduler runs `scripts/multi_query_viral_discovery.py` after the workflow manifest is created and records the merged discovery report path in state. Use `multiQueryViralDiscovery.dryRun: true` for planning-only recurring research. Use `multiQueryViralDiscovery.sampleVideoFrames: true` and `multiQueryViralDiscovery.videoSampleCount: 5` to carry browser-visible video sampling into that recurring discovery stage.
Scheduled jobs can set `skipCreatorLeaderboard: true` to skip creator/account aggregation after the viral material library.
Scheduled jobs can set `followUpCapture.captureBrowserAssisted: true` to attempt public browser-visible snapshots for queued browser-assisted follow-up tasks.
Scheduled jobs can set `followUpCapture.sampleVideoFrames: true` and `followUpCapture.videoSampleCount: 5` to sample browser-visible video metadata and frame screenshots during follow-up captures.
Scheduled jobs can set `creatorFollowUp.enabled: true` to run safe creator/account follow-up research after the creator leaderboard. Use `creatorFollowUp.dryRun: true` for planning-only runs.
Scheduled jobs can set `competitorInformedContent.enabled: false` to disable rewriting with viral/deep competitor libraries, or `true` to pass the explicit `--use-competitor-informed-content` flag.

## Bundled Resources

- `README.md`: Chinese GitHub-facing project introduction, quick start, install, usage, safety, and extension overview.
- `README.en.md`: English GitHub-facing project introduction with a language switch back to `README.md`.
- `docs/installation.md`: setup and Codex Skill sync tutorial.
- `docs/usage.md`: operator commands for intake, research, publishing, metrics, and next-round optimization.
- `docs/browser-extension.md`: Chrome extension load, store package command, subscription flow, and security notes.
- `docs/extension-store-submission.md`: Chrome Web Store and Microsoft Edge Add-ons submission checklist.
- `docs/zh-CN/browser-extension.md`: Chinese browser extension operator guide.
- `docs/zh-CN/extension-store-submission.md`: Chinese extension store submission guide.
- `docs/subscription-pricing.md`: token-backed subscription pricing assumptions and credit model.
- `docs/billing-backend-contract.md`: checkout, customer portal, license validation, usage ledger, webhook, and loss-control backend contract.
- `docs/final-capability-map.md`: requirement-to-capability map and remaining external gates.
- `docs/100-percent-completion-roadmap.md`: module-by-module gap-to-100% roadmap with Codex scope, operator actions, open-source references, and acceptance evidence.
- `docs/zh-CN/100-percent-completion-guide.md`: beginner-friendly Chinese guide for completing each module to 100% with copy-ready steps and checks.
- `docs/open-source-integration.md`: Firecrawl and AiToEarn integration plan, accepted components, rejected unsafe paths, and next steps.
- `browser-extension/manifest.json`: Chrome MV3 extension manifest with packaged icon declarations.
- `browser-extension/billing-contract.json`: machine-readable subscription backend contract for the extension and ENHE website.
- `browser-extension/popup.html`, `browser-extension/popup.css`, `browser-extension/popup.js`: extension operator UI, multi-command and periodic automation generator, subscription estimate, license validation, usage reservation, hosted run payload hooks, and ENHE website links.
- `browser-extension/icons/*.png`: packaged extension icons for local loading and store submission.
- `scripts/promotion_manager.py`: deterministic report generator.
- `scripts/run_promotion_workflow.py`: end-to-end local agent workflow runner.
- `scripts/automation_scheduler.py`: JSON-configured periodic runner and Windows Task Scheduler script generator.
- `scripts/browser_snapshot.py`: Playwright/HTML structured snapshot capturer for rendered product pages.
- `scripts/browser_video_sampler.py`: browser-visible video metadata and frame screenshot sampler for public video pages.
- `scripts/web_data_provider.py`: optional Firecrawl-style public Search, Scrape, Map, Crawl, and Batch Scrape provider used by product reading, site discovery, and platform search when configured by environment variables.
- `scripts/product_url_discovery.py`: public website link and sitemap scanner that finds likely product URLs and writes a URL file for Codex-first reading.
- `scripts/product_url_reader.py`: URL-to-structured-snapshot/product-profile runner for Codex-first product page reading with static and public web-text fallback.
- `scripts/product_batch_runner.py`: batch URL runner that can discover product URLs from a site, invoke Codex-first reading, run one promotion cycle per ready product, optionally run per-product multi-query viral discovery, and optionally run next-round optimization from recovered evidence.
- `scripts/product_intake.py`: public URL, saved HTML, rendered text, or structured snapshot product-profile extractor.
- `scripts/competitor_discovery.py`: platform competitor search task generator with optional official API connectors.
- `scripts/competitor_collector.py`: official/public competitor evidence collector for YouTube and GitHub.
- `scripts/platform_search_browser.py`: public search page browser snapshot generator for platform competitor discovery.
- `scripts/platform_search_capture.py`: multi-result search snapshot capture for rendered browser pages, HTML, text, and public URLs.
- `scripts/viral_discovery_runner.py`: standalone keyword-to-viral-library runner for platform search, content capture, creator leaderboard, and follow-up queues.
- `scripts/multi_query_viral_discovery.py`: product-driven multi-query viral discovery planner/runner and merged material/creator aggregator.
- `scripts/viral_content_library.py`: ranked multi-platform viral material library and follow-up capture task generator.
- `scripts/creator_leaderboard.py`: creator/account leaderboard and follow-up tracking task generator from ranked viral materials.
- `scripts/creator_follow_up_runner.py`: safe creator/account follow-up runner that uses public/official connectors where available and queues manual evidence elsewhere.
- `scripts/follow_up_capture_runner.py`: safe public and browser-visible follow-up capture executor and deep competitor library builder.
- `scripts/competitor_content_enhancer.py`: rewrites generated platform content and publish packs using observed viral/deep competitor patterns before videos are rendered.
- `scripts/competitor_intake.py`: competitor evidence importer for public pages and user-provided exports.
- `scripts/metric_parsing.py`: shared visible metric label and number parser for English/Chinese labels, `k/m/b`, `万/亿/千/百`, and common currency symbols.
- `scripts/metrics_intake.py`: real metrics importer for exports and supported official API reads.
- `scripts/metrics_recovery.py`: metrics recovery coordinator for workflow manifests, publish queues, published URL evidence, and business exports.
- `scripts/real_evidence_inbox_setup.py`: safe inbox initializer that writes fillable published URL, metric, comment, order, revenue, manifest, README, and import command files without seeding fake evidence.
- `scripts/real_evidence_inbox.py`: local evidence inbox orchestrator that discovers published URL, metric, comment, order, and revenue files, runs the recovery scripts, and writes a single manager-facing report.
- `scripts/synthetic_evidence_generator.py`: clearly marked synthetic/demo evidence generator for validating the recovery and next-round loop without claiming real performance.
- `scripts/performance_monitor.py`: post-publish monitor that reruns public metric capture, comment capture, optional business attribution, metrics recovery, next-round optimization, and history snapshots from registered published URLs.
- `scripts/published_items.py`: published URL registrar for official execution reports, publish queues, and manual/browser-assisted publish evidence.
- `scripts/publish_url_capture.py`: post-publish browser snapshot/HTML/text capturer that registers real published URLs.
- `scripts/post_publish_metrics_capture.py`: public/browser-visible post-publish metrics capturer for registered URLs; writes a metrics export for recovery and manual evidence requests when metrics are hidden.
- `scripts/comment_evidence_capture.py`: public/browser-visible comment and demand-signal capturer for post-publish retrospectives and next-round content optimization.
- `scripts/business_attribution.py`: order/revenue export attribution to proven published content using URL, UTM content, referrer, content ID, or title/campaign evidence.
- `scripts/next_round_optimizer.py`: evidence-backed next-round optimizer that turns recovered metrics, comments, and business attribution into platform actions, content angles, hooks, and next-cycle commands.
- `scripts/publish_queue.py`: publish queue builder that creates platform drafts, GitHub/YouTube official dry-runs, Douyin browser-assisted payloads with optional video assets, and manual/browser-assisted publish tasks.
- `scripts/publish_readiness_runner.py`: publish readiness auditor for queue status, target info, credentials, approval, and per-platform next actions without storing secret values.
- `scripts/publish_setup_assistant.py`: readiness-to-setup-kit generator that writes credential variable names, target gaps, official setup references, approval commands, an env template, checklist, and platform setup guide without storing secret values.
- `scripts/real_evidence_setup.py`: publish-queue-to-evidence-kit generator that writes platform metric, comment, published URL, business attribution, structured snapshot templates, and safe import commands without storing secrets or fabricating data.
- `scripts/launch_unlock_pack.py`: unified safe setup pack builder for external launch gates; it orchestrates platform access audit, publish setup, real evidence setup, browser publish payload preparation, checklist, and next commands without storing secrets.
- `scripts/browser_publish_assistant.py`: user-visible browser-assisted publishing payload preparer and real published URL registrar for platforms without verified direct API publishing.
- `scripts/browser_publish_form_fill.py`: controlled Playwright helper that fills visible publisher fields from a prepared payload, screenshots the result, and stops before final publish.
- `scripts/browser_publish_session.py`: session-level browser-assisted publisher that runs payload preparation, optional visible-field form fill, screenshots, final user-action checklist, URL registration commands, and evidence inbox command.
- `scripts/platform_access_audit.py`: official access boundary auditor for platform publishing, metrics recovery, app-review requirements, and manual/browser-assisted fallback rules.
- `scripts/platform_capabilities.py`: AiToEarn-inspired machine-readable platform capability registry for Create, Publish, Engage, Monetize, Search, analytics, and safety boundaries.
- `scripts/completion_roadmap.py`: machine-readable gap-to-100% roadmap generator for local modules, external gates, operator steps, and acceptance evidence.
- `scripts/publish_executor.py`: approved official publish executor for GitHub and YouTube, plus a reserved future Douyin Open Platform upload/create helper.
- `scripts/youtube_oauth_publish.py`: YouTube OAuth consent and same-process upload helper.
- `scripts/youtube_credential_check.py`: secret-safe YouTube official API credential readiness checker with optional read-only channel probe.
- `scripts/promotion_cycle_runner.py`: one-command local operating cycle for workflow generation, guarded publish queue, published item registration, post-publish metric/comment evidence capture, business attribution, metrics recovery, and next-round optimization.
- `scripts/real_run_playbook.py`: live-run command pack generator that writes phased commands, evidence checklist, platform gates, approval gates, and a PowerShell command file for a real product promotion cycle.
- `scripts/skill_entry.py`: Codex-facing one-link entry that runs playbook generation, final capability execution, and final readiness refresh from a product or website URL.
- `scripts/final_capability_runner.py`: highest-automation safe runner that orchestrates product batch reading/cycles, viral discovery, publish readiness, launch unlock packs, browser-assisted publish materials, optional visible-field form fill, real evidence recovery, next-round optimization, and audits.
- `scripts/final_capability_readiness.py`: final acceptance matrix builder that merges generated reports into requirement status, external gates, and next commands for the requested end state.
- `scripts/final_capability_audit.py`: final readiness auditor for requested end-state requirements, local tools, credential presence, platform limits, and controlled self-evolution actions.
- `scripts/self_evolution_audit.py`: controlled self-evolution auditor for runtime gaps, repository status, installed Skill drift, platform-learning freshness, safe install candidates, and approved local Skill sync.
- `scripts/operator_action_checklist.py`: Chinese operator checklist generator for per-module 100% gaps, beginner steps, acceptance evidence, and copy-ready commands.
- `scripts/billing_contract_simulator.py`: local reference backend simulator for browser-extension subscription plans, hashed licenses, quota authorization, hosted run acceptance, usage commits, and payment webhook state changes.
- `scripts/package_browser_extension.py`: validates and builds the Chrome/Edge store submission zip plus `browser-extension-package-report`.
- `scripts/render_video.py`: ffmpeg-based MP4 renderer with caption, voiceover-audio, and Windows TTS support.
- `scripts/media_asset_pack.py`: Pillow-based PNG cover/detail image generator and publish-pack media asset manifest writer.
- `scripts/test_promotion_manager.py`: regression tests for report paths, safety modes, content counts, and retrospective guardrails.
- `references/workflow.md`: full operating workflow.
- `references/platform-publishing.md`: platform publishing modes and safety rules.
- `references/final-capability-boundaries.md`: final automation, authorization, and self-evolution limits.
- `references/cheat-on-content-integration.md`: optional review integration and prediction-cycle boundary.
- `references/output-schema.md`: report and field schema.
