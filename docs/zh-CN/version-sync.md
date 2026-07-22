# 版本与功能同步

## 当前标记

公开仓库/Skill/扩展源码/发行候选版本：0.5.4

已发布的 Chrome 商店版本：0.5.3

非支付命令引用：11/11 已在随包 Skill 中存在

支付与订阅：不纳入功能同步结论，但扩展原有 UI 和 billing-contract.json 保留

Hosted Worker：关闭

## 11 项非支付命令

公开发行对扩展源码引用的 Python 命令进行解析，并确认随包 Skill 中存在对应脚本：

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

“11/11 已存在”只说明扩展引用的非支付命令在随包 Skill 中有对应入口，并经过公开发行合同检查。它不表示所有平台账号、第三方依赖、官方 API 权限、真实媒体或真实证据已经可用。

## 商店与源码版本关系

已发布的 Chrome 商店条目 https://chromewebstore.google.com/detail/enhe-promotion-manager/dloklkbnmoigemnfigbkibogmgbieppl 和 GitHub Release 包均使用版本 `0.5.3`。公开仓库/Skill/扩展源码为 `0.5.4` 发行候选，尚未提交 Chrome 商店审核。

## 同步结论不包含什么

支付、订阅、许可证购买、点数和账单后端不纳入“扩展命令与随包 Skill 同步”的结论。排除仅针对同步审计范围，不代表这些 UI 或文件被删除：

- 扩展原有支付与订阅界面继续保留。
- 许可证、用量授权、Hosted Run endpoint、结算页和账单入口的 UI 字段继续保留。
- `billing-contract.json` 继续保留。
- 这些商业能力需要独立部署、隐私、安全、计费和生产可用性验证。
- Hosted Worker 当前关闭，公开发行不把托管运行描述为可用能力。

## 发行边界

- Cookies、Chrome 登录配置、Sidecar checkout、虚拟环境、身份盐和运行态不进入公开仓库或公开发行包。
- 最终发布需要用户审核和操作；浏览器辅助流程在最终提交前停止。
- 工具不会规避 CAPTCHA、平台风险控制、登录检查或账号授权。
- 真实 URL、指标、评论、订单和收入才可作为真实证据；不会虚构数据。
- MediaCrawler 是独立上游依赖，其授权不因本仓库 MIT License 自动转移。

## 如何检查本地 Skill 是否同步

进入一个独立克隆的公开仓库 `skill\viral-product-copy-video-generator` 源目录后运行。不要从 `$HOME\.codex\skills\viral-product-copy-video-generator` 安装目标目录执行同步：

```powershell
python scripts\self_evolution_audit.py `
  --sync-installed-skill `
  --approval I_APPROVE_SKILL_SYNC `
  --out-dir ".\promotion-output"
```

然后运行就绪审计：

```powershell
python scripts\final_capability_readiness.py `
  --out-dir ".\promotion-output"
```

同步只覆盖受管理的 Skill 文件，不复制 Cookies、Chrome 登录配置、`.env`、证据收件箱或 `promotion-output`。
