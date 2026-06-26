import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const exe = process.env.SWAI_INSTALLED_EXE;
const outputRoot = path.join(root, "outputs");
const installedRoot = path.join(outputRoot, "installed_validation", "latest");
const shotDir = path.join(installedRoot, "screenshots");
const validationRoot = path.join(outputRoot, "validation", "latest");
const validationUserData = path.join(installedRoot, "electron-user-data");
const progressPath = path.join(validationRoot, "INSTALLED_EXE_FULL_VALIDATION_PROGRESS.txt");
const installedReportJsonPath = path.join(validationRoot, "INSTALLED_EXE_FULL_VALIDATION_REPORT.json");
const installedReportMdPath = path.join(validationRoot, "INSTALLED_EXE_FULL_VALIDATION_REPORT.md");
const validationApiKey = process.env.SWAI_VALIDATION_API_KEY ?? "";
const validationApiBaseUrl = process.env.SWAI_VALIDATION_API_BASE_URL ?? "";
const validationModel = process.env.SWAI_VALIDATION_MODEL ?? "";

fs.mkdirSync(shotDir, { recursive: true });
fs.mkdirSync(validationRoot, { recursive: true });
fs.rmSync(validationUserData, { recursive: true, force: true });
fs.mkdirSync(validationUserData, { recursive: true });

function markProgress(stage) {
  fs.writeFileSync(progressPath, `${new Date().toISOString()} ${stage}\n`, { encoding: "utf8", flag: "a" });
}
for (const entry of fs.readdirSync(shotDir, { withFileTypes: true })) {
  if (entry.isFile() && entry.name.toLowerCase().endsWith(".png")) {
    fs.unlinkSync(path.join(shotDir, entry.name));
  }
}

function writeInstalledReport(report) {
  fs.writeFileSync(installedReportJsonPath, JSON.stringify(report, null, 2), "utf8");
  fs.writeFileSync(
    installedReportMdPath,
    [
      "# 安装版 EXE 完整验证报告",
      "",
      `生成时间：${report.generated_at}`,
      `安装版 EXE 通过：${report.installed_exe_full_validation_ok}`,
      `安装版 EXE：${report.installed_exe}`,
      `Backend health：${report.backend_health?.ok ?? false}`,
      `真实 SolidWorks 已连接：${report.real_solidworks_connected}`,
      `验证密钥已注入：${report.validation_llm_configured ?? false}`,
      `真实 LLM chat 已验证：${report.llm_connection?.chat_verified ?? false}`,
      `真实 LLM API 复测已验证：${report.llm_connection_api?.chat_verified ?? false}`,
      `计划 demo_mode：${report.natural_language.plan_demo_mode ?? "not_run"}`,
      `脚本 demo_mode：${report.natural_language.generate_demo_mode ?? "not_run"}`,
      `脚本 fallback_used：${report.natural_language.generate_fallback_used ?? "not_run"}`,
      `自然语言真实证据：${report.natural_language.real_execution_verified ?? false}`,
      `自然语言产物存在：${report.natural_language.created_files_exist ?? false}`,
      `自然语言阶段：${report.natural_language.stage ?? "not_run"}`,
      `直接工具按钮：${report.direct_tool_results.filter((item) => item.semantic_ok).length}/${report.direct_tool_results.length}`,
      `Registry 按钮：${report.registry_tool_results.filter((item) => item.semantic_ok).length}/${report.registry_tool_results.length}`,
      `截图：${report.screenshots.length}`,
      "",
      "## Direct Tools",
      ...report.direct_tool_results.map((item) => `- ${item.label}: ${item.semantic_ok ? "通过" : "失败"} (HTTP ${item.status ?? "n/a"}, mode ${item.mode ?? "n/a"}, files ${item.files_exist ?? false}, real_output ${item.real_output_verified ?? false})`),
      "",
      "## Registry Tools",
      ...report.registry_tool_results.map((item) => `- ${item.label}: ${item.semantic_ok ? "通过" : "失败"} (HTTP ${item.status ?? "n/a"}, mode ${item.mode ?? "n/a"}, files ${item.files_exist ?? false}, real_output ${item.real_output_verified ?? false})`),
      ...(report.registry_tool_skipped?.length ? ["", "## Registry Skipped", ...report.registry_tool_skipped.map((item) => `- ${item.label}: ${item.reason}`)] : []),
      "",
      "## Strict Violations",
      ...(report.strict_violations?.length ? report.strict_violations.map((item) => `- ${item}`) : ["- 无"]),
      "",
      "## 错误",
      ...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ["- 无"]),
      "",
    ].join("\n"),
    "utf8",
  );
}

