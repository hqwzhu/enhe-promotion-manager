# Troubleshooting

Begin with the minimal command and inspect status under `promotion-output\reports\promotion-manager\`. Do not delete `partial_ready`, `missing`, or error reports; they record what completed and what to do next.

## Playwright or Chromium is missing

Symptoms: a dynamic page is empty, the browser fails to start, or a report says the browser runtime is unavailable.

```powershell
python -m pip install playwright
python -m playwright install chromium
```

Confirm that the current command uses the same Python environment. You can also add `--install-browser-if-missing` to `skill_entry.py`, but that flag performs an explicit network installation and should be used only in a local environment where the user has agreed.

## FFmpeg is missing

Symptoms: copy and storyboards are available, but MP4 status is `missing`, or the report cannot find `ffmpeg`.

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```

Reopen PowerShell after installation, then rerun the media step or complete workflow. Do not report a script and storyboard as a completed video file.

## Pillow is missing

Symptoms: PNG cover or detail images show `missing`.

```powershell
python -m pip install pillow
```

Rerun the media-pack step, then confirm that every image path in the publishing pack exists.

## `partial_ready` or media `missing`

`partial_ready` means that some facts, evidence, or drafts are usable, while a page, comment set, media file, or platform step remains incomplete. Address each `reason`, `warnings`, and `nextActions` entry in the report. Common causes include a missing dynamic-page dependency, partial platform responses, an absent video source, missing FFmpeg/Pillow, or no real evidence imported by the user.

## Sidecar is not ready

Begin with a read-only check:

```powershell
python scripts\platform_data_manager.py setup --check
```

If status is `provider_unavailable`, check Git, `uv`, Chrome, the pinned upstream commit, the Sidecar Python environment, and the default directory `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler`. Run installation only after confirming the MediaCrawler upstream license and platform terms and agreeing to network installation:

```powershell
python scripts\platform_data_manager.py setup --install
```

## Login, platform verification, or risk controls

Common statuses:

- `waiting_login`: complete login or scan a code in the local browser, then retry.
- `manual_verification_required`: the platform requires human verification, which the user handles.
- `blocked_by_platform`: stop the current request and use a public page, official interface, or user export.

The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization. Do not repeatedly retry a restricted path, and do not copy Cookies or a Chrome profile into the repository.

## Chinese text and UTF-8 on Windows

Symptoms: Chinese text is corrupted in the terminal while Markdown is correct in the editor, or scripts read and save files with inconsistent encodings.

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
```

Use an editor that supports UTF-8 and do not resave Markdown as ANSI. Verify file encoding:

```powershell
python -c "from pathlib import Path; Path('distribution/README.en.md').read_text(encoding='utf-8'); print('UTF-8 OK')"
```

## The installed Skill is stale

Symptoms: the Chrome extension creates a command, but the installed Skill lacks its script, or local behavior still matches an older version.

Synchronize from the reviewed `skill\viral-product-copy-video-generator` source directory in a separate clone of the public repository. Do not run the command inside the installed target at `$HOME\.codex\skills\viral-product-copy-video-generator`; identical source and target files cause a same-file copy error:

```powershell
python scripts\self_evolution_audit.py `
  --sync-installed-skill `
  --approval I_APPROVE_SKILL_SYNC `
  --out-dir ".\promotion-output"
```

After synchronization, inspect `SKILL.md`, `component-manifest.json` in a public release package, and the 11 non-payment command scripts under the installed directory. Synchronization does not copy `promotion-output`, Cookies, Chrome configuration, or `.env`.

## A publishing command is rejected

Return to dry-run first. Check that credentials exist, the target account and repository or video path are correct, permissions are sufficient, and the approval value is exact. The official-write switch for `skill_entry.py`, `final_capability_runner.py`, and `publish_readiness_runner.py` is `--execute-publish --approval I_APPROVE_PUBLISH`. Browser assistance stops before final submission; the user confirms the final publishing action.

## No retrospective data is available

If status is `waiting_real_data`, create and fill a real-evidence inbox. Import only real published URLs, real metrics, real comments, real orders, and real revenue. Demonstration data cannot support external performance conclusions.

## The issue remains unresolved

Retain a sanitized command, version, status code, and minimal log, then email them to huqingwei5942@gmail.com. Do not publish API keys, Cookies, license keys, account information, orders, or client personal data.

Hosted Worker remains disabled. Payment, subscription, license, credits, and billing backends are excluded only from the synchronization conclusion; the extension's existing billing UI and `billing-contract.json` remain included.
