from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from sw_ai_backend.core.config import ConfigStore
from sw_ai_backend.core.paths import project_root, user_data_dir, user_outputs_dir, user_temp_dir, validation_latest_dir
from sw_ai_backend.core.security import require_api_token
from sw_ai_backend.llm.client import (
    LLMClient,
    LLMConfigurationError,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMResponseError,
)
from sw_ai_backend.mcp.manager import MCPManager
from sw_ai_backend.mcp.tool_registry import MCPToolRegistry
from sw_ai_backend.mcp.tool_runner import MCPToolRunner
from sw_ai_backend.models.schemas import (
    AIPlanRequest,
    AIPlanResponse,
    AppConfig,
    ApproveRunRequest,
    Capability,
    CapabilityListResponse,
    CapabilityRunRequest,
    CapabilityValidationResponse,
    CapabilityExecutionKind,
    ConfigResponse,
    GenerateScriptRequest,
    GenerateScriptResponse,
    HealthResponse,
    MCPConfigSnippetsResponse,
    MCPStatusResponse,
    PreflightResponse,
    RealTestRunResponse,
    RunCreatedResponse,
    RunRecord,
    SkillIndexResponse,
    SkillSyncResponse,
    SolidWorksActionRequest,
    SolidWorksActionResponse,
    SolidWorksExecutionRecord,
    SolidWorksSessionResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    utc_now,
)
from sw_ai_backend.runner.queue import ExecutionQueue, ScriptSafetyError
from sw_ai_backend.skills.capabilities import CapabilityRegistry
from sw_ai_backend.skills.indexer import SkillIndexer
from sw_ai_backend.solidworks.execution_queue import SolidWorksExecutionQueue
from sw_ai_backend.solidworks.dwg_export import export_part_drawing
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession
from sw_ai_backend.solidworks.service import SolidWorksService


router = APIRouter(prefix="/api")
protected = APIRouter(prefix="/api", dependencies=[Depends(require_api_token)])
config_store = ConfigStore()
skill_indexer = SkillIndexer.default()
solidworks_service = SolidWorksService()
mcp_manager = MCPManager()
mcp_tool_registry = MCPToolRegistry()
mcp_tool_runner = MCPToolRunner()
execution_queue = ExecutionQueue()
solidworks_queue = SolidWorksExecutionQueue()
capability_registry = CapabilityRegistry()
validation_assembly_token = uuid.uuid4().hex[:8]
generated_script_registry: dict[str, dict[str, Any]] = {}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    from sw_ai_backend import __version__

    return HealthResponse(
        ok=True,
        app="SolidWorks AI Studio",
        version=__version__,
        mode="api",
        project_root=str(project_root()),
        user_data_dir=str(user_data_dir()),
    )


@protected.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    return ConfigResponse(
        config=config_store.public_config(),
        config_path=str(config_store.path),
        secure_storage="config-file",
        note="API Key 会保存在本地用户配置文件中，并在 API 响应与日志中脱敏显示。",
    )


@protected.post("/config", response_model=ConfigResponse)
async def save_config(config: AppConfig) -> ConfigResponse:
    config_store.save(config)
    return await get_config()


@protected.post("/llm/test", response_model=TestConnectionResponse)
async def test_llm(request: TestConnectionRequest) -> TestConnectionResponse:
    profile = _hydrate_masked_profile_secret(request.profile)
    ok, message, latency_ms, models, models_verified, chat_verified = await LLMClient(profile).test_connection()
    return TestConnectionResponse(
        ok=ok,
        provider=profile.name,
        message=message,
        latency_ms=latency_ms,
        models=models,
        models_verified=models_verified,
        chat_verified=chat_verified,
        provider_verified_at=utc_now() if ok and chat_verified else None,
    )


@protected.post("/skills/sync", response_model=SkillSyncResponse)
async def sync_skills() -> SkillSyncResponse:
    solidworks = _sync_repo("vendor/skills/solidworks-automation", "https://github.com/wzyn20051216/solidworks-automation-skill.git")
    taste = _sync_repo("vendor/skills/taste-skill", "https://github.com/Leonxlnx/taste-skill")
    return SkillSyncResponse(ok=True, solidworks=solidworks, taste=taste, message="Skill 同步命令已完成。")


