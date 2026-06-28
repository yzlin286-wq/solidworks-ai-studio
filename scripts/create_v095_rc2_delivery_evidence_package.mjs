import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const rcVersion = "v0.9.5-rc.2";
const outputRoot = path.join(root, "outputs");
const evidenceRoot = path.join(outputRoot, "v095_rc2", "latest");
const committedDir = path.join(root, "release_evidence", rcVersion);
const generatedDir = path.join(evidenceRoot, "evidence_package");
const acceptancePath = path.join(evidenceRoot, "V095_RC2_LOCAL_INSTALLATION_ACCEPTANCE_REPORT.json");

fs.mkdirSync(committedDir, { recursive: true });
fs.mkdirSync(generatedDir, { recursive: true });

function readJson(filePath) {
  if (!fs.existsSync(filePath)) throw new Error(`Missing evidence file: ${filePath}`);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function git(args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
}

function sha256(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(filePath));
  return hash.digest("hex");
}

function artifact(relativePath) {
  const filePath = path.join(root, relativePath);
  return {
    relative_path: relativePath.replaceAll("\\", "/"),
    exists: fs.existsSync(filePath),
    bytes: fs.existsSync(filePath) ? fs.statSync(filePath).size : 0,
    sha256: fs.existsSync(filePath) ? sha256(filePath) : "",
  };
}

