import type { AddinRequirement, CapabilityExecutionKind, RealValidationStatus, RunStage, StatusLevel } from "../types";

export const zhCN = {
  appName: "SolidWorks AI Studio",
  shell: {
    skipToContent: "跳到主内容",
    navigation: "主导航",
    systemStatus: "系统状态",
    paletteShortcut: "Ctrl K",
    statuses: {
      apiOnline: "本地后端在线",
      apiPending: "本地后端待连接",
      llmVerified: "LLM 已验证",
      llmUnverified: "LLM 未验证",
      solidworksReady: "SolidWorks 就绪",
      solidworksChecking: "预检进行中",
      solidworksStale: "预检未完成",
      blockedMode: "真实执行未就绪",
      mcpRunning: "MCP 运行中",
      mcpStopped: "MCP 已停止"
    }
  },
  nav: {
    workspace: "工作台",
    skills: "Skill",
    monitor: "执行",
    review: "审查",
    files: "文件",
    settings: "设置"
  },
  viewTitles: {
    onboarding: "首次设置",
    workspace: "自动化工作台",
    skills: "Skill 浏览器",
    monitor: "执行监控",
    review: "审查中心",
    files: "文件与导出",
    settings: "设置"
  },
  statusLevels: {
    pass: "通过",
    warn: "警告",
    fail: "失败",
    info: "信息"
  } satisfies Record<StatusLevel, string>,
  stages: {
    queued: "已排队",
    planning: "规划中",
    generated: "已生成",
    waiting_approval: "等待审批",
    running: "执行中",
    reviewing: "审查中",
    done: "已完成",
    failed: "失败"
  } satisfies Record<RunStage, string>,
  onboarding: {
    eyebrow: "本地 CAD 自动化工作站",
    headline: "SolidWorks AI Studio",
    intro:
      "连接 OpenAI-compatible 大模型，规划 SolidWorks 自动化任务，审查生成的 Python Script，再由本地 FastAPI 后端安全执行 COM 操作。",
    enterWorkspace: "进入工作台",
    refreshChecks: "刷新检查",
    readinessLabel: "首次运行就绪状态",
    tiles: {
      api: "本地 API",
      llm: "LLM 配置",
      preflight: "运行前自检",
      skills: "Skill 索引",
      realValidation: "真实验证"
    },
    details: {
      backendWaiting: "等待后端健康检查",
      profilesLoading: "正在加载 Profile",
      activeProfile: "当前 Profile",
      preflightLoading: "正在读取自检结果",
      swUnknown: "未知",
      indexLoading: "正在加载索引",
      noRealValidation: "尚未读取真实验证报告"
    }
  },
  prompt: {
    eyebrow: "Prompt Composer",
    title: "自然语言生成可审查的 SolidWorks Python",
    requestLabel: "自动化需求",
    placeholder: "描述 SolidWorks 任务、期望输出、保存路径和必须保留的工程约束。",
    templatesLabel: "Prompt 模板",
    templates: [
      "新建一个 120x80x10mm 安装板，四角各打 M6 通孔，倒角 1mm，保存并导出 STEP。",
      "打开当前装配体，添加一个组件，建立 coincident 与 concentric mates，然后运行模型审查。",
      "将当前文档导出为 STEP、STL、PDF、DXF，并生成包含预览图的 review_report.json。"
    ],
    planButton: "规划",
    generateButton: "生成 Script",
    approveButton: "审批并执行",
    executionPlan: "执行计划",
    noPlan: "尚未生成执行计划。",
    scriptPreview: "Script 预览",
    rejectedNonReal: "非真实生成已拒绝",
    liveProvider: "真实 Provider",
    providerVerified: "Provider 已验证",
    configuredOutput: "已配置输出目录",
    scriptEmpty: "生成 Script 后，可在审批前检查完整 Python 内容。",
    defaultPrompt: "新建一个 120x80x10mm 安装板，四角各打 M6 通孔，倒角 1mm，保存并导出 STEP。"
  },
  tools: {
    eyebrow: "直接工具",
    title: "串行 SolidWorks 操作",
    registryTitle: "Registry-backed 工具",
    lastAction: "最近一次直接操作",
    noAction: "本次会话尚未运行直接工具。",
    mode: "状态",
    realEvidence: "真实证据",
    verified: "已验证",
    unverified: "未验证",
    items: {
      health: "健康检查",
      connect: "连接 SolidWorks",
      newPart: "新建零件",
      open: "打开文档",
      save: "保存文档",
      exportStep: "导出 STEP",
      exportStl: "导出 STL",
      exportPdf: "导出 PDF",
      exportDxf: "导出 DXF",
      exportDwg: "导出 DWG",
      review: "审查当前文档",
      createBasicPart: "创建基础零件",
      mcpStart: "启动 MCP Server",
      mcpStop: "停止 MCP Server"
    }
  },
  workspace: {
    session: "会话",
    liveLane: "真实 COM 通道",
    blockedLane: "真实执行阻断",
    currentDocument: "当前文档",
    noDocument: "尚未加载活动文档",
    outputPath: "输出路径",
    userDataOutput: "用户数据输出目录",
    approval: "审批策略",
    approvalRequired: "执行前必须审批",
    approvalRecommended: "建议手动审查",
    timelineEyebrow: "执行时间线",
    waitingApproval: "等待审批",
    runPrefix: "Run"
  },
  palette: {
    ariaLabel: "命令面板",
    placeholder: "搜索命令",
    commands: [
      { label: "打开工作台", hint: "Prompt Composer 与直接工具", view: "workspace" },
      { label: "打开 Skill 浏览器", hint: "索引 SolidWorks 与 Taste Skill 上下文", view: "skills" },
      { label: "打开执行监控", hint: "执行时间线、stdout 与 stderr", view: "monitor" },
      { label: "打开审查中心", hint: "审查报告与迭代 Prompt", view: "review" },
      { label: "打开设置", hint: "LLM Profile、路径、MCP、主题", view: "settings" },
      { label: "刷新后端状态", hint: "重新读取 health、preflight、skills 与 MCP", action: "refresh" }
    ]
  },
  timeline: {
    ariaLabel: "执行时间线",
    empty: "还没有执行事件。请先生成 Script，审查后再审批执行。"
  },
  skills: {
    eyebrow: "Skill 上下文",
    title: "SolidWorks 自动化能力与 Taste Skill 规范",
    sync: "同步 Skill",
    searchPlaceholder: "搜索零件、装配体、工程图、导出、Motion、审查、MCP",
    solidworksSkill: "SolidWorks Skill",
    tasteSkill: "Taste Skill",
    documentsIndexed: "份文档已索引",
    functionsIndexed: "个 Python 函数",
    mcpToolsIndexed: "个 MCP 工具",
    capabilitiesIndexed: "项能力",
    loadingContext: "正在从 vendor/skills 加载 Skill 上下文。",
    capabilityMatrix: "能力矩阵",
    documents: "文档",
    functions: "函数与 MCP 工具",
    callable: "可调用",
    contextOnly: "仅上下文",
    mcpDescription: "由上游 SolidWorks MCP server 暴露。"
  },
  monitor: {
    eyebrow: "执行监控",
    noActiveRun: "没有活动 Run",
    outputAria: "执行输出",
    noStdout: "尚未捕获 stdout。",
    noStderr: "尚未捕获 stderr。",
    generatedFiles: "生成文件",
    generatedFilesEmpty: "Run 完成后，生成文件会显示在这里。",
    realEvidence: "真实证据",
    noEvidence: "尚未记录可核验的真实执行证据。"
  },
  review: {
    eyebrow: "审查中心",
    title: "几何检查、报告产物与迭代 Prompt",
    copyFixPrompt: "复制修复 Prompt",
    items: ["尺寸", "特征", "导出文件", "错误", "建议"],
    ready: "可审查",
    waiting: "等待 Run",
    previewImages: "预览图",
    previewEmpty: "运行审查后，这里会显示导出的预览图。"
  },
  files: {
    eyebrow: "文件 / 导出",
    title: "最近生成与导出的产物",
    openFolder: "打开文件夹",
    safetyNote: "应用不会删除用户文件。请使用明确输出路径，或使用已配置的用户数据输出目录。",
    byType: "按类型",
    recentPaths: "最近路径",
    empty: "本次会话还没有生成导出文件。",
    realEvidence: "真实证据"
  },
  settings: {
    eyebrow: "设置",
    title: "LLM Provider、路径、MCP 与安全控制",
    save: "保存设置",
    loading: "正在从本地后端加载设置。",
    profile: "Profile",
    llmProfile: "LLM Profile",
    apiBaseUrl: "API Base URL",
    apiKey: "API Key",
    apiKeyPlaceholder: "本地保存，API 响应与日志中会脱敏",
    model: "文本 Model",
    visionModel: "视觉 Model",
    modelPlaceholder: "选择或输入模型名称",
    visionModelPlaceholder: "选择或输入支持 image_url 的视觉模型",
    timeout: "Timeout",
    temperature: "Temperature",
    maxTokens: "Max Tokens",
    testConnection: "测试连接",
    testVisionConnection: "测试视觉",
    testingConnection: "正在测试",
    pathsSafety: "路径与安全",
    solidworksSkillPath: "SolidWorks Skill 路径",
    tasteSkillPath: "Taste Skill 路径",
    outputDirectory: "输出目录",
    validationOutputDirectory: "验证输出目录",
    partTemplatePath: "零件模板路径",
    assemblyTemplatePath: "装配体模板路径",
    drawingTemplatePath: "工程图模板路径",
    requireApproval: "运行生成 Script 前必须审批",
    theme: "主题",
    dark: "深色",
    light: "浅色",
    mcpConfig: "MCP 配置",
    running: "运行中",
    stopped: "已停止",
    start: "启动",
    stop: "停止",
    snippetsLoading: "正在加载 MCP snippets。",
    recommendedBaseUrl: "https://api.ccagent.cn/v1",
    modelOptions: ["glm-5.1", "doubao-seed-2.0-pro", "gpt-4.1", "custom-model", "local-model"]
  },
  backendErrors: {
    refreshFailed: "刷新后端状态失败。",
    runRefreshFailed: "刷新 Run 状态失败。",
    operationFailed: "操作失败。"
  },
  confirmations: {
    syncSkills: "同步 Skill 会跳过有本地改动的仓库。是否继续？"
  },
  reviewPrompt: "请基于最新 SolidWorks 审查结果与执行日志，提出一次修复方案。",
  validation: {
    reportTitle: "安装版 EXE 完整验证报告",
    none: "无"
  }
} as const;

