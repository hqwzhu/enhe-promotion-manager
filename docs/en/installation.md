# Installation guide

This guide is written for Windows PowerShell first and includes cross-platform notes. The public distribution contains a local Codex Skill, a Chrome Manifest V3 extension, and verification scripts. Hosted Worker remains disabled, so the local workflow does not require a server deployment.

## Preferred Windows installation check

After cloning the public repository and entering `skill\viral-product-copy-video-generator`, begin with these Windows PowerShell commands:

```powershell
python --version
python -m pip install playwright pillow
python -m playwright install chromium
python scripts\self_evolution_audit.py --skip-runtime-checks --out-dir ".\promotion-output\install-audit"
```

These commands install the browser and image dependencies and run a read-only installation audit. Install FFmpeg and the official YouTube API client separately only when needed, as described below.

## Path 1: Chrome Web Store

Use this path when you need only current-page task creation and command generation.

1. Open [ENHE Promotion Manager](https://chromewebstore.google.com/detail/enhe-promotion-manager/dloklkbnmoigemnfigbkibogmgbieppl).
2. Click "Add to Chrome" and confirm the browser installation prompt.
3. Open a public product page. Complete any login or page preparation yourself, then explicitly click the extension icon.
4. Click "Use current tab," choose the platforms, workflow depth, and command type, then copy the command to run in the local repository.

The public source/release candidate is `0.5.4`. The published Chrome Web Store and GitHub Release package version remains `0.5.3`; v0.5.4 has not yet been submitted for Chrome review. After installation, use the version displayed by the extension and the [version synchronization guide](version-sync.md) as the reference.

## Path 2: Unpacked extension

Use this path to review the source, participate in testing, or use a version that has not yet been submitted to the store.

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd .\enhe-promotion-manager
```

1. Open `chrome://extensions` in Chrome.
2. Enable "Developer mode" in the upper-right corner.
3. Click "Load unpacked."
4. Select the repository's `extension\chrome` directory.
5. Open a product page and use "Use current tab" after an explicit user action.

The extension reads the visible entry point for the current tab and creates a local command. It does not upload Cookies, Chrome login profiles, or page login state to this public repository or its public release packages.

## Path 3: Skill ZIP or source

Use this path for the complete local workflow, script output, media drafts, publishing packs, and real-evidence retrospectives. First install Python 3.10 or later, with Python 3.11 recommended, and confirm that PowerShell can invoke it:

```powershell
python --version
```

### Using the public repository source

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd .\enhe-promotion-manager\skill\viral-product-copy-video-generator
python -m pip install --upgrade pip
```

The public repository stores the Skill at `skill\viral-product-copy-video-generator`. From that directory, `SKILL.md` and `scripts\skill_entry.py` are in the current tree. No subscription or Hosted Worker is required.

### Using the Skill ZIP

Download `SHA256SUMS`, `enhe-product-promo-maker-skill-0.5.3.zip`, and `enhe-promotion-manager-extension-0.5.3.zip` from the same [GitHub Release](https://github.com/hqwzhu/enhe-promotion-manager/releases), and place them in the same download directory. Verify both release packages before installation:

```powershell
$releaseFiles = @(
  "enhe-product-promo-maker-skill-0.5.3.zip",
  "enhe-promotion-manager-extension-0.5.3.zip"
)
$sumLines = Get-Content ".\SHA256SUMS"
foreach ($name in $releaseFiles) {
  $record = $sumLines | Where-Object { $_.EndsWith($name) } | Select-Object -First 1
  if (-not $record) { throw "SHA256SUMS is missing $name" }
  $expected = ($record -split "\s+")[0]
  $actual = (Get-FileHash -LiteralPath ".\$name" -Algorithm SHA256).Hash
  if ($actual -ne $expected) { throw "$name SHA-256 verification failed" }
  Write-Host "$name SHA-256 OK"
}
```

Do not install either package if a hash differs. Download it again from the official release page and repeat the check.

Next, extract into a new empty staging directory, verify the Skill root, and replace the installed directory through a rollback-capable sequence. The process below does not recursively delete any directory:

```powershell
& {
  $ErrorActionPreference = "Stop"

  $skillHome = [IO.Path]::GetFullPath((Join-Path $HOME ".codex\skills"))
  if (Test-Path -LiteralPath $skillHome) {
    $skillHomeItem = Get-Item -LiteralPath $skillHome -Force
    if (-not $skillHomeItem.PSIsContainer) { throw "Skill home is not a directory" }
    if (($skillHomeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Skill home must not be a reparse point" }
  }
  New-Item -ItemType Directory -Path $skillHome -Force | Out-Null
  $skillHomeItem = Get-Item -LiteralPath $skillHome -Force
  if (-not $skillHomeItem.PSIsContainer) { throw "Skill home is not a directory" }
  if (($skillHomeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Skill home must not be a reparse point" }

  $installed = [IO.Path]::GetFullPath((Join-Path $skillHome "viral-product-copy-video-generator"))
  $expectedParent = [IO.Path]::GetFullPath((Split-Path -Parent $installed))
  if (-not [string]::Equals($expectedParent, $skillHome, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Install target is not contained by Skill home"
  }

  $tempRoot = [IO.Path]::GetFullPath($env:TEMP)
  $tempRootItem = Get-Item -LiteralPath $tempRoot -Force
  if (-not $tempRootItem.PSIsContainer) { throw "Temporary root is not a directory" }
  if (($tempRootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Temporary root must not be a reparse point" }
  $staging = [IO.Path]::GetFullPath((Join-Path $tempRoot ("enhe-skill-stage-" + [guid]::NewGuid().ToString("N"))))
  $stagingParent = [IO.Path]::GetFullPath((Split-Path -Parent $staging))
  if (-not [string]::Equals($stagingParent, $tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Staging path is not contained by the temporary root"
  }
  New-Item -ItemType Directory -Path $staging | Out-Null
  $stagingItem = Get-Item -LiteralPath $staging -Force
  if (($stagingItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Staging path must not be a reparse point" }
  Expand-Archive -LiteralPath ".\enhe-product-promo-maker-skill-0.5.3.zip" -DestinationPath $staging

  $stagingRoot = (Resolve-Path -LiteralPath $staging).Path
  $candidatePath = [IO.Path]::GetFullPath((Join-Path $staging "viral-product-copy-video-generator"))
  if (-not $candidatePath.StartsWith($stagingRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Staged Skill path escapes the staging directory"
  }
  $candidateItem = Get-Item -LiteralPath $candidatePath -Force
  if (-not $candidateItem.PSIsContainer) { throw "Staged Skill root is not a directory" }
  if (($candidateItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Staged Skill root must not be a reparse point" }
  $candidate = (Resolve-Path -LiteralPath $candidatePath).Path
  if (-not $candidate.StartsWith($stagingRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Resolved staged Skill path escapes the staging directory"
  }
  if (-not (Test-Path -LiteralPath (Join-Path $candidate "SKILL.md") -PathType Leaf)) { throw "Staged package is missing SKILL.md" }
  if (-not (Test-Path -LiteralPath (Join-Path $candidate "scripts\skill_entry.py") -PathType Leaf)) { throw "Staged package is missing scripts\skill_entry.py" }

  $backup = [IO.Path]::GetFullPath("$installed.backup.$(Get-Date -Format 'yyyyMMddHHmmss')")
  $backupParent = [IO.Path]::GetFullPath((Split-Path -Parent $backup))
  if (-not [string]::Equals($backupParent, $skillHome, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Backup path is not contained by Skill home"
  }
  $backupParentItem = Get-Item -LiteralPath $backupParent -Force
  if (-not $backupParentItem.PSIsContainer) { throw "Backup parent is not a directory" }
  if (($backupParentItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Backup parent must not be a reparse point" }
  if (Test-Path -LiteralPath $backup) { throw "Backup path already exists: $backup" }
  if (Test-Path -LiteralPath $installed) {
    $installedItem = Get-Item -LiteralPath $installed -Force
    if (-not $installedItem.PSIsContainer) { throw "Existing Skill path is not a directory" }
    if (($installedItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Existing Skill path must not be a reparse point" }
    $resolvedInstalled = (Resolve-Path -LiteralPath $installed).Path
    if (-not $resolvedInstalled.StartsWith($skillHome + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
      throw "Existing Skill path escapes Skill home"
    }
    Move-Item -LiteralPath $installed -Destination $backup
  }

  $failed = [IO.Path]::GetFullPath("$installed.failed.$([guid]::NewGuid().ToString('N'))")
  $failedParent = [IO.Path]::GetFullPath((Split-Path -Parent $failed))
  if (-not [string]::Equals($failedParent, $skillHome, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Failed-tree path is not contained by Skill home"
  }
  try {
    Move-Item -LiteralPath $candidate -Destination $installed
    python "$installed\scripts\skill_entry.py" --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "skill_entry.py --help validation failed" }
    python "$installed\scripts\self_evolution_audit.py" `
      --skip-runtime-checks `
      --out-dir "$HOME\promotion-output\install-audit"
    if ($LASTEXITCODE -ne 0) { throw "Installation audit failed" }
    Write-Host "New Skill validated. Rollback copy: $backup"
  } catch {
    $failureMessage = $_.Exception.Message
    if (Test-Path -LiteralPath $installed) {
      $failedInstalledItem = Get-Item -LiteralPath $installed -Force
      if (($failedInstalledItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Failed new Skill path is a reparse point and was not moved. $failureMessage" }
      Move-Item -LiteralPath $installed -Destination $failed
    }
    if (Test-Path -LiteralPath $backup) {
      $backupItem = Get-Item -LiteralPath $backup -Force
      if (($backupItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Backup path is a reparse point and was not restored. $failureMessage" }
      $resolvedBackup = (Resolve-Path -LiteralPath $backup).Path
      if (-not $resolvedBackup.StartsWith($skillHome + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Resolved backup path escapes Skill home and was not restored. $failureMessage"
      }
      Move-Item -LiteralPath $backup -Destination $installed
      throw "New Skill validation failed and the previous version was restored; failed tree retained at $failed. $failureMessage"
    }
    throw "New Skill validation failed; no previous version was available to restore, and the failed tree is retained at $failed. $failureMessage"
  }
}
```

After script-level validation succeeds, fully exit and reopen Codex, or refresh Skill discovery in the client and create a new task. Keep `$backup` until you complete one real command-discovery check and a minimal run. For a manual rollback, first confirm that the resolved `$installed` and `$backup` paths still remain under `$skillHome`, move the current installation to another retained directory, and move `$backup` back to `$installed`. Do not use recursive deletion commands for rollback.

To synchronize reviewed source into the Codex Skill directory, run `--sync-installed-skill` only from a Skill directory in a separate clone of the public repository. Do not run it from the installed `$installed` target directory; identical source and target files cause a same-file copy error.

## Optional dependencies

### Playwright, Chromium, and Pillow

Use these for dynamic product pages, browser-visible platform pages, and browser-assisted forms:

```powershell
python -m pip install playwright pillow
python -m playwright install chromium
```

You can also let the run command attempt to install Chromium under an explicit flag:

```powershell
python scripts\skill_entry.py `
  --link "https://www.enhe-tech.com.cn/promotion-manager" `
  --install-browser-if-missing `
  --out-dir ".\promotion-output"
```

### FFmpeg

FFmpeg is used for MP4 video drafts. On Windows:

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```

### Official YouTube API client (optional)

Install this only when you have your own OAuth credentials and account authorization and need the official API path:

```powershell
python -m pip install -r requirements-youtube.txt
```

Manage credentials through local environment variables or a local `.env` file. Do not commit or copy them into the public repository.

## MediaCrawler Sidecar (separate upstream dependency)

Local-login research for Zhihu, Xiaohongshu, and Douyin can use MediaCrawler Sidecar. It is not built into this repository. Obtain authorization and install it separately under the [MediaCrawler upstream project](https://github.com/NanmiCoder/MediaCrawler) license, installation instructions, and platform terms. Sidecar source, checkout, virtual environment, Cookies, Chrome profile, raw JSONL output, and identity salt should remain outside this public repository. The repository retains only controlled boundary scripts and normalized results.

The default Sidecar data root on Windows is `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler`. After installation, pin it to the upstream commit required by the documentation and scripts, then complete login locally. If it is not ready, the platform result is marked `provider_unavailable`; content is not invented.

## Installation boundaries

- Hosted Worker remains disabled; you do not need to deploy, configure, or purchase hosted execution.
- Cookies and Chrome login profiles stay on the local computer and are not uploaded to this public repository or its public release packages.
- Final publishing requires user review and action; official APIs additionally require user credentials and explicit approval.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Only real URLs, metrics, comments, orders, and revenue can enter the real-evidence workflow; evidence is not fabricated.
- Payment, subscription, license, credits, and billing backends are excluded only from the synchronization conclusion; the extension's existing billing UI and `billing-contract.json` remain included.

For operating instructions, continue with the [quick start](quick-start.md) and [Skill guide](skill-guide.md).