@protected.get("/skills/index", response_model=SkillIndexResponse)
async def skills_index() -> SkillIndexResponse:
    return skill_indexer.build_index()


@protected.get("/skills/capabilities", response_model=CapabilityListResponse)
async def skills_capabilities() -> CapabilityListResponse:
    return capability_registry.write()


@protected.get("/skills/capabilities/{capability_id}", response_model=Capability)
async def get_capability(capability_id: str) -> Capability:
    capability = capability_registry.get(capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail=f"未找到能力：{capability_id}")
    return capability


@protected.post("/skills/capabilities/{capability_id}/run", response_model=SolidWorksExecutionRecord)
async def run_capability(capability_id: str, request: CapabilityRunRequest) -> SolidWorksExecutionRecord:
    capability = capability_registry.get(capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail=f"未找到能力：{capability_id}")
    if not capability.callable:
        raise HTTPException(status_code=400, detail=f"该能力仅用于文档上下文，不能直接运行：{capability_id}")
    if capability.execution_kind == CapabilityExecutionKind.MCP_TOOL:
        tool_name = capability_id.split(".", 1)[1]
        return await _run_mcp_record(capability_id, tool_name, request.parameters, request.timeout_seconds)
    if capability.requires_solidworks:
        preflight = await solidworks_service.preflight_async(timeout_seconds=5)
        if not preflight.can_run_real_com:
            _raise_preflight_dependency_error(preflight, capability_id)
    if capability_id == "wrapper.export_dwg":
        output_path = _default_export_path("dwg")
        parameters = {
            "output_path": str(output_path),
            "drawing_path": str(output_path.with_suffix(".SLDDRW")),
            "part_path": str(_latest_existing_file([".sldprt"]) or _button_sample_paths()["shaft"]),
            **request.parameters,
        }
        return await solidworks_queue.submit(
            capability_id=capability_id,
            parameters=parameters,
            operation=lambda parameters: _run_drawing_export({**parameters, "export_format": "dwg"}),
            timeout_seconds=request.timeout_seconds,
        )
    return await solidworks_queue.submit(
        capability_id=capability_id,
        parameters=request.parameters,
        operation=lambda parameters: _run_script_capability(capability, parameters),
        timeout_seconds=request.timeout_seconds,
    )


@protected.get("/skills/capabilities/{capability_id}/validation", response_model=CapabilityValidationResponse)
async def capability_validation(capability_id: str) -> CapabilityValidationResponse:
    capability = capability_registry.get(capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail=f"未找到能力：{capability_id}")
    return CapabilityValidationResponse(
        capability_id=capability_id,
        status=capability.real_sw2025_status,
        skip_reason=capability.skip_reason,
        report_path=str(validation_latest_dir() / "REAL_SW2025_VALIDATION_REPORT.json"),
    )


@protected.get("/solidworks/preflight", response_model=PreflightResponse)
async def solidworks_preflight() -> PreflightResponse:
    return await solidworks_service.preflight_async()


@protected.post("/solidworks/connect", response_model=SolidWorksActionResponse)
async def solidworks_connect() -> SolidWorksActionResponse:
    return await _run_mcp_action("connect", "solidworks_connect", {})


@protected.post("/solidworks/open", response_model=SolidWorksActionResponse)
async def solidworks_open(request: SolidWorksActionRequest) -> SolidWorksActionResponse:
    return await _run_mcp_action("open", "solidworks_open_document", {"path": request.path})


@protected.post("/solidworks/save", response_model=SolidWorksActionResponse)
async def solidworks_save(request: SolidWorksActionRequest) -> SolidWorksActionResponse:
    return await _run_mcp_action("save", "solidworks_save_document", {"path": request.path or request.output_path or None})


