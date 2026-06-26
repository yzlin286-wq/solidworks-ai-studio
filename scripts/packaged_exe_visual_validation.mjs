import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const visualRoot = path.join(root, "outputs", "visual_validation", "latest");
const appShotDir = path.join(visualRoot, "screenshots", "app");
const validationRoot = path.join(root, "outputs", "validation", "latest");
const exe = path.join(root, "dist", "win-unpacked", "SolidWorks AI Studio.exe");
const validationApiKey = process.env.SWAI_VALIDATION_API_KEY ?? "";
const validationApiBaseUrl = process.env.SWAI_VALIDATION_API_BASE_URL ?? "";
const validationModel = process.env.SWAI_VALIDATION_MODEL ?? "";
fs.mkdirSync(appShotDir, { recursive: true });
fs.mkdirSync(validationRoot, { recursive: true });
for (const entry of fs.readdirSync(appShotDir, { withFileTypes: true })) {
  if (entry.isFile() && entry.name.toLowerCase().endsWith(".png")) {
    fs.unlinkSync(path.join(appShotDir, entry.name));
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

async function waitForCdp(port, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) {
        return await response.json();
      }
    } catch {
      // keep waiting
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for Electron CDP on port ${port}`);
}

async function pageText(page) {
  return await page.evaluate(() => document.body.innerText.slice(0, 20000));
}

async function snapshot(page, name, expectedText = []) {
  const filePath = path.join(appShotDir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  const text = await pageText(page);
  const viewport = page.viewportSize() ?? await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
  const assertions = expectedText.map((expected) => ({
    expected,
    pass: text.toLowerCase().includes(expected.toLowerCase()),
  }));
  return {
    file_path: filePath,
    created_at: new Date().toISOString(),
    page: name,
    app_mode: text.includes("SolidWorks 模式") || text.includes("真实 COM 通道") || text.includes("SolidWorks 就绪") ? "real" : "unknown",
    screenshot_size: viewport,
    pixel_variance: null,
    non_blank: fs.statSync(filePath).size > 10_000,
    visible_text_summary: text.slice(0, 1200),
    expected_ui_assertions: assertions,
    pass: fs.statSync(filePath).size > 10_000 && assertions.every((item) => item.pass),
  };
}

async function clickNav(page, label) {
  await page.locator(".nav-rail").getByRole("button", { name: new RegExp(`^${label}$`, "i") }).click();
  await page.waitForTimeout(900);
}

async function waitForBackendInfo(page, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const info = await page
      .evaluate(async () => {
        if (!window.swai?.getBackendInfo) {
          return null;
        }
        return await Promise.race([
          window.swai.getBackendInfo(),
          new Promise((resolve) => setTimeout(() => resolve({ timeout: true }), 2500)),
        ]);
      })
      .catch(() => null);
    if (info?.baseUrl && info?.token) {
      return info;
    }
    await page.waitForTimeout(1000);
  }
  return null;
}

async function waitForBackendHealth(page, backendInfo, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const health = await page.evaluate(async (info) => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000);
        try {
          const response = await fetch(`${info.baseUrl}/api/health`, {
            headers: { "X-SWAI-Token": info.token },
            signal: controller.signal,
          });
          return { ok: response.ok, status: response.status, body: await response.json() };
        } finally {
          clearTimeout(timeout);
        }
      }, backendInfo);
      if (health.ok) {
        return health;
      }
      lastError = `HTTP ${health.status}`;
    } catch (error) {
      lastError = String(error?.message ?? error);
    }
    await page.waitForTimeout(1000);
  }
  return { ok: false, status: 0, error: lastError ?? "backend health timeout" };
}

async function apiFetch(page, backendInfo, route, options = {}) {
  return await page.evaluate(async ({ info, routeValue, requestOptions }) => {
    const response = await fetch(`${info.baseUrl}${routeValue}`, {
      ...requestOptions,
      headers: {
        "Content-Type": "application/json",
        "X-SWAI-Token": info.token,
        ...(requestOptions.headers || {}),
      },
    });
    return { ok: response.ok, status: response.status, body: await response.json().catch(async () => ({ text: await response.text() })) };
  }, { info: backendInfo, routeValue: route, requestOptions: options });
}

async function configureValidationLlm(page, backendInfo, report) {
  if (!validationApiKey) {
    report.validation_llm_configured = false;
    report.errors.push("缺少 SWAI_VALIDATION_API_KEY，严格视觉验证无法执行真实 LLM 生成。");
    return false;
  }
  const configResponse = await apiFetch(page, backendInfo, "/api/config");
  const config = configResponse.body?.config;
  if (!config?.profiles?.length) {
    report.validation_llm_configured = false;
    report.errors.push("无法读取本地 LLM 配置。");
    return false;
  }
  const selected = config.active_profile_id || config.profiles[0].id;
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
  const saved = await apiFetch(page, backendInfo, "/api/config", { method: "POST", body: JSON.stringify(config) });
  report.validation_llm_configured = Boolean(saved.ok);
  return Boolean(saved.ok);
}

async function fetchRunRecord(page, backendInfo, runId) {
  return await page.evaluate(async ({ info, id }) => {
    const response = await fetch(`${info.baseUrl}/api/runs/${id}`, {
      headers: { "X-SWAI-Token": info.token },
    });
    return { ok: response.ok, status: response.status, body: await response.json() };
  }, { info: backendInfo, id: runId });
}

async function waitForRunTerminal(page, backendInfo, runId, timeoutMs = 360000) {
  const deadline = Date.now() + timeoutMs;
  let latest = null;
  while (Date.now() < deadline) {
    const response = await fetchRunRecord(page, backendInfo, runId).catch((error) => ({
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
  return latest ?? { stage: "timeout", files: [] };
}

async function clickIfVisible(page, label, report) {
  const button = page.getByRole("button", { name: new RegExp(label, "i") }).first();
  if ((await button.count()) === 0) {
    report.errors.push(`未找到按钮：${label}`);
    return false;
  }
  if (!(await button.isVisible().catch(() => false))) {
    report.errors.push(`按钮不可见：${label}`);
    return false;
  }
  await button.click();
  await page.waitForTimeout(500);
  return true;
}

async function waitForPostAfterClick(page, locator, label, urlPart, timeoutMs) {
  const result = {
    label,
    clicked: false,
    ok: false,
    status: null,
    body: null,
    error: "",
  };
  const responsePromise = page
    .waitForResponse(
      (response) => response.url().includes(urlPart) && response.request().method() === "POST",
      { timeout: timeoutMs },
    )
    .catch((error) => ({ error }));
  try {
    await locator.click();
    result.clicked = true;
  } catch (error) {
    result.error = `点击失败：${String(error?.message ?? error)}`;
    await responsePromise.catch(() => null);
    return result;
  }
  const response = await responsePromise;
  if (response?.error) {
    result.error = String(response.error?.message ?? response.error);
    return result;
  }
  result.status = response.status();
  result.ok = response.ok();
  result.body = await response.json().catch(async () => ({ text: await response.text().catch(() => "") }));
  return result;
}

async function main() {
  if (!fs.existsSync(exe)) {
    throw new Error(`未找到打包桌面 EXE：${exe}`);
  }
  const port = await freePort();
  const child = spawn(exe, [`--remote-debugging-port=${port}`], {
    cwd: path.dirname(exe),
    env: { ...process.env, SWAI_OUTPUT_DIR: path.join(root, "outputs") },
    stdio: "ignore",
    detached: false,
    windowsHide: true,
  });
  const report = {
    packaged_exe_ok: false,
    generated_at: new Date().toISOString(),
    executable: exe,
    pid: child.pid,
    cdp_port: port,
    backend_health: null,
    screenshots: [],
    errors: [],
    child_process_started: Boolean(child.pid),
    natural_language_ui_run_attempted: false,
    natural_language_ui_run_completed: false,
  };
  let browser;
  try {
    const version = await waitForCdp(port);
    browser = await chromium.connectOverCDP(version.webSocketDebuggerUrl);
    const context = browser.contexts()[0];
    let [page] = context.pages();
    if (!page) {
      page = await context.waitForEvent("page", { timeout: 30000 });
    }
    await page.setViewportSize({ width: 1480, height: 940 });
    await page.waitForLoadState("domcontentloaded");
    await page.getByRole("heading", { name: "SolidWorks AI Studio" }).waitFor({ timeout: 60000 });

    const backendInfo = await waitForBackendInfo(page);
    report.backend_bridge_exposed = Boolean(backendInfo?.baseUrl && backendInfo?.token);
    if (backendInfo?.baseUrl && backendInfo?.token) {
      report.backend_health = await waitForBackendHealth(page, backendInfo);
      await configureValidationLlm(page, backendInfo, report);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.getByRole("heading", { name: "SolidWorks AI Studio" }).waitFor({ timeout: 60000 });
      await page.getByRole("button", { name: /刷新检查/i }).click().catch(() => {});
      await page.waitForTimeout(2500);
    } else {
      report.errors.push("打包版 Electron 未暴露 window.swai backend bridge。");
    }

    report.screenshots.push(await snapshot(page, "01-onboarding-welcome", ["SolidWorks AI Studio", "运行前自检", "真实验证"]));
    await page.getByRole("button", { name: /进入工作台/i }).click();
    await page.getByRole("heading", { name: /自动化工作台/i }).waitFor({ timeout: 30000 });
    report.screenshots.push(await snapshot(page, "02-main-workspace", ["自动化工作台", "直接工具", "执行时间线"]));
    report.screenshots.push(await snapshot(page, "03-direct-tools-capabilities", ["Registry-backed 工具", "导出 DWG"]));

    await clickNav(page, "设置");
    await page.getByRole("heading", { name: /设置/i }).waitFor({ timeout: 30000 });
    await page.locator('input[type="password"]').first().waitFor({ timeout: 60000 }).catch(() => {});
    report.api_key_masked_input_count = await page.locator('input[type="password"]').count();
    const testConnection = await waitForPostAfterClick(
      page,
      page.getByRole("button", { name: /测试连接/i }),
      "测试连接",
      "/api/llm/test",
      120000,
    );
    report.llm_connection = testConnection.body ?? null;
    report.llm_connection_ok = Boolean(testConnection.ok && testConnection.body?.ok && testConnection.body?.chat_verified);
    if (!report.llm_connection_ok) {
      report.errors.push(`LLM 测试连接失败：${testConnection.error || `HTTP ${testConnection.status ?? "n/a"}`}`);
    }
    report.screenshots.push(await snapshot(page, "04-llm-verified", ["本地后端在线", "LLM 已验证", "设置"]));
    await clickNav(page, "工作台");

    const nlPrompt =
      "新建一个 120 x 80 x 10 mm 安装板，四角各打 M6 通孔，倒角 1 mm，保存为 SLDPRT 并导出 STEP。";
    await page.locator("textarea").first().fill(nlPrompt);
    report.natural_language_ui_run_attempted = true;
    const generateResult = await waitForPostAfterClick(
      page,
      page.getByRole("button", { name: /生成 Script/i }),
      "生成 Script",
      "/api/ai/generate-script",
      240000,
    );
    report.natural_language_generate_status = generateResult.status;
    if (!generateResult.ok) {
      report.errors.push(`生成 Script 失败：${generateResult.error || `HTTP ${generateResult.status ?? "n/a"}`}`);
    }
    await page.getByText(/真实 Provider|非真实生成已拒绝/i).first().waitFor({ timeout: 30000 }).catch(() => {});
    report.screenshots.push(await snapshot(page, "05-approve-run-generated-state", ["Script 预览", "审批并执行"]));

    const approveButton = page.getByRole("button", { name: /审批并执行/i });
    await approveButton.waitFor({ state: "visible", timeout: 30000 });
    const approveResult = await waitForPostAfterClick(page, approveButton, "审批并执行", "/api/ai/approve-run", 60000);
    report.natural_language_approve_status = approveResult.status;
    if (!approveResult.ok) {
      report.errors.push(`审批并执行失败：${approveResult.error || `HTTP ${approveResult.status ?? "n/a"}`}`);
    }
    const approvePayload = approveResult.body;
    report.natural_language_ui_run_id = approvePayload?.run_id ?? null;
    report.screenshots.push(await snapshot(page, "06-loading-running-state", ["执行时间线", "Run"]));
    if (backendInfo && approvePayload?.run_id) {
      const terminalRun = await waitForRunTerminal(page, backendInfo, approvePayload.run_id);
      report.natural_language_ui_run_stage = terminalRun?.stage ?? "unknown";
      report.natural_language_ui_run_completed = terminalRun?.stage === "done";
      report.natural_language_ui_run_files = terminalRun?.files ?? [];
      report.natural_language_ui_run_real_execution_verified = terminalRun?.real_execution_verified ?? false;
      report.natural_language_ui_run_evidence = terminalRun?.evidence ?? null;
      report.natural_language_ui_run_created_files_exist = Boolean(terminalRun?.evidence?.created_files_exist);
      report.natural_language_ui_run_stdout_tail = String(terminalRun?.stdout ?? "").slice(-2000);
      report.natural_language_ui_run_stderr_tail = String(terminalRun?.stderr ?? "").slice(-2000);
      if (terminalRun?.stage !== "done") {
      report.errors.push(`自然语言 UI Run 结束状态为 ${terminalRun?.stage ?? "unknown"}。`);
      }
      await page.waitForTimeout(1200);
    } else {
      report.errors.push("审批并执行未返回 run_id。");
    }

    await clickNav(page, "Skill");
    await page.getByRole("heading", { name: /Skill 浏览器/i }).waitFor({ timeout: 30000 });
    await page
      .waitForFunction(() => document.body.innerText.includes("能力矩阵") && !document.body.innerText.includes("0 项能力"), null, {
        timeout: 60000,
      })
      .catch(() => {});
    report.screenshots.push(await snapshot(page, "07-skill-browser", ["能力矩阵", "项能力"]));

    await clickNav(page, "执行");
    report.screenshots.push(await snapshot(page, "08-execution-monitor", ["执行监控", "stdout", "stderr", "真实证据"]));

    await clickNav(page, "审查");
    report.screenshots.push(await snapshot(page, "09-review-center", ["审查中心", "review_report.json"]));

    await clickNav(page, "文件");
    report.screenshots.push(await snapshot(page, "10-files-exports", ["文件与导出", "真实证据"]));

    await clickNav(page, "设置");
    await page.getByRole("heading", { name: /设置/i }).waitFor({ timeout: 30000 });
    await page.locator('input[type="password"]').first().waitFor({ timeout: 60000 }).catch(() => {});
    report.screenshots.push(await snapshot(page, "11-settings-llm-providers", ["LLM Profile", "API Key", "MCP 配置"]));
    const apiKeyType = await page.locator('input[type="password"]').count();
    report.api_key_masked_input_count = apiKeyType;
    await clickIfVisible(page, "浅色", report);
    report.screenshots.push(await snapshot(page, "12-theme-light", ["设置", "浅色"]));
    await clickIfVisible(page, "深色", report);
    report.screenshots.push(await snapshot(page, "13-theme-dark", ["设置", "深色"]));
    report.screenshots.push(await snapshot(page, "14-mcp-config", ["MCP 配置", "Codex", "Claude"]));

    await clickNav(page, "Skill");
    await page.locator('input[placeholder*="搜索"]').fill("motion");
    await page.waitForTimeout(500);
    report.screenshots.push(await snapshot(page, "15-error-skipped-disabled-state", ["motion", "Motion"]));

    await clickNav(page, "工作台");
    await page.getByRole("button", { name: /生成 Script/i }).focus();

    report.packaged_exe_ok =
      Boolean(report.child_process_started) &&
      Boolean(report.backend_health?.ok) &&
      report.validation_llm_configured &&
      report.llm_connection_ok &&
      report.api_key_masked_input_count > 0 &&
      report.natural_language_ui_run_attempted &&
      report.natural_language_ui_run_completed &&
      report.natural_language_ui_run_real_execution_verified &&
      report.natural_language_ui_run_created_files_exist &&
      report.screenshots.length >= 12 &&
      report.screenshots.every((item) => item.non_blank);
  } catch (error) {
    report.errors.push(String(error?.stack ?? error));
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    if (child.pid) {
      await new Promise((resolve) => {
        const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
        killer.on("close", resolve);
      });
    }
  }

  const manifestPath = path.join(visualRoot, "screenshot_manifest.json");
  fs.writeFileSync(manifestPath, JSON.stringify({ screenshots: report.screenshots }, null, 2), "utf8");
  const runtimeJson = path.join(validationRoot, "PACKAGED_EXE_RUNTIME_REPORT.json");
  fs.writeFileSync(runtimeJson, JSON.stringify(report, null, 2), "utf8");
  const runtimeMd = path.join(validationRoot, "PACKAGED_EXE_RUNTIME_REPORT.md");
  fs.writeFileSync(
    runtimeMd,
    [
      "# 打包 EXE 运行报告",
      "",
      `生成时间：${report.generated_at}`,
      `打包 EXE 通过：${report.packaged_exe_ok}`,
      `可执行文件：${report.executable}`,
      `Backend health：${report.backend_health?.ok ?? false}`,
      `截图：${report.screenshots.length}`,
      `API Key 脱敏输入框：${report.api_key_masked_input_count ?? 0}`,
      `自然语言 UI Run 已尝试：${report.natural_language_ui_run_attempted}`,
      `自然语言 UI Run 已完成：${report.natural_language_ui_run_completed}`,
      `自然语言 UI Run 阶段：${report.natural_language_ui_run_stage ?? "not_run"}`,
      `自然语言 UI Run ID：${report.natural_language_ui_run_id ?? "none"}`,
      "",
      "## 截图",
      ...report.screenshots.map((item) => `- ${item.page}: ${item.file_path} (${item.pass ? "通过" : "待检查"})`),
      "",
      "## 错误",
      ...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ["- 无"]),
      "",
    ].join("\n"),
    "utf8",
  );
  console.log(JSON.stringify({ packaged_exe_ok: report.packaged_exe_ok, screenshots: report.screenshots.length }, null, 2));
  if (!report.packaged_exe_ok) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
