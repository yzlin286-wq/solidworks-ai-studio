import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const appShotDir = path.join(root, "outputs", "visual_validation", "latest", "screenshots", "app");
const validationRoot = path.join(root, "outputs", "validation", "latest");
const exe = path.join(root, "dist", "win-unpacked", "SolidWorks AI Studio.exe");

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
      if (response.ok) return await response.json();
    } catch {
      // keep waiting
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for Electron CDP on port ${port}`);
}

async function waitForBackendInfo(page, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const info = await page.evaluate(async () => {
      if (!window.swai?.getBackendInfo) return null;
      return await window.swai.getBackendInfo();
    }).catch(() => null);
    if (info?.baseUrl && info?.token) return info;
    await page.waitForTimeout(1000);
  }
  return null;
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
    const body = await response.json().catch(async () => ({ text: await response.text() }));
    return { ok: response.ok, status: response.status, body };
  }, { info: backendInfo, routeValue: route, requestOptions: options });
}

async function snapshot(page, name, expectedText = []) {
  const filePath = path.join(appShotDir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  const text = await page.evaluate(() => document.body.innerText);
  const assertions = expectedText.map((expected) => ({
    expected,
    pass: text.toLowerCase().includes(expected.toLowerCase()),
  }));
  return {
    page: name,
    file_path: filePath,
    non_blank: fs.statSync(filePath).size > 10_000,
    assertions,
    pass: fs.statSync(filePath).size > 10_000 && assertions.every((item) => item.pass),
  };
}

async function clickNav(page, label) {
  await page.locator(".nav-rail").getByRole("button", { name: new RegExp(label, "i") }).click();
  await page.waitForTimeout(600);
}

async function main() {
  if (!fs.existsSync(exe)) {
    throw new Error(`Packaged EXE not found: ${exe}`);
  }

  const port = await freePort();
  const child = spawn(exe, [`--remote-debugging-port=${port}`], {
    cwd: path.dirname(exe),
    env: { ...process.env, SWAI_OUTPUT_DIR: path.join(root, "outputs") },
    stdio: "ignore",
    windowsHide: true,
  });

  const report = {
    packaged_exe_ok: false,
    generated_at: new Date().toISOString(),
    executable: exe,
    pid: child.pid,
    cdp_port: port,
    backend_health_ok: false,
    capability_count: 0,
    recipe_count: 0,
    mcp_tool_count: 0,
    mock_mounting_plate_completed: false,
    mock_task_id: "",
    mock_artifact_count: 0,
    screenshots: [],
    errors: [],
  };

  let browser;
  try {
    const version = await waitForCdp(port);
    browser = await chromium.connectOverCDP(version.webSocketDebuggerUrl);
    const context = browser.contexts()[0];
    let [page] = context.pages();
    if (!page) page = await context.waitForEvent("page", { timeout: 30000 });
    await page.setViewportSize({ width: 1480, height: 940 });
    await page.waitForLoadState("domcontentloaded");
    await page.getByRole("heading", { name: "Dashboard" }).waitFor({ timeout: 90000 });

    const backendInfo = await waitForBackendInfo(page);
    if (!backendInfo) {
      throw new Error("Packaged app did not expose backend bridge.");
    }

    const health = await apiFetch(page, backendInfo, "/api/health");
    report.backend_health_ok = Boolean(health.ok && health.body?.ok);
    const capabilities = await apiFetch(page, backendInfo, "/api/ai-capabilities");
    const recipes = await apiFetch(page, backendInfo, "/api/recipes");
    const tools = await apiFetch(page, backendInfo, "/api/mcp/tools");
    report.capability_count = Number(capabilities.body?.total ?? 0);
    report.recipe_count = Number(recipes.body?.total ?? 0);
    report.mcp_tool_count = Number(tools.body?.total ?? 0);

    report.screenshots.push(await snapshot(page, "01-dashboard", ["AI Capability Workbench", "Capabilities", "Recipes"]));
    await clickNav(page, "Capabilities");
    await page.getByText("mounting_plate", { exact: true }).waitFor({ timeout: 30000 });
    report.screenshots.push(await snapshot(page, "02-capabilities", ["Plan", "mounting_plate"]));

    await page.locator("article").filter({ hasText: "mounting_plate" }).getByRole("button", { name: "Mock Plan" }).click();
    await page.getByText("当前任务").waitFor({ timeout: 30000 });
    await page.getByRole("button", { name: "Generate Script" }).click();
    await page.getByRole("button", { name: "Static Validation" }).click();
    await page.getByRole("button", { name: "Approval" }).click();
    await page.getByRole("button", { name: "Execute" }).click();
    await page.getByText('"status": "completed"').waitFor({ timeout: 30000 });
    report.screenshots.push(await snapshot(page, "03-mock-task-completed", ['"status": "completed"', '"mock_demo": true']));

    const tasks = await apiFetch(page, backendInfo, "/api/tasks");
    const latest = (tasks.body?.tasks ?? []).find((item) => item.recipe_id === "mounting_plate" && item.status === "completed") ?? tasks.body?.tasks?.[0];
    report.mock_mounting_plate_completed = Boolean(latest?.recipe_id === "mounting_plate" && latest?.status === "completed" && latest?.mock_demo === true);
    report.mock_task_id = latest?.task_id ?? "";
    report.mock_artifact_count = latest?.artifacts?.length ?? 0;

    await clickNav(page, "Tasks");
    report.screenshots.push(await snapshot(page, "04-task-history", ["任务历史", "artifacts"]));
    await clickNav(page, "Integration");
    report.screenshots.push(await snapshot(page, "05-integration", ["SolidWorks", "Registry"]));
    await clickNav(page, "Developer");
    report.screenshots.push(await snapshot(page, "06-developer", ["Skill", "MCP"]));
    await clickNav(page, "Settings");
    report.screenshots.push(await snapshot(page, "07-settings", ["LLM Profile", "API Key"]));

    report.packaged_exe_ok =
      report.backend_health_ok &&
      report.capability_count === 27 &&
      report.recipe_count === 14 &&
      report.mcp_tool_count === 16 &&
      report.mock_mounting_plate_completed &&
      report.mock_artifact_count >= 5 &&
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
      });
    }
  }

  const manifestPath = path.join(root, "outputs", "visual_validation", "latest", "screenshot_manifest.json");
  fs.writeFileSync(manifestPath, JSON.stringify({ screenshots: report.screenshots }, null, 2), "utf8");
  const runtimeJson = path.join(validationRoot, "PACKAGED_EXE_RUNTIME_REPORT.json");
  fs.writeFileSync(runtimeJson, JSON.stringify(report, null, 2), "utf8");
  const runtimeMd = path.join(validationRoot, "PACKAGED_EXE_RUNTIME_REPORT.md");
  fs.writeFileSync(
    runtimeMd,
    [
      "# Packaged EXE Runtime Report",
      "",
      `packaged_exe_ok=${report.packaged_exe_ok}`,
      `backend_health_ok=${report.backend_health_ok}`,
      `capability_count=${report.capability_count}`,
      `recipe_count=${report.recipe_count}`,
      `mcp_tool_count=${report.mcp_tool_count}`,
      `mock_mounting_plate_completed=${report.mock_mounting_plate_completed}`,
      `mock_task_id=${report.mock_task_id}`,
      `mock_artifact_count=${report.mock_artifact_count}`,
      "",
      "## Screenshots",
      ...report.screenshots.map((item) => `- ${item.page}: ${item.pass} ${item.file_path}`),
      "",
      "## Errors",
      ...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ["- none"]),
      "",
    ].join("\n"),
    "utf8",
  );
  console.log(JSON.stringify({
    packaged_exe_ok: report.packaged_exe_ok,
    screenshots: report.screenshots.length,
    capability_count: report.capability_count,
    recipe_count: report.recipe_count,
    mcp_tool_count: report.mcp_tool_count,
    mock_task_id: report.mock_task_id,
  }, null, 2));
  if (!report.packaged_exe_ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
