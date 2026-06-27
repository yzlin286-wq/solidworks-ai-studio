import type {
  AIPlanResponse,
  AppConfig,
  ConfigResponse,
  GenerateScriptResponse,
  HealthResponse,
  LLMProfile,
  MCPConfigSnippetsResponse,
  MCPStatusResponse,
  PreflightResponse,
  CapabilityListResponse,
  AICapability,
  AICapabilityListResponse,
  RecipeListResponse,
  RealTestRunResponse,
  RunRecord,
  SkillIndexResponse,
  SolidWorksActionResponse,
  SolidWorksExecutionRecord,
  TestConnectionResponse,
  WorkbenchTask,
  WorkbenchTaskListResponse
} from "./types";

interface BackendInfo {
  baseUrl: string;
  token: string;
  logsDir: string;
}

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

let backendInfoPromise: Promise<BackendInfo> | null = null;
const DEFAULT_TIMEOUT_MS = 30000;

function fallbackBackendInfo(): BackendInfo {
  return {
    baseUrl: import.meta.env.VITE_SWAI_API_URL ?? "http://127.0.0.1:8765",
    token: import.meta.env.VITE_SWAI_API_TOKEN ?? "dev-token",
    logsDir: ""
  };
}

async function waitForBridgeBackendInfo(): Promise<BackendInfo | null> {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (window.swai?.getBackendInfo) {
      return window.swai.getBackendInfo();
    }
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return null;
}

async function backendInfo(): Promise<BackendInfo> {
  if (!backendInfoPromise) {
    backendInfoPromise = waitForBridgeBackendInfo().then((info) => info ?? fallbackBackendInfo());
  }
  return backendInfoPromise;
}

async function request<T>(path: string, method = "GET", body?: JsonValue, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const info = await backendInfo();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${info.baseUrl}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-SWAI-Token": info.token
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(formatHttpError(text, response.status));
    }
    return (await response.json()) as T;
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === "AbortError") {
      throw new Error(`请求超时：${path}`);
    }
    throw caught;
  } finally {
    window.clearTimeout(timeout);
  }
}

function formatHttpError(text: string, status: number): string {
  if (!text) {
    return `Request failed with HTTP ${status}`;
  }
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (parsed.detail && typeof parsed.detail === "object") {
      const detail = parsed.detail as { message?: string; failed_checks?: Array<{ label?: string; message?: string }> };
      const checks = Array.isArray(detail.failed_checks)
        ? detail.failed_checks
            .map((check) => [check.label, check.message].filter(Boolean).join("："))
            .filter(Boolean)
            .slice(0, 3)
        : [];
      return [detail.message, ...checks].filter(Boolean).join("；") || text;
    }
  } catch {
    return text;
  }
  return text;
}

