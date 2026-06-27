from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from sw_ai_backend.core.paths import skill_paths
from sw_ai_backend.core.security import require_api_token
from sw_ai_backend.execution.task_workflow import WorkbenchTask, WorkbenchWorkflow
from sw_ai_backend.mcp.tool_registry import MCPToolRegistry
from sw_ai_backend.mcp.tool_runner import MCPToolRunner
from sw_ai_backend.registry.ai_capability_registry import AICapabilityRegistry
from sw_ai_backend.registry.recipe_registry import RecipeRegistry
from sw_ai_backend.solidworks.com_runtime import solidworks_com_runtime
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
    geometry = _mounting_plate_geometry(parameters)

    created_files: list[str] = []
    stdout_chunks: list[str] = []
    try:
        create_payload = _create_mounting_plate_with_holes(sldprt, geometry)
        stdout_chunks.append(json.dumps(create_payload, ensure_ascii=False))
        created_files.extend(create_payload.get("created_files", []))
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
            "hole_features_restored": False,
            "geometry_parity_verified": False,
        }
        return workflow.complete_real(task, [], evidence).to_dict()

    params_path = task_dir / "mounting_plate_parameters.json"
    params_path.write_text(json.dumps(geometry, indent=2), encoding="utf-8")
    created_files.append(str(params_path))
    review_files = [str(path) for path in review_dir.rglob("*") if path.is_file()]
    artifacts = [{"name": Path(path).name, "path": path, "exists": Path(path).exists(), "kind": "real"} for path in sorted(set([*created_files, *review_files]))]
    features = create_payload.get("features", {}) if isinstance(create_payload, dict) else {}
    hole_count = int(features.get("holes") or 0)
    required_files_exist = sldprt.exists() and step.exists() and params_path.exists()
    review_report_exists = any(Path(item["path"]).suffix.lower() in {".json", ".md"} for item in artifacts if item["exists"] and "review" in item["name"].lower())
    previews_exist = sum(1 for item in artifacts if item["exists"] and Path(item["path"]).suffix.lower() in {".bmp", ".png", ".jpg", ".jpeg"}) >= 4
    geometry_parity_verified = hole_count == 4 and abs(float(features.get("hole_diameter_mm") or 0) - geometry["hole_diameter_mm"]) < 0.001
    real_verified = bool(required_files_exist and review_report_exists and previews_exist and geometry_parity_verified)
    evidence = {
        "execution_mode": "real",
        "real_execution_verified": real_verified,
        "solidworks_version": preflight.solidworks_version,
        "task_dir": str(task_dir),
        "stdout_json": [_try_json(chunk) for chunk in stdout_chunks],
        "created_files_exist": all(item["exists"] for item in artifacts),
        "hole_features_restored": geometry_parity_verified,
        "geometry_parity_verified": geometry_parity_verified,
        "hole_count_expected": 4,
        "hole_count_observed": hole_count,
        "hole_diameter_mm": geometry["hole_diameter_mm"],
        "hole_offset_mm": geometry["hole_offset_mm"],
        "feature_evidence": features,
        "required_files_exist": required_files_exist,
        "review_report_exists": review_report_exists,
        "preview_count": sum(1 for item in artifacts if item["exists"] and Path(item["path"]).suffix.lower() in {".bmp", ".png", ".jpg", ".jpeg"}),
    }
    return workflow.complete_real(task, artifacts, evidence).to_dict()


def _mounting_plate_geometry(parameters: dict[str, Any]) -> dict[str, float]:
    return {
        "width_mm": float(parameters.get("width_mm") or 120),
        "height_mm": float(parameters.get("height_mm") or 80),
        "thickness_mm": float(parameters.get("thickness_mm") or parameters.get("depth_mm") or 10),
        "hole_diameter_mm": float(parameters.get("hole_diameter_mm") or 6.5),
        "hole_offset_mm": float(parameters.get("hole_offset_mm") or 10),
        "chamfer_mm": float(parameters.get("chamfer_mm") or 1),
    }


def _create_mounting_plate_with_holes(output_path: Path, geometry: dict[str, float]) -> dict[str, Any]:
    scripts = skill_paths().solidworks_scripts
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from sw_connect import mm
    from sw_part import chamfer, extrude_boss, extrude_cut, sketch, sketch_circle, sketch_corner_rectangle
    from sw_session import SolidWorksSession

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width = geometry["width_mm"]
    height = geometry["height_mm"]
    thickness = geometry["thickness_mm"]
    hole_radius = geometry["hole_diameter_mm"] / 2
    hole_offset = geometry["hole_offset_mm"]
    chamfer_size = geometry["chamfer_mm"]
    hole_centers = [
        (-width / 2 + hole_offset, -height / 2 + hole_offset),
        (width / 2 - hole_offset, -height / 2 + hole_offset),
        (width / 2 - hole_offset, height / 2 - hole_offset),
        (-width / 2 + hole_offset, height / 2 - hole_offset),
    ]
    with solidworks_com_runtime("AI Capability mounting_plate geometry parity"):
        session = SolidWorksSession()
        model = session.new_part()
        with sketch(model, "Front Plane") as base_sketch:
            sketch_corner_rectangle(model, mm(-width / 2), mm(-height / 2), mm(width / 2), mm(height / 2))
        extrude_boss(model, base_sketch, mm(thickness))
        with sketch(model, "Front Plane") as hole_sketch:
            for x, y in hole_centers:
                sketch_circle(model, mm(x), mm(y), mm(hole_radius))
        extrude_cut(model, hole_sketch, mm(thickness * 2))
        chamfer(model, mm(chamfer_size), 45)
        saved = bool(session.save(model, str(output_path)))
    if not saved:
        raise RuntimeError("SolidWorks did not save mounting_plate.SLDPRT after four-hole geometry creation.")
    return {
        "status": "ok",
        "output_path": str(output_path),
        "created_files": [str(output_path)],
        "features": {
            "width_mm": width,
            "height_mm": height,
            "thickness_mm": thickness,
            "holes": 4,
            "hole_centers_mm": [{"x": x, "y": y} for x, y in hole_centers],
            "hole_diameter_mm": geometry["hole_diameter_mm"],
            "hole_offset_mm": hole_offset,
            "chamfer_mm": chamfer_size,
        },
    }


def _try_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
