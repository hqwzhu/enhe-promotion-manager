# Skill guide

## Inputs

The Skill's minimum input is one public product URL. It also supports:

- Repeated `--link` arguments, or one link per line through `--links-file`.
- `--link-mode product` to treat a link as a product page, or `--link-mode site` to discover products on a website first.
- Selection of `--platforms`, `--goal`, `--language`, and `--out-dir`.
- Optional steps for browser reads, additional competitor collection, video frame extraction, speech, media, and publishing queues.
- Real `--published-url` values, metric exports, comment evidence, orders, and revenue evidence after publishing.

The default data boundary is the local file system. URL reads use public pages, browser-visible content, official paths, or user-provided files. Private account data is not read or submitted as public evidence.

## Common commands

### Complete single-link run

```powershell
python scripts\skill_entry.py `
  --link "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir ".\promotion-output"
```

Regular users should use `skill_entry.py`. `promotion_manager.py` is a lower-level report generator that requires complete structured product fields and positional arguments; it is not the single-link entry point.

### Find the actual product run directory

The single-link entry point still creates product directories through the batch runner. Their names contain a run sequence and a sanitized product identifier and should not be guessed. Read the batch report:

```powershell
$batchPath = ".\promotion-output\reports\promotion-manager\batch\product-batch-runner.json"
$batch = Get-Content -Raw $batchPath | ConvertFrom-Json
$batch.promotionRuns | Format-Table id, status, outputDir, workflowManifest, publishQueue
$run = $batch.promotionRuns | Where-Object status -eq "ready" | Select-Object -First 1
if (-not $run) { throw "No ready product run; inspect the batch report first" }
$runDir = $run.outputDir
$queue = $run.publishQueue
```

If there are multiple product runs, select the target by `id`, URL, and status. `outputDir` points to the actual `promotion-output\product-batch-runs\<run>` directory. `workflowManifest` and `publishQueue` provide file paths that can be used directly.

### Browser-assisted publishing session

```powershell
python scripts\browser_publish_session.py `
  --publish-queue "$queue" `
  --out-dir "$runDir"
```

### Real-evidence inbox

```powershell
python scripts\real_evidence_inbox_setup.py `
  --product-url "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"

python scripts\real_evidence_inbox.py `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"
```

### Retrospective and readiness audits

```powershell
python scripts\performance_monitor.py --out-dir "$runDir"
python scripts\final_capability_readiness.py --out-dir ".\promotion-output"
```

## Output artifacts

`skill_entry.py` writes Skill, batch, final-run, and readiness reports under the top-level `--out-dir`. Facts, sources, competitor tasks, platform content, spoken scripts, storyboards, media, publishing queues, publishing packs, and retrospectives for each product are written under the `outputDir` listed in the batch report. Typical relative paths are `reports\promotion-manager\generated-content`, `videos`, `media-assets`, `reports\promotion-manager\publish-packs`, `reports\promotion-manager\publish-queue`, and `reports\promotion-manager\retrospectives`; interpret all of them relative to the actual `$runDir`.

Common statuses include:

- `ready`: inputs, dependencies, and output for the step satisfy local checks.
- `partial_ready`: some content or evidence is complete, with missing or limited steps remaining.
- `missing`: required media, sources, or user files have not been provided.
- `provider_unavailable`: a platform data provider, Sidecar, or browser runtime is unavailable.
- `waiting_login`: the user must complete platform login or scan a code locally.
- `manual_verification_required`: the platform requires the user to complete verification.
- `blocked_by_platform`: platform risk controls or access restrictions prevent the current request.
- `waiting_real_data`: no real published URL, metric, comment, or business evidence has been imported.

## Dependencies and local-data boundary

- Python 3.10+ (3.11 recommended) and Codex are the base runtime.
- Playwright/Chromium supports dynamic pages and browser-visible research; Pillow supports PNG; FFmpeg supports MP4; and the YouTube client supports the optional official API path.
- MediaCrawler Sidecar is installed separately on the local computer. Its default root is `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler`, and it is not part of the public repository.
- `promotion-output`, evidence inboxes, Cookies, Chrome login profiles, the Sidecar checkout, virtual environments, and raw output should all remain local.
- Hosted Worker remains disabled; a cloud runtime is not required.

## Error handling

The Skill writes error categories, retry counts, missing items, and next steps into its reports. Sidecar cleans its default raw directory; it retains raw debug output only when explicitly requested and then displays a sensitive-data warning. Do not commit Cookies, tokens, order information, or client data from logs to the public repository.

## Boundaries

- Final publishing requires user review and action; browser-assisted commands stop before final submission.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Import only real URLs, metrics, comments, orders, and revenue; synthetic demonstrations are for local validation only.
- Cookies and Chrome login profiles stay on the local computer and are not uploaded to this public repository or its public release packages.
- Payment, subscription, license, credits, and billing backends are excluded only from the synchronization conclusion; the extension's billing UI and `billing-contract.json` remain included.
