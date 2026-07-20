const ENHE_SITE = "https://www.enhe-tech.com.cn/";
const DEFAULT_ENDPOINT = "https://www.enhe-tech.com.cn/api/promotion-manager/license";
const DEFAULT_USAGE_AUTHORIZE_ENDPOINT = "https://www.enhe-tech.com.cn/api/promotion-manager/usage/authorize";
const DEFAULT_HOSTED_RUN_ENDPOINT = "https://www.enhe-tech.com.cn/api/promotion-manager/run";
const CHECKOUT_URL = "https://www.enhe-tech.com.cn/promotion-manager/checkout";
const CUSTOMER_PORTAL_URL = "https://www.enhe-tech.com.cn/promotion-manager/billing";
const HOSTED_WORKER_ENABLED = false;

const EN_TRANSLATIONS = Object.freeze({
  appTitle: "ENHE Product Promo Maker",
  productPromise: "Turn product pages into promotional copy, video scripts, and publishing assets.",
  languageSwitchLabel: "Interface language",
  openGuide: "?",
  openGuideLabel: "Open bilingual usage guide",
  openWorkspace: "Open full workspace",
  openWorkspaceLabel: "Open the full workspace in a new tab",
  guideEyebrow: "IN-EXTENSION GUIDE",
  guideTitle: "Product Promo Maker guide",
  guideIntro: "A bilingual reference for planning, evidence, and safe publishing.",
  guideBack: "Back to generator",
  guideTabsLabel: "Guide sections",
  guideFeaturesTab: "Features",
  guideUsageTab: "How to use",
  guideSubscriptionTab: "Subscription",
  guideFeaturesIntro: "Map each promotion step to a clear outcome and a safe handoff.",
  guideUsageIntro: "Use the popup as a controlled starting point, then review every external action.",
  guideSubscriptionIntro: "Choose a plan by monthly evidence-backed runs. Hosted Worker stays off in this extension.",
  guideWhat: "What",
  guideProblem: "Problem solved",
  guideBenefit: "Benefit",
  guideUseCase: "Use case",
  guideFeatureWeb: "Product web entry",
  guideFeatureCopy: "Copy and script",
  guideFeatureEvidence: "Platform evidence",
  guideFeatureMedia: "Image and video prep",
  guideFeaturePublish: "Publishing prep",
  guideFeatureReview: "Real-data review",
  guideFeatureOptimize: "Next-round optimization",
  guideFeatureAutomation: "Automation",
  guideFeatureAdvanced: "Advanced safeguards",
  guideFeatureWebWhat: "Start from one product or website URL.",
  guideFeatureWebProblem: "Scattered product context causes inconsistent promotion briefs.",
  guideFeatureWebBenefit: "Keeps the source page attached to every downstream asset.",
  guideFeatureWebUseCase: "Paste a product page before generating a first campaign command.",
  guideFeatureCopyWhat: "Create promotion copy and video script directions.",
  guideFeatureCopyProblem: "Ideas drift when hooks, proof, and calls to action are written separately.",
  guideFeatureCopyBenefit: "Turns one brief into a reviewable, repeatable message system.",
  guideFeatureCopyUseCase: "Use the research-and-copy depth for an early positioning pass.",
  guideFeatureEvidenceWhat: "Collect platform examples and audience signals.",
  guideFeatureEvidenceProblem: "Unverified trends make claims brittle and hard to audit.",
  guideFeatureEvidenceBenefit: "Separates observed evidence from assumptions before publishing.",
  guideFeatureEvidenceUseCase: "Capture search, detail, or creator evidence for a target platform.",
  guideFeatureMediaWhat: "Prepare image, video, and asset checklists.",
  guideFeatureMediaProblem: "Missing dimensions or source files delay final production.",
  guideFeatureMediaBenefit: "Makes every handoff explicit before a render or upload.",
  guideFeatureMediaUseCase: "Run the full promotion loop when media needs to be staged together.",
  guideFeaturePublishWhat: "Build a publish queue and browser handoff.",
  guideFeaturePublishProblem: "Publishing fails when credentials, fields, and approvals are implicit.",
  guideFeaturePublishBenefit: "Leaves a visible queue while keeping final clicks human-controlled.",
  guideFeaturePublishUseCase: "Prepare a browser publish session after the queue is reviewed.",
  guideFeatureReviewWhat: "Record real post-publish metrics and comments.",
  guideFeatureReviewProblem: "Without actual outcomes, the next brief repeats guesses.",
  guideFeatureReviewBenefit: "Creates a feedback loop grounded in audience response.",
  guideFeatureReviewUseCase: "Return with views, saves, comments, or conversions after a post runs.",
  guideFeatureOptimizeWhat: "Turn review findings into the next experiment.",
  guideFeatureOptimizeProblem: "Lessons disappear when they are not attached to a concrete change.",
  guideFeatureOptimizeBenefit: "Keeps iteration focused on one measurable improvement at a time.",
  guideFeatureOptimizeUseCase: "Compare hooks or platform choices in the next promotion cycle.",
  guideFeatureAutomationWhat: "Schedule repeatable local workflows.",
  guideFeatureAutomationProblem: "Manual repetition hides stale evidence and missed follow-ups.",
  guideFeatureAutomationBenefit: "Runs checklists on a cadence without silently publishing.",
  guideFeatureAutomationUseCase: "Create a weekly local job after the first cycle is stable.",
  guideFeatureAdvancedBody: "Advanced options can collect richer evidence or prepare browser fields, but credentials, CAPTCHA, risk controls, and final publishing always require a person.",
  guideUsageStep1: "1. Quick start: paste a product URL, choose platforms, and select workflow depth.",
  guideUsageStep2: "2. Local Skill execution: generate the command and run it from the repository root.",
  guideUsageStep3: "3. Evidence boundary: label observed sources, assumptions, and missing data before using a claim.",
  guideUsageStep4: "4. Review and publish: inspect assets, handle CAPTCHA or risk checks manually, then confirm the final publish action.",
  guideUsageSkill: "The extension prepares a command; it does not replace your local Skill runtime.",
  guideUsageEvidence: "Treat platform evidence as time-bound observations, not universal truth.",
  guideUsageCaptcha: "CAPTCHA, account challenges, policy warnings, and other risk controls must be handled manually.",
  guideUsageConfirm: "No final platform publish should happen without your explicit confirmation.",
  guidePlanCredits: "{credits} credits",
  guidePlanPrice: "¥{price}/30 days",
  guidePlanFree: "Free",
  guidePlanStarter: "Starter",
  guidePlanGrowth: "Growth",
  guidePlanScale: "Scale",
  guidePlanAudienceLabel: "Audience fit",
  guidePlanIncludedLabel: "Included usage",
  guidePlanFreeAudience: "Individuals evaluating the workflow before adopting a paid plan.",
  guidePlanFreeIncluded: "Includes {credits} ENHE hosted credits for evaluating future hosted capabilities; Hosted Worker is disabled here and local Skill runs are separate.",
  guidePlanStarterAudience: "Solo creators running occasional product campaigns.",
  guidePlanStarterIncluded: "Includes {credits} ENHE hosted credits for light future hosted usage; Hosted Worker is disabled here and local Skill runs do not consume them.",
  guidePlanGrowthAudience: "Active creators or small teams running recurring campaigns.",
  guidePlanGrowthIncluded: "Includes {credits} ENHE hosted credits for recurring future hosted workflows; Hosted Worker is disabled here and local Skill runs do not consume them.",
  guidePlanScaleAudience: "Teams managing frequent campaigns across products or platforms.",
  guidePlanScaleIncluded: "Includes {credits} ENHE hosted credits for future high-volume hosted operations; Hosted Worker is disabled here and local Skill runs do not consume them.",
  guideBillingLinks: "Manage billing on the ENHE website:",
  guideCheckout: "Checkout",
  guideBillingPortal: "Billing portal",
  guideHostedWorker: "Hosted Worker is off; local runs and human confirmation remain the default.",
  workspacePlaceholder: "Full workspace opens in a new tab in the next release.",
  productUrlLabel: "Product or website URL",
  useCurrentTab: "Use current tab",
  generateCommand: "Generate command",
  tabPrompt: "Open a product page, then capture the current tab.",
  platformsTitle: "Platforms",
  platformYouTube: "YouTube",
  platformZhihu: "Zhihu",
  platformXiaohongshu: "Xiaohongshu",
  platformDouyin: "Douyin",
  platformGitHub: "GitHub",
  selectAll: "All",
  workflowDepthLabel: "Workflow depth",
  workflowFull: "Full promotion loop",
  workflowResearch: "Research and copy",
  workflowPlaybook: "Playbook only",
  commandTypeLabel: "Command type",
  commandSkillEntry: "One-link Skill run",
  commandPublishSession: "Browser publish session",
  commandLaunchUnlock: "Launch unlock pack",
  commandViralEvidenceSetup: "Viral evidence setup",
  commandViralEvidenceInbox: "Viral evidence inbox",
  commandEvidenceSetup: "Evidence inbox setup",
  commandEvidenceInbox: "Real evidence inbox",
  commandPerformanceMonitor: "Performance monitor",
  commandPlatformData: "Local platform evidence",
  commandReadiness: "Final readiness audit",
  commandScheduleInit: "Schedule init",
  commandScheduledRun: "Run scheduled jobs",
  commandWindowsTask: "Windows task script",
  workflowPathsTitle: "Workflow paths",
  outputDirectoryLabel: "Output directory",
  localEvidencePlatformLabel: "Local evidence platform",
  collectionModeLabel: "Collection mode",
  collectionSearch: "Keyword search",
  collectionDetail: "Content detail",
  collectionCreator: "Creator works",
  targetLabel: "Keyword or target URL/ID",
  targetPlaceholder: "AI tools or a content/creator URL",
  publishQueueLabel: "Publish queue JSON",
  publisherOverridesLabel: "Publisher URL overrides",
  publisherOverridesPlaceholder: "xiaohongshu=https://creator.xiaohongshu.com/",
  evidenceInboxFolderLabel: "Evidence inbox folder",
  automationConfigLabel: "Automation config",
  automationOutputRootLabel: "Automation output root",
  jobIdLabel: "Job ID",
  intervalDaysLabel: "Interval days",
  windowsTaskScriptLabel: "Windows task script",
  windowsTaskTimeLabel: "Windows task time",
  includeSubComments: "Include second-level comments",
  fillPublisherFields: "Fill visible publisher fields",
  useBrowserCapture: "Use browser-visible capture",
  allowLocalhost: "Allow localhost test URLs",
  autoSearchCompetitors: "Auto search competitors",
  multiQueryDiscovery: "Multi-query viral discovery",
  browserFollowUps: "Browser-assisted follow-ups",
  enablePublishQueue: "Enable publish queue",
  enablePublishAssistant: "Enable browser publish assistant",
  enableBrowserFormFill: "Enable browser form fill",
  enableMetricsRecovery: "Enable metrics recovery",
  enableNextRound: "Enable next-round optimization",
  alsoWindowsTask: "Also generate Windows task script",
  subscriptionEstimateTitle: "Subscription estimate",
  planLabel: "Plan",
  planFree: "Free",
  monthlyRunsLabel: "Monthly runs",
  deepStrategyReview: "Deep strategy review",
  hostedVideoAddon: "Hosted MP4 add-on",
  costSummaryPrompt: "Estimated hosted cost appears here.",
  licenseKeyLabel: "License key",
  licenseKeyPlaceholder: "Paste ENHE license key",
  licenseEndpointLabel: "License endpoint",
  usageEndpointLabel: "Usage authorization endpoint",
  hostedRunEndpointLabel: "Hosted run endpoint (off)",
  saveButton: "Save",
  validateButton: "Validate",
  reserveCreditsButton: "Reserve credits (off)",
  copyHostedPayloadButton: "Copy hosted payload (off)",
  startHostedRunButton: "Hosted Worker off",
  openCheckoutButton: "Open checkout",
  billingPortalButton: "Billing portal",
  licenseMessagePrompt: "Use ENHE website billing for production licenses.",
  usageMessagePrompt: "Reserve hosted credits only before a hosted ENHE run.",
  hostedRunMessagePrompt: "Hosted runs require a backend quota check and never click final platform publish.",
  hostedWorkerOffMessage: "Hosted Worker is currently off. Local Skill runs remain available.",
  codexCommandTitle: "Codex command",
  copyButton: "Copy",
  commandHint: "Run this from the repository root. Publishing still requires credentials and approval.",
  productPageLink: "Product page",
  statusLocal: "Local",
  statusActive: "Active",
  statusInactive: "Inactive",
  statusOffline: "Offline",
  noActiveTab: "No active tab found.",
  currentTab: "Current tab: {title}",
  currentTabCaptured: "Current tab captured.",
  enterSearchKeyword: "Enter a search keyword first.",
  enterContentTarget: "Enter a content or creator URL/ID first.",
  enterProductUrl: "Enter a product or website URL first.",
  selectPlatform: "Select at least one platform.",
  enterPublishQueue: "Enter a publish-queue.json path first.",
  enterEvidenceInbox: "Enter an evidence inbox folder first.",
  generateFirst: "Generate a command first.",
  copied: "Copied",
  licenseSaved: "License settings saved locally.",
  pasteKeyForCredits: "Paste a license key before reserving hosted credits.",
  noHostedCredits: "This command type does not need hosted credits.",
  requestingUsage: "Requesting usage authorization...",
  usageBlocked: "Usage blocked: {reason}.",
  creditsReserved: "Reserved {reserved} credits. Remaining: {remaining}.",
  usageUnavailable: "Usage API not reachable. Run locally or manage billing on ENHE website. {error}",
  pasteKeyForValidation: "Paste a license key before validation.",
  checkingLicense: "Checking license endpoint...",
  licensePlanStatus: "Plan {plan}, credits {credits}.",
  licenseInactive: "License is not active.",
  licenseUnavailable: "License API not reachable. Manage billing on ENHE website. {error}",
  hostedPayloadCopied: "Hosted run payload copied.",
  pasteKeyForHosted: "Paste a license key before creating a hosted run payload.",
  reserveBeforeHosted: "Reserve credits before starting a hosted run.",
  submittingHosted: "Submitting hosted run request...",
  hostedAccepted: "Hosted run {status}{runId}{statusLink}.",
  hostedUnavailable: "Hosted run API not reachable. Copy the payload or run locally. {error}",
  acceptedStatus: "accepted",
  unknownValue: "unknown",
  creditsCount: "{credits} credits",
  hostedEstimateReference: "Reference only — Hosted Worker off. {plan} includes {included} hosted credits; this setup plans {planned} credits for {workflow}. Local Skill runs do not consume hosted credits.",
  costSummary: "{plan} includes {included} credits at CNY {price}/30 days. {workflow}: {perRun} credits/run, {planned} credits planned, estimated gross cost up to USD {cost}.",
  costOverage: " Add prepaid credits or reduce automation depth.",
  labelWorkflow: "Workflow",
  labelSkillRun: "Skill run",
  labelPublishSession: "Publish session",
  labelLaunchUnlock: "Launch unlock pack",
  labelViralEvidenceSetup: "Viral evidence setup",
  labelViralEvidenceInbox: "Viral evidence inbox",
  labelEvidenceSetup: "Evidence inbox setup",
  labelEvidenceInbox: "Evidence inbox",
  labelPerformanceMonitor: "Performance monitor",
  labelPlatformEvidence: "Local platform evidence",
  labelReadinessAudit: "Readiness audit",
  labelScheduleInit: "Schedule init",
  labelScheduledRun: "Scheduled run",
  labelWindowsTask: "Windows task",
  labelPlaybookCommand: "Playbook command",
  labelResearchRun: "Research run",
  labelFullSkillRun: "Full Skill run"
});

