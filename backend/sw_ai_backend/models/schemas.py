from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StatusLevel(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"


class RunStage(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    GENERATED = "generated"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    REVIEWING = "reviewing"
    DONE = "done"
    FAILED = "failed"


class CapabilitySourceType(str, Enum):
    SKILL_MD = "skill_md"
    SCRIPT = "script"
    MCP_TOOL = "mcp_tool"
    REFERENCE = "reference"
    SUBSKILL = "subskill"
    EXAMPLE = "example"


class CapabilityExecutionKind(str, Enum):
    PYTHON_SCRIPT = "python_script"
    MCP_TOOL = "mcp_tool"
    PROMPT_CONTEXT = "prompt_context"
    DOCUMENTATION_ONLY = "documentation_only"


class AddinRequirement(str, Enum):
    NONE = "none"
    MOTION = "motion"
    SIMULATION = "simulation"
    SHEET_METAL = "sheet_metal"
    WELDMENTS = "weldments"
    OTHER = "other"


class RealValidationStatus(str, Enum):
    UNTESTED = "untested"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED_WITH_REASON = "skipped_with_reason"


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class HealthResponse(BaseModel):
    ok: bool
    app: str
    version: str
    mode: Literal["api"]
    project_root: str
    user_data_dir: str
    time: datetime = Field(default_factory=utc_now)


class LLMProfile(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    api_base_url: str = Field(min_length=1)
    api_key: str = ""
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2200, ge=1, le=200000)
    timeout_seconds: int = Field(default=60, ge=5, le=600)

    @field_validator("api_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


class AppConfig(BaseModel):
    profiles: list[LLMProfile]
    active_profile_id: str
    theme: Literal["dark", "light", "system"] = "dark"
    solidworks_skill_path: str = "vendor/skills/solidworks-automation"
    taste_skill_path: str = "vendor/skills/taste-skill"
    output_dir: str = ""
    validation_output_dir: str = "outputs/validation"
    part_template_path: str = ""
    assembly_template_path: str = ""
    drawing_template_path: str = ""
    require_approval: bool = True
    mock_mode: bool = False


class ConfigResponse(BaseModel):
    config: AppConfig
    config_path: str
    secure_storage: Literal["config-file"]
    note: str


class TestConnectionRequest(BaseModel):
    profile: LLMProfile


class TestConnectionResponse(BaseModel):
    ok: bool
    provider: str
    message: str
    latency_ms: int | None = None
    models: list[str] = Field(default_factory=list)
    models_verified: bool = False
    chat_verified: bool = False
    provider_verified_at: datetime | None = None


class SkillFunction(BaseModel):
    name: str
    signature: str
    module: str
    doc: str = ""


class SkillDocument(BaseModel):
    title: str
    path: str
    kind: Literal["skill", "reference", "subskill", "example", "script", "mcp", "taste"]
    modified_at: datetime | None = None
    excerpt: str = ""


class SkillIndexResponse(BaseModel):
    solidworks_available: bool
    taste_available: bool
    solidworks_path: str
    taste_path: str
    indexed_at: datetime = Field(default_factory=utc_now)
    documents: list[SkillDocument]
    functions: list[SkillFunction]
    mcp_tools: list[str]
    context_summary: str


class Capability(BaseModel):
    id: str
    title: str
    source_type: CapabilitySourceType
    source_path: str
    callable: bool
    execution_kind: CapabilityExecutionKind
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    requires_solidworks: bool
    requires_active_document: bool
    requires_part: bool
    requires_assembly: bool
    requires_drawing: bool
    requires_addin: AddinRequirement = AddinRequirement.NONE
    ui_exposed: bool
    api_endpoint: str
    test_case: str
    real_sw2025_status: RealValidationStatus = RealValidationStatus.UNTESTED
    skip_reason: str = ""


class CapabilityListResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    capabilities_path: str
    capabilities: list[Capability]


class CapabilityRunRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=180, ge=5, le=3600)


class CapabilityValidationResponse(BaseModel):
    capability_id: str
    status: RealValidationStatus
    report_path: str = ""
    created_files: list[str] = Field(default_factory=list)
    skip_reason: str = ""
    error_summary: str = ""


class SkillSyncResponse(BaseModel):
    ok: bool
    solidworks: str
    taste: str
    message: str


class PreflightCheck(BaseModel):
    key: str
    label: str
    status: StatusLevel
    message: str
    suggestion: str = ""


class PreflightResponse(BaseModel):
    mode: Literal["solidworks", "mock"]
    checks: list[PreflightCheck]
    can_run_real_com: bool
    solidworks_version: str = ""
    report_json: str = ""
    report_markdown: str = ""
    state: str = ""
    stale: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None


class SolidWorksActionRequest(BaseModel):
    path: str = ""
    output_path: str = ""
    format: str = "STEP"
    parameters: dict[str, Any] = Field(default_factory=dict)


class SolidWorksActionResponse(BaseModel):
    ok: bool
    mode: Literal["solidworks", "mock"]
    action: str
    message: str
    stdout: str = ""
    stderr: str = ""
    files: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    real_execution_verified: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)
    active_document_before: str = ""
    active_document_after: str = ""
    created_files_exist: bool = False


class SolidWorksSessionResponse(BaseModel):
    attached: bool
    visible: bool
    version: str = ""
    revision: str = ""
    executable_path: str = ""
    active_document_title: str = ""
    active_document_type: str = ""
    message: str


class AIPlanRequest(BaseModel):
    prompt: str = Field(min_length=1)
    profile_id: str | None = None
    output_dir: str = ""


class AIPlanResponse(BaseModel):
    plan: str
    risks: list[str]
    required_files: list[str]
    prompt: str
    demo_mode: bool
    provider_verified_at: datetime | None = None


class GenerateScriptRequest(BaseModel):
    prompt: str = Field(min_length=1)
    profile_id: str | None = None
    output_dir: str = ""


class GenerateScriptResponse(BaseModel):
    plan: str
    risks: list[str]
    required_files: list[str]
    script: str
    script_path: str
    demo_mode: bool
    fallback_used: bool = False
    fallback_reason: str = ""
    capability_ids: list[str] = Field(default_factory=list)
    provider_verified_at: datetime | None = None


class ApproveRunRequest(BaseModel):
    script_path: str = Field(min_length=1)
    prompt: str = ""
    timeout_seconds: int = Field(default=120, ge=5, le=1800)


class RunEvent(BaseModel):
    time: datetime = Field(default_factory=utc_now)
    stage: RunStage
    message: str
    stdout: str = ""
    stderr: str = ""


class RunRecord(BaseModel):
    run_id: str
    stage: RunStage
    prompt: str = ""
    script_path: str = ""
    stdout: str = ""
    stderr: str = ""
    files: list[str] = Field(default_factory=list)
    events: list[RunEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    real_execution_verified: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)


class SolidWorksExecutionRecord(BaseModel):
    run_id: str
    capability_id: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: ExecutionStatus = ExecutionStatus.QUEUED
    stdout: str = ""
    stderr: str = ""
    created_files: list[str] = Field(default_factory=list)
    active_document_before: str = ""
    active_document_after: str = ""
    error_summary: str = ""
    log_path: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    real_execution_verified: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_files_exist: bool = False


class RunCreatedResponse(BaseModel):
    run_id: str
    stage: RunStage
    message: str


class MCPStatusResponse(BaseModel):
    running: bool
    pid: int | None = None
    command: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    message: str


class MCPToolDefinition(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    source_path: str = ""


class MCPConfigSnippetsResponse(BaseModel):
    snippets: dict[str, str]
    server_path: str


class RealTestRunResponse(BaseModel):
    ok: bool
    report_json: str
    report_markdown: str
    capability_matrix_csv: str
    files_manifest_json: str
    core_passed: int
    core_failed: int
    optional_skipped: list[CapabilityValidationResponse] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
