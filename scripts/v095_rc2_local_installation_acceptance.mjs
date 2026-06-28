import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const rcVersion = "0.9.5-rc.2";
const outputRoot = path.join(root, "outputs");
const evidenceRoot = path.join(outputRoot, "v095_rc2", "latest");
const installDir = path.join(evidenceRoot, "installed-app");
const reinstallDir = path.join(evidenceRoot, "reinstalled-app");
const userDataDir = path.join(evidenceRoot, "installed-user-data");
const reinstallUserDataDir = path.join(evidenceRoot, "reinstalled-user-data");
const screenshotDir = path.join(evidenceRoot, "screenshots");
const diagnosticsDir = path.join(evidenceRoot, "diagnostics");
const deliveryDir = path.join(evidenceRoot, "final_exe_package");
const reportJsonPath = path.join(evidenceRoot, "V095_RC2_LOCAL_INSTALLATION_ACCEPTANCE_REPORT.json");
const reportMdPath = path.join(evidenceRoot, "V095_RC2_LOCAL_INSTALLATION_ACCEPTANCE_REPORT.md");
const validationApiKey = process.env.SWAI_VALIDATION_API_KEY ?? "";
const validationApiBaseUrl = process.env.SWAI_VALIDATION_API_BASE_URL ?? "https://api.ccagent.cn/v1";
const validationModel = process.env.SWAI_VALIDATION_MODEL ?? "glm-5.1";
const validationVisionModel = process.env.SWAI_VALIDATION_VISION_MODEL ?? "doubao-seed-2.0-pro";
const stabilityCount = Number(process.env.SWAI_RC2_STABILITY_COUNT ?? "20");

for (const dir of [evidenceRoot, screenshotDir, diagnosticsDir, deliveryDir]) fs.mkdirSync(dir, { recursive: true });
for (const dir of [installDir, reinstallDir, userDataDir, reinstallUserDataDir]) fs.rmSync(dir, { recursive: true, force: true });
for (const dir of [installDir, reinstallDir, userDataDir, reinstallUserDataDir]) fs.mkdirSync(dir, { recursive: true });

function artifactPath(name) {
  return path.join(root, "dist", name);
}

function requiredArtifact(name) {
  const filePath = artifactPath(name);
  if (!fs.existsSync(filePath)) throw new Error(`Missing release artifact: dist/${name}`);
  return filePath;
}

function sha256(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(filePath));
  return hash.digest("hex");
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

function runProcess(command, args, options = {}, timeoutMs = 180000) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { ...options, windowsHide: true });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);
    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr?.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr, timedOut });
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
  throw new Error(`Timed out waiting for Electron CDP on ${port}`);
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
      if (text.includes("SolidWorks AI Studio") || text.includes("Dashboard")) return page;
    }
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
  throw new Error("Could not find rendered SolidWorks AI Studio page.");
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

async function snapshot(page, name, expected = []) {
  const filePath = path.join(screenshotDir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  const text = await pageText(page);
  const formValues = await page.evaluate(() =>
    Array.from(document.querySelectorAll("input, textarea, select"))
      .map((item) => item instanceof HTMLInputElement || item instanceof HTMLTextAreaElement || item instanceof HTMLSelectElement ? item.value : "")
      .filter(Boolean)
      .join("\n"),
  );
  const searchableText = `${text}\n${formValues}`;
  const assertions = expected.map((item) => ({ expected: item, pass: searchableText.toLowerCase().includes(item.toLowerCase()) }));
  return {
    page: name,
    path: filePath,
    non_blank: fs.statSync(filePath).size > 10000,
    assertions,
    pass: fs.statSync(filePath).size > 10000 && assertions.every((item) => item.pass),
  };
}

async function navigate(page, label, heading) {
  await page.getByRole("button", { name: new RegExp(`^${label}$`, "i") }).click();
  await page.locator("h1").filter({ hasText: new RegExp(heading, "i") }).waitFor({ timeout: 30000 });
  await page.waitForTimeout(500);
}

async function install(setupExe, targetDir) {
  fs.rmSync(targetDir, { recursive: true, force: true });
  fs.mkdirSync(targetDir, { recursive: true });
  const result = await runProcess(setupExe, ["/S", `/D=${targetDir}`], { cwd: root, stdio: ["ignore", "pipe", "pipe"] }, 240000);
  const exe = path.join(targetDir, "SolidWorks AI Studio.exe");
  return {
    target_dir: targetDir,
    exit_code: result.code,
    timed_out: result.timedOut,
    ok: result.code === 0 && !result.timedOut && fs.existsSync(exe),
    installed_exe: exe,
    installed_exe_exists: fs.existsSync(exe),
  };
}

async function uninstall(targetDir) {
  const candidates = fs.existsSync(targetDir) ? fs.readdirSync(targetDir).filter((name) => /^Uninstall .*\.exe$/i.test(name)) : [];
  const uninstaller = candidates.length ? path.join(targetDir, candidates[0]) : "";
  if (!uninstaller) return { ok: false, uninstaller_found: false, exit_code: null, target_removed: false };
  const result = await runProcess(uninstaller, ["/S"], { cwd: targetDir, stdio: ["ignore", "pipe", "pipe"] }, 240000);
  const exe = path.join(targetDir, "SolidWorks AI Studio.exe");
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline && fs.existsSync(exe)) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  const exeExists = fs.existsSync(exe);
  return {
    ok: result.code === 0 && !result.timedOut && !exeExists,
    uninstaller_found: true,
    uninstaller,
    exit_code: result.code,
    timed_out: result.timedOut,
    target_removed: !exeExists,
  };
}

