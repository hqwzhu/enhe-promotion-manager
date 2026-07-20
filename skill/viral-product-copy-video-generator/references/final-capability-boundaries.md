# Final Capability Boundaries

Use this reference when the user asks for full automation.

## What The Skill Can Automate Locally

- Parse public product URLs, saved HTML, rendered page text, or Codex/browser structured snapshots into product profiles.
- Capture public product URLs with Playwright Chromium into structured browser-visible snapshots for product intake.
- Discover likely product URLs from a public website/homepage using public HTML links, then pass those candidates into Codex-first product reading before promotion.
- Run `scripts/product_url_reader.py` to read one or more product URLs into per-URL structured browser snapshots, static URL profiles, or public web-text fallback profiles, then return correct next workflow commands.
- Run `scripts/product_batch_runner.py` to discover or read multiple product URLs first, execute one guarded local promotion cycle per ready product using structured snapshots or saved web-text fallback files when available, and optionally run product-driven multi-query viral discovery for every ready product.
- Run `scripts/skill_entry.py` from a single product or website link. It generates the real-run playbook, runs the final capability runner with safe high-automation defaults, and refreshes the final readiness matrix while preserving publish, credential, and evidence gates.
- Run an end-to-end local workflow from one product source through `scripts/run_promotion_workflow.py`, producing intake, competitor discovery, generated content, video status, publish automation status, metrics recovery status, and a workflow manifest.
- Run due promotion jobs from a local JSON schedule through `scripts/automation_scheduler.py`, including state tracking and Windows Task Scheduler script generation.
- Generate platform-native copy, articles, voiceover scripts, storyboards, publish packs, result templates, and retrospective templates.
- Render deterministic MP4 videos from generated platform content with captions, optional voiceover audio files, or Windows SAPI review voiceover when `ffmpeg` is available.
- Generate platform research docs, risk matrices, reference project notes, and self-learning notes.
- Generate platform competitor discovery tasks and run official public search connectors where credentials/access allow.
- Collect YouTube competitor evidence through official search/video/channel APIs and GitHub competitor evidence through public search APIs.
- Open public platform search pages with Playwright Chromium and save browser-visible competitor search snapshots for YouTube, Zhihu, Xiaohongshu, Douyin, GitHub, TikTok, and similar platforms.
- Capture multi-result browser-visible search snapshots for YouTube, Zhihu, Xiaohongshu, Douyin, GitHub, TikTok, and similar platforms without using private endpoints or hidden browser tokens.
- Run a standalone keyword-to-viral-library discovery pass with `scripts/viral_discovery_runner.py`, chaining browser-visible platform search, normalized captures, viral material ranking, creator leaderboard generation, and optional safe follow-up queues.
- Run product-driven multi-query viral discovery with `scripts/multi_query_viral_discovery.py`, deriving multiple search queries from a product profile or workflow manifest, planning or running one public discovery pass per query, and merging/deduping ranked viral materials and creators.
- Rank captured cross-platform search results into a viral material library with top titles, hooks, creators, visible metrics, reusable patterns, and source evidence paths.
- Group ranked viral materials into a creator/account leaderboard and safe creator follow-up tasks using only observed public/browser-visible evidence.
- Run safe creator/account follow-up research through supported official/public connectors for YouTube and GitHub, while routing Zhihu, Xiaohongshu, Douyin, TikTok, and unverified platforms to browser-visible evidence requests.
- Generate follow-up capture tasks from the viral material library, routing public YouTube/GitHub URLs to safe capture candidates and routing Zhihu, Xiaohongshu, Douyin, TikTok, and unverified platforms to browser-assisted or user-export evidence.
- Execute safe public follow-up capture tasks into a deep competitor library, attempt public browser-visible snapshots for queued browser-assisted platform pages when explicitly enabled, and write manual/browser evidence requests when login, captcha, verification, draft, preview, or access-denied content appears.
- Capture browser-visible video metadata and sampled frame screenshots from public/video pages with `scripts/browser_video_sampler.py` or follow-up capture `--sample-video-frames`, while redacting signed media query strings and avoiding private stream downloads.
- Rewrite generated platform content, video scripts, storyboards, and publish-pack content with observed viral/deep competitor structures before video rendering, while keeping competitor titles, hooks, and metrics as evidence metadata rather than product claims.
- Read user-provided competitor URLs, exported data, screenshots, or notes and turn them into deconstruction reports.
- Import real post-publish metrics from CSV, Excel `.xlsx`, JSON, text exports, Codex/browser structured snapshots, GitHub public repository data, and YouTube official statistics when `YOUTUBE_API_KEY` is provided.
- Capture public/browser-visible post-publish metrics from registered published URLs with `scripts/post_publish_metrics_capture.py`, write a metrics export for recovery, and generate manual evidence requests when metrics are hidden behind login, captcha, private analytics, or business systems.
- Capture public/browser-visible comments and demand signals from registered published URLs, saved HTML, copied text, or structured snapshots with `scripts/comment_evidence_capture.py`, then use those questions, objections, integration requests, pain points, and CTA-intent signals for the next content round.
- Attribute user-provided order/revenue exports to proven published content with `scripts/business_attribution.py` when rows contain exact URLs, referrer URLs, landing pages, UTM content, content IDs, or title/campaign evidence.
- Coordinate post-publish metrics recovery from workflow manifests, publish queues, published item JSON, published URLs, structured metric snapshots, GitHub repos, YouTube video IDs, and user-provided business exports without fabricating missing data.
- Convert recovered metrics, public/browser-visible comments, and matched business attribution into next-round platform actions, content angles, hooks, script briefs, and copy-ready commands with `scripts/next_round_optimizer.py`.
- Run `scripts/performance_monitor.py` as a repeatable post-publish monitor that orchestrates public metric capture, visible comment capture, optional business attribution, metrics recovery, next-round optimization, and history snapshots from registered published URLs.
- Generate a live-run command pack with `scripts/real_run_playbook.py`, sequencing final capability execution, publish readiness/setup, browser-assisted publishing, approved official publishing, real published URL registration, metrics/comment capture, business attribution, metrics recovery, next-round optimization, periodic operation, and controlled self-evolution. This is an execution guide and evidence checklist; it does not replace platform authorization or real data.
- Execute approved official publishing actions for GitHub and YouTube when the correct environment credentials, target files, official account authorization, and explicit approval phrase are supplied. Douyin is browser-assisted/manual in the current setup.
- Pass that same approved official publishing request through `scripts/final_capability_runner.py` or `scripts/skill_entry.py` with `--execute-publish --approval I_APPROVE_PUBLISH`, while preserving all credential, target, account-authorization, and platform-review gates.
- Build a publish execution queue that routes GitHub and YouTube into official dry-run/approved executor calls, attaches `--douyin-video-file` as a Douyin browser-assisted payload asset, and routes Zhihu, Xiaohongshu, Douyin, and unverified platforms into manual/browser-assisted publish tasks.
- Audit publish readiness for a workflow or queue, including target information, queue state, credential presence by environment variable name, approval status, and next actions without storing secret values.
- Generate a publish setup kit from readiness reports, including environment variable names, missing target fields, official setup references, required platform capabilities, approval gates, safe rerun/execution commands, and checklists without storing credential values.
- Prepare browser-assisted/manual publishing payloads for Zhihu, Xiaohongshu, Douyin, TikTok, and similar platforms with `scripts/browser_publish_assistant.py`, including clipboard text, form-fill helper scripts, publisher entry URLs, checklists, and post-publish URL registration commands.
- Fill visible title/body/tags/cover fields from one prepared browser publish payload with `scripts/browser_publish_form_fill.py`, save a screenshot/report, and stop before any final publish/submit action.
- Run a browser-assisted publish session with `scripts/browser_publish_session.py` to prepare payloads, optionally fill visible fields for each queued browser/manual platform, collect screenshots, and produce post-publish URL registration plus evidence inbox commands while still requiring user review and final publish action.
- Audit official platform access boundaries with `scripts/platform_access_audit.py`, mapping implemented official APIs, official app-review candidates, manual/browser-assisted fallback rules, required environment variable names, and metric evidence requirements.
- Register proven published URLs from official execution reports, publish queues, or manual/browser-assisted evidence into a standard published-items report for later metrics recovery.
- Capture browser-visible post-publish snapshots, saved HTML, copied text, or public published URLs and register them only when they resolve to a real platform URL rather than a draft, editor, preview, localhost, or unknown-platform page.
- Run a one-command local operating cycle that chains workflow generation, guarded publish queue, published URL registration, optional public post-publish metrics capture, optional public comment evidence capture, optional business attribution, and metrics recovery while preserving approval gates and evidence requirements.
- Audit final-agent readiness with `scripts/final_capability_audit.py`, including local scripts, browser runtime, `ffmpeg`, credential presence, platform publishing limits, real metrics inputs, and self-evolution boundaries.
- Audit controlled self-evolution with `scripts/self_evolution_audit.py`, including runtime gaps, repository status, installed Codex Skill drift, safe install candidates, and approved local Skill sync.
- Run a YouTube OAuth consent flow and upload in the same process without saving OAuth tokens.

