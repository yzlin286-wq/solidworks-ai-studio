import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outputRoot = path.join(root, "outputs");
const evidenceRoot = path.join(outputRoot, "v094_e2e", "latest");
const shotDir = path.join(evidenceRoot, "screenshots");
const visualAppDir = path.join(outputRoot, "visual_validation", "latest", "screenshots", "app");
const reportJsonPath = path.join(evidenceRoot, "V094_E2E_USABLE_APP_REPORT.json");
const reportMdPath = path.join(evidenceRoot, "V094_E2E_USABLE_APP_REPORT.md");
const validationUserData = path.join(evidenceRoot, "electron-user-data");
const validationApiKey = process.env.SWAI_VALIDATION_API_KEY ?? "";
const validationApiBaseUrl = process.env.SWAI_VALIDATION_API_BASE_URL ?? "https://api.ccagent.cn/v1";
const validationModel = process.env.SWAI_VALIDATION_MODEL ?? "glm-5.1";
const validationVisionModel = process.env.SWAI_VALIDATION_VISION_MODEL ?? "doubao-seed-2.0-pro";

fs.mkdirSync(shotDir, { recursive: true });
fs.mkdirSync(visualAppDir, { recursive: true });
fs.rmSync(validationUserData, { recursive: true, force: true });
fs.mkdirSync(validationUserData, { recursive: true });

function findPackagedExe() {
  if (process.env.SWAI_V094_EXE && fs.existsSync(process.env.SWAI_V094_EXE)) return process.env.SWAI_V094_EXE;
  const portable = path.join(root, "dist", "SolidWorks AI Studio Portable.exe");
  if (fs.existsSync(portable)) return portable;
  const setup = path.join(root, "dist", "win-unpacked", "SolidWorks AI Studio.exe");
  if (fs.existsSync(setup)) return setup;
  throw new Error("No packaged EXE found. Run scripts/build_backend.ps1 and scripts/build_desktop.ps1 first.");
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
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error(`Timed out waiting for Electron CDP on port ${port}`);
}

async function waitForBackendInfo(page, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const info = await page.evaluate(async () => window.swai?.getBackendInfo ? window.swai.getBackendInfo() : null).catch(() => null);
    if (info?.baseUrl && info?.token) return info;
    await page.waitForTimeout(800);
  }
  throw new Error("Packaged app did not expose backend bridge.");
}

async function apiFetch(info, route, options = {}, timeoutMs = 30000, attempts = 20) {
  let lastError;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${info.baseUrl}${route}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "X-SWAI-Token": info.token,
          ...(options.headers ?? {}),
        },
        signal: controller.signal,
      });
      const text = await response.text();
      let body = null;
      try {
        body = text ? JSON.parse(text) : null;
      } catch {
        body = { text };
      }
      return { ok: response.ok, status: response.status, body };
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 700));
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError ?? new Error(`fetch failed for ${route}`);
}

async function pageText(page) {
  return await page.evaluate(() => document.body.innerText.slice(0, 30000));
}

