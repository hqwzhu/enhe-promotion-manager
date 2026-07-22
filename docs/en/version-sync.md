# Version and feature synchronization

## Current markers

Public repository / Skill / extension source/release candidate version: 0.5.4

Published Chrome Web Store version: 0.5.3

Non-payment command references: 11/11 exist in the bundled Skill

Payment and subscriptions: excluded from the feature parity conclusion; the existing extension UI and billing-contract.json remain included

Hosted Worker: disabled

## The 11 non-payment commands

The public distribution parses the Python commands referenced by the extension source and confirms that the bundled Skill contains the corresponding scripts:

1. `automation_scheduler.py`
2. `browser_publish_session.py`
3. `final_capability_readiness.py`
4. `launch_unlock_pack.py`
5. `performance_monitor.py`
6. `promotion_manager.py`
7. `real_evidence_inbox.py`
8. `real_evidence_inbox_setup.py`
9. `skill_entry.py`
10. `viral_evidence_inbox.py`
11. `viral_evidence_inbox_setup.py`

"11/11 exist" means only that every non-payment command referenced by the extension has a corresponding entry point in the bundled Skill and has passed the public distribution contract check. It does not mean that every platform account, third-party dependency, official API permission, real media file, or real evidence source is available.

## Relationship between the store and source versions

The published Chrome Web Store listing at https://chromewebstore.google.com/detail/enhe-promotion-manager/dloklkbnmoigemnfigbkibogmgbieppl and the published GitHub Release packages use version `0.5.3`. The public repository / Skill / extension source is the `0.5.4` release candidate; it has not yet been submitted to the Chrome Web Store for review.

## What the synchronization conclusion excludes

Payment, subscriptions, license purchases, credits, and billing backends are outside the conclusion that extension commands match the bundled Skill. That scope exclusion does not mean that their UI or files were removed:

- The extension's existing payment and subscription interfaces remain included.
- UI fields for licenses, usage authorization, the Hosted Run endpoint, checkout pages, and billing entry points remain included.
- `billing-contract.json` remains included.
- These commercial capabilities require separate deployment, privacy, security, billing, and production-readiness validation.
- Hosted Worker is currently disabled, and the public release does not describe hosted execution as available.

## Distribution boundaries

- Cookies, Chrome login profiles, the Sidecar checkout, virtual environments, identity salts, and runtime data do not enter the public repository or public release packages.
- Final publishing requires user review and action; browser-assisted flows stop before final submission.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Only real URLs, metrics, comments, orders, and revenue can be treated as real evidence; data is not fabricated.
- MediaCrawler is a separate upstream dependency, and its license does not transfer under this repository's MIT License.

## How to check whether the local Skill is synchronized

Enter the `skill\viral-product-copy-video-generator` source directory in a separate clone of the public repository. Do not run synchronization from the installed target directory at `$HOME\.codex\skills\viral-product-copy-video-generator`:

```powershell
python scripts\self_evolution_audit.py `
  --sync-installed-skill `
  --approval I_APPROVE_SKILL_SYNC `
  --out-dir ".\promotion-output"
```

Then run the readiness audit:

```powershell
python scripts\final_capability_readiness.py `
  --out-dir ".\promotion-output"
```

Synchronization covers only managed Skill files. It does not copy Cookies, Chrome login profiles, `.env`, evidence inboxes, or `promotion-output`.