@protected.post("/solidworks/export", response_model=SolidWorksActionResponse)
async def solidworks_export(request: SolidWorksActionRequest) -> SolidWorksActionResponse:
    export_format = request.format.lower().lstrip(".")
    output = request.output_path or str(_default_export_path(export_format))
    if export_format in {"pdf", "dxf", "dwg"}:
        preflight = await solidworks_service.preflight_async(timeout_seconds=5)
        if not preflight.can_run_real_com:
            _raise_preflight_dependency_error(preflight, f"export_{export_format}")
        parameters = {
            "part_path": request.path or str(_latest_existing_file([".sldprt"]) or _button_sample_paths()["shaft"]),
            "output_path": output,
            "drawing_path": str(Path(output).with_suffix(".SLDDRW")),
            "export_format": export_format,
        }
        record = await solidworks_queue.submit(
            capability_id=f"wrapper.export_{export_format}",
            parameters=parameters,
            operation=lambda params: _run_drawing_export(params),
            timeout_seconds=300,
        )
        ok = record.status.value == "passed"
        return SolidWorksActionResponse(
            ok=ok,
            mode="solidworks",
            action=f"export_{export_format}",
            message=f"{export_format.upper()} 导出已通过 SolidWorks drawing wrapper {'完成' if ok else '失败'}。",
            stdout=record.stdout,
            stderr=record.stderr,
            files=record.created_files,
            data={
                "run_id": record.run_id,
                "capability_id": record.capability_id,
                "active_document_before": record.active_document_before,
                "active_document_after": record.active_document_after,
                "error_summary": record.error_summary,
            },
            real_execution_verified=record.real_execution_verified,
            evidence=record.evidence,
            active_document_before=record.active_document_before,
            active_document_after=record.active_document_after,
            created_files_exist=record.created_files_exist,
        )
    return await _run_mcp_action("export", "solidworks_export_active", {"output_path": output, "export_format": export_format})


@protected.post("/solidworks/review", response_model=SolidWorksActionResponse)
async def solidworks_review(request: SolidWorksActionRequest) -> SolidWorksActionResponse:
    output = request.output_path or str(project_root() / "outputs" / "review")
    return await _run_mcp_action("review", "solidworks_review_active", {"output_dir": output, "basename": "studio_review"})


@protected.post("/solidworks/create-basic-part", response_model=SolidWorksActionResponse)
async def solidworks_create_basic_part(request: SolidWorksActionRequest) -> SolidWorksActionResponse:
    parameters = {"shape": "box", **request.parameters}
    if parameters.get("shape") == "blank-part":
        parameters["shape"] = "box"
    return await _run_mcp_action("create_basic_part", "solidworks_create_basic_part", parameters)


@protected.get("/solidworks/session", response_model=SolidWorksSessionResponse)
async def solidworks_session() -> SolidWorksSessionResponse:
    return RealSolidWorksSession().status(start_if_missing=False)


@protected.post("/solidworks/session/start", response_model=SolidWorksSessionResponse)
async def solidworks_session_start() -> SolidWorksSessionResponse:
    return RealSolidWorksSession().status(start_if_missing=True)


@protected.post("/solidworks/session/stop", response_model=SolidWorksSessionResponse)
async def solidworks_session_stop() -> SolidWorksSessionResponse:
    return RealSolidWorksSession().detach()


@protected.post("/solidworks/session/attach", response_model=SolidWorksSessionResponse)
async def solidworks_session_attach() -> SolidWorksSessionResponse:
    return RealSolidWorksSession().status(start_if_missing=False)


@protected.post("/solidworks/session/reset", response_model=SolidWorksSessionResponse)
async def solidworks_session_reset() -> SolidWorksSessionResponse:
    return RealSolidWorksSession().status(start_if_missing=True)


@protected.post("/ai/plan", response_model=AIPlanResponse)
async def ai_plan(request: AIPlanRequest) -> AIPlanResponse:
    config = config_store.load()
    profile = _select_profile(config, request.profile_id)
    index = skill_indexer.build_index()
    output_dir = request.output_dir or config.output_dir
    try:
        return await LLMClient(profile).generate_plan(request.prompt, index.context_summary, output_dir)
    except (LLMConfigurationError, LLMProviderTimeoutError, LLMProviderError, LLMResponseError) as exc:
        _raise_llm_http_exception(exc)
        raise


