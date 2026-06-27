import { CheckCircle, GitBranch, Play, ShieldCheck } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import type { AICapability, Recipe, WorkbenchTask } from "../lib/types";

interface CapabilityGroupPageProps {
  capabilities: AICapability[];
  recipes: Recipe[];
  selectedGroup: string;
  selectedCapabilityId: string;
  selectedTask: WorkbenchTask | null;
  busy: boolean;
  onSelectGroup: (group: string) => void;
  onSelectCapability: (capabilityId: string) => void;
  onPlan: (capabilityId: string, recipeId: string, mode: "mock" | "real") => Promise<void>;
  onGenerate: (capabilityId: string, taskId: string) => Promise<void>;
  onValidate: (capabilityId: string, taskId: string) => Promise<void>;
  onApprove: (capabilityId: string, taskId: string) => Promise<void>;
  onExecute: (capabilityId: string, taskId: string) => Promise<void>;
}

export function CapabilityGroupPage({
  capabilities,
  recipes,
  selectedGroup,
  selectedCapabilityId,
  selectedTask,
  busy,
  onSelectGroup,
  onSelectCapability,
  onPlan,
  onGenerate,
  onValidate,
  onApprove,
  onExecute
}: CapabilityGroupPageProps) {
  const groups = Array.from(new Set(capabilities.map((item) => item.group)));
  const group = selectedGroup || groups[0] || "";
  const groupCapabilities = capabilities.filter((item) => item.group === group);
  const capability = capabilities.find((item) => item.id === selectedCapabilityId) ?? groupCapabilities[0] ?? capabilities[0];
  const capabilityRecipes = recipes.filter((item) => item.capability_id === capability?.id);
  const mountingPlate = capabilityRecipes.find((item) => item.recipe_id === "mounting_plate") ?? capabilityRecipes[0];

  return (
    <section className="capability-workbench">
      <aside className="group-sidebar" aria-label="Capability groups">
        {groups.map((item) => (
          <button key={item} type="button" className={item === group ? "active" : ""} onClick={() => onSelectGroup(item)}>
            <span>{item}</span>
            <strong>{capabilities.filter((capabilityItem) => capabilityItem.group === item).length}</strong>
          </button>
        ))}
      </aside>

      <div className="capability-list-pane">
        {groupCapabilities.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === capability?.id ? "capability-card active" : "capability-card"}
            onClick={() => onSelectCapability(item.id)}
          >
            <strong>{item.title}</strong>
            <span>{item.id}</span>
            <small>{item.status}</small>
          </button>
        ))}
      </div>

      <section className="capability-detail-pane">
        {capability ? (
          <>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">{capability.group}</p>
                <h2>{capability.title}</h2>
                <p className="muted-copy">{capability.ai_goal}</p>
              </div>
              <span className="status-chip">{capability.maturity}</span>
            </div>

            <div className="workflow-strip" aria-label="Task workflow">
              <WorkflowStep icon={<GitBranch size={18} weight="duotone" />} label="Plan" active={Boolean(selectedTask?.plan?.summary)} />
              <WorkflowStep icon={<Play size={18} weight="duotone" />} label="Script" active={Boolean(selectedTask?.script)} />
              <WorkflowStep icon={<ShieldCheck size={18} weight="duotone" />} label="Validate" active={Boolean(selectedTask?.validation?.ok)} />
              <WorkflowStep icon={<CheckCircle size={18} weight="duotone" />} label="Approval" active={Boolean(selectedTask?.approved)} />
              <WorkflowStep icon={<Play size={18} weight="duotone" />} label="Execute" active={selectedTask?.status === "completed"} />
            </div>

            <div className="recipe-list detail">
              {capabilityRecipes.length ? capabilityRecipes.map((recipe) => (
                <article key={recipe.recipe_id}>
                  <div>
                    <strong>{recipe.title}</strong>
                    <span>{recipe.recipe_id}</span>
                    <p>{recipe.description}</p>
                  </div>
                  <button type="button" className="secondary-button" disabled={busy} onClick={() => onPlan(capability.id, recipe.recipe_id, "mock")}>
                    Mock Plan
                  </button>
                  <button type="button" className="primary-button" disabled={busy} onClick={() => onPlan(capability.id, recipe.recipe_id, "real")}>
                    Real Plan
                  </button>
                </article>
              )) : <div className="empty-state">该 Capability 暂无 Recipe。</div>}
            </div>

            <div className="workbench-panel task-panel">
              <div className="panel-heading compact">
                <h2>当前任务</h2>
                <span>{selectedTask?.status ?? "未创建"}</span>
              </div>
              {selectedTask ? (
                <>
                  <div className="button-pair">
                    <button type="button" className="secondary-button" disabled={busy || !selectedTask.task_id} onClick={() => onGenerate(selectedTask.capability_id, selectedTask.task_id)}>Generate Script</button>
                    <button type="button" className="secondary-button" disabled={busy || !selectedTask.script} onClick={() => onValidate(selectedTask.capability_id, selectedTask.task_id)}>Static Validation</button>
                    <button type="button" className="approval-button" disabled={busy || !selectedTask.validation?.ok} onClick={() => onApprove(selectedTask.capability_id, selectedTask.task_id)}>Approval</button>
                    <button type="button" className="primary-button" disabled={busy || !selectedTask.approved} onClick={() => onExecute(selectedTask.capability_id, selectedTask.task_id)}>Execute</button>
                  </div>
                  <pre className="task-json">{JSON.stringify(selectedTask, null, 2)}</pre>
                </>
              ) : (
                <div className="empty-state">选择 Recipe 后创建任务。</div>
              )}
            </div>
          </>
        ) : (
          <div className="empty-state">暂无 Capability 数据。</div>
        )}
      </section>
    </section>
  );
}

function WorkflowStep({ icon, label, active }: { icon: ReactNode; label: string; active: boolean }) {
  return (
    <div className={active ? "workflow-step active" : "workflow-step"}>
      {icon}
      <span>{label}</span>
    </div>
  );
}
