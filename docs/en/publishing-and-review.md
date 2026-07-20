# Publishing and retrospective guide

The publishing flow creates drafts and a dry-run first, then asks the user to review facts, copy, media, accounts, and platform fields. Authorization varies by platform, and the public distribution does not present preparation readiness as a completed publication.

First obtain the actual product run directory and queue path from the batch report:

```powershell
$batch = Get-Content -Raw ".\promotion-output\reports\promotion-manager\batch\product-batch-runner.json" | ConvertFrom-Json
$batch.promotionRuns | Format-Table id, status, outputDir, workflowManifest, publishQueue
$run = $batch.promotionRuns | Where-Object status -eq "ready" | Select-Object -First 1
if (-not $run) { throw "No ready product run; inspect the batch report first" }
$runDir = $run.outputDir
$queue = $run.publishQueue
if (-not $queue -or -not (Test-Path -LiteralPath $queue)) { throw "The target run has no usable publishing queue" }
```

If the report contains multiple products, select the target by `id`, URL, and status. Do not guess the `product-batch-runs\<run>` name manually.

## Three publishing paths

### Dry-run

A dry-run creates publishing payloads, checks, missing items, and commands without writing to a real platform. Use it to check the target repository, video file, title, privacy state, account credential variable, and approval state.

```powershell
python scripts\publish_readiness_runner.py `
  --publish-queue "$queue" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir "$runDir"
```

### Manual publishing

Use this path when no supported official API exists, platform authorization is not confirmed, or the account owner wants full control over submission. The publishing pack provides titles, body copy, tags, media files, comment prompts, tracking URLs, and a checklist. The user checks each item on the platform page and submits it.

### Browser assistance

A browser session can open platform entry points, prepare payloads, fill visible fields, save screenshots, and create a final review checklist:

```powershell
python scripts\browser_publish_session.py `
  --publish-queue "$queue" `
  --run-form-fill `
  --headed `
  --out-dir "$runDir"
```

Browser assistance stops before final submission. The user must inspect the account, page, title, body copy, tags, video, images, privacy settings, and platform prompts, then confirm the final action personally.

## Official API paths

GitHub, YouTube, and other implemented official publishing ports use dry-run by default. A real write requires all of the following:

- The user owns or controls the target account and has permission to perform the action.
- Official API credentials or OAuth authorization are available locally.
- The target repository, branch, publishing type, video file, and privacy state are explicit.
- The dry-run contains no critical missing item.
- For `skill_entry.py`, `final_capability_runner.py`, or `publish_readiness_runner.py`, the command explicitly contains `--execute-publish --approval I_APPROVE_PUBLISH`.

YouTube also requires the official clients listed in `requirements-youtube.txt`. Before a GitHub write, confirm owner/repo, branch, and action type. Douyin official API capability depends on the permissions actually granted to the user's Open Platform account; without that authorization, use a manual or browser-assisted path.

## Pre-publish review checklist

1. Can every product fact be traced to a public page or real material supplied by the user?
2. Does competitor evidence retain sources, and are metrics actual visible values?
3. Do the title and body copy fit the target platform and avoid unsupported promises?
4. Do the MP4, cover, and detail images actually exist, and have all `missing` items been handled?
5. Are the publishing account, target page, privacy state, tags, and tracking links correct?
6. Does the user need to handle a platform login, verification, risk-control prompt, or authorization request?
7. Is the directory for recording URLs and importing evidence after publishing ready?

## Evidence registration and retrospectives

After publishing, record the real URL first, then import real metrics, comments, and business data:

```powershell
python scripts\real_evidence_inbox_setup.py `
  --product-url "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"

python scripts\real_evidence_inbox.py `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"

python scripts\performance_monitor.py `
  --out-dir "$runDir"
```

Evidence can come from platform-exported CSV/XLSX/JSON files, copied visible metric text, comment files, or order and revenue exports. Without real evidence, retain `waiting_real_data`. Demonstration files must retain their synthetic labels and must not be used for external result reporting.

## Publishing boundaries

- Hosted Worker remains disabled; the public edition does not provide a service that publishes without user supervision.
- Final publishing requires user review and action; browser-assisted flows do not complete the final platform submission for the user.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Cookies, Chrome login profiles, and official credentials stay on the local computer and are not uploaded to this public repository or its public release packages.
- Record only real published URLs, real metrics, real comments, real orders, and real revenue; evidence is not fabricated.
- Payment, subscription, license, credits, and billing backends are excluded only from the feature parity conclusion; the extension's existing billing UI and `billing-contract.json` remain included.