@protected.post("/ai/generate-script", response_model=GenerateScriptResponse)
async def ai_generate_script(request: GenerateScriptRequest) -> GenerateScriptResponse:
    config = config_store.load()
    profile = _select_profile(config, request.profile_id)
    index = skill_indexer.build_index()
    script_dir = user_temp_dir() / "generated" / uuid.uuid4().hex
    script_dir.mkdir(parents=True, exist_ok=True)
    output_dir = request.output_dir or config.output_dir or str(script_dir / "outputs")
    script_path = script_dir / "solidworks_task.py"
    try:
        response = await LLMClient(profile).generate_script(request.prompt, index.context_summary, output_dir, script_path)
    except (LLMConfigurationError, LLMProviderTimeoutError, LLMProviderError, LLMResponseError) as exc:
        _raise_llm_http_exception(exc)
        raise
    if response.demo_mode or response.fallback_used:
        raise HTTPException(status_code=422, detail="LLM 生成结果不是严格真实模式，已拒绝写入脚本。")
    script_path.write_text(response.script, encoding="utf-8")
    generated_script_registry[str(script_path.resolve())] = {
        "prompt": request.prompt,
        "output_dir": output_dir,
        "provider_verified_at": response.provider_verified_at.isoformat() if response.provider_verified_at else "",
        "demo_mode": response.demo_mode,
        "fallback_used": response.fallback_used,
    }
    return response.model_copy(update={"script_path": str(script_path)})


@protected.post("/ai/approve-run", response_model=RunCreatedResponse)
async def approve_run(request: ApproveRunRequest) -> RunCreatedResponse:
    registered = generated_script_registry.get(str(Path(request.script_path).expanduser().resolve()))
    if not registered:
        raise HTTPException(status_code=400, detail="只能执行本次由真实 LLM 生成并登记的脚本。")
    if registered.get("demo_mode") or registered.get("fallback_used"):
        raise HTTPException(status_code=400, detail="非真实脚本禁止执行。")
    preflight = await solidworks_service.preflight_async(timeout_seconds=5)
    if not preflight.can_run_real_com:
        _raise_preflight_dependency_error(preflight, "approve-run")
    try:
        record = await execution_queue.submit(
            request.script_path,
            request.prompt,
            request.timeout_seconds,
            evidence_output_dir=str(registered.get("output_dir") or ""),
        )
    except ScriptSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunCreatedResponse(run_id=record.run_id, stage=record.stage, message="Run 已接受并进入队列。")


@protected.get("/runs/{run_id}", response_model=RunRecord)
async def get_run(run_id: str) -> RunRecord:
    record = await execution_queue.store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到 Run。")
    return record


@protected.get("/runs/{run_id}/events", response_class=PlainTextResponse)
async def get_run_events(run_id: str) -> str:
    record = await execution_queue.store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到 Run。")
    return "\n".join(event.model_dump_json() for event in record.events)


@protected.post("/mcp/start", response_model=MCPStatusResponse)
async def mcp_start() -> MCPStatusResponse:
    return mcp_manager.start()


@protected.post("/mcp/stop", response_model=MCPStatusResponse)
async def mcp_stop() -> MCPStatusResponse:
    return mcp_manager.stop()


@protected.get("/mcp/status", response_model=MCPStatusResponse)
async def mcp_status() -> MCPStatusResponse:
    return mcp_manager.status()


@protected.get("/mcp/config-snippets", response_model=MCPConfigSnippetsResponse)
async def mcp_config_snippets() -> MCPConfigSnippetsResponse:
    return mcp_manager.snippets()


@protected.post("/solidworks/real-test/run", response_model=RealTestRunResponse)
async def real_test_run() -> RealTestRunResponse:
    from sw_ai_backend.validation.real_acceptance import RealAcceptanceRunner

    return await RealAcceptanceRunner().run()


@protected.get("/solidworks/real-test/report", response_model=RealTestRunResponse)
async def real_test_report() -> RealTestRunResponse:
    from sw_ai_backend.validation.real_acceptance import RealAcceptanceRunner

    return RealAcceptanceRunner().load_latest()


@protected.get("/runs/solidworks/{run_id}", response_model=SolidWorksExecutionRecord)
async def get_solidworks_run(run_id: str) -> SolidWorksExecutionRecord:
    record = solidworks_queue.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到 SolidWorks Run。")
    return record


