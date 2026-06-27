import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { CommandPalette } from "./components/CommandPalette";
import { Shell } from "./components/Shell";
import { api } from "./lib/api";
import type {
  AIPlanResponse,
  AICapability,
  AppConfig,
  Capability,
  ConfigResponse,
  GenerateScriptResponse,
  HealthResponse,
  MCPStatusResponse,
  PreflightResponse,
  Recipe,
  RunRecord,
  SkillIndexResponse,
  SolidWorksActionResponse,
  TestConnectionResponse,
  ViewKey,
  WorkbenchTask
} from "./lib/types";
import { CapabilityGroupPage } from "./pages/CapabilityGroupPage";
import { DashboardPage } from "./pages/DashboardPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillBrowserPage } from "./pages/SkillBrowserPage";
import { TasksPage } from "./pages/TasksPage";
import { WorkspacePage } from "./pages/WorkspacePage";

export default function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [skills, setSkills] = useState<SkillIndexResponse | null>(null);
  const [mcp, setMcp] = useState<MCPStatusResponse | null>(null);
  const [legacyCapabilities, setLegacyCapabilities] = useState<Capability[]>([]);
  const [aiCapabilities, setAiCapabilities] = useState<AICapability[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [tasks, setTasks] = useState<WorkbenchTask[]>([]);
  const [selectedGroup, setSelectedGroup] = useState("AI CAD Studio");
  const [selectedCapabilityId, setSelectedCapabilityId] = useState("ai.parametric_part_generator");
  const [selectedTask, setSelectedTask] = useState<WorkbenchTask | null>(null);
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
  const llmBlockReason = llmConnection ? `LLM Provider 未通过验证：${llmConnection.message}` : "请先在 Settings 测试真实 LLM Provider。";
  const solidworksReady = Boolean(preflight?.can_run_real_com);
  const solidworksBlockReason = preflight ? `SolidWorks preflight 未通过：${preflight.state || "not ready"}` : "请先运行健康检查。";

  async function refreshAll(): Promise<void> {
    setError(null);
    const results = await Promise.allSettled([
      api.health(),
      api.config(),
      api.preflight(),
      api.skills(),
      api.mcpStatus(),
      api.capabilities(),
      api.aiCapabilities(),
      api.recipes(),
      api.tasks()
    ]);
    if (results[0].status === "fulfilled") setHealth(results[0].value);
    if (results[1].status === "fulfilled") setConfig(results[1].value);
    if (results[2].status === "fulfilled") setPreflight(results[2].value);
    if (results[3].status === "fulfilled") setSkills(results[3].value);
    if (results[4].status === "fulfilled") setMcp(results[4].value);
    if (results[5].status === "fulfilled") setLegacyCapabilities(results[5].value.capabilities);
    if (results[6].status === "fulfilled") setAiCapabilities(results[6].value.capabilities);
    if (results[7].status === "fulfilled") setRecipes(results[7].value.recipes);
    if (results[8].status === "fulfilled") setTasks(results[8].value.tasks);
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    const removeSettings = window.swai?.onNavigateSettings(() => setView("settings"));
    const removeMcp = window.swai?.onExportMcpConfig(() => setView("integration"));
    return () => {
      removeSettings?.();
      removeMcp?.();
    };
  }, []);

  const body = useMemo(() => {
    if (view === "dashboard") {
      return (
        <DashboardPage
          capabilities={aiCapabilities}
          recipes={recipes}
          tasks={tasks}
          onSelectGroup={(group) => {
            setSelectedGroup(group);
            setView("capabilities");
          }}
          onOpenCapability={(capabilityId) => {
            const capability = aiCapabilities.find((item) => item.id === capabilityId);
            setSelectedCapabilityId(capabilityId);
            setSelectedGroup(capability?.group ?? selectedGroup);
            setView("capabilities");
          }}
          onOpenTasks={() => setView("tasks")}
        />
      );
    }
    if (view === "capabilities") {
      return (
        <CapabilityGroupPage
          capabilities={aiCapabilities}
          recipes={recipes}
          selectedGroup={selectedGroup}
          selectedCapabilityId={selectedCapabilityId}
          selectedTask={selectedTask}
          busy={busy}
          onSelectGroup={(group) => {
            setSelectedGroup(group);
            const first = aiCapabilities.find((item) => item.group === group);
            if (first) setSelectedCapabilityId(first.id);
          }}
          onSelectCapability={setSelectedCapabilityId}
          onPlan={handleWorkbenchPlan}
          onGenerate={handleWorkbenchGenerate}
          onValidate={handleWorkbenchValidate}
          onApprove={handleWorkbenchApprove}
          onExecute={handleWorkbenchExecute}
        />
      );
    }
    if (view === "tasks") {
      return (
        <TasksPage
          tasks={tasks}
          onSelectTask={(task) => {
            setSelectedTask(task);
            setSelectedCapabilityId(task.capability_id);
            const capability = aiCapabilities.find((item) => item.id === task.capability_id);
            setSelectedGroup(capability?.group ?? selectedGroup);
            setView("capabilities");
          }}
        />
      );
    }
    if (view === "integration") {
      return (
        <WorkspacePage
          config={configValue}
          preflight={preflight}
          plan={plan}
          generated={generated}
          run={run}
          busy={busy}
          lastAction={lastAction}
          capabilities={legacyCapabilities}
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
    if (view === "developer") {
      return <SkillBrowserPage skills={skills} capabilities={legacyCapabilities} busy={busy} onSync={handleSyncSkills} />;
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
    aiCapabilities,
    busy,
    config,
    configValue,
    generated,
    lastAction,
    legacyCapabilities,
    llmBlockReason,
    llmVerified,
    mcp,
    plan,
    preflight,
    recipes,
    run,
    selectedCapabilityId,
    selectedGroup,
    selectedTask,
    skills,
    solidworksBlockReason,
    solidworksReady,
    tasks,
    view
  ]);

  async function withBusy(work: () => Promise<void>): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await work();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function refreshTasks(nextTask?: WorkbenchTask): Promise<void> {
    if (nextTask) setSelectedTask(nextTask);
    const response = await api.tasks();
    setTasks(response.tasks);
  }

  async function handleWorkbenchPlan(capabilityId: string, recipeId: string, mode: "mock" | "real"): Promise<void> {
    await withBusy(async () => {
      const recipe = recipes.find((item) => item.recipe_id === recipeId);
      const task = await api.workbenchPlan(capabilityId, recipeId, mode, recipe?.default_prompt ?? "");
      await refreshTasks(task);
    });
  }

  async function handleWorkbenchGenerate(capabilityId: string, taskId: string): Promise<void> {
    await withBusy(async () => refreshTasks(await api.workbenchGenerate(capabilityId, taskId)));
  }

  async function handleWorkbenchValidate(capabilityId: string, taskId: string): Promise<void> {
    await withBusy(async () => refreshTasks(await api.workbenchValidate(capabilityId, taskId)));
  }

  async function handleWorkbenchApprove(capabilityId: string, taskId: string): Promise<void> {
    await withBusy(async () => refreshTasks(await api.workbenchApprove(capabilityId, taskId)));
  }

  async function handleWorkbenchExecute(capabilityId: string, taskId: string): Promise<void> {
    await withBusy(async () => refreshTasks(await api.workbenchExecute(capabilityId, taskId)));
  }

  async function handlePlan(prompt: string): Promise<void> {
    if (!llmVerified) {
      setError(llmBlockReason);
      setView("settings");
      return;
    }
    await withBusy(async () => setPlan(await api.plan(prompt, activeProfileId, outputDir)));
  }

  async function handleGenerate(prompt: string): Promise<void> {
    if (!llmVerified) {
      setError(llmBlockReason);
      setView("settings");
      return;
    }
    await withBusy(async () => setGenerated(await api.generateScript(prompt, activeProfileId, outputDir)));
  }

  async function handleApprove(): Promise<void> {
    if (!generated || !solidworksReady) {
      setError(!generated ? "请先生成脚本。" : solidworksBlockReason);
      return;
    }
    await withBusy(async () => {
      const created = await api.approveRun(generated.script_path, plan?.prompt ?? "");
      setRun(await api.run(created.run_id));
    });
  }

  async function handleTool(tool: string): Promise<void> {
    await withBusy(async () => {
      if (tool === "health") setPreflight(await api.preflight());
      if (tool === "connect") setLastAction(await api.connect());
      if (tool === "new-part" || tool === "create-basic-part") setLastAction(await api.createBasicPart("box"));
      if (tool === "open") setLastAction(await api.openDocument());
      if (tool === "save") setLastAction(await api.saveDocument(""));
      if (tool === "export-step") setLastAction(await api.exportActive("STEP", ""));
      if (tool === "export-stl") setLastAction(await api.exportActive("STL", ""));
      if (tool === "export-pdf") setLastAction(await api.exportActive("PDF", ""));
      if (tool === "export-dxf") setLastAction(await api.exportActive("DXF", ""));
      if (tool === "export-dwg") setLastAction(await api.exportActive("DWG", ""));
      if (tool === "review") setLastAction(await api.reviewActive(""));
      if (tool === "mcp-start") setMcp(await api.mcpStart());
      if (tool === "mcp-stop") setMcp(await api.mcpStop());
    });
  }

  async function handleCapabilityRun(capabilityId: string): Promise<void> {
    await withBusy(async () => {
      const record = await api.runCapability(capabilityId, {});
      setLastAction({
        ok: record.status === "passed",
        mode: "solidworks",
        action: capabilityId,
        message: `${capabilityId} ${record.status}`,
        stdout: record.stdout,
        stderr: record.stderr,
        files: record.created_files,
        data: record.evidence,
        real_execution_verified: record.real_execution_verified,
        evidence: record.evidence,
        active_document_before: record.active_document_before,
        active_document_after: record.active_document_after,
        created_files_exist: record.created_files_exist
      });
    });
  }

  async function handleSyncSkills(): Promise<void> {
    await withBusy(async () => {
      await api.syncSkills();
      setSkills(await api.skills());
    });
  }

  async function handleSaveConfig(nextConfig: AppConfig): Promise<void> {
    await withBusy(async () => {
      const response = await api.saveConfig({ ...nextConfig, mock_mode: false });
      setConfig(response);
      setLlmConnection(null);
    });
  }

  async function handleMcpStart(): Promise<void> {
    await withBusy(async () => setMcp(await api.mcpStart()));
  }

  async function handleMcpStop(): Promise<void> {
    await withBusy(async () => setMcp(await api.mcpStop()));
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
          <motion.div key={view} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.18 }}>
            {error ? <div className="inline-error" role="alert">{error}</div> : null}
            {body}
          </motion.div>
        </AnimatePresence>
      </Shell>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} onNavigate={setView} onRefresh={() => void refreshAll()} />
    </>
  );
}