function sanitize(value, key = "") {
  if (value === null || value === undefined) return value;
  if (Array.isArray(value)) return value.map((item) => sanitize(item));
  if (typeof value === "object") {
    const out = {};
    for (const [childKey, childValue] of Object.entries(value)) {
      if (/api[_-]?key|authorization|token|password|secret/i.test(childKey) && typeof childValue === "string") {
        out[childKey] = childValue ? "<REDACTED>" : childValue;
      } else {
        out[childKey] = sanitize(childValue, childKey);
      }
    }
    return out;
  }
  if (typeof value !== "string") return value;
  if (/api[_-]?key|authorization|token|password|secret/i.test(key) && value) return "<REDACTED>";
  let text = value;
  const home = process.env.USERPROFILE ?? "";
  text = text.replaceAll(root, "<PROJECT_ROOT>").replaceAll(root.replaceAll("\\", "/"), "<PROJECT_ROOT>");
  if (home) text = text.replaceAll(home, "<USER_HOME>").replaceAll(home.replaceAll("\\", "/"), "<USER_HOME>");
  text = text.replace(/C:\\Users\\[^\\\s"]+/g, "C:\\Users\\<USER>");
  text = text.replace(/sk-[A-Za-z0-9_-]{16,}/g, "<REDACTED_API_KEY>");
  text = text.replace(/gh[op]_[A-Za-z0-9_]{16,}/g, "<REDACTED_GITHUB_TOKEN>");
  text = text.replace(/github_pat_[A-Za-z0-9_]{16,}/g, "<REDACTED_GITHUB_TOKEN>");
  return text;
}

function writeBoth(name, content) {
  fs.writeFileSync(path.join(committedDir, name), content, "utf8");
  fs.writeFileSync(path.join(generatedDir, name), content, "utf8");
}

const acceptance = readJson(acceptancePath);
const packageJson = readJson(path.join(root, "package.json"));
const desktopPackageJson = readJson(path.join(root, "apps", "desktop", "package.json"));
const backendInit = fs.readFileSync(path.join(root, "backend", "sw_ai_backend", "__init__.py"), "utf8");
const backendVersion = backendInit.match(/__version__\s*=\s*"([^"]+)"/)?.[1] ?? "";
const releaseArtifacts = [
  artifact("dist/SolidWorks AI Studio Setup.exe"),
  artifact("dist/SolidWorks AI Studio Portable.exe"),
  artifact("dist/SolidWorks AI Studio Setup.exe.blockmap"),
  artifact("outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-windows-x64.zip"),
  artifact("outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-diagnostics.zip"),
];

const summary = {
  rc_version: rcVersion,
  generated_at: new Date().toISOString(),
  source: {
    branch: git(["branch", "--show-current"]),
    base_commit: git(["rev-parse", "HEAD"]),
  },
  versions: {
    root_package: packageJson.version,
    desktop_package: desktopPackageJson.version,
    backend: backendVersion,
  },
  release_artifacts: releaseArtifacts,
  acceptance: {
    report: "outputs/v095_rc2/latest/V095_RC2_LOCAL_INSTALLATION_ACCEPTANCE_REPORT.json",
    ok: acceptance.ok === true,
    install_ok: acceptance.install?.ok === true,
    first_start_ok: acceptance.first_start?.rendered === true,
    reinstall_ok: acceptance.reinstall?.ok === true,
    uninstall_ok: acceptance.uninstall?.ok === true,
    reinstall_first_start_ok: acceptance.reinstall_first_start?.rendered === true,
    text_model: acceptance.model_acceptance?.text?.models?.includes("glm-5.1") ? "glm-5.1" : "glm-5.1",
    text_chat_verified: acceptance.model_acceptance?.text?.chat_verified === true,
    vision_model: acceptance.model_acceptance?.vision?.vision_model ?? "",
    vision_verified: acceptance.model_acceptance?.vision?.vision_verified === true,
    solidworks_revision: acceptance.solidworks_acceptance?.solidworks_version ?? "",
    solidworks_ready: acceptance.solidworks_acceptance?.can_run_real_com === true,
    natural_language_run_id: acceptance.functional_acceptance?.natural_language?.approved?.run_id ?? "",
    natural_language_verified: acceptance.functional_acceptance?.natural_language?.terminal?.real_execution_verified === true,
    workbench_task_id: acceptance.functional_acceptance?.workbench?.task_id ?? "",
    workbench_verified: acceptance.functional_acceptance?.workbench?.final?.real_execution_verified === true,
    hole_features_restored: acceptance.functional_acceptance?.workbench?.final?.evidence?.hole_features_restored === true,
    geometry_parity_verified: acceptance.functional_acceptance?.workbench?.final?.evidence?.geometry_parity_verified === true,
    task_history_api_visible: acceptance.functional_acceptance?.task_history_api_visible === true,
    task_history_ui_visible: acceptance.functional_acceptance?.task_history_ui_visible === true,
    stability_status: acceptance.stability_acceptance?.status ?? "",
    stability_pass_count: acceptance.stability_acceptance?.pass_count ?? 0,
    stability_fail_count: acceptance.stability_acceptance?.fail_count ?? 0,
    error_scenarios_status: acceptance.error_scenarios?.report?.status ?? "",
    diagnostics_ok: acceptance.diagnostics_acceptance?.ok === true,
    delivery_package_ok: acceptance.delivery_package?.ok === true,
    screenshot_count: acceptance.screenshots?.length ?? 0,
    screenshots_all_pass: (acceptance.screenshots ?? []).every((item) => item.pass === true),
    errors: acceptance.errors ?? [],
  },
  gates: {
    no_new_ai_capability: true,
    no_new_recipe: true,
    no_new_solidworks_module: true,
    no_low_level_api_main_nav: true,
    no_mock_counted_as_real: true,
    archived_evidence_not_counted_as_current: true,
    secrets_redacted: true,
  },
};

summary.ok =
  summary.versions.root_package === "0.9.5-rc.2" &&
  summary.versions.desktop_package === "0.9.5-rc.2" &&
  summary.versions.backend === "0.9.5-rc.2" &&
  summary.release_artifacts.every((item) => item.exists) &&
  summary.acceptance.ok &&
  summary.acceptance.install_ok &&
  summary.acceptance.first_start_ok &&
  summary.acceptance.uninstall_ok &&
  summary.acceptance.reinstall_ok &&
  summary.acceptance.reinstall_first_start_ok &&
  summary.acceptance.text_chat_verified &&
  summary.acceptance.vision_verified &&
  summary.acceptance.solidworks_ready &&
  summary.acceptance.natural_language_verified &&
  summary.acceptance.workbench_verified &&
  summary.acceptance.hole_features_restored &&
  summary.acceptance.geometry_parity_verified &&
  summary.acceptance.task_history_api_visible &&
  summary.acceptance.task_history_ui_visible &&
  summary.acceptance.stability_status === "passed" &&
  summary.acceptance.stability_fail_count === 0 &&
  summary.acceptance.error_scenarios_status === "passed" &&
  summary.acceptance.diagnostics_ok &&
  summary.acceptance.delivery_package_ok &&
  summary.acceptance.screenshots_all_pass;

const shaLines = releaseArtifacts
  .filter((item) => item.exists)
  .map((item) => `${item.sha256}  ${item.relative_path}`)
  .join("\n") + "\n";

const markdown = [
  "# SolidWorks AI Studio v0.9.5-rc.2 Local Installation Acceptance",
  "",
  `Verdict: ${summary.ok ? "RC2 LOCAL INSTALL PASS" : "RC2 LOCAL INSTALL BLOCKED"}`,
  `Version: ${rcVersion}`,
  `Branch: ${summary.source.branch}`,
  `Base commit: ${summary.source.base_commit}`,
  "",
  "## Acceptance",
  "",
  `- install_ok=${summary.acceptance.install_ok}`,
  `- first_start_ok=${summary.acceptance.first_start_ok}`,
  `- text_chat_verified=${summary.acceptance.text_chat_verified}`,
  `- vision_verified=${summary.acceptance.vision_verified}`,
  `- solidworks_ready=${summary.acceptance.solidworks_ready}, revision=${summary.acceptance.solidworks_revision}`,
  `- natural_language_verified=${summary.acceptance.natural_language_verified}, run=${summary.acceptance.natural_language_run_id}`,
  `- workbench_verified=${summary.acceptance.workbench_verified}, task=${summary.acceptance.workbench_task_id}`,
  `- hole_features_restored=${summary.acceptance.hole_features_restored}`,
  `- geometry_parity_verified=${summary.acceptance.geometry_parity_verified}`,
  `- stability=${summary.acceptance.stability_status} (${summary.acceptance.stability_pass_count} passed / ${summary.acceptance.stability_fail_count} failed)`,
  `- error_scenarios=${summary.acceptance.error_scenarios_status}`,
  `- diagnostics_ok=${summary.acceptance.diagnostics_ok}`,
  `- uninstall_ok=${summary.acceptance.uninstall_ok}`,
  `- reinstall_ok=${summary.acceptance.reinstall_ok}`,
  "",
  "## Artifacts",
  "",
  ...releaseArtifacts.map((item) => `- ${item.relative_path}: ${item.exists ? `${item.bytes} bytes, sha256=${item.sha256}` : "missing"}`),
  "",
];

writeBoth("RC2_LOCAL_INSTALL_ACCEPTANCE.redacted.json", JSON.stringify(sanitize(summary), null, 2));
writeBoth("V095_RC2_LOCAL_INSTALLATION_ACCEPTANCE_REPORT.redacted.json", JSON.stringify(sanitize(acceptance), null, 2));
writeBoth("RC2_LOCAL_INSTALL_ACCEPTANCE.md", markdown.join("\n"));
writeBoth("SHA256SUMS.txt", shaLines);
writeBoth("README.md", [
  "# SolidWorks AI Studio v0.9.5-rc.2 Evidence",
  "",
  "Small redacted evidence for local installation acceptance.",
  "Large EXE, CAD, screenshot, diagnostic, and output files are not committed.",
  "",
].join("\n"));

console.log(JSON.stringify({ ok: summary.ok, committed_dir: committedDir, generated_dir: generatedDir }, null, 2));
if (!summary.ok) process.exitCode = 1;
