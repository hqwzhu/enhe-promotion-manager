# Skill 指南

## 输入

Skill 的最小输入是一个公开产品 URL。也支持：

- 重复传入 `--link`，或使用 `--links-file` 每行提供一个链接。
- 用 `--link-mode product` 直接把链接当成产品页，用 `--link-mode site` 先做网站产品发现。
- 选择 `--platforms`、`--goal`、`--language` 和 `--out-dir`。
- 选择浏览器读取、竞品补采、视频抽帧、语音、媒体和发布队列等可选步骤。
- 发布后提供真实 `--published-url`、指标导出、评论证据、订单和收入证据。

默认数据边界是本机文件系统。URL 读取使用公开页面、浏览器可见内容、官方路径或用户主动提供的文件；不会读取或提交私有账号数据作为公共证据。

## 常用命令

### 单链接完整运行

```powershell
python scripts\skill_entry.py `
  --link "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir ".\promotion-output"
```

普通用户应使用 `skill_entry.py`。`promotion_manager.py` 是需要完整结构化产品字段和位置参数的底层报告生成器，不是单链接入口。

### 找到实际产品运行目录

单链接入口仍通过批次运行器生成产品目录，名称包含运行序号和安全化产品标识，不应手工猜测。读取批次报告：

```powershell
$batchPath = ".\promotion-output\reports\promotion-manager\batch\product-batch-runner.json"
$batch = Get-Content -Raw $batchPath | ConvertFrom-Json
$batch.promotionRuns | Format-Table id, status, outputDir, workflowManifest, publishQueue
$run = $batch.promotionRuns | Where-Object status -eq "ready" | Select-Object -First 1
if (-not $run) { throw "没有 ready 产品运行，请先检查批次报告" }
$runDir = $run.outputDir
$queue = $run.publishQueue
```

如果有多个产品运行，请按 `id`、URL 和状态选择目标项。`outputDir` 指向实际的 `promotion-output\product-batch-runs\<run>`，`workflowManifest` 和 `publishQueue` 给出可直接使用的文件路径。

### 浏览器辅助发布会话

```powershell
python scripts\browser_publish_session.py `
  --publish-queue "$queue" `
  --out-dir "$runDir"
```

### 真实证据收件箱

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

### 复盘与就绪审计

```powershell
python scripts\performance_monitor.py --out-dir "$runDir"
python scripts\final_capability_readiness.py --out-dir ".\promotion-output"
```

## 输出产物

`skill_entry.py` 在顶层 `--out-dir` 写入 Skill、批次、最终运行和就绪报告。每个产品的事实、来源、竞品任务、平台内容、口播稿、分镜、媒体、发布队列、发布包和复盘写入批次报告所列的 `outputDir`。典型相对路径是 `reports\promotion-manager\generated-content`、`videos`、`media-assets`、`reports\promotion-manager\publish-packs`、`reports\promotion-manager\publish-queue` 和 `reports\promotion-manager\retrospectives`，均应相对于实际 `$runDir` 解读。

常见状态包括：

- `ready`：该步骤的输入、依赖和输出均满足本地检查。
- `partial_ready`：部分内容或证据已完成，仍有缺失或受限步骤。
- `missing`：所需媒体、来源或用户文件尚未提供。
- `provider_unavailable`：平台数据提供方、Sidecar 或浏览器运行时不可用。
- `waiting_login`：需要用户在本机完成平台登录或扫码。
- `manual_verification_required`：平台要求用户完成验证。
- `blocked_by_platform`：平台风险控制或访问限制阻止当前请求。
- `waiting_real_data`：尚未导入真实发布 URL、指标、评论或业务证据。

## 依赖与本地数据边界

- Python 3.10+（推荐 3.11）和 Codex 是基础运行环境。
- Playwright/Chromium 用于动态网页与浏览器可见研究；Pillow 用于 PNG；FFmpeg 用于 MP4；YouTube 客户端用于可选官方 API 路径。
- MediaCrawler Sidecar 单独安装在本机，默认根目录为 `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler`，不是公开仓库内容。
- `promotion-output`、证据收件箱、Cookies、Chrome 登录配置、Sidecar checkout、虚拟环境和原始输出均应留在本机。
- Hosted Worker 保持关闭，不需要云端运行时。

## 错误处理

Skill 会在报告中写明错误类别、重试次数、缺失项和下一步；Sidecar 会清理默认原始目录，只有显式保留调试原始输出时才留下并给出敏感数据警告。不要把日志中的 Cookies、令牌、订单或客户数据提交到公开仓库。

## 边界

- 最终发布需要用户审核和操作；浏览器辅助命令在最终提交前停止。
- 工具不会规避 CAPTCHA、平台风险控制、登录检查或账号授权。
- 只导入真实 URL、指标、评论、订单和收入；合成演示只能用于本地验证。
- Cookies 与 Chrome 登录配置只留在本机，不上传到本公开仓库或公开发行包。
- 支付、订阅、许可证、点数和账单后端仅排除在功能同步结论之外；扩展 billing UI 和 `billing-contract.json` 保留。
