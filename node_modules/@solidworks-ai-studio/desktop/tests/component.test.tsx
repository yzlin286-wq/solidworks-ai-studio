import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PromptComposer } from "../src/renderer/components/PromptComposer";
import { Timeline } from "../src/renderer/components/Timeline";
import { SettingsPage } from "../src/renderer/pages/SettingsPage";
import { SkillBrowserPage } from "../src/renderer/pages/SkillBrowserPage";
import { ReviewCenterPage } from "../src/renderer/pages/ReviewCenterPage";
import type { AppConfig, ConfigResponse, SkillIndexResponse } from "../src/renderer/lib/types";

const config: AppConfig = {
  profiles: [
    {
      id: "openai",
      name: "OpenAI",
      api_base_url: "https://api.openai.com/v1",
      api_key: "",
      model: "gpt-4.1",
      temperature: 0.2,
      max_tokens: 2200,
      timeout_seconds: 60
    }
  ],
  active_profile_id: "openai",
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
};

const configResponse: ConfigResponse = {
  config,
  config_path: "config.json",
  secure_storage: "config-file",
  note: "Local config file."
};

const skills: SkillIndexResponse = {
  solidworks_available: true,
  taste_available: true,
  solidworks_path: "vendor/skills/solidworks-automation",
  taste_path: "vendor/skills/taste-skill",
  indexed_at: new Date().toISOString(),
  documents: [
    {
      title: "SolidWorks automation",
      path: "SKILL.md",
      kind: "skill",
      modified_at: null,
      excerpt: "part assembly drawing export review"
    }
  ],
  functions: [
    {
      name: "session",
      signature: "session()",
      module: "sw_session",
      doc: "Create a session"
    }
  ],
  mcp_tools: ["solidworks_health_check"],
  context_summary: "SolidWorks automation skill summary"
};

describe("renderer components", () => {
  it("renders prompt composer controls", () => {
    render(
      <PromptComposer
        activeProfileId="openai"
        outputDir=""
        plan={null}
        generated={null}
        busy={false}
        llmVerified={true}
        llmBlockReason=""
        canRunRealSolidWorks={true}
        solidworksBlockReason=""
        onPlan={vi.fn()}
        onGenerate={vi.fn()}
        onApprove={vi.fn()}
      />
    );

    expect(screen.getByText("自然语言生成可审查的 SolidWorks Python")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成 Script/i })).toBeEnabled();
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

    expect(screen.getByRole("button", { name: /生成 Script/i })).toBeDisabled();
    expect(screen.getByText("请先测试连接")).toBeInTheDocument();
  });

  it("renders skill browser indexed content", () => {
    render(<SkillBrowserPage skills={skills} capabilities={[]} busy={false} onSync={vi.fn()} />);

    expect(screen.getByText("SolidWorks automation")).toBeInTheDocument();
    expect(screen.getByText("solidworks_health_check")).toBeInTheDocument();
  });

  it("renders timeline empty and populated states", () => {
    const { rerender } = render(<Timeline events={[]} />);
    expect(screen.getByText(/还没有执行事件/i)).toBeInTheDocument();

    rerender(
      <Timeline
        events={[
          {
            time: new Date().toISOString(),
            stage: "done",
            message: "Script 执行完成。",
            stdout: "",
            stderr: ""
          }
        ]}
      />
    );
    expect(screen.getByText("Script 执行完成。")).toBeInTheDocument();
  });

  it("renders settings and review center", () => {
    render(
      <SettingsPage
        configResponse={configResponse}
        mcp={{ running: false, pid: null, command: [], tools: [], message: "stopped" }}
        busy={false}
        onSave={vi.fn()}
        onConnectionTest={vi.fn()}
        onMcpStart={vi.fn()}
        onMcpStop={vi.fn()}
      />
    );
    expect(screen.getByText("LLM Profile")).toBeInTheDocument();

    render(<ReviewCenterPage run={null} lastAction={null} onCopyReviewPrompt={vi.fn()} />);
    expect(screen.getByText("几何检查、报告产物与迭代 Prompt")).toBeInTheDocument();
  });
});