@protected.post("/runs/solidworks/{run_id}/cancel", response_model=SolidWorksExecutionRecord)
async def cancel_solidworks_run(run_id: str) -> SolidWorksExecutionRecord:
    record = solidworks_queue.cancel(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到 SolidWorks Run。")
    return record


def _select_profile(config: AppConfig, profile_id: str | None):
    selected = profile_id or config.active_profile_id
    for profile in config.profiles:
        if profile.id == selected:
            return profile
    return config.profiles[0]


def _hydrate_masked_profile_secret(profile):
    if profile.api_key and profile.api_key != "********":
        return profile
    config = config_store.load()
    stored = next((item for item in config.profiles if item.id == profile.id), None)
    if stored and stored.api_key:
        return profile.model_copy(update={"api_key": stored.api_key})
    return profile.model_copy(update={"api_key": ""})


def _raise_llm_http_exception(exc: Exception) -> None:
    if isinstance(exc, LLMConfigurationError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, LLMProviderTimeoutError):
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    if isinstance(exc, LLMProviderError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if isinstance(exc, LLMResponseError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


def _raise_preflight_dependency_error(preflight: PreflightResponse, action: str) -> None:
    failed_checks = [
        check.model_dump(mode="json")
        for check in preflight.checks
        if check.status.value in {"fail", "warn"}
    ][:8]
    raise HTTPException(
        status_code=424,
        detail={
            "message": f"{action} 需要真实 SolidWorks COM 会话，当前 preflight 未通过。",
            "preflight_mode": preflight.mode,
            "preflight_state": preflight.state,
            "preflight_stale": preflight.stale,
            "can_run_real_com": preflight.can_run_real_com,
            "checks": failed_checks,
        },
    )


def _sync_repo(relative: str, url: str) -> str:
    target = project_root() / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["git", "clone", url, str(target)], cwd=str(project_root()))
        return f"已克隆 {url}。"
    if not (target / ".git").exists():
        return f"{target} 已存在但不是 git checkout，已保持不变。"
    dirty = subprocess.run(["git", "-C", str(target), "status", "--porcelain"], capture_output=True, text=True, check=False)
    if dirty.stdout.strip():
        return f"{target} 有本地改动，已保持不变。"
    subprocess.check_call(["git", "-C", str(target), "pull", "--ff-only"])
    return f"已更新 {target}。"


def _button_samples_dir() -> Path:
    path = validation_latest_dir() / "installed_button_samples"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _button_sample_paths() -> dict[str, Path]:
    base = _button_samples_dir()
    return {
        "shaft": base / "installed_validation_shaft.SLDPRT",
        "rotor": base / "installed_validation_rotor.SLDPRT",
        "box": base / "installed_validation_box.SLDPRT",
        "assembly": base / "installed_validation_assembly.SLDASM",
        "step": base / "installed_validation_export.STEP",
        "stl": base / "installed_validation_export.STL",
        "iges": base / "installed_validation_export.IGES",
        "parasolid": base / "installed_validation_export.x_t",
        "pdf": base / "installed_validation_export.PDF",
        "dxf": base / "installed_validation_export.DXF",
        "dwg": base / "installed_validation_export.DWG",
        "drawing": base / "installed_validation_export.SLDDRW",
        "review": base / "review",
    }


def _latest_existing_file(suffixes: list[str]) -> Path | None:
    normalized = {suffix.lower() for suffix in suffixes}
    candidates: list[Path] = []
    roots = [validation_latest_dir(), user_outputs_dir()]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        try:
            files = root.rglob("*")
            for path in files:
                try:
                    resolved = path.resolve()
                    if (
                        resolved in seen
                        or not path.is_file()
                        or path.name.startswith("~$")
                        or path.suffix.lower() not in normalized
                    ):
                        continue
                    seen.add(resolved)
                    candidates.append(path)
                except OSError:
                    continue
        except OSError:
            continue
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _default_export_path(export_format: str) -> Path:
    normalized = export_format.lower().lstrip(".")
    suffixes = {
        "step": "STEP",
        "stl": "STL",
        "iges": "IGES",
        "parasolid": "x_t",
        "pdf": "PDF",
        "dxf": "DXF",
        "dwg": "DWG",
    }
    suffix = suffixes.get(normalized, normalized.upper())
    return _button_samples_dir() / f"installed_validation_export_{uuid.uuid4().hex[:8]}.{suffix}"


def _clean_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if value is not None and value != ""}


def _default_mcp_parameters(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    paths = _button_sample_paths()
    params = _clean_parameters(parameters)
    latest_part = _latest_existing_file([".sldprt"])
    default_part = str(latest_part or paths["shaft"])
    samples_dir = _button_samples_dir()
    assembly_group = "main"
    if tool_name in {"solidworks_add_concentric_mate", "solidworks_add_rotary_motor"}:
        assembly_group = tool_name.replace("solidworks_", "")
    assembly_path = samples_dir / f"installed_validation_assembly_{validation_assembly_token}_{assembly_group}.SLDASM"
    assembly_shaft = samples_dir / f"installed_validation_assembly_{validation_assembly_token}_{assembly_group}_shaft.SLDPRT"
    assembly_rotor = samples_dir / f"installed_validation_assembly_{validation_assembly_token}_{assembly_group}_rotor.SLDPRT"
    defaults: dict[str, Any] = {
        "solidworks_connect": {"visible": True, "wait_seconds": 1},
        "solidworks_health_check": {"start_solidworks": True},
        "solidworks_new_document": {"doc_type": "part"},
        "solidworks_create_basic_part": {
            "shape": "box",
            "width_mm": 80,
            "height_mm": 60,
            "depth_mm": 12,
            "output_path": str(paths["box"]),
            "color": "#9DA7AA",
        },
        "solidworks_open_document": {"path": str(_button_samples_dir() / f"installed_validation_open_{uuid.uuid4().hex[:8]}.SLDPRT")},
        "solidworks_save_document": {"path": str(paths["box"])},
        "solidworks_close_documents": {"close_all": False, "save_changes": False},
        "solidworks_add_component": {"path": str(assembly_rotor), "x_mm": 0, "y_mm": 0, "z_mm": 45, "fix_component": False},
        "solidworks_set_component_fixed": {"component_keyword": "rotor", "fixed": False},
        "solidworks_add_coincident_mate": {
            "component_a_keyword": "shaft",
            "component_b_keyword": "rotor",
            "feature_a_name": "Front Plane",
            "feature_b_name": "Front Plane",
        },
        "solidworks_add_distance_mate": {
            "component_a_keyword": "shaft",
            "component_b_keyword": "rotor",
            "feature_a_name": "Top Plane",
            "feature_b_name": "Top Plane",
            "distance_mm": 20,
        },
        "solidworks_add_concentric_mate": {
            "component_a_keyword": "shaft",
            "component_b_keyword": "rotor",
            "radius_a_min_mm": 9,
            "radius_a_max_mm": 11,
            "radius_b_min_mm": 9,
            "radius_b_max_mm": 11,
            "lock_rotation": False,
        },
        "solidworks_set_appearance": {"target": "document", "color": "#8FA3AD"},
        "solidworks_review_active": {"output_dir": str(paths["review"]), "basename": "installed_button_review"},
        "solidworks_add_rotary_motor": {
            "shaft_component_keyword": "shaft",
            "rotor_component_keyword": "rotor",
            "shaft_radius_min_mm": 9,
            "shaft_radius_max_mm": 11,
            "rotor_radius_min_mm": 9,
            "rotor_radius_max_mm": 11,
            "rpm": 30,
            "calculate": False,
            "play": False,
        },
    }.get(tool_name, {})
    if tool_name in {
        "solidworks_add_component",
        "solidworks_set_component_fixed",
        "solidworks_add_coincident_mate",
        "solidworks_add_distance_mate",
        "solidworks_add_concentric_mate",
        "solidworks_add_rotary_motor",
    }:
        defaults = {
            **defaults,
            "_assembly_path": str(assembly_path),
            "_assembly_shaft_path": str(assembly_shaft),
            "_assembly_rotor_path": str(assembly_rotor),
        }
    if tool_name == "solidworks_export_active":
        export_format = str(params.get("export_format") or "step").lower().lstrip(".")
        defaults = {"output_path": str(_default_export_path(export_format)), "export_format": export_format}
    if tool_name == "solidworks_create_basic_part" and params.get("shape") == "blank-part":
        params["shape"] = "box"
    if tool_name in {"solidworks_save_document", "solidworks_export_active", "solidworks_review_active", "solidworks_set_appearance"}:
        default_part_path = paths["box"]
        if tool_name != "solidworks_save_document":
            default_part_path = _button_samples_dir() / f"installed_validation_context_{uuid.uuid4().hex[:8]}.SLDPRT"
        default_part = str(default_part_path)
        defaults = {**defaults, "_default_part_path": default_part}
    return {**defaults, **params}


def _strip_internal_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if not key.startswith("_")}


def _run_context_mcp_tool(tool_name: str, parameters: dict[str, Any], *, attempts: int = 2):
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return mcp_tool_runner.run(tool_name, parameters, raise_on_error_status=True)
        except Exception as exc:
            last_error = exc
            if attempt >= attempts - 1:
                raise
            try:
                mcp_tool_runner.run("solidworks_connect", {"wait_seconds": 2, "visible": True}, raise_on_error_status=False)
            except Exception:
                pass
            time.sleep(1.5)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"{tool_name} 上下文准备未执行。")


