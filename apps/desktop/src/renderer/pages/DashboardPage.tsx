import { ClipboardText, Cpu, GitBranch, Pulse, Stack } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import type { AICapability, Recipe, WorkbenchTask } from "../lib/types";

interface DashboardPageProps {
  capabilities: AICapability[];
  recipes: Recipe[];
  tasks: WorkbenchTask[];
  onSelectGroup: (group: string) => void;
  onOpenCapability: (capabilityId: string) => void;
  onOpenTasks: () => void;
}

export function DashboardPage({ capabilities, recipes, tasks, onSelectGroup, onOpenCapability, onOpenTasks }: DashboardPageProps) {
  const groups = Array.from(new Set(capabilities.map((item) => item.group)));
  const primary = capabilities.find((item) => item.id === "ai.parametric_part_generator") ?? capabilities[0];
  const completed = tasks.filter((task) => task.status === "completed").length;

  return (
    <section className="dashboard-grid" aria-label="AI Capability Workbench Dashboard">
      <div className="workbench-hero">
        <div>
          <p className="eyebrow">AI Capability Workbench</p>
          <h2>从能力选择到审批执行的可追溯工作台</h2>
          <p>
            首页只展示 AI workflow、Capability group、Recipe 和任务历史。底层 Direct Tools 保留在 Integration / Developer / MCP 区域。
          </p>
        </div>
        <button type="button" className="primary-button" onClick={() => primary && onOpenCapability(primary.id)}>
          <GitBranch size={18} weight="duotone" aria-hidden />
          开始 mounting_plate
        </button>
      </div>

      <div className="metric-strip">
        <Metric icon={<Cpu size={20} weight="duotone" />} label="Capabilities" value={capabilities.length} />
        <Metric icon={<Stack size={20} weight="duotone" />} label="Recipes" value={recipes.length} />
        <Metric icon={<ClipboardText size={20} weight="duotone" />} label="MCP Tools" value={16} />
        <Metric icon={<Pulse size={20} weight="duotone" />} label="Completed Tasks" value={completed} />
      </div>

      <div className="capability-group-grid">
        {groups.map((group) => {
          const count = capabilities.filter((item) => item.group === group).length;
          return (
            <button key={group} type="button" className="group-tile" onClick={() => onSelectGroup(group)}>
              <span>{group}</span>
              <strong>{count}</strong>
            </button>
          );
        })}
      </div>

      <div className="dashboard-two-col">
        <section className="workbench-panel">
          <div className="panel-heading compact">
            <h2>核心 Recipe</h2>
          </div>
          <div className="recipe-list">
            {recipes.slice(0, 6).map((recipe) => (
              <button key={recipe.recipe_id} type="button" onClick={() => onOpenCapability(recipe.capability_id)}>
                <strong>{recipe.title}</strong>
                <span>{recipe.recipe_id}</span>
              </button>
            ))}
          </div>
        </section>
        <section className="workbench-panel">
          <div className="panel-heading compact">
            <h2>Task History</h2>
            <button type="button" className="secondary-button" onClick={onOpenTasks}>查看全部</button>
          </div>
          {tasks.length ? (
            <div className="task-list compact">
              {tasks.slice(0, 4).map((task) => (
                <article key={task.task_id}>
                  <strong>{task.recipe_id || task.capability_id}</strong>
                  <span>{task.status}</span>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">还没有任务记录。</div>
          )}
        </section>
      </div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="metric-tile">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