const ZH_TRANSLATIONS = Object.freeze({
  appTitle: "ENHE 产品推广素材生成器",
  productPromise: "把产品网页变成推广文案、视频脚本和发布素材",
  languageSwitchLabel: "界面语言",
  openGuide: "?",
  openGuideLabel: "打开双语使用说明",
  openWorkspace: "打开完整工作台",
  openWorkspaceLabel: "在新标签页打开完整工作台",
  guideEyebrow: "插件内使用说明",
  guideTitle: "产品推广素材生成器说明",
  guideIntro: "用于规划、证据和安全发布的双语参考。",
  guideBack: "返回生成器",
  guideTabsLabel: "说明章节",
  guideFeaturesTab: "功能",
  guideUsageTab: "如何使用",
  guideSubscriptionTab: "订阅",
  guideFeaturesIntro: "把每个推广步骤对应到清晰结果和安全交接。",
  guideUsageIntro: "把弹窗作为受控起点，然后复核每个外部操作。",
  guideSubscriptionIntro: "按每月有证据支持的运行次数选择套餐。本插件保持 Hosted Worker 关闭。",
  guideWhat: "功能",
  guideProblem: "解决的问题",
  guideBenefit: "收益",
  guideUseCase: "使用场景",
  guideFeatureWeb: "产品网页入口",
  guideFeatureCopy: "文案与脚本",
  guideFeatureEvidence: "平台证据",
  guideFeatureMedia: "图片与视频准备",
  guideFeaturePublish: "发布准备",
  guideFeatureReview: "真实数据复盘",
  guideFeatureOptimize: "下一轮优化",
  guideFeatureAutomation: "自动化",
  guideFeatureAdvanced: "高级安全边界",
  guideFeatureWebWhat: "从一个产品或网站链接开始。",
  guideFeatureWebProblem: "产品上下文分散会导致推广简报前后不一致。",
  guideFeatureWebBenefit: "让源页面跟随每个后续素材。",
  guideFeatureWebUseCase: "生成第一条活动命令前先粘贴产品页面。",
  guideFeatureCopyWhat: "创建推广文案和视频脚本方向。",
  guideFeatureCopyProblem: "钩子、证据和行动号召分开书写时容易跑题。",
  guideFeatureCopyBenefit: "把一份简报变成可复核、可重复的消息体系。",
  guideFeatureCopyUseCase: "早期定位时选择“调研与文案”深度。",
  guideFeatureEvidenceWhat: "收集平台案例和受众信号。",
  guideFeatureEvidenceProblem: "未经核验的趋势让观点脆弱且难以审计。",
  guideFeatureEvidenceBenefit: "发布前区分观察到的证据和推测。",
  guideFeatureEvidenceUseCase: "为目标平台采集搜索、详情或创作者证据。",
  guideFeatureMediaWhat: "准备图片、视频和素材清单。",
  guideFeatureMediaProblem: "缺少尺寸或源文件会拖延最终制作。",
  guideFeatureMediaBenefit: "渲染或上传前明确每次交接。",
  guideFeatureMediaUseCase: "需要一起准备素材时运行完整推广闭环。",
  guideFeaturePublishWhat: "建立发布队列和浏览器交接。",
  guideFeaturePublishProblem: "凭据、字段和批准不明确会造成发布失败。",
  guideFeaturePublishBenefit: "保留可见队列，同时让最终点击由人控制。",
  guideFeaturePublishUseCase: "复核队列后准备浏览器发布会话。",
  guideFeatureReviewWhat: "记录发布后的真实指标和评论。",
  guideFeatureReviewProblem: "没有实际结果，下一份简报仍会重复猜测。",
  guideFeatureReviewBenefit: "用受众反馈建立反馈闭环。",
  guideFeatureReviewUseCase: "发布后带回播放、收藏、评论或转化数据。",
  guideFeatureOptimizeWhat: "把复盘发现转成下一次实验。",
  guideFeatureOptimizeProblem: "经验不落到具体改变就会消失。",
  guideFeatureOptimizeBenefit: "每次迭代聚焦一个可衡量的改进。",
  guideFeatureOptimizeUseCase: "在下一轮推广中比较钩子或平台选择。",
  guideFeatureAutomationWhat: "安排可重复的本地工作流。",
  guideFeatureAutomationProblem: "手工重复会掩盖过期证据和遗漏的跟进。",
  guideFeatureAutomationBenefit: "按节奏运行清单，但不会悄悄发布。",
  guideFeatureAutomationUseCase: "首轮稳定后创建每周本地任务。",
  guideFeatureAdvancedBody: "高级选项可以采集更丰富的证据或准备浏览器字段，但凭据、验证码、风险控制和最终发布始终需要人工处理。",
  guideUsageStep1: "1. 快速开始：粘贴产品链接，选择平台和工作流深度。",
  guideUsageStep2: "2. 本地 Skill 执行：生成命令，并在仓库根目录运行。",
  guideUsageStep3: "3. 证据边界：使用观点前标注已观察来源、假设和缺失数据。",
  guideUsageStep4: "4. 复核并发布：检查素材，人工处理验证码或风险检查，然后确认最终发布。",
  guideUsageSkill: "插件负责准备命令，不替代本地 Skill 运行环境。",
  guideUsageEvidence: "平台证据是有时效的观察，不是普遍真理。",
  guideUsageCaptcha: "验证码、账号挑战、政策警告及其他风险控制必须人工处理。",
  guideUsageConfirm: "没有你的明确确认，不应执行平台最终发布。",
  guidePlanCredits: "{credits} 点",
  guidePlanPrice: "¥{price}/30 天",
  guidePlanFree: "免费版",
  guidePlanStarter: "入门版",
  guidePlanGrowth: "成长版",
  guidePlanScale: "规模版",
  guidePlanAudienceLabel: "适合人群",
  guidePlanIncludedLabel: "包含用量",
  guidePlanFreeAudience: "准备先体验工作流、再决定是否付费的个人用户。",
  guidePlanFreeIncluded: "包含 {credits} 点 ENHE 托管额度，用于评估未来托管能力；本版 Hosted Worker 已关闭，本地 Skill 运行与额度分开。",
  guidePlanStarterAudience: "偶尔开展产品推广的独立创作者。",
  guidePlanStarterIncluded: "包含 {credits} 点 ENHE 托管额度，用于未来轻量托管需求；本版 Hosted Worker 已关闭，本地 Skill 不消耗这些额度。",
  guidePlanGrowthAudience: "持续开展推广的活跃创作者或小型团队。",
  guidePlanGrowthIncluded: "包含 {credits} 点 ENHE 托管额度，用于未来持续托管工作流；本版 Hosted Worker 已关闭，本地 Skill 不消耗这些额度。",
  guidePlanScaleAudience: "需要跨产品或跨平台高频推广的团队。",
  guidePlanScaleIncluded: "包含 {credits} 点 ENHE 托管额度，用于未来高频托管操作；本版 Hosted Worker 已关闭，本地 Skill 不消耗这些额度。",
  guideBillingLinks: "请在 ENHE 网站管理账单：",
  guideCheckout: "结算页",
  guideBillingPortal: "账单中心",
  guideHostedWorker: "Hosted Worker 保持关闭；默认使用本地运行并由人工确认。",
  workspacePlaceholder: "完整工作台将在下一版本于新标签页打开。",
  productUrlLabel: "产品或网站链接",
  useCurrentTab: "使用当前标签页",
  generateCommand: "生成命令",
  tabPrompt: "打开产品页面，然后获取当前标签页。",
  platformsTitle: "平台",
  platformYouTube: "YouTube",
  platformZhihu: "知乎",
  platformXiaohongshu: "小红书",
  platformDouyin: "抖音",
  platformGitHub: "GitHub",
  selectAll: "全部",
  workflowDepthLabel: "工作流深度",
  workflowFull: "完整推广闭环",
  workflowResearch: "调研与文案",
  workflowPlaybook: "仅生成执行手册",
  commandTypeLabel: "命令类型",
  commandSkillEntry: "一键 Skill 执行",
  commandPublishSession: "浏览器发布会话",
  commandLaunchUnlock: "发布解锁包",
  commandViralEvidenceSetup: "爆款证据初始化",
  commandViralEvidenceInbox: "爆款证据收件箱",
  commandEvidenceSetup: "证据收件箱初始化",
  commandEvidenceInbox: "真实证据收件箱",
  commandPerformanceMonitor: "效果监控",
  commandPlatformData: "本地平台证据",
  commandReadiness: "最终就绪审计",
  commandScheduleInit: "定时任务初始化",
  commandScheduledRun: "运行定时任务",
  commandWindowsTask: "Windows 任务脚本",
  workflowPathsTitle: "工作流路径",
  outputDirectoryLabel: "输出目录",
  localEvidencePlatformLabel: "本地证据平台",
  collectionModeLabel: "采集模式",
  collectionSearch: "关键词搜索",
  collectionDetail: "内容详情",
  collectionCreator: "创作者作品",
  targetLabel: "关键词或目标链接/ID",
  targetPlaceholder: "AI 工具或内容/创作者链接",
  publishQueueLabel: "发布队列 JSON",
  publisherOverridesLabel: "发布平台链接覆盖",
  publisherOverridesPlaceholder: "xiaohongshu=https://creator.xiaohongshu.com/",
  evidenceInboxFolderLabel: "证据收件箱目录",
  automationConfigLabel: "自动化配置",
  automationOutputRootLabel: "自动化输出根目录",
  jobIdLabel: "任务 ID",
  intervalDaysLabel: "间隔天数",
  windowsTaskScriptLabel: "Windows 任务脚本",
  windowsTaskTimeLabel: "Windows 任务时间",
  includeSubComments: "包含二级评论",
  fillPublisherFields: "填写可见发布字段",
  useBrowserCapture: "使用浏览器可见采集",
  allowLocalhost: "允许本机测试链接",
  autoSearchCompetitors: "自动搜索竞品",
  multiQueryDiscovery: "多关键词爆款发现",
  browserFollowUps: "浏览器辅助补采",
  enablePublishQueue: "启用发布队列",
  enablePublishAssistant: "启用浏览器发布助手",
  enableBrowserFormFill: "启用浏览器表单填写",
  enableMetricsRecovery: "启用指标补采",
  enableNextRound: "启用下一轮优化",
  alsoWindowsTask: "同时生成 Windows 任务脚本",
  subscriptionEstimateTitle: "订阅用量估算",
  planLabel: "套餐",
  planFree: "免费版",
  monthlyRunsLabel: "每月运行次数",
  deepStrategyReview: "深度策略复核",
  hostedVideoAddon: "托管 MP4 附加项",
  costSummaryPrompt: "托管费用估算将显示在这里。",
  licenseKeyLabel: "许可证密钥",
  licenseKeyPlaceholder: "粘贴 ENHE 许可证密钥",
  licenseEndpointLabel: "许可证接口",
  usageEndpointLabel: "用量授权接口",
  hostedRunEndpointLabel: "托管运行接口（已关闭）",
  saveButton: "保存",
  validateButton: "验证",
  reserveCreditsButton: "预留点数（已关闭）",
  copyHostedPayloadButton: "复制托管请求（已关闭）",
  startHostedRunButton: "Hosted Worker 已关闭",
  openCheckoutButton: "打开结算页",
  billingPortalButton: "账单中心",
  licenseMessagePrompt: "正式许可证请通过 ENHE 网站购买和管理。",
  usageMessagePrompt: "仅在启动 ENHE 托管任务前预留点数。",
  hostedRunMessagePrompt: "托管任务需经后端额度校验，且不会点击平台的最终发布按钮。",
  hostedWorkerOffMessage: "Hosted Worker 当前关闭，本地 Skill 可继续使用。",
  codexCommandTitle: "Codex 命令",
  copyButton: "复制",
  commandHint: "请在仓库根目录运行。正式发布仍需要凭据和人工批准。",
  productPageLink: "产品页面",
  statusLocal: "本地",
  statusActive: "已激活",
  statusInactive: "未激活",
  statusOffline: "离线",
  noActiveTab: "未找到活动标签页。",
  currentTab: "当前标签页：{title}",
  currentTabCaptured: "已获取当前标签页。",
  enterSearchKeyword: "请先输入搜索关键词。",
  enterContentTarget: "请先输入内容或创作者链接/ID。",
  enterProductUrl: "请先输入产品或网站链接。",
  selectPlatform: "请至少选择一个平台。",
  enterPublishQueue: "请先输入 publish-queue.json 路径。",
  enterEvidenceInbox: "请先输入证据收件箱目录。",
  generateFirst: "请先生成命令。",
  copied: "已复制",
  licenseSaved: "许可证设置已保存在本机。",
  pasteKeyForCredits: "预留托管点数前，请先粘贴许可证密钥。",
  noHostedCredits: "此命令类型不需要托管点数。",
  requestingUsage: "正在请求用量授权……",
  usageBlocked: "用量请求被拒绝：{reason}。",
  creditsReserved: "已预留 {reserved} 点，剩余 {remaining} 点。",
  usageUnavailable: "无法连接用量接口。请在本机运行或前往 ENHE 网站管理账单。{error}",
  pasteKeyForValidation: "验证前请先粘贴许可证密钥。",
  checkingLicense: "正在检查许可证接口……",
  licensePlanStatus: "套餐 {plan}，剩余点数 {credits}。",
  licenseInactive: "许可证未激活。",
  licenseUnavailable: "无法连接许可证接口。请前往 ENHE 网站管理账单。{error}",
  hostedPayloadCopied: "已复制托管运行请求。",
  pasteKeyForHosted: "创建托管运行请求前，请先粘贴许可证密钥。",
  reserveBeforeHosted: "启动托管运行前请先预留点数。",
  submittingHosted: "正在提交托管运行请求……",
  hostedAccepted: "托管任务{status}{runId}{statusLink}。",
  hostedUnavailable: "无法连接托管运行接口。请复制请求或在本机运行。{error}",
  acceptedStatus: "已受理",
  unknownValue: "未知",
  creditsCount: "{credits} 点",
  hostedEstimateReference: "仅供未来参考——Hosted Worker 当前关闭。{plan} 套餐包含 {included} 点托管额度，当前设置为 {workflow}、计划使用 {planned} 点。本地 Skill 不消耗托管点数。",
  costSummary: "{plan} 包含 {included} 点，价格为 ¥{price}/30 天。{workflow}：每次 {perRun} 点，计划使用 {planned} 点，预计最高成本约 USD {cost}。",
  costOverage: " 请购买预付点数或降低自动化深度。",
  labelWorkflow: "工作流",
  labelSkillRun: "Skill 执行",
  labelPublishSession: "发布会话",
  labelLaunchUnlock: "发布解锁包",
  labelViralEvidenceSetup: "爆款证据初始化",
  labelViralEvidenceInbox: "爆款证据收件箱",
  labelEvidenceSetup: "证据收件箱初始化",
  labelEvidenceInbox: "证据收件箱",
  labelPerformanceMonitor: "效果监控",
  labelPlatformEvidence: "本地平台证据",
  labelReadinessAudit: "就绪审计",
  labelScheduleInit: "定时任务初始化",
  labelScheduledRun: "定时运行",
  labelWindowsTask: "Windows 任务",
  labelPlaybookCommand: "执行手册命令",
  labelResearchRun: "调研任务",
  labelFullSkillRun: "完整 Skill 执行"
});