function sanitizeValidationUserData() {
  if (!validationApiKey || !fs.existsSync(validationUserData)) return;
  const stack = [validationUserData];
  while (stack.length) {
    const current = stack.pop();
    let entries = [];
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
        continue;
      }
      if (!entry.isFile()) continue;
      let stat;
      try {
        stat = fs.statSync(fullPath);
      } catch {
        continue;
      }
      if (stat.size > 5_000_000) continue;
      try {
        const text = fs.readFileSync(fullPath, "utf8");
        if (text.includes(validationApiKey)) {
          fs.writeFileSync(fullPath, text.split(validationApiKey).join("[REDACTED_VALIDATION_API_KEY]"), "utf8");
        }
      } catch {
        continue;
      }
    }
  }
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

async function waitForCdp(port, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return await response.json();
    } catch {
      // keep waiting
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for installed Electron CDP on port ${port}`);
}

async function withTimeout(promise, timeoutMs, message) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(message)), timeoutMs);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function pageText(page) {
  return await page.evaluate(() => document.body.innerText.slice(0, 24000));
}

async function snapshot(page, name, expected = []) {
  const filePath = path.join(shotDir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  const text = await pageText(page);
  const viewport = page.viewportSize() ?? { width: 0, height: 0 };
  const assertions = expected.map((item) => ({
    expected: item,
    pass: text.toLowerCase().includes(item.toLowerCase()),
  }));
  return {
    file_path: filePath,
    created_at: new Date().toISOString(),
    page: name,
    screenshot_size: viewport,
    non_blank: fs.statSync(filePath).size > 10_000,
    visible_text_summary: text.slice(0, 1800),
    expected_ui_assertions: assertions,
    pass: fs.statSync(filePath).size > 10_000 && assertions.every((item) => item.pass),
  };
}

async function waitForBackendInfo(page, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const info = await page
      .evaluate(async () => {
        if (!window.swai?.getBackendInfo) return null;
        return await Promise.race([
          window.swai.getBackendInfo(),
          new Promise((resolve) => setTimeout(() => resolve({ timeout: true }), 2500)),
        ]);
      })
      .catch(() => null);
    if (info?.baseUrl && info?.token) return info;
    await page.waitForTimeout(1000);
  }
  return null;
}

async function apiFetch(_page, info, route, options = {}, timeoutMs = 5000, retryAttempts = 30) {
  let response;
  let lastError;
  for (let attempt = 0; attempt < retryAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      response = await fetch(`${info.baseUrl}${route}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "X-SWAI-Token": info.token,
          ...(options.headers ?? {}),
        },
        signal: controller.signal,
      });
      break;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 500));
    } finally {
      clearTimeout(timeout);
    }
  }
  if (!response) {
    throw lastError ?? new Error(`fetch failed for ${route}`);
  }
  let body = null;
  const text = await response.text();
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { text };
  }
  return { ok: response.ok, status: response.status, body };
}

async function waitForResponseAfterClick(page, label, urlPart, report, timeoutMs = 180000) {
  const button = page.getByRole("button", { name: new RegExp(label, "i") }).first();
  const result = {
    label,
    clicked: false,
    visible: false,
    enabled: false,
    status: null,
    ok: false,
    body: null,
    error: "",
  };
  if ((await button.count()) === 0) {
    result.error = "未找到按钮";
    report.button_results.push(result);
    return result;
  }
  result.visible = await button.isVisible().catch(() => false);
  result.enabled = await button.isEnabled().catch(() => false);
  if (!result.visible || !result.enabled) {
    result.error = "按钮不可见或未启用";
    report.button_results.push(result);
    return result;
  }
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes(urlPart),
    { timeout: timeoutMs },
  ).catch((error) => ({ error }));
  await button.click();
  result.clicked = true;
  const response = await responsePromise;
  if (response?.error) {
    result.error = String(response.error?.message ?? response.error);
  } else {
    result.status = response.status();
    result.ok = response.ok();
    result.body = await response.json().catch(async () => ({ text: await response.text().catch(() => "") }));
  }
  report.button_results.push(result);
  await page.waitForTimeout(800);
  return result;
}

