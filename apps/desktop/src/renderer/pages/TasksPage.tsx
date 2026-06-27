import type { WorkbenchTask } from "../lib/types";

interface TasksPageProps {
  tasks: WorkbenchTask[];
  onSelectTask: (task: WorkbenchTask) => void;
}

export function TasksPage({ tasks, onSelectTask }: TasksPageProps) {
  return (
    <section className="tasks-page">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Task History</p>
          <h2>任务历史与 artifacts</h2>
        </div>
      </div>
      {tasks.length ? (
        <div className="task-list">
          {tasks.map((task) => (
            <button key={task.task_id} type="button" onClick={() => onSelectTask(task)}>
              <strong>{task.recipe_id || task.capability_id}</strong>
              <span>{task.status}</span>
              <small>{task.task_id}</small>
              <small>{task.artifacts.length} artifacts</small>
            </button>
          ))}
        </div>
      ) : (
        <div className="empty-state">还没有任务历史。</div>
      )}
    </section>
  );
}

