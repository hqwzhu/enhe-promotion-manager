# 快速开始

## 1. 准备本地目录

在 Windows PowerShell 中克隆公开仓库并进入随包 Skill 目录：

```powershell
git clone https://github.com/hqwzhu/enhe-promotion-manager.git
cd .\enhe-promotion-manager\skill\viral-product-copy-video-generator
python --version
```

Playwright/Chromium、Pillow 和 FFmpeg 都是可选依赖。没有它们时仍可生成产品事实、证据索引和文本草稿；缺失的媒体会明确标记。

## 2. 运行一个产品页

以下命令使用公开示例 URL，参数形状可直接替换为你的产品链接：

```powershell
python scripts\skill_entry.py `
  --link "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir ".\promotion-output"
```

运行不需要订阅或 Hosted Worker。若链接是网站首页而不是具体产品页，可以加 `--link-mode site`，让工作流先发现候选产品入口：

```powershell
python scripts\skill_entry.py `
  --link "https://example.com" `
  --link-mode site `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir ".\promotion-output"
```

## 3. 查看输出

先从顶层批次报告读取实际产品运行目录，不要猜测 `<run>` 名称：

```powershell
$batchPath = ".\promotion-output\reports\promotion-manager\batch\product-batch-runner.json"
$batch = Get-Content -Raw $batchPath | ConvertFrom-Json
$batch.promotionRuns | Format-Table id, status, outputDir, workflowManifest, publishQueue
$run = $batch.promotionRuns | Where-Object status -eq "ready" | Select-Object -First 1
if (-not $run) { throw "没有 ready 产品运行，请先检查批次报告" }
$runDir = $run.outputDir
$queue = $run.publishQueue
```

多个产品运行时，应根据 `id`、URL 和状态选择目标项。`outputDir` 是实际的 `promotion-output\product-batch-runs\<run>`，其中 `<run>` 由运行时生成。产品目录中的重点路径包括：

| 目录或文件 | 内容 |
| --- | --- |
| `$runDir\reports\promotion-manager\generated-content\` | 各平台标题、正文、标签、口播稿、分镜和内容审核报告 |
| `$runDir\videos\` | FFmpeg 可用时生成的 MP4 视频草稿 |
| `$runDir\media-assets\` | Pillow 可用时按平台生成的 PNG 封面图与详情图 |
| `$runDir\reports\promotion-manager\publish-queue\` | 发布队列和每个平台的人工/官方 API 入口 |
| `$runDir\reports\promotion-manager\publish-packs\` | 整理好的发布包、警告、缺失项和操作步骤 |
| `$runDir\reports\promotion-manager\retrospectives\` | 有真实证据后生成的复盘与下一轮建议 |

手动运行真实证据收件箱命令并把 `--out-dir` 设为 `$runDir` 后，报告分别位于 `$runDir\reports\promotion-manager\real-evidence-inbox-setup\` 和 `$runDir\reports\promotion-manager\real-evidence-inbox\`。

如果某个依赖不可用，报告可能出现 `partial_ready` 或媒体 `missing`。这表示文本或部分证据已可用，不代表缺失的媒体或平台结果已经生成。

## 4. 从 Chrome 当前页面生成命令

安装扩展后：

1. 打开公开产品页面。
2. 用户主动点击扩展图标，点击“使用当前标签页”。
3. 选择平台、工作流深度和命令类型。
4. 复制命令，在 `skill\viral-product-copy-video-generator` 目录运行并审阅输出。

扩展生成的命令只是本地执行入口，不会替你提交最终发布。语言可在插件内切换为中文或英文。

## 5. 先审阅，再准备发布

确认事实、来源、文案、媒体路径和风险提示后，使用发布辅助命令生成 dry-run 或浏览器可见字段载荷：

```powershell
python scripts\browser_publish_session.py `
  --publish-queue "$queue" `
  --out-dir "$runDir"
```

使用 `--run-form-fill --headed` 时，工具只填写可见字段并在最终提交前停止。真实发布仍需要用户确认、平台登录和账号授权。

## 6. 发布后导入真实证据

先创建证据收件箱：

```powershell
python scripts\real_evidence_inbox_setup.py `
  --product-url "https://www.enhe-tech.com.cn/promotion-manager" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"
```

把真实发布 URL、平台导出、评论、订单和收入文件放入收件箱，再导入并运行监控：

```powershell
python scripts\real_evidence_inbox.py `
  --inbox-dir ".\promotion-evidence-inbox" `
  --out-dir "$runDir"

python scripts\performance_monitor.py `
  --out-dir "$runDir"
```

没有真实数据时，状态保持 `waiting_real_data`。合成演示只用于验证本地流程，不能当作发布表现、订单或收入。

## 统一边界

- Hosted Worker 保持关闭，不描述为可用服务。
- Cookies 与 Chrome 登录配置只留在本机，不上传到本公开仓库或公开发行包。
- 最终发布需要用户审核和操作，浏览器辅助流程会在最终提交前停止。
- 工具不会规避 CAPTCHA、平台风险控制、登录检查或账号授权。
- 只使用真实 URL、指标、评论、订单和收入；不会虚构证据。
- 支付、订阅、许可证、点数和账单后端仅排除在同步结论之外；扩展原有 billing UI 和 `billing-contract.json` 保留。