async function selectAppPage(browser, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const pages = browser.contexts().flatMap((context) => context.pages());
    for (const page of pages) {
      const text = await pageText(page).catch(() => "");
      if (text.includes("SolidWorks AI Studio") || text.includes("Dashboard") || text.includes("AI Capability Workbench")) {
        return page;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
  const pages = browser.contexts().flatMap((context) => context.pages());
  const summaries = [];
  for (const page of pages) {
    summaries.push({
      url: page.url(),
      title: await page.title().catch(() => ""),
      text: (await pageText(page).catch(() => "")).slice(0, 500),
    });
  }
  throw new Error(`Could not find rendered app page. Pages: ${JSON.stringify(summaries)}`);
}

async function snapshot(page, name, expected = []) {
  const filePath = path.join(shotDir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  fs.copyFileSync(filePath, path.join(visualAppDir, `${name}.png`));
  const text = await pageText(page);
  const assertions = expected.map((item) => ({ expected: item, pass: text.toLowerCase().includes(item.toLowerCase()) }));
  return {
    page: name,
    file_path: filePath,
    non_blank: fs.statSync(filePath).size > 10_000,
    expected_ui_assertions: assertions,
    pass: fs.statSync(filePath).size > 10_000 && assertions.every((item) => item.pass),
  };
}

async function navigate(page, label, heading) {
  await page.getByRole("button", { name: new RegExp(`^${label}$`, "i") }).click();
  await page.locator("h1").filter({ hasText: new RegExp(heading, "i") }).waitFor({ timeout: 30000 });
  await page.waitForTimeout(500);
}

async function clickAndCaptureResponse(page, label, urlPart, timeoutMs = 180000) {
  const responsePromise = page.waitForResponse((response) => response.url().includes(urlPart), { timeout: timeoutMs }).catch((error) => ({ error }));
  await page.getByRole("button", { name: new RegExp(label, "i") }).first().click();
  const response = await responsePromise;
  if (response?.error) return { ok: false, status: 0, body: null, error: String(response.error?.message ?? response.error) };
  return { ok: response.ok(), status: response.status(), body: await response.json().catch(() => null), error: "" };
}

async function configureModels(info) {
  if (!validationApiKey) throw new Error("SWAI_VALIDATION_API_KEY is required for v0.9.4 real model validation.");
  const configResponse = await apiFetch(info, "/api/config");
  if (!configResponse.ok) throw new Error(`GET /api/config failed: ${configResponse.status}`);
  const config = configResponse.body.config;
  const active = config.active_profile_id || "ccagent";
  config.profiles = config.profiles.map((profile) =>
    profile.id === active
      ? {
          ...profile,
          api_base_url: validationApiBaseUrl,
          api_key: validationApiKey,
          model: validationModel,
          vision_model: validationVisionModel,
          max_tokens: Math.max(Number(profile.max_tokens || 0), 8192),
          timeout_seconds: Math.max(Number(profile.timeout_seconds || 0), 180),
        }
      : profile,
  );
  const saved = await apiFetch(info, "/api/config", { method: "POST", body: JSON.stringify(config) });
  if (!saved.ok) throw new Error(`POST /api/config failed: ${saved.status}`);
  return saved.body.config.profiles.find((profile) => profile.id === active) ?? saved.body.config.profiles[0];
}

async function runWorkbenchMountingPlate(info) {
  const capabilityId = "ai.parametric_part_generator";
  const recipeId = "mounting_plate";
  const prompt = "Create a 120x80x10mm mounting plate with four M6 through holes and 1mm chamfer.";
  const calls = [];
  let response = await apiFetch(info, `/api/ai-capabilities/${capabilityId}/plan`, {
    method: "POST",
    body: JSON.stringify({ recipe_id: recipeId, execution_mode: "real", prompt }),
  }, 60000);
  calls.push(["plan", response.status, response.body]);
  if (!response.ok) throw new Error(`Workbench plan failed: ${response.status}`);
  const taskId = response.body.task_id;
  for (const [endpoint, payload, timeout] of [
    ["generate-script", { task_id: taskId, recipe_id: recipeId, execution_mode: "real" }, 60000],
    ["validate", { task_id: taskId }, 60000],
    ["approve", { task_id: taskId, approved_by: "v0.9.4-e2e" }, 60000],
    ["execute", { task_id: taskId, execution_mode: "real" }, 420000],
  ]) {
    response = await apiFetch(info, `/api/ai-capabilities/${capabilityId}/${endpoint}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }, timeout);
    calls.push([endpoint, response.status, response.body]);
    if (!response.ok) throw new Error(`Workbench ${endpoint} failed: ${response.status}`);
  }
  return { task_id: taskId, calls, final: response.body };
}

async function runNaturalLanguage(info) {
  const prompt = "新建一个 120x80x10 mm 安装板，四角各打 M6 通孔，倒角 1 mm，保存为 SLDPRT 并导出 STEP。";
  const outputDir = path.join(evidenceRoot, "natural_language_outputs");
  fs.mkdirSync(outputDir, { recursive: true });
  const plan = await apiFetch(info, "/api/ai/plan", { method: "POST", body: JSON.stringify({ prompt, output_dir: outputDir }) }, 240000);
  if (!plan.ok) throw new Error(`Real LLM plan failed: ${plan.status} ${JSON.stringify(plan.body).slice(0, 300)}`);
  const generated = await apiFetch(info, "/api/ai/generate-script", { method: "POST", body: JSON.stringify({ prompt, output_dir: outputDir }) }, 240000);
  if (!generated.ok) throw new Error(`Real LLM generate-script failed: ${generated.status} ${JSON.stringify(generated.body).slice(0, 300)}`);
  const approved = await apiFetch(info, "/api/ai/approve-run", {
    method: "POST",
    body: JSON.stringify({ script_path: generated.body.script_path, prompt, timeout_seconds: 420 }),
  }, 90000);
  if (!approved.ok) throw new Error(`Real LLM approve-run failed: ${approved.status} ${JSON.stringify(approved.body).slice(0, 300)}`);
  const deadline = Date.now() + 480000;
  let terminal = null;
  while (Date.now() < deadline) {
    const run = await apiFetch(info, `/api/runs/${approved.body.run_id}`, {}, 30000);
    terminal = run.body;
    if (run.ok && ["done", "failed"].includes(run.body?.stage)) break;
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  return { plan: plan.body, generated: generated.body, approved: approved.body, terminal };
}

function runVisualValidation() {
  const python = fs.existsSync(path.join(root, ".venv", "Scripts", "python.exe"))
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : "python";
  const result = spawnSync(python, ["-m", "sw_ai_backend.validation.visual_validation"], {
    cwd: root,
    env: {
      ...process.env,
      PYTHONPATH: path.join(root, "backend"),
      SWAI_PROJECT_ROOT: root,
      SWAI_OUTPUT_DIR: outputRoot,
      SWAI_VISUAL_MAX_VISION_IMAGES: process.env.SWAI_VISUAL_MAX_VISION_IMAGES ?? "8",
    },
    encoding: "utf8",
    timeout: 420000,
  });
  const reportPath = path.join(outputRoot, "visual_validation", "latest", "VISUAL_VALIDATION_REPORT.json");
  return {
    exit_code: result.status,
    stdout: result.stdout,
    stderr: result.stderr,
    report_path: reportPath,
    report: fs.existsSync(reportPath) ? JSON.parse(fs.readFileSync(reportPath, "utf8")) : null,
  };
}

function writeReport(report) {
  fs.writeFileSync(reportJsonPath, JSON.stringify(report, null, 2), "utf8");
  fs.writeFileSync(
    reportMdPath,
    [
      "# v0.9.4 End-to-End Usable App Evidence",
      "",
      `Generated: ${report.generated_at}`,
      `Overall OK: ${report.ok}`,
      `EXE: ${report.exe}`,
      `Text model: ${report.configured_models?.text_model ?? ""}`,
      `Vision model: ${report.configured_models?.vision_model ?? ""}`,
      `Backend health: ${report.backend_health?.ok ?? false}`,
      `Text LLM verified: ${report.text_llm?.chat_verified ?? false}`,
      `Vision LLM verified: ${report.vision_llm?.vision_verified ?? false}`,
      `SolidWorks preflight: ${report.solidworks_preflight?.body?.can_run_real_com ?? false}`,
      `Natural language stage: ${report.natural_language?.terminal?.stage ?? "not_run"}`,
      `Workbench task: ${report.workbench?.task_id ?? ""}`,
      `Workbench real verified: ${report.workbench?.final?.real_execution_verified ?? false}`,
      `Hole features restored: ${report.workbench?.final?.evidence?.hole_features_restored ?? false}`,
      `Task history visible: ${report.task_history_visible}`,
      `Visual OK: ${report.visual_validation?.report?.visual_ok ?? false}`,
      "",
      "## Pages",
      ...report.screenshots.map((item) => `- ${item.page}: ${item.pass}`),
      "",
      "## Errors",
      ...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ["- none"]),
      "",
    ].join("\n"),
    "utf8",
  );
}

async function main() {
  const exe = findPackagedExe();
  const port = await freePort();
  const child = spawn(exe, [`--remote-debugging-port=${port}`, "--disable-gpu", `--user-data-dir=${validationUserData}`], {
    cwd: path.dirname(exe),
    env: { ...process.env, SWAI_OUTPUT_DIR: outputRoot },
    stdio: "ignore",
    windowsHide: true,
  });
  const report = {
    ok: false,
    generated_at: new Date().toISOString(),
    exe,
    configured_models: {
      api_base_url: validationApiBaseUrl,
      text_model: validationModel,
      vision_model: validationVisionModel,
    },
    backend_health: null,
    text_llm: null,
    vision_llm: null,
    solidworks_preflight: null,
    natural_language: null,
    workbench: null,
    visual_validation: null,
    task_history_visible: false,
    task_history_api_visible: false,
    screenshots: [],
    errors: [],
  };
  let browser;
  try {
    const version = await waitForCdp(port);
    browser = await chromium.connectOverCDP(version.webSocketDebuggerUrl);
    let page = await selectAppPage(browser);
    await page.setViewportSize({ width: 1480, height: 940 });
    const info = await waitForBackendInfo(page);
    report.backend_health = (await apiFetch(info, "/api/health")).body;
    const activeProfile = await configureModels(info);
    report.text_llm = (await apiFetch(info, "/api/llm/test", { method: "POST", body: JSON.stringify({ profile: activeProfile }) }, 180000)).body;
    report.vision_llm = (await apiFetch(info, "/api/llm/test-vision", { method: "POST", body: JSON.stringify({ profile: activeProfile }) }, 180000)).body;
    report.solidworks_preflight = await apiFetch(info, "/api/solidworks/preflight", {}, 120000);

    report.screenshots.push(await snapshot(page, "01-dashboard", ["Dashboard", "AI Capability Workbench", "Capabilities", "Recipes"]));
    await navigate(page, "Settings", "设置");
    report.screenshots.push(await snapshot(page, "02-settings-models", ["文本 Model", "视觉 Model", "测试连接", "测试视觉"]));
    await clickAndCaptureResponse(page, "测试连接", "/api/llm/test", 180000);
    await clickAndCaptureResponse(page, "测试视觉", "/api/llm/test-vision", 180000);
    report.screenshots.push(await snapshot(page, "03-settings-verified", ["已验证", validationModel, validationVisionModel]));

    await navigate(page, "Capabilities", "AI Capability Workbench");
    report.screenshots.push(await snapshot(page, "04-capabilities", ["AI CAD Studio", "mounting_plate", "Real Plan", "Plan"]));
    report.natural_language = await runNaturalLanguage(info);
    report.workbench = await runWorkbenchMountingPlate(info);
    const tasksAfterWorkbench = await apiFetch(info, "/api/tasks", {}, 30000);
    report.task_history_api_visible = Boolean(
      tasksAfterWorkbench.ok && tasksAfterWorkbench.body?.tasks?.some((task) => task.task_id === report.workbench.task_id),
    );
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForResponse((response) => response.url().includes("/api/tasks"), { timeout: 30000 }).catch(() => null);
    await page.waitForFunction(
      () => document.body.innerText.includes("SolidWorks AI Studio") || document.body.innerText.includes("Dashboard"),
      null,
      { timeout: 60000 },
    );
    await navigate(page, "Tasks", "Task History");
    await page.waitForFunction(
      (taskId) => document.body.innerText.includes(taskId),
      report.workbench.task_id,
      { timeout: 20000 },
    ).catch(() => null);
    const taskText = await pageText(page);
    report.task_history_visible = taskText.includes(report.workbench.task_id) && taskText.includes("mounting_plate");
    report.screenshots.push(await snapshot(page, "05-task-history", [report.workbench.task_id, "mounting_plate", "artifacts"]));
    await navigate(page, "Integration", "Integration");
    report.screenshots.push(await snapshot(page, "06-integration", ["Prompt Composer", "直接工具", "Registry-backed 工具"]));
    await navigate(page, "Developer", "Developer");
    report.screenshots.push(await snapshot(page, "07-developer", ["Skill 上下文", "能力矩阵"]));

    report.visual_validation = runVisualValidation();
    const naturalDone = report.natural_language.terminal?.stage === "done" && report.natural_language.terminal?.real_execution_verified === true;
    const workbenchOk =
      report.workbench.final?.status === "completed" &&
      report.workbench.final?.real_execution_verified === true &&
      report.workbench.final?.evidence?.hole_features_restored === true &&
      report.workbench.final?.evidence?.geometry_parity_verified === true;
    report.ok =
      report.backend_health?.ok === true &&
      report.text_llm?.chat_verified === true &&
      report.vision_llm?.vision_verified === true &&
      report.solidworks_preflight?.body?.can_run_real_com === true &&
      naturalDone &&
      workbenchOk &&
      report.task_history_visible &&
      report.task_history_api_visible &&
      report.visual_validation?.report?.visual_ok === true &&
      report.screenshots.length >= 7 &&
      report.screenshots.every((item) => item.pass);
  } catch (error) {
    report.errors.push(String(error?.stack ?? error));
  } finally {
    if (browser) await browser.close().catch(() => {});
    if (child.pid) {
      await new Promise((resolve) => {
        const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
        killer.on("close", resolve);
        setTimeout(resolve, 10000);
      });
    }
    writeReport(report);
  }
  console.log(JSON.stringify({ ok: report.ok, report: reportJsonPath }, null, 2));
  if (!report.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
