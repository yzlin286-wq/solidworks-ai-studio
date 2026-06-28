import { chromium } from "playwright";
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outputRoot = path.join(root, "outputs");
const evidenceRoot = path.join(outputRoot, "v095_rc", "latest");
const installDir = path.join(evidenceRoot, "installed-app");
const userDataDir = path.join(evidenceRoot, "first-start-user-data");
const screenshotDir = path.join(evidenceRoot, "first-start-screenshots");
const reportPath = path.join(evidenceRoot, "V095_INSTALL_FIRST_START_REPORT.json");
const reportMdPath = path.join(evidenceRoot, "V095_INSTALL_FIRST_START_REPORT.md");

fs.mkdirSync(evidenceRoot, { recursive: true });
fs.rmSync(installDir, { recursive: true, force: true });
fs.rmSync(userDataDir, { recursive: true, force: true });
fs.rmSync(screenshotDir, { recursive: true, force: true });
fs.mkdirSync(installDir, { recursive: true });
fs.mkdirSync(userDataDir, { recursive: true });
fs.mkdirSync(screenshotDir, { recursive: true });

function findSetupExe() {
  const setup = path.join(root, "dist", "SolidWorks AI Studio Setup.exe");
  if (!fs.existsSync(setup)) throw new Error("Missing dist/SolidWorks AI Studio Setup.exe. Run scripts/build_desktop.ps1 first.");
  return setup;
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
  throw new Error(`Timed out waiting for Electron CDP on port ${port}`);
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
  throw new Error("Packaged app did not expose backend bridge on first start.");
}

async function apiFetch(info, route, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${info.baseUrl}${route}`, {
      headers: { "X-SWAI-Token": info.token },
      signal: controller.signal,
    });
    const text = await response.text();
    return { ok: response.ok, status: response.status, body: text ? JSON.parse(text) : null };
  } finally {
    clearTimeout(timer);
  }
}

function writeReport(report) {
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
  fs.writeFileSync(
    reportMdPath,
    [
      "# v0.9.5 RC Install And First Start Evidence",
      "",
      `Generated: ${report.generated_at}`,
      `Overall OK: ${report.ok}`,
      `Setup installed: ${report.setup?.ok ?? false}`,
      `Installed EXE exists: ${report.installed_exe_exists}`,
      `First start rendered: ${report.first_start?.rendered ?? false}`,
      `Backend health: ${report.first_start?.backend_health?.ok ?? false}`,
      `Fresh user config: ${report.first_start?.fresh_config ?? false}`,
      "",
      "## Errors",
      ...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ["- none"]),
      "",
    ].join("\n"),
    "utf8",
  );
}

async function main() {
  const setupExe = findSetupExe();
  const report = {
    ok: false,
    generated_at: new Date().toISOString(),
    setup: {
      path: setupExe,
      sha256: sha256(setupExe),
      ok: false,
      exit_code: null,
      timed_out: false,
    },
    install_dir: installDir,
    installed_exe: path.join(installDir, "SolidWorks AI Studio.exe"),
    installed_exe_exists: false,
    first_start: null,
    errors: [],
  };

  let browser;
  let appProcess;
  try {
    const setupResult = await runProcess(setupExe, ["/S", `/D=${installDir}`], { cwd: root, stdio: ["ignore", "pipe", "pipe"] }, 240000);
    report.setup.exit_code = setupResult.code;
    report.setup.timed_out = setupResult.timedOut;
    report.setup.ok = setupResult.code === 0 && !setupResult.timedOut;
    if (!report.setup.ok) throw new Error(`Setup install failed. exit=${setupResult.code} timedOut=${setupResult.timedOut}`);
    if (!fs.existsSync(report.installed_exe)) throw new Error(`Installed EXE not found at ${report.installed_exe}`);
    report.installed_exe_exists = true;
    report.installed_exe_sha256 = sha256(report.installed_exe);

    const port = await freePort();
    appProcess = spawn(report.installed_exe, [`--remote-debugging-port=${port}`, "--disable-gpu", `--user-data-dir=${userDataDir}`], {
      cwd: installDir,
      env: { ...process.env, SWAI_OUTPUT_DIR: outputRoot },
      stdio: "ignore",
      windowsHide: true,
    });
    const version = await waitForCdp(port);
    browser = await chromium.connectOverCDP(version.webSocketDebuggerUrl);
    const page = await selectAppPage(browser);
    await page.setViewportSize({ width: 1440, height: 900 });
    const info = await waitForBackendInfo(page);
    const health = await apiFetch(info, "/api/health", 30000);
    const config = await apiFetch(info, "/api/config", 30000);
    const text = await pageText(page);
    const screenshotPath = path.join(screenshotDir, "first-start-dashboard.png");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const activeProfileId = config.body?.config?.active_profile_id;
    const activeProfile = config.body?.config?.profiles?.find((profile) => profile.id === activeProfileId) ?? null;
    report.first_start = {
      rendered: text.includes("SolidWorks AI Studio") && text.includes("Dashboard"),
      backend_health: health.body,
      config_loaded: config.ok,
      fresh_config: config.ok && !activeProfile?.api_key,
      active_profile_id: activeProfileId ?? "",
      screenshot: screenshotPath,
      screenshot_non_blank: fs.existsSync(screenshotPath) && fs.statSync(screenshotPath).size > 10000,
    };
    report.ok =
      report.setup.ok &&
      report.installed_exe_exists &&
      report.first_start.rendered &&
      report.first_start.backend_health?.ok === true &&
      report.first_start.config_loaded &&
      report.first_start.fresh_config &&
      report.first_start.screenshot_non_blank;
  } catch (error) {
    report.errors.push(String(error?.stack ?? error));
  } finally {
    if (browser) await browser.close().catch(() => {});
    if (appProcess?.pid) {
      await runProcess("taskkill", ["/PID", String(appProcess.pid), "/T", "/F"], { stdio: "ignore" }, 10000);
    }
    writeReport(report);
  }
  console.log(JSON.stringify({ ok: report.ok, report: reportPath }, null, 2));
  if (!report.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
