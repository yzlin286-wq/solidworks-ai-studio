import type { AIPlanResponse, AppConfig, Capability, GenerateScriptResponse, PreflightResponse, RunRecord, SolidWorksActionResponse } from "../lib/types";
import { DirectTools } from "../components/DirectTools";
import { PromptComposer } from "../components/PromptComposer";
import { StatusBadge } from "../components/StatusBadge";
import { Timeline } from "../components/Timeline";
import { modeLabel, preflightBadgeStatus, preflightStatusLabel, stageLabel, zhCN } from "../lib/copy/zhCN";

interface WorkspacePageProps {
  config: AppConfig | null;
  preflight: PreflightResponse | null;
  plan: AIPlanResponse | null;
  generated: GenerateScriptResponse | null;
  run: RunRecord | null;
  busy: boolean;
  lastAction: SolidWorksActionResponse | null;
  capabilities: Capability[];
  llmVerified: boolean;
  llmBlockReason: string;
  canRunRealSolidWorks: boolean;
  solidworksBlockReason: string;
  onPlan: (prompt: string) => Promise<void>;
  onGenerate: (prompt: string) => Promise<void>;
  onApprove: () => Promise<void>;
  onTool: (tool: string) => Promise<void>;
  onCapabilityRun: (capabilityId: string) => Promise<void>;
}

export function WorkspacePage({
  config,
  preflight,
  plan,
  generated,
  run,
  busy,
  lastAction,
  capabilities,
  llmVerified,
  llmBlockReason,
  canRunRealSolidWorks,
  solidworksBlockReason,
  onPlan,
  onGenerate,
  onApprove,
  onTool,
  onCapabilityRun
}: WorkspacePageProps) {
  return (
    <div className="workspace-grid">
      <PromptComposer
        activeProfileId={config?.active_profile_id ?? "openai"}
        outputDir={config?.output_dir ?? ""}
        plan={plan}
        generated={generated}
        busy={busy}
        llmVerified={llmVerified}
        llmBlockReason={llmBlockReason}
        canRunRealSolidWorks={canRunRealSolidWorks}
        solidworksBlockReason={solidworksBlockReason}
        onPlan={onPlan}
        onGenerate={onGenerate}
        onApprove={onApprove}
      />
      <aside className="session-panel" aria-label="SolidWorks 会话状态">
        <section>
          <p className="eyebrow">{zhCN.workspace.session}</p>
          <h2>{preflight?.can_run_real_com ? zhCN.workspace.liveLane : zhCN.workspace.blockedLane}</h2>
          <StatusBadge status={preflightBadgeStatus(preflight)} label={preflightStatusLabel(preflight)} />
          <dl>
            <div>
              <dt>预检状态</dt>
              <dd>{preflight?.state || modeLabel(preflight?.mode)}</dd>
            </div>
            <div>
              <dt>{zhCN.workspace.currentDocument}</dt>
              <dd>{lastAction?.active_document_after || lastAction?.active_document_before || (lastAction?.data.document ? String(lastAction.data.document) : zhCN.workspace.noDocument)}</dd>
            </div>
            <div>
              <dt>{zhCN.workspace.outputPath}</dt>
              <dd>{config?.output_dir || zhCN.workspace.userDataOutput}</dd>
            </div>
            <div>
              <dt>{zhCN.workspace.approval}</dt>
              <dd>{config?.require_approval ? zhCN.workspace.approvalRequired : zhCN.workspace.approvalRecommended}</dd>
            </div>
          </dl>
          {lastAction ? (
            <div className="evidence-panel compact">
              <strong>{zhCN.tools.realEvidence}</strong>
              <span>{lastAction.real_execution_verified ? zhCN.tools.verified : zhCN.tools.unverified}</span>
              <small>before: {lastAction.active_document_before || "未记录"}</small>
              <small>after: {lastAction.active_document_after || "未记录"}</small>
            </div>
          ) : null}
        </section>
        <DirectTools busy={busy} lastAction={lastAction} capabilities={capabilities} onTool={onTool} onCapabilityRun={onCapabilityRun} />
      </aside>
      <section className="bottom-run-panel">
        <div className="panel-heading compact">
          <div>
            <p className="eyebrow">{zhCN.workspace.timelineEyebrow}</p>
            <h2>{run ? `${zhCN.workspace.runPrefix} ${run.run_id.slice(0, 8)}` : zhCN.workspace.waitingApproval}</h2>
          </div>
          {run ? <StatusBadge status={run.stage === "failed" ? "fail" : run.stage === "done" ? "pass" : "info"} label={stageLabel(run.stage)} /> : null}
        </div>
        <Timeline events={run?.events ?? []} />
      </section>
    </div>
  );
}