def _ensure_sample_part(path: Path, shape: str, *, radius_mm: float = 10, depth_mm: float = 70, color: str = "#AEB7BC") -> None:
    if path.exists():
        try:
            _run_context_mcp_tool("solidworks_open_document", {"path": str(path)}, attempts=2)
        except Exception:
            if not _active_document_matches_path(path):
                raise
        return
    params: dict[str, Any] = {
        "shape": shape,
        "output_path": str(path),
        "depth_mm": depth_mm,
        "color": color,
    }
    if shape == "cylinder":
        params["radius_mm"] = radius_mm
    else:
        params.update({"width_mm": 80, "height_mm": 60})
    _run_context_mcp_tool("solidworks_create_basic_part", params, attempts=3)


def _ensure_sample_assembly(parameters: dict[str, Any] | None = None) -> None:
    paths = _button_sample_paths()
    parameters = parameters or {}
    assembly_path = Path(str(parameters.get("_assembly_path") or paths["assembly"])).expanduser()
    shaft_path = Path(str(parameters.get("_assembly_shaft_path") or paths["shaft"])).expanduser()
    rotor_path = Path(str(parameters.get("_assembly_rotor_path") or paths["rotor"])).expanduser()
    if assembly_path.exists():
        _run_context_mcp_tool("solidworks_open_document", {"path": str(assembly_path)}, attempts=2)
        return
    _ensure_sample_part(shaft_path, "cylinder", radius_mm=10, depth_mm=90, color="#AEB7BC")
    _ensure_sample_part(rotor_path, "cylinder", radius_mm=10, depth_mm=42, color="#C5B58A")
    _run_context_mcp_tool("solidworks_new_document", {"doc_type": "assembly"}, attempts=2)
    mcp_tool_runner.run(
        "solidworks_add_component",
        {"path": str(shaft_path), "x_mm": 0, "y_mm": 0, "z_mm": 0, "fix_component": True},
        raise_on_error_status=True,
    )
    mcp_tool_runner.run(
        "solidworks_add_component",
        {"path": str(rotor_path), "x_mm": 0, "y_mm": 0, "z_mm": 45, "fix_component": False},
        raise_on_error_status=True,
    )
    mcp_tool_runner.run("solidworks_save_document", {"path": str(assembly_path)}, raise_on_error_status=True)


