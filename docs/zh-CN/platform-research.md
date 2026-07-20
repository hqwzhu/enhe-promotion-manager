# 平台研究指南

平台研究的目标是获得可复核的内容结构、创作者线索、公开指标和用户反馈，而不是承诺某个传播结果。每条证据都应保留来源、时间、平台、获取方式和状态。

## 支持的研究路径

### 公开与官方路径

- 产品网站：公开 HTML、站点地图、浏览器快照和用户保存的页面文件。
- YouTube：公开页面、公开可见指标和用户授权的官方 API 路径。
- GitHub：公开仓库、README、Issue、Release、提交信息和公开互动。
- 知乎、小红书、抖音：公开页面、浏览器可见页面、用户主动导出和可选本机 Sidecar。

研究报告只把实际获取的页面、链接、指标和评论标为证据。无法访问、没有公开数字或没有用户导出时，应保留 `missing`、`partial_ready`、`provider_unavailable` 或相应阻塞状态。

### 浏览器可见研究

安装 Playwright/Chromium 后，工作流可以读取动态渲染的公开页面、截图和可见文本。浏览器辅助不会获得超出用户和浏览器当前权限的内容，也不会把 Chrome 登录配置上传到公开仓库。

### MediaCrawler Sidecar 本机登录态

Sidecar 是独立的上游依赖，支持知乎、小红书和抖音的 `search`、`detail`、`creator` 模式。安装和运行都发生在本机：

```powershell
python scripts\platform_data_manager.py setup --check
```

只有用户明确同意网络安装并已确认上游许可证与平台条款时，才执行：

```powershell
python scripts\platform_data_manager.py setup --install
```

关键词采集示例：

```powershell
python scripts\platform_data_manager.py collect `
  --platform xiaohongshu `
  --mode search `
  --query "AI 产品推广" `
  --max-contents 10 `
  --max-comments 20 `
  --out-dir ".\promotion-output"
```

Sidecar 默认连接用户控制的本机 Chrome、禁用代理并限制采集数量与并发。Cookies、登录配置、checkout、虚拟环境、身份盐和原始数据保存在公开仓库之外。默认原始目录在归一化后清理；`--keep-raw` 只用于本地调试，原始文件可能含敏感标识，不得上传。

## 平台限制

### 知乎

公开问题、回答和用户可见页面可以作为证据来源，但页面结构、登录要求、反自动化限制和内容折叠可能导致部分结果。出现验证或登录提示时，状态应停在 `manual_verification_required` 或 `waiting_login`，由用户处理后再决定是否继续。

### 小红书

匿名页面常出现内容不完整、链接参数变化或登录限制。详情模式应使用真实内容 URL/ID，搜索和评论数量保持受控。遇到风险控制、验证或登录要求时停止采集并保留状态，不把空结果写成“没有相关内容”。

### 抖音

网页可见内容、评论和创作者信息会受到登录、地区、页面渲染和平台权限影响。研究结果只记录实际可见信息。官方发布权限与研究访问是不同门槛，研究成功不代表账号具备发布 API 权限。

## 证据状态

| 状态 | 含义 | 建议动作 |
| --- | --- | --- |
| `ready` | 受控请求完成并产生可归一化证据 | 审核来源、时间和内容再用于草稿 |
| `partial_ready` | 获得部分内容，但评论、字段或目标不完整 | 使用已有证据，同时创建补采任务 |
| `provider_unavailable` | Sidecar、浏览器、固定版本或依赖不可用 | 检查安装，或改用公开页面/用户导出 |
| `waiting_login` | 需要用户在本机完成登录或扫码 | 用户完成登录后重试，禁止分享登录态 |
| `manual_verification_required` | 平台要求真人验证 | 用户自行处理平台验证，再决定是否继续 |
| `blocked_by_platform` | 平台风险控制或访问限制阻止请求 | 停止当前路径，改用官方、公开或用户导出证据 |
| `missing` | 目标、页面或证据文件不存在 | 补充真实目标或标记为未获取 |

## 研究边界

- Hosted Worker 保持关闭，平台研究在本机执行。
- 工具不会规避 CAPTCHA、平台风险控制、登录检查、账号授权或地区限制。
- Cookies 与 Chrome 登录配置只留在本机，不上传到本公开仓库或公开发行包。
- 最终发布需要用户审核和操作；研究结果不自动触发平台发布。
- 只使用真实 URL、指标、评论、订单和收入；不会虚构证据。
- 支付、订阅、许可证、点数和账单后端仅排除在功能同步结论之外；扩展原有 billing UI 和 `billing-contract.json` 保留。
