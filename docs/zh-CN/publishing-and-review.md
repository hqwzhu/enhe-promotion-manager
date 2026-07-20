# 发布与复盘指南

发布流程默认先生成草稿和 dry-run，再由用户审核事实、文案、媒体、账号和平台字段。不同平台的授权能力不同，公开发行不会把准备就绪描述为已发布。

先从批次报告取得真实产品运行目录与队列路径：

```powershell
$batch = Get-Content -Raw ".\promotion-output\reports\promotion-manager\batch\product-batch-runner.json" | ConvertFrom-Json
$batch.promotionRuns | Format-Table id, status, outputDir, workflowManifest, publishQueue
$run = $batch.promotionRuns | Where-Object status -eq "ready" | Select-Object -First 1
if (-not $run) { throw "没有 ready 产品运行，请先检查批次报告" }
$runDir = $run.outputDir
$queue = $run.publishQueue
if (-not $queue -or -not (Test-Path -LiteralPath $queue)) { throw "目标运行没有可用发布队列" }
```

如果报告包含多个产品，请根据 `id`、URL 和状态选择目标项；不要手工猜测 `product-batch-runs\<run>` 名称。

## 三种发布路径

### Dry-run

Dry-run 只生成发布载荷、检查结果、缺失项和命令，不写入真实平台。它适合检查目标仓库、视频文件、标题、隐私状态、账号凭据变量和审批状态。

```powershell
python scripts\publish_readiness_runner.py `
  --publish-queue "$queue" `
  --platforms youtube,zhihu,xiaohongshu,douyin,github `
  --out-dir "$runDir"
```

### 手动发布

适合没有受支持官方 API、平台授权尚未确认或账号所有者希望完全控制提交的场景。发布包提供标题、正文、标签、媒体文件、评论提示、跟踪 URL 和核对清单。用户在平台页面逐项核对并提交。

### 浏览器辅助

浏览器会话可以打开平台入口、准备 payload、填写可见字段、保存截图并生成最后检查清单：

```powershell
python scripts\browser_publish_session.py `
  --publish-queue "$queue" `
  --run-form-fill `
  --headed `
  --out-dir "$runDir"
```

浏览器辅助在最终提交前停止。用户必须检查账号、页面、标题、正文、标签、视频、图片、隐私设置和平台提示，然后自行确认。

## 官方 API 路径

GitHub、YouTube 和其他已实现的官方发布端口默认是 dry-run。执行真实写入必须同时满足：

- 用户拥有目标账号和操作权限。
- 本机提供官方 API 凭据或 OAuth 授权。
- 目标仓库、分支、发布类型、视频文件和隐私状态明确。
- dry-run 无关键缺失项。
- 对 `skill_entry.py`、`final_capability_runner.py` 或 `publish_readiness_runner.py`，命令显式包含 `--execute-publish --approval I_APPROVE_PUBLISH`。

YouTube 还需要安装 `requirements-youtube.txt` 中的官方客户端；GitHub 写入前应确认 owner/repo、分支和动作类型。抖音官方 API 能力取决于用户实际获得的开放平台权限，未授权时使用手动或浏览器辅助路径。

## 发布前审核清单

1. 产品事实是否都能回到公开页面或用户提供的真实资料。
2. 竞品证据是否有来源，指标是否为实际可见值。
3. 标题和正文是否适合目标平台，并避免未经证实的承诺。
4. MP4、封面和详情图是否真实存在，`missing` 项是否已处理。
5. 发布账号、目标页面、隐私状态、标签和跟踪链接是否正确。
6. 平台登录、验证、风险控制或授权提示是否需要用户处理。
7. 是否已准备发布后登记 URL 和导入证据的目录。

## 证据登记与复盘

发布后先登记真实 URL，再导入真实指标、评论和业务数据：

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

证据可以来自平台导出的 CSV/XLSX/JSON、复制的可见指标文本、评论文件、订单或收入导出。没有真实证据时保持 `waiting_real_data`；演示文件必须保持合成标记，不得用于对外结果汇报。

## 发布边界

- Hosted Worker 保持关闭，公开版不提供无人值守发布服务。
- 最终发布需要用户审核和操作；浏览器辅助流程不会替用户完成最终平台提交。
- 工具不会规避 CAPTCHA、平台风险控制、登录检查或账号授权。
- Cookies、Chrome 登录配置和官方凭据只留在本机，不上传到本公开仓库或公开发行包。
- 只登记真实发布 URL、真实指标、真实评论、真实订单和真实收入；不会虚构证据。
- 支付、订阅、许可证、点数和账单后端仅排除在功能同步结论之外；扩展原有 billing UI 和 `billing-contract.json` 保留。