def _prepare_mcp_context(tool_name: str, parameters: dict[str, Any]) -> None:
    paths = _button_sample_paths()
    if tool_name == "solidworks_open_document":
        target = Path(str(parameters.get("path", paths["shaft"]))).expanduser()
        if target.suffix.lower() == ".sldprt" and not target.exists():
            _ensure_sample_part(target, "cylinder", radius_mm=10, depth_mm=90)
    elif tool_name == "solidworks_save_document":
        part_path = Path(str(parameters.get("_default_part_path") or paths["shaft"])).expanduser()
        _ensure_sample_part(part_path, "cylinder", radius_mm=10, depth_mm=90)
    elif tool_name in {"solidworks_export_active", "solidworks_review_active", "solidworks_set_appearance"}:
        part_path = Path(str(parameters.get("_default_part_path") or paths["box"])).expanduser()
        _ensure_sample_part(part_path, "box", color="#9DA7AA")
    elif tool_name in {
        "solidworks_add_component",
        "solidworks_set_component_fixed",
        "solidworks_add_coincident_mate",
        "solidworks_add_distance_mate",
        "solidworks_add_concentric_mate",
        "solidworks_add_rotary_motor",
    }:
        _ensure_sample_assembly(parameters)
    elif tool_name == "solidworks_close_documents":
        _ensure_sample_part(paths["shaft"], "cylinder", radius_mm=10, depth_mm=90)


def _active_document_matches_path(path: Path) -> bool:
    try:
        from sw_connect import connect_solidworks, get_com_member

        _sw, model = connect_solidworks(wait_seconds=1)
        if model is None:
            return False
        active_path = str(get_com_member(model, "GetPathName") or "")
        if active_path and Path(active_path).resolve() == path.expanduser().resolve():
            return True
        active_title = str(get_com_member(model, "GetTitle") or "")
        return bool(active_title and active_title.lower().startswith(path.stem.lower()))
    except Exception:
        return False