export const api = {
  health: () => request<HealthResponse>("/api/health", "GET", undefined, 15000),
  config: () => request<ConfigResponse>("/api/config", "GET", undefined, 15000),
  saveConfig: (config: AppConfig) => request<ConfigResponse>("/api/config", "POST", config as unknown as JsonValue, 30000),
  testConnection: (profile: LLMProfile) =>
    request<TestConnectionResponse>("/api/llm/test", "POST", { profile: profile as unknown as JsonValue }, (profile.timeout_seconds + 15) * 1000),
  syncSkills: () => request<{ ok: boolean; message: string; solidworks: string; taste: string }>("/api/skills/sync", "POST", {}, 120000),
  skills: () => request<SkillIndexResponse>("/api/skills/index", "GET", undefined, 30000),
  capabilities: () => request<CapabilityListResponse>("/api/skills/capabilities", "GET", undefined, 30000),
  aiCapabilities: () => request<AICapabilityListResponse>("/api/ai-capabilities", "GET", undefined, 30000),
  aiCapability: (capabilityId: string) => request<AICapability>(`/api/ai-capabilities/${encodeURIComponent(capabilityId)}`, "GET", undefined, 30000),
  recipes: () => request<RecipeListResponse>("/api/recipes", "GET", undefined, 30000),
  tasks: () => request<WorkbenchTaskListResponse>("/api/tasks", "GET", undefined, 15000),
  task: (taskId: string) => request<WorkbenchTask>(`/api/tasks/${encodeURIComponent(taskId)}`, "GET", undefined, 15000),
  workbenchPlan: (capabilityId: string, recipeId: string, executionMode: "mock" | "real", prompt = "") =>
    request<WorkbenchTask>(`/api/ai-capabilities/${encodeURIComponent(capabilityId)}/plan`, "POST", {
      recipe_id: recipeId,
      execution_mode: executionMode,
      prompt
    }, 30000),
  workbenchGenerate: (capabilityId: string, taskId: string, parameters: Record<string, JsonValue> = {}) =>
    request<WorkbenchTask>(`/api/ai-capabilities/${encodeURIComponent(capabilityId)}/generate-script`, "POST", {
      task_id: taskId,
      parameters
    }, 30000),
  workbenchValidate: (capabilityId: string, taskId: string) =>
    request<WorkbenchTask>(`/api/ai-capabilities/${encodeURIComponent(capabilityId)}/validate`, "POST", { task_id: taskId }, 30000),
  workbenchApprove: (capabilityId: string, taskId: string) =>
    request<WorkbenchTask>(`/api/ai-capabilities/${encodeURIComponent(capabilityId)}/approve`, "POST", { task_id: taskId }, 30000),
  workbenchExecute: (capabilityId: string, taskId: string, parameters: Record<string, JsonValue> = {}) =>
    request<WorkbenchTask>(`/api/ai-capabilities/${encodeURIComponent(capabilityId)}/execute`, "POST", {
      task_id: taskId,
      parameters
    }, 300000),
  runCapability: (capabilityId: string, parameters: Record<string, JsonValue> = {}, timeoutSeconds = 180) =>
    request<SolidWorksExecutionRecord>(`/api/skills/capabilities/${encodeURIComponent(capabilityId)}/run`, "POST", {
      parameters,
      timeout_seconds: timeoutSeconds
    }, (timeoutSeconds + 20) * 1000),
  preflight: () => request<PreflightResponse>("/api/solidworks/preflight", "GET", undefined, 55000),
  connect: () => request<SolidWorksActionResponse>("/api/solidworks/connect", "POST", {}, 240000),
  openDocument: (pathValue?: string) =>
    request<SolidWorksActionResponse>("/api/solidworks/open", "POST", pathValue ? { path: pathValue } : {}, 240000),
  saveDocument: (pathValue: string) => request<SolidWorksActionResponse>("/api/solidworks/save", "POST", { path: pathValue }, 240000),
  exportActive: (format: string, outputPath: string) =>
    request<SolidWorksActionResponse>("/api/solidworks/export", "POST", { format, output_path: outputPath }, 300000),
  reviewActive: (outputPath: string) =>
    request<SolidWorksActionResponse>("/api/solidworks/review", "POST", { output_path: outputPath }, 240000),
  createBasicPart: (shape: string) =>
    request<SolidWorksActionResponse>("/api/solidworks/create-basic-part", "POST", { parameters: { shape } }, 240000),
  plan: (prompt: string, profileId: string, outputDir: string) =>
    request<AIPlanResponse>("/api/ai/plan", "POST", { prompt, profile_id: profileId, output_dir: outputDir }, 120000),
  generateScript: (prompt: string, profileId: string, outputDir: string) =>
    request<GenerateScriptResponse>("/api/ai/generate-script", "POST", { prompt, profile_id: profileId, output_dir: outputDir }, 120000),
  approveRun: (scriptPath: string, prompt: string) =>
    request<{ run_id: string; stage: string; message: string }>("/api/ai/approve-run", "POST", {
      script_path: scriptPath,
      prompt,
      timeout_seconds: 120
    }, 180000),
  run: (runId: string) => request<RunRecord>(`/api/runs/${runId}`, "GET", undefined, 15000),
  mcpStart: () => request<MCPStatusResponse>("/api/mcp/start", "POST", {}, 60000),
  mcpStop: () => request<MCPStatusResponse>("/api/mcp/stop", "POST", {}, 60000),
  mcpStatus: () => request<MCPStatusResponse>("/api/mcp/status", "GET", undefined, 15000),
  mcpSnippets: () => request<MCPConfigSnippetsResponse>("/api/mcp/config-snippets", "GET", undefined, 15000),
  realTestReport: () => request<RealTestRunResponse>("/api/solidworks/real-test/report", "GET", undefined, 20000),
  realTestRun: () => request<RealTestRunResponse>("/api/solidworks/real-test/run", "POST", {}, 900000)
};
