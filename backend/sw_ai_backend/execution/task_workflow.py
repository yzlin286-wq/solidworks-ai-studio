from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import user_outputs_dir
from sw_ai_backend.execution.static_validator import StaticValidator
from sw_ai_backend.registry.ai_capability_registry import AICapability
from sw_ai_backend.registry.recipe_registry import Recipe


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WorkbenchTask:
    task_id: str
    capability_id: str
    recipe_id: str
    prompt: str
    execution_mode: str
    status: str = "draft"
    plan: dict[str, Any] = field(default_factory=dict)
    script: str = ""
    validation: dict[str, Any] = field(default_factory=dict)
    approved: bool = False
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error_summary: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    real_execution_verified: bool = False
    mock_demo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "capability_id": self.capability_id,
            "recipe_id": self.recipe_id,
            "prompt": self.prompt,
            "execution_mode": self.execution_mode,
            "status": self.status,
            "plan": self.plan,
            "script": self.script,
            "validation": self.validation,
            "approved": self.approved,
            "artifacts": self.artifacts,
            "evidence": self.evidence,
            "error_summary": self.error_summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "real_execution_verified": self.real_execution_verified,
            "mock_demo": self.mock_demo,
        }


class WorkbenchTaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, WorkbenchTask] = {}

    def create(self, capability: AICapability, recipe: Recipe | None, prompt: str, execution_mode: str) -> WorkbenchTask:
        task = WorkbenchTask(
            task_id=uuid.uuid4().hex,
            capability_id=capability.id,
            recipe_id=recipe.recipe_id if recipe else "",
            prompt=prompt,
            execution_mode=execution_mode,
            mock_demo=execution_mode == "mock",
        )
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> WorkbenchTask | None:
        return self._tasks.get(task_id)

    def list(self) -> list[WorkbenchTask]:
        return sorted(self._tasks.values(), key=lambda task: task.created_at, reverse=True)

    def update(self, task: WorkbenchTask, **changes: Any) -> WorkbenchTask:
        for key, value in changes.items():
            setattr(task, key, value)
        task.updated_at = utc_now()
        self._tasks[task.task_id] = task
        return task


class WorkbenchWorkflow:
    def __init__(self, store: WorkbenchTaskStore | None = None) -> None:
        self.store = store or WorkbenchTaskStore()
        self.validator = StaticValidator()

    def plan(self, capability: AICapability, recipe: Recipe | None, prompt: str, execution_mode: str) -> WorkbenchTask:
        task = self.store.create(capability, recipe, prompt, execution_mode)
        steps = [
            "解析用户目标和参数",
            "生成可审计 SolidWorks Python 脚本",
            "运行静态校验",
            "等待人工审批",
            "执行并收集 artifacts 与 evidence",
        ]
        plan = {
            "summary": f"{capability.title}: {prompt}",
            "capability_id": capability.id,
            "recipe_id": recipe.recipe_id if recipe else "",
            "execution_mode": execution_mode,
            "steps": steps,
            "requires_approval": True,
            "mock_demo": execution_mode == "mock",
            "real_execution_verified": False,
        }
        return self.store.update(task, status="planned", plan=plan)

    def generate_script(self, task: WorkbenchTask, recipe: Recipe | None, parameters: dict[str, Any]) -> WorkbenchTask:
        script = self._script_for(task, recipe, parameters)
        return self.store.update(task, status="script_generated", script=script)

    def validate(self, task: WorkbenchTask) -> WorkbenchTask:
        result = self.validator.validate(task.script)
        status = "validated" if result.ok else "failed"
        return self.store.update(task, status=status, validation=result.to_dict(), error_summary="" if result.ok else "; ".join(result.issues))

    def approve(self, task: WorkbenchTask, approved_by: str = "local-user") -> WorkbenchTask:
        if task.status != "validated" or not task.validation.get("ok"):
            raise ValueError("Task must pass static validation before approval.")
        evidence = {**task.evidence, "approved_by": approved_by, "approved_at": utc_now().isoformat()}
        return self.store.update(task, status="approved", approved=True, evidence=evidence)

    def execute_mock(self, task: WorkbenchTask, recipe: Recipe | None, parameters: dict[str, Any]) -> WorkbenchTask:
        if not task.approved:
            raise ValueError("Task must be approved before execution.")
        task_dir = self._task_dir(task.task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        artifacts = self._write_mock_artifacts(task_dir, recipe, parameters)
        evidence = {
            **task.evidence,
            "execution_mode": "mock",
            "mock_demo": True,
            "task_dir": str(task_dir),
            "created_files_exist": all(Path(item["path"]).exists() for item in artifacts),
        }
        return self.store.update(
            task,
            status="completed",
            artifacts=artifacts,
            evidence=evidence,
            real_execution_verified=False,
            mock_demo=True,
        )

    def complete_real(self, task: WorkbenchTask, artifacts: list[dict[str, Any]], evidence: dict[str, Any]) -> WorkbenchTask:
        if not task.approved:
            raise ValueError("Task must be approved before execution.")
        verified = bool(evidence.get("real_execution_verified"))
        status = "completed" if verified else "failed"
        return self.store.update(
            task,
            status=status,
            artifacts=artifacts,
            evidence=evidence,
            real_execution_verified=verified,
            mock_demo=False,
            error_summary="" if verified else "Real execution evidence was not sufficient.",
        )

    def _task_dir(self, task_id: str) -> Path:
        return user_outputs_dir() / "tasks" / task_id

    def _script_for(self, task: WorkbenchTask, recipe: Recipe | None, parameters: dict[str, Any]) -> str:
        recipe_id = recipe.recipe_id if recipe else "custom"
        safe_parameters = json.dumps(parameters, ensure_ascii=False, indent=2)
        if task.execution_mode == "mock":
            return (
                "# AI Capability Workbench mock script\n"
                f"RECIPE_ID = {recipe_id!r}\n"
                f"CAPABILITY_ID = {task.capability_id!r}\n"
                f"PARAMETERS = {safe_parameters}\n"
                "print('mock execution is explicit and never counted as real SolidWorks evidence')\n"
            )
        return (
            "# AI Capability Workbench real SolidWorks script\n"
            "from pathlib import Path\n"
            f"RECIPE_ID = {recipe_id!r}\n"
            f"CAPABILITY_ID = {task.capability_id!r}\n"
            f"PARAMETERS = {safe_parameters}\n"
            "print('real execution requires approved SolidWorks COM tool calls')\n"
        )

    def _write_mock_artifacts(self, task_dir: Path, recipe: Recipe | None, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        recipe_id = recipe.recipe_id if recipe else "custom"
        names = recipe.mock_artifacts if recipe else [f"{recipe_id}_mock_result.json"]
        artifacts: list[dict[str, Any]] = []
        payload = {
            "recipe_id": recipe_id,
            "parameters": parameters,
            "mock_demo": True,
            "real_execution_verified": False,
            "note": "This artifact is for offline Workbench validation only.",
        }
        for name in names:
            path = task_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in {".json"}:
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            elif path.suffix.lower() in {".md"}:
                path.write_text(f"# Mock Review\n\nRecipe: `{recipe_id}`\n\nThis is not real SolidWorks evidence.\n", encoding="utf-8")
            else:
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts.append({"name": name, "path": str(path), "exists": path.exists(), "kind": "mock"})
        return artifacts