const TRANSLATIONS = Object.freeze({ en: EN_TRANSLATIONS, "zh-CN": ZH_TRANSLATIONS });
let currentLanguage = "en";
const messageState = new Map();
let commandMessage = null;
let licenseStatusState = { key: "statusLocal", className: "" };

const PLANS = {
  free: { label: "Free", credits: 5, priceCny: 0 },
  starter: { label: "Starter", credits: 60, priceCny: 19 },
  growth: { label: "Growth", credits: 220, priceCny: 59 },
  scale: { label: "Scale", credits: 800, priceCny: 199 }
};

const GUIDE_FEATURES = [
  ["guideFeatureWeb", "guideFeatureWebWhat", "guideFeatureWebProblem", "guideFeatureWebBenefit", "guideFeatureWebUseCase"],
  ["guideFeatureCopy", "guideFeatureCopyWhat", "guideFeatureCopyProblem", "guideFeatureCopyBenefit", "guideFeatureCopyUseCase"],
  ["guideFeatureEvidence", "guideFeatureEvidenceWhat", "guideFeatureEvidenceProblem", "guideFeatureEvidenceBenefit", "guideFeatureEvidenceUseCase"],
  ["guideFeatureMedia", "guideFeatureMediaWhat", "guideFeatureMediaProblem", "guideFeatureMediaBenefit", "guideFeatureMediaUseCase"],
  ["guideFeaturePublish", "guideFeaturePublishWhat", "guideFeaturePublishProblem", "guideFeaturePublishBenefit", "guideFeaturePublishUseCase"],
  ["guideFeatureReview", "guideFeatureReviewWhat", "guideFeatureReviewProblem", "guideFeatureReviewBenefit", "guideFeatureReviewUseCase"],
  ["guideFeatureOptimize", "guideFeatureOptimizeWhat", "guideFeatureOptimizeProblem", "guideFeatureOptimizeBenefit", "guideFeatureOptimizeUseCase"],
  ["guideFeatureAutomation", "guideFeatureAutomationWhat", "guideFeatureAutomationProblem", "guideFeatureAutomationBenefit", "guideFeatureAutomationUseCase"]
];