## What Requires Official Authorization

- YouTube uploads require Google/YouTube OAuth, approved scopes, quota, and explicit user approval.
- GitHub repository writes require a GitHub token or GitHub App permissions and explicit user approval.
- TikTok Direct Post requires developer app access, approved scopes, and creator authorization.
- Douyin official publishing is not available in the current operator setup. Use browser-assisted/manual publishing, stop before final publish, and register the real URL/evidence after the account owner publishes. The official upload/create executor remains a future reserved port only.
- Platform analytics require official API access or user-exported evidence.
- Orders and revenue require business-system exports or user-provided analytics evidence; public social platforms generally cannot prove those values.
- Public post pages may expose views, likes, comments, saves, shares, or similar counters, but hidden analytics, order attribution, and revenue still require official exports, screenshots, or business-system evidence.
- Public comment pages may expose user questions, objections, and feature requests, but hidden comments, private DMs, account analytics, order attribution, and revenue still require official exports, screenshots, or business-system evidence.
- Business attribution requires content-level evidence such as URL, UTM content, referrer, landing page, content ID, title, or campaign fields; a platform/source name alone is not enough to claim revenue for a specific post.

## What Must Stay Browser-Assisted Or Manual

- Zhihu and Xiaohongshu publishing should remain manual or browser-assisted unless stable official creator publishing access is verified.
- Douyin publishing remains browser-assisted/manual when no approved open-platform app authorization, user authorization, or video file is available.
- Browser-assisted publish preparation may open a user-visible creator page, prepare field payloads, and fill visible fields from those payloads, but it must not auto-login, solve challenges, or click the final publish/submit button.
- Any platform flow that triggers captcha, risk control, account verification, or login prompts must stop for user action.
- The agent must not extract, save, print, or reuse cookies, passwords, API keys, or hidden browser tokens.