async function waitForResponseAfterLocatorClick(page, locator, label, urlPart, report, timeoutMs = 180000) {
  const result = {
    label,
    clicked: false,
    visible: false,
    enabled: false,
    status: null,
    ok: false,
    body: null,
    error: "",
  };
  if ((await locator.count()) === 0) {
    result.error = "未找到按钮";
    report.button_results.push(result);
    return result;
  }
  result.visible = await locator.isVisible().catch(() => false);
  result.enabled = await locator.isEnabled().catch(() => false);
  if (!result.visible || !result.enabled) {
    result.error = "按钮不可见或未启用";
    report.button_results.push(result);
    return result;
  }
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes(urlPart),
    { timeout: timeoutMs },
  ).catch((error) => ({ error }));
  await locator.click();
  result.clicked = true;
  const response = await responsePromise;
  if (response?.error) {
    result.error = String(response.error?.message ?? response.error);
  } else {
    result.status = response.status();
    result.ok = response.ok();
    result.body = await response.json().catch(async () => ({ text: await response.text().catch(() => "") }));
  }
  report.button_results.push(result);
  await page.waitForTimeout(800);
  return result;
}

async function ensureWorkspace(page) {
  const text = await pageText(page);
  if (!text.includes("自动化工作台") || !text.includes("直接工具")) {
    await page.getByRole("button", { name: /^工作台$/i }).click();
    await page.getByRole("heading", { name: /自动化工作台/i }).waitFor({ timeout: 30000 });
    await page.waitForTimeout(500);
  }
}

async function navigateTo(page, navLabel, headingLabel) {
  await page.getByRole("button", { name: new RegExp(`^${navLabel}$`, "i") }).click();
  await page.getByRole("heading", { name: new RegExp(`^${headingLabel}$`, "i") }).waitFor({ timeout: 30000 });
  await page.waitForTimeout(400);
}

async function waitForRunDone(page, info, runId, timeoutMs = 420000) {
  const deadline = Date.now() + timeoutMs;
  let latest = null;
  while (Date.now() < deadline) {
    const response = await apiFetch(page, info, `/api/runs/${runId}`).catch((error) => ({
      ok: false,
      status: 0,
      body: { error: String(error?.message ?? error) },
    }));
    latest = response.body;
    if (response.ok && ["done", "failed"].includes(response.body?.stage)) {
      return response.body;
    }
    await page.waitForTimeout(2000);
  }
  return latest ?? { stage: "timeout" };
}

function actionBodyOk(body) {
  if (!body || typeof body !== "object") return false;
  if ("ok" in body) return Boolean(body.ok);
  if ("status" in body) return String(body.status).toLowerCase() === "passed";
  return true;
}

function preflightBodyConnected(body) {
  return Boolean(body?.can_run_real_com || body?.mode === "solidworks");
}

function llmConnectionOk(body) {
  return Boolean(body?.ok && body?.chat_verified);
}

function filesFromActionBody(body) {
  const files = [];
  if (!body || typeof body !== "object") return files;
  if (Array.isArray(body.files)) files.push(...body.files);
  const data = body.data && typeof body.data === "object" ? body.data : {};
  for (const key of ["path", "output_path", "drawing_path", "report_path"]) {
    if (typeof data[key] === "string") files.push(data[key]);
  }
  for (const key of ["files", "created_files"]) {
    if (Array.isArray(data[key])) files.push(...data[key]);
  }
  return [...new Set(files.map((item) => String(item)).filter(Boolean))];
}

function filesFromRecordBody(body) {
  if (!body || typeof body !== "object") return [];
  return [...new Set([...(Array.isArray(body.created_files) ? body.created_files : [])].map((item) => String(item)).filter(Boolean))];
}

function existingFiles(files) {
  return files.filter((filePath) => {
    try {
      return fs.existsSync(filePath) && fs.statSync(filePath).isFile();
    } catch {
      return false;
    }
  });
}

function directToolRequiresFile(label) {
  return /打开|保存|导出|审查|创建|新建/.test(label);
}

function registryToolRequiresFile(label) {
  return /open|save|export|review|create_basic_part|打开|保存|导出|审查|创建基础/i.test(label);
}