const GUIDE_PLAN_DETAILS = Object.freeze({
  free: { label: "guidePlanFree", audience: "guidePlanFreeAudience", included: "guidePlanFreeIncluded" },
  starter: { label: "guidePlanStarter", audience: "guidePlanStarterAudience", included: "guidePlanStarterIncluded" },
  growth: { label: "guidePlanGrowth", audience: "guidePlanGrowthAudience", included: "guidePlanGrowthIncluded" },
  scale: { label: "guidePlanScale", audience: "guidePlanScaleAudience", included: "guidePlanScaleIncluded" }
});

const COST_PER_CREDIT = 0.35;

const COMMAND_LABELS = {
  skill_entry: "labelSkillRun",
  browser_publish_session: "labelPublishSession",
  launch_unlock_pack: "labelLaunchUnlock",
  viral_evidence_inbox_setup: "labelViralEvidenceSetup",
  viral_evidence_inbox: "labelViralEvidenceInbox",
  real_evidence_inbox_setup: "labelEvidenceSetup",
  real_evidence_inbox: "labelEvidenceInbox",
  performance_monitor: "labelPerformanceMonitor",
  platform_data_collect: "labelPlatformEvidence",
  final_readiness: "labelReadinessAudit",
  automation_init: "labelScheduleInit",
  automation_run: "labelScheduledRun",
  automation_windows_task: "labelWindowsTask"
};

const WORKSPACE_DRAFT_KEY = "enhePromotionManagerWorkspaceDraft";
const WORKSPACE_DRAFT_VALUE_IDS = Object.freeze([
  "productUrl",
  "workflowDepth",
  "commandType",
  "outDir",
  "platformDataPlatform",
  "platformDataMode",
  "platformDataTarget",
  "publishQueue",
  "platformPublishUrls",
  "evidenceInbox",
  "automationConfig",
  "automationOutputRoot",
  "automationJobId",
  "automationIntervalDays",
  "windowsTaskScript",
  "windowsTaskTime",
  "plan",
  "monthlyRuns"
]);
const WORKSPACE_DRAFT_CHECKBOX_IDS = Object.freeze([
  "platformDataSubComments",
  "runFormFill",
  "captureBrowserEvidence",
  "allowLocalhost",
  "autoSearchCompetitors",
  "enableMultiQueryDiscovery",
  "browserFollowUps",
  "enablePublishQueue",
  "enableBrowserPublishAssistant",
  "enableBrowserFormFill",
  "enableMetricsRecovery",
  "enableNextRoundOptimization",
  "alsoWindowsTask",
  "deepReview",
  "hostedVideo"
]);

const els = {
  languageZh: document.getElementById("languageZh"),
  languageEn: document.getElementById("languageEn"),
  openGuide: document.getElementById("openGuide"),
  openWorkspace: document.getElementById("openWorkspace"),
  mainView: document.getElementById("mainView"),
  guideView: document.getElementById("guideView"),
  guideBack: document.getElementById("guideBack"),
  guideTabs: document.getElementById("guideTabs"),
  guideFeatures: document.getElementById("guideFeatures"),
  guideUsage: document.getElementById("guideUsage"),
  guideSubscription: document.getElementById("guideSubscription"),
  guideFeatureList: document.getElementById("guideFeatureList"),
  guideUsageList: document.getElementById("guideUsageList"),
  guidePlans: document.getElementById("guidePlans"),
  licenseStatus: document.getElementById("licenseStatus"),
  productUrl: document.getElementById("productUrl"),
  tabTitle: document.getElementById("tabTitle"),
  useTab: document.getElementById("useTab"),
  generate: document.getElementById("generate"),
  selectAll: document.getElementById("selectAll"),
  workflowDepth: document.getElementById("workflowDepth"),
  commandType: document.getElementById("commandType"),
  commandModeLabel: document.getElementById("commandModeLabel"),
  outDir: document.getElementById("outDir"),
  platformDataPlatform: document.getElementById("platformDataPlatform"),
  platformDataMode: document.getElementById("platformDataMode"),
  platformDataTarget: document.getElementById("platformDataTarget"),
  platformDataSubComments: document.getElementById("platformDataSubComments"),
  publishQueue: document.getElementById("publishQueue"),
  platformPublishUrls: document.getElementById("platformPublishUrls"),
  evidenceInbox: document.getElementById("evidenceInbox"),
  automationConfig: document.getElementById("automationConfig"),
  automationOutputRoot: document.getElementById("automationOutputRoot"),
  automationJobId: document.getElementById("automationJobId"),
  automationIntervalDays: document.getElementById("automationIntervalDays"),
  windowsTaskScript: document.getElementById("windowsTaskScript"),
  windowsTaskTime: document.getElementById("windowsTaskTime"),
  runFormFill: document.getElementById("runFormFill"),
  captureBrowserEvidence: document.getElementById("captureBrowserEvidence"),
  allowLocalhost: document.getElementById("allowLocalhost"),
  autoSearchCompetitors: document.getElementById("autoSearchCompetitors"),
  enableMultiQueryDiscovery: document.getElementById("enableMultiQueryDiscovery"),
  browserFollowUps: document.getElementById("browserFollowUps"),
  enablePublishQueue: document.getElementById("enablePublishQueue"),
  enableBrowserPublishAssistant: document.getElementById("enableBrowserPublishAssistant"),
  enableBrowserFormFill: document.getElementById("enableBrowserFormFill"),
  enableMetricsRecovery: document.getElementById("enableMetricsRecovery"),
  enableNextRoundOptimization: document.getElementById("enableNextRoundOptimization"),
  alsoWindowsTask: document.getElementById("alsoWindowsTask"),
  plan: document.getElementById("plan"),
  monthlyRuns: document.getElementById("monthlyRuns"),
  deepReview: document.getElementById("deepReview"),
  hostedVideo: document.getElementById("hostedVideo"),
  creditMeter: document.getElementById("creditMeter"),
  costSummary: document.getElementById("costSummary"),
  licenseKey: document.getElementById("licenseKey"),
  licenseEndpoint: document.getElementById("licenseEndpoint"),
  usageAuthorizeEndpoint: document.getElementById("usageAuthorizeEndpoint"),
  hostedRunEndpoint: document.getElementById("hostedRunEndpoint"),
  saveLicense: document.getElementById("saveLicense"),
  validateLicense: document.getElementById("validateLicense"),
  authorizeUsage: document.getElementById("authorizeUsage"),
  copyHostedPayload: document.getElementById("copyHostedPayload"),
  startHostedRun: document.getElementById("startHostedRun"),
  openCheckout: document.getElementById("openCheckout"),
  openPortal: document.getElementById("openPortal"),
  licenseMessage: document.getElementById("licenseMessage"),
  usageMessage: document.getElementById("usageMessage"),
  hostedRunMessage: document.getElementById("hostedRunMessage"),
  commandOutput: document.getElementById("commandOutput"),
  copyCommand: document.getElementById("copyCommand")
};

document.addEventListener("DOMContentLoaded", init);
els.useTab.addEventListener("click", useCurrentTab);
els.generate.addEventListener("click", generateCommand);
els.selectAll.addEventListener("click", selectAllPlatforms);
els.copyCommand.addEventListener("click", copyCommand);
els.saveLicense.addEventListener("click", saveLicense);
els.validateLicense.addEventListener("click", validateLicense);
els.authorizeUsage.addEventListener("click", authorizeUsage);
els.copyHostedPayload.addEventListener("click", copyHostedPayload);
els.startHostedRun.addEventListener("click", startHostedRun);
els.openCheckout.addEventListener("click", openCheckout);
els.openPortal.addEventListener("click", openPortal);
els.openGuide.addEventListener("click", () => {
  setView("guide");
  focusSelectedGuideTab();
});
els.openWorkspace.addEventListener("click", () => {
  openWorkspace().catch(() => {});
});
els.guideBack.addEventListener("click", () => {
  setView("main");
  els.openGuide.focus();
});
els.guideTabs.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-guide-tab]");
  if (tab) {
    setGuideTab(tab.dataset.guideTab);
  }
});
els.guideTabs.addEventListener("keydown", handleGuideTabKeydown);
els.languageZh.addEventListener("click", () => setLanguage("zh-CN"));
els.languageEn.addEventListener("click", () => setLanguage("en"));
els.plan.addEventListener("change", updateEstimate);
els.monthlyRuns.addEventListener("input", updateEstimate);
els.deepReview.addEventListener("change", updateEstimate);
els.hostedVideo.addEventListener("change", updateEstimate);
els.workflowDepth.addEventListener("change", updateEstimate);
els.commandType.addEventListener("change", handleCommandTypeChange);
els.runFormFill.addEventListener("change", updateEstimate);
els.captureBrowserEvidence.addEventListener("change", updateEstimate);
els.allowLocalhost.addEventListener("change", updateEstimate);
els.autoSearchCompetitors.addEventListener("change", updateEstimate);
els.enableMultiQueryDiscovery.addEventListener("change", updateEstimate);
els.browserFollowUps.addEventListener("change", updateEstimate);
els.enablePublishQueue.addEventListener("change", updateEstimate);
els.enableBrowserPublishAssistant.addEventListener("change", updateEstimate);
els.enableBrowserFormFill.addEventListener("change", updateEstimate);
els.enableMetricsRecovery.addEventListener("change", updateEstimate);
els.enableNextRoundOptimization.addEventListener("change", updateEstimate);
els.alsoWindowsTask.addEventListener("change", updateEstimate);
Array.from(document.querySelectorAll("#platforms input")).forEach((input) => {
  input.addEventListener("change", updateEstimate);
});

