from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from sw_ai_backend.core.security import require_api_token
from sw_ai_backend.execution.task_workflow import WorkbenchTask, WorkbenchWorkflow
from sw_ai_backend.mcp.tool_registry import MCPToolRegistry
from sw_ai_backend.mcp.tool_runner import MCPToolRunner
from sw_ai_backend.registry.ai_capability_registry import AICapabilityRegistry
from sw_ai_backend.registry.recipe_registry import RecipeRegistry
from sw_ai_backend.solidworks.service import SolidWorksService


router = APIRouter(prefix="/api", dependencies=[Depends(require_api_token)])
capability_registry = AICapabilityRegistry()
recipe_registry = RecipeRegistry()
workflow = WorkbenchWorkflow()
solidworks_service = SolidWorksService()
mcp_tool_runner = MCPToolRunner()
mcp_tool_registry = MCPToolRegistry()


@router.get("/ai-capabilities")
async def list_ai_capabilities() -> dict[str, Any]:
    return capability_registry.write()


@router.get("/ai-capabilities/{capability_id}")
async def get_ai_capability(capability_id: str) -> dict[str, Any]:
    capability = capability_registry.get(capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail=f"未找到 AI Capability: {capability_id}")
    recipes = [item.to_dict() for item in recipe_registry.for_capability(capability_id)]
    return {**capability.to_dict(), "recipes": recipes}


@router.get("/recipes")
async def list_recipes() -> dict[str, Any]:
    return recipe_registry.write()