function annotateSolidWorksActionResult(result, route) {
  if (route.includes("/api/solidworks/preflight")) {
    result.mode = result.body?.mode ?? null;
    result.files_checked = [];
    result.files_exist = false;
    result.real_output_verified = preflightBodyConnected(result.body);
    return result.ok && result.real_output_verified;
  }
  if (route.includes("/api/mcp/")) {
    result.mode = "mcp";
    result.files_checked = [];
    result.files_exist = false;
    result.real_output_verified = Boolean(result.ok && actionBodyOk(result.body));
    return result.real_output_verified;
  }
  const files = filesFromActionBody(result.body);
  const found = existingFiles(files);
  result.mode = result.body?.mode ?? null;
  result.files_checked = files;
  result.files_exist = found.length > 0;
  result.real_execution_verified = Boolean(result.body?.real_execution_verified);
  result.evidence = result.body?.evidence ?? null;
  result.real_output_verified = directToolRequiresFile(result.label)
    ? result.files_exist && result.real_execution_verified
    : result.real_execution_verified;
  return Boolean(
    result.ok &&
      result.body?.ok &&
      result.body?.mode === "solidworks" &&
      result.real_execution_verified &&
      result.real_output_verified,
  );
}

function annotateRegistryResult(result, realSolidWorksConnected) {
  const files = filesFromRecordBody(result.body);
  const found = existingFiles(files);
  result.mode = realSolidWorksConnected ? "solidworks" : "blocked";
  result.files_checked = files;
  result.files_exist = found.length > 0;
  result.real_execution_verified = Boolean(result.body?.real_execution_verified);
  result.evidence = result.body?.evidence ?? null;
  result.real_output_verified = registryToolRequiresFile(result.label)
    ? result.files_exist && result.real_execution_verified
    : result.real_execution_verified;
  return Boolean(
    realSolidWorksConnected &&
      result.ok &&
      String(result.body?.status ?? "").toLowerCase() === "passed" &&
      result.real_execution_verified &&
      result.real_output_verified,
  );
}

function runtimeStrictViolations(report, visibleText = "") {
  const violations = [];
  if (report.natural_language?.plan_demo_mode !== false) violations.push("plan demo_mode is not false");
  if (report.natural_language?.generate_demo_mode !== false) violations.push("generate demo_mode is not false");
  if (report.natural_language?.generate_fallback_used !== false) violations.push("generate fallback_used is not false");
  if (report.natural_language?.real_execution_verified !== true) violations.push("natural language run lacks real_execution_verified=true");
  if (report.natural_language?.created_files_exist !== true) violations.push("natural language run lacks created_files_exist=true");
  for (const item of [...report.direct_tool_results, ...report.registry_tool_results]) {
    if (item.mode === "mock") violations.push(`${item.label} returned mode=mock`);
    if (item.status === 424 || item.status >= 500) violations.push(`${item.label} returned HTTP ${item.status}`);
    if (item.semantic_ok && item.real_execution_verified === false) violations.push(`${item.label} passed without real execution evidence`);
  }
  const forbiddenVisible = ["API 在线", "API 已连接", "Mock/Demo"];
  for (const token of forbiddenVisible) {
    if (visibleText.includes(token)) violations.push(`visible UI still contains ${token}`);
  }
  const serialized = JSON.stringify(report);
  if (serialized.includes('"demo_mode":true')) violations.push("report contains demo_mode=true");
  if (serialized.includes('"fallback_used":true')) violations.push("report contains fallback_used=true");
  if (serialized.includes('"mode":"mock"')) violations.push("report contains mode=mock");
  if (serialized.includes("Mock/Demo")) violations.push("report contains Mock/Demo text");
  return violations;
}