async function init() {
  initializeViewState(window.location.search);
  try {
    setLanguage(browserUiLanguage(), false);
    const stored = await readLocalStorage([
      "licenseKey",
      "licenseEndpoint",
      "usageAuthorizeEndpoint",
      "hostedRunEndpoint",
      "licensePlan",
      "licenseActive",
      "uiLanguage"
    ]);
    await setLanguage(stored.uiLanguage || currentLanguage, !stored.uiLanguage);
    els.licenseKey.value = stored.licenseKey || "";
    els.licenseEndpoint.value = stored.licenseEndpoint || DEFAULT_ENDPOINT;
    els.usageAuthorizeEndpoint.value = stored.usageAuthorizeEndpoint || DEFAULT_USAGE_AUTHORIZE_ENDPOINT;
    els.hostedRunEndpoint.value = stored.hostedRunEndpoint || DEFAULT_HOSTED_RUN_ENDPOINT;
    applyHostedWorkerState();
    if (stored.licensePlan) {
      const planKey = String(stored.licensePlan).toLowerCase();
      if (PLANS[planKey]) {
        els.plan.value = planKey;
      }
    }
    setLicenseStatus(stored.licenseActive ? "statusActive" : "statusLocal", stored.licenseActive ? "active" : "");
    await useCurrentTab();
    if (document.body.dataset.layout === "workspace") {
      applyWorkspaceDraft(await readWorkspaceDraft());
    }
    handleCommandTypeChange();
    updateEstimate();
  } finally {
    document.body.dataset.initialized = "true";
  }
}

function browserUiLanguage() {
  if (typeof chrome !== "undefined" && chrome.i18n && typeof chrome.i18n.getUILanguage === "function") {
    try {
      return chrome.i18n.getUILanguage();
    } catch (error) {
      // Fall back to the browser language when extension i18n is unavailable.
    }
  }
  return typeof navigator !== "undefined" ? navigator.language : "en";
}

function localStorageApi() {
  if (typeof chrome === "undefined" || !chrome.storage || !chrome.storage.local) {
    return null;
  }
  return chrome.storage.local;
}

async function readLocalStorage(keys) {
  const storage = localStorageApi();
  if (!storage || typeof storage.get !== "function") {
    return {};
  }
  try {
    const stored = await storage.get(keys);
    return stored && typeof stored === "object" ? stored : {};
  } catch (error) {
    return {};
  }
}

async function writeLocalStorage(values) {
  const storage = localStorageApi();
  if (!storage || typeof storage.set !== "function") {
    return false;
  }
  try {
    await storage.set(values);
    return true;
  } catch (error) {
    return false;
  }
}

async function queryActiveTabs() {
  if (typeof chrome === "undefined" || !chrome.tabs || typeof chrome.tabs.query !== "function") {
    return [];
  }
  try {
    return await chrome.tabs.query({ active: true, currentWindow: true });
  } catch (error) {
    return [];
  }
}

async function writeClipboard(value) {
  if (typeof navigator === "undefined" || !navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
    return false;
  }
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch (error) {
    return false;
  }
}

async function openExternalTab(url) {
  if (typeof chrome !== "undefined" && chrome.tabs && typeof chrome.tabs.create === "function") {
    try {
      await chrome.tabs.create({ url });
      return true;
    } catch (error) {
      // Fall through to a normal browser window when extension tabs are unavailable.
    }
  }
  if (typeof window.open !== "function") {
    return false;
  }
  try {
    window.open(url, "_blank", "noopener,noreferrer");
    return true;
  } catch (error) {
    return false;
  }
}

function captureWorkspaceDraft() {
  const values = Object.fromEntries(
    WORKSPACE_DRAFT_VALUE_IDS.map((id) => [id, document.getElementById(id)?.value || ""])
  );
  const checks = Object.fromEntries(
    WORKSPACE_DRAFT_CHECKBOX_IDS.map((id) => [id, Boolean(document.getElementById(id)?.checked)])
  );
  return {
    version: 1,
    values,
    checks,
    platforms: selectedPlatforms(),
    commandOutput: els.commandOutput.value
  };
}

function applyWorkspaceDraft(draft) {
  if (!draft || typeof draft !== "object") {
    return;
  }
  const values = draft.values && typeof draft.values === "object" ? draft.values : {};
  WORKSPACE_DRAFT_VALUE_IDS.forEach((id) => {
    const element = document.getElementById(id);
    if (!element || !Object.hasOwn(values, id)) {
      return;
    }
    const value = String(values[id] ?? "");
    if (element.tagName === "SELECT" && !Array.from(element.options).some((option) => option.value === value)) {
      return;
    }
    element.value = value;
  });

  const checks = draft.checks && typeof draft.checks === "object" ? draft.checks : {};
  WORKSPACE_DRAFT_CHECKBOX_IDS.forEach((id) => {
    const element = document.getElementById(id);
    if (element && Object.hasOwn(checks, id)) {
      element.checked = Boolean(checks[id]);
    }
  });

  if (Array.isArray(draft.platforms)) {
    const selected = new Set(draft.platforms.map(String));
    document.querySelectorAll("#platforms input").forEach((input) => {
      input.checked = selected.has(input.value);
    });
  }
  if (typeof draft.commandOutput === "string") {
    setCommandValue(draft.commandOutput);
  }
}

async function persistWorkspaceDraft() {
  const draft = captureWorkspaceDraft();
  if (await writeLocalStorage({ [WORKSPACE_DRAFT_KEY]: draft })) {
    return true;
  }
  try {
    localStorage.setItem(WORKSPACE_DRAFT_KEY, JSON.stringify(draft));
    return true;
  } catch (error) {
    return false;
  }
}