export function stageLabel(stage: RunStage): string {
  return zhCN.stages[stage] ?? stage;
}

export function statusLevelLabel(status: StatusLevel): string {
  return zhCN.statusLevels[status] ?? status;
}

export function modeLabel(mode?: "solidworks" | "mock"): string {
  if (mode === "solidworks") return "SolidWorks";
  if (mode === "mock") return "依赖未满足";
  return "加载中";
}

export function preflightStatusLabel(preflight?: { mode?: "solidworks" | "mock"; can_run_real_com?: boolean; state?: string; stale?: boolean } | null): string {
  if (!preflight) return zhCN.shell.statuses.solidworksChecking;
  if (preflight.state === "timeout-session-ready") return "预检超时，会话可用";
  if (preflight.state === "timeout") return "预检超时";
  if (preflight.stale) return zhCN.shell.statuses.solidworksStale;
  if (preflight.can_run_real_com || preflight.mode === "solidworks") return zhCN.shell.statuses.solidworksReady;
  return zhCN.shell.statuses.blockedMode;
}

export function preflightBadgeStatus(preflight?: { mode?: "solidworks" | "mock"; can_run_real_com?: boolean; state?: string; stale?: boolean } | null): StatusLevel {
  if (!preflight) return "info";
  if (preflight.can_run_real_com || preflight.mode === "solidworks") return preflight.stale ? "warn" : "pass";
  return preflight.stale || preflight.state === "timeout" ? "warn" : "warn";
}

export function realValidationStatusLabel(status: RealValidationStatus): string {
  const labels: Record<RealValidationStatus, string> = {
    untested: "未测试",
    passed: "通过",
    failed: "失败",
    skipped_with_reason: "有原因跳过"
  };
  return labels[status] ?? status;
}

export function executionKindLabel(kind: CapabilityExecutionKind): string {
  const labels: Record<CapabilityExecutionKind, string> = {
    python_script: "Python Script",
    mcp_tool: "MCP Tool",
    prompt_context: "Prompt 上下文",
    documentation_only: "仅文档"
  };
  return labels[kind] ?? kind;
}

export function addinRequirementLabel(addin: AddinRequirement): string {
  const labels: Record<AddinRequirement, string> = {
    none: "无需 Add-in",
    motion: "需要 Motion",
    simulation: "需要 Simulation",
    sheet_metal: "需要 Sheet Metal",
    weldments: "需要 Weldments",
    other: "需要其他 Add-in"
  };
  return labels[addin] ?? addin;
}