async function configureValidationLlm(page, info, report) {
  if (!validationApiKey) {
    report.validation_llm_configured = false;
    return;
  }
  const configResponse = await apiFetch(page, info, "/api/config", {}, 15000, 1);
  const config = configResponse.body?.config;
  if (!config?.profiles?.length) {
    report.errors.push("无法读取本机 LLM 配置，跳过验证密钥注入。");
    report.validation_llm_configured = false;
    return;
  }
  const selected = config.active_profile_id || "ccagent";
  config.profiles = config.profiles.map((profile) =>
    profile.id === selected
      ? {
          ...profile,
          api_base_url: validationApiBaseUrl || profile.api_base_url || "https://api.ccagent.cn/v1",
          api_key: validationApiKey,
          model: validationModel || profile.model || "glm-5.1",
          max_tokens: Math.max(Number(profile.max_tokens || 0), 8192),
          timeout_seconds: Math.max(Number(profile.timeout_seconds || 0), 180),
        }
      : profile,
  );
  const saved = await apiFetch(
    page,
    info,
    "/api/config",
    {
      method: "POST",
      body: JSON.stringify(config),
    },
    30000,
    1,
  );
  report.validation_llm_configured = Boolean(saved.ok);
}

async function main() {
  if (!exe || !fs.existsSync(exe)) {
    throw new Error(`未找到已安装 EXE：${exe ?? "<unset>"}`);
  }
  fs.writeFileSync(progressPath, "", "utf8");
  markProgress("main:start");
  const port = await freePort();
  markProgress(`port:${port}`);
  const child = spawn(exe, [`--remote-debugging-port=${port}`, "--disable-gpu", `--user-data-dir=${validationUserData}`], {
    cwd: path.dirname(exe),
    env: { ...process.env, SWAI_OUTPUT_DIR: outputRoot },
    stdio: "ignore",
    detached: false,
    windowsHide: true,
  });
  const report = {
    installed_exe_full_validation_ok: false,
    generated_at: new Date().toISOString(),
    installed_exe: exe,
    install_location: path.dirname(exe),
    pid: child.pid,
    cdp_port: port,
    backend_health: null,
    solidworks_preflight: null,
    screenshots: [],
    button_results: [],
    direct_tool_results: [],
    registry_tool_results: [],
    registry_tool_skipped: [],
    natural_language: {},
    llm_connection: null,
    llm_connection_api: null,
    validation_llm_configured: false,
    real_solidworks_connected: false,
    api_key_masked_input_count: 0,
    strict_violations: [],
    errors: [],
  };
  let browser;
  try {
    markProgress("waitForCdp:start");
    const version = await waitForCdp(port);
    markProgress("waitForCdp:done");
    browser = await withTimeout(
      chromium.connectOverCDP(version.webSocketDebuggerUrl),
      30000,
      "Timed out connecting Playwright over CDP.",
    );
    markProgress("connectOverCDP:done");
    const context = browser.contexts()[0];
    let [page] = context.pages();
    if (!page) page = await context.waitForEvent("page", { timeout: 30000 });
    markProgress("page:ready");
    await page.setViewportSize({ width: 1480, height: 940 });
    await page.waitForLoadState("domcontentloaded");
    markProgress("domcontentloaded");
    await page.getByRole("heading", { name: "SolidWorks AI Studio" }).waitFor({ timeout: 60000 });
    markProgress("heading:ready");
    page.on("dialog", async (dialog) => {
      report.button_results.push({ label: `dialog:${dialog.type()}`, clicked: true, ok: true, message: dialog.message() });
      await dialog.accept().catch(() => {});
    });

    const backendInfo = await waitForBackendInfo(page);
    if (!backendInfo) throw new Error("Installed app did not expose backend bridge.");
    markProgress(`backendInfo:${backendInfo.baseUrl}`);
    report.backend_health = await apiFetch(page, backendInfo, "/api/health");
    markProgress("health:done");
    await configureValidationLlm(page, backendInfo, report);
    markProgress("validation-llm-config:done");
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: "SolidWorks AI Studio" }).waitFor({ timeout: 60000 });
    markProgress("ui-reloaded-after-llm-config");
    report.solidworks_preflight = await apiFetch(page, backendInfo, "/api/solidworks/preflight", {}, 60000, 1).catch((error) => {
      report.errors.push(`初始 preflight 预读失败，后续按钮验证继续：${String(error?.message ?? error)}`);
      return null;
    });
    markProgress("preflight:done");
    report.real_solidworks_connected = preflightBodyConnected(report.solidworks_preflight?.body);
    writeInstalledReport(report);

    await waitForResponseAfterClick(page, "刷新检查", "/api/solidworks/preflight", report, 90000);
    report.screenshots.push(await snapshot(page, "01-installed-onboarding", ["SolidWorks AI Studio", "运行前自检", "真实验证"]));
    await page.getByRole("button", { name: /进入工作台/i }).click();
    await page.getByRole("heading", { name: /自动化工作台/i }).waitFor({ timeout: 30000 });
    report.button_results.push({ label: "进入工作台", clicked: true, ok: true });
    report.screenshots.push(await snapshot(page, "02-installed-workspace", ["自动化工作台", "直接工具"]));

    await page.getByRole("button", { name: /Ctrl K/i }).click();
    await page.getByRole("dialog", { name: /命令面板/i }).waitFor({ timeout: 10000 });
    report.screenshots.push(await snapshot(page, "03-command-palette", ["打开设置", "刷新后端状态"]));
    await page.getByRole("button", { name: /打开工作台/i }).click();
    report.button_results.push({ label: "命令面板 打开工作台", clicked: true, ok: true });

    await navigateTo(page, "设置", "设置");
    await page.locator('input[type="password"]').first().waitFor({ timeout: 30000 });
    report.api_key_masked_input_count = await page.locator('input[type="password"]').count();
    const initialTestConnection = await waitForResponseAfterClick(page, "测试连接", "/api/llm/test", report, 120000);
    initialTestConnection.semantic_ok = initialTestConnection.ok && llmConnectionOk(initialTestConnection.body);
    report.llm_connection = initialTestConnection.body ?? null;
    report.screenshots.push(await snapshot(page, "04-llm-verified-before-generation", ["本地后端在线", "LLM 已验证", "设置"]));
    await ensureWorkspace(page);

    const prompt =
      "新建一个 120 x 80 x 10 mm 安装板，四角各打 M6 通孔，倒角 1 mm，保存为 SLDPRT 并导出 STEP。";
    await page.locator("textarea").first().fill(prompt);
    const plan = await waitForResponseAfterClick(page, "^规划$", "/api/ai/plan", report, 240000);
    report.natural_language.plan_status = plan.status;
    report.natural_language.plan_demo_mode = plan.body?.demo_mode ?? null;
    report.natural_language.plan_provider_verified_at = plan.body?.provider_verified_at ?? null;
    markProgress("llm-plan:done");
    const generate = await waitForResponseAfterClick(page, "生成 Script", "/api/ai/generate-script", report, 240000);
    report.natural_language.generate_status = generate.status;
    report.natural_language.generate_demo_mode = generate.body?.demo_mode ?? null;
    report.natural_language.generate_fallback_used = generate.body?.fallback_used ?? null;
    report.natural_language.generate_fallback_reason = generate.body?.fallback_reason ?? "";
    report.natural_language.generate_provider_verified_at = generate.body?.provider_verified_at ?? null;
    markProgress("llm-generate:done");
    report.screenshots.push(await snapshot(page, "05-script-generated", ["Script 预览", "审批并执行"]));
    const approve = await waitForResponseAfterClick(page, "审批并执行", "/api/ai/approve-run", report, 90000);
    report.natural_language.approve_status = approve.status;
    report.natural_language.run_id = approve.body?.run_id ?? null;
    if (approve.body?.run_id) {
      const terminal = await waitForRunDone(page, backendInfo, approve.body.run_id);
      report.natural_language.stage = terminal?.stage ?? "unknown";
      report.natural_language.files = terminal?.files ?? [];
      report.natural_language.real_execution_verified = terminal?.real_execution_verified ?? false;
      report.natural_language.evidence = terminal?.evidence ?? null;
      report.natural_language.created_files_exist = Boolean(terminal?.evidence?.created_files_exist);
      report.natural_language.stdout_tail = String(terminal?.stdout ?? "").slice(-2000);
      report.natural_language.stderr_tail = String(terminal?.stderr ?? "").slice(-2000);
      if (terminal?.stage === "done") {
        await page.getByText("已完成").first().waitFor({ timeout: 12000 }).catch(() => {});
      }
    }
    report.screenshots.push(await snapshot(page, "06-natural-language-done", ["执行监控", "已完成", "真实证据"]));
    writeInstalledReport(report);
    await ensureWorkspace(page);

    const directTools = [
      ["健康检查", "/api/solidworks/preflight"],
      ["连接 SolidWorks", "/api/solidworks/connect"],
      ["打开文档", "/api/solidworks/open"],
      ["保存文档", "/api/solidworks/save"],
      ["导出 STEP", "/api/solidworks/export"],
      ["导出 STL", "/api/solidworks/export"],
      ["导出 PDF", "/api/solidworks/export"],
      ["导出 DXF", "/api/solidworks/export"],
      ["导出 DWG", "/api/solidworks/export"],
      ["审查当前文档", "/api/solidworks/review"],
      ["创建基础零件", "/api/solidworks/create-basic-part"],
      ["新建零件", "/api/solidworks/create-basic-part"],
      ["启动 MCP Server", "/api/mcp/start"],
      ["停止 MCP Server", "/api/mcp/stop"],
    ];
    let consecutiveDirectFailures = 0;
    for (const [label, route] of directTools) {
      await ensureWorkspace(page);
      const locator = page.locator(".tool-grid button").filter({ hasText: label }).first();
      const result = await waitForResponseAfterLocatorClick(page, locator, label, route, report, 90000);
      result.semantic_ok = annotateSolidWorksActionResult(result, route);
      if (label === "健康检查" && result.semantic_ok) {
        report.real_solidworks_connected = preflightBodyConnected(result.body);
      }
      report.direct_tool_results.push(result);
      consecutiveDirectFailures = result.semantic_ok ? 0 : consecutiveDirectFailures + 1;
      writeInstalledReport(report);
      if (consecutiveDirectFailures >= 3) {
        report.errors.push("Direct Tools 连续失败，提前结束后续直接工具点击以保留诊断报告。");
        break;
      }
    }
    await ensureWorkspace(page);
    report.screenshots.push(await snapshot(page, "07-direct-tools-after-clicks", ["最近一次直接操作", "直接工具", "真实证据"]));
    markProgress("direct-tools:done");

    await ensureWorkspace(page);
    if (!report.real_solidworks_connected) {
      report.errors.push("真实 SolidWorks 未连接，跳过 Registry-backed 工具点击以避免重复 COM 超时。");
    } else {
      const registryButtonCount = await page.locator(".registry-tool-list button").count();
      let consecutiveRegistryFailures = 0;
      for (let index = 0; index < registryButtonCount; index += 1) {
        await ensureWorkspace(page);
        const locator = page.locator(".registry-tool-list button").nth(index);
        const label =
          (await locator.locator("span").first().textContent().catch(() => ""))?.replace(/\s+/g, " ").trim() ||
          `registry-${index}`;
        if (/关闭文档|close documents/i.test(label)) {
          report.registry_tool_skipped.push({ label, reason: "destructive close-documents tool is skipped during installed validation" });
          continue;
        }
        const result = await waitForResponseAfterLocatorClick(page, locator, label, "/api/skills/capabilities/", report, 240000);
        result.semantic_ok = annotateRegistryResult(result, report.real_solidworks_connected);
        report.registry_tool_results.push(result);
        consecutiveRegistryFailures = result.semantic_ok ? 0 : consecutiveRegistryFailures + 1;
        writeInstalledReport(report);
        if (consecutiveRegistryFailures >= 2) {
          report.errors.push("Registry 工具连续失败，提前结束后续 Registry 点击以保留诊断报告。");
          break;
        }
      }
    }
    markProgress("registry-tools:done");

    await navigateTo(page, "Skill", "Skill 浏览器");
    const sync = await waitForResponseAfterClick(page, "同步 Skill", "/api/skills/sync", report, 240000);
    sync.semantic_ok = sync.ok;
    report.screenshots.push(await snapshot(page, "08-skills-after-sync", ["Skill 浏览器", "能力矩阵"]));

    await navigateTo(page, "执行", "执行监控");
    await page.getByRole("button", { name: /^stdout$/i }).click();
    report.button_results.push({ label: "stdout tab", clicked: true, ok: true });
    await page.getByRole("button", { name: /^stderr$/i }).click();
    report.button_results.push({ label: "stderr tab", clicked: true, ok: true });
    report.screenshots.push(await snapshot(page, "09-monitor-tabs", ["执行监控", "stderr", "真实证据"]));

    await navigateTo(page, "审查", "审查中心");
    await page.getByRole("button", { name: /复制修复 Prompt/i }).click();
    report.button_results.push({ label: "复制修复 Prompt", clicked: true, ok: true });
    report.screenshots.push(await snapshot(page, "10-review-copy", ["审查中心", "review_report.json"]));

    await navigateTo(page, "文件", "文件与导出");
    const openFolder = page.getByRole("button", { name: /打开文件夹/i });
    report.button_results.push({
      label: "打开文件夹",
      clicked: false,
      ok: await openFolder.isDisabled().catch(() => false),
      disabled_expected: true,
    });
    report.screenshots.push(await snapshot(page, "11-files-page", ["文件与导出", "最近路径", "真实证据"]));

    await navigateTo(page, "设置", "设置");
    await page.locator('input[type="password"]').first().waitFor({ timeout: 30000 });
    report.api_key_masked_input_count = await page.locator('input[type="password"]').count();
    const testConnection = await waitForResponseAfterClick(page, "测试连接", "/api/llm/test", report, 120000);
    testConnection.semantic_ok = testConnection.ok && llmConnectionOk(testConnection.body);
    report.llm_connection = testConnection.body ?? null;
    const currentConfig = await apiFetch(page, backendInfo, "/api/config", {}, 15000, 1).catch(() => null);
    const activeProfileId = currentConfig?.body?.config?.active_profile_id;
    const activeProfile = currentConfig?.body?.config?.profiles?.find((profile) => profile.id === activeProfileId) ?? currentConfig?.body?.config?.profiles?.[0];
    if (activeProfile) {
      const apiConnection = await apiFetch(
        page,
        backendInfo,
        "/api/llm/test",
        {
          method: "POST",
          body: JSON.stringify({ profile: activeProfile }),
        },
        120000,
        1,
      ).catch((error) => ({ ok: false, status: 0, body: { error: String(error?.message ?? error) } }));
      report.llm_connection_api = apiConnection.body ?? null;
    }
    markProgress("llm-test:done");
    const saveSettings = await waitForResponseAfterClick(page, "保存设置", "/api/config", report, 90000);
    saveSettings.semantic_ok = saveSettings.ok;
    const settingsMcpStart = await waitForResponseAfterClick(page, "^启动$", "/api/mcp/start", report, 90000);
    settingsMcpStart.semantic_ok = settingsMcpStart.ok;
    const settingsMcpStop = await waitForResponseAfterClick(page, "^停止$", "/api/mcp/stop", report, 90000);
    settingsMcpStop.semantic_ok = settingsMcpStop.ok;
    await page.getByRole("button", { name: /^浅色$/i }).click();
    report.button_results.push({ label: "浅色主题", clicked: true, ok: true });
    await page.getByRole("button", { name: /^深色$/i }).click();
    report.button_results.push({ label: "深色主题", clicked: true, ok: true });
    report.screenshots.push(await snapshot(page, "12-settings-buttons", ["设置", "MCP 配置", "API Key"]));

    const failedButtons = [...report.direct_tool_results, ...report.registry_tool_results].filter((item) => item.semantic_ok === false);
    const visibleText = await pageText(page).catch(() => "");
    report.strict_violations = runtimeStrictViolations(report, visibleText);
    report.installed_exe_full_validation_ok =
      Boolean(report.backend_health?.ok) &&
      report.real_solidworks_connected &&
      llmConnectionOk(report.llm_connection) &&
      llmConnectionOk(report.llm_connection_api) &&
      report.natural_language.plan_demo_mode === false &&
      report.natural_language.generate_demo_mode === false &&
      report.natural_language.generate_fallback_used === false &&
      report.natural_language.stage === "done" &&
      report.natural_language.real_execution_verified === true &&
      report.natural_language.created_files_exist === true &&
      report.api_key_masked_input_count > 0 &&
      report.screenshots.length >= 10 &&
      report.screenshots.every((item) => item.non_blank) &&
      failedButtons.length === 0 &&
      report.strict_violations.length === 0;
  } catch (error) {
    report.errors.push(String(error?.stack ?? error));
    writeInstalledReport(report);
  } finally {
    if (browser) await browser.close().catch(() => {});
    sanitizeValidationUserData();
    writeInstalledReport(report);
    if (child.pid) {
      await new Promise((resolve) => {
        const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
        killer.on("close", resolve);
        setTimeout(resolve, 10000);
      });
    }
  }

  writeInstalledReport(report);
  console.log(JSON.stringify({ installed_exe_full_validation_ok: report.installed_exe_full_validation_ok, report: installedReportJsonPath }, null, 2));
  if (!report.installed_exe_full_validation_ok) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