@router.get("/tasks")
async def list_tasks() -> dict[str, Any]:
    tasks = [task.to_dict() for task in workflow.store.list()]
    return {"total": len(tasks), "tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    return _task_or_404(task_id).to_dict()


@router.get("/mcp/tools")
async def list_mcp_tools() -> dict[str, Any]:
    tools = [tool.model_dump(mode="json") for tool in mcp_tool_registry.discover()]
    return {"total": len(tools), "tools": tools}


@router.post("/ai-capabilities/{capability_id}/plan")
async def plan_ai_capability(capability_id: str, request: dict[str, Any]) -> dict[str, Any]:
    capability = _capability_or_404(capability_id)
    recipe = _recipe_from_request(request)
    prompt = str(request.get("prompt") or recipe.default_prompt if recipe else request.get("prompt") or capability.ai_goal)
    execution_mode = _execution_mode(request)
    task = workflow.plan(capability, recipe, prompt, execution_mode)
    return task.to_dict()


@router.post("/ai-capabilities/{capability_id}/generate-script")
async def generate_ai_capability_script(capability_id: str, request: dict[str, Any]) -> dict[str, Any]:
    task = _existing_or_planned_task(capability_id, request)
    recipe = recipe_registry.get(task.recipe_id) if task.recipe_id else _recipe_from_request(request)
    parameters = dict(request.get("parameters") or {})
    task = workflow.generate_script(task, recipe, parameters)
    return task.to_dict()


@router.post("/ai-capabilities/{capability_id}/validate")
async def validate_ai_capability(capability_id: str, request: dict[str, Any]) -> dict[str, Any]:
    task = _task_for_capability(capability_id, request)
    if not task.script:
        raise HTTPException(status_code=400, detail="请先生成脚本。")
    task = workflow.validate(task)
    return task.to_dict()


@router.post("/ai-capabilities/{capability_id}/approve")
async def approve_ai_capability(capability_id: str, request: dict[str, Any]) -> dict[str, Any]:
    task = _task_for_capability(capability_id, request)
    try:
        task = workflow.approve(task, approved_by=str(request.get("approved_by") or "local-user"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return task.to_dict()


@router.post("/ai-capabilities/{capability_id}/execute")
async def execute_ai_capability(capability_id: str, request: dict[str, Any]) -> dict[str, Any]:
    task = _task_for_capability(capability_id, request)
    recipe = recipe_registry.get(task.recipe_id) if task.recipe_id else _recipe_from_request(request)
    parameters = dict(request.get("parameters") or {})
    if not task.approved:
        raise HTTPException(status_code=400, detail="任务必须先通过审批链路。")
    if task.execution_mode == "mock":
        try:
            return workflow.execute_mock(task, recipe, parameters).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _execute_real_mounting_plate(task, recipe, parameters)


def _capability_or_404(capability_id: str):
    capability = capability_registry.get(capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail=f"未找到 AI Capability: {capability_id}")
    return capability


def _recipe_from_request(request: dict[str, Any]):
    recipe_id = str(request.get("recipe_id") or "")
    if recipe_id:
        recipe = recipe_registry.get(recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail=f"未找到 Recipe: {recipe_id}")
        return recipe
    return None


def _execution_mode(request: dict[str, Any]) -> str:
    mode = str(request.get("execution_mode") or "mock").lower()
    if mode not in {"mock", "real"}:
        raise HTTPException(status_code=400, detail="execution_mode 只能是 mock 或 real。")
    return mode


def _existing_or_planned_task(capability_id: str, request: dict[str, Any]) -> WorkbenchTask:
    task_id = str(request.get("task_id") or "")
    if task_id:
        return _task_for_capability(capability_id, request)
    capability = _capability_or_404(capability_id)
    recipe = _recipe_from_request(request)
    prompt = str(request.get("prompt") or recipe.default_prompt if recipe else request.get("prompt") or capability.ai_goal)
    return workflow.plan(capability, recipe, prompt, _execution_mode(request))


def _task_for_capability(capability_id: str, request: dict[str, Any]) -> WorkbenchTask:
    task_id = str(request.get("task_id") or "")
    if not task_id:
        raise HTTPException(status_code=400, detail="缺少 task_id。")
    task = _task_or_404(task_id)
    if task.capability_id != capability_id:
        raise HTTPException(status_code=400, detail="task_id 与 capability_id 不匹配。")
    return task


def _task_or_404(task_id: str) -> WorkbenchTask:
    task = workflow.store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"未找到任务: {task_id}")
    return task


async def _execute_real_mounting_plate(task: WorkbenchTask, recipe, parameters: dict[str, Any]) -> dict[str, Any]:
    preflight = await solidworks_service.preflight_async(timeout_seconds=5)
    if not preflight.can_run_real_com:
        failed = [check.model_dump(mode="json") for check in preflight.checks if check.status.value in {"fail", "warn"}][:8]
        raise HTTPException(
            status_code=424,
            detail={
                "message": "真实执行需要 SolidWorks COM preflight 通过。",
                "can_run_real_com": preflight.can_run_real_com,
                "solidworks_version": preflight.solidworks_version,
                "checks": failed,
            },
        )
    if recipe is None or recipe.recipe_id != "mounting_plate":
        raise HTTPException(status_code=400, detail="当前恢复版真实执行仅支持 mounting_plate Recipe。")

    task_dir = Path(task.evidence.get("task_dir") or Path.cwd())
    if not str(task_dir).endswith(task.task_id):
        from sw_ai_backend.core.paths import user_outputs_dir

        task_dir = user_outputs_dir() / "tasks" / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    sldprt = task_dir / "mounting_plate.SLDPRT"
    step = task_dir / "mounting_plate.STEP"
    review_dir = task_dir / "review"
    width = float(parameters.get("width_mm") or 120)
    height = float(parameters.get("height_mm") or 80)
    thickness = float(parameters.get("thickness_mm") or 10)

    created_files: list[str] = []
    stdout_chunks: list[str] = []
    try:
        create_result = mcp_tool_runner.run(
            "solidworks_create_basic_part",
            {
                "shape": "box",
                "width_mm": width,
                "height_mm": height,
                "depth_mm": thickness,
                "output_path": str(sldprt),
                "color": "#9DA7AA",
            },
            raise_on_error_status=True,
        )
        stdout_chunks.append(create_result.stdout)
        created_files.extend(create_result.created_files)
        export_result = mcp_tool_runner.run(
            "solidworks_export_active",
            {"output_path": str(step), "export_format": "step"},
            raise_on_error_status=True,
        )
        stdout_chunks.append(export_result.stdout)
        created_files.extend(export_result.created_files)
        review_result = mcp_tool_runner.run(
            "solidworks_review_active",
            {"output_dir": str(review_dir), "basename": "mounting_plate_review"},
            raise_on_error_status=True,
        )
        stdout_chunks.append(review_result.stdout)
        created_files.extend(review_result.created_files)
    except Exception as exc:
        evidence = {
            "execution_mode": "real",
            "real_execution_verified": False,
            "error": str(exc),
            "solidworks_version": preflight.solidworks_version,
            "task_dir": str(task_dir),
        }
        return workflow.complete_real(task, [], evidence).to_dict()

    params_path = task_dir / "mounting_plate_parameters.json"
    params_path.write_text(json.dumps({"width_mm": width, "height_mm": height, "thickness_mm": thickness}, indent=2), encoding="utf-8")
    created_files.append(str(params_path))
    artifacts = [{"name": Path(path).name, "path": path, "exists": Path(path).exists(), "kind": "real"} for path in sorted(set(created_files))]
    evidence = {
        "execution_mode": "real",
        "real_execution_verified": bool(sldprt.exists() and step.exists()),
        "solidworks_version": preflight.solidworks_version,
        "task_dir": str(task_dir),
        "stdout_json": [_try_json(chunk) for chunk in stdout_chunks],
        "created_files_exist": all(item["exists"] for item in artifacts),
        "hole_features_restored": False,
        "known_limit": "Recovered real mounting_plate path creates a real plate body plus STEP/review evidence; v0.9.0 hole feature source is still missing.",
    }
    return workflow.complete_real(task, artifacts, evidence).to_dict()


def _try_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text

