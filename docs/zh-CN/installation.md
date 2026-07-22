# 安装指南

本文面向 Windows PowerShell，也给出跨平台提示。公开发行包含本地 Codex Skill、Chrome Manifest V3 扩展和校验脚本；Hosted Worker 保持关闭，不需要为本地工作流部署服务端。

## Windows 首选安装检查

克隆公开仓库并进入 `skill\viral-product-copy-video-generator` 后，先运行这组 Windows PowerShell 命令：

```powershell
python --version
python -m pip install playwright pillow
python -m playwright install chromium
python scripts\self_evolution_audit.py --skip-runtime-checks --out-dir ".\promotion-output\install-audit"
```

这组命令安装浏览器与图片依赖并执行只读安装审计。FFmpeg 和 YouTube 官方 API 客户端按需单独安装，见下文。

## 路径一：Chrome Web Store

适合只需要当前页面转任务和命令生成的用户。

1. 打开 [ENHE Promotion Manager](https://chromewebstore.google.com/detail/enhe-promotion-manager/dloklkbnmoigemnfigbkibogmgbieppl)。
2. 点击“添加至 Chrome”，确认浏览器安装提示。
3. 打开一个公开产品页面，完成你的登录或页面准备后，主动点击扩展图标。
4. 点击“使用当前标签页”，选择平台、工作流深度和命令类型，再复制命令到本地仓库运行。

公开源码/发行候选为 `0.5.4`。已发布的 Chrome 商店和 GitHub Release 包版本仍为 `0.5.3`；v0.5.4 尚未提交 Chrome 审核。安装后请以扩展界面显示的版本和 [版本同步说明](version-sync.md) 为准。

## 路径二：未打包扩展

适合需要审阅源码、参与测试或使用尚未提交商店的版本。

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd .\enhe-promotion-manager
```

1. 在 Chrome 地址栏打开 `chrome://extensions`。
2. 打开右上角“开发者模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择仓库里的 `extension\chrome` 文件夹。
5. 打开产品页面并在用户主动操作后使用“使用当前标签页”。

扩展只读取当前标签页的可见入口并生成本地命令；它不会把 Cookies、Chrome 登录配置或页面登录态上传到本公开仓库或公开发行包。

## 路径三：Skill ZIP 或源码

适合需要完整本地流程、脚本输出、媒体草稿、发布包和真实证据复盘的用户。先安装 Python 3.10 或更高版本（推荐 Python 3.11），并确认 PowerShell 中可调用：

```powershell
python --version
```

### 使用公开仓库源码

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd .\enhe-promotion-manager\skill\viral-product-copy-video-generator
python -m pip install --upgrade pip
```

公开仓库把 Skill 放在 `skill\viral-product-copy-video-generator`；进入该目录后，`SKILL.md` 和 `scripts\skill_entry.py` 位于当前目录。无需订阅，不要求 Hosted Worker。

### 使用 Skill ZIP

从同一个 [GitHub Release](https://github.com/hqwzhu/enhe-promotion-manager/releases) 下载 `SHA256SUMS`、`enhe-product-promo-maker-skill-0.5.3.zip` 和 `enhe-promotion-manager-extension-0.5.3.zip`，放在同一下载目录。先校验两个发行包：

```powershell
$releaseFiles = @(
  "enhe-product-promo-maker-skill-0.5.3.zip",
  "enhe-promotion-manager-extension-0.5.3.zip"
)
$sumLines = Get-Content ".\SHA256SUMS"
foreach ($name in $releaseFiles) {
  $record = $sumLines | Where-Object { $_.EndsWith($name) } | Select-Object -First 1
  if (-not $record) { throw "SHA256SUMS 中缺少 $name" }
  $expected = ($record -split "\s+")[0]
  $actual = (Get-FileHash -LiteralPath ".\$name" -Algorithm SHA256).Hash
  if ($actual -ne $expected) { throw "$name SHA-256 校验失败" }
  Write-Host "$name SHA-256 OK"
}
```

任一哈希不一致时不要安装，重新从正式发行页下载并再次校验。

然后解压到新的空暂存目录，验证 Skill 根目录，再以可回退方式替换安装目录。以下流程不会递归删除任何目录：

```powershell
& {
  $ErrorActionPreference = "Stop"

  $skillHome = [IO.Path]::GetFullPath((Join-Path $HOME ".codex\skills"))
  if (Test-Path -LiteralPath $skillHome) {
    $skillHomeItem = Get-Item -LiteralPath $skillHome -Force
    if (-not $skillHomeItem.PSIsContainer) { throw "Skill 根路径不是目录" }
    if (($skillHomeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Skill 根路径不能是重解析点" }
  }
  New-Item -ItemType Directory -Path $skillHome -Force | Out-Null
  $skillHomeItem = Get-Item -LiteralPath $skillHome -Force
  if (-not $skillHomeItem.PSIsContainer) { throw "Skill 根路径不是目录" }
  if (($skillHomeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Skill 根路径不能是重解析点" }

  $installed = [IO.Path]::GetFullPath((Join-Path $skillHome "viral-product-copy-video-generator"))
  $expectedParent = [IO.Path]::GetFullPath((Split-Path -Parent $installed))
  if (-not [string]::Equals($expectedParent, $skillHome, [StringComparison]::OrdinalIgnoreCase)) {
    throw "安装目标不在 Skill 根目录内"
  }

  $tempRoot = [IO.Path]::GetFullPath($env:TEMP)
  $tempRootItem = Get-Item -LiteralPath $tempRoot -Force
  if (-not $tempRootItem.PSIsContainer) { throw "临时目录根路径不是目录" }
  if (($tempRootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "临时目录根路径不能是重解析点" }
  $staging = [IO.Path]::GetFullPath((Join-Path $tempRoot ("enhe-skill-stage-" + [guid]::NewGuid().ToString("N"))))
  $stagingParent = [IO.Path]::GetFullPath((Split-Path -Parent $staging))
  if (-not [string]::Equals($stagingParent, $tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "暂存路径不在临时目录内"
  }
  New-Item -ItemType Directory -Path $staging | Out-Null
  $stagingItem = Get-Item -LiteralPath $staging -Force
  if (($stagingItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "暂存路径不能是重解析点" }
  Expand-Archive -LiteralPath ".\enhe-product-promo-maker-skill-0.5.3.zip" -DestinationPath $staging

  $stagingRoot = (Resolve-Path -LiteralPath $staging).Path
  $candidatePath = [IO.Path]::GetFullPath((Join-Path $staging "viral-product-copy-video-generator"))
  if (-not $candidatePath.StartsWith($stagingRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "暂存 Skill 路径越出暂存目录"
  }
  $candidateItem = Get-Item -LiteralPath $candidatePath -Force
  if (-not $candidateItem.PSIsContainer) { throw "暂存 Skill 根路径不是目录" }
  if (($candidateItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "暂存 Skill 根路径不能是重解析点" }
  $candidate = (Resolve-Path -LiteralPath $candidatePath).Path
  if (-not $candidate.StartsWith($stagingRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "暂存 Skill 解析路径越出暂存目录"
  }
  if (-not (Test-Path -LiteralPath (Join-Path $candidate "SKILL.md") -PathType Leaf)) { throw "暂存包缺少 SKILL.md" }
  if (-not (Test-Path -LiteralPath (Join-Path $candidate "scripts\skill_entry.py") -PathType Leaf)) { throw "暂存包缺少 scripts\skill_entry.py" }

  $backup = [IO.Path]::GetFullPath("$installed.backup.$(Get-Date -Format 'yyyyMMddHHmmss')")
  $backupParent = [IO.Path]::GetFullPath((Split-Path -Parent $backup))
  if (-not [string]::Equals($backupParent, $skillHome, [StringComparison]::OrdinalIgnoreCase)) {
    throw "备份路径不在 Skill 根目录内"
  }
  $backupParentItem = Get-Item -LiteralPath $backupParent -Force
  if (-not $backupParentItem.PSIsContainer) { throw "备份父路径不是目录" }
  if (($backupParentItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "备份父路径不能是重解析点" }
  if (Test-Path -LiteralPath $backup) { throw "备份路径已存在：$backup" }
  if (Test-Path -LiteralPath $installed) {
    $installedItem = Get-Item -LiteralPath $installed -Force
    if (-not $installedItem.PSIsContainer) { throw "现有 Skill 路径不是目录" }
    if (($installedItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "现有 Skill 路径不能是重解析点" }
    $resolvedInstalled = (Resolve-Path -LiteralPath $installed).Path
    if (-not $resolvedInstalled.StartsWith($skillHome + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
      throw "现有 Skill 路径越出 Skill 根目录"
    }
    Move-Item -LiteralPath $installed -Destination $backup
  }

  $failed = [IO.Path]::GetFullPath("$installed.failed.$([guid]::NewGuid().ToString('N'))")
  $failedParent = [IO.Path]::GetFullPath((Split-Path -Parent $failed))
  if (-not [string]::Equals($failedParent, $skillHome, [StringComparison]::OrdinalIgnoreCase)) {
    throw "失败树路径不在 Skill 根目录内"
  }
  try {
    Move-Item -LiteralPath $candidate -Destination $installed
    python "$installed\scripts\skill_entry.py" --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "skill_entry.py --help 验证失败" }
    python "$installed\scripts\self_evolution_audit.py" `
      --skip-runtime-checks `
      --out-dir "$HOME\promotion-output\install-audit"
    if ($LASTEXITCODE -ne 0) { throw "安装审计执行失败" }
    Write-Host "新 Skill 验证通过。回退副本：$backup"
  } catch {
    $failureMessage = $_.Exception.Message
    if (Test-Path -LiteralPath $installed) {
      $failedInstalledItem = Get-Item -LiteralPath $installed -Force
      if (($failedInstalledItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "失败的新 Skill 路径是重解析点，未移动。$failureMessage" }
      Move-Item -LiteralPath $installed -Destination $failed
    }
    if (Test-Path -LiteralPath $backup) {
      $backupItem = Get-Item -LiteralPath $backup -Force
      if (($backupItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "备份路径是重解析点，未恢复。$failureMessage" }
      $resolvedBackup = (Resolve-Path -LiteralPath $backup).Path
      if (-not $resolvedBackup.StartsWith($skillHome + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "备份解析路径越出 Skill 根目录，未恢复。$failureMessage"
      }
      Move-Item -LiteralPath $backup -Destination $installed
      throw "新 Skill 验证失败，已恢复旧版本；失败树保留在 $failed。$failureMessage"
    }
    throw "新 Skill 验证失败；没有旧版本可恢复，失败树保留在 $failed。$failureMessage"
  }
}
```

脚本级验证通过后，完全退出并重新打开 Codex，或在客户端中刷新 Skill 发现并新建任务。完成一次实际命令发现与最小运行验收前保留 `$backup`。如需人工回退，先确认 `$installed` 与 `$backup` 的解析路径仍位于 `$skillHome`，把当前安装移到另一个保留目录，再把 `$backup` 移回 `$installed`；不要用递归删除命令处理回退。

如需把已审核源码同步到 Codex Skill 目录，只能从一个独立克隆的公开仓库 Skill 目录运行 `--sync-installed-skill`。不要从 `$installed` 目标目录运行同步命令；源文件与目标文件相同时会发生同文件复制错误。

## 可选依赖

### Playwright、Chromium 与 Pillow

用于动态产品页、浏览器可见平台页面和浏览器辅助表单：

```powershell
python -m pip install playwright pillow
python -m playwright install chromium
```

也可以在明确参数下让运行命令尝试安装 Chromium：

```powershell
python scripts\skill_entry.py `
  --link "https://www.enhe-tech.com.cn/promotion-manager" `
  --install-browser-if-missing `
  --out-dir ".\promotion-output"
```

### FFmpeg

用于 MP4 视频草稿。Windows 可使用：

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```

### YouTube 官方 API（可选）

仅在你拥有自己的 OAuth 凭据、账号授权并需要官方 API 路径时安装：

```powershell
python -m pip install -r requirements-youtube.txt
```

凭据只通过本机环境变量或本机 `.env` 管理；不要提交或复制到公开仓库。

## MediaCrawler Sidecar（独立上游依赖）

知乎、小红书、抖音的本机登录态研究可以使用 MediaCrawler Sidecar。它不是本仓库内置组件，需要你按 [MediaCrawler 上游项目](https://github.com/NanmiCoder/MediaCrawler) 的许可证、安装说明和平台条款单独取得授权与安装。Sidecar 代码、checkout、虚拟环境、Cookies、Chrome profile、原始 JSONL 输出和身份盐应位于本公开仓库之外；本仓库只保留受控边界脚本和归一化结果。

Sidecar 默认数据根目录为 Windows 的 `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler`。安装后应固定到文档和脚本要求的上游提交，并在本机完成登录。若未就绪，平台结果会标记为 `provider_unavailable`，不会伪造内容。

## 安装边界

- Hosted Worker 保持关闭，不需要部署、配置或购买托管运行。
- Cookies 与 Chrome 登录配置只留在本机，不上传到本公开仓库或公开发行包。
- 最终发布需要用户审核和操作；官方 API 还需要用户凭据与明确批准。
- 工具不会规避 CAPTCHA、平台风险控制、登录检查或账号授权。
- 真实 URL、指标、评论、订单和收入才可进入真实证据；不会虚构证据。
- 支付、订阅、许可证、点数和账单后端仅排除在同步结论之外；扩展原有 billing UI 和 `billing-contract.json` 保留。

更多运行说明见 [快速开始](quick-start.md) 和 [Skill 指南](skill-guide.md)。