## What The Skill Must Not Claim

- Do not claim auto-publishing works until code has executed through official APIs with real user authorization.
- Do not claim competitor metrics unless they were observed from public pages, official APIs, exports, or user-provided evidence.
- Do not infer hidden follower counts, private analytics, creator income, orders, or conversion performance from public creator ranking.
- Do not treat creator follow-up dry-runs, queued evidence requests, or search plans as captured creator performance data.
- Do not treat video frame sampling as a transcript, audio analysis, private media download, or proof of metrics; it is only browser-visible visual evidence plus visible page text.
- Do not treat a promotion cycle as fully published unless the publish queue or published-items report contains proven published URLs.
- Do not copy competitor wording into final product copy; reuse only structure, sequence, and safe pattern labels.
- Do not claim revenue, orders, leads, views, likes, comments, or click data without evidence.
- Do not treat `post_publish_metrics_capture.py` manual evidence requests as recovered data; only captured metric records, official APIs, exports, screenshots, or user-provided evidence count.
- Do not treat `comment_evidence_capture.py` manual evidence requests as recovered comments or demand signals; only captured public/browser-visible comments, official exports, screenshots, or user-provided evidence count.
- Do not treat `business_attribution.py` unmatched rows as recovered content performance; only matched rows in the attribution export can be merged into metrics recovery.
- Do not treat `next_round_optimizer.py` recommendations as proof of performance; they are next-action proposals backed by the evidence files attached to the report.
- Do not call unofficial endpoints "official APIs."

## Self-Evolution Rule

The Skill may research, write notes, check local tool availability, detect installed Skill drift, and propose upgrades. `scripts/final_capability_audit.py` and `scripts/self_evolution_audit.py` may install only explicit allowlisted runtime dependencies, such as Playwright Chromium, when the command includes `--install-safe-missing-tools`. `scripts/self_evolution_audit.py` may sync reviewed local Skill files into the installed Codex Skill directory only when the command includes `--sync-installed-skill --approval I_APPROVE_SKILL_SYNC`. It must not silently install arbitrary packages, modify itself from unreviewed network code, delete installed Skill files during sync, or upgrade dependencies without an explicit command and a clear source/risk note.