def _run_mcp_tool_with_context(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    import json

    _prepare_mcp_context(tool_name, parameters)
    runner_parameters = _strip_internal_parameters(parameters)
    try:
        return mcp_tool_runner.run(tool_name, runner_parameters, raise_on_error_status=True).__dict__
    except RuntimeError:
        if tool_name == "solidworks_open_document":
            target = Path(str(runner_parameters.get("path", ""))).expanduser()
            if target and _active_document_matches_path(target):
                payload = {"status": "ok", "document": {"path": str(target), "already_active": True}}
                return {
                    "stdout": json.dumps(payload, ensure_ascii=False, indent=2),
                    "stderr": "",
                    "created_files": [str(target)],
                    "data": {"raw": payload, "tool": tool_name},
                }
        raise


def _run_drawing_export(parameters: dict[str, Any]) -> dict[str, Any]:
    part_path = Path(str(parameters.get("part_path") or _button_sample_paths()["shaft"])).expanduser()
    if not part_path.exists():
        _ensure_sample_part(part_path, "cylinder", radius_mm=10, depth_mm=90)
    return export_part_drawing(
        str(part_path),
        str(parameters.get("output_path", "")) if parameters.get("output_path") else "",
        str(parameters.get("drawing_path")) if parameters.get("drawing_path") else None,
        str(parameters.get("export_format") or "dwg"),
    )


async def _run_mcp_record(
    capability_id: str,
    tool_name: str,
    parameters: dict,
    timeout_seconds: int = 180,
) -> SolidWorksExecutionRecord:
    preflight = await solidworks_service.preflight_async(timeout_seconds=5)
    if not preflight.can_run_real_com:
        _raise_preflight_dependency_error(preflight, capability_id)
    normalized_parameters = _default_mcp_parameters(tool_name, parameters)
    return await solidworks_queue.submit(
        capability_id=capability_id,
        parameters=_strip_internal_parameters(normalized_parameters),
        operation=lambda params: _run_mcp_tool_with_context(tool_name, normalized_parameters),
        timeout_seconds=timeout_seconds,
    )


async def _run_mcp_action(action: str, tool_name: str, parameters: dict, timeout_seconds: int = 60) -> SolidWorksActionResponse:
    preflight = await solidworks_service.preflight_async(timeout_seconds=5)
    if not preflight.can_run_real_com:
        _raise_preflight_dependency_error(preflight, action)
    record = await _run_mcp_record(f"mcp.{tool_name}", tool_name, parameters, timeout_seconds=timeout_seconds)
    ok = record.status.value == "passed"
    return SolidWorksActionResponse(
        ok=ok,
        mode="solidworks",
        action=action,
        message=f"{action} 已通过 {tool_name} {'完成' if ok else '失败'}。",
        stdout=record.stdout,
        stderr=record.stderr,
        files=record.created_files,
        data={
            "run_id": record.run_id,
            "capability_id": record.capability_id,
            "active_document_before": record.active_document_before,
            "active_document_after": record.active_document_after,
            "error_summary": record.error_summary,
        },
        real_execution_verified=record.real_execution_verified,
        evidence=record.evidence,
        active_document_before=record.active_document_before,
        active_document_after=record.active_document_after,
        created_files_exist=record.created_files_exist,
    )


def _run_script_capability(capability: Capability, parameters: dict) -> dict:
    import importlib.util
    import sys

    source = Path(capability.source_path)
    if source.suffix.lower() != ".py" or not source.exists():
        return {"message": "该能力仅用于上下文，或来源不是 Python Script。", "source_path": capability.source_path}
    scripts_dir = source.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(f"_swai_capability_{source.stem}", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法导入 Script 能力：{source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    public_functions = [name for name in dir(module) if not name.startswith("_") and callable(getattr(module, name))]
    return {
        "message": "Script 能力已成功导入。COM 操作请使用明确的直接工具或生成后的 Script。",
        "source_path": str(source),
        "public_functions": public_functions,
        "parameters": parameters,
    }


api_router = APIRouter()
api_router.include_router(router)
api_router.include_router(protected)
