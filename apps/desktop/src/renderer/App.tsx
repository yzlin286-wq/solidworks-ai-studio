import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { CommandPalette } from "./components/CommandPalette";
import { Onboarding } from "./components/Onboarding";
import { Shell } from "./components/Shell";
import { api } from "./lib/api";
import { zhCN } from "./lib/copy/zhCN";
import type {
  AIPlanResponse,
  ConfigResponse,
  GenerateScriptResponse,
  HealthResponse,
  MCPStatusResponse,
  PreflightResponse,
  Capability,
  RealTestRunResponse,
  RunRecord,
  SkillIndexResponse,
  SolidWorksActionResponse,
  TestConnectionResponse,
  ViewKey
} from "./lib/types";
import { ExecutionMonitorPage } from "./pages/ExecutionMonitorPage";
import { FilesPage } from "./pages/FilesPage";
import { ReviewCenterPage } from "./pages/ReviewCenterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillBrowserPage } from "./pages/SkillBrowserPage";
import { WorkspacePage } from "./pages/WorkspacePage";

export default function App() {
  const [view, setView] = useState<ViewKey>("onboarding");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [skills, setSkills] = useState<SkillIndexResponse | null>(null);
  const [mcp, setMcp] = useState<MCPStatusResponse | null>(null);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [realReport, setRealReport] = useState<RealTestRunResponse | null>(null);
  const [plan, setPlan] = useState<AIPlanResponse | null>(null);
  const [generated, setGenerated] = useState<GenerateScriptResponse | null>(null);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [lastAction, setLastAction] = useState<SolidWorksActionResponse | null>(null);
  const [llmConnection, setLlmConnection] = useState<TestConnectionResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const configValue = config?.config ?? null;
  const activeProfileId = configValue?.active_profile_id ?? "ccagent";
  const outputDir = configValue?.output_dir ?? "";
  const llmVerified = Boolean(llmConnection?.ok && llmConnection.chat_verified);
  const llmBlockReason = llmConnection
    ? `LLM Provider 未通过验证：${llmConnection.message}`
    : "请先在设置页点击“测试连接”，通过真实 Provider 验证后再生成。";
  const solidworksReady = Boolean(preflight?.can_run_real_com);
  const solidworksBlockReason = preflight
    ? `SolidWorks 真实执行未就绪：${preflight.state || preflight.checks.find((check) => check.status === "fail")?.message || "预检未通过"}`
    : "请先运行健康检查，确认 SolidWorks COM 预检通过。";

  async function refreshAll(): Promise<void> {
    setError(null);
    const [healthValue, configValueNext, preflightValue, skillsValue, mcpValue, capabilitiesValue, realReportValue] =
      await Promise.allSettled([
        api.health(),
        api.config(),
        api.preflight(),
        api.skills(),
        api.mcpStatus(),
        api.capabilities(),
        api.realTestReport()
      ]);
    const failures: string[] = [];
    if (healthValue.status === "fulfilled") {
      setHealth(healthValue.value);
    } else {
      failures.push(`health：${failureMessage(healthValue.reason)}`);
    }
    if (configValueNext.status === "fulfilled") {
      setConfig(configValueNext.value);
      document.documentElement.dataset.theme =
        configValueNext.value.config.theme === "system" ? "dark" : configValueNext.value.config.theme;
    } else {
      failures.push(`config：${failureMessage(configValueNext.reason)}`);
    }
    if (preflightValue.status === "fulfilled") {
      setPreflight(preflightValue.value);
    } else {
      failures.push(`preflight：${failureMessage(preflightValue.reason)}`);
    }
    if (skillsValue.status === "fulfilled") {
      setSkills(skillsValue.value);
    } else {
      failures.push(`skills：${failureMessage(skillsValue.reason)}`);
    }
    if (mcpValue.status === "fulfilled") {
      setMcp(mcpValue.value);
    } else {
      failures.push(`mcp：${failureMessage(mcpValue.reason)}`);
    }
    if (capabilitiesValue.status === "fulfilled") {
      setCapabilities(capabilitiesValue.value.capabilities);
    } else {
      failures.push(`capabilities：${failureMessage(capabilitiesValue.reason)}`);
    }
    if (realReportValue.status === "fulfilled") {
      setRealReport(realReportValue.value);
    }
    if (failures.length > 0) {
      setError(`${zhCN.backendErrors.refreshFailed}：${failures.slice(0, 3).join("；")}`);
    }
  }

  function failureMessage(reason: unknown): string {
    const raw = reason instanceof Error ? reason.message : String(reason);
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
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
        return [detail.message, ...checks].filter(Boolean).join("；") || raw;
      }
    } catch {
      return raw;
    }
    return raw;
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    const removeSettings = window.swai?.onNavigateSettings(() => setView("settings"));
    const removeMcp = window.swai?.onExportMcpConfig(() => setView("settings"));
    return () => {
      removeSettings?.();
      removeMcp?.();
    };
  }, []);

  useEffect(() => {
    if (!run || run.stage === "done" || run.stage === "failed") {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        setRun(await api.run(run.run_id));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : zhCN.backendErrors.runRefreshFailed);
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [run]);

  const body = useMemo(() => {
    if (view === "workspace") {
      return (
        <WorkspacePage
          config={configValue}
          preflight={preflight}
          plan={plan}
          generated={generated}
          run={run}
          busy={busy}
          lastAction={lastAction}
          capabilities={capabilities}
          llmVerified={llmVerified}
          llmBlockReason={llmBlockReason}
          canRunRealSolidWorks={solidworksReady}
          solidworksBlockReason={solidworksBlockReason}
          onPlan={handlePlan}
          onGenerate={handleGenerate}
          onApprove={handleApprove}
          onTool={handleTool}
          onCapabilityRun={handleCapabilityRun}
        />
      );
    }
    if (view === "skills") {
      return <SkillBrowserPage skills={skills} capabilities={capabilities} busy={busy} onSync={handleSyncSkills} />;
    }
    if (view === "monitor") {
      return <ExecutionMonitorPage run={run} />;
    }
    if (view === "review") {
      return <ReviewCenterPage run={run} lastAction={lastAction} onCopyReviewPrompt={handleCopyReviewPrompt} />;
    }
    if (view === "files") {
      return <FilesPage run={run} lastAction={lastAction} />;
    }
    return (
      <SettingsPage
        configResponse={config}
        mcp={mcp}
        busy={busy}
        onSave={handleSaveConfig}
        onConnectionTest={setLlmConnection}
        onMcpStart={handleMcpStart}
        onMcpStop={handleMcpStop}
      />
    );
  }, [
    busy,
    capabilities,
    config,
    configValue,
    generated,
    lastAction,
    llmBlockReason,
    llmVerified,
    mcp,
    plan,
    preflight,
    run,
    skills,
    solidworksBlockReason,
    solidworksReady,
    view
  ]);

  async function withBusy(work: () => Promise<void>): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await work();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : zhCN.backendErrors.operationFailed);
    } finally {
      setBusy(false);
    }
  }

  async function handlePlan(prompt: string): Promise<void> {
    if (!llmVerified) {
      setError(llmBlockReason);
      setView("settings");
      return;
    }
    await withBusy(async () => {
      const response = await api.plan(prompt, activeProfileId, outputDir);
      if (response.demo_mode) {
        setPlan(null);
        throw new Error("Provider 返回了非真实规划标记，已拒绝继续。");
      }
      setPlan(response);
      setView("workspace");
    });
  }

  async function handleGenerate(prompt: string): Promise<void> {
    if (!llmVerified) {
      setError(llmBlockReason);
      setView("settings");
      return;
    }
    await withBusy(async () => {
      const response = await api.generateScript(prompt, activeProfileId, outputDir);
      if (response.demo_mode || response.fallback_used) {
        setGenerated(null);
        throw new Error("Provider 返回了非真实生成标记，已拒绝写入和审批。");
      }
      setGenerated(response);
      setPlan({
        plan: response.plan,
        risks: response.risks,
        required_files: response.required_files,
        prompt,
        demo_mode: response.demo_mode
      });
      setView("workspace");
    });
  }

  async function handleApprove(): Promise<void> {
    if (!generated) {
      return;
    }
    if (generated.demo_mode || generated.fallback_used) {
      setError("非真实脚本禁止执行。");
      return;
    }
    if (!solidworksReady) {
      setError(solidworksBlockReason);
      return;
    }
    await withBusy(async () => {
      const created = await api.approveRun(generated.script_path, plan?.prompt ?? "");
      const record = await api.run(created.run_id);
      setRun(record);
      setView("monitor");
    });
  }

  async function handleTool(tool: string): Promise<void> {
    await withBusy(async () => {
      if (tool === "health") {
        setPreflight(await api.preflight());
        return;
      }
      if (tool === "connect") {
        setLastAction(await api.connect());
        return;
      }
      if (tool === "new-part") {
        setLastAction(await api.createBasicPart("box"));
        return;
      }
      if (tool === "open") {
        setLastAction(await api.openDocument());
        return;
      }
      if (tool === "save") {
        setLastAction(await api.saveDocument(""));
        return;
      }
      if (tool === "export-step") {
        setLastAction(await api.exportActive("STEP", ""));
        return;
      }
      if (tool === "export-stl") {
        setLastAction(await api.exportActive("STL", ""));
        return;
      }
      if (tool === "export-pdf") {
        setLastAction(await api.exportActive("PDF", ""));
        return;
      }
      if (tool === "export-dxf") {
        setLastAction(await api.exportActive("DXF", ""));
        return;
      }
      if (tool === "export-dwg") {
        setLastAction(await api.exportActive("DWG", ""));
        return;
      }
      if (tool === "review") {
        setLastAction(await api.reviewActive(""));
        setView("review");
        return;
      }
      if (tool === "create-basic-part") {
        setLastAction(await api.createBasicPart("box"));
        return;
      }
      if (tool === "mcp-start") {
        setMcp(await api.mcpStart());
        return;
      }
      if (tool === "mcp-stop") {
        setMcp(await api.mcpStop());
      }
    });
  }

  async function handleCapabilityRun(capabilityId: string): Promise<void> {
    await withBusy(async () => {
      const record = await api.runCapability(capabilityId, {});
      setLastAction({
        ok: record.status === "passed",
        mode: "solidworks",
        action: capabilityId,
        message: `${capabilityId} ${record.status === "passed" ? "通过" : record.status}`,
        stdout: record.stdout,
        stderr: record.stderr,
        files: record.created_files,
        real_execution_verified: record.real_execution_verified,
        evidence: record.evidence,
        active_document_before: record.active_document_before,
        active_document_after: record.active_document_after,
        created_files_exist: record.created_files_exist,
        data: {
          run_id: record.run_id,
          active_document_before: record.active_document_before,
          active_document_after: record.active_document_after,
          error_summary: record.error_summary,
          evidence: record.evidence
        }
      });
    });
  }

  async function handleSyncSkills(): Promise<void> {
    const confirmed = window.confirm(zhCN.confirmations.syncSkills);
    if (!confirmed) {
      return;
    }
    await withBusy(async () => {
      await api.syncSkills();
      setSkills(await api.skills());
    });
  }

  async function handleSaveConfig(nextConfig: ConfigResponse["config"]): Promise<void> {
    await withBusy(async () => {
      const response = await api.saveConfig({ ...nextConfig, mock_mode: false });
      setConfig(response);
      setLlmConnection(null);
      document.documentElement.dataset.theme = response.config.theme === "system" ? "dark" : response.config.theme;
    });
  }

  async function handleMcpStart(): Promise<void> {
    await withBusy(async () => setMcp(await api.mcpStart()));
  }

  async function handleMcpStop(): Promise<void> {
    await withBusy(async () => setMcp(await api.mcpStop()));
  }

  function handleCopyReviewPrompt(): void {
    const text = `${zhCN.reviewPrompt} Run ID: ${run?.run_id ?? "none"}。最近动作：${lastAction?.action ?? "none"}。`;
    void navigator.clipboard.writeText(text);
  }

  if (view === "onboarding") {
    return (
      <>
        <Onboarding
          health={health}
          config={config}
          preflight={preflight}
          skills={skills}
          realReport={realReport}
          onEnter={() => setView("workspace")}
          onRefresh={refreshAll}
        />
        {error ? <div className="global-error" role="alert">{error}</div> : null}
      </>
    );
  }

  return (
    <>
      <Shell
        view={view}
        onNavigate={setView}
        health={health}
        preflight={preflight}
          mcp={mcp}
          llmConnection={llmConnection}
          onPaletteOpen={() => setPaletteOpen(true)}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            {error ? <div className="inline-error" role="alert">{error}</div> : null}
            {body}
          </motion.div>
        </AnimatePresence>
      </Shell>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} onNavigate={setView} onRefresh={() => void refreshAll()} />
    </>
  );
}
