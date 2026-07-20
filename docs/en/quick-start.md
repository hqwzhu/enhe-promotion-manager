# Quick start

## 1. Prepare the local directory

In Windows PowerShell, clone the public repository and enter the bundled Skill directory:

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd .\enhe-promotion-manager\skill\viral-product-copy-video-generator
python --version
```

Playwright/Chromium, Pillow, and FFmpeg are optional dependencies. Without them, the workflow can still create product facts, evidence indexes, and text drafts; missing media is marked explicitly.

## 2. Run one product page

The following command uses a public example URL. Replace it directly with your product link while keeping the argument structure:

```powershell
python scripts\skill_entry.py `
  --link "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir ".\promotion-output"
```

The run does not require a subscription or Hosted Worker. If the link is a website homepage rather than a specific product page, add `--link-mode site` so the workflow first discovers candidate product entries:

```powershell
python scripts\skill_entry.py `
  --link "https://example.com" `
  --link-mode site `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir ".\promotion-output"
```

## 3. Inspect the output

Read the actual product run directory from the top-level batch report; do not guess the `<run>` name:

```powershell
$batchPath = ".\promotion-output\reports\promotion-manager\batch\product-batch-runner.json"
$batch = Get-Content -Raw $batchPath | ConvertFrom-Json
$batch.promotionRuns | Format-Table id, status, outputDir, workflowManifest, publishQueue
$run = $batch.promotionRuns | Where-Object status -eq "ready" | Select-Object -First 1
if (-not $run) { throw "No ready product run; inspect the batch report first" }
$runDir = $run.outputDir
$queue = $run.publishQueue
```

When a batch contains multiple products, select the target by `id`, URL, and status. `outputDir` is the actual `promotion-output\product-batch-runs\<run>` path, where the runtime creates `<run>`. Important paths in a product directory include:

| Directory or file | Contents |
| --- | --- |
| `$runDir\reports\promotion-manager\generated-content\` | Platform titles, body copy, tags, spoken scripts, storyboards, and content review reports |
| `$runDir\videos\` | MP4 video drafts when FFmpeg is available |
| `$runDir\media-assets\` | Platform-specific PNG cover and detail images when Pillow is available |
| `$runDir\reports\promotion-manager\publish-queue\` | Publishing queues and each platform's manual or official API entry point |
| `$runDir\reports\promotion-manager\publish-packs\` | Organized publishing packs, warnings, missing items, and operating steps |
| `$runDir\reports\promotion-manager\retrospectives\` | Retrospectives and next-iteration recommendations after real evidence is available |

When you run the real-evidence inbox commands manually with `--out-dir` set to `$runDir`, their reports appear at `$runDir\reports\promotion-manager\real-evidence-inbox-setup\` and `$runDir\reports\promotion-manager\real-evidence-inbox\` respectively.

If a dependency is unavailable, a report may show `partial_ready` or media may show `missing`. That means text or part of the evidence is available; it does not mean that absent media or platform output was created.

## 4. Create a command from the current Chrome page

After installing the extension:

1. Open a public product page.
2. Explicitly click the extension icon, then click "Use current tab."
3. Choose platforms, workflow depth, and command type.
4. Copy the command, run it from `skill\viral-product-copy-video-generator`, and review the output.

The extension-generated command is only a local execution entry point. It does not submit the final publication for you. The extension interface can be switched between Chinese and English.

## 5. Review first, then prepare publishing

After checking facts, sources, copy, media paths, and risk notes, use the publishing assistance command to create a dry-run or browser-visible field payload:

```powershell
python scripts\browser_publish_session.py `
  --publish-queue "$queue" `
  --out-dir "$runDir"
```

With `--run-form-fill --headed`, the tool fills only visible fields and stops before final submission. A real publication still requires user confirmation, platform login, and account authorization.

## 6. Import real evidence after publishing

First create the evidence inbox:

```powershell
python scripts\real_evidence_inbox_setup.py `
  --product-url "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"
```

Add real published URLs, platform exports, comments, order files, and revenue files to the inbox, then import them and run monitoring:

```powershell
python scripts\real_evidence_inbox.py `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"

python scripts\performance_monitor.py `
  --out-dir "$runDir"
```

Without real data, the status remains `waiting_real_data`. Synthetic demonstrations are for validating the local workflow only and cannot be treated as publishing performance, orders, or revenue.

## Shared boundaries

- Hosted Worker remains disabled and is not described as an available service.
- Cookies and Chrome login profiles stay on the local computer and are not uploaded to this public repository or its public release packages.
- Final publishing requires user review and action; browser-assisted flows stop before final submission.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Only real URLs, metrics, comments, orders, and revenue are used as real evidence; evidence is not fabricated.
- Payment, subscription, license, credits, and billing backends are excluded only from the synchronization conclusion; the extension's existing billing UI and `billing-contract.json` remain included.
