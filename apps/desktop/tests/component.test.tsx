import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Shell } from "../src/renderer/components/Shell";
import { PromptComposer } from "../src/renderer/components/PromptComposer";
import { CapabilityGroupPage } from "../src/renderer/pages/CapabilityGroupPage";
import { DashboardPage } from "../src/renderer/pages/DashboardPage";
import { TasksPage } from "../src/renderer/pages/TasksPage";
import type { AICapability, Recipe, WorkbenchTask } from "../src/renderer/lib/types";

const capabilities: AICapability[] = Array.from({ length: 27 }, (_, index) => ({
  id: index === 2 ? "ai.parametric_part_generator" : `ai.capability_${index + 1}`,
  title: index === 2 ? "参数化零件生成" : `能力 ${index + 1}`,
  group: index < 4 ? "Part & Manufacturing" : "Integration",
  status: "Ready Tool",
  maturity: "stable",
  ai_goal: "恢复 AI Capability Workbench。",
  user_intents: [],
  execution_modes: ["mock", "real"],
  requires: [],
  source_files: [],
  default_outputs: [],
  approval_required: true,
  source_missing: false,
  not_primary_entries: []
}));

const recipes: Recipe[] = Array.from({ length: 14 }, (_, index) => ({
  recipe_id: index === 0 ? "mounting_plate" : `recipe_${index + 1}`,
  capability_id: index === 0 ? "ai.parametric_part_generator" : capabilities[index % capabilities.length].id,
  title: index === 0 ? "安装板" : `Recipe ${index + 1}`,
  description: "Recipe 描述",
  parameters_schema: {},
  default_prompt: "生成 mounting_plate",
  mock_artifacts: ["artifact.json"],
  maturity: "stable",
  real_execution: "requires_solidworks"
}));

const task: WorkbenchTask = {
  task_id: "task-1",
  capability_id: "ai.parametric_part_generator",
  recipe_id: "mounting_plate",
  prompt: "生成 mounting_plate",
  execution_mode: "mock",
  status: "validated",
  plan: { summary: "plan" },
  script: "print('ok')",
  validation: { ok: true },
  approved: false,
  artifacts: [],
  evidence: {},
  error_summary: "",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  real_execution_verified: false,
  mock_demo: true
};

const profile = {
  id: "ccagent",
  name: "CCAgent",
  api_base_url: "https://api.ccagent.cn/v1",
  api_key: "",
  model: "glm-5.1",
  vision_model: "doubao-seed-2.0-pro",
  temperature: 0.2,
  max_tokens: 8192,
  timeout_seconds: 180
};

describe("AI Capability Workbench", () => {
  it("renders dashboard counts", () => {
    render(<DashboardPage capabilities={capabilities} recipes={recipes} tasks={[]} onSelectGroup={vi.fn()} onOpenCapability={vi.fn()} onOpenTasks={vi.fn()} />);

    expect(screen.getByText("AI Capability Workbench")).toBeInTheDocument();
    expect(screen.getByText("27")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });

  it("renders grouped capability sidebar", () => {
    renderWorkbench(task);

    expect(screen.getAllByText("Part & Manufacturing").length).toBeGreaterThan(0);
    expect(screen.getAllByText("参数化零件生成").length).toBeGreaterThan(0);
    expect(screen.getByText("mounting_plate")).toBeInTheDocument();
  });

  it("shows the approval workflow controls", () => {
    renderWorkbench(task);

    expect(screen.getByRole("button", { name: "Approval" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Execute" })).toBeDisabled();
  });

  it("renders task history", () => {
    render(<TasksPage tasks={[task]} onSelectTask={vi.fn()} />);

    expect(screen.getByText("任务历史与 artifacts")).toBeInTheDocument();
    expect(screen.getByText("task-1")).toBeInTheDocument();
  });

  it("renders shell without low-level direct tool nav", () => {
    render(
      <Shell view="dashboard" onNavigate={vi.fn()} health={null} llmConnection={null} preflight={null} mcp={null} onPaletteOpen={vi.fn()}>
        <div>content</div>
      </Shell>
    );

    expect(screen.getByRole("button", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Direct Tools/i })).not.toBeInTheDocument();
  });

  it("blocks prompt generation before LLM verification", () => {
    render(
      <PromptComposer
        activeProfileId="openai"
        outputDir=""
        plan={null}
        generated={null}
        busy={false}
        llmVerified={false}
        llmBlockReason="请先测试连接"
        canRunRealSolidWorks={true}
        solidworksBlockReason=""
        onPlan={vi.fn()}
        onGenerate={vi.fn()}
        onApprove={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /Script/i })).toBeDisabled();
    expect(screen.getByText("请先测试连接")).toBeInTheDocument();
  });

  it("keeps workflow first screen independent from SolidWorks", () => {
    render(<DashboardPage capabilities={capabilities} recipes={recipes} tasks={[task]} onSelectGroup={vi.fn()} onOpenCapability={vi.fn()} onOpenTasks={vi.fn()} />);

    expect(screen.getByText("Completed Tasks")).toBeInTheDocument();
    expect(screen.getByText("开始 mounting_plate")).toBeInTheDocument();
  });

  it("renders separate text and vision model settings", async () => {
    const { SettingsPage } = await import("../src/renderer/pages/SettingsPage");
    render(
      <SettingsPage
        configResponse={{
          config: {
            profiles: [profile],
            active_profile_id: "ccagent",
            theme: "dark",
            solidworks_skill_path: "vendor/skills/solidworks-automation",
            taste_skill_path: "vendor/skills/taste-skill",
            output_dir: "",
            validation_output_dir: "outputs/validation",
            part_template_path: "",
            assembly_template_path: "",
            drawing_template_path: "",
            require_approval: true,
            mock_mode: false
          },
          config_path: "config.json",
          secure_storage: "config-file",
          note: "local only"
        }}
        mcp={null}
        busy={false}
        onSave={vi.fn()}
        onConnectionTest={vi.fn()}
        onMcpStart={vi.fn()}
        onMcpStop={vi.fn()}
      />
    );

    expect(screen.getByText("文本 Model")).toBeInTheDocument();
    expect(screen.getByText("视觉 Model")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试视觉" })).toBeEnabled();
  });
});

function renderWorkbench(selectedTask: WorkbenchTask | null) {
  render(
    <CapabilityGroupPage
      capabilities={capabilities}
      recipes={recipes}
      selectedGroup="Part & Manufacturing"
      selectedCapabilityId="ai.parametric_part_generator"
      selectedTask={selectedTask}
      busy={false}
      onSelectGroup={vi.fn()}
      onSelectCapability={vi.fn()}
      onPlan={vi.fn()}
      onGenerate={vi.fn()}
      onValidate={vi.fn()}
      onApprove={vi.fn()}
      onExecute={vi.fn()}
    />
  );
}
