# Chrome extension guide

The Chrome extension is a Manifest V3 local entry point that turns the current product page into a reviewable Codex command. The local Skill still performs the complete research, generation, publishing-pack, and retrospective workflow.

## Installation

### Chrome Web Store

Open the [published Chrome Web Store listing](https://chromewebstore.google.com/detail/enhe-promotion-manager/dloklkbnmoigemnfigbkibogmgbieppl) and install it. The current public store version is `0.5.3`; source/release candidate `0.5.4` has not yet been submitted for Chrome review.

### Unpacked extension

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd enhe-promotion-manager
```

Open Developer mode at `chrome://extensions`, choose "Load unpacked," and select `extension\chrome`. The public source/release candidate version is `0.5.4`.

## Current-tab capture

Capture must be initiated by the user:

1. Open a product page or website entry point.
2. Click the extension icon.
3. Click "Use current tab."
4. Check the URL, title, target platforms, and output directory.
5. Generate the command, then copy it and execute it from `skill\viral-product-copy-video-generator`.

The extension reads the current tab's URL and title as task inputs. It does not read tabs in bulk in the background, and it does not upload Cookies, Chrome login profiles, or page tokens to this public repository or its public release packages.

## Language selection

The interface supports Chinese and English. Switching changes only extension display text and command-selection prompts. Skill file output, platform arguments, and safety boundaries do not change with the interface language. Chrome extension local storage holds the language preference.

## Command types

The extension can create these local entry points:

| Command type | Purpose |
| --- | --- |
| One-click Skill run | Run the complete local workflow, or a selected depth, from a product URL |
| Browser publishing session | Read the publishing queue, prepare visible entry points and fields, and stop before final submission |
| Publishing unlock pack | Collect platform entry points, credential variable names, publishing payloads, and real-evidence templates |
| High-performing evidence setup / inbox | Create an additional-collection directory and import entry point for public content research |
| Real-evidence inbox setup / inbox | Create and import published URLs, metrics, comments, orders, and revenue files |
| Performance monitoring | Read public metrics or user exports and create performance and next-iteration recommendations |
| Local platform evidence | Create a local evidence collection command for a platform, keyword, or detail target |
| Final readiness audit | Check facts, media, publishing, evidence, and next-iteration status |
| Scheduled-task setup / run | Create reviewable local scheduling configuration and a Windows execution entry point |
| Windows task script | Produce a task script that the user reviews before registration |

These are non-payment commands. See [version synchronization](version-sync.md) for the 11 scripts covered by public distribution synchronization checks.

## Local-first paths

The extension creates commands and stores only the necessary local interface preferences. Product reads, platform research, media generation, publishing packs, evidence, and retrospectives are written to the local `--out-dir` you choose. The extension's existing license key, license endpoint, usage endpoint, Hosted Run endpoint, checkout page, and billing entry point remain in the UI. Hosted Worker remains disabled, and the public distribution does not describe hosted execution as available.

## Final publishing and evidence

Browser-assisted options can open platform entry points, fill visible fields, save screenshots, and create review checklists; they stop before final submission. Official API paths require the user's own credentials, account authorization, and explicit approval. After publishing, record real URLs and import real metrics, comments, orders, and revenue through the evidence inbox.

## Boundaries

- Cookies and Chrome login profiles stay on the local computer and are not uploaded to this public repository or its public release packages.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Final publishing requires user review and action; the extension does not replace the user's final platform confirmation.
- Only real URLs, metrics, comments, orders, and revenue are retrospective evidence; data is not fabricated.
- Payment, subscription, license, credits, and billing backends are excluded only from the synchronization conclusion; the extension's existing billing UI and `billing-contract.json` remain included.
