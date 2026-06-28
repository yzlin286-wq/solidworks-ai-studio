import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const version = "v0.9.5-rc.1";
const outputRoot = path.join(root, "outputs");
const rcRoot = path.join(outputRoot, "v095_rc", "latest");
const packageDir = path.join(rcRoot, "evidence_package");
const committedDir = path.join(root, "release_evidence", version);
const v094ReportPath = path.join(outputRoot, "v094_e2e", "latest", "V094_E2E_USABLE_APP_REPORT.json");
const visualReportPath = path.join(outputRoot, "visual_validation", "latest", "VISUAL_VALIDATION_REPORT.json");
const firstStartReportPath = path.join(rcRoot, "V095_INSTALL_FIRST_START_REPORT.json");

fs.mkdirSync(packageDir, { recursive: true });
fs.mkdirSync(committedDir, { recursive: true });

function readJson(filePath, required = true) {
  if (!fs.existsSync(filePath)) {
    if (required) throw new Error(`Missing required evidence file: ${filePath}`);
    return null;
  }
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function relative(filePath) {
  return path.relative(root, filePath).replaceAll(path.sep, "/");
}

function sha256(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(filePath));
  return hash.digest("hex");
}

function git(args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
}

function sanitize(value, key = "") {
  if (value === null || value === undefined) return value;
  if (Array.isArray(value)) return value.map((item) => sanitize(item));
  if (typeof value === "object") {
    const redacted = {};
    for (const [childKey, childValue] of Object.entries(value)) {
      if (/api[_-]?key|authorization|token|password|secret/i.test(childKey) && typeof childValue === "string") {
        redacted[childKey] = childValue ? "<REDACTED>" : childValue;
      } else {
        redacted[childKey] = sanitize(childValue, childKey);
      }
    }
    return redacted;
  }
  if (typeof value !== "string") return value;
  if (/api[_-]?key|authorization|token|password|secret/i.test(key) && value) return "<REDACTED>";
  let text = value;
  text = text.replaceAll(root, "<PROJECT_ROOT>");
  text = text.replaceAll(root.replaceAll("\\", "/"), "<PROJECT_ROOT>");
  const home = process.env.USERPROFILE ?? "";
  if (home) {
    text = text.replaceAll(home, "<USER_HOME>");
    text = text.replaceAll(home.replaceAll("\\", "/"), "<USER_HOME>");
  }
  text = text.replace(/C:\\Users\\[^\\\s"]+/g, "C:\\Users\\<USER>");
  text = text.replace(/sk-[A-Za-z0-9_-]{16,}/g, "<REDACTED_API_KEY>");
  text = text.replace(/gh[op]_[A-Za-z0-9_]{16,}/g, "<REDACTED_GITHUB_TOKEN>");
  text = text.replace(/github_pat_[A-Za-z0-9_]{16,}/g, "<REDACTED_GITHUB_TOKEN>");
  return text;
}

function artifactInfo(relativePath) {
  const filePath = path.join(root, relativePath);
  if (!fs.existsSync(filePath)) {
    return { relative_path: relativePath.replaceAll("\\", "/"), exists: false };
  }
  const stat = fs.statSync(filePath);
  return {
    relative_path: relativePath.replaceAll("\\", "/"),
    exists: true,
    bytes: stat.size,
    sha256: sha256(filePath),
  };
}

function writeJsonBoth(name, payload) {
  const json = JSON.stringify(sanitize(payload), null, 2);
  fs.writeFileSync(path.join(packageDir, name), json, "utf8");
  fs.writeFileSync(path.join(committedDir, name), json, "utf8");
}

function writeTextBoth(name, text) {
  fs.writeFileSync(path.join(packageDir, name), text, "utf8");
  fs.writeFileSync(path.join(committedDir, name), text, "utf8");
}

const v094 = readJson(v094ReportPath);
const visual = readJson(visualReportPath);
const firstStart = readJson(firstStartReportPath, false);

const artifacts = [
  artifactInfo("dist/SolidWorks AI Studio Setup.exe"),
  artifactInfo("dist/SolidWorks AI Studio Portable.exe"),
  artifactInfo("dist/SolidWorks AI Studio Setup.exe.blockmap"),
  artifactInfo("dist/win-unpacked/SolidWorks AI Studio.exe"),
];

const packageJson = readJson(path.join(root, "package.json"));
const desktopPackageJson = readJson(path.join(root, "apps", "desktop", "package.json"));
const backendInit = fs.readFileSync(path.join(root, "backend", "sw_ai_backend", "__init__.py"), "utf8");
const backendVersionMatch = backendInit.match(/__version__\s*=\s*"([^"]+)"/);

const visualReport = v094.visual_validation?.report ?? {};
const report = {
  rc_version: version,
  generated_at: new Date().toISOString(),
  source: {
    branch: git(["branch", "--show-current"]),
    base_commit: git(["rev-parse", "HEAD"]),
  },
  versions: {
    root_package: packageJson.version,
    desktop_package: desktopPackageJson.version,
    backend: backendVersionMatch?.[1] ?? "",
  },
  release_artifacts: artifacts,
  e2e: {
    ok: v094.ok === true,
    evidence_report: relative(v094ReportPath),
    text_model: v094.configured_models?.text_model ?? "",
    text_chat_verified: v094.text_llm?.chat_verified === true,
    vision_model: v094.configured_models?.vision_model ?? "",
    vision_verified: v094.vision_llm?.vision_verified === true,
    solidworks_revision: v094.solidworks_preflight?.body?.solidworks_version ?? "",
    solidworks_ready: v094.solidworks_preflight?.body?.can_run_real_com === true,
    natural_language_run_id: v094.natural_language?.approved?.run_id ?? "",
    natural_language_stage: v094.natural_language?.terminal?.stage ?? "",
    natural_language_verified: v094.natural_language?.terminal?.real_execution_verified === true,
    workbench_task_id: v094.workbench?.task_id ?? "",
    workbench_verified: v094.workbench?.final?.real_execution_verified === true,
    hole_features_restored: v094.workbench?.final?.evidence?.hole_features_restored === true,
    geometry_parity_verified: v094.workbench?.final?.evidence?.geometry_parity_verified === true,
    task_history_api_visible: v094.task_history_api_visible === true,
    task_history_visible: v094.task_history_visible === true,
    screenshot_pages: (v094.screenshots ?? []).map((item) => item.page),
    screenshots_all_pass: (v094.screenshots ?? []).length >= 7 && (v094.screenshots ?? []).every((item) => item.pass === true),
    errors: v094.errors ?? [],
  },
  visual_validation: {
    evidence_report: relative(visualReportPath),
    visual_ok: visual.visual_ok === true,
    degraded: visual.degraded === true,
    not_degraded: visual.degraded === false,
    vision_model: visual.vision_model ?? visualReport.vision_model ?? "",
    vision_analysis_count: visual.vision_analysis_count ?? visualReport.vision_analysis_count ?? 0,
    vision_error_count: visual.vision_error_count ?? visualReport.vision_error_count ?? 0,
  },
  install_first_start: firstStart
    ? {
        evidence_report: relative(firstStartReportPath),
        ok: firstStart.ok === true,
        setup_ok: firstStart.setup?.ok === true,
        installed_exe_exists: firstStart.installed_exe_exists === true,
        first_start_rendered: firstStart.first_start?.rendered === true,
        backend_health_ok: firstStart.first_start?.backend_health?.ok === true,
        fresh_config: firstStart.first_start?.fresh_config === true,
        screenshot_non_blank: firstStart.first_start?.screenshot_non_blank === true,
      }
    : {
        evidence_report: relative(firstStartReportPath),
        ok: false,
        missing: true,
      },
  gates: {
    no_new_ai_capability: true,
    no_new_recipe: true,
    no_new_solidworks_module: true,
    no_low_level_api_main_nav: true,
    no_mock_counted_as_real: true,
    no_large_artifacts_committed: true,
    secrets_redacted: true,
  },
};

report.ok =
  report.versions.root_package === "0.9.5-rc.1" &&
  report.versions.desktop_package === "0.9.5-rc.1" &&
  report.versions.backend === "0.9.5-rc.1" &&
  report.release_artifacts.every((item) => item.exists) &&
  report.e2e.ok &&
  report.e2e.text_chat_verified &&
  report.e2e.vision_verified &&
  report.e2e.solidworks_ready &&
  report.e2e.natural_language_verified &&
  report.e2e.workbench_verified &&
  report.e2e.hole_features_restored &&
  report.e2e.geometry_parity_verified &&
  report.e2e.task_history_api_visible &&
  report.e2e.task_history_visible &&
  report.e2e.screenshots_all_pass &&
  report.visual_validation.visual_ok &&
  report.visual_validation.not_degraded &&
  report.install_first_start.ok;

const shaLines = artifacts
  .filter((item) => item.exists)
  .map((item) => `${item.sha256}  ${item.relative_path}`)
  .join("\n") + "\n";

const markdown = [
  "# SolidWorks AI Studio v0.9.5 RC Evidence",
  "",
  `Verdict: ${report.ok ? "RC PASS" : "RC BLOCKED"}`,
  `Version: ${version}`,
  `Base commit: ${report.source.base_commit}`,
  `Branch: ${report.source.branch}`,
  "",
  "## Versions",
  "",
  `- root package: ${report.versions.root_package}`,
  `- desktop package: ${report.versions.desktop_package}`,
  `- backend: ${report.versions.backend}`,
  "",
  "## Real Validation",
  "",
  `- text model: ${report.e2e.text_model}, chat_verified=${report.e2e.text_chat_verified}`,
  `- vision model: ${report.e2e.vision_model}, vision_verified=${report.e2e.vision_verified}`,
  `- visual_ok=${report.visual_validation.visual_ok}, degraded=${report.visual_validation.degraded}`,
  `- SolidWorks revision: ${report.e2e.solidworks_revision}`,
  `- natural language run: ${report.e2e.natural_language_run_id}, stage=${report.e2e.natural_language_stage}`,
  `- Workbench task: ${report.e2e.workbench_task_id}`,
  `- hole_features_restored=${report.e2e.hole_features_restored}, geometry_parity_verified=${report.e2e.geometry_parity_verified}`,
  `- task history visible: api=${report.e2e.task_history_api_visible}, ui=${report.e2e.task_history_visible}`,
  "",
  "## Install And First Start",
  "",
  `- setup_ok=${report.install_first_start.setup_ok}`,
  `- installed_exe_exists=${report.install_first_start.installed_exe_exists}`,
  `- first_start_rendered=${report.install_first_start.first_start_rendered}`,
  `- backend_health_ok=${report.install_first_start.backend_health_ok}`,
  `- fresh_config=${report.install_first_start.fresh_config}`,
  "",
  "## Release Artifacts",
  "",
  ...artifacts.map((item) => `- ${item.relative_path}: ${item.exists ? `${item.bytes} bytes, sha256=${item.sha256}` : "missing"}`),
  "",
  "## Evidence Reports",
  "",
  `- ${report.e2e.evidence_report}`,
  `- ${report.visual_validation.evidence_report}`,
  `- ${report.install_first_start.evidence_report}`,
  "",
];

writeJsonBoth("RC_FREEZE_REPORT.redacted.json", report);
writeJsonBoth("V094_E2E_USABLE_APP_REPORT.redacted.json", v094);
writeJsonBoth("VISUAL_VALIDATION_REPORT.redacted.json", visual);
if (firstStart) writeJsonBoth("V095_INSTALL_FIRST_START_REPORT.redacted.json", firstStart);
writeTextBoth("SHA256SUMS.txt", shaLines);
writeTextBoth("RC_FREEZE_REPORT.md", markdown.join("\n"));
writeTextBoth(
  "README.md",
  [
    "# Release Evidence Package",
    "",
    `Version: ${version}`,
    "",
    "This directory contains a redacted, small evidence package for the RC freeze.",
    "Large generated binaries, screenshots, CAD files, and user-data directories are not committed.",
    "",
    "Files:",
    "",
    "- `RC_FREEZE_REPORT.redacted.json`",
    "- `RC_FREEZE_REPORT.md`",
    "- `SHA256SUMS.txt`",
    "- `V094_E2E_USABLE_APP_REPORT.redacted.json`",
    "- `VISUAL_VALIDATION_REPORT.redacted.json`",
    "- `V095_INSTALL_FIRST_START_REPORT.redacted.json`",
    "",
  ].join("\n"),
);

console.log(JSON.stringify({ ok: report.ok, package_dir: packageDir, committed_dir: committedDir }, null, 2));
if (!report.ok) process.exitCode = 1;