async function readWorkspaceDraft() {
  const stored = await readLocalStorage([WORKSPACE_DRAFT_KEY]);
  if (stored[WORKSPACE_DRAFT_KEY] && typeof stored[WORKSPACE_DRAFT_KEY] === "object") {
    return stored[WORKSPACE_DRAFT_KEY];
  }
  try {
    const raw = localStorage.getItem(WORKSPACE_DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function normalizeLanguage(value) {
  return String(value || "").toLowerCase().startsWith("zh") ? "zh-CN" : "en";
}

function t(key, params = {}) {
  const dictionary = TRANSLATIONS[currentLanguage] || EN_TRANSLATIONS;
  const template = dictionary[key] || EN_TRANSLATIONS[key] || key;
  return Object.entries(params).reduce(
    (message, [name, value]) => message.replaceAll(`{${name}}`, String(value)),
    template
  );
}

async function setLanguage(language, persist = true) {
  currentLanguage = normalizeLanguage(language);
  document.documentElement.lang = currentLanguage;
  applyTranslations();
  if (persist) {
    await writeLocalStorage({ uiLanguage: currentLanguage });
  }
}

function applyTranslations() {
  document.title = t("appTitle");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  els.languageZh.setAttribute("aria-pressed", String(currentLanguage === "zh-CN"));
  els.languageEn.setAttribute("aria-pressed", String(currentLanguage === "en"));
  messageState.forEach((state, element) => {
    element.textContent = t(state.key, state.params);
  });
  if (commandMessage) {
    els.commandOutput.value = t(commandMessage.key, commandMessage.params);
  }
  renderLicenseStatus();
  handleCommandTypeChange();
  renderGuideContent();
}

function setLayout(layoutName) {
  document.body.dataset.layout = layoutName === "workspace" ? "workspace" : "popup";
}

function initializeViewState(search) {
  const requestedView = new URLSearchParams(search).get("view");
  setLayout(requestedView === "workspace" ? "workspace" : "popup");
  setView(requestedView === "guide" ? "guide" : "main");
}

function setView(viewName) {
  const view = viewName === "guide" ? "guide" : "main";
  const guideVisible = view === "guide";
  els.mainView.hidden = guideVisible;
  els.guideView.hidden = !guideVisible;
  document.body.dataset.view = view;
  if (guideVisible) {
    setGuideTab(document.querySelector("[data-guide-tab][aria-selected='true']")?.dataset.guideTab || "features");
  }
}

function setGuideTab(tabName) {
  const tab = ["features", "usage", "subscription"].includes(tabName) ? tabName : "features";
  document.querySelectorAll("[data-guide-tab]").forEach((button) => {
    const selected = button.dataset.guideTab === tab;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  ["features", "usage", "subscription"].forEach((sectionName) => {
    const section = els[`guide${sectionName[0].toUpperCase()}${sectionName.slice(1)}`];
    section.hidden = sectionName !== tab;
  });
}

function focusSelectedGuideTab() {
  document.querySelector("[data-guide-tab][aria-selected='true']")?.focus();
}

function handleGuideTabKeydown(event) {
  const tabs = Array.from(document.querySelectorAll("[data-guide-tab]"));
  const current = event.target.closest("[data-guide-tab]");
  const currentIndex = tabs.indexOf(current);
  if (currentIndex < 0) {
    return;
  }

  let nextIndex;
  if (event.key === "ArrowRight") {
    nextIndex = (currentIndex + 1) % tabs.length;
  } else if (event.key === "ArrowLeft") {
    nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = tabs.length - 1;
  } else {
    return;
  }

  event.preventDefault();
  const next = tabs[nextIndex];
  setGuideTab(next.dataset.guideTab);
  next.focus();
}

async function openWorkspace() {
  await persistWorkspaceDraft();
  const target = new URL(window.location.href);
  target.search = "";
  target.searchParams.set("view", "workspace");
  const targetUrl = target.toString();
  if (typeof chrome !== "undefined" && chrome.tabs && typeof chrome.tabs.create === "function") {
    try {
      await chrome.tabs.create({ url: targetUrl });
      return;
    } catch (error) {
      openWorkspaceFallback(targetUrl);
      return;
    }
  }
  openWorkspaceFallback(targetUrl);
}

function openWorkspaceFallback(targetUrl) {
  if (typeof window.open !== "function") {
    return;
  }
  try {
    window.open(targetUrl, "_blank", "noopener,noreferrer");
  } catch (error) {
    // Keep the popup usable when both tab-opening paths are unavailable.
  }
}

function renderGuideContent() {
  if (!els.guideFeatureList || !els.guideUsageList || !els.guidePlans) {
    return;
  }
  els.guideFeatureList.replaceChildren(
    ...GUIDE_FEATURES.map(([title, what, problem, benefit, useCase]) => {
      const article = document.createElement("article");
      article.className = "guide-card";
      const heading = document.createElement("h3");
      heading.textContent = t(title);
      article.append(heading);
      [["guideWhat", what], ["guideProblem", problem], ["guideBenefit", benefit], ["guideUseCase", useCase]].forEach(([label, key]) => {
        const paragraph = document.createElement("p");
        const strong = document.createElement("strong");
        strong.textContent = `${t(label)}: `;
        paragraph.append(strong, document.createTextNode(t(key)));
        article.append(paragraph);
      });
      return article;
    })
  );
  const advanced = document.createElement("details");
  advanced.className = "guide-disclosure";
  const summary = document.createElement("summary");
  summary.textContent = t("guideFeatureAdvanced");
  advanced.append(summary, document.createTextNode(t("guideFeatureAdvancedBody")));
  els.guideFeatureList.append(advanced);

  const usageItems = ["guideUsageStep1", "guideUsageStep2", "guideUsageStep3", "guideUsageStep4", "guideUsageSkill", "guideUsageEvidence", "guideUsageCaptcha", "guideUsageConfirm"];
  els.guideUsageList.replaceChildren(
    ...usageItems.map((key) => {
      const item = document.createElement("p");
      item.className = "guide-usage-item";
      item.textContent = t(key);
      return item;
    })
  );

  els.guidePlans.replaceChildren(
    ...Object.entries(PLANS).map(([key, plan]) => {
      const details = GUIDE_PLAN_DETAILS[key];
      const row = document.createElement("div");
      row.className = "plan-row";
      const summary = document.createElement("div");
      summary.className = "plan-row-summary";
      const name = document.createElement("strong");
      name.textContent = t(details.label);
      const credits = document.createElement("span");
      credits.textContent = t("guidePlanCredits", { credits: plan.credits });
      const price = document.createElement("span");
      price.textContent = t("guidePlanPrice", { price: plan.priceCny });
      summary.append(name, credits, price);
      const audience = document.createElement("p");
      audience.className = "plan-audience";
      const audienceLabel = document.createElement("strong");
      audienceLabel.textContent = `${t("guidePlanAudienceLabel")}: `;
      audience.append(audienceLabel, document.createTextNode(t(details.audience)));
      const included = document.createElement("p");
      included.className = "plan-included";
      const includedLabel = document.createElement("strong");
      includedLabel.textContent = `${t("guidePlanIncludedLabel")}: `;
      included.append(includedLabel, document.createTextNode(t(details.included, { credits: plan.credits })));
      row.append(summary, audience, included);
      return row;
    })
  );
}

function setMessage(element, key, params = {}) {
  messageState.set(element, { key, params });
  element.textContent = t(key, params);
}

function applyHostedWorkerState() {
  const disabled = !HOSTED_WORKER_ENABLED;
  [els.authorizeUsage, els.copyHostedPayload, els.startHostedRun, els.hostedRunEndpoint].forEach((element) => {
    element.disabled = disabled;
    element.setAttribute("aria-disabled", String(disabled));
  });
  if (disabled) {
    setMessage(els.usageMessage, "hostedWorkerOffMessage");
    setMessage(els.hostedRunMessage, "hostedWorkerOffMessage");
  }
}

function requireHostedWorker(messageElement) {
  if (HOSTED_WORKER_ENABLED) {
    return true;
  }
  setMessage(messageElement, "hostedWorkerOffMessage");
  return false;
}

function setCommandMessage(key, params = {}) {
  commandMessage = { key, params };
  els.commandOutput.value = t(key, params);
}

function setCommandValue(value) {
  commandMessage = null;
  els.commandOutput.value = value;
}

async function useCurrentTab() {
  const tabs = await queryActiveTabs();
  const tab = tabs && tabs[0];
  if (!tab) {
    setMessage(els.tabTitle, "noActiveTab");
    return;
  }
  if (tab.url && /^https?:\/\//.test(tab.url)) {
    els.productUrl.value = tab.url;
    if (els.commandType.value === "platform_data_collect" && els.platformDataMode.value !== "search") {
      els.platformDataTarget.value = tab.url;
    }
  }
  setMessage(els.tabTitle, tab.title ? "currentTab" : "currentTabCaptured", tab.title ? { title: tab.title } : {});
}

function selectedPlatforms() {
  return Array.from(document.querySelectorAll("#platforms input:checked")).map((input) => input.value);
}

function selectAllPlatforms() {
  const boxes = Array.from(document.querySelectorAll("#platforms input"));
  const allChecked = boxes.every((box) => box.checked);
  boxes.forEach((box) => {
    box.checked = !allChecked;
  });
  updateEstimate();
}

function generateCommand() {
  const commandType = els.commandType.value;
  if (commandType === "platform_data_collect") {
    generatePlatformDataCommand();
    return;
  }
  if (commandType === "browser_publish_session") {
    generateBrowserPublishSessionCommand();
    return;
  }
  if (commandType === "launch_unlock_pack") {
    generateLaunchUnlockPackCommand();
    return;
  }
  if (commandType === "viral_evidence_inbox_setup") {
    generateViralEvidenceInboxSetupCommand();
    return;
  }
  if (commandType === "viral_evidence_inbox") {
    generateViralEvidenceInboxCommand();
    return;
  }
  if (commandType === "real_evidence_inbox_setup") {
    generateRealEvidenceInboxSetupCommand();
    return;
  }
  if (commandType === "real_evidence_inbox") {
    generateRealEvidenceInboxCommand();
    return;
  }
  if (commandType === "performance_monitor") {
    generatePerformanceMonitorCommand();
    return;
  }
  if (commandType === "final_readiness") {
    generateFinalReadinessCommand();
    return;
  }
  if (commandType === "automation_init") {
    generateAutomationInitCommand();
    return;
  }
  if (commandType === "automation_run") {
    generateAutomationRunCommand();
    return;
  }
  if (commandType === "automation_windows_task") {
    setCommandValue(automationWindowsTaskCommand());
    updateEstimate();
    return;
  }
  generateSkillEntryCommand();
}

function generatePlatformDataCommand() {
  const target = els.platformDataTarget.value.trim();
  if (!target) {
    setCommandMessage(els.platformDataMode.value === "search" ? "enterSearchKeyword" : "enterContentTarget");
    return;
  }
  const args = [
    "python scripts\\promotion_manager.py platform-data collect",
    `--platform ${els.platformDataPlatform.value}`,
    `--mode ${els.platformDataMode.value}`,
    `--out-dir ${quote(outDir())}`
  ];
  if (els.platformDataMode.value === "search") {
    args.push(`--query ${quote(target)}`);
  } else {
    args.push(`--target ${quote(target)}`);
  }
  if (els.platformDataSubComments.checked) {
    args.push("--include-sub-comments");
  }
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateSkillEntryCommand() {
  const url = els.productUrl.value.trim();
  const platforms = selectedPlatforms();
  if (!url) {
    setCommandMessage("enterProductUrl");
    return;
  }
  if (!platforms.length) {
    setCommandMessage("selectPlatform");
    return;
  }
  const args = [
    "python scripts\\skill_entry.py",
    `--link ${quote(url)}`,
    `--platforms ${platforms.join(",")}`,
    `--out-dir ${quote(outDir())}`
  ];
  if (els.workflowDepth.value === "playbook") {
    args.push("--skip-video");
    args.push("--skip-publish-queue");
    args.push("--skip-final-capability-audit");
  }
  if (els.workflowDepth.value === "research") {
    args.push("--skip-video");
    args.push("--skip-publish-queue");
  }
  if (els.workflowDepth.value === "full") {
    args.push("--install-browser-if-missing");
  }
  if (els.deepReview.checked) {
    args.push("--multi-query-query-count 8");
  }
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateBrowserPublishSessionCommand() {
  const queuePath = els.publishQueue.value.trim();
  if (!queuePath) {
    setCommandMessage("enterPublishQueue");
    return;
  }
  const platforms = selectedPlatforms();
  const args = [
    "python scripts\\browser_publish_session.py",
    `--publish-queue ${quote(queuePath)}`,
    `--out-dir ${quote(outDir())}`
  ];
  if (platforms.length) {
    args.push(`--platforms ${platforms.join(",")}`);
  }
  parseList(els.platformPublishUrls.value).forEach((value) => {
    args.push(`--platform-publish-url ${quote(value)}`);
  });
  if (els.runFormFill.checked) {
    args.push("--run-form-fill");
  }
  if (els.captureBrowserEvidence.checked) {
    args.push("--open-browser");
  }
  if (els.allowLocalhost.checked) {
    args.push("--allow-localhost");
  }
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateLaunchUnlockPackCommand() {
  const queuePath = els.publishQueue.value.trim();
  if (!queuePath) {
    setCommandMessage("enterPublishQueue");
    return;
  }
  const platforms = selectedPlatforms();
  const args = [
    "python scripts\\launch_unlock_pack.py",
    `--publish-queue ${quote(queuePath)}`,
    `--out-dir ${quote(outDir())}`
  ];
  if (platforms.length) {
    args.push(`--platforms ${platforms.join(",")}`);
  }
  parseList(els.platformPublishUrls.value).forEach((value) => {
    args.push(`--platform-publish-url ${quote(value)}`);
  });
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateRealEvidenceInboxCommand() {
  const inboxPath = els.evidenceInbox.value.trim();
  if (!inboxPath) {
    setCommandMessage("enterEvidenceInbox");
    return;
  }
  const args = [
    "python scripts\\real_evidence_inbox.py",
    `--inbox-dir ${quote(inboxPath)}`,
    `--out-dir ${quote(outDir())}`
  ];
  if (els.captureBrowserEvidence.checked) {
    args.push("--capture-browser-assisted");
  }
  if (els.allowLocalhost.checked) {
    args.push("--allow-localhost");
  }
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateViralEvidenceInboxCommand() {
  const inboxPath = els.evidenceInbox.value.trim();
  if (!inboxPath) {
    setCommandMessage("enterEvidenceInbox");
    return;
  }
  const args = [
    "python scripts\\viral_evidence_inbox.py",
    `--inbox-dir ${quote(inboxPath)}`,
    `--out-dir ${quote(outDir())}`
  ];
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateViralEvidenceInboxSetupCommand() {
  const url = els.productUrl.value.trim();
  const inboxPath = els.evidenceInbox.value.trim();
  const platforms = selectedPlatforms();
  if (!url) {
    setCommandMessage("enterProductUrl");
    return;
  }
  if (!inboxPath) {
    setCommandMessage("enterEvidenceInbox");
    return;
  }
  if (!platforms.length) {
    setCommandMessage("selectPlatform");
    return;
  }
  const args = [
    "python scripts\\viral_evidence_inbox_setup.py",
    `--product-url ${quote(url)}`,
    `--platforms ${platforms.join(",")}`,
    `--inbox-dir ${quote(inboxPath)}`,
    `--out-dir ${quote(outDir())}`
  ];
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateRealEvidenceInboxSetupCommand() {
  const url = els.productUrl.value.trim();
  const inboxPath = els.evidenceInbox.value.trim();
  const platforms = selectedPlatforms();
  if (!url) {
    setCommandMessage("enterProductUrl");
    return;
  }
  if (!inboxPath) {
    setCommandMessage("enterEvidenceInbox");
    return;
  }
  if (!platforms.length) {
    setCommandMessage("selectPlatform");
    return;
  }
  const args = [
    "python scripts\\real_evidence_inbox_setup.py",
    `--product-url ${quote(url)}`,
    `--platforms ${platforms.join(",")}`,
    `--inbox-dir ${quote(inboxPath)}`,
    `--out-dir ${quote(outDir())}`
  ];
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generatePerformanceMonitorCommand() {
  const args = [
    "python scripts\\performance_monitor.py",
    `--out-dir ${quote(outDir())}`
  ];
  if (els.captureBrowserEvidence.checked) {
    args.push("--capture-browser-assisted");
  }
  if (els.allowLocalhost.checked) {
    args.push("--allow-localhost");
  }
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateFinalReadinessCommand() {
  const args = [
    "python scripts\\final_capability_readiness.py",
    `--out-dir ${quote(outDir())}`
  ];
  setCommandValue(args.join(" "));
  updateEstimate();
}

function generateAutomationInitCommand() {
  const url = els.productUrl.value.trim();
  const platforms = selectedPlatforms();
  if (!url) {
    setCommandMessage("enterProductUrl");
    return;
  }
  if (!platforms.length) {
    setCommandMessage("selectPlatform");
    return;
  }
  const args = [
    "python scripts\\automation_scheduler.py init",
    `--config ${quote(automationConfig())}`,
    `--job-id ${quote(els.automationJobId.value.trim() || "product-weekly")}`,
    `--browser-url ${quote(url)}`,
    `--platforms ${platforms.join(",")}`,
    `--interval-days ${positiveInt(els.automationIntervalDays.value, 7)}`,
    `--output-root ${quote(automationOutputRoot())}`,
    "--install-browser-if-missing"
  ];
  if (els.autoSearchCompetitors.checked) {
    args.push("--auto-search-competitors");
  }
  if (els.enableMultiQueryDiscovery.checked) {
    args.push("--enable-multi-query-viral-discovery");
  }
  if (els.browserFollowUps.checked) {
    args.push("--run-follow-up-captures");
    args.push("--capture-browser-assisted-follow-ups");
    args.push("--sample-video-frames");
  }
  if (els.enablePublishQueue.checked) {
    args.push("--enable-publish-queue");
  }
  if (els.enableBrowserPublishAssistant.checked) {
    args.push("--enable-browser-publish-assistant");
  }
  if (els.enableBrowserFormFill.checked) {
    args.push("--enable-browser-form-fill");
  }
  if (els.enableMetricsRecovery.checked) {
    args.push("--enable-metrics-recovery");
  }
  if (els.enableNextRoundOptimization.checked) {
    args.push("--enable-next-round-optimization");
  }
  const commands = [args.join(" ")];
  if (els.alsoWindowsTask.checked) {
    commands.push(automationWindowsTaskCommand());
  }
  setCommandValue(commands.join("\n"));
  updateEstimate();
}

function generateAutomationRunCommand() {
  const args = [
    "python scripts\\automation_scheduler.py run",
    `--config ${quote(automationConfig())}`,
    "--force"
  ];
  setCommandValue(args.join(" "));
  updateEstimate();
}

function automationWindowsTaskCommand() {
  const args = [
    "python scripts\\automation_scheduler.py windows-task",
    `--config ${quote(automationConfig())}`,
    `--out-file ${quote(els.windowsTaskScript.value.trim() || ".\\register-enhe-promotion-task.ps1")}`,
    "--task-name \"ENHE Promotion Manager\"",
    `--time ${quote(els.windowsTaskTime.value.trim() || "09:00")}`
  ];
  return args.join(" ");
}

async function copyCommand() {
  const value = els.commandOutput.value.trim();
  if (!value) {
    return;
  }
  if (!(await writeClipboard(value))) {
    return;
  }
  els.copyCommand.textContent = t("copied");
  setTimeout(() => {
    els.copyCommand.textContent = t("copyButton");
  }, 1200);
}

async function saveLicense() {
  const saved = await writeLocalStorage({
    licenseKey: els.licenseKey.value.trim(),
    licenseEndpoint: els.licenseEndpoint.value.trim() || DEFAULT_ENDPOINT,
    usageAuthorizeEndpoint: els.usageAuthorizeEndpoint.value.trim() || DEFAULT_USAGE_AUTHORIZE_ENDPOINT,
    hostedRunEndpoint: els.hostedRunEndpoint.value.trim() || DEFAULT_HOSTED_RUN_ENDPOINT,
    licensePlan: els.plan.value
  });
  if (saved) {
    setMessage(els.licenseMessage, "licenseSaved");
  }
}

async function authorizeUsage() {
  if (!requireHostedWorker(els.usageMessage)) {
    return;
  }
  const licenseKey = els.licenseKey.value.trim();
  const endpoint = els.usageAuthorizeEndpoint.value.trim() || DEFAULT_USAGE_AUTHORIZE_ENDPOINT;
  const estimate = estimateCredits();
  if (!licenseKey) {
    setMessage(els.usageMessage, "pasteKeyForCredits");
    return;
  }
  if (estimate.creditsPerRun <= 0) {
    setMessage(els.usageMessage, "noHostedCredits");
    return;
  }
  setMessage(els.usageMessage, "requestingUsage");
  const idempotencyKey = createIdempotencyKey();
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        licenseKey,
        workflowType: estimate.workflowType,
        estimatedCredits: estimate.creditsPerRun,
        idempotencyKey,
        commandType: els.commandType.value,
        extensionVersion: chrome.runtime.getManifest().version,
        website: ENHE_SITE
      })
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (!payload.allowed) {
      setMessage(els.usageMessage, "usageBlocked", { reason: payload.reason || "not_allowed" });
      return;
    }
    await writeLocalStorage({
      usageAuthorizeEndpoint: endpoint,
      lastUsageId: payload.usageId || "",
      lastUsageWorkflowType: estimate.workflowType,
      lastUsageCreditsReserved: payload.creditsReserved ?? estimate.creditsPerRun,
      lastUsageCommandType: els.commandType.value,
      lastUsageIdempotencyKey: idempotencyKey
    });
    setMessage(els.usageMessage, "creditsReserved", {
      reserved: payload.creditsReserved ?? estimate.creditsPerRun,
      remaining: payload.creditsRemainingAfterReservation ?? t("unknownValue")
    });
  } catch (error) {
    setMessage(els.usageMessage, "usageUnavailable", { error: error.message });
  }
}

async function validateLicense() {
  const licenseKey = els.licenseKey.value.trim();
  const endpoint = els.licenseEndpoint.value.trim() || DEFAULT_ENDPOINT;
  if (!licenseKey) {
    setLicenseStatus("statusLocal", "");
    setMessage(els.licenseMessage, "pasteKeyForValidation");
    return;
  }
  setMessage(els.licenseMessage, "checkingLicense");
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        licenseKey,
        requestedPlan: els.plan.value,
        extensionVersion: chrome.runtime.getManifest().version,
        website: ENHE_SITE,
        commandType: els.commandType.value,
        estimatedMonthlyCredits: estimateCredits().credits
      })
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    const active = Boolean(payload.active);
    await writeLocalStorage({
      licenseKey,
      licenseEndpoint: endpoint,
      hostedRunEndpoint: payload.hostedRunEndpoint || els.hostedRunEndpoint.value.trim() || DEFAULT_HOSTED_RUN_ENDPOINT,
      licensePlan: String(payload.plan || els.plan.value).toLowerCase(),
      licenseActive: active,
      checkoutUrl: payload.checkoutUrl || CHECKOUT_URL,
      customerPortalUrl: payload.customerPortalUrl || CUSTOMER_PORTAL_URL
    });
    els.hostedRunEndpoint.value = payload.hostedRunEndpoint || els.hostedRunEndpoint.value.trim() || DEFAULT_HOSTED_RUN_ENDPOINT;
    setLicenseStatus(active ? "statusActive" : "statusInactive", active ? "active" : "error");
    setMessage(
      els.licenseMessage,
      active ? "licensePlanStatus" : "licenseInactive",
      active ? { plan: payload.plan || els.plan.value, credits: payload.creditsRemaining ?? t("unknownValue") } : {}
    );
  } catch (error) {
    await writeLocalStorage({ licenseActive: false });
    setLicenseStatus("statusOffline", "error");
    setMessage(els.licenseMessage, "licenseUnavailable", { error: error.message });
  }
}

async function copyHostedPayload() {
  if (!requireHostedWorker(els.hostedRunMessage)) {
    return;
  }
  try {
    const payload = await buildHostedRunPayload();
    if (!(await writeClipboard(JSON.stringify(payload, null, 2)))) {
      throw new Error("Clipboard unavailable");
    }
    setMessage(els.hostedRunMessage, "hostedPayloadCopied");
  } catch (error) {
    setMessage(els.hostedRunMessage, error.translationKey || "hostedUnavailable", error.translationKey ? {} : { error: error.message });
  }
}

async function startHostedRun() {
  if (!requireHostedWorker(els.hostedRunMessage)) {
    return;
  }
  const endpoint = els.hostedRunEndpoint.value.trim() || DEFAULT_HOSTED_RUN_ENDPOINT;
  let payload;
  try {
    payload = await buildHostedRunPayload();
  } catch (error) {
    setMessage(els.hostedRunMessage, error.translationKey || "hostedUnavailable", error.translationKey ? {} : { error: error.message });
    return;
  }
  if (payload.estimatedCredits > 0 && !payload.usageId) {
    setMessage(els.hostedRunMessage, "reserveBeforeHosted");
    return;
  }
  setMessage(els.hostedRunMessage, "submittingHosted");
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const result = await response.json();
    await writeLocalStorage({
      hostedRunEndpoint: endpoint,
      lastHostedRunId: result.runId || "",
      lastHostedRunStatus: result.status || "",
      lastHostedRunStatusUrl: result.statusUrl || "",
      lastHostedRunDashboardUrl: result.dashboardUrl || ""
    });
    const statusLink = result.statusUrl || result.dashboardUrl || "";
    setMessage(els.hostedRunMessage, "hostedAccepted", {
      status: result.status || t("acceptedStatus"),
      runId: result.runId ? `${currentLanguage === "zh-CN" ? "：" : ": "}${result.runId}` : "",
      statusLink: statusLink ? `${currentLanguage === "zh-CN" ? "。状态：" : ". Status: "}${statusLink}` : ""
    });
  } catch (error) {
    setMessage(els.hostedRunMessage, "hostedUnavailable", { error: error.message });
  }
}

async function buildHostedRunPayload() {
  const licenseKey = els.licenseKey.value.trim();
  const estimate = estimateCredits();
  const url = els.productUrl.value.trim();
  if (!licenseKey) {
    throw localizedError("pasteKeyForHosted");
  }
  if (requiresProductUrl(els.commandType.value) && !url) {
    throw localizedError("enterProductUrl");
  }
  if (requiresPlatforms(els.commandType.value) && !selectedPlatforms().length) {
    throw localizedError("selectPlatform");
  }
  if ((els.commandType.value === "browser_publish_session" || els.commandType.value === "launch_unlock_pack") && !els.publishQueue.value.trim()) {
    throw localizedError("enterPublishQueue");
  }
  if (
    (
      els.commandType.value === "real_evidence_inbox" ||
      els.commandType.value === "real_evidence_inbox_setup" ||
      els.commandType.value === "viral_evidence_inbox" ||
      els.commandType.value === "viral_evidence_inbox_setup"
    ) &&
    !els.evidenceInbox.value.trim()
  ) {
    throw localizedError("enterEvidenceInbox");
  }
  generateCommand();
  const localCommand = els.commandOutput.value.trim();
  if (commandMessage) {
    throw localizedError(commandMessage.key);
  }
  if (!localCommand) {
    throw localizedError("generateFirst");
  }
  const stored = await readLocalStorage([
    "lastUsageId",
    "lastUsageWorkflowType",
    "lastUsageCreditsReserved",
    "lastUsageCommandType"
  ]);
  const usageMatches =
    stored.lastUsageWorkflowType === estimate.workflowType &&
    stored.lastUsageCommandType === els.commandType.value &&
    Number(stored.lastUsageCreditsReserved || 0) >= estimate.creditsPerRun;
  return {
    licenseKey,
    usageId: usageMatches ? stored.lastUsageId || "" : "",
    workflowType: estimate.workflowType,
    estimatedCredits: estimate.creditsPerRun,
    commandType: els.commandType.value,
    extensionVersion: chrome.runtime.getManifest().version,
    website: ENHE_SITE,
    requestSource: "chrome_extension",
    idempotencyKey: createIdempotencyKey(),
    productUrl: url,
    platforms: selectedPlatforms(),
    workflowDepth: els.workflowDepth.value,
    localCommand,
    options: hostedRunOptions(),
    safety: {
      approvalRequiredForOfficialPublish: true,
      finalPublishNotClickedByExtension: true,
      noPlatformSecretsInPayload: true,
      noCaptchaBypass: true
    }
  };
}

function hostedRunOptions() {
  return {
    outputDir: outDir(),
    publishQueue: els.publishQueue.value.trim(),
    publisherUrlOverrides: parseList(els.platformPublishUrls.value),
    evidenceInbox: els.evidenceInbox.value.trim(),
    automationConfig: automationConfig(),
    automationOutputRoot: automationOutputRoot(),
    automationJobId: els.automationJobId.value.trim() || "product-weekly",
    automationIntervalDays: positiveInt(els.automationIntervalDays.value, 7),
    windowsTaskScript: els.windowsTaskScript.value.trim() || ".\\register-enhe-promotion-task.ps1",
    windowsTaskTime: els.windowsTaskTime.value.trim() || "09:00",
    runFormFill: els.runFormFill.checked,
    captureBrowserEvidence: els.captureBrowserEvidence.checked,
    allowLocalhost: els.allowLocalhost.checked,
    autoSearchCompetitors: els.autoSearchCompetitors.checked,
    enableMultiQueryDiscovery: els.enableMultiQueryDiscovery.checked,
    browserFollowUps: els.browserFollowUps.checked,
    enablePublishQueue: els.enablePublishQueue.checked,
    enableBrowserPublishAssistant: els.enableBrowserPublishAssistant.checked,
    enableBrowserFormFill: els.enableBrowserFormFill.checked,
    enableMetricsRecovery: els.enableMetricsRecovery.checked,
    enableNextRoundOptimization: els.enableNextRoundOptimization.checked,
    alsoWindowsTask: els.alsoWindowsTask.checked,
    deepReview: els.deepReview.checked,
    hostedVideo: els.hostedVideo.checked
  };
}

function requiresProductUrl(commandType) {
  return (
    commandType === "skill_entry" ||
    commandType === "automation_init" ||
    commandType === "real_evidence_inbox_setup" ||
    commandType === "viral_evidence_inbox_setup"
  );
}

function requiresPlatforms(commandType) {
  return (
    commandType === "skill_entry" ||
    commandType === "automation_init" ||
    commandType === "real_evidence_inbox_setup" ||
    commandType === "viral_evidence_inbox_setup"
  );
}

async function openCheckout() {
  const estimate = estimateCredits();
  const url = new URL(CHECKOUT_URL);
  url.searchParams.set("plan", els.plan.value);
  url.searchParams.set("source", "extension");
  url.searchParams.set("credits", String(estimate.credits));
  url.searchParams.set("runs", String(estimate.runs));
  url.searchParams.set("workflow", estimate.workflowType);
  await openExternalTab(url.toString());
}

async function openPortal() {
  const stored = await readLocalStorage(["customerPortalUrl"]);
  const url = new URL(stored.customerPortalUrl || CUSTOMER_PORTAL_URL);
  url.searchParams.set("source", "extension");
  await openExternalTab(url.toString());
}

function updateEstimate() {
  const estimate = estimateCredits();
  const plan = PLANS[els.plan.value] || PLANS.free;
  els.creditMeter.textContent = t("creditsCount", { credits: estimate.credits });
  if (!HOSTED_WORKER_ENABLED) {
    els.costSummary.textContent = t("hostedEstimateReference", {
      plan: plan.label,
      included: plan.credits,
      workflow: t(estimate.label),
      planned: estimate.credits
    });
    return;
  }
  const estimatedCost = estimate.credits * COST_PER_CREDIT;
  els.costSummary.textContent = currentLanguage === "en"
    ? `${plan.label} includes ${plan.credits} credits at CNY ${plan.priceCny}/30 days. ${t(estimate.label)}: ${estimate.creditsPerRun} credits/run, ${estimate.credits} credits planned, estimated gross cost up to USD ${estimatedCost.toFixed(2)}.`
    : t("costSummary", {
      plan: plan.label,
      included: plan.credits,
      price: plan.priceCny,
      workflow: t(estimate.label),
      perRun: estimate.creditsPerRun,
      planned: estimate.credits,
      cost: estimatedCost.toFixed(2)
    });
  if (estimate.credits > plan.credits && plan.priceCny > 0) {
    els.costSummary.textContent += t("costOverage");
  }
}

function estimateCredits() {
  const runs = Math.max(0, Number.parseInt(els.monthlyRuns.value || "0", 10));
  const commandType = els.commandType.value;
  const depth = els.workflowDepth.value;
  let workflowType = commandType;
  let label = COMMAND_LABELS[commandType] || "labelWorkflow";
  let creditsPerRun = 0;

  if (commandType === "skill_entry") {
    workflowType = depth === "playbook" ? "command_only" : depth === "research" ? "research_run" : "standard_run";
    creditsPerRun = depth === "playbook" ? 0 : depth === "research" ? 3 : 4;
    label = depth === "playbook" ? "labelPlaybookCommand" : depth === "research" ? "labelResearchRun" : "labelFullSkillRun";
  }
  if (commandType === "browser_publish_session") {
    workflowType = "browser_publish_session";
    creditsPerRun = 2;
  }
  if (commandType === "launch_unlock_pack") {
    workflowType = "launch_unlock_pack";
    creditsPerRun = 2;
  }
  if (commandType === "viral_evidence_inbox_setup") {
    workflowType = "viral_evidence_inbox_setup";
    creditsPerRun = 1;
  }
  if (commandType === "viral_evidence_inbox") {
    workflowType = "viral_evidence_inbox";
    creditsPerRun = 2;
  }
  if (commandType === "real_evidence_inbox_setup") {
    workflowType = "real_evidence_inbox_setup";
    creditsPerRun = 1;
  }
  if (commandType === "real_evidence_inbox") {
    workflowType = "real_evidence_inbox";
    creditsPerRun = 2;
  }
  if (commandType === "performance_monitor") {
    workflowType = "performance_monitor";
    creditsPerRun = 2;
  }
  if (commandType === "final_readiness") {
    workflowType = "final_readiness_audit";
    creditsPerRun = 1;
  }
  if (commandType === "automation_init") {
    workflowType = "automation_config_init";
    creditsPerRun = els.alsoWindowsTask.checked ? 2 : 1;
  }
  if (commandType === "automation_run") {
    workflowType = "automation_due_run";
    creditsPerRun = 4;
  }
  if (commandType === "automation_windows_task") {
    workflowType = "automation_windows_task";
    creditsPerRun = 1;
  }
  if (commandType === "skill_entry" && els.deepReview.checked) {
    creditsPerRun += 15;
  }
  if (commandType === "skill_entry" && els.hostedVideo.checked) {
    creditsPerRun += 3;
  }
  return { runs, workflowType, label, creditsPerRun, credits: runs * creditsPerRun };
}

function setLicenseStatus(key, className) {
  licenseStatusState = { key, className };
  renderLicenseStatus();
}

function renderLicenseStatus() {
  els.licenseStatus.textContent = t(licenseStatusState.key);
  els.licenseStatus.className = `status ${licenseStatusState.className || ""}`.trim();
}

function handleCommandTypeChange() {
  const commandType = els.commandType.value;
  const scope = commandScope(commandType);
  els.commandModeLabel.textContent = t(COMMAND_LABELS[commandType] || "labelWorkflow");
  Array.from(document.querySelectorAll("[data-command-scope]")).forEach((node) => {
    const scopes = String(node.dataset.commandScope || "").split(/\s+/);
    node.classList.toggle("is-hidden", scope ? !scopes.includes(scope) : true);
  });
  updateEstimate();
}

function commandScope(commandType) {
  if (commandType === "platform_data_collect") {
    return "platform-data";
  }
  if (commandType === "browser_publish_session" || commandType === "launch_unlock_pack") {
    return "publish";
  }
  if (
    commandType === "real_evidence_inbox" ||
    commandType === "real_evidence_inbox_setup" ||
    commandType === "viral_evidence_inbox" ||
    commandType === "viral_evidence_inbox_setup"
  ) {
    return "evidence-inbox";
  }
  if (commandType === "performance_monitor") {
    return "performance";
  }
  if (commandType === "automation_init") {
    return "automation-init";
  }
  if (commandType === "automation_run") {
    return "automation-run";
  }
  if (commandType === "automation_windows_task") {
    return "automation-task";
  }
  return "";
}

function outDir() {
  return els.outDir.value.trim() || ".\\promotion-output";
}

function automationConfig() {
  return els.automationConfig.value.trim() || ".\\promotion-automation.json";
}

function automationOutputRoot() {
  return els.automationOutputRoot.value.trim() || ".\\promotion-output\\automation";
}

function parseList(value) {
  return String(value || "")
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function quote(value) {
  return `"${String(value).replace(/"/g, '\\"')}"`;
}

function positiveInt(value, fallback) {
  const parsed = Number.parseInt(value || "", 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return parsed;
}

function createIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `pm_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function localizedError(key) {
  const error = new Error(t(key));
  error.translationKey = key;
  return error;
}