async function launchInstalled(exe, userData, outputDir) {
  const port = await freePort();
  const child = spawn(exe, [`--remote-debugging-port=${port}`, "--disable-gpu", `--user-data-dir=${userData}`], {
    cwd: path.dirname(exe),
    env: { ...process.env, SWAI_OUTPUT_DIR: outputDir },
    stdio: "ignore",
    windowsHide: true,
  });
  const version = await waitForCdp(port);
  const browser = await chromium.connectOverCDP(version.webSocketDebuggerUrl);
  const page = await selectAppPage(browser);
  await page.setViewportSize({ width: 1480, height: 940 });
  const info = await waitForBackendInfo(page);
  return { child, browser, page, info };
}

async function stopInstalled(session) {
  await session.browser?.close().catch(() => {});
  if (session.child?.pid) {
    await runProcess("taskkill", ["/PID", String(session.child.pid), "/T", "/F"], { stdio: "ignore" }, 10000);
  }
}

async function configureModels(info) {
  if (!validationApiKey) throw new Error("SWAI_VALIDATION_API_KEY is required for rc.2 real model acceptance.");
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

async function runNaturalLanguage(info) {
  const outputDir = path.join(evidenceRoot, "natural_language_outputs");
  fs.mkdirSync(outputDir, { recursive: true });
  const prompt = "新建一个 120x80x10 mm 安装板，四角各打 M6 通孔，倒角 1 mm，保存为 SLDPRT 并导出 STEP。";
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

async function runWorkbenchMountingPlate(info, approvedBy = "v0.9.5-rc.2") {
  const capabilityId = "ai.parametric_part_generator";
  const recipeId = "mounting_plate";
  const prompt = "Create a 120x80x10mm mounting plate with four M6 through holes and 1mm chamfer.";
  let response = await apiFetch(info, `/api/ai-capabilities/${capabilityId}/plan`, {
    method: "POST",
    body: JSON.stringify({ recipe_id: recipeId, execution_mode: "real", prompt }),
  }, 60000);
  if (!response.ok) throw new Error(`Workbench plan failed: ${response.status}`);
  const taskId = response.body.task_id;
  const calls = [["plan", response.status, response.body]];
  for (const [endpoint, payload, timeout] of [
    ["generate-script", { task_id: taskId, recipe_id: recipeId, execution_mode: "real" }, 60000],
    ["validate", { task_id: taskId }, 60000],
    ["approve", { task_id: taskId, approved_by: approvedBy }, 60000],
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

async function runInstalledStability(info, count) {
  const runs = [];
  let passCount = 0;
  let failCount = 0;
  for (let index = 1; index <= count; index += 1) {
    const run = { iteration: index, status: "running", task_id: "", artifact_count: 0, error: "" };
    try {
      const readyDeadline = Date.now() + 90000;
      let ready = null;
      while (Date.now() < readyDeadline) {
        const preflight = await apiFetch(info, "/api/solidworks/preflight", {}, 90000);
        ready = preflight.body;
        if (preflight.ok && ready?.can_run_real_com === true) break;
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
      run.preflight = {
        can_run_real_com: ready?.can_run_real_com === true,
        solidworks_version: ready?.solidworks_version ?? "",
        state: ready?.state ?? "",
      };
      if (!run.preflight.can_run_real_com) throw new Error("SolidWorks preflight was not ready before stability iteration.");
      await new Promise((resolve) => setTimeout(resolve, 1500));
      const result = await runWorkbenchMountingPlate(info, "v0.9.5-rc.2-stability");
      const evidence = result.final?.evidence ?? {};
      run.task_id = result.task_id;
      run.status = result.final?.status ?? "";
      run.real_execution_verified = result.final?.real_execution_verified === true;
      run.hole_features_restored = evidence.hole_features_restored === true;
      run.geometry_parity_verified = evidence.geometry_parity_verified === true;
      run.hole_count_observed = evidence.hole_count_observed;
      run.artifact_count = (result.final?.artifacts ?? []).length;
      const artifactsExist = (result.final?.artifacts ?? []).every((item) => item.exists === true);
      const ok =
        run.status === "completed" &&
        run.real_execution_verified &&
        run.hole_features_restored &&
        run.geometry_parity_verified &&
        run.hole_count_observed === 4 &&
        run.artifact_count >= 8 &&
        artifactsExist;
      if (ok) {
        run.status = "passed";
        passCount += 1;
      } else {
        run.status = "failed";
        run.error = "missing real execution, artifact, or four-hole parity evidence";
        failCount += 1;
      }
    } catch (error) {
      run.status = "failed";
      run.error = String(error?.message ?? error);
      failCount += 1;
    }
    runs.push(run);
  }
  const report = {
    status: failCount === 0 && passCount === count ? "passed" : "failed",
    count_requested: count,
    pass_count: passCount,
    fail_count: failCount,
    runs,
  };
  fs.writeFileSync(path.join(evidenceRoot, "INSTALLED_LONG_STABILITY_REPORT.json"), JSON.stringify(report, null, 2), "utf8");
  return report;
}

function runErrorScenarioValidation() {
  const result = spawnSync("powershell", ["-ExecutionPolicy", "Bypass", "-File", path.join(root, "scripts", "validate_error_scenarios.ps1")], {
    cwd: root,
    encoding: "utf8",
    timeout: 300000,
    windowsHide: true,
  });
  const reportPath = path.join(outputRoot, "validation", "latest", "ERROR_SCENARIOS_REPORT.json");
  return {
    exit_code: result.status,
    stdout_tail: String(result.stdout ?? "").slice(-2000),
    stderr_tail: String(result.stderr ?? "").slice(-2000),
    report_path: reportPath,
    report: fs.existsSync(reportPath) ? JSON.parse(fs.readFileSync(reportPath, "utf8")) : null,
  };
}

function copyIfExists(source, targetName) {
  if (!fs.existsSync(source)) return null;
  const target = path.join(diagnosticsDir, targetName);
  fs.copyFileSync(source, target);
  return target;
}

function sanitizeFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const home = process.env.USERPROFILE ?? "";
  let text = fs.readFileSync(filePath, "utf8");
  text = text.replaceAll(root, "<PROJECT_ROOT>").replaceAll(root.replaceAll("\\", "/"), "<PROJECT_ROOT>");
  if (home) text = text.replaceAll(home, "<USER_HOME>").replaceAll(home.replaceAll("\\", "/"), "<USER_HOME>");
  text = text.replace(/C:\\Users\\[^\\\s"]+/g, "C:\\Users\\<USER>");
  text = text.replace(/sk-[A-Za-z0-9_-]{16,}/g, "<REDACTED_API_KEY>");
  text = text.replace(/gh[op]_[A-Za-z0-9_]{16,}/g, "<REDACTED_GITHUB_TOKEN>");
  text = text.replace(/github_pat_[A-Za-z0-9_]{16,}/g, "<REDACTED_GITHUB_TOKEN>");
  fs.writeFileSync(filePath, text, "utf8");
}

function createDiagnosticsPackage(report) {
  fs.rmSync(diagnosticsDir, { recursive: true, force: true });
  fs.mkdirSync(diagnosticsDir, { recursive: true });
  const copied = [];
  for (const [source, name] of [
    [reportJsonPath, "V095_RC2_LOCAL_INSTALLATION_ACCEPTANCE_REPORT.json"],
    [path.join(outputRoot, "visual_validation", "latest", "VISUAL_VALIDATION_REPORT.json"), "VISUAL_VALIDATION_REPORT.json"],
    [path.join(outputRoot, "validation", "latest", "ERROR_SCENARIOS_REPORT.json"), "ERROR_SCENARIOS_REPORT.json"],
    [path.join(evidenceRoot, "INSTALLED_LONG_STABILITY_REPORT.json"), "INSTALLED_LONG_STABILITY_REPORT.json"],
  ]) {
    const copiedPath = copyIfExists(source, name);
    if (copiedPath) {
      sanitizeFile(copiedPath);
      copied.push(copiedPath);
    }
  }
  const summary = {
    generated_at: new Date().toISOString(),
    rc_version: rcVersion,
    copied_files: copied.map((item) => path.basename(item)),
    release_artifacts: report.release_artifacts,
  };
  fs.writeFileSync(path.join(diagnosticsDir, "DIAGNOSTIC_SUMMARY.redacted.json"), JSON.stringify(summary, null, 2), "utf8");
  const zipPath = path.join(evidenceRoot, "SolidWorks-AI-Studio-v0.9.5-rc.2-diagnostics.zip");
  fs.rmSync(zipPath, { force: true });
  const zipResult = spawnSync("powershell", ["-NoProfile", "-Command", `Compress-Archive -Path '${diagnosticsDir}\\*' -DestinationPath '${zipPath}' -Force`], {
    cwd: root,
    encoding: "utf8",
    timeout: 120000,
    windowsHide: true,
  });
  return {
    ok: zipResult.status === 0 && fs.existsSync(zipPath) && fs.statSync(zipPath).size > 1000,
    zip_path: zipPath,
    zip_size: fs.existsSync(zipPath) ? fs.statSync(zipPath).size : 0,
    copied_files: copied.map((item) => path.basename(item)),
    exit_code: zipResult.status,
    stderr_tail: String(zipResult.stderr ?? "").slice(-1000),
  };
}

function createDeliveryPackage(report) {
  fs.rmSync(deliveryDir, { recursive: true, force: true });
  fs.mkdirSync(deliveryDir, { recursive: true });
  const copied = [];
  for (const relative of ["SolidWorks AI Studio Setup.exe", "SolidWorks AI Studio Portable.exe", "SolidWorks AI Studio Setup.exe.blockmap"]) {
    const source = artifactPath(relative);
    if (fs.existsSync(source)) {
      const target = path.join(deliveryDir, relative);
      fs.copyFileSync(source, target);
      copied.push(target);
    }
  }
  fs.writeFileSync(path.join(deliveryDir, "SHA256SUMS.txt"), report.release_artifacts.map((item) => `${item.sha256}  ${item.relative_path}`).join("\n") + "\n", "utf8");
  fs.writeFileSync(path.join(deliveryDir, "README.txt"), [
    "SolidWorks AI Studio v0.9.5-rc.2",
    "",
    "Use SolidWorks AI Studio Setup.exe for installation, or SolidWorks AI Studio Portable.exe for a portable launch.",
    "Configure your own OpenAI-compatible API key in Settings. No API key is included.",
    "See SHA256SUMS.txt for artifact hashes.",
    "",
  ].join("\n"), "utf8");
  const zipPath = path.join(evidenceRoot, "SolidWorks-AI-Studio-v0.9.5-rc.2-windows-x64.zip");
  fs.rmSync(zipPath, { force: true });
  const zipResult = spawnSync("powershell", ["-NoProfile", "-Command", `Compress-Archive -Path '${deliveryDir}\\*' -DestinationPath '${zipPath}' -Force`], {
    cwd: root,
    encoding: "utf8",
    timeout: 240000,
    windowsHide: true,
  });
  return {
    ok: zipResult.status === 0 && fs.existsSync(zipPath) && fs.statSync(zipPath).size > 100000000,
    directory: deliveryDir,
    zip_path: zipPath,
    zip_size: fs.existsSync(zipPath) ? fs.statSync(zipPath).size : 0,
    copied_count: copied.length,
    exit_code: zipResult.status,
    stderr_tail: String(zipResult.stderr ?? "").slice(-1000),
  };
}

function writeReport(report) {
  fs.writeFileSync(reportJsonPath, JSON.stringify(report, null, 2), "utf8");
  fs.writeFileSync(reportMdPath, [
    "# v0.9.5-rc.2 Local Installation Acceptance",
    "",
    `Overall OK: ${report.ok}`,
    `Version: ${rcVersion}`,
    `Setup install: ${report.install?.ok ?? false}`,
    `Reinstall: ${report.reinstall?.ok ?? false}`,
    `Uninstall: ${report.uninstall?.ok ?? false}`,
    `Text model verified: ${report.model_acceptance?.text?.chat_verified ?? false}`,
    `Vision model verified: ${report.model_acceptance?.vision?.vision_verified ?? false}`,
    `SolidWorks ready: ${report.solidworks_acceptance?.can_run_real_com ?? false}`,
    `Natural language stage: ${report.functional_acceptance?.natural_language?.terminal?.stage ?? "not_run"}`,
    `Workbench task: ${report.functional_acceptance?.workbench?.task_id ?? ""}`,
    `Installed stability: ${report.stability_acceptance?.pass_count ?? 0}/${report.stability_acceptance?.count_requested ?? 0}`,
    `Error scenarios: ${report.error_scenarios?.report?.status ?? "not_run"}`,
    `Diagnostics package: ${report.diagnostics_acceptance?.ok ?? false}`,
    `Delivery package: ${report.delivery_package?.ok ?? false}`,
    "",
    "## Errors",
    ...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ["- none"]),
    "",
  ].join("\n"), "utf8");
}

async function main() {
  const setupExe = requiredArtifact("SolidWorks AI Studio Setup.exe");
  const portableExe = requiredArtifact("SolidWorks AI Studio Portable.exe");
  const blockmap = requiredArtifact("SolidWorks AI Studio Setup.exe.blockmap");
  const report = {
    ok: false,
    generated_at: new Date().toISOString(),
    rc_version: rcVersion,
    release_artifacts: [
      { relative_path: "dist/SolidWorks AI Studio Setup.exe", bytes: fs.statSync(setupExe).size, sha256: sha256(setupExe) },
      { relative_path: "dist/SolidWorks AI Studio Portable.exe", bytes: fs.statSync(portableExe).size, sha256: sha256(portableExe) },
      { relative_path: "dist/SolidWorks AI Studio Setup.exe.blockmap", bytes: fs.statSync(blockmap).size, sha256: sha256(blockmap) },
    ],
    install: null,
    first_start: null,
    model_acceptance: null,
    solidworks_acceptance: null,
    functional_acceptance: null,
    stability_acceptance: null,
    error_scenarios: null,
    uninstall: null,
    reinstall: null,
    reinstall_first_start: null,
    diagnostics_acceptance: null,
    delivery_package: null,
    screenshots: [],
    errors: [],
  };
  let session;
  let reinstallSession;
  try {
    report.install = await install(setupExe, installDir);
    if (!report.install.ok) throw new Error("Initial install failed.");
    session = await launchInstalled(report.install.installed_exe, userDataDir, outputRoot);
    const health = await apiFetch(session.info, "/api/health", {}, 30000);
    const config = await apiFetch(session.info, "/api/config", {}, 30000);
    report.first_start = {
      rendered: (await pageText(session.page)).includes("Dashboard"),
      backend_health: health.body,
      config_loaded: config.ok,
      fresh_config: config.ok && !(config.body?.config?.profiles ?? []).some((profile) => profile.api_key),
    };
    report.screenshots.push(await snapshot(session.page, "01-installed-dashboard", ["Dashboard", "AI Capability Workbench"]));

    const activeProfile = await configureModels(session.info);
    const text = await apiFetch(session.info, "/api/llm/test", { method: "POST", body: JSON.stringify({ profile: activeProfile }) }, 180000);
    const vision = await apiFetch(session.info, "/api/llm/test-vision", { method: "POST", body: JSON.stringify({ profile: activeProfile }) }, 180000);
    report.model_acceptance = { text: text.body, vision: vision.body };
    await session.page.reload({ waitUntil: "domcontentloaded" });
    await session.page.waitForFunction(
      () => document.body.innerText.includes("SolidWorks AI Studio") || document.body.innerText.includes("Dashboard"),
      null,
      { timeout: 60000 },
    );

    const preflight = await apiFetch(session.info, "/api/solidworks/preflight", {}, 120000);
    report.solidworks_acceptance = preflight.body;
    if (preflight.body?.can_run_real_com !== true) throw new Error("SolidWorks preflight is not ready.");

    await navigate(session.page, "Settings", "设置");
    report.screenshots.push(await snapshot(session.page, "02-settings-verified", ["glm-5.1", "doubao-seed-2.0-pro"]));
    await navigate(session.page, "Capabilities", "AI Capability Workbench");
    report.screenshots.push(await snapshot(session.page, "03-capabilities", ["AI CAD Studio", "mounting_plate"]));

    const naturalLanguage = await runNaturalLanguage(session.info);
    const workbench = await runWorkbenchMountingPlate(session.info);
    const tasks = await apiFetch(session.info, "/api/tasks", {}, 30000);
    report.functional_acceptance = {
      natural_language: naturalLanguage,
      workbench,
      task_history_api_visible: Boolean(tasks.ok && tasks.body?.tasks?.some((task) => task.task_id === workbench.task_id)),
    };
    await session.page.reload({ waitUntil: "domcontentloaded" });
    await session.page.waitForFunction(
      () => document.body.innerText.includes("SolidWorks AI Studio") || document.body.innerText.includes("Dashboard"),
      null,
      { timeout: 60000 },
    );
    await navigate(session.page, "Tasks", "Task History");
    await session.page.waitForFunction((taskId) => document.body.innerText.includes(taskId), workbench.task_id, { timeout: 30000 }).catch(() => null);
    const taskText = await pageText(session.page);
    report.functional_acceptance.task_history_ui_visible = taskText.includes(workbench.task_id) && taskText.includes("mounting_plate");
    report.screenshots.push(await snapshot(session.page, "04-task-history", [workbench.task_id, "mounting_plate"]));
    await navigate(session.page, "Integration", "Integration");
    report.screenshots.push(await snapshot(session.page, "05-integration", ["Prompt Composer", "Registry-backed 工具"]));
    await navigate(session.page, "Developer", "Developer");
    report.screenshots.push(await snapshot(session.page, "06-developer", ["Skill 上下文", "能力矩阵"]));

    report.stability_acceptance = await runInstalledStability(session.info, stabilityCount);
    report.error_scenarios = runErrorScenarioValidation();
    writeReport(report);
    report.diagnostics_acceptance = createDiagnosticsPackage(report);
    report.delivery_package = createDeliveryPackage(report);

    await stopInstalled(session);
    session = null;
    report.uninstall = await uninstall(installDir);
    report.reinstall = await install(setupExe, reinstallDir);
    reinstallSession = await launchInstalled(report.reinstall.installed_exe, reinstallUserDataDir, outputRoot);
    const reinstallHealth = await apiFetch(reinstallSession.info, "/api/health", {}, 30000);
    const reinstallConfig = await apiFetch(reinstallSession.info, "/api/config", {}, 30000);
    report.reinstall_first_start = {
      rendered: (await pageText(reinstallSession.page)).includes("Dashboard"),
      backend_health: reinstallHealth.body,
      config_loaded: reinstallConfig.ok,
      fresh_config: reinstallConfig.ok && !(reinstallConfig.body?.config?.profiles ?? []).some((profile) => profile.api_key),
    };
    report.screenshots.push(await snapshot(reinstallSession.page, "07-reinstall-dashboard", ["Dashboard", "AI Capability Workbench"]));

    const naturalDone = report.functional_acceptance.natural_language.terminal?.stage === "done" && report.functional_acceptance.natural_language.terminal?.real_execution_verified === true;
    const evidence = report.functional_acceptance.workbench.final?.evidence ?? {};
    const workbenchOk =
      report.functional_acceptance.workbench.final?.status === "completed" &&
      report.functional_acceptance.workbench.final?.real_execution_verified === true &&
      evidence.hole_features_restored === true &&
      evidence.geometry_parity_verified === true;
    report.ok =
      report.install.ok &&
      report.first_start.rendered &&
      report.first_start.backend_health?.version === rcVersion &&
      report.model_acceptance.text?.chat_verified === true &&
      report.model_acceptance.vision?.vision_verified === true &&
      report.solidworks_acceptance?.can_run_real_com === true &&
      naturalDone &&
      workbenchOk &&
      report.functional_acceptance.task_history_api_visible &&
      report.functional_acceptance.task_history_ui_visible &&
      report.stability_acceptance.status === "passed" &&
      report.error_scenarios.exit_code === 0 &&
      report.error_scenarios.report?.status === "passed" &&
      report.diagnostics_acceptance.ok &&
      report.delivery_package.ok &&
      report.uninstall.ok &&
      report.reinstall.ok &&
      report.reinstall_first_start.rendered &&
      report.reinstall_first_start.backend_health?.version === rcVersion &&
      report.reinstall_first_start.fresh_config &&
      report.screenshots.every((item) => item.pass);
  } catch (error) {
    report.errors.push(String(error?.stack ?? error));
  } finally {
    if (session) await stopInstalled(session);
    if (reinstallSession) await stopInstalled(reinstallSession);
    writeReport(report);
  }
  console.log(JSON.stringify({ ok: report.ok, report: reportJsonPath }, null, 2));
  if (!report.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
