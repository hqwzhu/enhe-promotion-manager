#!/usr/bin/env python3
"""Generate a Chinese operator action checklist for reaching 100% readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from completion_roadmap import build_report


ZH_MODULES: dict[str, dict[str, str]] = {
    "codex_skill_local_promotion_loop": {
        "name": "Codex Skill 本地推广闭环",
        "whyNot100": "还缺少一次当前真实产品的端到端运行证据，以及运行后生成的最终 readiness 报告。",
        "definition": "用真实产品 URL 跑完读取、竞品研究、内容生成、发布包、证据收集模板、最终审计，并且输出文件都存在。",
        "firstAction": "先给一个真实产品 URL，然后运行 skill_entry.py。",
    },
    "copy_video_cover_detail_publish_pack": {
        "name": "文案、视频、封面、详情图、发布包",
        "whyNot100": "代码可以生成资产，但 100% 需要当前真实产品对应的 MP4、封面 PNG、详情图 PNG 和完整发布包证据。",
        "definition": "每个平台的爆款标题、正文、标签、首批互动、视频、封面、详情图、资产清单和追踪计划都完整。",
        "firstAction": "先安装 ffmpeg 和 Pillow，再对真实产品运行视频与媒体资产生成。",
    },
    "competitor_research_and_web_data": {
        "name": "竞品研究与网页数据能力",
        "whyNot100": "还需要真实产品关键词的搜索结果、公开可见竞品证据、被限制平台的人工导入证据，以及可复用的素材库。",
        "definition": "YouTube/GitHub 有公开或官方证据，知乎/小红书/抖音等限制平台有用户导入的真实链接、文本、截图 OCR 或导出文件。",
        "firstAction": "先配置 Playwright；如果要增强网页抓取，再配置 Firecrawl API Key。",
    },
    "browser_extension_and_commercial_infrastructure": {
        "name": "插件和商业化基础设施",
        "whyNot100": "本地代码和材料已具备，但 100% 需要真实 HTTPS 部署、Stripe live、数据库迁移、商店审核通过和生产监控。",
        "definition": "插件能连接生产 HTTPS 后端，License、扣量、hosted worker、Stripe webhook、隐私条款和商店审核都可用。",
        "firstAction": "先准备服务器、域名、Stripe 账号、Chrome/Edge 开发者账号，然后部署 license-service。",
    },
    "true_all_platform_auto_publish": {
        "name": "真正全自动发布",
        "whyNot100": "不是代码问题，主要受平台官方 API、授权、审核、Token、账号权限和用户明确批准限制。",
        "definition": "只对有官方 API 且已授权的平台真实发布；没有官方创作者发布 API 的平台保持手动或浏览器辅助。",
        "firstAction": "先完成 GitHub token 和 YouTube OAuth；抖音走半自动发布包并在发布后登记真实 URL。",
    },
    "creator_tasks_settlement_monetize_marketplace": {
        "name": "创作者任务、结算和 Monetize 市场",
        "whyNot100": "目前是蓝图和能力注册表，还缺真实数据库模型、任务流、证据审核、付款通道、合规和真实试点。",
        "definition": "有真实广告主活动、创作者提交、证据审核、CPS/CPE/CPM 计算、人工结算记录和合规流程。",
        "firstAction": "先做一个人工结算 MVP，不要一开始就做自动 CPS 付款。",
    },
}


ZH_TERMS = {
    "run audits and tests": "运行本地审计和测试",
    "generate playbooks and readiness matrices": "生成实操命令包和 readiness 矩阵",
    "create launch unlock packs and evidence inboxes": "生成上线解锁包和证据收集文件夹",
    "sync reviewed Skill files after explicit approval": "在你明确批准后同步已审查的 Skill 文件",
}


def main() -> None:
    args = parse_args()
    roadmap = build_report()
    checklist = build_checklist(roadmap, args)
    if args.out_dir:
        write_checklist(Path(args.out_dir), checklist)
        print(
            "Operator action checklist written to: "
            f"{(checklist_dir(Path(args.out_dir)) / 'operator-action-checklist.zh-CN.json').resolve()}"
        )
    else:
        print(json.dumps(checklist, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a Chinese operator checklist for completing every module to 100%.")
    parser.add_argument("--out-dir", default="", help="Write checklist reports under promotion-output.")
    parser.add_argument("--product-url", default="https://your-real-product-url.example")
    parser.add_argument("--github-repo", default="hqwzhu/Viral-Product-Copy-Video-Generator")
    parser.add_argument("--server-host", default="www.enhe-tech.com.cn")
    return parser.parse_args()


def build_checklist(roadmap: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    modules = [translate_module(module, args) for module in roadmap["modules"]]
    return {
        "generatedAt": roadmap["generatedAt"],
        "status": "operator_action_checklist_ready",
        "language": "zh-CN",
        "rule": "只有当前证据证明代码、运行环境、账号授权、真实输出、真实发布和真实结算均完成时，模块才算 100%。",
        "quickStart": [
            "先完成本地真实产品运行，不要先追求全平台自动发布。",
            "先生成手动发布包和证据收集模板，再处理平台授权。",
            "所有平台真实发布前必须 dry-run，并且只能走官方 API 或手动发布。",
        ],
        "modules": modules,
        "whatCodexCanSolveNow": [
            item
            for module in modules
            for item in module["codexCanDo"]
        ],
        "whatOperatorMustDo": [
            item
            for module in modules
            for item in module["operatorMustDo"]
        ],
        "openSourceReferences": roadmap["openSourceReferences"],
        "rejectedShortcuts": roadmap["summary"]["unsafeShortcutsRejected"],
        "priorityOrder": [
            "第 1 步：用真实产品 URL 跑通 Codex Skill 本地闭环。",
            "第 2 步：确认 MP4、封面、详情图和发布包都能生成。",
            "第 3 步：配置 Firecrawl 或人工导入真实竞品证据。",
            "第 4 步：部署插件 License 后端和 hosted worker。",
            "第 5 步：提交 Chrome/Edge 商店审核。",
            "第 6 步：只对官方授权完成的平台开启真实 API 发布。",
            "第 7 步：最后再做创作者任务和结算市场 MVP。",
        ],
        "copyReadyCommands": command_pack(args),
        "acceptanceRule": "如果某个验收文件、生产服务、平台审核、真实 URL、真实指标或真实结算记录不存在，就不能宣称该模块已到 100%。",
    }


def translate_module(module: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    zh = ZH_MODULES[module["id"]]
    return {
        "id": module["id"],
        "name": zh["name"],
        "currentEstimate": module["currentEstimate"],
        "whyNot100": zh["whyNot100"],
        "definitionOf100": zh["definition"],
        "firstAction": zh["firstAction"],
        "missingTo100": module["missingTo100"],
        "codexCanDo": module["codexCanDo"],
        "operatorMustDo": module["operatorMustDo"],
        "beginnerSteps": localize_steps(module["operatorSteps"], args),
        "acceptanceEvidence": module["acceptanceEvidence"],
        "externalGates": module["operatorExternalGates"],
    }


def localize_steps(steps: list[str], args: argparse.Namespace) -> list[dict[str, str]]:
    localized: list[dict[str, str]] = []
    for index, step in enumerate(steps, start=1):
        command = (
            step.replace("https://your-real-product-url.example", args.product_url)
            .replace("hqwzhu/Viral-Product-Copy-Video-Generator", args.github_repo)
            .replace("www.enhe-tech.com.cn", args.server_host)
        )
        localized.append(
            {
                "step": str(index),
                "do": explain_step(command),
                "command": command,
                "howToCheck": check_for_step(command),
            }
        )
    return localized


def explain_step(command: str) -> str:
    lower = command.lower()
    if lower.startswith("cd "):
        return "进入项目目录。PowerShell 里先执行这一步，后面的命令才会在正确目录运行。"
    if "final_capability_audit.py" in lower:
        return "检查当前本地工具、脚本、凭证和能力缺口。"
    if "skill_entry.py" in lower:
        return "用真实产品链接运行整个 Skill，生成内容、发布包、证据模板和 readiness 报告。"
    if "render_video.py" in lower:
        return "把生成的脚本渲染成平台视频草稿。"
    if "media_asset_pack.py" in lower:
        return "生成封面图、详情图，并把视频/图片路径写回发布包。"
    if "web_data_provider.py" in lower:
        return "测试 Firecrawl 或兼容网页数据服务能否抓取目标页面。"
    if "viral_evidence_inbox_setup.py" in lower:
        return "创建竞品证据收集文件夹，用于你手动放入链接、文本、导出或 OCR 结果。"
    if "viral_evidence_inbox.py" in lower:
        return "导入你放入的真实竞品证据，生成素材库和创作者榜单。"
    if "publish_readiness_runner.py" in lower:
        return "发布前 dry-run 检查，确认每个平台缺什么 Token、视频或授权。"
    if "final_capability_runner.py" in lower:
        return "在全部授权和审批满足后运行最终安全流程。"
    if "package_browser_extension.py" in lower:
        return "打包 Chrome/Edge 插件上架 ZIP。"
    if lower.startswith("$env:"):
        return "在当前 PowerShell 会话里设置环境变量。真实密钥只在你自己的机器或服务器上填写。"
    if "npm run migrate" in lower:
        return "在服务器上执行数据库迁移，创建 License 服务需要的表。"
    if lower.startswith("ssh "):
        return "连接你的服务器。把 your-server-ip 替换成真实服务器 IP。"
    return "按顺序执行或完成这一步。"


def check_for_step(command: str) -> str:
    lower = command.lower()
    if "skill_entry.py" in lower:
        return "检查 promotion-output/reports/promotion-manager/skill-entry/skill-entry.json 是否存在。"
    if "render_video.py" in lower:
        return "检查 promotion-output/videos/ 下是否生成 .mp4 文件。"
    if "media_asset_pack.py" in lower:
        return "检查 promotion-output/media-assets/ 下是否生成 PNG 文件。"
    if "web_data_provider.py" in lower:
        return "检查 promotion-output/reports/promotion-manager/web-data/ 下是否生成 JSON 报告。"
    if "viral_evidence_inbox.py" in lower:
        return "检查 viral-content-library.json 和 creator-leaderboard.json 是否生成。"
    if "publish_readiness_runner.py" in lower:
        return "检查 publish-readiness.json 中目标平台状态和 missing 字段。"
    if "package_browser_extension.py" in lower:
        return "检查 dist/ 下是否生成浏览器插件 ZIP 和打包报告。"
    if "final_capability_audit.py" in lower:
        return "检查 final-capability-audit.json 的 finalStatus 和 requirements。"
    return "执行后没有报错，并按对应模块的 acceptanceEvidence 检查文件或外部状态。"


def command_pack(args: argparse.Namespace) -> dict[str, str]:
    return {
        "进入项目": 'cd "C:\\Users\\HU\\Documents\\Viral-Product-Copy-Video-Generator"',
        "生成中文操作清单": 'python scripts\\operator_action_checklist.py --out-dir ".\\promotion-output"',
        "真实产品本地闭环": (
            f'python scripts\\skill_entry.py --link "{args.product_url}" '
            '--platforms youtube,zhihu,xiaohongshu,douyin,github --out-dir ".\\promotion-output"'
        ),
        "生成完成路线图": 'python scripts\\completion_roadmap.py --out-dir ".\\promotion-output"',
        "生成平台能力矩阵": 'python scripts\\platform_capabilities.py --out-dir ".\\promotion-output"',
        "最终能力审计": 'python scripts\\final_capability_audit.py --skip-runtime-checks --out-dir ".\\promotion-output\\verification"',
    }


def write_checklist(out_dir: Path, checklist: dict[str, Any]) -> None:
    directory = checklist_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "operator-action-checklist.zh-CN.json").write_text(
        json.dumps(checklist, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8-sig",
    )
    (directory / "operator-action-checklist.zh-CN.md").write_text(render_markdown(checklist) + "\n", encoding="utf-8-sig")


def render_markdown(checklist: dict[str, Any]) -> str:
    lines = [
        "# 100% 完成操作清单",
        "",
        f"- 生成日期：{checklist['generatedAt']}",
        f"- 状态：`{checklist['status']}`",
        f"- 规则：{checklist['rule']}",
        "",
        "## 先做什么",
    ]
    lines.extend(f"{index}. {item}" for index, item in enumerate(checklist["quickStart"], start=1))
    lines.extend(["", "## 模块总览", "", "| 模块 | 当前估算 | 为什么不是 100% | 先做什么 |", "| --- | ---: | --- | --- |"])
    for module in checklist["modules"]:
        lines.append(f"| {module['name']} | {module['currentEstimate']}% | {module['whyNot100']} | {module['firstAction']} |")
    for module in checklist["modules"]:
        lines.extend(
            [
                "",
                f"## {module['name']}",
                "",
                f"- 当前估算：{module['currentEstimate']}%",
                f"- 100% 标准：{module['definitionOf100']}",
                f"- 为什么还没到 100%：{module['whyNot100']}",
                "",
                "### 还差什么",
            ]
        )
        lines.extend(f"- {item}" for item in module["missingTo100"])
        lines.extend(["", "### Codex 可以继续解决"])
        lines.extend(f"- {item}" for item in module["codexCanDo"])
        lines.extend(["", "### 必须你来完成"])
        lines.extend(f"- {item}" for item in module["operatorMustDo"])
        lines.extend(["", "### 新手逐步执行"])
        for step in module["beginnerSteps"]:
            lines.extend(
                [
                    f"{step['step']}. {step['do']}",
                    "",
                    "```powershell",
                    step["command"],
                    "```",
                    "",
                    f"检查方式：{step['howToCheck']}",
                    "",
                ]
            )
        lines.extend(["### 验收证据"])
        lines.extend(f"- {item}" for item in module["acceptanceEvidence"])
        lines.extend(["", "### 外部门槛"])
        lines.extend(f"- {item}" for item in module["externalGates"])
    lines.extend(["", "## 可参考的开源项目"])
    for ref in checklist["openSourceReferences"]:
        lines.append(f"- [{ref['project']}]({ref['url']})：{ref['use']} 边界：{ref['boundary']}")
    lines.extend(["", "## 明确不能走的捷径"])
    lines.extend(f"- {item}" for item in checklist["rejectedShortcuts"])
    lines.extend(["", "## 推荐顺序"])
    lines.extend(f"{index}. {item}" for index, item in enumerate(checklist["priorityOrder"], start=1))
    lines.extend(["", "## 可复制命令"])
    for name, command in checklist["copyReadyCommands"].items():
        lines.extend(["", f"### {name}", "```powershell", command, "```"])
    lines.extend(["", "## 最终验收规则", "", checklist["acceptanceRule"]])
    return "\n".join(lines)


def checklist_dir(out_dir: Path) -> Path:
    return out_dir / "reports/promotion-manager/capability"


if __name__ == "__main__":
    main()
