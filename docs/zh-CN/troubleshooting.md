# 故障排查

先运行最小命令并查看 `promotion-output\reports\promotion-manager\` 下的状态。不要删除 `partial_ready`、`missing` 或错误报告；它们说明了已完成内容和下一步。

## 缺少 Playwright 或 Chromium

现象：动态页面为空、浏览器启动失败、报告显示浏览器运行时不可用。

```powershell
python -m pip install playwright
python -m playwright install chromium
```

确认当前命令使用同一个 Python 环境。也可在 `skill_entry.py` 加 `--install-browser-if-missing`，但该参数会执行明确的网络安装，适合用户已同意的本机环境。

## 缺少 FFmpeg

现象：文案和分镜已生成，MP4 状态为 `missing`，或报告提示找不到 `ffmpeg`。

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```

安装后重新打开 PowerShell，再运行媒体或完整工作流。不要把脚本和分镜误报为已完成的视频文件。

## 缺少 Pillow

现象：PNG 封面图或详情图为 `missing`。

```powershell
python -m pip install pillow
```

重跑媒体包步骤后，检查发布包中的图片路径是否真实存在。

## `partial_ready` 或媒体 `missing`

`partial_ready` 表示部分事实、证据或草稿已可用，但某些页面、评论、媒体或平台步骤未完成。按报告中的 `reason`、`warnings` 和 `nextActions` 逐项处理。常见原因包括动态页面依赖缺失、平台只返回部分内容、视频源不存在、FFmpeg/Pillow 未安装或用户尚未导入真实证据。

## Sidecar 未就绪

先做只读检查：

```powershell
python scripts\platform_data_manager.py setup --check
```

若状态为 `provider_unavailable`，核对 Git、`uv`、Chrome、固定上游提交、Sidecar Python 环境和默认目录 `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler`。仅在确认 MediaCrawler 上游许可证、平台条款并同意网络安装后执行：

```powershell
python scripts\platform_data_manager.py setup --install
```

## 登录、平台验证或风险控制

常见状态：

- `waiting_login`：在本机浏览器完成登录或扫码后再重试。
- `manual_verification_required`：平台要求用户完成人机验证，由用户处理。
- `blocked_by_platform`：停止当前请求，改用公开页面、官方接口或用户导出。

工具不会规避 CAPTCHA、平台风险控制、登录检查或账号授权。不要频繁重试受限路径，也不要把 Cookies 或 Chrome profile 复制到仓库。

## Windows 中文与 UTF-8

现象：终端中文乱码，但 Markdown 文件在编辑器中正常；或脚本读取保存文件时编码不一致。

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
```

使用支持 UTF-8 的编辑器，不要把 Markdown 另存为 ANSI。验证文件编码：

```powershell
python -c "from pathlib import Path; Path('distribution/README.md').read_text(encoding='utf-8'); print('UTF-8 OK')"
```

## 已安装 Skill 版本陈旧

现象：Chrome 扩展生成了命令，但已安装 Skill 缺少对应脚本，或本地行为仍像旧版本。

进入一个独立克隆、已审核的公开仓库 `skill\viral-product-copy-video-generator` 源目录后同步。不要在 `$HOME\.codex\skills\viral-product-copy-video-generator` 安装目标目录中运行；源与目标相同时会发生同文件复制错误：

```powershell
python scripts\self_evolution_audit.py `
  --sync-installed-skill `
  --approval I_APPROVE_SKILL_SYNC `
  --out-dir ".\promotion-output"
```

同步后检查已安装目录中的 `SKILL.md`、`component-manifest.json`（公开发行包）和 11 项非支付命令脚本。同步不会复制 `promotion-output`、Cookies、Chrome 配置或 `.env`。

## 发布命令被拒绝

先回到 dry-run，检查凭据存在性、目标账号、仓库/视频路径、权限和审批值。`skill_entry.py`、`final_capability_runner.py` 和 `publish_readiness_runner.py` 的官方写入开关是 `--execute-publish --approval I_APPROVE_PUBLISH`；浏览器辅助在最终提交前停止，最终发布由用户确认。

## 没有复盘数据

若状态为 `waiting_real_data`，创建并填写真实证据收件箱。只导入真实发布 URL、真实指标、真实评论、真实订单和真实收入。演示数据不能用于对外表现结论。

## 仍然无法解决

保留脱敏后的命令、版本、状态代码和最小日志，发送至 huqingwei5942@gmail.com。不要公开粘贴 API 密钥、Cookies、许可证密钥、账号信息、订单或客户个人数据。

Hosted Worker 保持关闭；支付、订阅、许可证、点数和账单后端仅排除在同步结论之外，扩展原有 billing UI 和 `billing-contract.json` 保留。
